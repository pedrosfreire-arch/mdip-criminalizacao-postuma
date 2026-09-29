"""
Pipeline de Coleta e Raspagem de Notícias — MDIP
=================================================
Pesquisa: Desinformação e Criminalização Póstuma
FAAC-UNESP Bauru / FAPESP IC

Etapas:
    1. Descoberta de matérias via múltiplos crawlers (Google News, Wayback Machine)
    2. Deduplicação por URL normalizada
    3. Raspagem de conteúdo via múltiplos scrapers (Trafilatura, Newspaper, Playwright)
    4. Exportação consolidada em CSV

Correções v3:
    - GDELT desativado (API instável para termos em pt-BR)
    - Deduplicação por título removida (O(n²), trava com >4000 matérias)
    - Resolução de URLs do Google News ANTES da raspagem (corrige manchetes desassociadas)
    - Browser Playwright reutilizado entre matérias (reduz tempo de ~28s para ~5-8s)
    - Filtragem de páginas de índice/listagem após resolução de URL
    - OUTPUT_DIR configurável via variável no topo do arquivo

Requisitos:
    pip install newspaper4k trafilatura playwright requests feedparser
    pip install pandas tqdm beautifulsoup4
    playwright install chromium
"""

import csv
import hashlib
import json
import logging
import os
import random
import re
import time
from dataclasses import dataclass, field, asdict
from datetime import datetime, timedelta
from typing import Optional
from urllib.parse import urlparse, urljoin, parse_qs, urlencode, urlunparse

import pandas as pd
import requests
from tqdm import tqdm

# ============================================================================
# CONFIGURAÇÃO
# ============================================================================

DATA_INICIO = "2022-01-01"
DATA_FIM = "2023-12-31"

TERMOS_BUSCA = [
    "morte intervenção policial",
    "morto operação policial",
    "auto de resistência",
    "confronto policial morto",
    "baleado policial",
    "morte ação policial",
    "vítima operação policial",
    "letalidade policial",
    "homicídio decorrente intervenção policial",
    "resistência seguida de morte",
]

VEICULOS_ALVO = {
    "g1":           "g1.globo.com",
    "folha":        "folha.uol.com.br",
    "oglobo":       "oglobo.globo.com",
    "uol":          "noticias.uol.com.br",
    "ponte":        "ponte.org",
    "intercept":    "theintercept.com/brasil",
    "brasil_fato":  "brasildefato.com.br",
    "midia_ninja":  "midianinja.org",
    "fogo_cruzado": "fogocruzado.org.br",
    "agencia_publica": "apublica.org",
    "alma_preta":   "almapreta.com",
}

# Padrões de URL que indicam páginas de índice/listagem (não matérias)
PADROES_PAGINA_INDICE = [
    r"/autor/",
    r"/tag/",
    r"/categoria/",
    r"/editorias/",
    r"/acompanhe/",
    r"/especial/",
    r"folha\.uol\.com\.br/$",
    r"g1\.globo\.com/$",
    r"/busca\?",
    r"/search\?",
]

OUTPUT_DIR = os.path.join(os.path.expanduser("~"), "Downloads", "dados_coletados")
os.makedirs(OUTPUT_DIR, exist_ok=True)

CHECKPOINT_INTERVALO = 500  # salvar progresso a cada N matérias

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.FileHandler(os.path.join(OUTPUT_DIR, "coleta.log"), encoding="utf-8"),
        logging.StreamHandler(),
    ],
)
logger = logging.getLogger(__name__)

DELAY_MIN = 1
DELAY_MAX = 3


# ============================================================================
# MODELO DE DADOS
# ============================================================================

@dataclass
class Materia:
    url: str
    titulo: str = ""
    veiculo: str = ""
    data_publicacao: str = ""
    autor: str = ""
    fonte_descoberta: str = ""
    scraper_utilizado: str = ""
    sucesso_raspagem: bool = False
    texto: str = ""
    observacoes: str = ""
    data_coleta: str = field(default_factory=lambda: datetime.now().isoformat())
    url_original: str = ""  # preserva a URL do Google News antes da resolução


# ============================================================================
# UTILITÁRIOS
# ============================================================================

