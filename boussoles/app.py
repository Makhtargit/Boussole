"""Boussoles SCANOPTIMUS9 — tableau de bord qui se met à jour seul.   Lancer :  streamlit run app.py"""
import datetime as dt
import numpy as np, pandas as pd, streamlit as st
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from boussoles.regles import MARCHES, SEUIL, SP
from boussoles.donnees import tout_charger
from boussoles.calcul import tout_calculer, historique, nb, pc, cone, rang
from boussoles.titres import titres as calc_titres, THEMES, peremptions, or_titres
from boussoles.ui import CSS, COUL, badge, chip, bar, jauge, sparkline, carte

st.set_page_config(page_title="Boussoles SCANOPTIMUS9", page_icon="🧭", layout="wide", initial_sidebar_state="expanded")
def md(h): st.markdown(h.replace("\n", ""), unsafe_allow_html=True)
md(CSS)
def jour(d, court=False): return "—" if d is None or pd.isna(d) else pd.Timestamp(d).strftime("%d/%m" if court else "%d/%m/%Y")
COURT = {"SOX": "Semi-conducteurs", "Logiciel": "Logiciel", "NDX": "Nasdaq 100", "S&P 500": "S&P 500", "Mines d'or (GDX)": "Mines d'or", "Pétrolières (XLE)": "Pétrolières", "Or": "Or · stratégie"}
SYMB = {"ok": "●", "warn": "▲", "bad": "■", "info": "◆", "mute": "○"}

# ---------------------------------------------------------------- données
@st.cache_data(ttl=6 * 3600, show_spinner="Téléchargement des cours, des taux, du dollar et des positions des spéculateurs…")
def charger():
    D, src = tout_charger(MARCHES); return D, src, dt.datetime.now()

@st.cache_data(show_spinner="Calcul des boussoles…", max_entries=12)
def calculer(_D, asof, memoire, cle):
    R = tout_calculer(_D, asof, memoire); H = historique(R[2], R[1]); return R + (H,)

with st.sidebar:
    st.markdown("### 🧭 Boussoles")
    if st.button("Mettre à jour les données", width="stretch"): charger.clear(); calculer.clear()
D, SRC, quand = charger()
if D["vix"].empty or D[SP].empty:
    st.error("Aucune donnée disponible (ni réseau, ni copie locale)."); st.stop()
seances = D["vix"].index[D["vix"].index <= min(D["vix"].index[-1], D[SP].index[-1])]
dernier = seances[-1]
with st.sidebar:
    asof = st.date_input("Séance analysée", value=dernier.date(), min_value=dt.date(1995, 1, 3), max_value=dernier.date())
    comparer = st.toggle("Comparer avec une autre séance", value=False)
    ref_def = seances[seances <= pd.Timestamp(asof)][-6] if (seances <= pd.Timestamp(asof)).sum() > 6 else seances[0]
    asof2 = st.date_input("Séance de comparaison", value=ref_def.date(), min_value=dt.date(1995, 1, 3), max_value=dernier.date(), disabled=not comparer)
    mem_lab = st.radio("Mémoire des statistiques", ["4 dernières années", "Tout l'historique (1990)"], index=0,
                       help="Âges, profondeurs, situations comparables et carte des prix. Les lois du VIX restent ajustées sur 1990-2026 (il faut assez de corrections).")
    memoire = 4 if mem_lab.startswith("4") else None
    st.divider(); st.markdown("**Péremption**")
    PER = peremptions()
    for lab, ech, j in PER:
        ic = "🔴" if j < 0 else ("🟡" if j <= 30 else "🟢")
        st.caption(f"{ic} {lab} · {'expiré depuis ' + str(-j) + ' j' if j < 0 else 'jusqu’au ' + ech.strftime('%d/%m/%Y')}")
    st.caption(f"Données du {quand:%d/%m/%Y %H:%M}")
    for k, v in SRC.items(): st.caption(f"{'🟢' if v not in ('indisponible', 'copie locale') else ('🟡' if v == 'copie locale' else '🔴')} {k} · {v}")
cle = str(quand)
asof, C, E, O, ST, LO, V, H = calculer(D, pd.Timestamp(asof), memoire, cle)
R2 = calculer(D, pd.Timestamp(asof2), memoire, cle) if comparer else None
if R2: _, C2, E2, O2, ST2, LO2, V2, _ = R2[:8]; d2 = jour(R2[0], True)

@st.cache_data(show_spinner="Sélection des titres…", max_entries=12)
def titres_du_jour(_E, _C, _T, asof_, cle_):
    try: return calc_titres(_E, _C, _T, asof_)
    except Exception as ex: return {"erreur": str(ex)}
TI = titres_du_jour(E, C, D.get("titres"), asof, cle)
ok_src = sum(v not in ("indisponible", "copie locale") for v in SRC.values())
mem_txt = "4 dernières années" if memoire else "1990-2026"

md(f'<div class="topbar"><div><div class="brand">SCANOPTIMUS9 · BOUSSOLES</div><div class="title">Séance du {jour(asof)}'
   f'{(" <span style=" + chr(39) + "font-size:18px;color:#64748b;font-weight:600" + chr(39) + ">· comparée au " + jour(R2[0]) + "</span>") if R2 else ""}</div>'
   f'<div class="sub">On ne prédit pas, on gère : chaque verdict applique une loi testée. Statistiques : {mem_txt}.</div></div>'
   f'<div>{chip(f"{ok_src}/{len(SRC)} sources en direct", "ok" if ok_src == len(SRC) else "warn")}</div></div>')

_exp = [lab for lab, _, j in PER if j < 0]
if _exp: st.warning("À réviser : " + " · ".join(_exp) + ". Voir le journal de décisions.")

def delta(txt): return f'<div class="small" style="margin-top:6px;color:#a5b4fc">⇄ {txt}</div>' if R2 else ""
def dnum(a, b, d=1, unite=""):
    x = a - b; return f'{"+" if x >= 0 else ""}{nb(x, d)}{unite}'

t1, t2, t3 = st.tabs(["Vue d'ensemble", "Marchés", "Interroger l'historique"])

# ================================================================ VUE D'ENSEMBLE
def tuile_climat(lab, valeur, etat, niv, concl, visuel, dl=""):
    return carte(f'<div class="row"><span class="lab">{lab}</span>{badge(etat, niv)}</div>'
                 f'<div class="row" style="align-items:flex-end;margin-top:6px"><div class="big num">{valeur}</div><div>{visuel}</div></div>'
                 f'<div class="txt" style="margin-top:6px">{concl}</div>{dl}')
