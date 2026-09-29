#!/usr/bin/env python3
"""
Análise de Matérias sobre Mortes Decorrentes de Intervenção Policial
====================================================================
Pesquisa: Desinformação e Criminalização Póstuma (IC - UNESP/FAAC)

Este script realiza três camadas de análise:
1. Mapeamento do corpus (volume, distribuição, casos mais cobertos)
2. Análise de linguagem (termos criminalizantes, fontes, marcadores raciais)
3. Análise comparativa (veículos, perfis de vítima, padrões temporais)

Requisitos:
    pip install pandas matplotlib seaborn spacy nltk wordcloud openpyxl
    python -m spacy download pt_core_news_lg

Uso:
    python analise_materias.py

Entrada: CSV gerado pelo news_pipeline.py (04_materias_raspadas_sucesso.csv)
Saída: Gráficos, tabelas e relatório em dados_coletados/analise/
"""

import os
import re
import json
import warnings
from collections import Counter, defaultdict
from datetime import datetime

import pandas as pd
import matplotlib
matplotlib.use("Agg")  # backend não-interativo para salvar gráficos
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
import seaborn as sns
from wordcloud import WordCloud

warnings.filterwarnings("ignore")

# Configuração de estilo dos gráficos
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

# Caminho do CSV de entrada (gerado pelo pipeline de coleta)
CSV_ENTRADA = os.path.join("dados_coletados", "04_materias_raspadas_sucesso.csv")

# Diretório de saída para análises
DIR_ANALISE = os.path.join("dados_coletados", "analise")
os.makedirs(DIR_ANALISE, exist_ok=True)

# Subdiretórios
DIR_GRAFICOS = os.path.join(DIR_ANALISE, "graficos")
DIR_TABELAS = os.path.join(DIR_ANALISE, "tabelas")
os.makedirs(DIR_GRAFICOS, exist_ok=True)
os.makedirs(DIR_TABELAS, exist_ok=True)


# ============================================================================
# DICIONÁRIOS DE ANÁLISE
# ============================================================================

# Termos criminalizantes — associam a vítima a criminalidade
TERMOS_CRIMINALIZANTES = [
    "bandido", "bandidos", "criminoso", "criminosos", "criminosa",
    "traficante", "traficantes", "suspeito", "suspeitos", "suspeita",
    "elemento", "elementos", "meliante", "meliantes",
    "marginal", "marginais", "delinquente", "delinquentes",
    "foragido", "foragidos", "foragida",
    "infrator", "infratores", "infratora",
    "comparsa", "comparsas",
    "facção", "facções", "fação",
    "envolvido com o tráfico", "envolvido com o crime",
    "ligação com o tráfico", "ligado ao tráfico",
    "antecedentes criminais", "passagem pela polícia",
    "ficha criminal", "ficha suja",
    "anotações criminais",
]

# Termos humanizantes — apresentam a vítima como pessoa
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

# Eufemismos institucionais — linguagem que naturaliza a violência
EUFEMISMOS = [
    "auto de resistência",
    "resistência seguida de morte",
    "confronto", "confrontos",
    "troca de tiros", "troca de disparos",
    "revide", "revidaram",
    "reagiu à abordagem", "reagiram à abordagem",
    "ação policial resultou",
    "incidente", "ocorrência",
    "intervenção", "intervenções",
    "legítima defesa",
    "excludente de ilicitude",
]

# Termos que questionam a versão oficial
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

# Marcadores de fontes
FONTES_OFICIAIS = [
    "segundo a polícia", "de acordo com a polícia",
    "a polícia informou", "a polícia disse", "a polícia afirmou",
    "segundo a pm", "de acordo com a pm",
    "a pm informou", "a pm disse", "a pm afirmou",
    "segundo a ssp", "de acordo com a ssp",
    "secretaria de segurança", "secretaria de segurança pública",
    "segundo o delegado", "delegado informou", "delegado disse",
    "segundo a delegacia", "de acordo com a delegacia",
    "boletim de ocorrência", "registro policial",
    "nota oficial", "nota da polícia", "nota da pm",
    "comunicado da polícia", "comunicado oficial",
    "porta-voz da polícia", "porta-voz da pm",
    "comando da pm", "comando da polícia",
    "batalhão", "bope", "core",
]

FONTES_COMUNITARIAS = [
    "moradores relatam", "moradores dizem", "moradores afirmam",
    "moradores contam", "moradores denunciam",
    "familiares dizem", "familiares relatam", "familiares afirmam",
    "familiares contam", "familiares denunciam",
    "segundo familiares", "de acordo com familiares",
    "segundo moradores", "de acordo com moradores",
    "testemunhas", "testemunha",
    "vizinhos relatam", "vizinhos dizem",
    "mãe da vítima", "pai da vítima", "família da vítima",
    "amigos da vítima", "amigos relatam",
]