def esperar():
    time.sleep(random.uniform(DELAY_MIN, DELAY_MAX))


def normalizar_url(url: str) -> str:
    """Remove parâmetros de rastreamento e normaliza a URL para deduplicação."""
    try:
        parsed = urlparse(url)
        # Remover parâmetros comuns de rastreamento
        params_remover = {"utm_source", "utm_medium", "utm_campaign",
                          "utm_content", "utm_term", "oc", "hl", "gl", "ceid"}
        qs = parse_qs(parsed.query)
        qs_limpo = {k: v for k, v in qs.items() if k not in params_remover}
        query_limpa = urlencode(qs_limpo, doseq=True)
        normalizada = urlunparse(parsed._replace(query=query_limpa, fragment=""))
        return normalizada.rstrip("/").lower()
    except Exception:
        return url.lower()


def identificar_veiculo(url: str) -> str:
    """Identifica o veículo a partir do domínio da URL."""
    try:
        dominio = urlparse(url).netloc.lower()
        dominio = dominio.replace("www.", "")
        for nome, d in VEICULOS_ALVO.items():
            if d in dominio or dominio in d:
                return nome
        return dominio
    except Exception:
        return "desconhecido"


def eh_pagina_indice(url: str) -> bool:
    """Verifica se a URL parece ser uma página de índice/listagem, não uma matéria."""
    for padrao in PADROES_PAGINA_INDICE:
        if re.search(padrao, url, re.IGNORECASE):
            return True
    return False


# ============================================================================
# RESOLUÇÃO DE URLs DO GOOGLE NEWS  ← CORREÇÃO PRINCIPAL
# ============================================================================

def resolver_url_google_news(url: str) -> str:
    """
    Resolve o redirect das URLs encurtadas do Google News RSS
    para obter a URL real da matéria antes de passar para os scrapers.

    Sem isso, o scraper cai em páginas de índice do veículo em vez
    da matéria específica, gerando manchetes desassociadas.
    """
    if "news.google.com" not in url:
        return url

    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/120.0.0.0 Safari/537.36"
        )
    }

    try:
        # Primeiro tenta HEAD (mais rápido)
        resp = requests.head(url, allow_redirects=True, timeout=15, headers=headers)
        url_final = resp.url

        # Se ainda for do Google, tenta GET completo
        if "news.google.com" in url_final:
            resp = requests.get(url, allow_redirects=True, timeout=15, headers=headers)
            url_final = resp.url

        # Se após resolução for página de índice, descarta
        if eh_pagina_indice(url_final):
            logger.debug(f"URL resolvida é página de índice, descartando: {url_final}")
            return ""

        logger.debug(f"URL resolvida: {url} -> {url_final}")
        return url_final

    except Exception as e:
        logger.debug(f"Não foi possível resolver URL do Google News: {url} — {e}")
        return url  # retorna original em caso de falha


# ============================================================================
# PLAYWRIGHT — INSTÂNCIA GLOBAL REUTILIZÁVEL  ← CORREÇÃO DE PERFORMANCE
# ============================================================================

_playwright_instance = None
_playwright_browser = None


def iniciar_playwright():
    """Inicia o browser Playwright uma única vez para toda a sessão de raspagem."""
    global _playwright_instance, _playwright_browser
    try:
        from playwright.sync_api import sync_playwright
        _playwright_instance = sync_playwright().start()
        _playwright_browser = _playwright_instance.chromium.launch(
            headless=True,
            args=["--no-sandbox", "--disable-dev-shm-usage"]
        )
        logger.info("Playwright iniciado (instância global).")
    except Exception as e:
        logger.error(f"Falha ao iniciar Playwright: {e}")


def encerrar_playwright():
    """Encerra o browser Playwright ao final da raspagem."""
    global _playwright_instance, _playwright_browser
    try:
        if _playwright_browser:
            _playwright_browser.close()
        if _playwright_instance:
            _playwright_instance.stop()
        logger.info("Playwright encerrado.")
    except Exception as e:
        logger.warning(f"Erro ao encerrar Playwright: {e}")


# ============================================================================
# SCRAPERS
# ============================================================================

