# CODEBOOK — Análise de Enquadramento e Desinformação na Cobertura de MDIP

**Projeto:** Desinformação e Criminalização Póstuma: análise da construção narrativa sobre vítimas de violência policial na mídia brasileira (IC — FAAC/UNESP)

**Versão:** 1.0 (para teste-piloto)

**Fontes de adaptação:**
- ZIEMS & YANG (2021), *Police Violence Frame Corpus* — estrutura de enquadramento centrado em entidades (vítima × policial), frames de questão, estilo linguístico e protocolo de validação
- LIU et al. (2019), *Gun Violence Frame Corpus* — formato de codebook com variáveis, definições e regras aplicadas por anotadores especialistas
- BOYDSTUN et al. (2014) / CARD et al. (2015), *Policy Frames Codebook / Media Frames Corpus* — princípio de dimensões de enquadramento mutuamente exclusivas com regras de decisão
- WARDLE & DERAKHSHAN (2017) — taxonomia da desordem informacional (módulo original deste projeto, sem equivalente nos codebooks-fonte)

---

## 0. INSTRUÇÕES GERAIS

**Unidade de análise:** a matéria jornalística completa (título + linha fina + corpo + legendas de fotos). Codifique cada matéria como um todo, exceto onde a variável indicar trecho específico (ex.: variáveis de título).

**Procedimento:** (1) leia a matéria integralmente antes de codificar qualquer variável; (2) codifique na ordem dos módulos; (3) em caso de dúvida entre dois códigos, consulte a regra de decisão da variável; se a dúvida persistir, use o código de indeterminação (99) e registre no campo de observações.

**Princípio herdado do MFC:** enquadrar é tanto *presença* quanto *ausência*. Várias variáveis pedem que você registre o que a matéria NÃO diz. A omissão é dado, não falta de dado.

**Princípio herdado de Ziems & Yang:** vítima e policial são entidades distintas. Um adjetivo, verbo ou atributo deve ser codificado para a entidade a que se refere sintaticamente — "o policial atirou" e "o suspeito atirou" são registros opostos. Nunca codifique um termo sem verificar de quem ele é predicado.

---

## MÓDULO A — IDENTIFICAÇÃO (variáveis descritivas)

| Var | Nome | Valores |
|---|---|---|
| A1 | ID da matéria | id_estavel do corpus |
| A2 | Veículo | nome padronizado |
| A3 | Tipo de veículo | 1=mainstream nacional; 2=regional/local; 3=alternativo/especializado; 4=agência oficial |
| A4 | Data de publicação | AAAA-MM-DD |
| A5 | Gênero jornalístico | 1=nota curta (<300 palavras); 2=reportagem; 3=coluna/opinião; 4=editorial; 5=entrevista; 99=indeterminado |
| A6 | Autoria | 1=repórter identificado; 2="da redação"/sem assinatura; 3=agência (reproduzido); 99=indeterminado |
| A7 | Caso coberto | nome da vítima ou operação (texto livre) |
| A8 | Dias desde a ocorrência | número inteiro (data de publicação − data da morte) |

**Regra de decisão A6:** matéria assinada por agência (ex.: "com informações do g1") reproduzida em outro veículo = código 3. Isso alimenta a análise de circulação (quem pauta quem).

---

## MÓDULO B — ENQUADRAMENTO DA VÍTIMA (entidade 1)

*Adaptado dos entity frames de Ziems & Yang (age, gender, race, armed, attacking/fleeing, criminality, mental illness), com acréscimos para o contexto brasileiro (território, trabalho/vínculo social). Para cada variável, codifique apenas atributos predicados DA VÍTIMA.*

**B1 — Nomeação da vítima**
Como a vítima é predominantemente designada no texto?
- 1 = Nome próprio completo (humanização máxima)
- 2 = Primeiro nome ou apelido afetivo
- 3 = Categoria social neutra ("jovem", "morador", "homem de 24 anos")
- 4 = Categoria criminalizante ("suspeito", "acusado", "elemento", "traficante", "bandido")
- 5 = Mista — começa criminalizante e humaniza (ou o inverso; registrar direção em observações)
- 99 = Indeterminado
*Regra de decisão:* se o texto usa nome próprio E "suspeito", identifique qual predomina no título e no primeiro parágrafo (peso do lead — cf. ordenação de frames em Ziems & Yang). Termos entre aspas atribuídos a fonte policial NÃO contam como escolha do veículo (ver B8).

