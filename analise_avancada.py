#!/usr/bin/env python3
"""
Análise Avançada de Matérias sobre Mortes Decorrentes de Intervenção Policial
==============================================================================
Pesquisa: Desinformação e Criminalização Póstuma (IC - UNESP/FAAC)

MELHORIAS EM RELAÇÃO À VERSÃO ANTERIOR:
- Análise separada de títulos/leads vs. corpo
- Análise de legendas de imagens
- Intertextualidade (similaridade com textos oficiais)
- Redes de circulação (quem pauta quem)
- Classificador de enquadramento (ML)
- Fichas consolidadas por caso
- Análise de omissões
- Dashboard interativo (HTML/Plotly)
- NER automático para descoberta de casos
- Análise de fontes por espaço textual
- Evolução temporal de enquadramento por caso
- Análise de sentimento por trecho
- Pré-codificação automática para codebook

Requisitos:
    pip install pandas matplotlib seaborn spacy scikit-learn plotly
    pip install wordcloud openpyxl jinja2 nltk fuzzywuzzy python-Levenshtein
    python -m spacy download pt_core_news_lg

Uso:
    python analise_avancada.py

Entrada: CSV gerado pelo news_pipeline.py (04_materias_raspadas_sucesso.csv)
Saída: Gráficos, tabelas, fichas, dashboard e relatório em dados_coletados/analise/
"""

import os
import re
import json
import math
import warnings
from collections import Counter, defaultdict
from datetime import datetime, timedelta
from typing import Optional

import pandas as pd
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
import seaborn as sns

warnings.filterwarnings("ignore")

plt.rcParams.update({
    "figure.figsize": (14, 7),
    "font.size": 11,
    "axes.titlesize": 14,
    "axes.labelsize": 12,
    "figure.dpi": 150,
})
sns.set_theme(style="whitegrid", palette="muted")


# ============================================================================
# CONFIGURAÇÃO
# ============================================================================

CSV_ENTRADA = os.path.join("dados_coletados", "04_materias_raspadas_sucesso.csv")

DIR_ANALISE = os.path.join("dados_coletados", "analise_avancada")
DIR_GRAFICOS = os.path.join(DIR_ANALISE, "graficos")
DIR_TABELAS = os.path.join(DIR_ANALISE, "tabelas")
DIR_FICHAS = os.path.join(DIR_ANALISE, "fichas_por_caso")
DIR_CODEBOOK = os.path.join(DIR_ANALISE, "pre_codificacao")
DIR_DASHBOARD = os.path.join(DIR_ANALISE, "dashboard")

for d in [DIR_ANALISE, DIR_GRAFICOS, DIR_TABELAS, DIR_FICHAS, DIR_CODEBOOK, DIR_DASHBOARD]:
    os.makedirs(d, exist_ok=True)


# ============================================================================
# DICIONÁRIOS DE ANÁLISE
# ============================================================================

TERMOS_CRIMINALIZANTES = [
    "bandido", "bandidos", "criminoso", "criminosos", "criminosa",
    "traficante", "traficantes", "suspeito", "suspeitos", "suspeita",
    "elemento", "elementos", "meliante", "meliantes",
    "marginal", "marginais", "delinquente", "delinquentes",
    "foragido", "foragidos", "foragida",
    "infrator", "infratores", "infratora",
    "comparsa", "comparsas",
    "facção", "facções",
    "envolvido com o tráfico", "envolvido com o crime",
    "ligação com o tráfico", "ligado ao tráfico",
    "antecedentes criminais", "passagem pela polícia",
    "ficha criminal", "ficha suja",
    "anotações criminais",
]

TERMOS_HUMANIZANTES = [
    "morador", "moradora", "moradores",
    "pai", "mãe", "filho", "filha", "irmão", "irmã",
    "trabalhador", "trabalhadora", "trabalhadores",
    "estudante", "estudantes",
    "jovem", "jovens",
    "adolescente", "adolescentes",
    "criança", "crianças",
    "família", "familiares", "familiar",
    "comunidade", "vizinhos", "vizinha",
    "sonho", "sonhava", "queria ser",
    "inocente", "inocentes",
    "vítima", "vítimas",
]

EUFEMISMOS = [
    "auto de resistência",
    "resistência seguida de morte",
    "confronto", "confrontos",
    "troca de tiros", "troca de disparos",
    "revide", "revidaram",
    "reagiu à abordagem", "reagiram à abordagem",
    "ação policial resultou",
    "incidente", "ocorrência",
    "legítima defesa",
    "excludente de ilicitude",
]

TERMOS_QUESTIONAMENTO = [
    "testemunhas relatam", "testemunhas afirmam",
    "moradores contestam", "moradores negam", "moradores dizem",
    "familiares dizem", "familiares afirmam", "familiares contestam",
    "contradiz", "contradição", "contradições",
    "versão contestada", "versão questionada",
    "perícia", "peritos",
    "imagens mostram", "vídeo mostra", "câmera", "câmeras",
    "execução", "execuções", "executado", "executados",
    "chacina", "massacre",
    "uso excessivo", "desproporcional", "abuso",
    "plantou", "plantar", "forjar", "forjado", "fraude",
    "manipulação de cena", "alteração de cena",
]

FONTES_OFICIAIS_PADROES = [
    r"segundo a pol[íi]cia", r"de acordo com a pol[íi]cia",
    r"a pol[íi]cia informou", r"a pol[íi]cia disse", r"a pol[íi]cia afirmou",
    r"segundo a pm", r"de acordo com a pm",
    r"a pm informou", r"a pm disse", r"a pm afirmou",
    r"segundo a ssp", r"de acordo com a ssp",
    r"secretaria de seguran[çc]a",
    r"segundo o delegado", r"delegado informou", r"delegado disse",
    r"boletim de ocorr[êe]ncia", r"registro policial",
    r"nota oficial", r"nota da pol[íi]cia", r"nota da pm",
    r"porta-voz da pol[íi]cia",
    r"comando da pm", r"comando da pol[íi]cia",
    r"bope", r"core",
]

FONTES_COMUNITARIAS_PADROES = [
    r"moradores? (?:relata|diz|afirma|conta|denuncia)",
    r"familiares? (?:diz|relata|afirma|conta|denuncia)",
    r"segundo (?:familiares|moradores)",
    r"de acordo com (?:familiares|moradores)",
    r"testemunhas?", r"vizinhos? (?:relata|diz)",
    r"m[ãa]e da v[íi]tima", r"pai da v[íi]tima", r"fam[íi]lia da v[íi]tima",
]

FONTES_ESPECIALIZADAS_PADROES = [
    r"pesquisador(?:a|es)?", r"especialista(?:s)?",
    r"professor(?:a)?", r"universidade",
    r"observat[óo]rio", r"f[óo]rum brasileiro de seguran",
    r"defensor(?:a)? p[úu]blic", r"defensoria",
    r"direitos humanos", r"anistia internacional",
    r"human rights watch",
]

MARCADORES_RACIAIS = [
    "negro", "negra", "negros", "negras",
    "preto", "preta", "pretos", "pretas",
    "pardo", "parda", "pardos", "pardas",
    "branco", "branca", "brancos", "brancas",
    "afrodescendente", "afro-brasileiro",
    "racismo", "racial", "raciais",
    "cor da pele", "cor de pele",
    "genocídio negro",
    "racismo estrutural", "racismo institucional",
]

# Elementos que DEVERIAM estar presentes em cobertura completa
ELEMENTOS_ESPERADOS = {
    "nome_vitima": {
        "descricao": "Nome completo da vítima",
        "padroes": [r"[A-Z][a-záàâãéèêíïóôõúç]+ (?:dos? |das? |de |da )?[A-Z][a-záàâãéèêíïóôõúç]+"],
        "peso": 3,
    },
    "idade_vitima": {
        "descricao": "Idade da vítima",
        "padroes": [r"\d{1,2}\s*anos", r"idade", r"menor de idade", r"adolescente de \d+"],
        "peso": 2,
    },
    "contexto_familiar": {
        "descricao": "Contexto familiar/pessoal",
        "padroes": [r"pai de", r"mãe de", r"filho de", r"casado", r"família", r"deixa \d+ filhos?"],
        "peso": 2,
    },
    "versao_testemunhas": {
        "descricao": "Versão de testemunhas/moradores",
        "padroes": [r"moradores? (?:relata|diz|afirma|conta)", r"testemunha", r"vizinhos?"],
        "peso": 3,
    },
    "versao_familia": {
        "descricao": "Versão dos familiares",
        "padroes": [r"familiares?", r"mãe (?:da vítima|disse|afirm)", r"pai (?:da vítima|disse|afirm)"],
        "peso": 3,
    },
    "circunstancias_detalhadas": {
        "descricao": "Circunstâncias detalhadas da morte",
        "padroes": [r"como aconteceu", r"din[âa]mica dos fatos", r"reconstituição", r"perícia"],
        "peso": 2,
    },
    "historico_local": {
        "descricao": "Histórico de violência no local",
        "padroes": [r"outras mortes", r"histórico", r"não é a primeira vez", r"operações anteriores",
                     r"mortes na região", r"letalidade"],
        "peso": 2,
    },
    "dados_estatisticos": {
        "descricao": "Dados estatísticos sobre violência policial",
        "padroes": [r"dados do", r"estatístic", r"anuário", r"fórum brasileiro",
                     r"observatório", r"segundo pesquisa", r"levantamento"],
        "peso": 1,
    },
    "identificacao_racial": {
        "descricao": "Identificação racial da vítima",
        "padroes": [r"negro", r"negra", r"pardo", r"parda", r"branco", r"branca", r"cor ", r"raça"],
        "peso": 2,
    },
    "acompanhamento_judicial": {
        "descricao": "Informações sobre investigação/processo",
        "padroes": [r"investiga", r"inquérito", r"ministério público", r"denúncia",
                     r"processo", r"julgamento", r"iml", r"laudo"],
        "peso": 1,
    },
}