FONTES_ESPECIALIZADAS = [
    "pesquisador", "pesquisadora", "pesquisadores",
    "especialista", "especialistas",
    "professor", "professora",
    "universidade", "estudo", "pesquisa",
    "observatório", "fórum brasileiro de segurança",
    "instituto", "ong", "organização",
    "defensor público", "defensoria",
    "direitos humanos",
    "anistia internacional", "amnistia",
    "human rights watch",
]

# Marcadores raciais
MARCADORES_RACIAIS = [
    "negro", "negra", "negros", "negras",
    "preto", "preta", "pretos", "pretas",
    "pardo", "parda", "pardos", "pardas",
    "branco", "branca", "brancos", "brancas",
    "afrodescendente", "afro-brasileiro",
    "racismo", "racial", "raciais",
    "cor da pele", "cor de pele",
    "genocídio", "genocídio negro",
    "racismo estrutural", "racismo institucional",
]

# Classificação de veículos
VEICULOS_MAINSTREAM = ["G1", "O Globo", "Folha de S.Paulo", "Estadão", "UOL", "R7",
                        "CNN Brasil", "O Globo / Globo", "Terra"]
VEICULOS_ALTERNATIVOS = ["Ponte Jornalismo", "The Intercept Brasil", "Brasil de Fato",
                          "Mídia NINJA", "CartaCapital", "Fogo Cruzado"]


# ============================================================================
# FUNÇÕES AUXILIARES
# ============================================================================

def contar_ocorrencias(texto: str, termos: list[str]) -> dict[str, int]:
    """Conta ocorrências de cada termo no texto (case-insensitive)."""
    texto_lower = texto.lower()
    contagem = {}
    for termo in termos:
        n = texto_lower.count(termo.lower())
        if n > 0:
            contagem[termo] = n
    return contagem


def contar_total(texto: str, termos: list[str]) -> int:
    """Conta total de ocorrências de todos os termos no texto."""
    return sum(contar_ocorrencias(texto, termos).values())


def classificar_veiculo(nome: str) -> str:
    """Classifica veículo como mainstream, alternativo ou outro."""
    if nome in VEICULOS_MAINSTREAM:
        return "Mainstream"
    elif nome in VEICULOS_ALTERNATIVOS:
        return "Alternativo"
    else:
        return "Outro/Regional"


def extrair_casos_mencionados(texto: str, titulo: str) -> list[str]:
    """
    Tenta extrair nomes de vítimas ou operações mencionadas.
    Usa heurísticas baseadas em padrões comuns na cobertura.
    """
    casos = []
    texto_completo = f"{titulo} {texto}".lower()

    # Casos emblemáticos conhecidos de 2022-2023
    casos_conhecidos = {
        "genivaldo": "Genivaldo de Jesus Santos",
        "vila cruzeiro": "Operação Vila Cruzeiro",
        "complexo do alemão": "Operação Complexo do Alemão",
        "jacarezinho": "Operação Jacarezinho",
        "guarapari": "Chacina de Guarapari",
        "kathlen romeu": "Kathlen Romeu",
        "durval teófilo": "Durval Teófilo",
        "ágatha félix": "Ágatha Félix",
        "paraisópolis": "Paraisópolis",
        "favela do muquiço": "Favela do Muquiço",
        "complexo da penha": "Complexo da Penha",
        "cidade de deus": "Cidade de Deus",
        "maré": "Complexo da Maré",
        "salgueiro": "Complexo do Salgueiro",
        "batista neves": "Operação Batista Neves",
        "rio das pedras": "Rio das Pedras",
        "cyrano": "Operação Cyrano",
    }

    for chave, nome_caso in casos_conhecidos.items():
        if chave in texto_completo:
            casos.append(nome_caso)

    return casos if casos else ["Caso não identificado"]


def salvar_grafico(fig, nome: str):
    """Salva gráfico no diretório de gráficos."""
    caminho = os.path.join(DIR_GRAFICOS, f"{nome}.png")
    fig.savefig(caminho, bbox_inches="tight", facecolor="white")
    plt.close(fig)
    print(f"  Gráfico salvo: {caminho}")


def salvar_tabela(df: pd.DataFrame, nome: str):
    """Salva tabela em CSV e Excel."""
    caminho_csv = os.path.join(DIR_TABELAS, f"{nome}.csv")
    caminho_xlsx = os.path.join(DIR_TABELAS, f"{nome}.xlsx")
    df.to_csv(caminho_csv, index=True, encoding="utf-8-sig")
    try:
        df.to_excel(caminho_xlsx, index=True)
    except Exception:
        pass  # se openpyxl não estiver instalado
    print(f"  Tabela salva: {caminho_csv}")


# ============================================================================
# CAMADA 1: MAPEAMENTO DO CORPUS
# ============================================================================

