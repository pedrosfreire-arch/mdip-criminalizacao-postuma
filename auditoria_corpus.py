#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Auditoria do corpus MDIP (2022-2023) — resultados preliminares para o artigo
============================================================================
Entradas (mesma pasta):
    03_materias_completas.csv   corpus raspado (execução de 04/03/2026)
    01_materias_brutas.csv      listagem de descoberta (execução de 19/03/2026)

Nenhuma etapa usa codificação humana nem modelo de linguagem. Todas as regras
são léxicas e estão escritas abaixo, para auditoria. As regras de título
(relevância, agência, "suspeito") NÃO estão validadas: gerar a amostra de
validação (amostra_validacao_titulos.csv) e rotulá-la à mão antes de publicar.

Uso:  py -3.12 auditoria_corpus.py
Saída: pasta auditoria/ com tabelas CSV, resumo.json e a amostra de validação.
"""
import json, os, re, unicodedata
import numpy as np
import pandas as pd

ENTRADA_COMPLETAS = "03_materias_completas.csv"
ENTRADA_BRUTAS = "01_materias_brutas.csv"
SAIDA = "auditoria"
os.makedirs(SAIDA, exist_ok=True)
RNG = np.random.default_rng(42)

# ---------------------------------------------------------------- grupos
GRANDE_CIRCULACAO = {  # 25 portais de maior audiência (lista-alvo do projeto)
    "G1", "UOL Notícias", "UOL", "Folha de S.Paulo", "O Globo", "Globo", "Estadão",
    "Metrópoles", "R7", "CNN Brasil", "Terra", "Band", "band.com.br", "Poder360",
    "CartaCapital", "Valor Econômico", "Valor", "BBC", "BBC News Brasil", "SBT News",
    "Jovem Pan", "Gazeta do Povo", "Correio Braziliense", "Diario de Pernambuco",
    "Diário de Pernambuco", "Estado de Minas", "O Tempo", "O TEMPO", "A Gazeta",
    "NSC Total", "GZH", "Agência Brasil",
}
ESPECIALIZADOS = {  # 10 veículos de segurança pública e direitos humanos
    "Ponte Jornalismo", "The Intercept Brasil", "Intercept Brasil", "Agência Pública",
    "Alma Preta Jornalismo", "Alma Preta", "Brasil de Fato", "Fogo Cruzado",
    "Mídia NINJA", "Marco Zero Conteúdo", "Marco Zero", "Amazônia Real", "Justificando",
    "Instituto Fogo Cruzado",
}
INSTITUCIONAL = re.compile(
    r"(\.gov|gov\.br|goias\.gov|pol[ií]cia|\bssp\b|mp[a-z]{2}\.mp|\.mp\.br|minist[ée]rio|"
    r"defensoria|portal stf|tribunal|\bstf\b|\bstj\b|\btj[a-z]{2}\b|secretaria|prefeitura|"
    r"governo|c[aâ]mara|senado|assembleia|ag[eê]ncia tocantins|ag[eê]ncia par[aá])",
    re.I)

def sem_acento(s):
    s = unicodedata.normalize("NFKD", str(s))
    return "".join(ch for ch in s if not unicodedata.combining(ch)).lower()

def grupo(v):
    if v in ESPECIALIZADOS: return "Especializado"
    if v in GRANDE_CIRCULACAO: return "Grande circulação"
    if INSTITUCIONAL.search(v): return "Fonte institucional"
    return "Outros"

def veiculo_real(row):
    """Recupera o veículo do sufixo do título quando a URL é um redirecionamento."""
    if row["veiculo"] != "news.google.com":
        return row["veiculo"]
    t = str(row["titulo"])
    return t.rsplit(" - ", 1)[1].strip() if " - " in t else "desconhecido"

def titulo_limpo(t):
    t = str(t)
    return t.rsplit(" - ", 1)[0].strip() if " - " in t else t.strip()

def data_pub(s):
    d = pd.to_datetime(s, errors="coerce", utc=True, format="mixed")
    return d

# ------------------------------------------------ regras de título (léxicas)
# Morte/disparo
MORTE = r"(mort[oa]s?|mortes?|homicidios?|morre[mu]?|morreram|mata[mr]?|matou|mataram|assassinad[oa]s?|assassin|baleado?a?s?|executad[oa]s?|execu[cç]|chacina|massacre|atirou|atiraram|disparos?|tiros?|letal|letalidade|obito)"
# Agente estatal/contexto policial
POLICIA = r"(policia|policial|policiais|\bpms?\b|\bprf\b|\bbope\b|\brota\b|\bgcm\b|guarda municipal|batalhao|\bchoque\b|operacao|intervencao|confronto|troca de tiros|abordagem|viatura|agentes? de seguranca|forcas? de seguranca|forcas armadas|exercito|militares)"
# Policial como vítima (sai do escopo de MDIP)
POLICIAL_VITIMA = (
    r"(\b(pm|policial|policiais|sargento|cabo|soldado|tenente|delegad[oa]|investigador|"
    r"agente|guarda)\b[^,.;:]{0,30}\b(e|sao|foi|foram)?\s*(mort[oa]s?|baleado?a?s?|"
    r"assassinad[oa]s?|executad[oa]s?)\b|morte d[eoa]s? (pm|policial|policiais|sargento|"
    r"cabo|soldado|agente)|(matam|mata|matou|mataram|assassinam|executam)\s+(pm|policial|"
    r"policiais|sargento|cabo|soldado))")
# Tratamento agregado/temático (letalidade como problema, dados, política)
TEMATICO = r"(letalidade|violencia policial|mortes? (pela|por) policia|mortes em (acoes|intervencoes|operacoes)|cameras? corporais|anuario|dados mostram|levantamento|relatorio|pesquisa)"

# Agência no título (entre as matérias de MDIP)
AGENTE_SUJEITO = (r"\b(pm|pms|policial|policiais|policia|prf|bope|rota|gcm|agentes?|"
                  r"guarda|sargento|cabo|soldado|delegado)\b[^,.;:]{0,25}\b(mata|matam|matou|"
                  r"mataram|atira|atiram|atirou|atiraram|executa|executam|executou|executaram|"
                  r"baleia|balearam|baleou|fuzila|fuzilaram|assassina|assassinam|assassinou)")
PASSIVA_COM_AGENTE = r"(mort[oa]s?|baleado?a?s?|executad[oa]s?|assassinad[oa]s?)\s+(por|pela|pelo|pelos|pelas)\s+(pm|pms|policia|policial|policiais|prf|agentes?|guarda|bope|rota|gcm)"
SEM_AGENTE = (r"\b(e|sao|foi|foram)\s+(mort[oa]s?|baleado?a?s?|atingid[oa]s?|alvejad[oa]s?)\b|\bmorre[mu]?\b|\bmorreram\b|acaba(m|ram|ou)? morto"
              r"|\bmort[oa]s?\s+(em|durante|apos|numa|na|no)\s+(um\s+|uma\s+)?(suposto\s+)?(confronto|troca de tiros|operacao|acao|intervencao|abordagem|perseguicao)")
# A operação ou o confronto como sujeito gramatical da morte ("operação deixa 5 mortos")
AGENCIA_TRANSFERIDA = r"(operacao|acao policial|acao da (pm|policia)|confronto|intervencao|incursao|tiroteio|troca de tiros)[^,.;:]{0,40}\b(deixa|deixam|deixou|deixaram|resulta|resultou|termina|terminou|mata|matou)\b"
# Etapa judicial/investigativa (regra aproximada, usada só como análise de sensibilidade)
ETAPA_JUDICIAL = r"\b(condenad|absolv|denunci|indiciad|reus?\b|julgament|juri\b|pres[oa]s?\b|prisao|acusad|investiga|inquerito|ministerio publico|\bmp\b|justica|stf\b|processo|indeniz|afastad|expuls)"
SUSPEITO = r"\bsuspeit[oa]s?\b|\bcriminos[oa]s?\b|\bbandid[oa]s?\b|\btraficantes?\b|\bassaltantes?\b"
ATRIBUICAO = r"(diz (a )?(pm|policia)|segundo (a )?(pm|policia)|afirma (a )?(pm|policia)|de acordo com (a )?(pm|policia)|, diz pm|, diz policia|versao da (pm|policia))"
EUFEMISMO = r"(confronto|troca de tiros|intervencao policial|auto de resistencia|resistencia seguida de morte|reagiu|reagiram|revid)"

# Padrões fortes de morte causada por agente estatal (verificados antes de "policial vítima")
MDIP_FORTE = (
    r"(mort[oa]s?|morre[mu]?|morreram|baleado?a?s?|executad[oa]s?|atingid[oa]s?)\s+"
    r"(em|durante|apos|numa|na|no)\s+(um\s+|uma\s+)?(suposto\s+)?(confronto|troca de tiros|operacao|acao policial|"
    r"acao da (pm|policia)|intervencao|abordagem|perseguicao|incursao)"
    r"|(mort[oa]s?|baleado?a?s?|executad[oa]s?|assassinad[oa]s?)\s+(por|pela|pelo|pelos|pelas)\s+"
    r"(pm|pms|policia|policial|policiais|prf|agentes?|guarda|bope|rota|gcm|militares)"
    r"|\b(pm|pms|policial|policiais|policia|prf|bope|rota|gcm)\b[^,.;:]{0,25}\b(mata|matam|matou|mataram|"
    r"executa|executam|executou|executaram|fuzila|fuzilaram)\b"
    r"|confronto com (a )?(pm|policia|policiais)[^,.;:]{0,30}(mort|morre)"
    r"|(mort|morre)[^.;:]{0,40}confronto com (a )?(pm|policia|policiais|bope|rota)"
    r"|(operacao|acao|confronto|intervencao|incursao)[^,.;:]{0,40}deixa(m|ram)?\s[^,.;:]{0,20}mort"
    r"|chacina (policial|da pm|da policia|de policiais)|pms? (preso|presos|condenad|denunciad|indiciad|reus?)[^,.;:]{0,30}(morte|matar|chacina|homicidio)")
INTERNACIONAL = r"\b(franca|frances|eua|estados unidos|americano|minneapolis|africa do sul|haiti|israel|gaza|argentina|chile|colombia|mexico|equador|peru|reino unido|inglaterra|india|ira|venezuela)\b"

def classifica_relevancia(t):
    s = sem_acento(t)
    if re.search(INTERNACIONAL, s):
        return "fora do escopo"
    if re.search(MDIP_FORTE, s):
        return "tematico" if re.search(TEMATICO, s) else "caso MDIP"
    if re.search(POLICIAL_VITIMA, s):
        return "policial vítima"
    tem_morte = re.search(MORTE, s) is not None
    tem_pol = re.search(POLICIA, s) is not None
    if tem_morte and tem_pol:
        return "tematico" if re.search(TEMATICO, s) else "caso MDIP"
    if re.search(TEMATICO, s) and tem_pol:
        return "tematico"
    return "fora do escopo"

def agencia(t):
    s = sem_acento(t)
    if re.search(AGENTE_SUJEITO, s): return "agente como sujeito"
    if re.search(PASSIVA_COM_AGENTE, s): return "passiva com agente"
    if re.search(AGENCIA_TRANSFERIDA, s): return "agência transferida"
    if re.search(SEM_AGENTE, s): return "sem agente"
    return "indeterminada"

# ------------------------------------------------ bootstrap por veículo
def boot_diff_cluster(df, col, g1, g2, n=5000):
    """Diferença de proporções entre grupos, reamostrando veículos (clusters)."""
    agg = df.groupby(["grupo", "veiculo_real"])[col].agg(["sum", "count"]).reset_index()
    a = agg[agg.grupo == g1][["sum", "count"]].to_numpy()
    b = agg[agg.grupo == g2][["sum", "count"]].to_numpy()
    if len(a) < 2 or len(b) < 2:
        return None
    obs = a[:, 0].sum() / a[:, 1].sum() - b[:, 0].sum() / b[:, 1].sum()
    diffs = []
    for _ in range(n):
        ra = a[RNG.integers(0, len(a), len(a))]
        rb = b[RNG.integers(0, len(b), len(b))]
        diffs.append(ra[:, 0].sum() / ra[:, 1].sum() - rb[:, 0].sum() / rb[:, 1].sum())
    lo, hi = np.percentile(diffs, [2.5, 97.5])
    return {"diferenca": obs, "ic95": [lo, hi], "n_veiculos": [len(a), len(b)]}

def main():
    R = {}
    c = pd.read_csv(ENTRADA_COMPLETAS)
    c["texto"] = c["texto"].fillna("")
    c["veiculo_real"] = c.apply(veiculo_real, axis=1)
    c["grupo"] = c["veiculo_real"].map(grupo)
    c["titulo_limpo"] = c["titulo"].map(titulo_limpo)
    c["data"] = data_pub(c["data_publicacao"])
    c["n_chars"] = c["texto"].str.len()
    c["rota"] = c["fonte_descoberta"].map(
        lambda f: "varredura Wayback" if "Wayback" in str(f) else "consulta por termos")
    c["texto_bloqueado"] = c["texto"].str.contains(r"Access Denied|You don't have permission", regex=True)
    c["texto_curto"] = c["sucesso_raspagem"] & (c["n_chars"] < 500) & ~c["texto_bloqueado"]
    c["texto_valido"] = c["sucesso_raspagem"] & ~c["texto_bloqueado"] & (c["n_chars"] >= 500)

    # ---------- 0. duplicatas que a deduplicação do pipeline não removeu
    # O pipeline compara títulos só dentro do mesmo campo "veiculo"; as URLs de
    # redirecionamento do Google chegam com veiculo = news.google.com e escapam.
    c["chave"] = c["titulo_limpo"].map(sem_acento).str.replace(r"\W+", " ", regex=True).str.strip()
    R["n_bruto_arquivo"] = len(c)
    dup = c.duplicated(["veiculo_real", "chave"], keep=False)
    R["linhas_em_grupos_duplicados"] = int(dup.sum())
    R["excedentes_duplicados"] = int(c.duplicated(["veiculo_real", "chave"]).sum())
    R["excedentes_por_veiculo"] = c[c.duplicated(["veiculo_real", "chave"])]["veiculo_real"].value_counts().head(5).to_dict()
    c_pre = c.copy()
    c = (c.sort_values(["texto_valido", "n_chars"], ascending=False)
          .drop_duplicates(["veiculo_real", "chave"]).sort_index())
    R["n_unico"] = len(c)

    # ---------- 1. composição
    R["n_total"] = len(c)
    R["execucao_coleta"] = c["data_coleta"].str[:10].unique().tolist()
    fonte = c["fonte_descoberta"].str.replace(r" \(.*?\)", "", regex=True)
    R["por_estrategia"] = c["fonte_descoberta"].value_counts().to_dict()
    R["multi_estrategia"] = int(c["fonte_descoberta"].str.contains(r"\|").sum())
    R["url_redirecionamento_google"] = int(c["url"].str.contains("news.google.com").sum())
    R["veiculo_nao_resolvido_pelo_pipeline"] = int((c["veiculo"] == "news.google.com").sum())
    R["n_veiculos"] = int(c["veiculo_real"].nunique())
    vc = c["veiculo_real"].value_counts()
    R["top10_veiculos"] = vc.head(10).to_dict()
    R["share_top2"] = float(vc.head(2).sum() / len(c))
    R["veiculos_com_1_ou_2_materias"] = int((vc <= 2).sum())
    R["por_grupo"] = c["grupo"].value_counts().to_dict()
    alvo_presentes = sorted(set(vc.index) & (GRANDE_CIRCULACAO | ESPECIALIZADOS))
    R["veiculos_alvo_presentes"] = alvo_presentes

    # ---------- 2. datas
    ini, fim = pd.Timestamp("2022-01-01", tz="UTC"), pd.Timestamp("2023-12-31 23:59", tz="UTC")
    R["sem_data"] = int(c["data"].isna().sum())
    R["fora_da_janela"] = int(((c["data"] < ini) | (c["data"] > fim)).sum())
    c["ano"] = c["data"].dt.year
    R["por_ano"] = c["ano"].value_counts().sort_index().to_dict()
    mensal = c.groupby(c["data"].dt.to_period("M")).size()
    mensal.to_csv(f"{SAIDA}/materias_por_mes.csv")
    R["mensal_min_max"] = [int(mensal.min()), int(mensal.max())]

    # ---------- 3. extração
    R["raspagem_ok_pipeline"] = int(c["sucesso_raspagem"].sum())
    R["texto_bloqueado"] = int(c["texto_bloqueado"].sum())
    R["texto_curto"] = int(c["texto_curto"].sum())
    R["texto_valido"] = int(c["texto_valido"].sum())
    bloq_v = c[c.texto_bloqueado]["veiculo_real"].value_counts()
    R["bloqueio_por_veiculo"] = bloq_v.head(10).to_dict()
    tab_grupo = c.groupby("grupo").agg(
        materias=("url", "size"),
        veiculos=("veiculo_real", "nunique"),
        falha_pipeline=("sucesso_raspagem", lambda s: 1 - s.mean()),
        bloqueado=("texto_bloqueado", "mean"),
        texto_valido=("texto_valido", "mean"),
        mediana_chars=("n_chars", "median"),
    )
    tab_grupo.to_csv(f"{SAIDA}/extracao_por_grupo.csv")
    R["extracao_por_grupo"] = tab_grupo.round(4).to_dict(orient="index")
    c["falhou"] = (~c["texto_valido"]).astype(int)
    R["falha_GC_menos_ESP"] = boot_diff_cluster(c, "falhou", "Grande circulação", "Especializado")
    ext_v = c.groupby("veiculo_real").agg(n=("url", "size"), valido=("texto_valido", "mean"))
    ext_v[ext_v.n >= 10].sort_values("valido").to_csv(f"{SAIDA}/extracao_por_veiculo.csv")

    # ---------- 4. duplicatas residuais (já removidas acima; registro)
    chave = c["titulo_limpo"].map(sem_acento).str.replace(r"\W+", " ", regex=True).str.strip()
    R["titulos_repetidos_entre_veiculos_no_unico"] = int(chave.duplicated().sum())

    # ---------- 5. relevância (regra de título, NÃO validada)
    c["relevancia"] = c["titulo_limpo"].map(classifica_relevancia)
    R["relevancia"] = c["relevancia"].value_counts().to_dict()
    rel_g = pd.crosstab(c["grupo"], c["relevancia"], normalize="index")
    rel_g.to_csv(f"{SAIDA}/relevancia_por_grupo.csv")
    R["relevancia_por_grupo"] = rel_g.round(4).to_dict(orient="index")
    R["relevancia_instituicional_n"] = c[c.grupo == "Fonte institucional"]["relevancia"].value_counts().to_dict()

    # ---------- 6. cobertura versus eventos (2023)
    casos23 = c[(c.relevancia == "caso MDIP") & (c.ano == 2023)]
    R["materias_caso_2023"] = len(casos23)
    R["razao_materias_por_morte_2023"] = len(casos23) / 6393  # FBSP (2024)

    # ---------- 7. títulos das matérias de caso (NÃO validado)
    casos = c[c.relevancia == "caso MDIP"].copy()
    casos["agencia"] = casos["titulo_limpo"].map(agencia)
    casos["suspeito_no_titulo"] = casos["titulo_limpo"].map(lambda t: bool(re.search(SUSPEITO, sem_acento(t))))
    casos["atribuicao_policial"] = casos["titulo_limpo"].map(lambda t: bool(re.search(ATRIBUICAO, sem_acento(t))))
    casos["eufemismo_no_titulo"] = casos["titulo_limpo"].map(lambda t: bool(re.search(EUFEMISMO, sem_acento(t))))
    R["n_caso"] = len(casos)
    R["agencia_geral"] = casos["agencia"].value_counts().to_dict()
    ag = pd.crosstab(casos["grupo"], casos["agencia"])
    ag.to_csv(f"{SAIDA}/agencia_por_grupo_n.csv")
    R["agencia_por_grupo_n"] = ag.to_dict(orient="index")
    R["agencia_por_grupo_pct"] = pd.crosstab(casos["grupo"], casos["agencia"], normalize="index").round(4).to_dict(orient="index")
    for var in ["suspeito_no_titulo", "atribuicao_policial", "eufemismo_no_titulo"]:
        R[var + "_por_grupo"] = casos.groupby("grupo")[var].agg(["mean", "sum", "count"]).round(4).to_dict(orient="index")
    casos["sem_agente"] = (casos["agencia"] == "sem agente").astype(int)
    casos["agente_sujeito"] = (casos["agencia"] == "agente como sujeito").astype(int)
    casos["suspeito_int"] = casos["suspeito_no_titulo"].astype(int)
    R["sem_agente_GC_menos_ESP"] = boot_diff_cluster(casos, "sem_agente", "Grande circulação", "Especializado")
    R["agente_sujeito_GC_menos_ESP"] = boot_diff_cluster(casos, "agente_sujeito", "Grande circulação", "Especializado")
    R["suspeito_GC_menos_ESP"] = boot_diff_cluster(casos, "suspeito_int", "Grande circulação", "Especializado")
    casos["transferida"] = (casos["agencia"] == "agência transferida").astype(int)
    casos["apaga_agente"] = casos["agencia"].isin(["sem agente", "agência transferida"]).astype(int)
    R["apaga_agente_GC_menos_ESP"] = boot_diff_cluster(casos, "apaga_agente", "Grande circulação", "Especializado")
    casos["etapa_judicial"] = casos["titulo_limpo"].map(lambda t: bool(re.search(ETAPA_JUDICIAL, sem_acento(t))))
    R["etapa_judicial_por_grupo"] = casos.groupby("grupo")["etapa_judicial"].mean().round(4).to_dict()
    fato = casos[~casos["etapa_judicial"]]
    R["n_caso_etapa_fato"] = len(fato)
    R["agencia_etapa_fato_pct"] = pd.crosstab(fato["grupo"], fato["agencia"], normalize="index").round(4).to_dict(orient="index")
    R["agencia_etapa_fato_n"] = pd.crosstab(fato["grupo"], fato["agencia"]).to_dict(orient="index")
    R["apaga_agente_fato_GC_menos_ESP"] = boot_diff_cluster(fato, "apaga_agente", "Grande circulação", "Especializado")
    R["suspeito_fato_GC_menos_ESP"] = boot_diff_cluster(fato, "suspeito_int", "Grande circulação", "Especializado")
    for v in ["G1", "Ponte Jornalismo"]:
        sv = casos[casos.veiculo_real == v]; fv = fato[fato.veiculo_real == v]
        R["perfil_" + v] = {"n": len(sv), "n_fato": len(fv),
            "agencia_pct": sv["agencia"].value_counts(normalize=True).round(4).to_dict(),
            "agencia_fato_pct": fv["agencia"].value_counts(normalize=True).round(4).to_dict(),
            "suspeito": round(sv["suspeito_int"].mean(), 4), "suspeito_fato": round(fv["suspeito_int"].mean(), 4),
            "eufemismo": round(sv["eufemismo_no_titulo"].mean(), 4), "etapa_judicial": round(sv["etapa_judicial"].mean(), 4)}
    # Robustez à rota de entrada: as consultas por termos podem selecionar
    # títulos com a própria construção medida (circularidade). A Ponte entrou
    # pelas duas rotas; comparar as duas isola o efeito da seleção.
    R["por_rota_grupo"] = casos.groupby(["rota", "grupo"])[["apaga_agente", "agente_sujeito", "suspeito_int", "eufemismo_no_titulo"]].agg(["mean", "count"]).round(4).to_dict(orient="index")
    ponte = casos[casos.veiculo_real == "Ponte Jornalismo"]
    R["ponte_por_rota"] = ponte.groupby("rota")[["apaga_agente", "agente_sujeito", "suspeito_int", "eufemismo_no_titulo"]].agg(["mean", "count"]).round(4).to_dict(orient="index")
    so_consulta = casos[casos.rota == "consulta por termos"]
    R["apaga_agente_consulta_GC_menos_ESP"] = boot_diff_cluster(so_consulta, "apaga_agente", "Grande circulação", "Especializado")
    R["suspeito_consulta_GC_menos_ESP"] = boot_diff_cluster(so_consulta, "suspeito_int", "Grande circulação", "Especializado")
    # Ponte por rota: deduplicada DENTRO de cada rota, para que uma matéria achada
    # pelas duas rotas conte nas duas (a atribuição a uma só dependeria do desempate)
    pr = c_pre[c_pre.veiculo_real == "Ponte Jornalismo"].drop_duplicates(["rota", "chave"]).copy()
    pr["relevancia"] = pr["titulo_limpo"].map(classifica_relevancia)
    pr[["url", "rota", "titulo_limpo", "relevancia"]].to_csv(f"{SAIDA}/ponte_por_rota_titulos.csv", index=False, encoding="utf-8-sig")
    R["ponte_titulos_por_rota"] = pr.groupby("rota").size().to_dict()
    R["relevancia_ponte_varredura"] = pr[pr.rota == "varredura Wayback"]["relevancia"].value_counts().to_dict()
    ext_chave = c.groupby("veiculo_real").agg(n=("url", "size"), valido=("texto_valido", "mean"), bloqueado=("texto_bloqueado", "mean"))
    R["extracao_veiculos_chave"] = ext_chave.loc[[v for v in ["G1", "Ponte Jornalismo", "Brasil de Fato", "Mídia NINJA", "UOL Notícias", "Estadão", "Folha de S.Paulo", "O Globo", "CNN Brasil"] if v in ext_chave.index]].round(4).to_dict(orient="index")

    # por veículo (grandes)
    pv = casos.groupby("veiculo_real").agg(n=("url", "size"), sem_agente=("sem_agente", "mean"), apaga_agente=("apaga_agente", "mean"),
                                           agente_sujeito=("agente_sujeito", "mean"),
                                           suspeito=("suspeito_int", "mean"))
    pv[pv.n >= 10].sort_values("n", ascending=False).to_csv(f"{SAIDA}/titulos_por_veiculo.csv")
    R["titulos_por_veiculo_n10"] = pv[pv.n >= 10].round(3).to_dict(orient="index")

    # ---------- 8. amostra de validação humana (estratificada)
    partes = []
    for rel, k in [("caso MDIP", 90), ("tematico", 30), ("policial vítima", 30), ("fora do escopo", 50)]:
        sub = c[c.relevancia == rel]
        partes.append(sub.sample(min(k, len(sub)), random_state=7))
    am = pd.concat(partes).sample(frac=1, random_state=7)
    am = am[["url", "veiculo_real", "titulo_limpo"]].copy()
    am["relevancia_humana"] = ""   # caso MDIP | tematico | policial vítima | fora do escopo
    am["agencia_humana"] = ""      # agente como sujeito | passiva com agente | agência transferida | sem agente | indeterminada
    am["suspeito_humano"] = ""     # sim | não
    am.to_csv(f"{SAIDA}/amostra_validacao_titulos.csv", index=False, encoding="utf-8-sig")
    # regras ficam num arquivo separado, para não contaminar a leitura humana
    regras = c.loc[am.index, ["url", "relevancia"]].copy()
    regras = regras.merge(casos[["url", "agencia", "suspeito_no_titulo"]], on="url", how="left")
    regras.to_csv(f"{SAIDA}/amostra_validacao_regras.csv", index=False, encoding="utf-8-sig")

    # ---------- 9. arquivo de descoberta (execução de 19/03)
    if os.path.exists(ENTRADA_BRUTAS):
        b = pd.read_csv(ENTRADA_BRUTAS)
        wb = b[b.fonte_descoberta == "wayback_discovery"]
        paths = wb["url"].str.replace(r"^https?://(www\.)?", "", regex=True)
        R["brutas_n"] = len(b)
        R["brutas_por_estrategia"] = b["fonte_descoberta"].value_counts().to_dict()
        R["brutas_wayback_por_veiculo"] = wb["veiculo"].value_counts().to_dict()
        R["brutas_wayback_so_pagina_inicial"] = int(paths.str.fullmatch(r"[^/]+/?").sum())
        gn = b[b.fonte_descoberta == "Google News RSS"]
        R["brutas_gn_veiculos_distintos"] = int(gn["titulo"].map(lambda t: str(t).rsplit(" - ", 1)[-1]).nunique())
        R["brutas_gn_titulos_unicos"] = int(gn["titulo"].map(titulo_limpo).map(sem_acento).nunique())

    def chaves_str(o):
        if isinstance(o, dict):
            return {(" | ".join(map(str, k)) if isinstance(k, tuple) else str(k)): chaves_str(v) for k, v in o.items()}
        return o
    R = chaves_str(R)
    with open(f"{SAIDA}/resumo.json", "w", encoding="utf-8") as f:
        json.dump(R, f, ensure_ascii=False, indent=2, default=str)
    c.drop(columns=["texto"]).to_csv(f"{SAIDA}/corpus_anotado_regras.csv", index=False, encoding="utf-8-sig")
    print(json.dumps(R, ensure_ascii=False, indent=1, default=str))

if __name__ == "__main__":
    main()