VEICULOS_MAINSTREAM = ["G1", "O Globo", "Folha de S.Paulo", "Estadão", "UOL", "R7",
                        "CNN Brasil", "O Globo / Globo", "Terra"]
VEICULOS_ALTERNATIVOS = ["Ponte Jornalismo", "The Intercept Brasil", "Brasil de Fato",
                          "Mídia NINJA", "CartaCapital", "Fogo Cruzado"]

CASOS_CONHECIDOS = {
    "genivaldo": "Genivaldo de Jesus Santos",
    "vila cruzeiro": "Operação Vila Cruzeiro",
    "complexo do alemão": "Operação Complexo do Alemão",
    "complexo da penha": "Operação Complexo da Penha",
    "jacarezinho": "Operação Jacarezinho",
    "kathlen romeu": "Kathlen Romeu",
    "durval teófilo": "Durval Teófilo",
    "ágatha félix": "Ágatha Félix",
    "paraisópolis": "Paraisópolis",
    "cidade de deus": "Cidade de Deus",
    "complexo da maré": "Complexo da Maré",
    "salgueiro": "Complexo do Salgueiro",
    "rio das pedras": "Rio das Pedras",
    "guarapari": "Chacina de Guarapari",
    "favela do muquiço": "Favela do Muquiço",
}


# ============================================================================
# FUNÇÕES AUXILIARES
# ============================================================================

def contar_ocorrencias(texto: str, termos: list[str]) -> dict[str, int]:
    texto_lower = texto.lower()
    contagem = {}
    for termo in termos:
        n = texto_lower.count(termo.lower())
        if n > 0:
            contagem[termo] = n
    return contagem


def contar_total(texto: str, termos: list[str]) -> int:
    return sum(contar_ocorrencias(texto, termos).values())


def contar_regex(texto: str, padroes: list[str]) -> int:
    texto_lower = texto.lower()
    total = 0
    for padrao in padroes:
        total += len(re.findall(padrao, texto_lower))
    return total


def classificar_veiculo(nome: str) -> str:
    if nome in VEICULOS_MAINSTREAM:
        return "Mainstream"
    elif nome in VEICULOS_ALTERNATIVOS:
        return "Alternativo"
    else:
        return "Outro/Regional"


def extrair_lead(texto: str, n_chars: int = 500) -> str:
    """Extrai o lead (primeiros ~500 caracteres / primeiro parágrafo)."""
    paragrafos = texto.split("\n")
    lead = ""
    for p in paragrafos:
        p = p.strip()
        if len(p) > 50:
            lead = p
            break
    if not lead:
        lead = texto[:n_chars]
    return lead[:n_chars]


def extrair_corpo(texto: str, n_chars_lead: int = 500) -> str:
    """Extrai o corpo (tudo após o lead)."""
    lead = extrair_lead(texto, n_chars_lead)
    idx = texto.find(lead)
    if idx >= 0:
        return texto[idx + len(lead):]
    return texto[n_chars_lead:]


def calcular_sentimento_simples(texto: str) -> float:
    """
    Sentimento simples baseado em dicionário.
    Retorna valor entre -1 (muito negativo) e 1 (muito positivo).
    Calibrado para contexto de violência policial.
    """
    palavras_negativas = [
        "morte", "morto", "morta", "mortes", "mortos",
        "matar", "matou", "mataram", "assassinato", "assassinado",
        "violência", "violento", "violenta", "brutal", "brutalidade",
        "execução", "executado", "chacina", "massacre",
        "terror", "medo", "pânico", "desespero", "sofrimento",
        "dor", "luto", "tragédia", "trágico", "bárbaro",
        "denúncia", "abuso", "tortura", "agressão",
        "injustiça", "impunidade", "descaso", "negligência",
        "revolta", "indignação", "horror",
    ]
    palavras_positivas = [
        "justiça", "direito", "direitos", "proteção",
        "solidariedade", "apoio", "esperança", "resistência",
        "dignidade", "respeito", "humanidade",
        "investigação", "apuração", "responsabilização",
        "condenação", "preso", "punido", "punição",
        "reforma", "mudança", "avanço",
        "memória", "homenagem",
    ]

    texto_lower = texto.lower()
    palavras = texto_lower.split()
    if not palavras:
        return 0.0

    neg = sum(1 for p in palavras if p in palavras_negativas)
    pos = sum(1 for p in palavras if p in palavras_positivas)
    total = neg + pos
    if total == 0:
        return 0.0
    return (pos - neg) / total


def calcular_similaridade_textos(texto1: str, texto2: str) -> float:
    """Calcula similaridade entre dois textos usando Jaccard sobre n-grams."""
    def ngrams(texto, n=3):
        texto = texto.lower().strip()
        return set(texto[i:i+n] for i in range(len(texto) - n + 1))

    g1 = ngrams(texto1)
    g2 = ngrams(texto2)
    if not g1 or not g2:
        return 0.0
    return len(g1 & g2) / len(g1 | g2)


def extrair_citacoes(texto: str) -> list[dict]:
    """
    Extrai trechos de citação direta e indireta com a fonte associada.
    Retorna lista de dicts com 'fonte', 'tipo', 'trecho', 'tamanho'.
    """
    citacoes = []
    # Citação direta: "texto", disse/afirmou/declarou FONTE
    padrao_direta = re.compile(
        r'["""](.{10,300}?)["""],?\s*(?:disse|afirmou|declarou|informou|relatou|contou|explicou)\s+(.{5,80}?)[\.,]',
        re.IGNORECASE
    )
    for match in padrao_direta.finditer(texto):
        trecho, fonte = match.group(1), match.group(2)
        citacoes.append({
            "fonte": fonte.strip(),
            "tipo": "direta",
            "trecho": trecho.strip(),
            "tamanho": len(trecho.split()),
        })

    # Citação indireta: Segundo/De acordo com FONTE, ...
    padrao_indireta = re.compile(
        r'(?:segundo|de acordo com|conforme|para)\s+(.{5,100}?),\s*(.{10,300}?)[\.\n]',
        re.IGNORECASE
    )
    for match in padrao_indireta.finditer(texto):
        fonte, trecho = match.group(1), match.group(2)
        citacoes.append({
            "fonte": fonte.strip(),
            "tipo": "indireta",
            "trecho": trecho.strip(),
            "tamanho": len(trecho.split()),
        })

    return citacoes


def classificar_fonte_citacao(fonte_texto: str) -> str:
    """Classifica uma fonte extraída de citação."""
    fonte_lower = fonte_texto.lower()
    oficiais = ["polícia", "policial", "pm", "delegado", "delegada", "ssp",
                 "secretaria", "comando", "batalhão", "bope", "core", "prf",
                 "governador", "secretário", "porta-voz"]
    comunitarias = ["morador", "moradora", "familiar", "mãe", "pai", "irmão",
                     "vizinho", "testemunha", "amigo"]
    especializadas = ["pesquisador", "professor", "especialista", "advogado",
                       "defensor", "ong", "instituto", "observatório"]

    for t in oficiais:
        if t in fonte_lower:
            return "oficial"
    for t in comunitarias:
        if t in fonte_lower:
            return "comunitária"
    for t in especializadas:
        if t in fonte_lower:
            return "especializada"
    return "outra"


def salvar_grafico(fig, nome: str):
    caminho = os.path.join(DIR_GRAFICOS, f"{nome}.png")
    fig.savefig(caminho, bbox_inches="tight", facecolor="white")
    plt.close(fig)
    print(f"  Gráfico: {nome}.png")


def salvar_tabela(df_tab: pd.DataFrame, nome: str):
    caminho_csv = os.path.join(DIR_TABELAS, f"{nome}.csv")
    df_tab.to_csv(caminho_csv, index=True, encoding="utf-8-sig")
    try:
        df_tab.to_excel(os.path.join(DIR_TABELAS, f"{nome}.xlsx"), index=True)
    except Exception:
        pass
    print(f"  Tabela: {nome}.csv")


# ============================================================================
# NER — DESCOBERTA AUTOMÁTICA DE CASOS
# ============================================================================

def descobrir_casos_ner(df: pd.DataFrame) -> pd.DataFrame:
    """
    Usa NER (spaCy) para extrair nomes de pessoas e locais,
    combinado com dicionário de casos conhecidos.
    """
    print("\n  Executando NER para descoberta de casos...")

    # Primeiro: dicionário de casos conhecidos
    def match_casos_conhecidos(texto, titulo):
        texto_completo = f"{titulo} {texto}".lower()
        encontrados = []
        for chave, nome_caso in CASOS_CONHECIDOS.items():
            if chave in texto_completo:
                encontrados.append(nome_caso)
        return encontrados

    df["casos_dicionario"] = df.apply(
        lambda row: match_casos_conhecidos(row["texto"], row["titulo"]), axis=1
    )

    # Segundo: tentar NER com spaCy
    try:
        import spacy
        nlp = spacy.load("pt_core_news_lg")
        print("  spaCy carregado — extraindo entidades nomeadas...")

        def extrair_entidades(texto):
            # Processar apenas os primeiros 5000 chars (performance)
            doc = nlp(texto[:5000])
            pessoas = [ent.text for ent in doc.ents if ent.label_ == "PER" and len(ent.text) > 5]
            locais = [ent.text for ent in doc.ents if ent.label_ == "LOC" and len(ent.text) > 3]
            return {"pessoas": pessoas, "locais": locais}

        entidades = df["texto"].apply(extrair_entidades)
        df["pessoas_ner"] = entidades.apply(lambda x: x["pessoas"])
        df["locais_ner"] = entidades.apply(lambda x: x["locais"])

        # Combinar NER com dicionário
        df["casos_identificados"] = df.apply(
            lambda row: row["casos_dicionario"] if row["casos_dicionario"]
            else (row["pessoas_ner"][:3] if row["pessoas_ner"] else ["Caso não identificado"]),
            axis=1,
        )

        # Contar pessoas mais mencionadas no corpus (possíveis vítimas)
        todas_pessoas = Counter()
        for lista in df["pessoas_ner"]:
            todas_pessoas.update(lista)
        
        # Salvar as 50 pessoas mais mencionadas para revisão
        pessoas_freq = pd.DataFrame(
            todas_pessoas.most_common(50), columns=["nome", "frequencia"]
        )
        salvar_tabela(pessoas_freq.set_index("nome"), "ner_pessoas_frequentes")
        print(f"  NER: {len(todas_pessoas)} pessoas distintas identificadas")

    except (ImportError, OSError) as e:
        print(f"  spaCy não disponível ({e}). Usando apenas dicionário de casos.")
        df["pessoas_ner"] = [[] for _ in range(len(df))]
        df["locais_ner"] = [[] for _ in range(len(df))]
        df["casos_identificados"] = df["casos_dicionario"].apply(
            lambda x: x if x else ["Caso não identificado"]
        )

    return df


