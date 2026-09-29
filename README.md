# Criminalização póstuma na cobertura de MDIP (2022–2023)

Código da pesquisa de iniciação científica "Desinformação e criminalização póstuma: modelo de análise do enquadramento de vítimas de violência policial" (FAAC/UNESP Bauru, bolsa FAPESP). Orientação: Profa. Dra. Angela Maria Grossi. Autor: Pedro Santos Freire.

O repositório reúne a coleta de notícias sobre mortes decorrentes de intervenção policial (MDIP), a auditoria do corpus, a validação das regras de título e o livro de códigos.

## Arquivos

| Arquivo | Função |
|---|---|
| `news_pipeline.py` | Coleta (Google News RSS, buscas por veículo, Wayback CDX), deduplicação e extração de texto em cascata (Trafilatura → Newspaper4k → Wayback → Playwright). Gera `dados_coletados/`. |
| `auditoria_corpus.py` | Auditoria do corpus (duplicatas, extração por veículo, rotas de entrada), regras de título e amostra estratificada de validação. Gera `auditoria/`. |
| `validacao_titulos_mdip.html` | Ferramenta offline de rotulagem dos 200 títulos da amostra. É só abrir no navegador. |
| `validar_regras.py` | Precisão, sensibilidade, F1 e kappa de Cohen das regras contra a codificação humana, além das estimativas corrigidas para o corpus com IC de 95%. |
| `analise_materias.py`, `analise_avancada.py` | Análises descritivas e de enquadramento do texto integral. |
| `validacao_representatividade.py` | Comparação do corpus com os registros de MDIP. |
| `codebook_mdip.md` | Livro de códigos (módulos A–F). |
| `requirements.txt` | Dependências. |

## Como rodar

Requer Python 3.12.

```
py -3.12 -m pip install -r requirements.txt
py -3.12 news_pipeline.py          # coleta: demora horas
py -3.12 auditoria_corpus.py       # lê 03_materias_completas.csv e 01_materias_brutas.csv na mesma pasta
# abrir validacao_titulos_mdip.html, rotular e exportar o CSV para auditoria/amostra_validacao_titulos.csv
py -3.12 validar_regras.py
```

## Dados

Os CSVs com o texto integral das matérias não são publicados, por causa dos direitos autorais dos veículos. Para reproduzir o corpus, rode a coleta. As regras e a amostra de validação são reproduzíveis com semente fixa (42).

## Licença

MIT. Ao usar, cite o artigo.