def u_(x): return f"<span style='font-size:16px;color:#94a3b8'>{x}</span>"

def bloc_cycle(e, st_):
    cy = e["cycle"]; A = e["A"]; pr = rang(cy["seances"], st_["cycle_seances"])
    if A["investie"]:
        tete = f'<span style="color:{COUL["ok"]}">●</span> CYCLE OUVERT · J+{cy["seances"]}'
        l1 = f'Depuis le creux du {jour(cy["creux"])} : {pc(cy["gain_actuel"], 0)} (sommet {pc(cy["gain"], 0)}). Plus long que {pc(pr, 0, False)} des cycles depuis 1990.'
        l2 = f'Recul du sommet {pc(cy["recul"])} · {pc(cy["recul_x_seuil"], 0, False)} du chemin vers la sortie ({nb(A["niveau_sortie"])})'
        b = bar(cy["recul_x_seuil"], "warn" if cy["recul_x_seuil"] >= 0.5 else "ok", 1.0)
    else:
        tete = f'<span style="color:{COUL["bad"]}">■</span> CYCLE FERMÉ'; l1 = f"En attente d'un signal S7 (dernier : {jour(e['dernier_S7'])})."; l2 = ""; b = ""
    return f'<div class="lab" style="margin-top:12px">{tete}</div><div class="txt" style="margin-top:4px">{l1}</div>{b}<div class="small" style="margin-top:4px">{l2}</div>'

def bloc_mini(e, lois):
    m = e["mini"]
    if m["phase"] == "correction":
        d = next(l for l in lois if l["titre"].startswith("Loi du VIX · durée")); j = d["jauge"]
        tete = f'<span style="color:{COUL["warn"]}">▼</span> MINI-CORRECTION · SÉANCE {m["seances"]}'
        l1 = f'{pc(-m["ampleur"])} du mini-pic (au pire {pc(-m["ampleur_max"])}, {nb(m["x_seuil_max"])} seuil). Loi du VIX : fin entre {j[3][0]:.0f} et {j[3][1]:.0f} séances.'
        b = bar(j[0] / j[1], d["niveau"], j[2] / j[1], (j[3][0] / j[1], j[3][1] / j[1]))
        c_ = next(l for l in lois if l["titre"] == "Creux ou continuation ?"); l2 = f'{c_["valeur"].capitalize()} · barre = séances, cadre = intervalle de la loi'
    else:
        d = next(l for l in lois if l["titre"] == "Dynamique de la mini-hausse"); j = d["jauge"]
        tete = f'<span style="color:{COUL["ok"]}">▲</span> MINI-HAUSSE · {m["seances"]} SÉANCES'
        l1 = f'{pc(m["ampleur"])} depuis le creux, {pc(-m["retombee"])} depuis son plus haut. Bascule en correction sous {nb(m["niveau_bascule"])}.'
        b = bar(j[0], d["niveau"], 1.0, j[3]); c_ = next(l for l in lois if l["titre"] == "Bascule en correction ?")
        l2 = f'Bascule dans les 10 séances : {c_["valeur"].split(" ")[0]} des cas comparables · barre = retombée vers la bascule'
    return f'<div class="lab" style="margin-top:14px">{tete}</div><div class="txt" style="margin-top:4px">{l1}</div>{b}<div class="small" style="margin-top:4px">{l2}</div>'