# ============================================================================
# CAMADA 1: MAPEAMENTO DO CORPUS
# ============================================================================

def camada1_mapeamento(df: pd.DataFrame) -> pd.DataFrame:
    print("\n" + "=" * 60)
    print("CAMADA 1: MAPEAMENTO DO CORPUS")
    print("=" * 60)

    print(f"\n  Total de matérias: {len(df)}")
    print(f"  Veículos distintos: {df['veiculo'].nunique()}")
    print(f"  Período: {df['data_publicacao'].min()} a {df['data_publicacao'].max()}")

    # Volume por veículo
    vol_veiculo = df["veiculo"].value_counts().head(20)
    fig, ax = plt.subplots(figsize=(14, 8))
    vol_veiculo.plot(kind="barh", ax=ax, color=sns.color_palette("viridis", len(vol_veiculo)))
    ax.set_title("Volume de Matérias por Veículo (Top 20)")
    ax.set_xlabel("Número de matérias")
    ax.invert_yaxis()
    for i, v in enumerate(vol_veiculo.values):
        ax.text(v + 0.5, i, str(v), va="center", fontsize=10)
    salvar_grafico(fig, "01_volume_por_veiculo")
    salvar_tabela(vol_veiculo.to_frame("quantidade"), "01_volume_por_veiculo")

    # Distribuição temporal
    df["ano_mes"] = df["data_publicacao"].dt.to_period("M")
    vol_mensal = df.groupby("ano_mes").size()
    fig, ax = plt.subplots(figsize=(16, 6))
    vol_mensal.plot(kind="bar", ax=ax, color="#2c7bb6", width=0.8)
    ax.set_title("Distribuição Temporal das Matérias (por mês)")
    ax.set_xlabel("Mês")
    ax.set_ylabel("Número de matérias")
    ax.tick_params(axis="x", rotation=45)
    salvar_grafico(fig, "02_distribuicao_temporal")
    salvar_tabela(vol_mensal.to_frame("quantidade"), "02_distribuicao_temporal")

    # Tipo de veículo
    df["tipo_veiculo"] = df["veiculo"].apply(classificar_veiculo)
    vol_tipo = df["tipo_veiculo"].value_counts()
    fig, axes = plt.subplots(1, 2, figsize=(14, 6))
    vol_tipo.plot(kind="pie", ax=axes[0], autopct="%1.1f%%",
                  colors=["#d73027", "#4575b4", "#91bfdb"])
    axes[0].set_title("Proporção por Tipo de Veículo")
    axes[0].set_ylabel("")
    pivot_tipo = df.groupby(["ano_mes", "tipo_veiculo"]).size().unstack(fill_value=0)
    pivot_tipo.plot(kind="bar", stacked=True, ax=axes[1],
                    color=["#4575b4", "#d73027", "#91bfdb"])
    axes[1].set_title("Cobertura por Tipo ao Longo do Tempo")
    axes[1].tick_params(axis="x", rotation=45)
    fig.tight_layout()
    salvar_grafico(fig, "03_tipo_veiculo")

    # Casos mais cobertos
    casos_explodidos = df.explode("casos_identificados")
    casos_contagem = casos_explodidos["casos_identificados"].value_counts()
    casos_id = casos_contagem[casos_contagem.index != "Caso não identificado"]

    if not casos_id.empty:
        fig, ax = plt.subplots(figsize=(14, 8))
        casos_id.head(15).plot(kind="barh", ax=ax, color=sns.color_palette("rocket", 15))
        ax.set_title("Casos Mais Cobertos pela Mídia")
        ax.set_xlabel("Número de matérias")
        ax.invert_yaxis()
        for i, v in enumerate(casos_id.head(15).values):
            ax.text(v + 0.3, i, str(v), va="center")
        salvar_grafico(fig, "04_casos_mais_cobertos")
        salvar_tabela(casos_contagem.to_frame("quantidade"), "04_casos_mais_cobertos")

    return df


# ============================================================================
# CAMADA 2: ANÁLISE DE LINGUAGEM (com título/lead separado)
# ============================================================================