def camada1_mapeamento(df: pd.DataFrame) -> pd.DataFrame:
    """
    Mapeamento geral do corpus coletado.
    Responde: o que temos? quais casos? quais veículos? qual distribuição?
    """
    print("\n" + "=" * 60)
    print("CAMADA 1: MAPEAMENTO DO CORPUS")
    print("=" * 60)

    # --- 1.1 Estatísticas gerais ---
    print(f"\n  Total de matérias: {len(df)}")
    print(f"  Veículos distintos: {df['veiculo'].nunique()}")
    print(f"  Período: {df['data_publicacao'].min()} a {df['data_publicacao'].max()}")
    print(f"  Tamanho médio do texto: {df['texto'].str.len().mean():.0f} caracteres")

    # --- 1.2 Volume por veículo ---
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

    # --- 1.3 Distribuição temporal (por mês) ---
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

    # --- 1.4 Volume por tipo de veículo (mainstream vs alternativo) ---
    df["tipo_veiculo"] = df["veiculo"].apply(classificar_veiculo)
    vol_tipo = df["tipo_veiculo"].value_counts()

    fig, axes = plt.subplots(1, 2, figsize=(14, 6))
    # Pizza
    vol_tipo.plot(kind="pie", ax=axes[0], autopct="%1.1f%%",
                  colors=["#d73027", "#4575b4", "#91bfdb"])
    axes[0].set_title("Proporção por Tipo de Veículo")
    axes[0].set_ylabel("")
    # Barras por tipo ao longo do tempo
    pivot_tipo = df.groupby(["ano_mes", "tipo_veiculo"]).size().unstack(fill_value=0)
    pivot_tipo.plot(kind="bar", stacked=True, ax=axes[1],
                    color=["#4575b4", "#d73027", "#91bfdb"])
    axes[1].set_title("Cobertura por Tipo de Veículo ao Longo do Tempo")
    axes[1].set_xlabel("Mês")
    axes[1].set_ylabel("Matérias")
    axes[1].tick_params(axis="x", rotation=45)
    axes[1].legend(title="Tipo")
    fig.tight_layout()
    salvar_grafico(fig, "03_tipo_veiculo")

    # --- 1.5 Casos mais cobertos ---
    df["casos_mencionados"] = df.apply(
        lambda row: extrair_casos_mencionados(row["texto"], row["titulo"]), axis=1
    )
    # Explodir para contar cada caso separadamente
    casos_explodidos = df.explode("casos_mencionados")
    casos_contagem = casos_explodidos["casos_mencionados"].value_counts()
    # Remover "Caso não identificado" para o gráfico
    casos_identificados = casos_contagem[casos_contagem.index != "Caso não identificado"]

    if not casos_identificados.empty:
        fig, ax = plt.subplots(figsize=(14, 8))
        casos_identificados.head(15).plot(
            kind="barh", ax=ax, color=sns.color_palette("rocket", 15)
        )
        ax.set_title("Casos Mais Cobertos pela Mídia")
        ax.set_xlabel("Número de matérias")
        ax.invert_yaxis()
        for i, v in enumerate(casos_identificados.head(15).values):
            ax.text(v + 0.3, i, str(v), va="center", fontsize=10)
        salvar_grafico(fig, "04_casos_mais_cobertos")
        salvar_tabela(casos_contagem.to_frame("quantidade"), "04_casos_mais_cobertos")

    # --- 1.6 Dias de cobertura por caso ---
    # Para cada caso identificado, calcular janela de cobertura
    if not casos_identificados.empty:
        janelas = []
        for caso in casos_identificados.head(10).index:
            mask = casos_explodidos["casos_mencionados"] == caso
            datas = casos_explodidos.loc[mask, "data_publicacao"].dropna()
            if len(datas) > 1:
                janela = (datas.max() - datas.min()).days
                janelas.append({"caso": caso, "dias_cobertura": janela,
                                "n_materias": len(datas)})
        if janelas:
            df_janelas = pd.DataFrame(janelas)
            salvar_tabela(df_janelas.set_index("caso"), "05_janela_cobertura_por_caso")

    return df


# ============================================================================
# CAMADA 2: ANÁLISE DE LINGUAGEM
# ============================================================================

