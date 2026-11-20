"""Titres de chaque thématique (univers_coeur, coeur_controles, minicycles_titres — 17/11/2026).
Règle : parmi les 15 plus gros poids de l'ETF (NDX : les 15 plus gros volumes en dollars sur 60 séances), les 5 au bêta
en correction le plus élevé ; cœur = les 2 premiers. Liste figée à chaque signal S5 du secteur.
Position (système retenu, en titres) : trade S5 en cours → le cœur ; cycle ouvert sans trade → la liste des 5 ;
cycle fermé ou interrupteur coût du capital actif → cash."""
import os
import numpy as np, pandas as pd
from .calcul import zz
from .regles import SEUIL

ICI = os.path.dirname(__file__)
THEMES = {"SOX": "SOXX", "Logiciel": "IGV", "NDX": "NDX"}

def compositions():
    c = pd.read_csv(os.path.join(ICI, "compositions_actuelles.csv"))
    n = pd.read_csv(os.path.join(ICI, "ndx_membres.csv")); n = n[n.date == n.date.max()]
    return c, sorted(set(n.ticker)), str(c.date.max()), str(n.date.max())

def yahoo(t): return str(t).replace(".", "-")

def beta_corr(px, S, mth, d):
    """Médiane, sur les mini-corrections de l'indice des 2 années avant d, de baisse du titre / baisse de l'indice."""
    SS = S.loc[:d].dropna(); piv = zz(SS, mth)[0]; P_ = [(SS.index[i], ty) for i, ty in piv[1:]]; r = []
    for (a, ta), (b, _) in zip(P_[:-1], P_[1:]):
        if ta == "H" and a >= d - pd.DateOffset(years=2):
            pa, pb = px.asof(a), px.asof(b)
            if pd.notna(pa) and pd.notna(pb): r.append((pb / pa - 1) / (SS[b] / SS[a] - 1))
    return float(np.median(r)) if r else np.nan

def selection(theme, S, mth, d, T, comp, ndx):
    """Liste des 5 (triée par bêta) et bêtas, à la date d."""
    cl, vo = T["close"], T["volume"]
    if theme == "NDX":
        dv = (cl * vo).loc[:d].iloc[-60:].mean()
        cand = [(t, dv.get(yahoo(t), np.nan)) for t in ndx]
    else:
        c = comp[comp.etf == THEMES[theme]]; cand = list(zip(c.ticker, c.poids))
    cand = [(t, w) for t, w in cand if yahoo(t) in cl and pd.notna(w) and cl[yahoo(t)].loc[:d].notna().sum() > 260]
    top = [t for t, _ in sorted(cand, key=lambda x: -x[1])[:15]]; poids = dict(cand)
    b = {t: beta_corr(cl[yahoo(t)], S, mth, d) for t in top}
    L5 = sorted([t for t in top if not np.isnan(b[t])], key=lambda t: -b[t])[:5]
    return L5, b, poids