def scraper_trafilatura(url: str) -> Optional[dict]:
    """Extrai texto com Trafilatura — mais rápido e de boa qualidade."""
    try:
        import trafilatura

        downloaded = trafilatura.fetch_url(url)
        if not downloaded:
            return None

        texto = trafilatura.extract(
            downloaded,
            include_comments=False,
            include_tables=True,
            no_fallback=False,
            favor_recall=True,
        )
        metadata = trafilatura.extract_metadata(downloaded)

        if texto and len(texto.strip()) > 100:
            return {
                "texto": texto,
                "titulo": metadata.title if metadata else "",
                "autor": metadata.author if metadata else "",
                "data": str(metadata.date) if metadata and metadata.date else "",
                "scraper": "trafilatura",
            }
    except Exception as e:
        logger.debug(f"Trafilatura falhou para {url}: {e}")
    return None


def scraper_newspaper(url: str) -> Optional[dict]:
    """Extrai texto com Newspaper4k — bom fallback."""
    try:
        from newspaper import Article

        artigo = Article(url, language="pt")
        artigo.download()
        artigo.parse()

        if artigo.text and len(artigo.text.strip()) > 100:
            return {
                "texto": artigo.text,
                "titulo": artigo.title or "",
                "autor": ", ".join(artigo.authors) if artigo.authors else "",
                "data": str(artigo.publish_date) if artigo.publish_date else "",
                "scraper": "newspaper4k",
            }
    except Exception as e:
        logger.debug(f"Newspaper falhou para {url}: {e}")
    return None


def scraper_wayback(url: str) -> Optional[dict]:
    """Tenta raspar via Wayback Machine — contorna paywalls de conteúdo arquivado."""
    try:
        import trafilatura

        api_url = f"http://archive.org/wayback/available?url={url}"
        resp = requests.get(api_url, timeout=10)
        data = resp.json()

        snapshot = data.get("archived_snapshots", {}).get("closest", {})
        if not snapshot.get("available"):
            return None

        wayback_url = snapshot["url"]
        downloaded = trafilatura.fetch_url(wayback_url)
        if not downloaded:
            return None

        texto = trafilatura.extract(downloaded, favor_recall=True)
        metadata = trafilatura.extract_metadata(downloaded)

        if texto and len(texto.strip()) > 100:
            return {
                "texto": texto,
                "titulo": metadata.title if metadata else "",
                "autor": metadata.author if metadata else "",
                "data": str(metadata.date) if metadata and metadata.date else "",
                "scraper": "wayback",
            }
    except Exception as e:
        logger.debug(f"Wayback falhou para {url}: {e}")
    return None


def scraper_playwright(url: str) -> Optional[dict]:
    """
    Extrai texto com Playwright — último recurso para sites com JS pesado.
    Usa a instância global do browser (não cria/destrói por matéria).
    """
    global _playwright_browser

    if _playwright_browser is None:
        logger.warning("Browser Playwright não iniciado, pulando.")
        return None

    try:
        import trafilatura

        context = _playwright_browser.new_context(
            user_agent=(
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/120.0.0.0 Safari/537.36"
            ),
            viewport={"width": 1920, "height": 1080},
            locale="pt-BR",
        )

        page = context.new_page()

        # Bloquear recursos pesados desnecessários
        page.route(
            "**/*.{png,jpg,jpeg,gif,svg,woff,woff2,ttf,mp4,webm,ico}",
            lambda route: route.abort(),
        )
        # Bloquear trackers e analytics
        page.route("**/{google-analytics,googletagmanager,facebook,doubleclick}*",
                   lambda route: route.abort())

        page.goto(url, wait_until="domcontentloaded", timeout=30000)
        page.wait_for_timeout(2000)
        page.evaluate("window.scrollTo(0, document.body.scrollHeight / 2)")
        page.wait_for_timeout(500)

        html = page.content()
        titulo_pagina = page.title()
        context.close()  # fecha só o contexto, mantém o browser

        texto = trafilatura.extract(
            html,
            include_comments=False,
            include_tables=True,
            no_fallback=False,
            favor_recall=True,
        )

        if texto and len(texto.strip()) > 100:
            metadata = trafilatura.extract_metadata(html)
            return {
                "texto": texto,
                "titulo": (metadata.title if metadata and metadata.title
                           else titulo_pagina),
                "autor": metadata.author if metadata else "",
                "data": str(metadata.date) if metadata and metadata.date else "",
                "scraper": "playwright+trafilatura",
            }
    except Exception as e:
        logger.debug(f"Playwright falhou para {url}: {e}")
    return None