def camada2_linguagem(df: pd.DataFrame) -> pd.DataFrame:
    print("\n" + "=" * 60)
    print("CAMADA 2: ANÁLISE DE LINGUAGEM")
    print("=" * 60)

    # Extrair lead e corpo
    print("\n  Separando títulos, leads e corpo...")
    df["lead"] = df["texto"].apply(extrair_lead)
    df["corpo"] = df["texto"].apply(extrair_corpo)
    df["n_palavras"] = df["texto"].apply(lambda t: len(t.split()))

    # --- Contagens para texto completo, título, lead e corpo ---
    for parte, col_texto in [("texto", "texto"), ("titulo", "titulo"), ("lead", "lead"), ("corpo", "corpo")]:
        prefix = f"{parte}_"
        df[f"{prefix}n_crim"] = df[col_texto].apply(lambda t: contar_total(t, TERMOS_CRIMINALIZANTES))
        df[f"{prefix}n_hum"] = df[col_texto].apply(lambda t: contar_total(t, TERMOS_HUMANIZANTES))
        df[f"{prefix}n_euf"] = df[col_texto].apply(lambda t: contar_total(t, EUFEMISMOS))
        df[f"{prefix}n_quest"] = df[col_texto].apply(lambda t: contar_total(t, TERMOS_QUESTIONAMENTO))
        df[f"{prefix}n_racial"] = df[col_texto].apply(lambda t: contar_total(t, MARCADORES_RACIAIS))

    # Fontes (regex para maior precisão)
    print("  Analisando fontes citadas...")
    df["n_fontes_oficiais"] = df["texto"].apply(lambda t: contar_regex(t, FONTES_OFICIAIS_PADROES))
    df["n_fontes_comunitarias"] = df["texto"].apply(lambda t: contar_regex(t, FONTES_COMUNITARIAS_PADROES))
    df["n_fontes_especializadas"] = df["texto"].apply(lambda t: contar_regex(t, FONTES_ESPECIALIZADAS_PADROES))

    # Taxas por 1000 palavras
    for col in ["texto_n_crim", "texto_n_hum", "texto_n_euf", "texto_n_quest",
                 "texto_n_racial", "n_fontes_oficiais", "n_fontes_comunitarias", "n_fontes_especializadas"]:
        col_taxa = col.replace("texto_n_", "taxa_").replace("n_fontes_", "taxa_fontes_")
        df[col_taxa] = (df[col] / df["n_palavras"] * 1000).fillna(0)

    # Índices
    df["indice_criminalizacao"] = df.apply(
        lambda r: r["texto_n_crim"] / (r["texto_n_crim"] + r["texto_n_hum"])
        if (r["texto_n_crim"] + r["texto_n_hum"]) > 0 else 0.5, axis=1
    )
    df["indice_fonte_oficial"] = df.apply(
        lambda r: r["n_fontes_oficiais"] / (r["n_fontes_oficiais"] + r["n_fontes_comunitarias"] + r["n_fontes_especializadas"])
        if (r["n_fontes_oficiais"] + r["n_fontes_comunitarias"] + r["n_fontes_especializadas"]) > 0 else 0.5, axis=1
    )

    # Índices separados para título e lead
    df["indice_crim_titulo"] = df.apply(
        lambda r: r["titulo_n_crim"] / (r["titulo_n_crim"] + r["titulo_n_hum"])
        if (r["titulo_n_crim"] + r["titulo_n_hum"]) > 0 else 0.5, axis=1
    )
    df["indice_crim_lead"] = df.apply(
        lambda r: r["lead_n_crim"] / (r["lead_n_crim"] + r["lead_n_hum"])
        if (r["lead_n_crim"] + r["lead_n_hum"]) > 0 else 0.5, axis=1
    )

    # --- Análise de sentimento por trecho ---
    print("  Calculando sentimento por trecho...")
    df["sentimento_titulo"] = df["titulo"].apply(calcular_sentimento_simples)
    df["sentimento_lead"] = df["lead"].apply(calcular_sentimento_simples)
    df["sentimento_corpo"] = df["corpo"].apply(calcular_sentimento_simples)
    df["sentimento_geral"] = df["texto"].apply(calcular_sentimento_simples)

    # --- Análise de citações e espaço por fonte ---
    print("  Extraindo citações e calculando espaço por fonte...")
    df["citacoes"] = df["texto"].apply(extrair_citacoes)
    df["n_citacoes_total"] = df["citacoes"].apply(len)

    def espaco_por_tipo_fonte(citacoes):
        espaco = {"oficial": 0, "comunitária": 0, "especializada": 0, "outra": 0}
        for c in citacoes:
            tipo = classificar_fonte_citacao(c["fonte"])
            espaco[tipo] += c["tamanho"]
        return espaco

    espacos = df["citacoes"].apply(espaco_por_tipo_fonte)
    df["espaco_fonte_oficial"] = espacos.apply(lambda x: x["oficial"])
    df["espaco_fonte_comunitaria"] = espacos.apply(lambda x: x["comunitária"])
    df["espaco_fonte_especializada"] = espacos.apply(lambda x: x["especializada"])
    df["espaco_total_fontes"] = df["espaco_fonte_oficial"] + df["espaco_fonte_comunitaria"] + df["espaco_fonte_especializada"]
    df["pct_espaco_oficial"] = df.apply(
        lambda r: r["espaco_fonte_oficial"] / r["espaco_total_fontes"] * 100
        if r["espaco_total_fontes"] > 0 else 50, axis=1
    )

    # --- GRÁFICOS ---

    # Comparação título vs lead vs corpo
    fig, axes = plt.subplots(1, 3, figsize=(18, 6))
    for i, (parte, label) in enumerate([("titulo", "Título"), ("lead", "Lead"), ("corpo", "Corpo")]):
        dados = {
            "Criminalizantes": df[f"{parte}_n_crim"].mean(),
            "Humanizantes": df[f"{parte}_n_hum"].mean(),
            "Eufemismos": df[f"{parte}_n_euf"].mean(),
        }
        cores = ["#d73027", "#4575b4", "#fc8d59"]
        axes[i].bar(dados.keys(), dados.values(), color=cores)
        axes[i].set_title(f"{label}")
        axes[i].set_ylabel("Média por matéria")
    fig.suptitle("Linguagem por Trecho da Matéria: Título vs Lead vs Corpo", fontsize=14)
    fig.tight_layout()
    salvar_grafico(fig, "05_linguagem_titulo_lead_corpo")

    # Termos mais frequentes
    todos_crim = Counter()
    todos_hum = Counter()
    for texto in df["texto"]:
        todos_crim.update(contar_ocorrencias(texto, TERMOS_CRIMINALIZANTES))
        todos_hum.update(contar_ocorrencias(texto, TERMOS_HUMANIZANTES))

    fig, axes = plt.subplots(1, 2, figsize=(18, 8))
    if todos_crim:
        pd.Series(dict(todos_crim.most_common(15))).plot(kind="barh", ax=axes[0], color="#d73027")
        axes[0].set_title("Termos Criminalizantes Mais Frequentes")
        axes[0].invert_yaxis()
    if todos_hum:
        pd.Series(dict(todos_hum.most_common(15))).plot(kind="barh", ax=axes[1], color="#4575b4")
        axes[1].set_title("Termos Humanizantes Mais Frequentes")
        axes[1].invert_yaxis()
    fig.tight_layout()
    salvar_grafico(fig, "06_termos_crim_vs_hum")

    # Eufemismos
    todos_euf = Counter()
    for texto in df["texto"]:
        todos_euf.update(contar_ocorrencias(texto, EUFEMISMOS))
    if todos_euf:
        fig, ax = plt.subplots(figsize=(14, 6))
        pd.Series(dict(todos_euf.most_common(15))).plot(kind="barh", ax=ax, color="#fc8d59")
        ax.set_title("Eufemismos Institucionais Mais Frequentes")
        ax.invert_yaxis()
        salvar_grafico(fig, "07_eufemismos")

    # Distribuição de fontes: menções vs espaço textual
    fig, axes = plt.subplots(1, 2, figsize=(14, 6))
    fontes_mencoes = {
        "Oficiais": df["n_fontes_oficiais"].sum(),
        "Comunitárias": df["n_fontes_comunitarias"].sum(),
        "Especializadas": df["n_fontes_especializadas"].sum(),
    }
    fontes_espaco = {
        "Oficiais": df["espaco_fonte_oficial"].sum(),
        "Comunitárias": df["espaco_fonte_comunitaria"].sum(),
        "Especializadas": df["espaco_fonte_especializada"].sum(),
    }
    cores_fontes = ["#d73027", "#4575b4", "#91bfdb"]
    axes[0].bar(fontes_mencoes.keys(), fontes_mencoes.values(), color=cores_fontes)
    axes[0].set_title("Fontes: Número de Menções")
    axes[0].set_ylabel("Total de menções")
    axes[1].bar(fontes_espaco.keys(), fontes_espaco.values(), color=cores_fontes)
    axes[1].set_title("Fontes: Espaço Textual (palavras em citações)")
    axes[1].set_ylabel("Total de palavras")
    fig.suptitle("Comparação: Menções vs. Espaço Textual por Tipo de Fonte", fontsize=14)
    fig.tight_layout()
    salvar_grafico(fig, "08_fontes_mencoes_vs_espaco")

    # Marcadores raciais
    com_racial = (df["texto_n_racial"] > 0).sum()
    sem_racial = (df["texto_n_racial"] == 0).sum()
    fig, ax = plt.subplots(figsize=(8, 6))
    ax.pie([com_racial, sem_racial],
           labels=[f"Com marcador\n({com_racial})", f"Sem marcador\n({sem_racial})"],
           autopct="%1.1f%%", colors=["#4575b4", "#fee090"])
    ax.set_title("Presença de Marcadores Raciais nas Matérias")
    salvar_grafico(fig, "09_marcadores_raciais")

    # Sentimento por trecho
    fig, ax = plt.subplots(figsize=(10, 6))
    sentimentos = pd.DataFrame({
        "Título": df["sentimento_titulo"],
        "Lead": df["sentimento_lead"],
        "Corpo": df["sentimento_corpo"],
    })
    sentimentos.boxplot(ax=ax)
    ax.axhline(y=0, color="red", linestyle="--", alpha=0.5)
    ax.set_title("Distribuição de Sentimento por Trecho da Matéria")
    ax.set_ylabel("Sentimento (-1 negativo, +1 positivo)")
    salvar_grafico(fig, "10_sentimento_por_trecho")

    # Nuvem de palavras
    try:
        from wordcloud import WordCloud
        stopwords_pt = set([
            "de", "a", "o", "que", "e", "do", "da", "em", "um", "para", "é",
            "com", "não", "uma", "os", "no", "se", "na", "por", "mais", "as",
            "dos", "como", "mas", "foi", "ao", "ele", "das", "tem", "à", "seu",
            "sua", "ou", "ser", "quando", "muito", "há", "nos", "já", "está",
            "eu", "também", "só", "pelo", "pela", "até", "isso", "ela", "entre",
            "era", "depois", "sem", "mesmo", "aos", "ter", "seus", "quem",
            "nas", "me", "esse", "eles", "estão", "você", "tinha", "foram",
            "essa", "num", "nem", "suas", "meu", "às", "minha", "têm", "numa",
            "pelos", "elas", "havia", "seja", "qual", "será", "nós", "disse",
            "sobre", "ainda", "anos", "dia", "onde", "dois", "três", "pode",
            "segundo", "acordo", "cada", "ser", "ter", "fazer",
        ])
        todo_texto = " ".join(df["texto"].dropna().tolist())
        wc = WordCloud(width=1600, height=800, background_color="white",
                       stopwords=stopwords_pt, max_words=150, colormap="RdBu_r").generate(todo_texto)
        fig, ax = plt.subplots(figsize=(16, 8))
        ax.imshow(wc, interpolation="bilinear")
        ax.axis("off")
        ax.set_title("Nuvem de Palavras do Corpus", fontsize=16)
        salvar_grafico(fig, "11_nuvem_palavras")
    except ImportError:
        print("  wordcloud não instalado, pulando nuvem de palavras")

    # Tabela resumo
    resumo = pd.DataFrame({
        "Métrica": [
            "Média termos criminalizantes (texto)", "Média termos humanizantes (texto)",
            "Média eufemismos (texto)", "Índice médio criminalização",
            "Índice criminalização no TÍTULO", "Índice criminalização no LEAD",
            "Fontes oficiais (menções)", "Fontes comunitárias (menções)",
            "Fontes especializadas (menções)", "% espaço textual fontes oficiais",
            "% matérias com marcadores raciais", "Sentimento médio título",
            "Sentimento médio lead", "Sentimento médio corpo",
        ],
        "Valor": [
            f"{df['texto_n_crim'].mean():.2f}", f"{df['texto_n_hum'].mean():.2f}",
            f"{df['texto_n_euf'].mean():.2f}", f"{df['indice_criminalizacao'].mean():.3f}",
            f"{df['indice_crim_titulo'].mean():.3f}", f"{df['indice_crim_lead'].mean():.3f}",
            f"{df['n_fontes_oficiais'].mean():.2f}", f"{df['n_fontes_comunitarias'].mean():.2f}",
            f"{df['n_fontes_especializadas'].mean():.2f}", f"{df['pct_espaco_oficial'].mean():.1f}%",
            f"{com_racial/len(df)*100:.1f}%", f"{df['sentimento_titulo'].mean():.3f}",
            f"{df['sentimento_lead'].mean():.3f}", f"{df['sentimento_corpo'].mean():.3f}",
        ],
    })
    salvar_tabela(resumo.set_index("Métrica"), "05_resumo_linguistico")

    return df


# ============================================================================
# CAMADA 3: ANÁLISE COMPARATIVA
# ============================================================================

