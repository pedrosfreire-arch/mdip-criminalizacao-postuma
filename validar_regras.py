#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Valida as regras de título contra a sua leitura humana.

1. Abra auditoria/amostra_validacao_titulos.csv (Excel ou LibreOffice) e preencha,
   para cada título, sem olhar o arquivo de regras:
     relevancia_humana : caso MDIP | tematico | policial vítima | fora do escopo
     agencia_humana    : agente como sujeito | passiva com agente | agência transferida
                         | sem agente | indeterminada   (só nos que você marcou "caso MDIP")
     suspeito_humano   : sim | não                     (só nos "caso MDIP")
2. Salve e rode:  py -3.12 validar_regras.py
Saída: precisão, sensibilidade e F1 por categoria, e concordância (kappa de Cohen)
entre a regra e a sua leitura. Se precisar, depois peça a uma segunda pessoa para
codificar 50 títulos às cegas e calcule o alfa de Krippendorff entre vocês.
"""
import pandas as pd

print("validar_regras.py — versão 2 (com estimativas corrigidas)\n")
h = pd.read_csv("auditoria/amostra_validacao_titulos.csv", sep=None, engine="python", encoding="utf-8-sig")
r = pd.read_csv("auditoria/amostra_validacao_regras.csv", encoding="utf-8-sig")
d = h.merge(r, on="url", how="left")
d = d[d["relevancia_humana"].fillna("").str.strip() != ""]
print(f"Títulos rotulados: {len(d)}\n")

def metricas(y_h, y_r, rotulos):
    for rot in rotulos:
        vp = ((y_h == rot) & (y_r == rot)).sum()
        fp = ((y_h != rot) & (y_r == rot)).sum()
        fn = ((y_h == rot) & (y_r != rot)).sum()
        prec = vp / (vp + fp) if vp + fp else float("nan")
        sens = vp / (vp + fn) if vp + fn else float("nan")
        f1 = 2 * prec * sens / (prec + sens) if prec + sens else float("nan")
        print(f"  {str(rot):24s} precisão {prec:.3f}  sensibilidade {sens:.3f}  F1 {f1:.3f}  (n humano = {(y_h == rot).sum()})")
    po = (y_h == y_r).mean()
    pe = sum((y_h == k).mean() * (y_r == k).mean() for k in set(y_h) | set(y_r))
    print(f"  concordância bruta {po:.3f}  kappa de Cohen {(po - pe) / (1 - pe):.3f}\n")

print("RELEVÂNCIA")
metricas(d["relevancia_humana"].str.strip(), d["relevancia"].str.strip(),
         ["caso MDIP", "tematico", "policial vítima", "fora do escopo"])

casos = d[(d["relevancia_humana"].str.strip() == "caso MDIP") & (d["relevancia"] == "caso MDIP")]
casos = casos[casos["agencia_humana"].fillna("").str.strip() != ""]
if len(casos):
    print("AGÊNCIA (títulos que você e a regra marcaram como caso)")
    metricas(casos["agencia_humana"].str.strip(), casos["agencia"].str.strip(),
             ["agente como sujeito", "passiva com agente", "agência transferida", "sem agente", "indeterminada"])
    print("SUSPEITO")
    metricas(casos["suspeito_humano"].str.strip().str.lower().map({"sim": True, "não": False, "nao": False}),
             casos["suspeito_no_titulo"].astype(bool), [True, False])  # True = "suspeito" no título

# ------------------------------------------------------------------
# Estimativas corrigidas para o corpus (estimador de razão estratificado)
# A amostra foi estratificada pela categoria que a regra atribuiu; dentro de
# cada estrato, a proporção de cada categoria humana é aplicada ao tamanho do
# estrato no corpus. IC de 95% por reamostragem dentro dos estratos.
# ------------------------------------------------------------------
import json, os
import numpy as np
if not os.path.exists("auditoria/corpus_anotado_regras.csv"):
    print("ESTIMATIVAS NÃO CALCULADAS: falta auditoria/corpus_anotado_regras.csv. Rode antes o auditoria_corpus.py nesta pasta.")
else:
    corpus = pd.read_csv("auditoria/corpus_anotado_regras.csv")
    anos = pd.to_datetime(corpus["data_publicacao"], errors="coerce", utc=True, format="mixed").dt.year
    N = corpus["relevancia"].value_counts().to_dict()
    N23 = corpus[anos == 2023]["relevancia"].value_counts().to_dict()
    rotulos = ["caso MDIP", "tematico", "policial vítima", "fora do escopo"]
    amostra = d.assign(h=d["relevancia_humana"].str.strip(), r=d["relevancia"].str.strip())
    def estimar(df, Nr):
        return {k: sum(Nr.get(r, 0) * (g["h"] == k).mean() for r, g in df.groupby("r")) for k in rotulos}
    rng = np.random.default_rng(42)
    boots, boots23 = [], []
    for _ in range(5000):
        rs = pd.concat([g.sample(len(g), replace=True, random_state=int(rng.integers(1e9))) for _, g in amostra.groupby("r")])
        boots.append(estimar(rs, N)); boots23.append(estimar(rs, N23))
    est, est23 = estimar(amostra, N), estimar(amostra, N23)
    saida = {}
    print("ESTIMATIVAS CORRIGIDAS PARA O CORPUS (IC 95%)")
    for k in rotulos:
        lo, hi = np.percentile([b[k] for b in boots], [2.5, 97.5])
        saida[k] = [est[k], lo, hi]
        print(f"  {k:18s} {est[k]:7.0f}  [{lo:.0f}, {hi:.0f}]   (regra: {N.get(k, 0)})")
    lo, hi = np.percentile([b["caso MDIP"] for b in boots23], [2.5, 97.5])
    saida["caso MDIP 2023"] = [est23["caso MDIP"], lo, hi]
    print(f"  caso MDIP em 2023  {est23['caso MDIP']:7.0f}  [{lo:.0f}, {hi:.0f}]   (regra: {N23.get('caso MDIP', 0)})")
    json.dump(saida, open("auditoria/estimativas_corrigidas.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)