def titres(E, C, T, asof):
    """Par thématique : état de la position, date de la liste, liste des 5, cœur, mesures par titre."""
    if T is None or T["close"].empty: return {}
    comp, ndx, d_comp, d_ndx = compositions(); out = {}; cl = T["close"].loc[:asof]
    arme = C["taux10_6m"] >= SEUIL["taux10_6m"] or (C["fed_12m"] == C["fed_12m"] and C["fed_12m"] >= 1.0)
    for theme in ["SOX", "Logiciel", "NDX"]:          # SOX avant NDX : le cœur NDX évite les titres du cœur SOX
        if theme not in E: continue
        e = E[theme]; S = e["s"]; mth = e["seuil_mini"]
        tr = e["S5"]["trades"]; en_cours = bool(tr) and tr[-1]["motif"] == "en cours"
        d = pd.Timestamp(tr[-1]["entree"]) if tr else pd.Timestamp(asof)
        if d - cl.index[0] < pd.Timedelta(days=3 * 365):
            out[theme] = dict(dispo=False, raison="historique des titres insuffisant pour cette date"); continue
        L5, b, poids = selection(theme, S, mth, d, dict(close=cl, volume=T["volume"].loc[:asof]), comp, ndx)
        coeur = L5[:2]
        if theme == "NDX" and "SOX" in out and out["SOX"].get("dispo") and out["SOX"]["en_cours"]:
            pris = set(out["SOX"]["coeur"]); coeur = [t for t in L5 if t not in pris][:2] or coeur
        abri = arme and not e["ma50"]
        if abri: etat, niv, txt = "À L'ABRI", "bad", "Interrupteur coût du capital actif : cash."
        elif en_cours: etat, niv, txt = "CŒUR", "ok", f"Mini-cycle en cours depuis le {d:%d/%m/%Y} : détenir le cœur."
        elif e["A"]["investie"]: etat, niv, txt = "LISTE DES 5", "info", "Cycle ouvert, pas de mini-cycle en cours : détenir la liste des 5 (figée au dernier S5)."
        else: etat, niv, txt = "CASH", "mute", "Cycle fermé : cash. La liste sera refaite au prochain S5."
        lignes = []
        for t in L5:
            s = cl[yahoo(t)].dropna(); p = s.iloc[-1]
            lignes.append(dict(titre=t, coeur=t in coeur, beta=b[t], poids=poids.get(t), cours=p, depuis=p / s.asof(d) - 1,
                               recul=p / s.iloc[-252:].max() - 1, ma50=bool(p > s.iloc[-50:].mean()), r20=p / s.iloc[-21] - 1))
        out[theme] = dict(dispo=True, etat=etat, niveau=niv, texte=txt, date_liste=d, en_cours=en_cours, coeur=coeur, liste=L5, lignes=lignes,
                          source=f"compositions {THEMES[theme]} du {d_comp}" if theme != "NDX" else f"membres du NDX au {d_ndx}, classés par volume en dollars")
    return out

def peremptions(aujourdhui=None):
    """Liste (libellé, échéance, jours restants) : réglages et fichiers de l'univers."""
    from .regles import PEREMPTION_REGLAGES, PEREMPTION_FICHIERS, PEREMPTION_GDX
    j = pd.Timestamp(aujourdhui or pd.Timestamp.today()).normalize(); out = []
    for lab, d in PEREMPTION_REGLAGES: out.append((lab, pd.Timestamp(d), (pd.Timestamp(d) - j).days))
    for f, (lab, vie) in PEREMPTION_FICHIERS.items():
        try:
            df = pd.read_csv(os.path.join(ICI, f))
            groupes = df.groupby("etf").date.max().items() if "etf" in df else [(lab, df.date.max())]
            for etf, d0 in groupes:
                d0 = pd.Timestamp(d0); v = PEREMPTION_GDX if etf == "GDX" else vie; e = d0 + pd.Timedelta(days=v)
                out.append((f"{'Poids ' + etf if 'etf' in df else lab} (au {d0:%d/%m/%Y})", e, (e - j).days))
        except Exception: out.append((lab + " (fichier illisible)", j, -1))
    return sorted(out, key=lambda x: x[1])

def or_titres(O, T, asof):
    """Or sans ETF (or_sans_etf, 17/11/2026) : les 5 plus gros poids de GDX, parts égales, détenus quand la stratégie or est investie."""
    if T is None or T["close"].empty or O is None: return None
    comp = compositions()[0]; g = comp[comp.etf == "GDX"].sort_values("poids", ascending=False); cl = T["close"].loc[:asof]
    L5 = [t for t in g.ticker if yahoo(t) in cl and cl[yahoo(t)].dropna().size > 260][:5]
    if not L5: return None
    lignes = []
    for t in L5:
        s_ = cl[yahoo(t)].dropna(); p = s_.iloc[-1]
        lignes.append(dict(titre=t, poids=float(g[g.ticker == t].poids.iloc[0]), cours=p, r20=p / s_.iloc[-21] - 1, recul=p / s_.iloc[-252:].max() - 1, ma50=bool(p > s_.iloc[-50:].mean())))
    inv = bool(O["investie"])
    return dict(etat="LISTE DES 5 MINES" if inv else "CASH", niveau="ok" if inv else "mute", liste=L5, lignes=lignes, date_compo=str(g.date.iloc[0]),
                texte="Stratégie or investie : détenir les 5 mines à parts égales." if inv else "Stratégie or en attente : cash. On achète les 5 mines au signal d'entrée.")