def camada2_linguagem(df: pd.DataFrame) -> pd.DataFrame:
    """
    Análise de padrões linguísticos nas matérias.
    Identifica termos criminalizantes, humanizantes, eufemismos,
    fontes citadas e presença de marcadores raciais.
    """
    print("\n" + "=" * 60)
    print("CAMADA 2: ANÁLISE DE LINGUAGEM")
    print("=" * 60)

    # --- 2.1 Contagem de termos por matéria ---
    print("\n  Processando termos em cada matéria...")

    df["n_criminalizantes"] = df["texto"].apply(lambda t: contar_total(t, TERMOS_CRIMINALIZANTES))
    df["n_humanizantes"] = df["texto"].apply(lambda t: contar_total(t, TERMOS_HUMANIZANTES))
    df["n_eufemismos"] = df["texto"].apply(lambda t: contar_total(t, EUFEMISMOS))
    df["n_questionamento"] = df["texto"].apply(lambda t: contar_total(t, TERMOS_QUESTIONAMENTO))
    df["n_fontes_oficiais"] = df["texto"].apply(lambda t: contar_total(t, FONTES_OFICIAIS))
    df["n_fontes_comunitarias"] = df["texto"].apply(lambda t: contar_total(t, FONTES_COMUNITARIAS))
    df["n_fontes_especializadas"] = df["texto"].apply(lambda t: contar_total(t, FONTES_ESPECIALIZADAS))
    df["n_marcadores_raciais"] = df["texto"].apply(lambda t: contar_total(t, MARCADORES_RACIAIS))

    # Normalizar pelo tamanho do texto (por 1000 palavras)
    df["n_palavras"] = df["texto"].apply(lambda t: len(t.split()))
    for col in ["n_criminalizantes", "n_humanizantes", "n_eufemismos", "n_questionamento",
                 "n_fontes_oficiais", "n_fontes_comunitarias", "n_fontes_especializadas",
                 "n_marcadores_raciais"]:
        col_norm = col.replace("n_", "taxa_")
        df[col_norm] = (df[col] / df["n_palavras"] * 1000).fillna(0)

    # Índice de criminalização: razão criminalizantes / (criminalizantes + humanizantes)
    df["indice_criminalizacao"] = df.apply(
        lambda row: row["n_criminalizantes"] / (row["n_criminalizantes"] + row["n_humanizantes"])
        if (row["n_criminalizantes"] + row["n_humanizantes"]) > 0 else 0.5,
        axis=1,
    )

    # Índice de dependência de fontes oficiais
    df["indice_fonte_oficial"] = df.apply(
        lambda row: row["n_fontes_oficiais"] / (row["n_fontes_oficiais"] + row["n_fontes_comunitarias"] + row["n_fontes_especializadas"])
        if (row["n_fontes_oficiais"] + row["n_fontes_comunitarias"] + row["n_fontes_especializadas"]) > 0 else 0.5,
        axis=1,
    )

    # --- 2.2 Gráfico: termos mais frequentes ---
    # Criminalizantes
    todos_crim = Counter()
    for texto in df["texto"]:
        todos_crim.update(contar_ocorrencias(texto, TERMOS_CRIMINALIZANTES))
    
    if todos_crim:
        fig, axes = plt.subplots(1, 2, figsize=(18, 8))
        
        crim_df = pd.Series(dict(todos_crim.most_common(15)))
        crim_df.plot(kind="barh", ax=axes[0], color="#d73027")
        axes[0].set_title("Termos Criminalizantes Mais Frequentes")
        axes[0].invert_yaxis()
        
        # Humanizantes
        todos_hum = Counter()
        for texto in df["texto"]:
            todos_hum.update(contar_ocorrencias(texto, TERMOS_HUMANIZANTES))
        hum_df = pd.Series(dict(todos_hum.most_common(15)))
        hum_df.plot(kind="barh", ax=axes[1], color="#4575b4")
        axes[1].set_title("Termos Humanizantes Mais Frequentes")
        axes[1].invert_yaxis()
        
        fig.tight_layout()
        salvar_grafico(fig, "06_termos_criminalizantes_vs_humanizantes")

    # --- 2.3 Gráfico: eufemismos ---
    todos_euf = Counter()
    for texto in df["texto"]:
        todos_euf.update(contar_ocorrencias(texto, EUFEMISMOS))
    
    if todos_euf:
        fig, ax = plt.subplots(figsize=(14, 6))
        euf_df = pd.Series(dict(todos_euf.most_common(15)))
        euf_df.plot(kind="barh", ax=ax, color="#fc8d59")
        ax.set_title("Eufemismos Institucionais Mais Frequentes")
        ax.invert_yaxis()
        salvar_grafico(fig, "07_eufemismos")

    # --- 2.4 Gráfico: distribuição de fontes ---
    fontes_resumo = {
        "Fontes oficiais\n(polícia, SSP, delegados)": df["n_fontes_oficiais"].sum(),
        "Fontes comunitárias\n(moradores, familiares)": df["n_fontes_comunitarias"].sum(),
        "Fontes especializadas\n(pesquisadores, ONGs)": df["n_fontes_especializadas"].sum(),
    }
    fig, ax = plt.subplots(figsize=(10, 6))
    cores = ["#d73027", "#4575b4", "#91bfdb"]
    bars = ax.bar(fontes_resumo.keys(), fontes_resumo.values(), color=cores)
    ax.set_title("Distribuição de Fontes Citadas no Corpus")
    ax.set_ylabel("Total de menções")
    for bar, val in zip(bars, fontes_resumo.values()):
        ax.text(bar.get_x() + bar.get_width() / 2, bar.get_height() + 5,
                str(val), ha="center", fontsize=12, fontweight="bold")
    salvar_grafico(fig, "08_distribuicao_fontes")

    # --- 2.5 Marcadores raciais ---
    com_racial = (df["n_marcadores_raciais"] > 0).sum()
    sem_racial = (df["n_marcadores_raciais"] == 0).sum()
    
    fig, axes = plt.subplots(1, 2, figsize=(14, 6))
    axes[0].pie([com_racial, sem_racial],
                labels=[f"Com marcador racial\n({com_racial})",
                        f"Sem marcador racial\n({sem_racial})"],
                autopct="%1.1f%%", colors=["#4575b4", "#fee090"])
    axes[0].set_title("Presença de Marcadores Raciais nas Matérias")

    # Quais marcadores aparecem
    todos_racial = Counter()
    for texto in df["texto"]:
        todos_racial.update(contar_ocorrencias(texto, MARCADORES_RACIAIS))
    if todos_racial:
        racial_df = pd.Series(dict(todos_racial.most_common(10)))
        racial_df.plot(kind="barh", ax=axes[1], color="#4575b4")
        axes[1].set_title("Marcadores Raciais Mais Frequentes")
        axes[1].invert_yaxis()
    fig.tight_layout()
    salvar_grafico(fig, "09_marcadores_raciais")

    # --- 2.6 Distribuição do índice de criminalização ---
    fig, ax = plt.subplots(figsize=(12, 6))
    df["indice_criminalizacao"].hist(ax=ax, bins=20, color="#d73027", alpha=0.7, edgecolor="white")
    ax.axvline(x=0.5, color="black", linestyle="--", label="Equilíbrio (0.5)")
    ax.axvline(x=df["indice_criminalizacao"].mean(), color="blue", linestyle="-",
               label=f"Média ({df['indice_criminalizacao'].mean():.2f})")
    ax.set_title("Distribuição do Índice de Criminalização")
    ax.set_xlabel("Índice (0 = totalmente humanizante, 1 = totalmente criminalizante)")
    ax.set_ylabel("Número de matérias")
    ax.legend()
    salvar_grafico(fig, "10_indice_criminalizacao_distribuicao")

    # --- 2.7 Nuvem de palavras ---
    try:
        # Stopwords em português
        stopwords_pt = set([
            "de", "a", "o", "que", "e", "do", "da", "em", "um", "para", "é",
            "com", "não", "uma", "os", "no", "se", "na", "por", "mais", "as",
            "dos", "como", "mas", "foi", "ao", "ele", "das", "tem", "à", "seu",
            "sua", "ou", "ser", "quando", "muito", "há", "nos", "já", "está",
            "eu", "também", "só", "pelo", "pela", "até", "isso", "ela", "entre",
            "era", "depois", "sem", "mesmo", "aos", "ter", "seus", "quem",
            "nas", "me", "esse", "eles", "estão", "você", "tinha", "foram",
            "essa", "num", "nem", "suas", "meu", "às", "minha", "têm", "numa",
            "pelos", "elas", "havia", "seja", "qual", "será", "nós", "tenho",
            "lhe", "deles", "essas", "esses", "pelas", "este", "fosse", "dele",
            "tu", "te", "vocês", "vos", "lhes", "meus", "minhas", "teu", "tua",
            "teus", "tuas", "nosso", "nossa", "nossos", "nossas", "dela", "delas",
            "esta", "estes", "estas", "aquele", "aquela", "aqueles", "aquelas",
            "isto", "aquilo", "estou", "está", "estamos", "estão", "estive",
            "disse", "sobre", "ainda", "anos", "dia", "onde", "dois", "três",
            "pode", "segundo", "acordo", "ser", "ter", "fazer", "cada",
        ])

        todo_texto = " ".join(df["texto"].dropna().tolist())
        wc = WordCloud(
            width=1600, height=800,
            background_color="white",
            stopwords=stopwords_pt,
            max_words=150,
            colormap="RdBu_r",
        ).generate(todo_texto)
        
        fig, ax = plt.subplots(figsize=(16, 8))
        ax.imshow(wc, interpolation="bilinear")
        ax.axis("off")
        ax.set_title("Nuvem de Palavras do Corpus", fontsize=16)
        salvar_grafico(fig, "11_nuvem_palavras")
    except Exception as e:
        print(f"  Nuvem de palavras falhou: {e}")

    # --- 2.8 Tabela resumo linguístico ---
    resumo_ling = pd.DataFrame({
        "Métrica": [
            "Média de termos criminalizantes por matéria",
            "Média de termos humanizantes por matéria",
            "Média de eufemismos por matéria",
            "Média de menções a fontes oficiais",
            "Média de menções a fontes comunitárias",
            "Média de menções a fontes especializadas",
            "% matérias com marcadores raciais",
            "Índice médio de criminalização",
            "Índice médio de dependência de fontes oficiais",
        ],
        "Valor": [
            f"{df['n_criminalizantes'].mean():.2f}",
            f"{df['n_humanizantes'].mean():.2f}",
            f"{df['n_eufemismos'].mean():.2f}",
            f"{df['n_fontes_oficiais'].mean():.2f}",
            f"{df['n_fontes_comunitarias'].mean():.2f}",
            f"{df['n_fontes_especializadas'].mean():.2f}",
            f"{com_racial / len(df) * 100:.1f}%",
            f"{df['indice_criminalizacao'].mean():.3f}",
            f"{df['indice_fonte_oficial'].mean():.3f}",
        ],
    })
    salvar_tabela(resumo_ling.set_index("Métrica"), "06_resumo_linguistico")
    print("\n  Resumo linguístico:")
    print(resumo_ling.to_string(index=False))

    return df