with t1:
    md('<div class="sec">Climat</div>')
    vx, q8 = C["vix"], C["vix_q80"]; dE = C["seances_depuis_e80"]; vm5 = C["vix_max5"]
    if vx >= 30: pe, pn = "PANIQUE", "bad"
    elif dE is not None and dE <= 7: pe, pn = "FENÊTRE DE CREUX", "ok"
    elif vx >= q8 and vx >= 0.95 * vm5: pe, pn = "PEUR QUI MONTE", "warn"
    elif vx >= q8 and vx <= SEUIL["reflux"] * vm5: pe, pn = "PEUR QUI REFLUE", "ok"
    elif vx >= q8: pe, pn = "PEUR ÉLEVÉE", "warn"
    else: pe, pn = "CALME", "ok"
    aD, bD, _ = (ST.get("NDX") or ST[SP])["duree"]
    c1, c2, c3, c4, c5 = st.columns(5)
    with c1: md(tuile_climat("Peur · VIX", nb(vx, 1), pe, pn, f"Seuil de peur {nb(q8, 1)} · à ce VIX, une correction du Nasdaq dure ≈ {aD * (vx / 20) ** bD:.0f} séances.",
                             jauge(vx, 45, pn, q8, 120), delta(f"{d2} : {nb(C2['vix'], 1)} ({dnum(vx, C2['vix'])})") if R2 else ""))
    rr = C["taux_reel_12m"]; n_ = "warn" if rr >= SEUIL["taux_reel_12m"] else "ok"
    with c2: md(tuile_climat("Taux réel · 12 mois", f"{'+' if rr >= 0 else ''}{nb(rr)}{u_(' pt')}", "VENT CONTRAIRE" if n_ == "warn" else "NEUTRE", n_,
                             f"Taux réel {nb(C['taux_reel'])} %. Au-delà de +0,5 pt, la tech fait moins bien que le marché.", jauge(max(rr, 0), 1.5, n_, 0.5, 120),
                             delta(f"{d2} : {nb(C2['taux_reel_12m'])} pt ({dnum(rr, C2['taux_reel_12m'], 2)})") if R2 else ""))
    t6 = C["taux10_6m"]; f12 = C["fed_12m"] if C["fed_12m"] == C["fed_12m"] else 0.0; cc = max(t6, f12); n_ = "bad" if cc >= SEUIL["taux10_6m"] else "ok"
    with c3: md(tuile_climat("Coût du capital", f"{'+' if t6 >= 0 else ''}{nb(t6)}{u_(' pt')}", "ARMÉ" if n_ == "bad" else "CALME", n_,
                             f"Taux 10 ans {nb(C['taux10'])} % ({'+' if t6 >= 0 else ''}{nb(t6)} pt sur 6 mois) · Fed {nb(C['fed'])} % ({'+' if f12 >= 0 else ''}{nb(f12)} pt sur 12 mois). L'interrupteur s'arme à +1 pt et coupe si l'indice passe sous sa moyenne 50.",
                             jauge(max(cc, 0), 1.5, n_, 1.0, 120), delta(f"{d2} : 10 ans {nb(C2['taux10_6m'])} pt ({dnum(t6, C2['taux10_6m'], 2)})") if R2 else ""))
    u = C["dollar_10s"]; n_ = "bad" if C["dollar_ruee_20s"] else "ok"
    with c4: md(tuile_climat("Dollar · 10 séances", pc(u, 2), "RUÉE" if n_ == "bad" else "CALME", n_, "Une ruée (≥ +1,14 %) transforme 57-74 % des creux en couteaux.",
                             jauge(max(u, 0), 0.02, n_, 0.0114, 120), delta(f"{d2} : {pc(C2['dollar_10s'], 2)}") if R2 else ""))
    co = C["concentration"]; n_ = "warn" if C["concentration_60"] else "ok"
    with c5: md(tuile_climat("Concentration · NDX", pc(co) if co == co else "—", "VIGILANCE" if n_ == "warn" else "LARGE", n_,
                             "NDX contre la moyenne à parts égales de ses membres sur 6 mois. Au-delà de +5 pts, la hausse tient à quelques géants (profil du sommet de fin 2021).",
                             jauge(max(co, 0) if co == co else 0, 0.15, n_, 0.05, 120)))

    md('<div class="sec">Signaux du jour</div>')
    def comptes(E_, C_):
        nA = sum(e["A"]["investie"] for e in E_.values()); s5 = [n for n, e in E_.items() if e["S5"]["valide"]]
        p4 = [n for n, e in E_.items() if e["P4"]["seances"] is not None and e["P4"]["seances"] <= 10]
        nr = [n for n, e in E_.items() if e["mini"]["phase"] == "correction" and e["mini"]["x_seuil_max"] >= SEUIL["approche"]]
        return nA, s5, p4, nr
    nA, nS5, nP4, nNR = comptes(E, C)
    if R2: nA2, nS52, nP42, nNR2 = comptes(E2, C2)
    dc = lambda a, b: f' <span style="font-size:15px;color:#a5b4fc">({"+" if a - b >= 0 else ""}{a - b})</span>' if R2 else ""
    cpt = [("Cycles ouverts", f"{nA}/{len(E)}" + dc(nA, nA2 if R2 else 0), "ok" if nA == len(E) else ("warn" if nA else "bad"), "stratégie A investie"),
           ("Signaux de creux S5", str(len(nS5)) + dc(len(nS5), len(nS52) if R2 else 0), "ok" if nS5 else "mute", " · ".join(COURT[n] for n in nS5) or "aucun"),
           ("Signaux de pic P4", str(len(nP4)) + dc(len(nP4), len(nP42) if R2 else 0), "warn" if nP4 else "mute", " · ".join(COURT[n] for n in nP4) or "aucun (10 séances)"),
           ("Près du non-retour", str(len(nNR)) + dc(len(nNR), len(nNR2) if R2 else 0), "bad" if nNR else "mute", " · ".join(COURT[n] for n in nNR) or "aucun"),
           ("Fenêtre VIX 80e", f"J+{dE}" if dE is not None and dE <= 7 else "fermée", "ok" if dE is not None and dE <= 7 else "mute", f"dernière entrée {jour(C['dernier_e80'])}")]
    for col, (lab, n, niv, det) in zip(st.columns(5), cpt):
        with col: md(carte(f'<div class="lab">{lab}</div><div class="n num" style="color:{COUL[niv]}">{n}</div><div class="small" style="margin-top:6px">{det}</div>', "card tight counter"))

    md('<div class="sec">Marchés · cycle et mini-cycle</div>')
    noms = list(E)
    for i in range(0, len(noms), 3):
        for col, n in zip(st.columns(3), noms[i:i + 3]):
            e = E[n]; vtxt, vniv, raison = V[n]; s = e["s"]; ch1 = s.iloc[-1] / s.iloc[-2] - 1
            lw = next((l for l in LO[n] if l["niveau"] == vniv), LO[n][0])
            chips = (chip("S5 ACTIF", "ok") if e["S5"]["valide"] else "") + (chip(f"P4 J+{e['P4']['seances']}", "warn") if n in nP4 else "") + \
                    (chip("NON-RETOUR PROCHE", "bad") if n in nNR else "")
            cc = next((l for l in LO[n] if l["titre"] in ("Creux ou continuation ?", "Bascule en correction ?")), None)
            if cc and cc["titre"] == "Creux ou continuation ?": chips += chip(cc["valeur"], cc["niveau"])
            dl = ""
            if R2 and n in E2:
                e2 = E2[n]; v2 = V2[n]
                dl = delta(f"{d2} : {v2[0].lower()} → {vtxt.lower()} · cours {pc(e['prix'] / e2['prix'] - 1)} · "
                           + (f"mini-{e2['mini']['phase']} {nb(e2['mini']['x_seuil_max'] if e2['mini']['phase'] == 'correction' else e2['mini']['x_seuil'])} seuil"))
            spk = sparkline(s.iloc[-126:].values, vniv, bandes=e["bande80"][10])
            with col: md(carte(f'<div class="row"><div><div class="lab">{n}</div><div class="mid">{COURT[n]}</div></div>{badge(vtxt, vniv)}</div>'
                               f'<div class="row" style="margin-top:8px"><span class="big num">{nb(e["prix"])}</span>{chip(pc(ch1), "ok" if ch1 >= 0 else "bad")}</div>'
                               f'<div style="margin:6px 0 0 0">{spk}</div><div class="small">6 mois · cône = carte des prix à 10 séances (80 %, situations comparables)</div>'
                               f'{bloc_cycle(e, ST[n])}{bloc_mini(e, LO[n])}'
                               f'<div class="txt" style="margin-top:12px;padding-top:10px;border-top:1px solid #1e293b"><b style="color:{COUL[vniv]}">{SYMB[vniv]} {raison}</b> — {lw["conclusion"]}</div>'
                               f'<div style="margin-top:8px">{chips}</div>{dl}'))
        st.write("")

    if O:
        md('<div class="sec">Or</div>')
        nd, na = sum(O["decor"].values()), sum(O["amorce"].values()); b = O["budget"]
        dots = lambda dct: "".join(f'<span class="dot" style="background:{COUL["ok"] if v else "#1e293b"};border:1px solid {COUL["ok"] if v else "#334155"}"></span>' for v in dct.values())
        etat = ("INVESTIE", "ok") if O["investie"] else (("DÉCOR PRÊT", "warn") if nd == 3 else ("EN ATTENTE", "mute"))
        c1, c2, c3, c4 = st.columns([1.3, 1, 1, 1])
        with c1: md(carte(f'<div class="row"><span class="lab">Stratégie or · 70 GDX / 30 PHYS</span>{badge(etat[0], etat[1])}</div>'
                          f'<div class="txt" style="margin-top:10px">{"En position : on suit les sorties (or −13 %, stop de départ, règle de cycle)." if O["investie"] else "Hors marché : on attend le décor complet puis l’amorce."}</div>'
                          f'<div class="small" style="margin-top:8px">Or {nb(O["or_prix"], 1)} · GDX {nb(O["gdx"])}</div>'
                          + (delta(f"{d2} : décor {sum(O2['decor'].values())}/3, amorce {sum(O2['amorce'].values())}/3") if R2 and O2 else "")))
        with c2: md(carte(f'<div class="lab">Décor (60 séances)</div><div class="row" style="margin-top:8px"><span class="big num">{nd}/3</span><span>{dots(O["decor"])}</span></div><div class="small">dollar · taux réel · spéculateurs</div>', "card counter"))
        with c3: md(carte(f'<div class="lab">Amorce (20 séances)</div><div class="row" style="margin-top:8px"><span class="big num">{na}/3</span><span>{dots(O["amorce"])}</span></div><div class="small">taux ↓ · volatilité ↓ · GDX &gt; S&amp;P</div>', "card counter"))
        with c4: md(carte(f'<div class="lab">Budget de risque</div><div class="row" style="margin-top:8px"><span class="big num">{b["part"]:.0%}</span>{jauge(b["part"], 1, "info", 0.7, 90)}</div><div class="small">part de mines conseillée</div>', "card counter"))

    md('<div class="sec">Ce que valent nos règles · 2013-2026</div>')
    tr = [("Or", "+16,4 %/an", "pire baisse −30 %", "S&P 500 : +12,8 %/an, −34 % · mines détenues : +5,1 %, −73 %", "ok"),
          ("Semi-conducteurs · A", "+26,1 %/an", "pire baisse −43 %", "détention : +26,7 %, −46 % · protège dans les krachs longs (2000-02, 2008)", "info"),
          ("Nasdaq 100 · A", "+18,0 %/an", "pire baisse −39 %", "détention : +18,5 %, −36 % · 1990-2026 : +15,9 %/an", "info"),
          ("Méthode", "16 lois", "751 mini-corrections", "Protocole écrit avant chaque calcul · validation hors échantillon · 6 marchés, 1990-2026", "mute")]
    for col, (a, b_, c_, d_, niv) in zip(st.columns(4), tr):
        with col: md(carte(f'<div class="lab">{a}</div><div class="big num" style="color:{COUL[niv] if niv != "mute" else "#f8fafc"}">{b_}</div><div class="txt" style="font-weight:600">{c_}</div><div class="small" style="margin-top:6px">{d_}</div>'))