# ============================================================================
# RASPAGEM ORQUESTRADA
# ============================================================================

def raspar_materia(materia: Materia) -> Materia:
    """
    Tenta raspar uma matéria com múltiplos scrapers em cascata.
    CORREÇÃO: resolve URL do Google News ANTES de tentar qualquer scraper.
    """
    # --- RESOLUÇÃO DE URL (correção principal) ---
    if "news.google.com" in materia.url:
        materia.url_original = materia.url
        url_resolvida = resolver_url_google_news(materia.url)

        if not url_resolvida:
            # URL resolveu para página de índice — descartar
            materia.sucesso_raspagem = False
            materia.observacoes += " | URL resolvida é página de índice — descartada"
            logger.warning(f"Descartada (índice): {materia.url_original}")
            return materia

        materia.url = url_resolvida
        # Atualizar veículo com base na URL real
        materia.veiculo = identificar_veiculo(url_resolvida)

    # --- CASCATA DE SCRAPERS ---
    scrapers = [
        ("trafilatura", scraper_trafilatura),
        ("newspaper4k", scraper_newspaper),
        ("wayback",     scraper_wayback),
        ("playwright",  scraper_playwright),
    ]

    for nome, func in scrapers:
        logger.debug(f"  Tentando {nome} para {materia.url}")
        resultado = func(materia.url)

        if resultado:
            materia.texto = resultado["texto"]
            materia.scraper_utilizado = resultado["scraper"]
            materia.sucesso_raspagem = True

            # Preencher metadados apenas se estavam vazios
            if not materia.titulo and resultado.get("titulo"):
                materia.titulo = resultado["titulo"]
            if not materia.autor and resultado.get("autor"):
                materia.autor = resultado["autor"]
            if not materia.data_publicacao and resultado.get("data"):
                materia.data_publicacao = resultado["data"]

            logger.info(f"  OK ({nome}): {materia.titulo[:70]}...")
            return materia

        esperar()

    materia.sucesso_raspagem = False
    materia.observacoes += " | Todos os scrapers falharam"
    logger.warning(f"  FALHA: {materia.url}")
    return materia


# ============================================================================
# CRAWLERS
# ============================================================================

def crawler_gdelt(termos: list[str], data_inicio: str, data_fim: str) -> list[Materia]:
    """Busca matérias via GDELT Doc 2.0 API."""
    from gdeltdoc import GdeltDoc, Filters

    logger.info("=== Iniciando crawler GDELT ===")
    materias = []

    for termo in tqdm(termos, desc="GDELT"):
        try:
            filtros = Filters(
                keyword=termo,
                start_date=data_inicio.replace("-", ""),
                end_date=data_fim.replace("-", ""),
                country="BR",
            )
            gd = GdeltDoc()
            resultados = gd.article_search(filtros)

            if resultados is not None and not resultados.empty:
                for _, row in resultados.iterrows():
                    url = row.get("url", "")
                    if not url:
                        continue
                    m = Materia(
                        url=url,
                        titulo=row.get("title", ""),
                        veiculo=identificar_veiculo(url),
                        data_publicacao=str(row.get("seendate", "")),
                        fonte_descoberta="GDELT",
                    )
                    materias.append(m)
                logger.info(f"  GDELT '{termo}': {len(resultados)} resultados")
            else:
                logger.info(f"  GDELT '{termo}': 0 resultados")

            esperar()
        except Exception as e:
            logger.warning(f"  GDELT erro para '{termo}': {e}")

    logger.info(f"GDELT total: {len(materias)} matérias")
    return materias