def camada3_comparativa(df: pd.DataFrame) -> pd.DataFrame:
    print("\n" + "=" * 60)
    print("CAMADA 3: ANÁLISE COMPARATIVA")
    print("=" * 60)

    cores_tipo = {"Mainstream": "#d73027", "Alternativo": "#4575b4", "Outro/Regional": "#91bfdb"}
    metricas = ["indice_criminalizacao", "indice_fonte_oficial", "indice_crim_titulo",
                "indice_crim_lead", "taxa_crim", "taxa_hum", "taxa_euf", "taxa_quest",
                "taxa_racial", "pct_espaco_oficial", "sentimento_geral"]

    # Garantir que colunas existam
    metricas_existentes = [m for m in metricas if m in df.columns]

    # Mainstream vs Alternativo
    comp = df.groupby("tipo_veiculo")[metricas_existentes].mean()
    salvar_tabela(comp, "07_comparacao_tipo_veiculo")

    fig, axes = plt.subplots(2, 3, figsize=(18, 10))
    axes = axes.flatten()
    metricas_box = ["indice_criminalizacao", "indice_fonte_oficial", "indice_crim_titulo",
                     "pct_espaco_oficial", "sentimento_geral", "taxa_racial"]
    labels_box = {
        "indice_criminalizacao": "Criminalização\n(texto completo)",
        "indice_fonte_oficial": "Dependência\nfontes oficiais",
        "indice_crim_titulo": "Criminalização\n(só título)",
        "pct_espaco_oficial": "% espaço\nfontes oficiais",
        "sentimento_geral": "Sentimento\ngeral",
        "taxa_racial": "Taxa marcadores\nraciais",
    }
    for i, met in enumerate(metricas_box):
        if met in df.columns and i < len(axes):
            tipos = [t for t in ["Mainstream", "Alternativo", "Outro/Regional"] if t in df["tipo_veiculo"].values]
            dados = [df.loc[df["tipo_veiculo"] == t, met].dropna() for t in tipos]
            bp = axes[i].boxplot(dados, labels=tipos, patch_artist=True)
            for patch, tipo in zip(bp["boxes"], tipos):
                patch.set_facecolor(cores_tipo.get(tipo, "#ccc"))
                patch.set_alpha(0.7)
            axes[i].set_title(labels_box.get(met, met), fontsize=10)
    fig.suptitle("Comparação: Mainstream vs. Alternativo", fontsize=14, y=1.02)
    fig.tight_layout()
    salvar_grafico(fig, "12_comparacao_mainstream_alt")

    # Heatmap por veículo
    top_veiculos = df["veiculo"].value_counts().head(10).index.tolist()
    if top_veiculos:
        colunas_heat = ["indice_criminalizacao", "indice_fonte_oficial", "indice_crim_titulo",
                         "taxa_euf", "taxa_quest", "taxa_racial", "pct_espaco_oficial"]
        colunas_heat = [c for c in colunas_heat if c in df.columns]
        dados_heat = df[df["veiculo"].isin(top_veiculos)].groupby("veiculo")[colunas_heat].mean()
        dados_heat.columns = [c.replace("indice_", "").replace("taxa_", "").replace("pct_", "%") for c in dados_heat.columns]

        fig, ax = plt.subplots(figsize=(14, 8))
        sns.heatmap(dados_heat, annot=True, fmt=".2f", cmap="RdYlBu_r",
                    ax=ax, linewidths=0.5, center=dados_heat.values.mean())
        ax.set_title("Heatmap: Perfil Linguístico por Veículo")
        fig.tight_layout()
        salvar_grafico(fig, "13_heatmap_veiculo")
        salvar_tabela(dados_heat, "08_perfil_por_veiculo")

    # Evolução temporal
    if "ano_mes" in df.columns:
        cols_evol = ["indice_criminalizacao", "indice_fonte_oficial", "taxa_racial"]
        cols_evol = [c for c in cols_evol if c in df.columns]
        evolucao = df.groupby("ano_mes")[cols_evol].mean()
        fig, ax = plt.subplots(figsize=(16, 6))
        evolucao.plot(ax=ax, marker="o", linewidth=2)
        ax.set_title("Evolução Temporal dos Índices")
        ax.tick_params(axis="x", rotation=45)
        salvar_grafico(fig, "14_evolucao_temporal")
        salvar_tabela(evolucao, "09_evolucao_temporal")

    # Correlação fontes oficiais x criminalização
    fig, ax = plt.subplots(figsize=(10, 8))
    cores_scatter = df["tipo_veiculo"].map(cores_tipo)
    ax.scatter(df["indice_fonte_oficial"], df["indice_criminalizacao"],
               c=cores_scatter, alpha=0.4, s=30)
    ax.set_xlabel("Dependência de Fontes Oficiais")
    ax.set_ylabel("Índice de Criminalização")
    ax.set_title("Correlação: Fontes Oficiais × Criminalização")
    for tipo, cor in cores_tipo.items():
        ax.scatter([], [], c=cor, label=tipo, s=60)
    ax.legend()
    salvar_grafico(fig, "15_correlacao_fontes_crim")

    return df


# ============================================================================
# CAMADA 4: ANÁLISE DE OMISSÕES
# ============================================================================

def camada4_omissoes(df: pd.DataFrame) -> pd.DataFrame:
    print("\n" + "=" * 60)
    print("CAMADA 4: ANÁLISE DE OMISSÕES")
    print("=" * 60)

    print("\n  Verificando elementos presentes/ausentes em cada matéria...")

    # Para cada elemento esperado, verificar presença
    for elem_key, elem_info in ELEMENTOS_ESPERADOS.items():
        df[f"tem_{elem_key}"] = df["texto"].apply(
            lambda t: 1 if contar_regex(t, elem_info["padroes"]) > 0 else 0
        )

    # Índice de completude (0-1)
    peso_total = sum(e["peso"] for e in ELEMENTOS_ESPERADOS.values())
    df["indice_completude"] = df.apply(
        lambda row: sum(
            row[f"tem_{k}"] * v["peso"]
            for k, v in ELEMENTOS_ESPERADOS.items()
        ) / peso_total,
        axis=1,
    )

    # Gráfico: % de matérias que contêm cada elemento
    presenca = {}
    for elem_key, elem_info in ELEMENTOS_ESPERADOS.items():
        pct = df[f"tem_{elem_key}"].mean() * 100
        presenca[elem_info["descricao"]] = pct

    fig, ax = plt.subplots(figsize=(14, 8))
    presenca_series = pd.Series(presenca).sort_values()
    cores = ["#d73027" if v < 30 else "#fc8d59" if v < 60 else "#4575b4" for v in presenca_series.values]
    presenca_series.plot(kind="barh", ax=ax, color=cores)
    ax.set_title("Presença de Elementos Esperados na Cobertura")
    ax.set_xlabel("% das matérias que contêm o elemento")
    ax.axvline(x=50, color="black", linestyle="--", alpha=0.3, label="50%")
    for i, v in enumerate(presenca_series.values):
        ax.text(v + 0.5, i, f"{v:.1f}%", va="center", fontsize=10)
    salvar_grafico(fig, "16_omissoes_elementos")
    salvar_tabela(presenca_series.to_frame("pct_presenca"), "10_omissoes_elementos")

    # Completude por tipo de veículo
    comp_completude = df.groupby("tipo_veiculo")["indice_completude"].agg(["mean", "median", "std"])
    fig, ax = plt.subplots(figsize=(10, 6))
    tipos = df["tipo_veiculo"].unique()
    cores_tipo = {"Mainstream": "#d73027", "Alternativo": "#4575b4", "Outro/Regional": "#91bfdb"}
    for tipo in tipos:
        dados = df.loc[df["tipo_veiculo"] == tipo, "indice_completude"]
        ax.hist(dados, bins=15, alpha=0.5, label=tipo, color=cores_tipo.get(tipo, "#ccc"))
    ax.set_title("Distribuição do Índice de Completude por Tipo de Veículo")
    ax.set_xlabel("Índice de completude (0 = omite tudo, 1 = cobertura completa)")
    ax.set_ylabel("Número de matérias")
    ax.legend()
    salvar_grafico(fig, "17_completude_por_tipo")
    salvar_tabela(comp_completude, "11_completude_por_tipo")

    # Completude por veículo individual (top 10)
    top_v = df["veiculo"].value_counts().head(10).index
    comp_v = df[df["veiculo"].isin(top_v)].groupby("veiculo")["indice_completude"].mean().sort_values()
    fig, ax = plt.subplots(figsize=(12, 6))
    comp_v.plot(kind="barh", ax=ax, color=sns.color_palette("RdYlBu", len(comp_v)))
    ax.set_title("Índice Médio de Completude por Veículo")
    ax.set_xlabel("Completude média")
    for i, v in enumerate(comp_v.values):
        ax.text(v + 0.01, i, f"{v:.2f}", va="center")
    salvar_grafico(fig, "18_completude_por_veiculo")

    print(f"  Índice médio de completude: {df['indice_completude'].mean():.3f}")
    print(f"  Elemento mais omitido: {presenca_series.idxmin()} ({presenca_series.min():.1f}%)")
    print(f"  Elemento mais presente: {presenca_series.idxmax()} ({presenca_series.max():.1f}%)")

    return df


# ============================================================================
# CAMADA 5: FICHAS POR CASO
# ============================================================================