# ============================================================================
# CAMADA 3: ANÁLISE COMPARATIVA
# ============================================================================

def camada3_comparativa(df: pd.DataFrame) -> pd.DataFrame:
    """
    Comparações sistemáticas entre:
    - Veículos mainstream vs. alternativos
    - Casos com diferentes perfis
    - Padrões temporais de enquadramento
    """
    print("\n" + "=" * 60)
    print("CAMADA 3: ANÁLISE COMPARATIVA")
    print("=" * 60)

    # --- 3.1 Mainstream vs. Alternativo: índices linguísticos ---
    metricas_comparacao = [
        "indice_criminalizacao", "indice_fonte_oficial",
        "taxa_criminalizantes", "taxa_humanizantes",
        "taxa_eufemismos", "taxa_questionamento",
        "taxa_marcadores_raciais",
    ]
    
    labels_metricas = {
        "indice_criminalizacao": "Índice de\ncriminalização",
        "indice_fonte_oficial": "Dependência de\nfontes oficiais",
        "taxa_criminalizantes": "Taxa de termos\ncriminalizantes",
        "taxa_humanizantes": "Taxa de termos\nhumanizantes",
        "taxa_eufemismos": "Taxa de\neufemismos",
        "taxa_questionamento": "Taxa de\nquestionamento",
        "taxa_marcadores_raciais": "Taxa de marcadores\nraciais",
    }

    comparacao = df.groupby("tipo_veiculo")[metricas_comparacao].mean()
    salvar_tabela(comparacao, "07_comparacao_tipo_veiculo")

    fig, axes = plt.subplots(2, 4, figsize=(20, 10))
    axes = axes.flatten()
    cores_tipo = {"Mainstream": "#d73027", "Alternativo": "#4575b4", "Outro/Regional": "#91bfdb"}

    for i, metrica in enumerate(metricas_comparacao):
        if i < len(axes):
            dados_box = [df.loc[df["tipo_veiculo"] == tipo, metrica].dropna()
                         for tipo in ["Mainstream", "Alternativo", "Outro/Regional"]
                         if tipo in df["tipo_veiculo"].values]
            labels_box = [tipo for tipo in ["Mainstream", "Alternativo", "Outro/Regional"]
                          if tipo in df["tipo_veiculo"].values]
            bp = axes[i].boxplot(dados_box, labels=labels_box, patch_artist=True)
            for patch, tipo in zip(bp["boxes"], labels_box):
                patch.set_facecolor(cores_tipo.get(tipo, "#cccccc"))
                patch.set_alpha(0.7)
            axes[i].set_title(labels_metricas.get(metrica, metrica), fontsize=10)
            axes[i].tick_params(axis="x", rotation=30)

    # Esconder eixo extra
    if len(metricas_comparacao) < len(axes):
        for j in range(len(metricas_comparacao), len(axes)):
            axes[j].set_visible(False)

    fig.suptitle("Comparação Linguística: Mainstream vs. Alternativo", fontsize=14, y=1.02)
    fig.tight_layout()
    salvar_grafico(fig, "12_comparacao_mainstream_alternativo")

    # --- 3.2 Top veículos individuais comparados ---
    top_veiculos = df["veiculo"].value_counts().head(8).index.tolist()
    if top_veiculos:
        comp_veiculo = df[df["veiculo"].isin(top_veiculos)].groupby("veiculo")[
            ["indice_criminalizacao", "indice_fonte_oficial", "taxa_eufemismos",
             "taxa_questionamento", "taxa_marcadores_raciais"]
        ].mean()

        fig, ax = plt.subplots(figsize=(14, 8))
        comp_veiculo.plot(kind="barh", ax=ax, width=0.8)
        ax.set_title("Perfil Linguístico por Veículo (Top 8)")
        ax.set_xlabel("Valor médio")
        ax.legend(title="Métrica", bbox_to_anchor=(1.05, 1), loc="upper left")
        fig.tight_layout()
        salvar_grafico(fig, "13_perfil_linguistico_por_veiculo")
        salvar_tabela(comp_veiculo, "08_perfil_linguistico_por_veiculo")

    # --- 3.3 Evolução temporal dos índices ---
    if "ano_mes" in df.columns:
        evolucao = df.groupby("ano_mes")[
            ["indice_criminalizacao", "indice_fonte_oficial", "taxa_marcadores_raciais"]
        ].mean()

        fig, ax = plt.subplots(figsize=(16, 6))
        evolucao.plot(ax=ax, marker="o", linewidth=2)
        ax.set_title("Evolução Temporal dos Índices de Enquadramento")
        ax.set_xlabel("Mês")
        ax.set_ylabel("Valor médio")
        ax.legend(["Criminalização", "Dependência fontes oficiais", "Marcadores raciais"])
        ax.tick_params(axis="x", rotation=45)
        salvar_grafico(fig, "14_evolucao_temporal_indices")
        salvar_tabela(evolucao, "09_evolucao_temporal_indices")

    # --- 3.4 Comparação por caso (se houver casos identificados) ---
    if "casos_mencionados" in df.columns:
        casos_explodidos = df.explode("casos_mencionados")
        casos_com_volume = (
            casos_explodidos.groupby("casos_mencionados")
            .filter(lambda x: len(x) >= 5 and x.name != "Caso não identificado")
        )

        if not casos_com_volume.empty:
            comp_caso = casos_com_volume.groupby("casos_mencionados")[
                ["indice_criminalizacao", "indice_fonte_oficial",
                 "taxa_eufemismos", "taxa_marcadores_raciais"]
            ].mean()

            fig, ax = plt.subplots(figsize=(14, 8))
            comp_caso.plot(kind="barh", ax=ax, width=0.8)
            ax.set_title("Perfil de Enquadramento por Caso")
            ax.set_xlabel("Valor médio")
            ax.legend(title="Métrica", bbox_to_anchor=(1.05, 1), loc="upper left")
            fig.tight_layout()
            salvar_grafico(fig, "15_perfil_por_caso")
            salvar_tabela(comp_caso, "10_perfil_enquadramento_por_caso")

    # --- 3.5 Heatmap: veículo × métrica ---
    if top_veiculos:
        fig, ax = plt.subplots(figsize=(12, 8))
        dados_heat = df[df["veiculo"].isin(top_veiculos)].groupby("veiculo")[
            ["taxa_criminalizantes", "taxa_humanizantes", "taxa_eufemismos",
             "taxa_questionamento", "taxa_fontes_oficiais", "taxa_fontes_comunitarias",
             "taxa_marcadores_raciais"]
        ].mean()

        # Renomear colunas para o gráfico
        dados_heat.columns = [
            "Criminalizantes", "Humanizantes", "Eufemismos",
            "Questionamento", "Fontes oficiais", "Fontes comunitárias",
            "Marcadores raciais",
        ]

        sns.heatmap(dados_heat, annot=True, fmt=".2f", cmap="RdYlBu_r",
                    ax=ax, linewidths=0.5, center=dados_heat.values.mean())
        ax.set_title("Heatmap: Perfil Linguístico por Veículo\n(ocorrências por 1000 palavras)")
        fig.tight_layout()
        salvar_grafico(fig, "16_heatmap_veiculo_metrica")

    # --- 3.6 Correlação entre criminalização e uso de fontes oficiais ---
    fig, ax = plt.subplots(figsize=(10, 8))
    cores_scatter = df["tipo_veiculo"].map(cores_tipo)
    ax.scatter(df["indice_fonte_oficial"], df["indice_criminalizacao"],
               c=cores_scatter, alpha=0.4, s=30)
    ax.set_xlabel("Índice de Dependência de Fontes Oficiais")
    ax.set_ylabel("Índice de Criminalização")
    ax.set_title("Correlação: Dependência de Fontes Oficiais × Criminalização")
    # Legenda manual
    for tipo, cor in cores_tipo.items():
        ax.scatter([], [], c=cor, label=tipo, s=60)
    ax.legend()
    salvar_grafico(fig, "17_correlacao_fontes_criminalizacao")

    return df