def crawler_google_news(termos: list[str], data_inicio: str, data_fim: str) -> list[Materia]:
    """
    Busca matérias via Google News RSS.
    NOTA: as URLs coletadas aqui são do formato news.google.com/rss/...
    e serão resolvidas para URLs reais na etapa de raspagem.
    """
    try:
        import feedparser
    except ImportError:
        logger.error("feedparser não instalado. Execute: pip install feedparser")
        return []

    logger.info("=== Iniciando crawler Google News ===")
    materias = []

    di = datetime.strptime(data_inicio, "%Y-%m-%d")
    df = datetime.strptime(data_fim, "%Y-%m-%d")
    # Dividir em janelas mensais para contornar limite de resultados
    janelas = []
    atual = di
    while atual < df:
        proximo = min(atual + timedelta(days=30), df)
        janelas.append((atual.strftime("%Y-%m-%d"), proximo.strftime("%Y-%m-%d")))
        atual = proximo + timedelta(days=1)

    for termo in tqdm(termos, desc="Google News"):
        for d_ini, d_fim in janelas:
            try:
                termo_enc = requests.utils.quote(termo)
                # Inclui filtro de data e idioma português
                url_feed = (
                    f"https://news.google.com/rss/search?"
                    f"q={termo_enc}+after:{d_ini}+before:{d_fim}"
                    f"&hl=pt-BR&gl=BR&ceid=BR:pt-419"
                )
                feed = feedparser.parse(url_feed)

                for entry in feed.entries:
                    url = entry.get("link", "")
                    if not url:
                        continue
                    m = Materia(
                        url=url,
                        titulo=entry.get("title", ""),
                        veiculo="",  # será preenchido após resolução da URL
                        data_publicacao=entry.get("published", ""),
                        fonte_descoberta="Google News RSS",
                        url_original=url,
                    )
                    materias.append(m)

                esperar()
            except Exception as e:
                logger.warning(f"  Google News erro '{termo}' ({d_ini}): {e}")

    logger.info(f"Google News total: {len(materias)} matérias (URLs ainda não resolvidas)")
    return materias


def crawler_busca_direta(termos: list[str], veiculos: dict,
                         data_inicio: str, data_fim: str) -> list[Materia]:
    """Busca direta via Google com operador site: para cada veículo."""
    logger.info("=== Iniciando crawler busca direta ===")
    materias = []

    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 Chrome/120.0.0.0 Safari/537.36"
        )
    }

    for veiculo, dominio in veiculos.items():
        for termo in termos:
            try:
                query = f'site:{dominio} "{termo}" after:{data_inicio} before:{data_fim}'
                url_busca = f"https://www.google.com/search?q={requests.utils.quote(query)}&num=20"

                resp = requests.get(url_busca, headers=headers, timeout=15)
                if resp.status_code != 200:
                    esperar()
                    continue

                from bs4 import BeautifulSoup
                soup = BeautifulSoup(resp.text, "html.parser")

                for a in soup.select("a[href]"):
                    href = a["href"]
                    if "/url?q=" in href:
                        url_real = href.split("/url?q=")[1].split("&")[0]
                        url_real = requests.utils.unquote(url_real)
                        if dominio in url_real and not eh_pagina_indice(url_real):
                            m = Materia(
                                url=url_real,
                                titulo="",
                                veiculo=veiculo,
                                fonte_descoberta=f"busca_direta:{veiculo}",
                            )
                            materias.append(m)

                esperar()
            except Exception as e:
                logger.warning(f"  Busca direta erro '{veiculo}/{termo}': {e}")

    logger.info(f"Busca direta total: {len(materias)} matérias")
    return materias