**B2 — Idade mencionada?** 0=não; 1=sim
**B3 — Gênero marcado?** 0=não; 1=sim (uso de "jovem", "mãe", "pai" onde alternativa neutra existia)
**B4 — Raça/cor da vítima mencionada?**
- 0 = Não mencionada
- 1 = Mencionada explicitamente ("jovem negro", "homem pardo")
- 2 = Mencionada apenas indiretamente (foto evidencia, texto silencia)
- 99 = Indeterminado
*Nota teórica:* a omissão sistemática do marcador racial é o "segredo público" (French, 2013) e configura malinformation por subtração — este é um dos achados centrais esperados. Ziems & Yang encontraram que fontes liberais mencionam raça 100% mais que conservadoras; a hipótese brasileira é que veículos alternativos mencionem e mainstream omita.

**B5 — Vítima descrita como armada?**
- 0 = Sem menção
- 1 = Armada (afirmação direta)
- 2 = Armada segundo versão policial, sem confirmação independente ("com ele foi encontrada uma pistola")
- 3 = Desarmada (afirmação direta)
- 4 = Versões em disputa (polícia diz armada; testemunhas negam)
*Regra de decisão:* código 2 é central para o projeto — marca a reprodução da versão policial como fato. Se a matéria usa "estava armado" sem atribuição, código 1; com atribuição ("segundo a PM"), código 2.

**B6 — Vítima descrita como atacando ou fugindo?**
- 0 = Sem menção
- 1 = Atacou/reagiu (versão assumida pelo texto)
- 2 = Atacou/reagiu (apenas na versão policial atribuída)
- 3 = Fugia
- 4 = Não reagiu / rendição mencionada
- 5 = Versões em disputa
*Nota:* corresponde aos frames *attacking/fleeing* de Ziems & Yang, que justificam legalmente a força letal. No Brasil, o equivalente funcional é a narrativa do "revide" que fundamenta o auto de resistência.

**B7 — Criminalidade atribuída à vítima**
- 0 = Nenhuma menção
- 1 = Antecedentes/passagens mencionados sem relevância demonstrada para o evento
- 2 = Antecedentes mencionados com vínculo argumentado ao evento
- 3 = Vínculo com facção/tráfico afirmado sem fonte
- 4 = Vínculo com facção/tráfico atribuído a fonte policial
- 5 = Texto nega ou relativiza criminalidade ("não tinha passagens")
*Regra de decisão:* o código 1 é o indicador clássico de criminalização póstuma via malinformation (informação verdadeira instrumentalizada). Registre em observações o trecho literal.

**B8 — Termos criminalizantes: origem**
Quando termos como "suspeito"/"traficante" aparecem, de quem são?
- 0 = Não aparecem
- 1 = Voz do veículo (texto do repórter, sem aspas/atribuição)
- 2 = Somente em citação atribuída a fonte oficial
- 3 = Ambos
*Nota:* distingue a criminalização produzida pelo veículo da reproduzida. Ambas importam, mas são mecanismos diferentes (disinformation institucional vs. amplificação jornalística).

**B9 — Contexto humanizador presente?** (família, trabalho, estudos, sonhos, comunidade)
- 0 = Ausente; 1 = Menção breve (1 frase); 2 = Desenvolvido (parágrafo+)

**B10 — Saúde mental mencionada?** 0=não; 1=sim, como vulnerabilidade (falha do Estado em lidar); 2=sim, como periculosidade ("surtado", "descontrolado")

**B11 — Território da vítima como marcador**
- 0 = Local apenas informativo
- 1 = Território usado como marcador de suspeição ("área dominada pelo tráfico", "reduto de facção")
- 2 = Território contextualizado sociologicamente (histórico de operações, ausência de serviços)
*Nota:* variável sem equivalente em Ziems & Yang — adaptação necessária ao contexto brasileiro, onde a favela opera como dispositivo de criminalização territorial (Caldeira, 2000).

---

## MÓDULO C — ENQUADRAMENTO DO AGENTE POLICIAL (entidade 2)