# ============================================================================
# RELATÓRIO FINAL
# ============================================================================

def gerar_relatorio_analise(df: pd.DataFrame):
    """Gera relatório textual consolidado da análise."""
    
    com_racial = (df["n_marcadores_raciais"] > 0).sum()

    relatorio = f"""
{'='*70}
RELATÓRIO DE ANÁLISE — COBERTURA DE MDIP (2022-2023)
Pesquisa: Desinformação e Criminalização Póstuma
Gerado em: {datetime.now().strftime('%Y-%m-%d %H:%M')}
{'='*70}

1. VISÃO GERAL DO CORPUS
   Total de matérias analisadas: {len(df)}
   Veículos distintos: {df['veiculo'].nunique()}
   Período coberto: {df['data_publicacao'].min()} a {df['data_publicacao'].max()}
   Tamanho médio dos textos: {df['texto'].str.len().mean():.0f} caracteres
   Número médio de palavras: {df['n_palavras'].mean():.0f}

2. PADRÕES LINGUÍSTICOS
   Média de termos criminalizantes por matéria: {df['n_criminalizantes'].mean():.2f}
   Média de termos humanizantes por matéria: {df['n_humanizantes'].mean():.2f}
   Média de eufemismos por matéria: {df['n_eufemismos'].mean():.2f}
   Índice médio de criminalização: {df['indice_criminalizacao'].mean():.3f}
     (0 = totalmente humanizante, 1 = totalmente criminalizante)

3. FONTES
   Média de menções a fontes oficiais: {df['n_fontes_oficiais'].mean():.2f}
   Média de menções a fontes comunitárias: {df['n_fontes_comunitarias'].mean():.2f}
   Média de menções a fontes especializadas: {df['n_fontes_especializadas'].mean():.2f}
   Índice médio de dependência oficial: {df['indice_fonte_oficial'].mean():.3f}
     (0 = nenhuma fonte oficial, 1 = apenas fontes oficiais)

4. DIMENSÃO RACIAL
   Matérias com marcadores raciais: {com_racial} ({com_racial/len(df)*100:.1f}%)
   Matérias sem marcadores raciais: {len(df) - com_racial} ({(len(df)-com_racial)/len(df)*100:.1f}%)

5. COMPARAÇÃO POR TIPO DE VEÍCULO
"""
    for tipo in ["Mainstream", "Alternativo", "Outro/Regional"]:
        subset = df[df["tipo_veiculo"] == tipo]
        if not subset.empty:
            relatorio += f"""
   {tipo.upper()} ({len(subset)} matérias):
     Índice de criminalização: {subset['indice_criminalizacao'].mean():.3f}
     Dependência fontes oficiais: {subset['indice_fonte_oficial'].mean():.3f}
     Taxa de eufemismos (por 1000 palavras): {subset['taxa_eufemismos'].mean():.2f}
     Taxa de questionamento (por 1000 palavras): {subset['taxa_questionamento'].mean():.2f}
     % com marcadores raciais: {(subset['n_marcadores_raciais']>0).mean()*100:.1f}%
"""

    relatorio += f"""
{'='*70}
ARQUIVOS GERADOS
  Gráficos: {DIR_GRAFICOS}/
  Tabelas: {DIR_TABELAS}/
  Este relatório: {os.path.join(DIR_ANALISE, 'relatorio_analise.txt')}
  Dados enriquecidos: {os.path.join(DIR_ANALISE, 'materias_com_indices.csv')}
{'='*70}
"""

    # Salvar relatório
    caminho = os.path.join(DIR_ANALISE, "relatorio_analise.txt")
    with open(caminho, "w", encoding="utf-8") as f:
        f.write(relatorio)
    print(relatorio)


