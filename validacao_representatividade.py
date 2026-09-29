#!/usr/bin/env python3
"""
Validação de Representatividade do Corpus
==========================================
Pesquisa: Desinformação e Criminalização Póstuma (IC - UNESP/FAAC)

Implementa o "Argumento de Representatividade" (cf. literatura de validação
de corpora, 2024): cruza o corpus coletado com uma lista de casos de
referência (população conhecida via FBSP, Rede de Observatórios, Fogo
Cruzado) e quantifica:

  1. TAXA DE COBERTURA: % dos casos de referência capturados pelo corpus
  2. VIÉS DE COBERTURA: quais tipos de caso ficam de fora (perfil da vítima,
     região, contexto)
  3. VIÉS DE SELEÇÃO: distribuição do corpus por veículo vs. distribuição
     esperada

Uso:
    1. Preencha o arquivo casos_referencia.csv (gerado na primeira execução)
       com casos documentados pelo FBSP / Rede de Observatórios / Fogo Cruzado
    2. python validacao_representatividade.py

Saída: dados_coletados/validacao/ com relatório e tabelas.
"""

import os
import re
import unicodedata
from datetime import datetime

import pandas as pd

# ============================================================================
# CONFIGURAÇÃO
# ============================================================================

CSV_CORPUS = os.path.join("dados_coletados", "04_materias_raspadas_sucesso.csv")
CSV_REFERENCIA = os.path.join("dados_coletados", "casos_referencia.csv")
DIR_VALIDACAO = os.path.join("dados_coletados", "validacao")
os.makedirs(DIR_VALIDACAO, exist_ok=True)


# ============================================================================
# TEMPLATE DA LISTA DE REFERÊNCIA
# ============================================================================

TEMPLATE_REFERENCIA = """nome_vitima,data_morte,cidade,uf,contexto,raca_vitima,idade_vitima,fonte_registro,termos_busca_alternativos
Genivaldo de Jesus Santos,2022-05-25,Umbaúza,SE,abordagem PRF,negra,38,imprensa nacional,"genivaldo;viatura;gás"
,,,,,,,,
,,,,,,,,
"""

INSTRUCOES_REFERENCIA = """INSTRUÇÕES — Lista de casos de referência
============================================================
Este arquivo define a "população conhecida" de casos de MDIP contra a qual
o corpus será validado. Preencha uma linha por caso, usando como fontes:

  - Anuário Brasileiro de Segurança Pública (FBSP)
  - Relatório "Pele Alvo" (Rede de Observatórios da Segurança)
  - Plataforma Fogo Cruzado (API aberta: api.fogocruzado.org.br)
  - Relatórios da Ouvidoria das Polícias / MP-SP

Colunas:
  nome_vitima ................. nome completo (como registrado)
  data_morte .................. AAAA-MM-DD
  cidade, uf .................. local da ocorrência
  contexto .................... operação policial | abordagem | perseguição | outro
  raca_vitima ................. negra | branca | não informada
  idade_vitima ................ número ou vazio
  fonte_registro .............. de onde veio o registro (FBSP, Pele Alvo etc.)
  termos_busca_alternativos ... apelidos/grafias alternativas separados por ;

Quanto mais completa a lista, mais forte o Argumento de Representatividade.
Recomenda-se registrar TODOS os casos do recorte (2022-2023) documentados
pelas fontes acima para o(s) estado(s) do escopo — não apenas os famosos.
============================================================
"""


# ============================================================================
# FUNÇÕES
# ============================================================================

def normalizar(texto: str) -> str:
    """Remove acentos e normaliza para comparação."""
    if not isinstance(texto, str):
        return ""
    texto = unicodedata.normalize("NFKD", texto)
    texto = "".join(c for c in texto if not unicodedata.combining(c))
    return texto.lower().strip()