*Espelho do Módulo B: os mesmos eventos, predicados do policial. Adaptado dos frames de officer e do estilo linguístico (passivas sem agente) de Ziems & Yang.*

**C1 — Nomeação do agente**
- 1 = Policial identificado por nome
- 2 = "Policial"/"PM"/"agente" (individualizado, sem nome)
- 3 = Instituição como agente ("a polícia", "a PM", "equipe do 12º Batalhão")
- 4 = Agente ausente da oração (ver C2)
*Nota:* a progressão 1→4 dilui a responsabilidade individual.

**C2 — Apagamento de agência (voz passiva/construções impessoais)**
A morte é narrada com agente explícito?
- 0 = Agência explícita ("policiais atiraram em X")
- 1 = Passiva com agente ("X foi morto por policiais")
- 2 = Passiva sem agente / impessoal ("X foi baleado", "X acabou morrendo", "houve confronto e X morreu")
- 3 = Morte atribuída a objeto ("o tiro atingiu X", "a bala o atingiu")
*Regra de decisão:* codifique a construção do TÍTULO e a predominante no corpo separadamente (C2a título, C2b corpo). Ziems & Yang mostram que fontes que protegem a polícia usam 61% mais passivas sem agente — este é o teste equivalente brasileiro.

**C3 — Ação policial caracterizada como:**
- 1 = Legítima defesa/revide (assumida pelo texto)
- 2 = Legítima defesa (apenas na versão policial atribuída)
- 3 = Neutra/não caracterizada
- 4 = Questionada (desproporcionalidade, execução, contradições apontadas)
- 99 = Indeterminado

**C4 — Histórico do agente/batalhão mencionado?** (outras mortes, processos, letalidade da unidade) 0=não; 1=sim

**C5 — Consequências para o agente mencionadas?** (afastamento, investigação, prisão) 0=não; 1=sim

---

## MÓDULO D — ENQUADRAMENTO DA QUESTÃO (issue frames)

*Adaptado dos issue frames de Ziems & Yang (systemic, legal, sources, video) e da lógica de frames temáticos do GVFC/MFC.*

**D1 — Enquadramento episódico × temático (Iyengar, 1991)**
- 1 = Episódico puro (evento isolado, sem qualquer contextualização)
- 2 = Predominantemente episódico (menção protocolar a contexto)
- 3 = Predominantemente temático (evento inserido em padrão: dados, histórico, outras mortes)
- 4 = Temático puro (o evento é ilustração de um problema estrutural)
*Regra de decisão:* presença de dados estatísticos (Anuário, Pele Alvo, Fogo Cruzado) ou menção a outras mortes na mesma região/operação = no mínimo código 3. Corresponde ao frame *systemic* de Ziems & Yang.

**D2 — Fontes citadas (marque todas; conte ocorrências)**
- D2a = Oficiais-segurança (PM, PC, SSP, delegado, nota oficial): n
- D2b = Oficiais-justiça (MP, Defensoria, Judiciário): n
- D2c = Comunitárias (familiares, moradores, testemunhas): n
- D2d = Especializadas (pesquisadores, ONGs, observatórios): n
- D2e = Movimentos sociais: n

**D3 — Hierarquia de fontes**
Qual fonte abre a matéria (primeira citada ou parafraseada)?
- 1 = Oficial-segurança; 2 = Oficial-justiça; 3 = Comunitária; 4 = Especializada; 5 = Movimento social; 0 = Nenhuma
*Nota:* Ziems & Yang medem *ordering* dos frames pela pirâmide invertida — a fonte que abre define a moldura de leitura de todo o resto.

**D4 — Contraditório presente?**
A versão policial é confrontada com outra versão no mesmo texto?
- 0 = Só versão policial
- 1 = Outra versão mencionada, subordinada (1 frase ao final)
- 2 = Versões em paridade de espaço
- 3 = Versão não-policial predomina
- 4 = Não se aplica (matéria não trata da dinâmica da morte)

**D5 — Evidência audiovisual mencionada?** (câmera corporal, vídeo de morador, câmera de segurança) 0=não; 1=sim, corrobora versão policial; 2=sim, contradiz versão policial; 3=sim, neutra/indefinida