# ================================================================ MARCHÉS
LAYOUT = dict(hovermode="x unified", paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="#0e1626", font=dict(color="#94a3b8", family="Inter"),
              legend=dict(orientation="h", y=1.05, x=0, bgcolor="rgba(0,0,0,0)"), hoverlabel=dict(bgcolor="#121a2b", bordercolor="#334155", font_color="#e2e8f0"))

def graphique(e, nj):
    s = e["s"].iloc[-nj:]; vix = C["vix_serie"].reindex(s.index).ffill(); q80 = C["q80_serie"].reindex(s.index).ffill()
    fig = make_subplots(rows=2, cols=1, shared_xaxes=True, row_heights=[0.74, 0.26], vertical_spacing=0.035)
    fut = pd.bdate_range(s.index[-1], periods=21); Q = cone(e)          # quantiles 10/25/50/75/90 à 0…20 séances
    for (a, b), al, lab in [((0, 4), 0.16, "Carte des prix 80 %"), ((1, 3), 0.30, "Carte des prix 50 %")]:
        fig.add_trace(go.Scatter(x=list(fut) + list(fut[::-1]), y=list(Q[:, b]) + list(Q[::-1, a]), fill="toself", fillcolor=f"rgba(59,130,246,{al})",
                                 line=dict(width=0), name=lab, hoverinfo="skip"), 1, 1)
    fig.add_trace(go.Scatter(x=fut, y=Q[:, 2], mode="lines", line=dict(color="#93c5fd", width=1.5, dash="dot"), name="Médiane attendue",
                             hovertemplate="médiane %{y:,.0f}<extra></extra>"), 1, 1)
    for hh in (5, 10, 20):
        fig.add_trace(go.Scatter(x=[fut[hh], fut[hh]], y=[Q[hh, 0], Q[hh, 4]], mode="lines+markers", line=dict(color="#93c5fd", width=1, dash="dot"), marker=dict(size=5, color="#93c5fd"),
                                 showlegend=False, hovertemplate=f"Dans {hh} séances : 80 % de chances entre {nb(Q[hh, 0])} et {nb(Q[hh, 4])} (médiane {nb(Q[hh, 2])})<extra></extra>"), 1, 1)
    for k in (0, 2, 4):
        fig.add_annotation(x=fut[-1], y=Q[-1, k], text=f"<b>{nb(Q[-1, k], 0)}</b>", showarrow=False, xanchor="left", font=dict(color="#93c5fd", size=12 if k != 2 else 11), row=1, col=1)
    fig.add_trace(go.Scatter(x=s.index, y=s.values, name="Cours", line=dict(color="#e2e8f0", width=2), hovertemplate="%{y:,.2f}<extra>Cours</extra>"), 1, 1)
    for nom_sig, col, sym, lab in [("S5", COUL["ok"], "triangle-up", "Creux S5"), ("P4", COUL["warn"], "triangle-down", "Pic P4"), ("S7", "#60a5fa", "star", "Creux de cycle S7")]:
        sg = e["series"][nom_sig].reindex(s.index).fillna(False).astype(bool); sg = sg & ~sg.shift(1, fill_value=False)
        if sg.any(): fig.add_trace(go.Scatter(x=s.index[sg], y=s[sg] * (0.985 if nom_sig != "P4" else 1.015), mode="markers", name=lab,
                                              marker=dict(color=col, size=12, symbol=sym, line=dict(color="#0a0f1c", width=1.5)), hovertemplate=f"{lab}<extra></extra>"), 1, 1)
    m = e["mini"]
    niv = [("Sortie du cycle (A)", e["A"]["niveau_sortie"], COUL["bad"]), ("Couteau S5", e["S5"]["invalidation"] if e["S5"]["valide"] else None, "#fb7185"),
           ("Non-retour", m["niveau_non_retour"], COUL["warn"]), ("Fin de correction", m["niveau_confirmation"], COUL["ok"]),
           ("Bascule en correction", m["niveau_bascule"], COUL["warn"])]
    prev = None
    for lab, y, col in sorted([x for x in niv if x[1] is not None], key=lambda x: x[1]):
        proche = prev is not None and abs(y / prev - 1) < 0.03          # deux niveaux voisins : on décale l'étiquette
        fig.add_shape(type="line", x0=s.index[0], x1=fut[-1], y0=y, y1=y, line=dict(color=col, width=1.4, dash="dash"), row=1, col=1)
        fig.add_annotation(x=s.index[0] if not proche else s.index[len(s) // 3], y=y, text=f"{lab} · {nb(y)}", showarrow=False, xanchor="left",
                           yanchor="bottom" if not proche else "top", font=dict(color=col, size=11.5), row=1, col=1)
        prev = y
    fig.add_trace(go.Scatter(x=q80.index, y=q80.values, name="Seuil de peur (80e)", line=dict(color="#64748b", width=1.5, dash="dot"), hovertemplate="%{y:.1f}<extra>seuil</extra>"), 2, 1)
    fig.add_trace(go.Scatter(x=vix.index, y=np.maximum(vix.values, q80.values), fill="tonexty", fillcolor="rgba(239,68,68,.25)", line=dict(width=0), showlegend=False, hoverinfo="skip"), 2, 1)
    fig.add_trace(go.Scatter(x=vix.index, y=vix.values, name="VIX", line=dict(color="#a78bfa", width=1.8), hovertemplate="%{y:.1f}<extra>VIX</extra>"), 2, 1)
    E8 = [d for d in C["e80_dates"] if d >= s.index[0]]
    if E8: fig.add_trace(go.Scatter(x=E8, y=vix.reindex(E8).values, mode="markers", name="VIX entre dans la peur", marker=dict(color="#f472b6", size=9, symbol="diamond")), 2, 1)
    fig.update_layout(height=640, margin=dict(l=8, r=60, t=10, b=8), **LAYOUT)
    fig.update_xaxes(showgrid=False, linecolor="#1e293b"); fig.update_yaxes(gridcolor="#1a2438", zeroline=False); fig.update_yaxes(title_text="VIX", row=2, col=1)
    return fig

def carte_loi(l):
    j = l["jauge"]; b = ""
    if j is not None and j[1]:
        bd = (j[3][0] / j[1], j[3][1] / j[1]) if len(j) > 3 and j[3] is not None else None
        b = bar(j[0] / j[1], l["niveau"], (j[2] / j[1]) if j[2] is not None else None, bd)
    c = COUL[l["niveau"]]
    return carte(f'<div class="row"><span class="lab">{l["titre"]}</span><span style="color:{c};font-size:15px">{SYMB[l["niveau"]]}</span></div>'
                 f'<div class="mid num" style="margin-top:4px;color:{c}">{l["valeur"]}</div>{b}'
                 f'<div class="txt" style="margin-top:10px">{l["conclusion"]}</div><div class="small" style="margin-top:8px">{l["source"]}</div>', "card law", f"border-left-color:{c}")

def vue_marche(n):
    e = E[n]; vtxt, vniv, raison = V[n]; m = e["mini"]; s = e["s"]; ch1 = s.iloc[-1] / s.iloc[-2] - 1
    lw = next((l for l in LO[n] if l["niveau"] == vniv), LO[n][0])
    c1, c2 = st.columns([1.15, 2])
    dl = delta(f"{d2} : {V2[n][0].lower()} · cours {nb(E2[n]['prix'])} ({pc(e['prix'] / E2[n]['prix'] - 1)})") if R2 and n in E2 else ""
    with c1: md(carte(f'<div class="lab">{n} · seuils cycle {pc(e["seuil_cycle"], 1, False)} · mini {pc(e["seuil_mini"], 1, False)}</div>'
                      f'<div class="title" style="font-size:26px">{COURT[n]}</div><div class="row" style="margin-top:8px"><span class="big num">{nb(e["prix"])}</span>{chip(pc(ch1), "ok" if ch1 >= 0 else "bad")}</div>{dl}'))
    with c2: md(carte(f'<div class="row"><div>{badge(vtxt, vniv, True)}</div><div class="small">verdict = la loi la plus sévère du jour</div></div>'
                      f'<div class="mid" style="margin-top:10px">{raison}</div><div class="txt" style="margin-top:4px">{lw["conclusion"]}</div>'))
    st.write("")
    A = e["A"]; dA = A["niveau_sortie"] / e["prix"] - 1 if A["investie"] else None; an = e["analogue"]
    if m["phase"] == "correction": mv, mn_, md_ = f"CORRECTION {pc(-m['ampleur'])}", "warn", f"séance {m['seances']} · au pire {pc(-m['ampleur_max'])} ({nb(m['x_seuil_max'])} seuil)"
    else: mv, mn_, md_ = f"HAUSSE {pc(m['ampleur'])}", ("warn" if m["retombee"] / e["seuil_mini"] >= 0.5 else "ok"), f"{m['seances']} séances · {pc(-m['retombee'])} depuis son plus haut"
    lo10, hi10 = e["bande80"][10]
    tiles = [("Cycle", "OUVERT" if A["investie"] else "FERMÉ", "ok" if A["investie"] else "bad", f"J+{e['cycle']['seances']} · sortie à {nb(A['niveau_sortie'])} ({pc(dA)})" if A["investie"] else f"dernier S7 {jour(e['dernier_S7'])}"),
             ("Mini-cycle", mv, mn_, md_),
             ("Signal de creux S5", "ACTIF" if e["S5"]["valide"] else "—", "ok" if e["S5"]["valide"] else "mute", f"couteau sous {nb(e['S5']['invalidation'])}" if e["S5"]["valide"] else f"dernier le {jour(e['S5']['dernier'])}"),
             ("Carte des prix · 10 séances", f"{nb(lo10, 0)} – {nb(hi10, 0)}", "info", f"80 % · bas {pc(lo10 / e['prix'] - 1, 0)} / haut {pc(hi10 / e['prix'] - 1, 0)}")]
    for col, (lab, v_, niv, det) in zip(st.columns(4), tiles):
        with col: md(carte(f'<div class="lab">{lab}</div><div class="mid num" style="color:{COUL[niv]};margin-top:4px">{v_}</div><div class="small" style="margin-top:4px">{det}</div>', "card tight"))
    per = st.segmented_control("Période", ["3 mois", "6 mois", "1 an", "3 ans", "10 ans"], default="1 an", label_visibility="collapsed", key="per_" + n) or "1 an"
    st.plotly_chart(graphique(e, {"3 mois": 63, "6 mois": 126, "1 an": 252, "3 ans": 756, "10 ans": 2520}[per]), width="stretch", config=dict(displayModeBar=False))
    q20 = cone(e, [20])[0]
    md(f'<div class="small">Carte des prix : ce qu’ont fait les {an["n"]} situations les plus proches (6 marchés, {mem_txt} ; même {an["critere"]}), ramenées à la volatilité du jour. '
       f'Médiane à 20 séances {pc(q20[2] / e["prix"] - 1)} ; 80 % entre {pc(q20[0] / e["prix"] - 1)} et {pc(q20[4] / e["prix"] - 1)}. Un cône qui penche vers le bas = les cas comparables ont plus souvent prolongé la baisse.</div>')
    md('<div class="sec">Lecture par nos lois</div>')
    lois = LO[n]
    for i in range(0, len(lois), 3):
        for col, l in zip(st.columns(3), lois[i:i + 3]):
            with col: md(carte_loi(l))
        st.write("")
    if n in THEMES: bloc_titres(n)

def bloc_titres(n):
    md(f'<div class="sec">Titres de la thématique · {THEMES[n]}</div>')
    t = TI.get(n)
    if not t or not t.get("dispo"):
        st.info("Sélection des titres indisponible : " + (t["raison"] if t else TI.get("erreur", "cours des titres non chargés"))); return
    c1, c2 = st.columns([1, 2.6])
    with c1: md(carte(f'<div class="lab">Position en titres</div><div style="margin:10px 0">{badge(t["etat"], t["niveau"], True)}</div>'
                      f'<div class="txt">{t["texte"]}</div><div class="small" style="margin-top:10px">Cœur : <b style="color:#e2e8f0">{" · ".join(t["coeur"])}</b></div>'
                      f'<div class="small">Liste figée au S5 du {jour(t["date_liste"])}</div>'))
    tete = "".join(f'<th style="white-space:nowrap;text-align:{a};padding:6px 10px;color:#94a3b8;font-size:11px;letter-spacing:.1em;text-transform:uppercase;font-weight:600">{h}</th>'
                   for h, a in [("Titre", "left"), ("Rôle", "left"), ("Bêta", "right"), ("Cours", "right"), ("Depuis S5", "right"), ("20 s.", "right"), ("vs haut 1 an", "right"), ("MM50", "center")])
    def cel(x, a="right", c="#e2e8f0"): return f'<td class="num" style="white-space:nowrap;text-align:{a};padding:7px 10px;color:{c};border-top:1px solid #1e293b">{x}</td>'
    def cpc(x): return COUL["ok"] if x >= 0 else COUL["bad"]
    rows = ""
    for l in t["lignes"]:
        role = chip("CŒUR", "ok") if l["coeur"] else chip("LISTE", "mute")
        rows += ("<tr>" + f'<td style="padding:7px 10px;border-top:1px solid #1e293b;font-weight:700;color:#f8fafc">{l["titre"]}</td>' + f'<td style="padding:7px 10px;border-top:1px solid #1e293b">{role}</td>'
                 + cel(nb(l["beta"], 2)) + cel(nb(l["cours"])) + cel(pc(l["depuis"]), c=cpc(l["depuis"])) + cel(pc(l["r20"]), c=cpc(l["r20"])) + cel(pc(l["recul"]))
                 + cel("▲ dessus" if l["ma50"] else "▼ dessous", "center", COUL["ok"] if l["ma50"] else COUL["bad"]) + "</tr>")
    with c2: md(carte(f'<table style="width:100%;border-collapse:collapse;font-size:13.5px"><tr>{tete}</tr>{rows}</table>'
                      f'<div class="small" style="margin-top:10px">Parmi les 15 plus gros {"volumes" if n == "NDX" else "poids"} ({t["source"]}), les 5 qui ont le plus amplifié les mini-corrections de l’indice sur 2 ans (bêta en correction). '
                      f'Cœur = les 2 premiers{" (hors titres déjà au cœur des semis)" if n == "NDX" else ""}. Gain du cœur : il tient à quelques grands rebonds, la médiane par trade vaut l’indice (coeur_controles).</div>'))

def vue_or():
    if O is None: st.warning("Données des mines indisponibles."); return
    nd, na = sum(O["decor"].values()), sum(O["amorce"].values()); b = O["budget"]
    etat = ("INVESTIE", "ok") if O["investie"] else (("DÉCOR PRÊT", "warn") if nd == 3 else ("EN ATTENTE", "mute"))
    c1, c2, c3 = st.columns([1.4, 1, 1])
    manque = f"Il manque {3 - nd} condition{'s' if 3 - nd > 1 else ''} de décor et {3 - na} d’amorce. On ne force pas : la règle a fait 4 entrées depuis 2013."
    with c1: md(carte(f'<div class="lab">Stratégie or · 5 plus grosses mines de GDX, parts égales</div><div style="margin:10px 0">{badge(etat[0], etat[1], True)}</div>'
                      f'<div class="txt">{"En position. Les trois sorties ci-dessous sont actives." if O["investie"] else ("Le décor est complet : l’entrée viendra avec l’amorce." if nd == 3 else manque)}</div>'
                      f'<div class="row" style="margin-top:12px"><span class="small">Or <b class="num" style="color:#e2e8f0">{nb(O["or_prix"], 1)}</b></span><span class="small">GDX <b class="num" style="color:#e2e8f0">{nb(O["gdx"])}</b></span><span class="small">GVZ <b class="num" style="color:#e2e8f0">{nb(O["gvz"], 1)}</b></span></div>'
                      + (delta(f"{d2} : décor {sum(O2['decor'].values())}/3, amorce {sum(O2['amorce'].values())}/3, budget {O2['budget']['part']:.0%}") if R2 and O2 else "")))
    with c2: md(carte(f'<div class="lab">Conditions remplies</div><div class="row" style="margin-top:6px"><div><div class="num" style="font-size:44px;font-weight:800;color:{COUL["ok"] if nd == 3 else "#f8fafc"}">{nd}<span style="font-size:20px;color:#64748b">/3</span></div><div class="small">décor</div></div>'
                      f'<div><div class="num" style="font-size:44px;font-weight:800;color:{COUL["ok"] if na == 3 else "#f8fafc"}">{na}<span style="font-size:20px;color:#64748b">/3</span></div><div class="small">amorce</div></div></div>', "card counter"))
    bt = (f"GDX en correction {pc(b['profondeur'])}, séance {b['seances']} / ≈ {b['duree']:.0f}. 90 % de mines seulement après −17 % et la durée dépassée." if b["phase"] == "correction"
          else f"GDX en hausse, {b['seances']} séances / ≈ {b['duree']:.0f}, écart à l'or {pc(b['ecart'])}. 50 % de mines en surchauffe (écart ≥ +20 % et durée dépassée).")
    with c3: md(carte(f'<div class="lab">Budget de risque · part de mines</div><div class="row"><span class="big num" style="font-size:40px">{b["part"]:.0%}</span>{jauge(b["part"], 1, "info", 0.7, 110)}</div><div class="txt">{bt}</div>'))
    md('<div class="sec">Les six conditions d’entrée</div>')
    def cond(lab, ok_, val, frac, rep, aide):
        c = COUL["ok"] if ok_ else "#475569"
        return carte(f'<div class="row"><span class="lab">{lab}</span><span style="color:{c};font-size:20px">{"✔" if ok_ else "○"}</span></div>'
                     f'<div class="mid num" style="margin-top:4px;color:{COUL["ok"] if ok_ else "#e2e8f0"}">{val}</div>{bar(frac, "ok" if ok_ else "mute", rep)}<div class="small" style="margin-top:8px">{aide}</div>', "card law", f"border-left-color:{c}")
    vr = O["var20"]
    r1 = [("Dollar fort", O["decor"]["dollar"], f"rang {nb(O['dollar_rang'], 0)}/100", O["dollar_rang"] / 100, 0.9, "rang ≥ 90 sur 1 an, dans les 60 dernières séances"),
          ("Taux réel haut", O["decor"]["taux"], f"rang {nb(O['taux_reel_rang'], 0)}/100", O["taux_reel_rang"] / 100, 0.9, "rang ≥ 90 sur 1 an, dans les 60 dernières séances"),
          ("Spéculateurs vendus", O["decor"]["spec"], f"rang {nb(O['spec_rang'], 0)}/100", 1 - O["spec_rang"] / 100, 0.9, "rang ≤ 10 sur 3 ans (CFTC) : barre pleine = spéculateurs au plus bas")]
    r2 = [("Taux réel qui baisse", O["amorce"]["taux"], f"{'+' if vr['taux'] >= 0 else ''}{nb(vr['taux'])} pt", 0.5 + np.clip(-vr["taux"], -0.5, 0.5), 0.5, "variation sur 20 séances < 0 (barre à droite du repère)"),
          ("Volatilité de l'or qui baisse", O["amorce"]["vol"], f"{'+' if vr['vol'] >= 0 else ''}{nb(vr['vol'], 1)} pt", 0.5 + np.clip(-vr["vol"] / 10, -0.5, 0.5), 0.5, "GVZ sur 20 séances < 0"),
          ("Mines meilleures que le S&P", O["amorce"]["gdx_sp"], pc(np.expm1(vr["gdx_sp"])), 0.5 + np.clip(vr["gdx_sp"] * 2.5, -0.5, 0.5), 0.5, "écart GDX − S&P sur 20 séances > 0")]
    for row in (r1, r2):
        for col, x in zip(st.columns(3), row):
            with col: md(cond(*x))
        st.write("")
    md('<div class="sec">GDX, signaux d’entrée et volatilité de l’or</div>')
    per = st.segmented_control("Période or", ["1 an", "3 ans", "10 ans", "Tout"], default="3 ans", label_visibility="collapsed") or "3 ans"
    nj = {"1 an": 252, "3 ans": 756, "10 ans": 2520, "Tout": 10 ** 6}[per]
    g = O["mines"].iloc[-nj:]; pos = O["position"].reindex(g.index); vo = O["vol_or"].reindex(g.index)
    fig = make_subplots(rows=2, cols=1, shared_xaxes=True, row_heights=[0.72, 0.28], vertical_spacing=0.04); inn = pos.values > 0
    if inn.any(): fig.add_trace(go.Scatter(x=g.index, y=np.where(inn, g.values, np.nan), fill="tozeroy", fillcolor="rgba(34,197,94,.10)", line=dict(width=0), name="Stratégie investie", hoverinfo="skip"), 1, 1)
    fig.add_trace(go.Scatter(x=g.index, y=g.values, name="GDX", line=dict(color="#fbbf24", width=2), hovertemplate="%{y:,.2f}<extra>GDX</extra>"), 1, 1)
    sg = [d for d in O["signaux"] if d >= g.index[0]]
    if sg: fig.add_trace(go.Scatter(x=sg, y=g.reindex(sg).values * 0.97, mode="markers", name="Signal d'entrée", marker=dict(color=COUL["ok"], size=14, symbol="triangle-up", line=dict(color="#0a0f1c", width=1.5))), 1, 1)
    fig.add_trace(go.Scatter(x=vo.index, y=vo.values, name="Volatilité de l'or (GVZ)", line=dict(color="#a78bfa", width=1.6)), 2, 1)
    fig.update_layout(height=520, margin=dict(l=8, r=8, t=10, b=8), **LAYOUT)
    fig.update_xaxes(showgrid=False); fig.update_yaxes(gridcolor="#1a2438", zeroline=False); fig.update_yaxes(range=[g.min() * 0.9, g.max() * 1.05], row=1, col=1)
    st.plotly_chart(fig, width="stretch", config=dict(displayModeBar=False))
    md('<div class="sec">Sorties (actives une fois investi)</div>')
    OT = or_titres(O, D.get("titres"), asof)
    if OT:
        md('<div class="sec">Titres · les 5 plus grosses mines de GDX</div>')
        c1, c2 = st.columns([1, 2.6])
        with c1: md(carte(f'<div class="lab">Position en titres</div><div style="margin:10px 0">{badge(OT["etat"], OT["niveau"], True)}</div><div class="txt">{OT["texte"]}</div>'
                          f'<div class="small" style="margin-top:10px">Composition GDX au {OT["date_compo"]} (déclaration SEC). Sans ETF ni contrat à terme : 100 % mines.</div>'))
        th = "".join(f'<th style="white-space:nowrap;text-align:{a};padding:6px 10px;color:#94a3b8;font-size:11px;letter-spacing:.1em;text-transform:uppercase;font-weight:600">{h}</th>'
                     for h, a in [("Titre", "left"), ("Poids GDX", "right"), ("Cours", "right"), ("20 s.", "right"), ("vs haut 1 an", "right"), ("MM50", "center")])
        def ce(x, a="right", c="#e2e8f0"): return f'<td class="num" style="white-space:nowrap;text-align:{a};padding:7px 10px;color:{c};border-top:1px solid #1e293b">{x}</td>'
        rw = "".join("<tr>" + f'<td style="padding:7px 10px;border-top:1px solid #1e293b;font-weight:700;color:#f8fafc">{l["titre"]}</td>' + ce(nb(l["poids"], 1) + " %") + ce(nb(l["cours"]))
                     + ce(pc(l["r20"]), c=COUL["ok"] if l["r20"] >= 0 else COUL["bad"]) + ce(pc(l["recul"])) + ce("▲ dessus" if l["ma50"] else "▼ dessous", "center", COUL["ok"] if l["ma50"] else COUL["bad"]) + "</tr>" for l in OT["lignes"])
        with c2: md(carte(f'<table style="width:100%;border-collapse:collapse;font-size:13.5px"><tr>{th}</tr>{rw}</table><div class="small" style="margin-top:10px">Choix du test or_sans_etf : les 5 plus gros poids battent le cœur de 2 au bêta le plus élevé (rapport 0,55 contre 0,46 sur 2013-2026) et la version ETF 70/30 (0,51). Cours en devise locale (.TO Toronto, .AX Sydney, .L Londres).</div>'))
    nv = O["niveaux"] or {}
    sx = [("Stop de départ", "GDX −10 %", nb(nv.get("stop_depart")) if nv.get("stop_depart") else "—", "tant que GDX n'a pas fait +10 % depuis l'entrée"),
          ("Recul de l'or", "or −13 %", nb(nv.get("or_moins13"), 1) if nv else "—", "depuis son plus haut depuis l'entrée"),
          ("Règle de cycle", "or −15 % + macro", nb(nv.get("or_moins15"), 1) if nv else "—", f"et taux réel ou dollar en hausse sur 63 séances (aujourd'hui : {'oui' if O['macro'] else 'non'})")]
    for col, (a, b_, c_, d_) in zip(st.columns(3), sx):
        with col: md(carte(f'<div class="lab">{a}</div><div class="mid" style="margin-top:4px">{b_}</div><div class="small">niveau : <b class="num" style="color:#e2e8f0">{c_}</b></div><div class="small" style="margin-top:6px">{d_}</div>', "card tight"))

with t2:
    choix = list(E) + ["Or"]
    n = st.segmented_control("Marché", choix, default="NDX" if "NDX" in E else choix[0], format_func=lambda x: COURT[x], label_visibility="collapsed") or "NDX"
    if n == "Or": vue_or()
    else: vue_marche(n)

# ================================================================ INTERROGER L'HISTORIQUE
with t3:
    md('<div class="txt" style="margin-bottom:10px">Choisis un marché, un signal et une période : tu vois ce qui s’est passé ensuite, chaque fois que le signal est apparu.</div>')
    c1, c2, c3 = st.columns([2, 2, 2])
    mk = c1.multiselect("Marchés", list(E), default=["NDX"] if "NDX" in E else None, format_func=lambda x: COURT[x])
    sg = c2.multiselect("Signaux", sorted(H["signal"].unique()), default=["S5 mini"])
    an_ = c3.slider("Années", 1990, asof.year, (max(1990, asof.year - 4), asof.year))
    c4, c5 = st.columns(2)
    vixmin = c4.slider("VIX minimum le jour du signal", 0, 60, 0)
    retard = c5.toggle("Seulement avec un retard ≥ 3,3 pts sur le S&P (20 séances)")
    q = H[H["marché"].isin(mk or list(E)) & H["signal"].isin(sg or H["signal"].unique()) & H.date.dt.year.between(*an_)].copy()
    if vixmin: q = q[C["vix_serie"].reindex(q.date).values >= vixmin]
    if retard:
        rel = []
        for _, r in q.iterrows():
            s_ = E[r["marché"]]["s"]; spx = E[SP]["s"]; t = s_.index.get_loc(r.date)
            rel.append(np.nan if t < 20 else (s_.iloc[t] / s_.iloc[t - 20] - 1) - (spx.asof(r.date) / spx.asof(s_.index[t - 20]) - 1))
        q = q[np.array(rel) <= SEUIL["retard"]]
    if len(q):
        r20 = q["20 s."].dropna()
        kp = [("Occurrences", str(len(q)), "info"), ("Gain moyen à 20 séances", pc(r20.mean()), "ok" if r20.mean() > 0 else "bad"),
              ("Positifs à 20 séances", pc((r20 > 0).mean(), 0, False), "ok" if (r20 > 0).mean() > 0.5 else "warn"), ("Pire recul moyen (20 s.)", pc(q["pire 20 s."].mean()), "bad")]
        for col, (a, b_, niv) in zip(st.columns(4), kp):
            with col: md(carte(f'<div class="lab">{a}</div><div class="big num" style="color:{COUL[niv]}">{b_}</div>', "card tight counter"))
        g = q.groupby(["marché", "signal"])[["5 s.", "20 s.", "40 s."]].mean().reset_index()
        fig = go.Figure()
        for hz, col in [("5 s.", "#93c5fd"), ("20 s.", "#3b82f6"), ("40 s.", "#1d4ed8")]:
            fig.add_trace(go.Bar(x=[f"{COURT[a]} · {b_}" for a, b_ in zip(g["marché"], g["signal"])], y=g[hz] * 100, name=f"à {hz}", marker_color=col,
                                 text=[pc(x) for x in g[hz]], textposition="outside", hovertemplate="%{y:.1f} %<extra></extra>"))
        fig.update_layout(barmode="group", height=360, margin=dict(l=8, r=8, t=30, b=8), paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="#0e1626",
                          font=dict(color="#94a3b8", family="Inter"), legend=dict(orientation="h", y=1.12), yaxis=dict(title="gain moyen (%)", gridcolor="#1a2438", zerolinecolor="#334155"))
        st.plotly_chart(fig, width="stretch", config=dict(displayModeBar=False))
        with st.expander(f"Voir les {len(q)} occurrences"):
            aff = q.copy(); aff["marché"] = aff["marché"].map(COURT); aff["date"] = aff.date.map(jour); aff["prix"] = aff.prix.map(nb)
            for col in ["5 s.", "20 s.", "40 s.", "pire 20 s."]: aff[col] = aff[col].map(pc)
            st.dataframe(aff, hide_index=True, width="stretch", height=380)
            st.download_button("Télécharger (CSV)", q.to_csv(index=False).encode("utf-8"), "signaux.csv", "text/csv")
    else: st.info("Aucun signal pour ces filtres.")
    md('<div class="small" style="margin-top:12px">Un filtre ajouté ici est une piste, pas une loi : il devient une règle après son protocole et sa validation hors échantillon.</div>')