def camada5_fichas(df: pd.DataFrame):
    print("\n" + "=" * 60)
    print("CAMADA 5: FICHAS CONSOLIDADAS POR CASO")
    print("=" * 60)

    casos_explodidos = df.explode("casos_identificados")
    casos_contagem = casos_explodidos["casos_identificados"].value_counts()
    casos_relevantes = casos_contagem[
        (casos_contagem.index != "Caso não identificado") & (casos_contagem >= 3)
    ].index.tolist()

    if not casos_relevantes:
        print("  Nenhum caso com 3+ matérias identificado.")
        return

    print(f"  Gerando fichas para {len(casos_relevantes)} casos...")
    fichas_resumo = []

    for caso in casos_relevantes:
        mask = casos_explodidos["casos_identificados"] == caso
        subset = casos_explodidos.loc[mask].copy()

        n_materias = len(subset)
        veiculos = subset["veiculo"].unique().tolist()
        tipos_veiculo = subset["tipo_veiculo"].value_counts().to_dict()
        datas = subset["data_publicacao"].dropna()
        primeira_data = datas.min() if not datas.empty else "N/D"
        ultima_data = datas.max() if not datas.empty else "N/D"
        janela_dias = (datas.max() - datas.min()).days if len(datas) > 1 else 0

        indice_crim_medio = subset["indice_criminalizacao"].mean()
        indice_fonte_medio = subset["indice_fonte_oficial"].mean()
        completude_media = subset["indice_completude"].mean() if "indice_completude" in subset.columns else 0
        pct_racial = (subset["texto_n_racial"] > 0).mean() * 100
        sentimento_medio = subset["sentimento_geral"].mean()

        # Evolução temporal do enquadramento
        evolucao_caso = None
        if len(datas) > 1:
            subset_sorted = subset.sort_values("data_publicacao")
            evolucao_caso = subset_sorted[["data_publicacao", "veiculo", "indice_criminalizacao",
                                            "indice_fonte_oficial", "sentimento_geral"]].to_dict("records")

        # Verificar se houve contra-narrativa
        tem_questionamento = (subset["texto_n_quest"] > 0).sum()
        tem_fontes_comunidade = (subset["n_fontes_comunitarias"] > 0).sum()

        ficha = {
            "caso": caso,
            "n_materias": n_materias,
            "veiculos": ", ".join(veiculos),
            "n_veiculos": len(veiculos),
            "tipos_veiculo": json.dumps(tipos_veiculo, ensure_ascii=False),
            "primeira_publicacao": str(primeira_data),
            "ultima_publicacao": str(ultima_data),
            "janela_cobertura_dias": janela_dias,
            "indice_criminalizacao_medio": round(indice_crim_medio, 3),
            "indice_fonte_oficial_medio": round(indice_fonte_medio, 3),
            "completude_media": round(completude_media, 3),
            "pct_marcadores_raciais": round(pct_racial, 1),
            "sentimento_medio": round(sentimento_medio, 3),
            "n_materias_com_questionamento": tem_questionamento,
            "n_materias_com_fontes_comunitarias": tem_fontes_comunidade,
        }
        fichas_resumo.append(ficha)

        # Salvar ficha individual em texto
        ficha_texto = f"""
{'='*60}
FICHA DO CASO: {caso}
{'='*60}

COBERTURA:
  Número de matérias: {n_materias}
  Veículos: {', '.join(veiculos)}
  Primeira publicação: {primeira_data}
  Última publicação: {ultima_data}
  Janela de cobertura: {janela_dias} dias

ENQUADRAMENTO:
  Índice de criminalização: {indice_crim_medio:.3f} (0=humanizante, 1=criminalizante)
  Dependência fontes oficiais: {indice_fonte_medio:.3f}
  Completude da cobertura: {completude_media:.3f}
  % matérias com marcadores raciais: {pct_racial:.1f}%
  Sentimento médio: {sentimento_medio:.3f}

CONTRA-NARRATIVAS:
  Matérias com questionamento da versão oficial: {tem_questionamento}/{n_materias}
  Matérias com fontes comunitárias: {tem_fontes_comunidade}/{n_materias}

TIPOS DE VEÍCULO:
{chr(10).join(f'  {k}: {v}' for k, v in tipos_veiculo.items())}
{'='*60}
"""
        nome_arquivo = re.sub(r'[^\w\s-]', '', caso).strip().replace(' ', '_')[:50]
        with open(os.path.join(DIR_FICHAS, f"ficha_{nome_arquivo}.txt"), "w", encoding="utf-8") as f:
            f.write(ficha_texto)

        # Gráfico de evolução temporal do enquadramento por caso (se houver dados)
        if evolucao_caso and len(evolucao_caso) > 2:
            try:
                ev_df = pd.DataFrame(evolucao_caso)
                ev_df["data_publicacao"] = pd.to_datetime(ev_df["data_publicacao"])
                ev_df = ev_df.sort_values("data_publicacao")

                fig, ax = plt.subplots(figsize=(12, 5))
                ax.plot(ev_df["data_publicacao"], ev_df["indice_criminalizacao"],
                        "o-", color="#d73027", label="Criminalização")
                ax.plot(ev_df["data_publicacao"], ev_df["indice_fonte_oficial"],
                        "s-", color="#4575b4", label="Fontes oficiais")
                ax.set_title(f"Evolução do Enquadramento: {caso}")
                ax.set_ylabel("Índice")
                ax.legend()
                ax.tick_params(axis="x", rotation=30)
                salvar_grafico(fig, f"caso_{nome_arquivo}_evolucao")
            except Exception:
                pass

    # Tabela consolidada de fichas
    df_fichas = pd.DataFrame(fichas_resumo)
    salvar_tabela(df_fichas.set_index("caso"), "12_fichas_consolidadas")
    print(f"  {len(fichas_resumo)} fichas geradas em {DIR_FICHAS}/")


# ============================================================================
# CAMADA 6: PRÉ-CODIFICAÇÃO PARA CODEBOOK
# ============================================================================

def camada6_codebook(df: pd.DataFrame):
    print("\n" + "=" * 60)
    print("CAMADA 6: PRÉ-CODIFICAÇÃO PARA CODEBOOK")
    print("=" * 60)

    codebook = []
    for _, row in df.iterrows():
        # Enquadramento dominante
        if row["indice_criminalizacao"] > 0.6:
            enquadramento = "Predominantemente criminalizante"
        elif row["indice_criminalizacao"] < 0.4:
            enquadramento = "Predominantemente humanizante"
        else:
            enquadramento = "Equilibrado/neutro"

        # Enquadramento episódico vs temático
        tem_dados = row.get("tem_dados_estatisticos", 0)
        tem_historico = row.get("tem_historico_local", 0)
        if tem_dados or tem_historico:
            tipo_enquadramento = "Temático (contextualizado)"
        else:
            tipo_enquadramento = "Episódico (evento isolado)"

        # Tom
        sent = row["sentimento_geral"]
        if sent < -0.3:
            tom = "Muito negativo"
        elif sent < -0.1:
            tom = "Negativo"
        elif sent < 0.1:
            tom = "Neutro"
        else:
            tom = "Empático/solidário"

        # Representação da vítima
        if row["texto_n_hum"] > row["texto_n_crim"] * 2:
            representacao = "Humanizada"
        elif row["texto_n_crim"] > row["texto_n_hum"] * 2:
            representacao = "Desumanizada/criminalizada"
        else:
            representacao = "Mista"

        # Fonte predominante
        if row["n_fontes_oficiais"] > (row["n_fontes_comunitarias"] + row["n_fontes_especializadas"]):
            fonte_predominante = "Oficial (polícia, SSP)"
        elif row["n_fontes_comunitarias"] > row["n_fontes_oficiais"]:
            fonte_predominante = "Comunitária (moradores, familiares)"
        elif row["n_fontes_especializadas"] > row["n_fontes_oficiais"]:
            fonte_predominante = "Especializada (pesquisadores, ONGs)"
        else:
            fonte_predominante = "Equilibrada/Indefinida"

        entrada = {
            "url": row["url"],
            "titulo": row["titulo"],
            "veiculo": row["veiculo"],
            "tipo_veiculo": row["tipo_veiculo"],
            "data_publicacao": str(row["data_publicacao"]),
            "autor": row.get("autor", ""),
            "enquadramento_crim_hum": enquadramento,
            "enquadramento_episodico_tematico": tipo_enquadramento,
            "tom": tom,
            "representacao_vitima": representacao,
            "fonte_predominante": fonte_predominante,
            "tem_marcadores_raciais": "Sim" if row["texto_n_racial"] > 0 else "Não",
            "tem_eufemismos": "Sim" if row["texto_n_euf"] > 0 else "Não",
            "tem_questionamento": "Sim" if row["texto_n_quest"] > 0 else "Não",
            "indice_criminalizacao": round(row["indice_criminalizacao"], 3),
            "indice_fonte_oficial": round(row["indice_fonte_oficial"], 3),
            "indice_completude": round(row.get("indice_completude", 0), 3),
            "sentimento": round(row["sentimento_geral"], 3),
            "n_palavras": row["n_palavras"],
            "REVISAO_MANUAL": "",  # campo para o pesquisador preencher
        }
        codebook.append(entrada)

    df_codebook = pd.DataFrame(codebook)
    caminho_csv = os.path.join(DIR_CODEBOOK, "pre_codificacao.csv")
    caminho_xlsx = os.path.join(DIR_CODEBOOK, "pre_codificacao.xlsx")
    df_codebook.to_csv(caminho_csv, index=False, encoding="utf-8-sig")
    try:
        df_codebook.to_excel(caminho_xlsx, index=False)
    except Exception:
        pass

    print(f"  Pré-codificação gerada: {len(codebook)} matérias")
    print(f"  CSV: {caminho_csv}")
    print(f"  XLSX: {caminho_xlsx}")
    print("  Campo REVISAO_MANUAL disponível para anotações do pesquisador")


# ============================================================================
# CAMADA 7: CLASSIFICADOR DE ENQUADRAMENTO (ML)
# ============================================================================