**D6 — Linguagem jurídica presente?** (inquérito, excludente de ilicitude, auto de resistência como termo técnico, flagrante) 0=não; 1=sim
*Registrar termos em observações.*

---

## MÓDULO E — DESORDEM INFORMACIONAL (Wardle & Derakhshan)

*Módulo original do projeto — sem equivalente nos codebooks-fonte. Codifique apenas quando houver elemento verificável; na dúvida, 99.*

**E1 — Tipo de informação problemática presente (marque todas):**
- E1a = Misinformation: erro factual sem intenção aparente (nome errado, local errado) — 0/1
- E1b = Disinformation: elemento comprovadamente fabricado reproduzido (flagrante forjado, arma plantada — exige que fato posterior tenha desmentido) — 0/1
- E1c = Malinformation: informação verdadeira instrumentalizada (antecedentes irrelevantes, foto descontextualizada da vítima) — 0/1
- E1d = Descontextualização: omissão de elemento crucial já público à época (testemunho existente não citado, contradição pericial ignorada) — 0/1
*Regra de decisão E1b/E1d:* exigem conhecimento do desenrolar do caso. Codifique em segunda passada, após montar a ficha do caso (o pipeline gera fichas por caso justamente para isso).

**E2 — Eufemismos institucionais reproduzidos sem aspas/problematização** ("confronto", "troca de tiros", "auto de resistência", "intervenção"): contar ocorrências; registrar termos.

**E3 — A matéria corrige/atualiza versão anterior?** 0=não; 1=sim, corrige a própria cobertura; 2=sim, noticia queda da versão policial (perícia, MP, vídeo)

---

## MÓDULO F — SÍNTESE AVALIATIVA (preencher por último)

**F1 — Enquadramento dominante geral**
- 1 = Legitimador (a ação policial aparece justificada)
- 2 = Neutro-protocolar (registro burocrático da ocorrência)
- 3 = Questionador (a ação policial aparece problematizada)
- 99 = Indeterminado

**F2 — Representação dominante da vítima:** 1=humanizada; 2=neutra; 3=criminalizada; 4=mista

**F3 — Grau de completude** (checklist: nome, idade, contexto familiar, versão de testemunhas, versão da família, circunstâncias, histórico do local, dados estatísticos, marcador racial, acompanhamento judicial — somar itens presentes, 0–10)

**F4 — Observações** (texto livre: trechos literais que fundamentam códigos críticos — B7=1, C2=2/3, E1)

---

## PROTOCOLO DE CONFIABILIDADE

*Adaptado da validação de Ziems & Yang (50 artigos rotulados à mão contra o sistema automático) e do padrão MFC.*

1. **Teste-piloto:** 2 codificadores codificam independentemente 20 matérias sorteadas (estratificadas por tipo de veículo). Calcular Alfa de Krippendorff por variável.
2. **Referências de qualidade:** α ≥ 0,80 confiável; 0,67–0,80 aceitável para conclusões tentativas. O MFC — anotado por especialistas — alcançou ICR de 0,60; variáveis de enquadramento abaixo de 0,67 não indicam fracasso, mas exigem reescrita da definição e novo piloto.
3. **Variáveis críticas** (B1, B5, B7, C2, D1, F1): se α < 0,67 após segunda rodada, transformar categorias em binárias (presença/ausência) — a literatura mostra que granularidade menor eleva a concordância.
4. **Validação do sistema automático:** após estabilizar a codificação manual, comparar as 20 matérias com a pré-codificação do pipeline (precision/recall por variável, como na Tabela 5 de Ziems & Yang). Reportar na dissertação. Isto também valida o conjunto de treino do BERTimbau.
5. **Dupla passada para o Módulo E:** codificar E1b/E1d somente com a ficha do caso montada (conhecimento do desfecho).

## FLUXO DE APLICAÇÃO

1. Pipeline gera pré-codificação automática (campo REVISAO_MANUAL vazio)
2. Codificador lê a matéria e confirma/corrige cada módulo (mais rápido que codificar do zero; registrar discordâncias com o automático — elas são o dado de validação)
3. Piloto de confiabilidade (20 matérias, 2 codificadores) → ajuste do codebook → versão 2.0
4. Codificação do corpus completo
5. Módulo E em segunda passada, por caso
6. Exportar para treino do BERTimbau (labels de F1/F2)