# ============================================================================
# MAIN
# ============================================================================

def main():
    """Executa pipeline completo de análise."""

    print("=" * 60)
    print("ANÁLISE DE MATÉRIAS — MDIP 2022-2023")
    print("=" * 60)

    # --- Carregar dados ---
    if not os.path.exists(CSV_ENTRADA):
        print(f"\nERRO: Arquivo não encontrado: {CSV_ENTRADA}")
        print("Execute primeiro o news_pipeline.py para coletar as matérias.")
        print("Ou ajuste a variável CSV_ENTRADA no topo deste script.")
        return

    print(f"\nCarregando dados de: {CSV_ENTRADA}")
    df = pd.read_csv(CSV_ENTRADA, encoding="utf-8")

    # Limpar e preparar
    df["texto"] = df["texto"].fillna("").astype(str)
    df["titulo"] = df["titulo"].fillna("").astype(str)
    df["veiculo"] = df["veiculo"].fillna("Desconhecido").astype(str)

    # Converter datas
    df["data_publicacao"] = pd.to_datetime(df["data_publicacao"], errors="coerce")

    # Filtrar matérias com texto válido
    df = df[df["texto"].str.len() > 100].copy()
    print(f"Matérias com texto válido: {len(df)}")

    if len(df) == 0:
        print("ERRO: Nenhuma matéria com texto válido encontrada.")
        return

    # --- Executar camadas de análise ---
    df = camada1_mapeamento(df)
    df = camada2_linguagem(df)
    df = camada3_comparativa(df)

    # --- Salvar dataset enriquecido ---
    caminho_enriquecido = os.path.join(DIR_ANALISE, "materias_com_indices.csv")
    df.to_csv(caminho_enriquecido, index=False, encoding="utf-8-sig")
    print(f"\nDataset enriquecido salvo: {caminho_enriquecido}")

    # --- Relatório final ---
    gerar_relatorio_analise(df)

    print("\n" + "=" * 60)
    print("ANÁLISE CONCLUÍDA")
    print(f"Resultados em: {DIR_ANALISE}/")
    print("=" * 60)


if __name__ == "__main__":
    main() 