def crawler_wayback_discovery(veiculos: dict, data_inicio: str,
                               data_fim: str) -> list[Materia]:
    """Descobre matérias via CDX API da Wayback Machine."""
    logger.info("=== Iniciando crawler Wayback Machine ===")
    materias = []

    di = data_inicio.replace("-", "")
    df = data_fim.replace("-", "")

    for veiculo, dominio in veiculos.items():
        try:
            cdx_url = (
                f"http://web.archive.org/cdx/search/cdx"
                f"?url={dominio}/*&output=json&fl=original,timestamp,statuscode"
                f"&filter=statuscode:200&from={di}&to={df}&limit=200"
            )
            resp = requests.get(cdx_url, timeout=30)
            if resp.status_code != 200:
                continue

            dados = resp.json()
            if len(dados) <= 1:
                continue

            for linha in dados[1:]:  # pula cabeçalho
                url_orig = linha[0]
                timestamp = linha[1]
                if not eh_pagina_indice(url_orig):
                    data_pub = (f"{timestamp[:4]}-{timestamp[4:6]}-{timestamp[6:8]}"
                                if len(timestamp) >= 8 else "")
                    m = Materia(
                        url=url_orig,
                        veiculo=veiculo,
                        data_publicacao=data_pub,
                        fonte_descoberta="wayback_discovery",
                    )
                    materias.append(m)

            logger.info(f"  Wayback '{veiculo}': {len(dados)-1} URLs")
            esperar()
        except Exception as e:
            logger.warning(f"  Wayback erro para '{veiculo}': {e}")

    logger.info(f"Wayback discovery total: {len(materias)} matérias")
    return materias


# ============================================================================
# DEDUPLICAÇÃO
# ============================================================================

def deduplicar_materias(materias: list[Materia]) -> list[Materia]:
    """
    Deduplica por URL normalizada.
    Deduplicação por título (fuzzy) removida — O(n²), trava com >4000 matérias.
    A dedup por URL já elimina a grande maioria das duplicatas.
    """
    logger.info(f"Deduplicando {len(materias)} matérias...")
    vistas = {}
    unicas = []
    for m in materias:
        chave = normalizar_url(m.url)
        if chave not in vistas:
            vistas[chave] = True
            unicas.append(m)
    logger.info(f"  Resultado: {len(unicas)} matérias únicas")
    return unicas


# ============================================================================
# EXPORTAÇÃO
# ============================================================================

def exportar_csv(materias: list[Materia], nome_arquivo: str):
    caminho = os.path.join(OUTPUT_DIR, nome_arquivo)
    campos = [
        "url", "url_original", "titulo", "veiculo", "data_publicacao", "autor",
        "fonte_descoberta", "scraper_utilizado", "sucesso_raspagem",
        "texto", "observacoes", "data_coleta",
    ]
    with open(caminho, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=campos, extrasaction="ignore")
        writer.writeheader()
        for m in materias:
            writer.writerow(asdict(m))
    logger.info(f"Exportado: {caminho} ({len(materias)} registros)")


def gerar_relatorio(materias: list[Materia]) -> str:
    total = len(materias)
    sucesso = sum(1 for m in materias if m.sucesso_raspagem)
    por_scraper = {}
    por_veiculo = {}

    for m in materias:
        if m.scraper_utilizado:
            por_scraper[m.scraper_utilizado] = por_scraper.get(m.scraper_utilizado, 0) + 1
        if m.veiculo:
            por_veiculo[m.veiculo] = por_veiculo.get(m.veiculo, 0) + 1

    linhas = [
        "=" * 60,
        "RELATÓRIO FINAL DA COLETA",
        "=" * 60,
        f"Total de matérias:        {total}",
        f"Raspagem bem-sucedida:    {sucesso} ({sucesso/total*100:.1f}%)" if total else "",
        f"Falhas:                   {total - sucesso}",
        "",
        "Por scraper:",
        *[f"  {k}: {v}" for k, v in sorted(por_scraper.items(), key=lambda x: -x[1])],
        "",
        "Por veículo (top 15):",
        *[f"  {k}: {v}" for k, v in sorted(por_veiculo.items(),
                                            key=lambda x: -x[1])[:15]],
        "=" * 60,
    ]
    return "\n".join(linhas)


# ============================================================================
# MAIN
# ============================================================================