def camada7_classificador(df: pd.DataFrame) -> pd.DataFrame:
    print("\n" + "=" * 60)
    print("CAMADA 7: CLASSIFICADOR DE ENQUADRAMENTO (ML)")
    print("=" * 60)

    try:
        from sklearn.feature_extraction.text import TfidfVectorizer
        from sklearn.cluster import KMeans
        from sklearn.decomposition import PCA

        print("\n  Criando features TF-IDF...")
        vectorizer = TfidfVectorizer(
            max_features=1000,
            stop_words=None,  # será tratado manualmente
            ngram_range=(1, 2),
            min_df=3,
            max_df=0.95,
        )
        tfidf = vectorizer.fit_transform(df["texto"].fillna(""))

        # Clustering para descobrir padrões de enquadramento
        print("  Executando clustering (K-Means)...")
        n_clusters = min(5, len(df) // 10) if len(df) > 50 else 3
        km = KMeans(n_clusters=n_clusters, random_state=42, n_init=10)
        df["cluster_enquadramento"] = km.fit_predict(tfidf)

        # Palavras características de cada cluster
        feature_names = vectorizer.get_feature_names_out()
        cluster_termos = {}
        for c in range(n_clusters):
            centro = km.cluster_centers_[c]
            top_indices = centro.argsort()[-15:][::-1]
            termos = [feature_names[i] for i in top_indices]
            cluster_termos[f"Cluster {c}"] = ", ".join(termos)

        # Perfil de cada cluster
        perfil_clusters = df.groupby("cluster_enquadramento").agg({
            "indice_criminalizacao": "mean",
            "indice_fonte_oficial": "mean",
            "sentimento_geral": "mean",
            "texto_n_racial": lambda x: (x > 0).mean() * 100,
        }).round(3)
        perfil_clusters.columns = ["Criminalização", "Fontes oficiais", "Sentimento", "% racial"]

        # Nomear clusters com base no perfil
        for c in range(n_clusters):
            crim = perfil_clusters.loc[c, "Criminalização"]
            if crim > 0.6:
                perfil_clusters.loc[c, "Rótulo sugerido"] = "Criminalizante"
            elif crim < 0.4:
                perfil_clusters.loc[c, "Rótulo sugerido"] = "Humanizante"
            else:
                perfil_clusters.loc[c, "Rótulo sugerido"] = "Neutro/Misto"

        salvar_tabela(perfil_clusters, "13_perfil_clusters")

        # PCA para visualização 2D
        pca = PCA(n_components=2, random_state=42)
        coords = pca.fit_transform(tfidf.toarray())

        fig, ax = plt.subplots(figsize=(12, 8))
        scatter = ax.scatter(coords[:, 0], coords[:, 1],
                            c=df["cluster_enquadramento"], cmap="Set1",
                            alpha=0.5, s=20)
        ax.set_title("Clusters de Enquadramento (PCA 2D)")
        ax.set_xlabel("Componente 1")
        ax.set_ylabel("Componente 2")
        plt.colorbar(scatter, label="Cluster")
        salvar_grafico(fig, "19_clusters_enquadramento")

        # Distribuição de clusters por tipo de veículo
        fig, ax = plt.subplots(figsize=(10, 6))
        ct = pd.crosstab(df["tipo_veiculo"], df["cluster_enquadramento"], normalize="index") * 100
        ct.plot(kind="bar", stacked=True, ax=ax, colormap="Set1")
        ax.set_title("Distribuição de Clusters por Tipo de Veículo")
        ax.set_ylabel("% das matérias")
        ax.legend(title="Cluster")
        ax.tick_params(axis="x", rotation=0)
        salvar_grafico(fig, "20_clusters_por_tipo_veiculo")

        print(f"  {n_clusters} clusters identificados")
        print(f"  Termos por cluster:")
        for c, termos in cluster_termos.items():
            print(f"    {c}: {termos[:80]}...")

    except ImportError:
        print("  scikit-learn não disponível. Pulando classificação ML.")

    return df


# ============================================================================
# CAMADA 8: DASHBOARD INTERATIVO
# ============================================================================

def camada8_dashboard(df: pd.DataFrame):
    print("\n" + "=" * 60)
    print("CAMADA 8: DASHBOARD INTERATIVO")
    print("=" * 60)

    try:
        import plotly.graph_objects as go
        from plotly.subplots import make_subplots
        import plotly.express as px

        # --- Página principal do dashboard ---
        fig = make_subplots(
            rows=3, cols=2,
            subplot_titles=(
                "Distribuição Temporal", "Volume por Tipo de Veículo",
                "Criminalização vs Fontes Oficiais", "Completude por Veículo (Top 10)",
                "Sentimento por Trecho", "Presença de Elementos",
            ),
            specs=[
                [{"type": "bar"}, {"type": "pie"}],
                [{"type": "scatter"}, {"type": "bar"}],
                [{"type": "box"}, {"type": "bar"}],
            ],
            vertical_spacing=0.08,
        )

        # 1. Distribuição temporal
        if "ano_mes" in df.columns:
            vol_mensal = df.groupby("ano_mes").size().reset_index(name="quantidade")
            vol_mensal["ano_mes"] = vol_mensal["ano_mes"].astype(str)
            fig.add_trace(go.Bar(x=vol_mensal["ano_mes"], y=vol_mensal["quantidade"],
                                  marker_color="#2c7bb6", name="Matérias/mês"), row=1, col=1)

        # 2. Volume por tipo
        vol_tipo = df["tipo_veiculo"].value_counts()
        fig.add_trace(go.Pie(labels=vol_tipo.index, values=vol_tipo.values,
                              marker=dict(colors=["#d73027", "#4575b4", "#91bfdb"])), row=1, col=2)

        # 3. Scatter criminalização vs fontes
        cores_map = {"Mainstream": "#d73027", "Alternativo": "#4575b4", "Outro/Regional": "#91bfdb"}
        for tipo in df["tipo_veiculo"].unique():
            mask = df["tipo_veiculo"] == tipo
            fig.add_trace(go.Scatter(
                x=df.loc[mask, "indice_fonte_oficial"],
                y=df.loc[mask, "indice_criminalizacao"],
                mode="markers",
                marker=dict(color=cores_map.get(tipo, "#ccc"), size=5, opacity=0.5),
                name=tipo,
                text=df.loc[mask, "titulo"].str[:50],
                hovertemplate="%{text}<br>Fontes: %{x:.2f}<br>Crim: %{y:.2f}",
            ), row=2, col=1)

        # 4. Completude por veículo
        if "indice_completude" in df.columns:
            top_v = df["veiculo"].value_counts().head(10).index
            comp_v = df[df["veiculo"].isin(top_v)].groupby("veiculo")["indice_completude"].mean().sort_values()
            fig.add_trace(go.Bar(x=comp_v.values, y=comp_v.index, orientation="h",
                                  marker_color="#4575b4", name="Completude"), row=2, col=2)

        # 5. Sentimento por trecho
        for col, nome in [("sentimento_titulo", "Título"), ("sentimento_lead", "Lead"),
                           ("sentimento_corpo", "Corpo")]:
            if col in df.columns:
                fig.add_trace(go.Box(y=df[col], name=nome), row=3, col=1)

        # 6. Presença de elementos
        if any(f"tem_{k}" in df.columns for k in ELEMENTOS_ESPERADOS):
            presenca = {}
            for k, v in ELEMENTOS_ESPERADOS.items():
                if f"tem_{k}" in df.columns:
                    presenca[v["descricao"][:30]] = df[f"tem_{k}"].mean() * 100
            presenca_s = pd.Series(presenca).sort_values()
            fig.add_trace(go.Bar(x=presenca_s.values, y=presenca_s.index, orientation="h",
                                  marker_color=["#d73027" if v < 30 else "#fc8d59" if v < 60 else "#4575b4"
                                                  for v in presenca_s.values],
                                  name="% presente"), row=3, col=2)

        fig.update_layout(
            height=1200,
            title_text="Dashboard: Análise de Cobertura de MDIP (2022-2023)",
            showlegend=True,
        )
        caminho_dash = os.path.join(DIR_DASHBOARD, "dashboard_principal.html")
        fig.write_html(caminho_dash)
        print(f"  Dashboard principal: {caminho_dash}")

        # --- Dashboard por caso ---
        casos_explodidos = df.explode("casos_identificados")
        casos_contagem = casos_explodidos["casos_identificados"].value_counts()
        casos_top = casos_contagem[
            (casos_contagem.index != "Caso não identificado") & (casos_contagem >= 3)
        ].head(10)

        if not casos_top.empty:
            fig2 = make_subplots(
                rows=2, cols=2,
                subplot_titles=(
                    "Matérias por Caso", "Criminalização por Caso",
                    "Completude por Caso", "Fontes Oficiais por Caso",
                ),
            )

            # Matérias por caso
            fig2.add_trace(go.Bar(x=casos_top.values, y=casos_top.index, orientation="h",
                                   marker_color="#2c7bb6"), row=1, col=1)

            # Métricas por caso
            for i, (metrica, titulo, cor) in enumerate([
                ("indice_criminalizacao", "Criminalização", "#d73027"),
                ("indice_completude", "Completude", "#4575b4"),
                ("indice_fonte_oficial", "Fontes oficiais", "#fc8d59"),
            ]):
                if metrica in casos_explodidos.columns:
                    dados_caso = casos_explodidos[
                        casos_explodidos["casos_identificados"].isin(casos_top.index)
                    ].groupby("casos_identificados")[metrica].mean().sort_values()
                    r, c = (1, 2) if i == 0 else ((2, 1) if i == 1 else (2, 2))
                    fig2.add_trace(go.Bar(x=dados_caso.values, y=dados_caso.index,
                                           orientation="h", marker_color=cor), row=r, col=c)

            fig2.update_layout(height=800, title_text="Dashboard: Análise por Caso", showlegend=False)
            caminho_casos = os.path.join(DIR_DASHBOARD, "dashboard_casos.html")
            fig2.write_html(caminho_casos)
            print(f"  Dashboard por caso: {caminho_casos}")

        # --- Dashboard de exploração individual ---
        fig3 = px.scatter(
            df,
            x="indice_fonte_oficial",
            y="indice_criminalizacao",
            color="tipo_veiculo",
            size="n_palavras",
            hover_data=["titulo", "veiculo", "data_publicacao"],
            title="Exploração Interativa: Criminalização × Fontes Oficiais",
            labels={
                "indice_fonte_oficial": "Dependência de Fontes Oficiais",
                "indice_criminalizacao": "Índice de Criminalização",
                "tipo_veiculo": "Tipo de Veículo",
                "n_palavras": "Tamanho (palavras)",
            },
            color_discrete_map=cores_map,
        )
        caminho_explora = os.path.join(DIR_DASHBOARD, "dashboard_exploracao.html")
        fig3.write_html(caminho_explora)
        print(f"  Dashboard exploração: {caminho_explora}")

    except ImportError:
        print("  Plotly não disponível. Instalando: pip install plotly")
        print("  Dashboard não gerado.")


# ============================================================================
# CAMADA 9: REDES DE CIRCULAÇÃO
# ============================================================================

def camada9_circulacao(df: pd.DataFrame):
    print("\n" + "=" * 60)
    print("CAMADA 9: REDES DE CIRCULAÇÃO")
    print("=" * 60)

    # Para cada caso, verificar qual veículo publicou primeiro
    casos_explodidos = df.explode("casos_identificados")
    casos_com_volume = casos_explodidos[
        casos_explodidos["casos_identificados"] != "Caso não identificado"
    ]

    if casos_com_volume.empty:
        print("  Sem casos identificados para análise de circulação.")
        return

    # Quem publica primeiro?
    primeiro_por_caso = {}
    for caso in casos_com_volume["casos_identificados"].unique():
        subset = casos_com_volume[casos_com_volume["casos_identificados"] == caso].sort_values("data_publicacao")
        if not subset.empty:
            primeiro = subset.iloc[0]
            primeiro_por_caso[caso] = primeiro["veiculo"]

    if primeiro_por_caso:
        primeiro_contagem = Counter(primeiro_por_caso.values())
        fig, ax = plt.subplots(figsize=(12, 6))
        pc = pd.Series(primeiro_contagem).sort_values(ascending=True)
        pc.plot(kind="barh", ax=ax, color="#2c7bb6")
        ax.set_title("Quem Publica Primeiro? (por caso)")
        ax.set_xlabel("Número de casos em que o veículo publicou primeiro")
        for i, v in enumerate(pc.values):
            ax.text(v + 0.1, i, str(v), va="center")
        salvar_grafico(fig, "21_quem_publica_primeiro")
        salvar_tabela(pc.to_frame("casos_como_primeiro"), "14_primeiro_a_publicar")

    # Tempo médio de resposta por veículo (dias após primeira publicação)
    tempos_resposta = defaultdict(list)
    for caso in casos_com_volume["casos_identificados"].unique():
        subset = casos_com_volume[casos_com_volume["casos_identificados"] == caso].sort_values("data_publicacao")
        if len(subset) > 1:
            primeira_data = subset["data_publicacao"].iloc[0]
            for _, row in subset.iloc[1:].iterrows():
                delta = (row["data_publicacao"] - primeira_data).days
                tempos_resposta[row["veiculo"]].append(delta)

    if tempos_resposta:
        tempo_medio = {v: np.mean(t) for v, t in tempos_resposta.items() if len(t) >= 2}
        if tempo_medio:
            fig, ax = plt.subplots(figsize=(12, 6))
            tm = pd.Series(tempo_medio).sort_values()
            tm.plot(kind="barh", ax=ax, color="#fc8d59")
            ax.set_title("Tempo Médio de Resposta (dias após 1ª publicação)")
            ax.set_xlabel("Dias")
            for i, v in enumerate(tm.values):
                ax.text(v + 0.1, i, f"{v:.1f}d", va="center")
            salvar_grafico(fig, "22_tempo_resposta")
            salvar_tabela(tm.to_frame("dias_media"), "15_tempo_resposta")

    # Similaridade entre matérias do mesmo caso (quem copia quem?)
    print("  Calculando similaridade entre matérias (intertextualidade)...")
    pares_similares = []
    for caso in casos_com_volume["casos_identificados"].unique():
        subset = casos_com_volume[casos_com_volume["casos_identificados"] == caso]
        if len(subset) < 2 or len(subset) > 30:  # limitar para performance
            continue
        textos = subset[["url", "veiculo", "titulo", "texto", "data_publicacao"]].values
        for i in range(len(textos)):
            for j in range(i + 1, len(textos)):
                sim = calcular_similaridade_textos(textos[i][3][:2000], textos[j][3][:2000])
                if sim > 0.3:  # limiar de similaridade
                    pares_similares.append({
                        "caso": caso,
                        "veiculo_1": textos[i][1],
                        "titulo_1": textos[i][2][:60],
                        "data_1": str(textos[i][4]),
                        "veiculo_2": textos[j][1],
                        "titulo_2": textos[j][2][:60],
                        "data_2": str(textos[j][4]),
                        "similaridade": round(sim, 3),
                    })

    if pares_similares:
        df_sim = pd.DataFrame(pares_similares).sort_values("similaridade", ascending=False)
        salvar_tabela(df_sim.head(50).set_index("caso"), "16_pares_similares")
        print(f"  {len(pares_similares)} pares com alta similaridade encontrados")
    else:
        print("  Nenhum par com alta similaridade encontrado")


# ============================================================================
# RELATÓRIO FINAL
# ============================================================================

def gerar_relatorio_final(df: pd.DataFrame):
    com_racial = (df["texto_n_racial"] > 0).sum()

    relatorio = f"""
{'='*70}
RELATÓRIO DE ANÁLISE AVANÇADA — COBERTURA DE MDIP (2022-2023)
Pesquisa: Desinformação e Criminalização Póstuma
Gerado em: {datetime.now().strftime('%Y-%m-%d %H:%M')}
{'='*70}

1. CORPUS
   Matérias analisadas: {len(df)}
   Veículos: {df['veiculo'].nunique()}
   Período: {df['data_publicacao'].min()} a {df['data_publicacao'].max()}
   Palavras (média): {df['n_palavras'].mean():.0f}

2. ENQUADRAMENTO
   Índice criminalização (texto): {df['indice_criminalizacao'].mean():.3f}
   Índice criminalização (título): {df['indice_crim_titulo'].mean():.3f}
   Índice criminalização (lead): {df['indice_crim_lead'].mean():.3f}
   → Títulos tendem a ser {'MAIS' if df['indice_crim_titulo'].mean() > df['indice_criminalizacao'].mean() else 'MENOS'} criminalizantes que o texto completo

3. FONTES
   Dependência fontes oficiais (menções): {df['indice_fonte_oficial'].mean():.3f}
   % espaço textual fontes oficiais: {df['pct_espaco_oficial'].mean():.1f}%
   Fontes comunitárias aparecem em: {(df['n_fontes_comunitarias'] > 0).mean()*100:.1f}% das matérias

4. DIMENSÃO RACIAL
   Matérias com marcadores raciais: {com_racial/len(df)*100:.1f}%

5. OMISSÕES
   Completude média: {df['indice_completude'].mean():.3f}

6. SENTIMENTO
   Título: {df['sentimento_titulo'].mean():.3f}
   Lead: {df['sentimento_lead'].mean():.3f}
   Corpo: {df['sentimento_corpo'].mean():.3f}

7. POR TIPO DE VEÍCULO
"""
    for tipo in ["Mainstream", "Alternativo", "Outro/Regional"]:
        s = df[df["tipo_veiculo"] == tipo]
        if not s.empty:
            relatorio += f"""
   {tipo.upper()} ({len(s)} matérias):
     Criminalização: {s['indice_criminalizacao'].mean():.3f}
     Fontes oficiais: {s['indice_fonte_oficial'].mean():.3f}
     Completude: {s.get('indice_completude', pd.Series([0])).mean():.3f}
     % com marcadores raciais: {(s['texto_n_racial']>0).mean()*100:.1f}%
"""

    relatorio += f"""
{'='*70}
ARQUIVOS GERADOS
  Gráficos: {DIR_GRAFICOS}/
  Tabelas: {DIR_TABELAS}/
  Fichas por caso: {DIR_FICHAS}/
  Pré-codificação: {DIR_CODEBOOK}/
  Dashboards: {DIR_DASHBOARD}/
{'='*70}
"""

    caminho = os.path.join(DIR_ANALISE, "relatorio_analise_avancada.txt")
    with open(caminho, "w", encoding="utf-8") as f:
        f.write(relatorio)
    print(relatorio)


# ============================================================================
# MAIN
# ============================================================================

def main():
    print("=" * 60)
    print("ANÁLISE AVANÇADA — MDIP 2022-2023")
    print("=" * 60)

    if not os.path.exists(CSV_ENTRADA):
        print(f"\nERRO: Arquivo não encontrado: {CSV_ENTRADA}")
        print("Execute primeiro o news_pipeline.py para coletar as matérias.")
        return

    print(f"\nCarregando: {CSV_ENTRADA}")
    df = pd.read_csv(CSV_ENTRADA, encoding="utf-8")
    df["texto"] = df["texto"].fillna("").astype(str)
    df["titulo"] = df["titulo"].fillna("").astype(str)
    df["veiculo"] = df["veiculo"].fillna("Desconhecido").astype(str)
    df["data_publicacao"] = pd.to_datetime(df["data_publicacao"], errors="coerce")
    df = df[df["texto"].str.len() > 100].copy()
    print(f"Matérias válidas: {len(df)}")

    if len(df) == 0:
        print("ERRO: Nenhuma matéria válida.")
        return

    # Executar todas as camadas
    df = descobrir_casos_ner(df)
    df = camada1_mapeamento(df)
    df = camada2_linguagem(df)
    df = camada3_comparativa(df)
    df = camada4_omissoes(df)
    camada5_fichas(df)
    camada6_codebook(df)
    df = camada7_classificador(df)
    camada8_dashboard(df)
    camada9_circulacao(df)

    # Salvar dataset enriquecido
    # Remover colunas com listas (não serializáveis em CSV simples)
    cols_exportar = [c for c in df.columns if not df[c].apply(lambda x: isinstance(x, list)).any()]
    caminho_enriquecido = os.path.join(DIR_ANALISE, "materias_enriquecidas.csv")
    df[cols_exportar].to_csv(caminho_enriquecido, index=False, encoding="utf-8-sig")

    gerar_relatorio_final(df)

    print("\n" + "=" * 60)
    print("ANÁLISE CONCLUÍDA")
    print(f"Resultados em: {DIR_ANALISE}/")
    print("=" * 60)


if __name__ == "__main__":
    main()