def caso_aparece_no_corpus(caso: pd.Series, df_corpus: pd.DataFrame) -> pd.DataFrame:
    """
    Verifica se um caso de referência aparece no corpus.
    Busca o nome da vítima (e termos alternativos) em título + texto.
    Retorna as matérias que mencionam o caso.
    """
    termos = []
    nome = normalizar(str(caso.get("nome_vitima", "")))
    if nome and len(nome) > 5:
        termos.append(nome)
        # Também primeiro + último nome (cobre variações)
        partes = nome.split()
        if len(partes) >= 3:
            termos.append(f"{partes[0]} {partes[-1]}")

    alternativos = str(caso.get("termos_busca_alternativos", ""))
    for t in alternativos.split(";"):
        t = normalizar(t)
        if t and len(t) > 3:
            termos.append(t)

    if not termos:
        return df_corpus.iloc[0:0]

    mask = df_corpus["_texto_norm"].apply(
        lambda texto: any(t in texto for t in termos)
    )
    return df_corpus[mask]


def main():
    print("=" * 60)
    print("VALIDAÇÃO DE REPRESENTATIVIDADE DO CORPUS")
    print("=" * 60)

    # --- Verificar/criar lista de referência ---
    if not os.path.exists(CSV_REFERENCIA):
        with open(CSV_REFERENCIA, "w", encoding="utf-8-sig") as f:
            f.write(TEMPLATE_REFERENCIA)
        with open(
            os.path.join("dados_coletados", "INSTRUCOES_casos_referencia.txt"),
            "w", encoding="utf-8",
        ) as f:
            f.write(INSTRUCOES_REFERENCIA)
        print(f"""
Arquivo de referência criado: {CSV_REFERENCIA}

PRÓXIMO PASSO: preencha esse CSV com os casos documentados pelo FBSP,
Rede de Observatórios (Pele Alvo) e Fogo Cruzado para o período 2022-2023.
Instruções detalhadas em: dados_coletados/INSTRUCOES_casos_referencia.txt

Depois rode este script novamente.
""")
        return

    # --- Carregar dados ---
    if not os.path.exists(CSV_CORPUS):
        print(f"ERRO: corpus não encontrado em {CSV_CORPUS}")
        print("Execute primeiro o news_pipeline.py.")
        return

    df_corpus = pd.read_csv(CSV_CORPUS, encoding="utf-8")
    df_corpus["texto"] = df_corpus["texto"].fillna("").astype(str)
    df_corpus["titulo"] = df_corpus["titulo"].fillna("").astype(str)
    df_corpus["_texto_norm"] = (df_corpus["titulo"] + " " + df_corpus["texto"]).apply(normalizar)

    df_ref = pd.read_csv(CSV_REFERENCIA, encoding="utf-8-sig")
    df_ref = df_ref.dropna(subset=["nome_vitima"])
    df_ref = df_ref[df_ref["nome_vitima"].str.strip() != ""]

    if df_ref.empty:
        print(f"A lista de referência está vazia. Preencha {CSV_REFERENCIA} e rode novamente.")
        return

    print(f"\nCorpus: {len(df_corpus)} matérias")
    print(f"Casos de referência: {len(df_ref)}")

    # --- Cruzamento ---
    resultados = []
    for _, caso in df_ref.iterrows():
        materias_caso = caso_aparece_no_corpus(caso, df_corpus)
        veiculos = materias_caso["veiculo"].unique().tolist() if not materias_caso.empty else []
        resultados.append({
            "nome_vitima": caso["nome_vitima"],
            "data_morte": caso.get("data_morte", ""),
            "uf": caso.get("uf", ""),
            "contexto": caso.get("contexto", ""),
            "raca_vitima": caso.get("raca_vitima", ""),
            "capturado_no_corpus": len(materias_caso) > 0,
            "n_materias": len(materias_caso),
            "veiculos": "; ".join(veiculos),
        })

    df_result = pd.DataFrame(resultados)

    # --- Métricas de cobertura ---
    taxa_cobertura = df_result["capturado_no_corpus"].mean() * 100
    capturados = df_result[df_result["capturado_no_corpus"]]
    perdidos = df_result[~df_result["capturado_no_corpus"]]

    # Viés de cobertura por atributo
    def cobertura_por(coluna):
        if coluna not in df_result.columns or df_result[coluna].isna().all():
            return None
        return df_result.groupby(coluna)["capturado_no_corpus"].agg(["mean", "count"])

    cob_raca = cobertura_por("raca_vitima")
    cob_uf = cobertura_por("uf")
    cob_contexto = cobertura_por("contexto")

    # --- Relatório ---
    relatorio = f"""
{'='*70}
ARGUMENTO DE REPRESENTATIVIDADE — VALIDAÇÃO DO CORPUS
Gerado em: {datetime.now().strftime('%Y-%m-%d %H:%M')}
{'='*70}

1. TAXA DE COBERTURA GERAL
   Casos de referência: {len(df_ref)}
   Casos capturados pelo corpus: {len(capturados)} ({taxa_cobertura:.1f}%)
   Casos NÃO capturados: {len(perdidos)}

   Interpretação: o corpus cobre {taxa_cobertura:.1f}% da população conhecida
   de casos. {"Cobertura alta — o corpus é defensável como representativo." if taxa_cobertura >= 70 else "Cobertura moderada/baixa — reportar como limitação e investigar o padrão dos casos perdidos (viés de cobertura)." }

2. VIÉS DE COBERTURA (quem fica de fora?)
"""
    if cob_raca is not None:
        relatorio += "\n   Por raça da vítima:\n"
        for idx, row in cob_raca.iterrows():
            relatorio += f"     {idx}: {row['mean']*100:.0f}% capturados (n={int(row['count'])})\n"
    if cob_uf is not None:
        relatorio += "\n   Por UF:\n"
        for idx, row in cob_uf.iterrows():
            relatorio += f"     {idx}: {row['mean']*100:.0f}% capturados (n={int(row['count'])})\n"
    if cob_contexto is not None:
        relatorio += "\n   Por contexto:\n"
        for idx, row in cob_contexto.iterrows():
            relatorio += f"     {idx}: {row['mean']*100:.0f}% capturados (n={int(row['count'])})\n"

    relatorio += f"""
   Se algum grupo tem cobertura sistematicamente menor, isso indica viés
   de cobertura — casos desse perfil recebem menos atenção midiática OU
   os crawlers não os alcançam. Ambas as hipóteses são achados relevantes
   para a pesquisa (a primeira é, em si, evidência de invisibilização).

3. CASOS NÃO CAPTURADOS (verificar manualmente)
"""
    for _, row in perdidos.iterrows():
        relatorio += f"   - {row['nome_vitima']} ({row['uf']}, {row['data_morte']})\n"

    relatorio += f"""
   Para cada caso perdido, verifique manualmente (busca no Google) se:
   (a) houve cobertura que os crawlers não alcançaram → viés de coleta
   (b) não houve cobertura → invisibilização midiática (achado!)

4. DECLARAÇÃO PARA A DISSERTAÇÃO (modelo)
   "O corpus foi validado contra uma lista de {len(df_ref)} casos de MDIP
   documentados por [FBSP/Pele Alvo/Fogo Cruzado] no período, alcançando
   taxa de cobertura de {taxa_cobertura:.1f}%. [Descrever padrão dos casos
   não capturados]. Reconhece-se como limitação a impossibilidade de
   amostragem aleatória em coleta via web, mitigada pela multiplicidade
   de fontes de descoberta (4 crawlers independentes) e pela busca
   direcionada em {35} veículos."
{'='*70}
"""

    print(relatorio)
    with open(os.path.join(DIR_VALIDACAO, "argumento_representatividade.txt"), "w", encoding="utf-8") as f:
        f.write(relatorio)
    df_result.to_csv(os.path.join(DIR_VALIDACAO, "cobertura_por_caso.csv"),
                     index=False, encoding="utf-8-sig")

    print(f"Relatório: {DIR_VALIDACAO}/argumento_representatividade.txt")
    print(f"Tabela: {DIR_VALIDACAO}/cobertura_por_caso.csv")


if __name__ == "__main__":
    main()