def main():
    logger.info("=" * 60)
    logger.info("PIPELINE DE COLETA — MDIP v3")
    logger.info(f"Período: {DATA_INICIO} a {DATA_FIM}")
    logger.info(f"Termos de busca: {len(TERMOS_BUSCA)}")
    logger.info(f"Saída: {OUTPUT_DIR}")
    logger.info("=" * 60)

    # -----------------------------------------------------------------------
    # FASE 1: DESCOBERTA
    # -----------------------------------------------------------------------
    logger.info("\n>>> FASE 1: DESCOBERTA DE MATÉRIAS <<<\n")
    todas_materias = []

    # GDELT desativado — API instável para termos em pt-BR
    logger.info("GDELT: desativado nesta versão.")

    try:
        todas_materias.extend(crawler_google_news(TERMOS_BUSCA, DATA_INICIO, DATA_FIM))
    except Exception as e:
        logger.error(f"Google News falhou: {e}")

    # Busca direta desativada — Google bloqueia scraping automatizado
    logger.info("Busca direta: desativada (bloqueio do Google).")

    try:
        todas_materias.extend(
            crawler_wayback_discovery(VEICULOS_ALVO, DATA_INICIO, DATA_FIM)
        )
    except Exception as e:
        logger.error(f"Wayback discovery falhou: {e}")

    if not todas_materias:
        logger.error("Nenhuma matéria encontrada. Encerrando.")
        return

    exportar_csv(todas_materias, "01_materias_brutas.csv")

    # -----------------------------------------------------------------------
    # FASE 2: DEDUPLICAÇÃO
    # -----------------------------------------------------------------------
    logger.info("\n>>> FASE 2: DEDUPLICAÇÃO <<<\n")
    materias_unicas = deduplicar_materias(todas_materias)
    exportar_csv(materias_unicas, "02_materias_deduplicadas.csv")

    # -----------------------------------------------------------------------
    # FASE 3: RASPAGEM
    # -----------------------------------------------------------------------
    logger.info("\n>>> FASE 3: RASPAGEM DE CONTEÚDO <<<\n")
    logger.info(f"Raspando {len(materias_unicas)} matérias...\n")

    # Verificar se há checkpoint de progresso anterior
    checkpoint_path = os.path.join(OUTPUT_DIR, "checkpoint_raspagem.json")
    indice_inicio = 0
    materias_raspadas = []

    if os.path.exists(checkpoint_path):
        with open(checkpoint_path, "r") as f:
            chk = json.load(f)
            indice_inicio = chk.get("ultimo_indice", 0)
            logger.info(f"Retomando do checkpoint: matéria {indice_inicio}")
        # Carregar raspagem parcial se existir
        parcial_path = os.path.join(OUTPUT_DIR, "parcial_raspagem.csv")
        if os.path.exists(parcial_path):
            df_parcial = pd.read_csv(parcial_path)
            for _, row in df_parcial.iterrows():
                m = Materia(**{k: row.get(k, "") for k in Materia.__dataclass_fields__})
                materias_raspadas.append(m)

    # Iniciar Playwright UMA VEZ para toda a sessão
    iniciar_playwright()

    try:
        for i, m in enumerate(
            tqdm(materias_unicas[indice_inicio:],
                 desc="Raspando matérias",
                 initial=indice_inicio,
                 total=len(materias_unicas)),
            start=indice_inicio
        ):
            m_raspada = raspar_materia(m)
            materias_raspadas.append(m_raspada)
            esperar()

            # Checkpoint periódico
            if (i + 1) % CHECKPOINT_INTERVALO == 0:
                exportar_csv(materias_raspadas, "parcial_raspagem.csv")
                with open(checkpoint_path, "w") as f:
                    json.dump({"ultimo_indice": i + 1}, f)
                logger.info(f"  Progresso salvo: {i+1}/{len(materias_unicas)}")

    finally:
        encerrar_playwright()

    # -----------------------------------------------------------------------
    # FASE 4: EXPORTAÇÃO FINAL
    # -----------------------------------------------------------------------
    logger.info("\n>>> FASE 4: EXPORTAÇÃO FINAL <<<\n")
    exportar_csv(materias_raspadas, "03_materias_completas.csv")

    # Limpar checkpoint após conclusão
    if os.path.exists(checkpoint_path):
        os.remove(checkpoint_path)

    relatorio = gerar_relatorio(materias_raspadas)
    logger.info("\n" + relatorio)

    with open(os.path.join(OUTPUT_DIR, "relatorio_coleta.txt"), "w",
              encoding="utf-8") as f:
        f.write(relatorio)


if __name__ == "__main__":
    main()