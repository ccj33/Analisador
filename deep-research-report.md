# Arquitetura de referência para um analisador de editais inspirado em Harvey e Enter

## Conclusão da pesquisa

Depois de confrontar a especificação proposta com o que **Harvey**, **Enter**, **TypeSafe/Jev**, padrões formais de representação de regras jurídicas e literatura sobre raciocínio com informação incompleta publicam, minha conclusão é:

**a correção que você propôs — adicionar um `Constraint Graph` e um solver determinístico acima dos requisitos atômicos — não é apenas uma melhoria. Ela deveria ser tratada como parte central da arquitetura.**

A arquitetura anterior resolvia muito bem:

> “O que o edital diz?”

Mas ainda deixava parcialmente para o LLM resolver, em tempo de pergunta:

> “Como todas essas coisas se combinam para produzir uma conclusão?”

É justamente nessa segunda pergunta que surgem erros perigosos.

Harvey revelou em setembro de 2026 que sua primeira geração de Playbook Review também sofria quando regras eram tratadas isoladamente: contexto se perdia entre chamadas, regras podiam produzir sugestões contraditórias e dependências entre diferentes trechos do documento podiam escapar. A empresa migrou para uma arquitetura de orquestrador + agentes especializados, na qual cada agente examina uma regra, navega por diferentes partes do documento e um agente principal reconcilia os resultados. citeturn21view0turn21view1

Isso valida o diagnóstico. Minha recomendação, entretanto, é ir **um passo além para editais**: depois de a IA descobrir essas relações, elas devem deixar de existir somente como “raciocínio de agente” e passar a existir como **objetos explícitos, persistentes, verificáveis e executáveis no banco**.

A arquitetura definitiva, portanto, não deveria ser:

```text
documentos
   ↓
requisitos
   ↓
LLM decide se a empresa atende
```

Nem apenas:

```text
documentos
   ↓
requisitos
   ↓
multiagentes
   ↓
LLM reconcilia tudo
```

Eu faria:

```text
DOCUMENTOS ORIGINAIS
        │
        ▼
CANONICAL DOCUMENT GRAPH
        │
        ▼
NORMATIVE DISCOVERY
        │
        ├───────────── requisitos atômicos
        ├───────────── definições
        ├───────────── escopos
        ├───────────── exceções
        ├───────────── precedências
        └───────────── relações lógicas
        │
        ▼
VERIFIED NORMATIVE GRAPH
        │
        ▼
CONSTRAINT GRAPH / DECISION GRAPH
        │
        │
        ├──────── ORGANIZATION FACT GRAPH
        │
        └──────── PROJECT FACT GRAPH
        │
        ▼
DETERMINISTIC SOLVER
        │
        ├── SATISFIED
        ├── UNSATISFIED
        ├── UNKNOWN
        ├── CONFLICT
        └── NOT_APPLICABLE
        │
        ▼
EXPLANATION LLM
        │
        ▼
resposta + fontes + condições faltantes
```

O padrão jurídico LegalRuleML da OASIS reforça exatamente a necessidade de representar mais do que frases isoladas: ele prevê relações entre regra e disposição textual, obrigações, permissões, proibições, negação, temporalidade, jurisdição, condições, proveniência e regras derrotáveis/exceções. Também admite relação muitos-para-muitos entre texto normativo e regras formalizadas. citeturn16view0turn17view1

**Eu não implementaria LegalRuleML em XML diretamente.** Seria complexidade demais para o produto. Mas copiaria vários conceitos dele para nossa representação interna.

Essa mudança transforma seu produto de um “analisador inteligente de PDFs” em algo mais interessante:

> **um compilador de editais para uma representação normativa computável.**

E é isso que eu construiria.

## O que Harvey e Enter realmente ensinam

A parte mais importante da pesquisa é separar o que sabemos de fato sobre essas empresas do que estamos inferindo.

### Harvey mostra como construir a infraestrutura documental

Em julho de 2026, a Harvey publicou detalhes incomuns de sua infraestrutura. Segundo a empresa, uma semana recente processou **24,8 milhões de documentos e 56 TB de arquivos**, comparados a 0,94 milhão de documentos um ano antes. Cada documento passa por etapas distintas de extração/OCR, estruturação, chunking/embeddings e indexação; as etapas foram separadas porque possuem gargalos, erros e requisitos de escala diferentes. citeturn20view0

Mais importante para nós, a Harvey abandonou uma representação documental monolítica em favor de um **Unified Document Format, UDF**, uma representação interna versionada e composta por partes tipadas. Assim, sistemas downstream podem acessar separadamente texto de páginas, tabelas, imagens ou outros elementos sem carregar um objeto documental gigantesco. citeturn20view0

Isso é praticamente obrigatório para seu produto.

Um edital não deveria virar:

```json
{
  "text": "1. OBJETO ... 180 páginas depois ..."
}
```

Deveria virar algo como:

```json
{
  "document_id": "doc_0193",
  "version": 3,
  "elements": [
    {
      "id": "elm_001",
      "type": "heading",
      "page": 4,
      "text": "5. Elegibilidade"
    },
    {
      "id": "elm_002",
      "type": "paragraph",
      "page": 4,
      "section_path": ["5", "5.1"],
      "text": "Poderão participar..."
    },
    {
      "id": "elm_003",
      "type": "table",
      "page": 5,
      "cells": [...]
    }
  ]
}
```

E **cada elemento precisa de ID permanente**.

A nova arquitetura multiagente do Playbook Review da Harvey usa exatamente esse princípio: componentes do documento recebem identificadores únicos para que agentes possam apontar de maneira inequívoca para aquilo que leram ou editaram. Os agentes trabalham paralelamente por regra; o orquestrador depois reconcilia os resultados. citeturn21view1

### Harvey também confirma que “um prompt grande” não é a solução

A versão antiga do Playbook Review já era relativamente sofisticada. Não era simplesmente ChatGPT + contrato. Havia uma cadeia fixa de chamadas para classificação, recuperação de evidências e produção da resposta.

Mesmo assim, segundo a própria Harvey, apareceram problemas de perda de contexto, dependências entre parágrafos e conflitos entre regras analisadas isoladamente. Isso motivou a mudança de arquitetura, não apenas uma mudança de prompt. citeturn21view0

A conclusão para seu sistema é forte:

**nem mesmo um pipeline de prompts bem projetado deveria ser a autoridade final sobre elegibilidade.**

O LLM deve descobrir a estrutura.

Depois, o código executa a estrutura.

### Review Tables dá outra pista importante

Harvey permite analisar até milhares de documentos em forma tabular. No produto descrito pela empresa, cada célula é sua própria chamada de modelo, e uma tabela pode provocar centenas de milhares de chamadas. A resposta de cada célula pode incluir raciocínio e citações à fonte. citeturn21view2

Mais importante, a Harvey considera uma resposta de qualidade aquela que:

1. encontrou a parte certa do documento;
2. respondeu corretamente **ou se absteve quando deveria**;
3. respeitou o schema;
4. apresentou a evidência correta.

Para datas, números e aderência ao schema, parte da avaliação pode ser determinística; a qualidade das citações é avaliada em precisão e recall. citeturn21view3

Eu copiaria essa filosofia quase literalmente.

No seu sistema:

```text
"Não sei"
```

precisa ser uma resposta de primeira classe, não um fracasso.

### Enter mostra como transformar leitura massiva em infraestrutura operacional

A Enter publica uma visão complementar.

Sua plataforma declara coletar dados de tribunais, ERPs e outros sistemas, estruturar as informações dos processos em uma base, cruzá-las com outras evidências e executar dezenas de verificações específicas antes ou durante o trabalho jurídico. A empresa afirma ainda exigir revisão e validação humana dos insights produzidos por IA. citeturn22view0

No case SulAmérica, a Enter afirma ter lido e estruturado mais de **500 mil documentos em 30 mil processos**, criando um banco de dados que posteriormente é cruzado com os documentos de cada processo para apoiar a defesa. Esses números são publicados pela própria fornecedora e, portanto, devem ser entendidos como dados de case da Enter, não como auditoria independente. citeturn22view1

O blog de engenharia também é revelador: antes de uma análise com LLM, os casos são validados; jobs pesados rodam de forma assíncrona; o processamento é dividido em fases; a etapa cara é paralelizada; artefatos são persistidos em S3 e o estado da execução em PostgreSQL. citeturn21view4

Essa combinação leva a um princípio que manteria como constituição do projeto:

> **LLM é um trabalhador da pipeline. Não é a pipeline, não é o banco e não é a autoridade de estado do sistema.**

### O sinal dos usuários é coerente com isso

Relatos públicos em comunidades como r/legaltech devem ser tratados como anedóticos, não como benchmark. Ainda assim, há usuários relatando inconsistência de resultados jurídicos mesmo com ferramentas especializadas, incluindo respostas diferentes para o mesmo arquivo e prompt. Isso reforça — sem provar por si só — a necessidade de avaliações, persistência intermediária e mecanismos determinísticos em vez de depender da geração final de um modelo. citeturn17view3

Ou seja, construir “nosso Harvey para editais” não significa achar um prompt melhor.

Significa construir a infraestrutura que **limita o que a IA pode esquecer, inventar ou resolver silenciosamente**.

## A camada lógica definitiva

Sua proposta de `Constraint Graph` está certa, mas minha pesquisa sugere ampliá-la um pouco.

Eu separaria **quatro grafos conceituais**, ainda que todos possam inicialmente morar no PostgreSQL.

### Source Document Graph

Representa o que fisicamente existe.

```text
PACKAGE
│
├─ Edital.pdf
│  ├─ página 1
│  ├─ página 2
│  │  ├─ heading
│  │  ├─ paragraph
│  │  └─ table
│  └─ ...
│
├─ Anexo-I.docx
├─ Cronograma.xlsx
├─ Retificação-01.pdf
└─ FAQ.pdf
```

Nada jurídico ainda.

Ele responde:

> “Onde está essa informação?”

### Normative Graph

Representa **o que o edital está dizendo**.

Por exemplo:

```text
REQ-001
predicate:
organization.country == "BR"

modality:
ELIGIBILITY_CONDITION

subject:
PROPONENT

source:
doc_1 / elm_882
```

Outro:

```text
REQ-002
predicate:
organization.legal_nature == "PUBLIC"

modality:
ELIGIBILITY_CONDITION

subject:
PROPONENT

source:
doc_1 / elm_3972
```

E então:

```text
GROUP-001
operator: ALL

members:
REQ-001
REQ-002
```

É precisamente aqui que sua correção entra.

Mas não limitaria esse grafo a `AND/OR`.

O LegalRuleML foi criado justamente porque regras normativas reais incluem exceções, temporalidade, modalidades como obrigação/proibição/permissão, prioridades e relações entre norma e texto. citeturn17view1

Nosso DSL deveria conseguir expressar:

```text
ALL
ANY
NOT

IF
THEN
IFF
IMPLIES

UNLESS
EXCEPT_IF

ONE_OF
EXACTLY_ONE

AT_LEAST_N
AT_MOST_N
EXACTLY_N

FOR_ALL
EXISTS

GT
GTE
LT
LTE
EQ
NEQ

IN
NOT_IN
BETWEEN

SUM
COUNT
PERCENTAGE
```

Isso é importante porque edital contém coisas como:

> “No mínimo dois pesquisadores deverão possuir doutorado.”

Isso não é um simples AND.

É:

```text
COUNT(
    project.members
    WHERE degree == "PHD"
) >= 2
```

Ou:

> “As despesas com serviços de terceiros não poderão superar 30% do valor solicitado.”

```text
SUM(budget.third_party)
/
SUM(budget.requested)
<= 0.30
```

Ou:

> “Deverá haver pelo menos uma ICT entre as instituições parceiras.”

```text
EXISTS(
    project.partners,
    partner.type == ICT
)
```

Isso transforma seu solver em algo realmente útil.

### Fact Graph

Aqui entra outra das suas melhores correções.

A organização não deveria possuir simplesmente:

```json
{
  "country": "BR"
}
```

Ela deveria possuir **assertions**.

```json
{
  "assertion_id": "FA-123",
  "entity": "ORG-1",
  "predicate": "country",
  "value": "BR",
  "source_type": "USER_DECLARATION",
  "verification_status": "UNVERIFIED",
  "asserted_at": "2026-09-21"
}
```

Depois você fornece CNPJ ou documento constitutivo:

```json
{
  "assertion_id": "FA-476",
  "entity": "ORG-1",
  "predicate": "country",
  "value": "BR",
  "source_type": "DOCUMENT",
  "evidence_id": "EV-932",
  "verification_status": "VERIFIED"
}
```

**Eu não sobrescreveria a primeira assertion.**

Guardaria ambas.

O “fato atual” seria uma **visão derivada** das assertions existentes.

Isso cria auditabilidade.

### Decision Graph

Este seria o topo:

```text
DECISION:
PROJECT_ELIGIBILITY

ALL
├── GeographicEligibility
├── InstitutionEligibility
├── CoordinatorEligibility
├── ProjectEligibility
├── DocumentationEligibility
└── NoExclusionCondition
```

Cada filho pode conter dezenas de outras condições.

Assim você consegue explicar não apenas:

> “Não elegível.”

Mas:

```text
PROJECT_ELIGIBILITY
UNKNOWN

├─ GeographicEligibility       SATISFIED
├─ InstitutionEligibility      UNKNOWN
│  └─ public_status            UNKNOWN
├─ CoordinatorEligibility      SATISFIED
├─ ProjectEligibility          SATISFIED
└─ NoExclusionCondition        SATISFIED
```

Isso é muito mais poderoso.

### Sua expressão de elegibilidade fica exatamente correta

Para:

> Podem participar instituições brasileiras, desde que públicas. Instituições privadas também poderão participar quando associadas a uma ICT pública.

Teríamos:

```text
ELEGIBLE =
    country == BR
    AND
    (
        legal_nature == PUBLIC
        OR
        (
            legal_nature == PRIVATE
            AND
            EXISTS(
                partners,
                partner.type == ICT
                AND partner.legal_nature == PUBLIC
            )
        )
    )
```

Agora suponha que você apenas informe:

```text
country = BR
```

O solver calcula:

```text
country == BR                    SATISFIED

legal_nature == PUBLIC           UNKNOWN

legal_nature == PRIVATE          UNKNOWN

public_ICT_partner_exists        UNKNOWN

----------------------------------------

ELIGIBILITY                      UNKNOWN
```

O LLM não decide isso.

O LLM recebe:

```json
{
  "decision": "ELIGIBILITY",
  "status": "UNKNOWN",
  "satisfied": [
    "REQ-001"
  ],
  "unsatisfied": [],
  "unknown": [
    "REQ-002",
    "REQ-003"
  ],
  "blocking_facts": [
    "organization.legal_nature"
  ]
}
```

e escreve:

> A condição territorial está atendida. Ainda não é possível confirmar a elegibilidade, pois a natureza jurídica da instituição não foi verificada. Se a instituição for pública, esta parte da elegibilidade será atendida diretamente; se for privada, será necessário verificar a condição alternativa relativa à parceria com ICT pública.

Isso é excelente.

### Mas eu acrescentaria um quarto estado além dos seus três

Eu não ficaria apenas em:

```text
SATISFIED
UNSATISFIED
UNKNOWN
```

Acrescentaria:

```text
CONFLICT
```

E manteria:

```text
NOT_APPLICABLE
```

como estado separado de aplicabilidade.

O motivo é simples.

Imagine:

```text
Usuário:
"Somos uma instituição pública."

Documento cadastrado:
natureza jurídica = privada
```

Não é correto dizer `UNKNOWN`.

Existe **informação conflitante**.

Lógicas de quatro valores são justamente estudadas para cenários com fontes múltiplas contendo informação incompleta e/ou inconsistente. Não é necessário implementar academicamente toda a lógica Belnap-Dunn, mas a distinção conceitual é extremamente útil para seu produto. citeturn18view0

Eu teria:

```text
TRUTH STATUS

TRUE
FALSE
UNKNOWN
CONFLICT
```

e, separadamente:

```text
APPLICABILITY

APPLICABLE
NOT_APPLICABLE
UNKNOWN
```

Assim:

```text
REQ-89

applicability = NOT_APPLICABLE
truth = UNKNOWN
```

não precisa ser forçado artificialmente a `TRUE`.

### Outro acréscimo crucial: as arestas também precisam de evidência

Este é, para mim, o principal complemento à sua própria correção.

Não basta provar:

```text
R1 existe
R2 existe
```

Temos também que provar:

```text
R1 AND R2
```

Imagine uma IA que extraia corretamente duas frases, mas erre sua relação:

Original:

> “Poderão participar instituições públicas OU privadas.”

IA:

```text
PUBLIC AND PRIVATE
```

Todos os nós estão certos.

**A aresta está errada.**

Portanto, teríamos:

```text
rule_relations
--------------
id
from_node_id
to_node_id
relation_type
evidence_id
extraction_run_id
verification_status
confidence
```

O verificador avalia:

> “A fonte realmente sustenta que essas condições estão ligadas por AND?”

Isso se torna uma regra fundamental:

> **Toda semântica que possa mudar uma decisão deve possuir proveniência, inclusive relações entre regras.**

O LegalRuleML também trata explicitamente a ligação entre regras formalizadas e disposições textuais, inclusive em relações muitos-para-muitos, o que reforça esse desenho. citeturn17view1

### Exceções e retificações não devem ser meros operadores booleanos

Precisamos também de:

```text
OVERRIDES
SUPERSEDES
DEFEATS
SPECIALIZES
AMENDS
REVOKES
```

Por exemplo:

```text
RULE-21
deadline = 10/10/2026

RETIFICATION-RULE-3
deadline = 17/10/2026

RELATION:
RETIFICATION-RULE-3
SUPERSEDES
RULE-21
```

O LegalRuleML modela tanto temporalidade quanto regras que podem ser derrotadas por outras regras, precisamente porque normas não são conjuntos estáticos de booleanos. citeturn17view1

O seu banco precisa saber:

```text
10/10 não está "errado".
10/10 foi a regra original.

17/10 é a regra vigente.
```

Isso preserva história.

### Open-world semantics deve ser regra absoluta

A ausência de fato não significa falso.

Se não sabemos se sua instituição é pública:

```text
public = UNKNOWN
```

e não:

```text
public = FALSE
```

Isso impediria uma quantidade enorme de falsos negativos.

A própria abordagem de avaliação da Harvey considera a abstenção um resultado correto quando não há base adequada para uma resposta. citeturn21view2turn21view3

### O solver ainda oferece uma função fantástica: “o que falta saber?”

Depois de construir a árvore, podemos calcular **minimal blocking sets**.

Imagine:

```text
ELIGIBLE =
    Brazil
    AND
    (
       Public
       OR
       (
         Private
         AND ICTPartner
       )
    )
```

Já sabemos:

```text
Brazil = TRUE
```

O solver pode responder:

> Para resolver sua elegibilidade, a próxima informação de maior valor é a natureza jurídica da instituição.

Se você disser:

```text
Private = TRUE
```

então:

> Agora falta apenas comprovar parceria com ICT pública.

Isso permite que seu app construa automaticamente um **questionário inteligente**.

Em vez de perguntar 70 coisas:

> “Me diga primeiro a única informação que pode desbloquear a próxima decisão.”

Essa seria uma das funções mais legais do produto.

## Onde Jev entra de verdade

A pesquisa oficial sobre Jev fortaleceu bastante a decisão de usá-lo, mas também reforçou que ele **não deve ser o solver nem o interpretador jurídico principal**.

A TypeSafe lançou Jev em early access em 15 de setembro de 2026. A API recebe um estado não estruturado mais perguntas tipadas e retorna valores estruturados e distribuições probabilísticas. Os tipos oficiais incluem `Choice`, `Score` e `Noul`; as perguntas são avaliadas independentemente sobre o mesmo estado. citeturn21view5turn21view7

E a própria documentação da TypeSafe faz uma recomendação que coincide quase exatamente com nossa arquitetura:

> perguntas devem ser atômicas e bem delimitadas; julgamentos que exigem múltiplos fatores devem ser decompostos e os resultados combinados por código. citeturn21view7

Ou seja:

**Jev não deveria decidir `PROJECT_ELIGIBILITY`.**

Código faz isso.

### Excelente uso de Jev: triagem de cláusulas

Para cada bloco:

```text
"Serão elegíveis instituições científicas,
tecnológicas e de inovação sediadas no
Estado de Minas Gerais..."
```

Jev:

```json
{
  "contains_normative_rule": {
    "value": true,
    "probability": 0.998
  },
  "category": {
    "value": "ELIGIBILITY",
    "probabilities": {
      "ELIGIBILITY": 0.981,
      "BUDGET": 0.004,
      "DEADLINE": 0.002
    }
  }
}
```

Milhares dessas classificações pequenas são exatamente o formato para o qual o modelo é posicionado. citeturn21view5turn21view7

### Excelente uso: roteamento para agentes caros

```text
Jev:
is_simple_atomic_clause? 0.96

→ processa barato
```

versus:

```text
contains_exception? 0.74
contains_cross_reference? 0.88
logical_complexity? HIGH

→ frontier legal reasoning agent
```

Assim você não envia tudo para o modelo mais caro.

### Excelente uso: classificação de escopo

```text
actor_role?

PROPONENT      0.96
PARTNER        0.02
COORDINATOR    0.01
OTHER          0.01
```

### Excelente uso: detector de características críticas

```text
is_eliminatory?
contains_deadline?
contains_exception?
contains_prohibition?
contains_external_dependency?
contains_numeric_limit?
contains_cross_reference?
requires_human_review?
```

Cada pergunta é estreita.

### Excelente uso: evidence triage

Dado:

```text
claim:
"Instituição deve estar em Minas Gerais."

candidate evidence:
"São elegíveis ICTs sediadas no Estado
de Minas Gerais."
```

Jev pode rapidamente pontuar se aquela evidência merece seguir para o verifier caro.

### Excelente uso: matching preliminar

```text
requirement:
"coordenador deverá ter vínculo permanente"

fact:
"Professor adjunto efetivo da UFMG"

question:
"Este fato é evidência relevante
para o requisito?"

YES 0.97
```

Mas eu ainda enviaria casos semanticamente críticos para verificação.

### Onde eu NÃO usaria Jev

Não usaria para:

```text
interpretar sozinho 80 páginas
construir sozinho o Constraint Graph
resolver precedência entre retificações
fazer contas
calcular prazos
resolver elegibilidade final
interpretar uma cadeia jurídica complexa
decidir que um fato inexistente é falso
```

A própria TypeSafe afirma que Jev funciona melhor com muitas decisões estreitas, decompostas, com a lógica geral mantida no workflow de código. citeturn21view6turn21view7

Há também uma nuance importante na publicidade da TypeSafe. A empresa diz que Jev “não alucina”, mas posteriormente esclarece que o número de 0% usado para essa comparação **não é uma medição empírica**: ele deriva da garantia de aderência ao schema. Portanto, a interpretação segura é que Jev não produzirá um tipo de saída arbitrário fora do contrato estabelecido; isso não constitui prova de que toda classificação semântica feita por ele será correta. citeturn21view5turn21view6

Portanto, no nosso projeto:

> **type-safe ≠ semantically infallible.**

### Não fixaria thresholds agora

Não colocaria no código:

```python
if confidence > 0.98:
    trust()
```

porque 0,98 pode significar coisas diferentes para tarefas diferentes.

Criaria:

```text
jev_policy_thresholds

task_type
model_version
auto_accept_threshold
verify_threshold
escalate_threshold
calibration_dataset_version
```

E definiria os thresholds **depois de medir no nosso conjunto de editais**.

Isso é muito mais profissional.

## Cobertura, verificação e o que significa “não esquecer nada”

Aqui sua correção sobre coverage está absolutamente certa.

Eu removeria qualquer frase como:

> “Garantimos que 100% do significado jurídico foi identificado.”

Isso é impossível provar apenas olhando para a execução.

O que podemos provar é outra coisa.

### Processing Coverage

Matematicamente verificável:

```text
Arquivos recebidos             37
Arquivos processados           37/37

Páginas                        1428/1428
Slides                         82/82
Planilhas                      14/14
Abas                           67/67
Tabelas                        126/126
Imagens relevantes             43/43

Blocos estruturais             18.731/18.731
```

Isso é fato operacional.

### Structural Coverage

```text
Sections discovered            218
Sections processed             218

Numbered clauses               811
Processed clauses              811

Footnotes                      73
Processed footnotes            73

Cross-references               129
Resolved                       125
Unresolved                     4
```

Também mensurável.

### Rule Candidate Coverage

```text
Candidate normative passages   694
Adjudicated                    694
Ignored                        188
Converted to rules             506
```

E cada “ignored” precisa de reason code.

### Evidence Coverage

```text
Requirements                   506
With source evidence           506

Logical relations              294
With source evidence           294

Overrides/retifications        12
With source evidence           12
```

### Verification Coverage

```text
Requirement nodes verified     506/506
Logical edges verified         294/294
Scope assignments verified     506/506
Critical requirements          47/47
```

Tudo isso é runtime.

### Semantic recall é diferente

A pergunta:

> “Dos requisitos que realmente existem no edital, quantos nosso sistema encontrou?”

só pode ser respondida se você já possuir **ground truth**.

Portanto:

```text
Semantic Recall:
não é runtime coverage.
```

É uma métrica de benchmark.

A Harvey adotou exatamente a ideia de construir conjuntos próprios de avaliação para fluxos jurídicos em que não havia benchmark público adequado, usando contratos, playbooks, regras e rubricas elaboradas com sua equipe jurídica. citeturn21view1

Seu projeto deveria fazer o mesmo para editais.

### Eu criaria um TenderBench privado

Por exemplo:

```text
FAPEMIG
20 editais

FINEP
20 editais

CNPq
20 editais

CAPES
10 editais

BNDES
10 chamadas

outros
20

TOTAL
100 pacotes documentais
```

Especialistas anotariam manualmente:

```text
todos os requisitos
relações AND/OR
exceções
escopo
prazos
valores
precedência
retificações
critérios eliminatórios
documentos obrigatórios
referências externas
```

Depois mediríamos pelo menos:

| Métrica | O que mede |
|---|---|
| Requirement Recall | Requisitos existentes encontrados |
| Critical Requirement Recall | Requisitos eliminatórios encontrados |
| Requirement Precision | Extrações que realmente eram regras |
| Operator Accuracy | AND/OR/UNLESS/etc. corretos |
| Scope Accuracy | A quem a regra se aplica |
| Exception Recall | Exceções encontradas |
| Override Accuracy | Retificações/precedência corretas |
| Citation Precision | A fonte realmente sustenta a regra |
| Citation Recall | Toda evidência necessária foi citada |
| Solver Accuracy | Resultado lógico correto |
| Abstention Accuracy | Soube dizer “indeterminado” |
| End-to-End Decision Accuracy | Decisão final correta |
| Catastrophic Miss Rate | Perdeu condição capaz de invalidar proposta |

A ideia da Harvey de separar correctness, schema e qualidade da evidência é um excelente precedente para esse desenho. citeturn21view3

### Eu adicionaria testes contrafactuais

Depois de o sistema construir:

```text
ELIGIBLE =
    BR
    AND
    (
        PUBLIC
        OR
        PRIVATE_AND_ICT
    )
```

geramos automaticamente casos:

```text
BR=true
PUBLIC=true
→ ELIGIBLE
```

```text
BR=true
PUBLIC=false
PRIVATE=true
ICT=false
→ NOT_ELIGIBLE
```

```text
BR=true
PUBLIC=unknown
→ UNKNOWN
```

```text
BR=false
→ NOT_ELIGIBLE
```

Isso testa o **compilador jurídico + solver**, independentemente do LLM.

### E um teste de reconstrução

Outra coisa que adicionaria:

o sistema pega o grafo extraído e gera novamente uma frase legível:

```text
"Para ser elegível, a instituição deverá
estar no Brasil e ser pública ou,
caso privada, estar associada a uma ICT pública."
```

Um verifier compara essa reconstrução com o texto original.

Não prova perfeição, mas detecta muitos erros de atomização.

### O invariant mais importante passa a ser

Seu invariant 16 é excelente. Eu o reforçaria:

> **Invariant — Semantic Preservation:** atomizar uma disposição normativa jamais pode destruir, alterar ou inventar sua composição lógica, escopo, modalidade, exceção, temporalidade ou relação de precedência.

E adicionaria:

> **Invariant — Evidence-Bound Semantics:** todo nó e toda aresta capaz de alterar uma decisão deverá possuir evidência rastreável no documento original.

E:

> **Invariant — No Silent Resolution:** conflitos, lacunas ou ambiguidades capazes de alterar uma decisão jamais poderão ser resolvidos silenciosamente por um LLM.

Essa tríade seria a constituição do motor.

## Arquitetura final recomendada

Com tudo que pesquisei, eu fecharia a arquitetura assim:

```text
┌──────────────────────────────────────────────────────────────┐
│                       EDITAL PACKAGE                         │
│                                                              │
│ PDF • DOCX • DOC • XLSX • PPTX • MD • HTML • IMG • EMAIL    │
└──────────────────────────────┬───────────────────────────────┘
                               │
                               ▼
┌──────────────────────────────────────────────────────────────┐
│                    INGESTION GATE                            │
│                                                              │
│ hash • malware scan • mime detection • version • provenance │
│ deduplication • integrity • tenant isolation                │
└──────────────────────────────┬───────────────────────────────┘
                               │
                               ▼
┌──────────────────────────────────────────────────────────────┐
│            UNIVERSAL DOCUMENT PROCESSING                     │
│                                                              │
│ native extraction • OCR • Office conversion • vision        │
│ tables • spreadsheets • slides • images • footnotes         │
└──────────────────────────────┬───────────────────────────────┘
                               │
                               ▼
┌──────────────────────────────────────────────────────────────┐
│          CANONICAL DOCUMENT FORMAT / DOC GRAPH               │
│                                                              │
│ document                                                     │
│   page / slide / sheet                                       │
│     section                                                  │
│       element                                                │
│         sentence / cell / image                              │
│                                                              │
│ every element → immutable unique ID                          │
└──────────────────────────────┬───────────────────────────────┘
                               │
               ┌───────────────┼────────────────┐
               │               │                │
               ▼               ▼                ▼
        lexical index     vector index     metadata index
               │               │                │
               └───────────────┼────────────────┘
                               ▼
                        HYBRID RETRIEVAL
                               │
                               ▼
┌──────────────────────────────────────────────────────────────┐
│               NORMATIVE DISCOVERY ENGINE                    │
│                                                              │
│ Jev fast classification                                     │
│ + deterministic parsers                                     │
│ + frontier LLM agents                                       │
│ + cross-reference traversal                                 │
└──────────────────────────────┬───────────────────────────────┘
                               │
              ┌────────────────┴────────────────┐
              ▼                                 ▼
      atomic requirements                logical relations
              │                                 │
              └────────────────┬────────────────┘
                               ▼
┌──────────────────────────────────────────────────────────────┐
│                   NORMATIVE GRAPH                            │
│                                                              │
│ predicates                                                   │
│ scopes                                                       │
│ modalities                                                   │
│ definitions                                                  │
│ exceptions                                                   │
│ temporal validity                                            │
│ override / supersede                                         │
│ source provenance                                            │
└──────────────────────────────┬───────────────────────────────┘
                               │
                               ▼
                     NODE + EDGE VERIFIERS
                               │
                               ▼
                       RECONCILIATION
                               │
                               ▼
                       COVERAGE GATE
                               │
                               ▼
┌──────────────────────────────────────────────────────────────┐
│                VERIFIED CONSTRAINT GRAPH                     │
└──────────────────────────────┬───────────────────────────────┘
                               │
             ┌─────────────────┴──────────────────┐
             │                                    │
             ▼                                    ▼
┌───────────────────────────┐       ┌───────────────────────────┐
│ ORGANIZATION FACT GRAPH   │       │    PROJECT FACT GRAPH     │
│                           │       │                           │
│ assertions                │       │ assertions                │
│ evidence                  │       │ budget                    │
│ verification              │       │ people                    │
│ validity                  │       │ TRL                       │
│ provenance                │       │ evidence                  │
└──────────────┬────────────┘       └──────────────┬────────────┘
               │                                   │
               └─────────────────┬─────────────────┘
                                 ▼
┌──────────────────────────────────────────────────────────────┐
│                 DETERMINISTIC SOLVER                         │
│                                                              │
│ boolean logic                                                │
│ quantified rules                                             │
│ arithmetic                                                   │
│ dates                                                        │
│ set operations                                               │
│ aggregates                                                   │
│ precedence                                                   │
│ open-world semantics                                         │
│ contradiction handling                                       │
└──────────────────────────────┬───────────────────────────────┘
                               │
                  ┌────────────┼────────────┐
                  ▼            ▼            ▼
             SATISFIED    UNSATISFIED    UNKNOWN
                  │                         │
                  └─────── CONFLICT ───────┘
                               │
                               ▼
                      EXPLANATION ENGINE
                               │
                               ▼
                explanation + exact evidence
```

Isso combina três ideias públicas muito fortes: o processamento documental tipado, versionado e resiliente da Harvey; a decomposição e reconciliação multiagente do Playbook Review; e a transformação em massa de documentos não estruturados em dados operacionais exemplificada pela Enter. citeturn20view0turn21view1turn22view0turn22view1

E acrescenta a camada que eu considero específica para o seu domínio:

**Formal Constraint Engine.**

### Banco de dados

Eu expandiria suas tabelas para algo próximo disto:

```text
tenants

users

tender_packages
package_versions

source_documents
document_versions
document_elements

processing_runs
processing_artifacts

evidences
evidence_spans

normative_rules
rule_predicates
rule_scopes
rule_modalities

constraint_groups
constraint_members
constraint_relations

rule_overrides
rule_temporal_validity

definitions
external_references

organizations
projects
people

fact_assertions
fact_evidences
fact_resolution

decision_models
decision_nodes

solver_runs
solver_node_results
solver_explanations

analysis_runs
analysis_findings

model_calls
model_decisions
model_versions

coverage_snapshots

evaluation_datasets
evaluation_cases
evaluation_runs

audit_events
```

Especialmente:

```text
normative_rules
---------------
id
tenant_id
package_id
canonical_key
rule_type
modality
severity
criticality
predicate_ast_json
actor_role
scope_json
valid_from
valid_to
effective_status
extraction_run_id
verification_status
```

```text
constraint_groups
-----------------
id
tenant_id
package_id
operator
parent_group_id
expression_ast_json
effective_status
```

```text
constraint_relations
--------------------
id
from_node_id
to_node_id
relation_type
evidence_id
verification_status
extraction_run_id
```

```text
fact_assertions
---------------
id
entity_type
entity_id
fact_key
typed_value_json
source_type
source_id
verification_status
confidence
valid_from
valid_to
asserted_at
superseded_by
```

```text
solver_node_results
-------------------
solver_run_id
node_id
applicability_status
truth_status
reason_code
dependency_results_json
blocking_facts_json
evidence_ids
```

O **AST** é importante.

Em vez de:

```json
{
  "logic": "complicada"
}
```

teremos algo como:

```json
{
  "op": "ALL",
  "args": [
    {
      "op": "EQ",
      "left": {"fact": "organization.country"},
      "right": {"literal": "BR"}
    },
    {
      "op": "ANY",
      "args": [
        {
          "op": "EQ",
          "left": {"fact": "organization.legal_nature"},
          "right": {"literal": "PUBLIC"}
        },
        {
          "op": "ALL",
          "args": [
            {
              "op": "EQ",
              "left": {"fact": "organization.legal_nature"},
              "right": {"literal": "PRIVATE"}
            },
            {
              "op": "EXISTS",
              "collection": {"fact": "project.partners"},
              "where": {
                "op": "ALL",
                "args": [
                  {
                    "op": "EQ",
                    "left": {"field": "type"},
                    "right": {"literal": "ICT"}
                  },
                  {
                    "op": "EQ",
                    "left": {"field": "legal_nature"},
                    "right": {"literal": "PUBLIC"}
                  }
                ]
              }
            }
          ]
        }
      ]
    }
  ]
}
```

Isso é executável, testável e versionável.

Uma tecnologia como OPA/Rego demonstra o valor de tratar políticas como regras declarativas executadas sobre dados estruturados e inclusive possui conceito de valores desconhecidos durante avaliação parcial. Eu usaria isso como inspiração para o solver, embora não necessariamente adotasse Rego como formato canônico do produto. citeturn16view3

**Nosso AST deve ser o formato canônico.**

Depois poderemos compilar para:

```text
Python
SQL
Rego
ou outro motor
```

sem perder o original.

## Prompt mestre para construir o aplicativo

Abaixo está o prompt que eu realmente entregaria a um coding agent. Ele incorpora a pesquisa e, principalmente, impede que a IA “finja” ter implementado o sistema inteiro criando mocks.

A filosofia de execução faseada é deliberada. Tanto Harvey quanto Enter descrevem sistemas com componentes independentes, jobs persistentes, etapas com falhas diferentes e processamento assíncrono; não existe evidência de que um monólito de uma chamada seja adequado para esse tipo de produto. citeturn20view0turn21view4

```text
You are the Principal Architect and Principal Engineer responsible for
building a production-grade AI platform for analysis of public funding
calls, grants, tenders and "editais", initially focused on Brazilian
agencies such as FAPEMIG, FINEP, CNPq, CAPES and similar organizations.

PROJECT WORKING NAME:
Tender Intelligence Engine

IMPORTANT:
This is NOT a ChatPDF project.
This is NOT a generic RAG chatbot.
This is NOT a demo.
This is NOT a UI prototype with mocked backend behavior.

The core product is a versioned, auditable, evidence-backed compiler that
converts a heterogeneous tender document package into an executable
normative/constraint graph and compares that graph against verified facts
about organizations and projects.

The system must be designed so that LLMs are workers inside a deterministic
software architecture. LLM output must never become the sole source of truth
for final eligibility decisions.

============================================================
PROJECT CONSTITUTION
============================================================

Create and permanently maintain these files before implementing production
features:

/docs/MASTER_SPEC.md
/docs/ARCHITECTURE.md
/docs/INVARIANTS.md
/docs/DATA_MODEL.md
/docs/AI_PIPELINE.md
/docs/SOLVER_SPEC.md
/docs/EVALS.md
/docs/SECURITY.md
/docs/ADRS/
/docs/PHASE_STATUS.md

MASTER_SPEC.md is the constitution of the project.

No implementation decision may silently contradict it.

When an engineering tradeoff requires deviation:
1. document the issue;
2. create an ADR;
3. explain the tradeoff;
4. preserve all safety invariants.

Never silently simplify a requirement.

============================================================
NON-NEGOTIABLE PRINCIPLES
============================================================

P1 — Evidence first.

Every material statement extracted from a tender must be traceable to exact
source evidence.

P2 — Original files are immutable.

Never replace, rewrite or discard source files.

P3 — Source fidelity.

Every page, slide, worksheet, table, paragraph, cell, image, footnote and
other structural element that can affect meaning receives stable identity
and provenance.

P4 — No direct PDF-to-summary architecture.

A summary may only be generated AFTER structural extraction, normative
extraction, verification and reconciliation.

P5 — Atomization without semantic destruction.

A compound source clause may become multiple atomic requirements, but its
logical relationships must be preserved.

Example:

"Applicant must be an ICT based in Minas Gerais and its coordinator must
have a permanent employment relationship."

May become:

R1 organization.type == ICT
R2 organization.state == MG
R3 coordinator.employment_relationship == PERMANENT

but MUST ALSO produce:

ALL(R1, R2, R3)

P6 — Every semantic relation requires provenance.

Not only rule nodes but also edges such as:

AND
OR
UNLESS
EXCEPTION
OVERRIDES
SUPERSEDES
IMPLIES

must be linked to evidence and independently verifiable.

P7 — Open world semantics.

Missing information is UNKNOWN, never automatically FALSE.

P8 — Contradiction is explicit.

Conflicting assertions produce CONFLICT.
Do not silently select one.

P9 — Applicability and truth are separate dimensions.

A rule can be NOT_APPLICABLE rather than SATISFIED.

P10 — Deterministic final logic.

Once rules and facts have been compiled into typed expressions, final
eligibility evaluation is performed by deterministic code.

An LLM must never decide final eligibility by free-form reasoning.

P11 — LLM explains; solver decides.

Natural-language answers about organization/project eligibility are
generated from solver results.

P12 — No unsupported negation.

Failure to find a requirement does NOT justify:
"No such requirement exists."

Use:
"No such requirement was identified in the documents analyzed."

P13 — No unsupported positive claim.

A factual conclusion must have evidence or an explicit source type such as
USER_DECLARATION.

P14 — No silent ambiguity resolution.

Ambiguities affecting eligibility, deadlines, budget or mandatory
documentation must be surfaced.

P15 — No silent conflict resolution.

Conflicting official documents must be represented explicitly until a
verified precedence rule resolves them.

P16 — Semantic preservation invariant.

Requirement atomization must never destroy:
- logical composition;
- exception;
- scope;
- modality;
- temporality;
- authority;
- precedence;
- dependency.

P17 — Evidence-bound semantics invariant.

Every rule node and logical edge capable of changing a decision must have
traceable evidence.

P18 — Runtime coverage must never be presented as semantic completeness.

The platform may prove all 1,428 pages were processed.
It cannot claim to have mathematically proved that every legal meaning was
discovered.

P19 — Human review remains possible at every critical layer.

A reviewer must be able to inspect:
source → extracted rule → logical graph → solver conclusion.

P20 — Model independence.

Business logic must not be hard-wired to one AI vendor.

============================================================
TARGET USER EXPERIENCE
============================================================

The user creates an "Edital Package".

They may upload an arbitrary number of files:

PDF
scanned PDF
DOCX
legacy DOC
XLSX
XLS
CSV
PPTX
TXT
Markdown
HTML
images
ZIP archives when safe and supported

Files within one package may include:

main edital
annexes
forms
budget spreadsheets
manuals
FAQs
errata
retifications
presentation decks
templates
external rules downloaded by the user

The user does not have to manually classify them.

The application attempts classification and asks for review only when
necessary.

After processing, provide:

Visão Geral
Elegibilidade
Cronograma
Valores
Orçamento
Documentação
Critérios de Avaliação
Critérios Eliminatórios
Contrapartidas
Despesas Permitidas
Despesas Proibidas
Equipe
TRL
Parcerias
Propriedade Intelectual
Prestação de Contas
Obrigações
Impedimentos
Recursos
Retificações
Referências Externas
Pontos de Atenção
Fontes
Cobertura
Auditoria

Every displayed factual statement must have:
[Ver fonte]

The source viewer must open the exact original document location whenever
possible.

============================================================
SYSTEM ARCHITECTURE
============================================================

Use a modular monorepo.

Recommended logical components:

apps/web
apps/api

services/document-processing
services/normative-engine
services/constraint-engine
services/solver
services/ai-gateway
services/worker

packages/domain
packages/schemas
packages/sdk
packages/ui

infra/

The exact physical deployment may begin simpler than the logical
architecture.

Do NOT create microservices merely for aesthetics.

Clear module boundaries are mandatory.
Independent deployment is optional until scale justifies it.

============================================================
RECOMMENDED TECHNOLOGY BASELINE
============================================================

Frontend:
- Next.js
- TypeScript
- React
- server/client boundaries used correctly
- accessible component system
- strong typed API client

Backend:
- Python
- FastAPI
- Pydantic
- SQLAlchemy or equivalent typed ORM
- Alembic migrations

Primary relational database:
- PostgreSQL

Object storage:
- S3-compatible object storage

Search:
- lexical search
- vector search
- metadata filtering
- hybrid retrieval abstraction

The implementation may use PostgreSQL initially where appropriate, but
search interfaces must allow migration to a specialized search engine
without rewriting domain logic.

Long-running orchestration:
- durable workflow abstraction
- retries
- idempotency
- task state persistence
- cancellation
- resume after worker crash
- per-stage concurrency limits

A mature workflow engine such as Temporal or Hatchet may be used.

Do not implement long document jobs as one HTTP request.

Cache:
- Redis only when actually useful.

Observability:
- OpenTelemetry-compatible tracing
- structured logs
- metrics
- audit logs

Do not introduce ClickHouse, Kafka, NATS or additional distributed systems
until there is a demonstrated operational reason.

"Enterprise architecture" does not mean maximizing technology count.

============================================================
TENANCY AND SECURITY
============================================================

Multi-tenant by design.

Every tenant-owned table must include tenant_id directly or have a safe,
enforced ownership path.

Use PostgreSQL RLS where appropriate.

Requirements:

- strict tenant isolation
- encryption in transit
- encryption at rest
- secrets manager
- signed object URLs
- short-lived file access
- malware scanning
- MIME verification
- upload size controls
- ZIP bomb protection
- path traversal prevention
- audit logging
- least privilege
- role-based authorization
- deletion workflow
- retention policies
- LGPD-aware handling
- no customer files used for model training unless explicitly authorized
- AI provider configuration capable of enterprise/no-training modes

Never expose private object-storage keys to browsers.

============================================================
DOCUMENT INGESTION
============================================================

Each upload creates:

source_document
document_version
content_hash
original_filename
detected_mime
declared_mime
byte_size
tenant_id
package_id
origin
uploaded_at
processing_status

Use cryptographic hashes for integrity and deduplication assistance.

Original binary is immutable.

Do not use filename as identity.

A replacement document creates a new version.

============================================================
CANONICAL DOCUMENT FORMAT
============================================================

Implement a versioned internal Universal/Canonical Document Format inspired
by typed document intermediate representations.

Do NOT store extraction as one giant text string.

Represent:

Document
  Pages / Slides / Worksheets
    Sections
      Elements
        Sentences / Cells / Items

Every element has:

element_id
document_version_id
element_type
order_index
page_number nullable
slide_number nullable
sheet_name nullable
section_path
bounding_box nullable
text nullable
structured_content_json
parent_element_id nullable
extraction_method
extraction_confidence nullable

Element types must include at least:

heading
paragraph
list
list_item
table
table_row
table_cell
footnote
header
footer
caption
image
chart
formula
form_field
page_break
other

Preserve reading order.

Preserve table structure.

Do not flatten spreadsheets into prose.

Preserve merged cells and sheet names where practical.

============================================================
OCR AND MULTIMODAL PROCESSING
============================================================

Prefer native extraction when reliable.

Use OCR when required.

Use image/vision analysis only for information that text extraction cannot
reliably represent, such as:

complex diagrams
charts
scanned tables
layout-dependent content
embedded images containing material instructions

Store which extraction route produced each element.

Never silently replace failed OCR with invented content.

============================================================
DOCUMENT PROCESSING WORKFLOW
============================================================

At minimum:

UPLOAD
↓
SECURITY_SCAN
↓
TYPE_DETECTION
↓
NATIVE_EXTRACTION
↓
OCR_IF_REQUIRED
↓
STRUCTURE_NORMALIZATION
↓
ELEMENT_ID_ASSIGNMENT
↓
QUALITY_CHECK
↓
LEXICAL_INDEX
↓
EMBEDDING
↓
VECTOR_INDEX
↓
STRUCTURAL_ANALYSIS
↓
NORMATIVE_DISCOVERY

Each stage is:

idempotent
retryable
observable
independently fail-able

One corrupted file must not kill a 50-file package.

Persist progress.

============================================================
SEARCH AND RETRIEVAL
============================================================

Do not build vector-only RAG.

Support:

exact lexical retrieval
BM25-like retrieval
semantic vector retrieval
metadata filtering
document filtering
section filtering
element type filtering
reranking
cross-reference traversal

Tender language frequently contains exact identifiers such as:

"7.2.4"
"R$ 500.000,00"
"17h59"
"Anexo III"
"TRL 4"
"CNPJ"

These must be retrievable precisely.

Implement retrieval snapshots so AI analysis can be reproduced later.

============================================================
NORMATIVE ONTOLOGY
============================================================

A normative rule must have a typed category.

Minimum categories:

DEFINITION
ELIGIBILITY_CONDITION
OBLIGATION
PROHIBITION
PERMISSION
DEADLINE
DOCUMENT_REQUIREMENT
BUDGET_RULE
EXPENSE_ALLOWED
EXPENSE_PROHIBITED
COUNTERPART_REQUIREMENT
TEAM_REQUIREMENT
PARTNERSHIP_REQUIREMENT
TRL_REQUIREMENT
GEOGRAPHIC_REQUIREMENT
EVALUATION_CRITERION
SCORING_CRITERION
ELIMINATORY_CRITERION
TIE_BREAKER
SUBMISSION_RULE
EXECUTION_RULE
REPORTING_RULE
INTELLECTUAL_PROPERTY_RULE
APPEAL_RULE
SANCTION
EXCEPTION
EXTERNAL_DEPENDENCY
INFORMATIONAL

Do not assume this enumeration will never evolve.

============================================================
ACTORS AND SCOPE
============================================================

Rules must explicitly model the actor they apply to.

Initial actor roles:

PROPONENT
EXECUTOR
COEXECUTOR
PARTNER
ICT
COMPANY
SUPPORT_FOUNDATION
COORDINATOR
RESEARCHER
TEAM_MEMBER
SCHOLARSHIP_RECIPIENT
OTHER

Scope may also include:

project type
funding modality
program line
geography
institution category
phase
date interval
submission path

A statement about PROPONENT must never automatically apply to PARTNER.

============================================================
RULE ATOMIZATION
============================================================

For each normative provision:

1. identify candidate rule;
2. determine whether it contains multiple atomic predicates;
3. create atomic requirements;
4. preserve original composition as a constraint group;
5. retain source evidence for nodes;
6. retain source evidence for relations;
7. verify the resulting graph.

Example:

"Eligible applicants are public ICTs located in Minas Gerais."

Create:

R1 actor.type == ICT
R2 actor.legal_nature == PUBLIC
R3 actor.state == MG

and:

ALL(R1,R2,R3)

Never keep only R1/R2/R3 and discard ALL.

============================================================
CONSTRAINT DSL
============================================================

Create a typed AST.

Required operators:

Logical:
ALL
ANY
NOT
XOR
IMPLIES
IFF

Conditional:
IF_THEN
UNLESS
EXCEPT_IF

Cardinality:
ONE_OF
EXACTLY_ONE
AT_LEAST_N
AT_MOST_N
EXACTLY_N

Comparison:
EQ
NEQ
GT
GTE
LT
LTE
BETWEEN
IN
NOT_IN

Quantification:
EXISTS
FOR_ALL

Aggregates:
COUNT
SUM
AVERAGE
PERCENTAGE

Temporal:
BEFORE
AFTER
ON_OR_BEFORE
ON_OR_AFTER
WITHIN
DURATION

Set:
CONTAINS
INTERSECTS
SUBSET_OF

Do not execute arbitrary Python from AST.

Use a safe interpreter/compiler.

============================================================
LEGAL / NORMATIVE RELATIONS
============================================================

Separately support relations:

DEPENDS_ON
REQUIRES
EXCEPTION_TO
SPECIALIZES
OVERRIDES
SUPERSEDES
AMENDS
REVOKES
REFERENCES
DEFINED_BY

These are not merely display metadata.

They may affect effective rule state.

============================================================
TEMPORALITY
============================================================

Rules may have:

published_at
valid_from
valid_to
effective_from
effective_to
superseded_at

Retifications must preserve history.

Example:

Original:
deadline = 2026-10-10

Retification:
deadline = 2026-10-17

Store both.

Represent:

retification_rule
SUPERSEDES
original_rule

The active graph resolves to 2026-10-17 while audit/history continues to
show the original.

============================================================
EXTERNAL REFERENCES
============================================================

Detect references such as:

"conforme Manual X"
"nos termos da Resolução Y"
"vide Anexo IV"

Create ExternalDependency records.

Statuses:

RESOLVED
MISSING_DOCUMENT
UNRESOLVED_REFERENCE
NOT_ACCESSIBLE
REVIEW_REQUIRED

Never infer the content of an absent referenced document.

Display missing dependencies prominently.

============================================================
EVIDENCE MODEL
============================================================

Every important assertion has one or more evidence spans.

Evidence must point to:

document_version_id
element_id
page/slide/sheet when applicable
character/cell span where possible
original text
extraction version

Support one rule from many source provisions and many rules from one
provision.

============================================================
RULE RELATION EVIDENCE
============================================================

A logical relation itself must be verifiable.

Example:

R1 exists.
R2 exists.
Relation = ALL(R1,R2).

Store evidence explaining why the source means AND rather than OR.

This is mandatory.

============================================================
AI ORCHESTRATION
============================================================

Use specialized agents.

Suggested roles:

StructureAgent
NormativeCandidateAgent
EligibilityAgent
BudgetAgent
TimelineAgent
DocumentationAgent
EvaluationCriteriaAgent
ScopeAgent
ExceptionAgent
CrossReferenceAgent
RetificationAgent
DefinitionAgent
LogicalRelationAgent
EvidenceAgent
VerificationAgent
ReconciliationAgent

Agents are logical roles.
Do not require one infrastructure process per role.

Run independent work in parallel where safe.

============================================================
FRONTIER MODEL RESPONSIBILITIES
============================================================

Use strong reasoning-capable models for:

complex clause interpretation
logical decomposition
cross-clause relationships
exceptions
scope ambiguity
definition propagation
retification interpretation
hard evidence verification
conflict reconciliation

Never let provider-specific output leak into core domain schemas.

All AI provider responses pass through validated adapters.

============================================================
JEV INTEGRATION
============================================================

Jev is an accelerator and classifier, never the authoritative legal engine.

Create a JevAdapter behind AI Gateway.

Good Jev tasks:

contains_normative_rule?
rule_category?
actor_role?
is_eliminatory?
contains_exception?
contains_cross_reference?
contains_deadline?
contains_numeric_constraint?
contains_prohibition?
contains_external_dependency?
candidate_evidence_relevance?
simple_vs_complex?
requires_frontier_model?
possible_duplicate?
review_priority?

Ask narrow atomic questions.

Do NOT ask:

"Is this project eligible under the entire edital?"

Do NOT ask Jev to replace ConstraintSolver.

Do NOT ask Jev to perform deterministic arithmetic.

Persist:

task_type
model_version
input_hash
typed_questions
output
probabilities
confidence
latency
cost metadata where available

Thresholds must be empirically calibrated by task type.

Do not hard-code universal 0.90/0.95/0.98 trust values without eval data.

============================================================
AI ROUTING
============================================================

Implement a routing policy:

deterministic parser first when possible
↓
Jev narrow decision where appropriate
↓
specialized model
↓
frontier reasoning model
↓
human review when policy requires it

The escalation policy must be configurable.

============================================================
NODE VERIFICATION
============================================================

For each extracted normative node, a separate verification operation asks:

1. Does the cited evidence actually contain/support this rule?
2. Is the predicate faithful?
3. Is modality correct?
4. Is actor/scope correct?
5. Are numeric values exact?
6. Are units exact?
7. Is temporal information exact?

A failed verification cannot silently become VERIFIED.

============================================================
EDGE VERIFICATION
============================================================

For every decision-changing relation:

AND
OR
IF
UNLESS
EXCEPTION
OVERRIDE
SUPERSEDE
etc.

verify:

1. source support;
2. operator correctness;
3. directionality;
4. scope;
5. exception semantics.

This is as important as node verification.

============================================================
RECONCILIATION
============================================================

After parallel extraction, reconcile:

duplicates
overlapping rules
contradictory rules
conflicting scope
conflicting operators
retifications
definitions
cross-document dependencies

Never resolve a material conflict without recording how it was resolved.

============================================================
FACT ASSERTIONS
============================================================

Organizations and projects use append-only FactAssertions.

Do not model facts as mutable fields only.

FactAssertion:

id
entity_type
entity_id
fact_key
typed_value
source_type
source_id
verification_status
confidence nullable
valid_from nullable
valid_to nullable
created_at

source_type:

USER_DECLARATION
USER_DOCUMENT
OFFICIAL_DOCUMENT
EXTERNAL_REGISTRY
DERIVED
ADMIN_OVERRIDE

verification_status:

UNVERIFIED
VERIFIED
REJECTED
CONFLICTING
EXPIRED

Example:

User:
"We are located in Brazil."

Store:

organization.country = BR
source_type = USER_DECLARATION
verification_status = UNVERIFIED

Do NOT call it documentary proof.

============================================================
FACT RESOLUTION
============================================================

Multiple assertions may concern the same fact.

Implement FactResolver.

Do not destroy old assertions.

Produce canonical/derived state based on:

source authority
verification
validity
conflict policy
date

If two credible assertions conflict:

status = CONFLICT

Do not silently choose one.

============================================================
CONVERSATIONAL FACT INTERPRETER
============================================================

When user says:

"Somos uma instituição brasileira."

The chat pipeline is:

user message
↓
FactInterpreter
↓
candidate assertion:
organization.country = BR
source = USER_DECLARATION
↓
user-visible interpretation when needed
↓
store assertion
↓
invalidate affected solver cache
↓
incrementally recompute affected decision nodes

Do NOT send the conversation to an LLM and ask it to reassess the edital from
scratch.

============================================================
CONSTRAINT SOLVER
============================================================

Implement deterministic ConstraintSolver.

It consumes:

Verified Normative Graph
+
Resolved Fact Graph
+
Evaluation Context

It outputs:

truth_status
applicability_status
dependency tree
satisfied nodes
unsatisfied nodes
unknown nodes
conflicting nodes
blocking facts
evidence references
reason codes

Truth statuses:

SATISFIED
UNSATISFIED
UNKNOWN
CONFLICT

Applicability statuses:

APPLICABLE
NOT_APPLICABLE
UNKNOWN

Implement open-world semantics.

============================================================
SOLVER EXAMPLE
============================================================

Rule:

Brazil
AND
(
  Public
  OR
  (
    Private
    AND
    PublicICTPartner
  )
)

Facts:

Brazil = TRUE
legal_nature = UNKNOWN

Output:

overall = UNKNOWN

satisfied:
Brazil

unknown:
Public
Private

blocking_facts:
organization.legal_nature

Do not return ELIGIBLE.

============================================================
PARTIAL EVALUATION
============================================================

Implement the ability to simplify the constraint graph using known facts.

This supports:

"What else do we need to know?"

After known facts are substituted, return residual constraints.

Example:

Brazil = TRUE
Private = TRUE

Original:

Brazil AND (Public OR (Private AND PublicICTPartner))

Residual:

PublicICTPartner

============================================================
MINIMAL BLOCKING SETS
============================================================

Implement a mechanism to identify minimal unknown or failed conditions that
prevent a decision.

Use this to generate:

"Para concluir sua elegibilidade precisamos saber X."

When there are alternative branches, return them explicitly.

Example:

Path A:
prove PUBLIC

Path B:
prove PRIVATE + PUBLIC_ICT_PARTNER

Do not suggest that every unknown fact must necessarily be supplied.

============================================================
COUNTERFACTUALS
============================================================

Solver should support:

"What would need to change for this requirement to be satisfied?"

Example:

Current:
third_party_budget = 34%
max = 30%

Return deterministic counterfactual:

third_party_budget must be <= 30%

The explanation LLM may verbalize it but cannot change the calculation.

============================================================
BUDGET ENGINE
============================================================

Budget rules must use deterministic arithmetic.

Support:

amount limits
percent limits
category caps
category exclusions
counterpart percentages
minimum/maximum requested value
per-item restrictions
aggregate restrictions

Never ask an LLM to calculate values that normal code can calculate.

============================================================
DATE ENGINE
============================================================

Dates and deadlines must be normalized and calculated deterministically.

Represent:

absolute dates
date-times
time zones
business-day expressions when defined
relative deadlines
event-triggered deadlines

Retain original textual form.

When interpretation depends on an external calendar/rule not provided,
mark dependency rather than guessing.

============================================================
SCORING MODEL
============================================================

Distinguish:

ELIGIBILITY
from
COMPETITIVE_EVALUATION

An eligible project may still score poorly.

Support:

weighted criteria
minimum per criterion
minimum total score
bonus criteria
penalties
tie-breakers
elimination thresholds

Do not collapse score into eligibility.

============================================================
COVERAGE ENGINE
============================================================

Never output one misleading "100% analyzed" metric.

Create distinct metrics.

processing_coverage:
files/pages/slides/sheets technically processed

structural_coverage:
structural elements traversed

candidate_coverage:
normative candidates adjudicated

evidence_coverage:
rules and edges with source evidence

verification_coverage:
rules/edges that passed verification

external_dependency_coverage:
resolved/unresolved external references

semantic_recall:
NEVER claimed from runtime alone

Semantic recall comes from offline benchmark/evaluation datasets.

============================================================
SUMMARY GENERATION
============================================================

Summary is generated only from VERIFIED knowledge.

Never summarize raw documents as the authoritative summary path.

The summary engine receives structured facts such as:

deadlines
eligibility rules
budget rules
documents
exceptions
risks
evaluation criteria

and source references.

============================================================
"POINTS OF ATTENTION"
============================================================

Do not create speculative suggestions.

Points of attention must be evidence-backed conditions such as:

eliminatory rule
exception
negative formulation
deadline
unresolved reference
document conflict
retification
mandatory attachment
budget cap
minimum score
special actor condition
uncertain logical interpretation

Each item requires source evidence.

============================================================
CHAT ARCHITECTURE
============================================================

For generic document questions:

query
↓
intent classification
↓
Verified Knowledge Base / retrieval
↓
evidence
↓
answer

For personalized eligibility questions:

query
↓
fact extraction if applicable
↓
Fact Graph
↓
Constraint Solver
↓
solver result
↓
evidence retrieval
↓
Explanation LLM

The Explanation LLM must receive machine-readable solver state.

It cannot override solver status.

============================================================
LANGUAGE POLICY
============================================================

Final answers should distinguish carefully:

"The edital states..."

"The documents analyzed indicate..."

"The system did not identify..."

"Based on currently verified organization data..."

"Based only on your declaration..."

"The available evidence is insufficient..."

Avoid:

"Probably..."
"It seems..."
"I assume..."

for material eligibility claims.

============================================================
EXPLANATION CONTRACT
============================================================

For a personalized requirement return:

requirement
status
applicability
what_the_edital_requires
what_we_know
what_is_missing
blocking_condition
source_evidence
fact_evidence
confidence_metadata when applicable

============================================================
RETIFICATION ENGINE
============================================================

Automatically detect likely:

retificação
errata
comunicado
FAQ update

Extract explicit amendment relations.

Never infer supersession solely because two values differ.

Require evidence establishing amendment/precedence or flag conflict.

============================================================
DEPENDENCY GRAPH
============================================================

Follow internal references:

item → subitem
clause → annex
annex → spreadsheet
rule → manual
retification → original clause

The engine must recursively resolve available dependencies.

============================================================
OBSERVABILITY
============================================================

Every AI call must be observable.

Store where permitted:

provider
model
model_version
prompt/template version
task type
input hash
output hash
latency
token usage
estimated cost
retry count
result validation
trace id

Never store secret credentials.

============================================================
REPRODUCIBILITY
============================================================

Every analysis must record:

document versions
canonical-document-format version
extractor versions
ontology version
prompt versions
AI model versions
Jev version
constraint compiler version
solver version

An old analysis must remain auditable after the system evolves.

============================================================
EVALUATION HARNESS
============================================================

Build eval infrastructure as a first-class feature.

Do not postpone it until "after MVP".

Support manually annotated gold packages.

Measure:

requirement recall
critical requirement recall
requirement precision
logical operator accuracy
scope accuracy
exception recall
override accuracy
citation precision
citation recall
abstention accuracy
solver accuracy
end-to-end decision accuracy
catastrophic miss rate

Store results by model/prompt/pipeline version.

No AI component may be upgraded globally without regression evaluation.

============================================================
CRITICAL REQUIREMENT TESTS
============================================================

Maintain special tests for:

eliminatory criteria
deadlines
budget limits
eligibility
mandatory documentation

Errors here must be weighted more severely than harmless summary wording.

============================================================
PROPERTY-BASED SOLVER TESTS
============================================================

Create deterministic unit/property tests for:

ALL
ANY
NOT
IMPLIES
UNLESS
EXCEPT_IF
cardinality
aggregates
unknown propagation
conflict propagation
not-applicable behavior
precedence
temporal validity

The solver must be independently testable without an LLM.

============================================================
METAMORPHIC TESTS
============================================================

For extracted graphs create controlled fact changes.

Example:

public=true → eligible

then mutate:

public=false

and ensure result changes according to the graph.

Use this to find logically malformed rule graphs.

============================================================
ROUND-TRIP SEMANTIC TEST
============================================================

Create a rendering of extracted constraint expressions back into human
language.

A verification process compares the reconstructed meaning with the original
source provisions.

Failures become REVIEW_REQUIRED.

============================================================
HUMAN REVIEW UI
============================================================

Build a review screen displaying:

left:
original source document

middle:
extracted atomic rules

right:
constraint graph

Allow reviewers to:

approve
reject
edit predicate
change scope
change operator
link evidence
resolve conflict
mark exception
set precedence

Every edit creates an audit event.

Never mutate history invisibly.

============================================================
MAIN DASHBOARD
============================================================

Show something similar to:

Arquivos recebidos             37
Arquivos processados           37/37

Páginas                        1428/1428
Slides                         82/82
Planilhas                      14/14
Tabelas                        126/126

Requisitos                     281
Condições                      74
Exceções                       23
Prazos                         17
Critérios eliminatórios        11

Relações lógicas verificadas   194/194

Referências externas           9
Resolvidas                     8
Ausentes                       1

Conflitos não resolvidos       1

Do NOT show:
"100% semantic accuracy."

============================================================
ORGANIZATION PROFILE
============================================================

Allow reusable organization profiles.

Data can include:

identity
legal nature
CNPJ
location
institution category
ICT status
foundation relationship
certifications
registrations
financial information
people
historical projects
documents

Every material fact supports provenance/verification.

============================================================
PROJECT PROFILE
============================================================

Reusable project profiles support:

title
description
area
subarea
TRL
team
institutions
partners
budget
timeline
technical objectives
deliverables
IP assumptions
documents

Again, assertions + evidence.

============================================================
COMPARE BUTTON
============================================================

The UI has:

"Comparar com minha organização/projeto"

This must trigger:

selected Verified Constraint Graph
×
resolved Organization Fact Graph
×
resolved Project Fact Graph

Return:

SATISFIED
UNSATISFIED
UNKNOWN
CONFLICT
NOT_APPLICABLE

for every applicable requirement.

Never ask one LLM:
"Does this company qualify?"

============================================================
RESULT VIEW
============================================================

Example:

Elegibilidade

22 condições avaliadas

18 SATISFIED
1 UNSATISFIED
3 UNKNOWN
0 CONFLICT

Overall:
UNSATISFIED

Primary blocker:
REQ-083

Requirement:
Project coordinator must have condition X.

Evidence:
Edital, item 7.2.3, page 18.

Organization/project fact:
...

Provide:
[Ver regra]
[Ver fonte]
[Ver fato]
[Ver grafo]

============================================================
NO HIDDEN INFERENCES
============================================================

Every conclusion must be classifiable as:

EXPLICIT_SOURCE_FACT
DERIVED_DETERMINISTICALLY
AI_INTERPRETED_VERIFIED
USER_DECLARATION
UNVERIFIED_AI_INTERPRETATION

Do not mix these categories.

============================================================
API DESIGN
============================================================

Design explicit REST/typed endpoints or equivalent for:

packages
documents
processing
elements
rules
constraints
evidence
organizations
projects
facts
solver
analysis
chat
coverage
review
audit
evals

Long jobs return job IDs.

Do not keep HTTP connections open for multi-minute AI pipelines.

============================================================
BACKGROUND JOB REQUIREMENTS
============================================================

Jobs must be:

durable
idempotent
retryable
cancelable
observable
resume-safe

Persist intermediate artifacts.

Never recompute expensive OCR/embeddings unnecessarily.

============================================================
FAILURE MODEL
============================================================

One broken file:
mark file failed
continue package where safe

One failed model call:
retry according to policy
then escalate/fail isolated task

One failed rule:
mark incomplete
never call overall analysis complete

Unresolved critical item:
analysis status = NEEDS_REVIEW

============================================================
CACHE INVALIDATION
============================================================

When a fact changes:
recompute only affected constraint subgraphs.

When a retification is added:
invalidate only dependent rule and decision graph sections when possible.

When a model/prompt changes:
old analysis remains immutable.
New analysis receives new run/version.

============================================================
PHASED IMPLEMENTATION
============================================================

DO NOT implement the whole platform shallowly in one pass.

Implement sequentially.

PHASE FOUNDATION

Deliver:
monorepo
CI
database
migrations
authentication foundation
tenant model
object storage
basic audit
typed schemas
developer environment
tests

Gate:
all tests pass.

PHASE DOCUMENT CORE

Deliver:
uploads
versioning
hashing
document jobs
canonical document format
PDF/DOCX/PPTX/XLSX/MD/TXT support
OCR abstraction
element IDs
source viewer

Gate:
fixture documents round-trip correctly.

PHASE SEARCH

Deliver:
lexical index
vector index
hybrid retrieval
metadata filters
reranker abstraction
retrieval tests

PHASE NORMATIVE DISCOVERY

Deliver:
ontology
candidate extraction
atomic rule schema
evidence schema
initial specialized agents
Jev adapter for narrow classifications

Do not implement final eligibility yet.

PHASE CONSTRAINT GRAPH

Deliver:
typed AST
logical groups
scope
temporal semantics
exceptions
edge evidence
node verifier
edge verifier

Gate:
gold examples reproduce expected logical graph.

PHASE SOLVER

Deliver:
deterministic evaluator
UNKNOWN semantics
CONFLICT semantics
applicability
quantifiers
aggregates
arithmetic
dates
precedence
partial evaluation
minimal blocker sets

Gate:
solver tests run without AI.

PHASE FACT GRAPH

Deliver:
organization/project models
fact assertions
provenance
verification
fact resolution
conversation-to-fact interpreter

PHASE PERSONALIZED ANALYSIS

Deliver:
organization/project × tender
solver result matrix
blocking requirements
evidence viewer
explanations

PHASE RETIFICATIONS

Deliver:
document relationship graph
amendment detection
precedence
history

PHASE CHAT

Deliver:
KB questions
personalized solver-aware questions
source citations
fact capture

PHASE EVALS

Expand:
gold datasets
regression framework
model comparison
Jev calibration
critical miss metrics

PHASE HARDENING

Deliver:
security review
RLS tests
tenant isolation tests
load testing
failure injection
observability
cost controls
rate limits
backup/restore
disaster recovery documentation

PHASE UX POLISH

Only after core invariants are passing.

============================================================
RULE FOR CODING AGENT EXECUTION
============================================================

At the beginning of every work session:

1. read MASTER_SPEC.md;
2. read INVARIANTS.md;
3. read PHASE_STATUS.md;
4. inspect repository state;
5. identify current phase;
6. implement only work belonging to that phase unless a prerequisite fix is
   necessary.

At the end of each phase:

1. run tests;
2. run lint;
3. run type checking;
4. run migrations in clean database;
5. document known limitations;
6. update PHASE_STATUS.md;
7. create/update ADRs;
8. verify invariants;
9. only then continue to next phase.

Do not create fake implementations merely to make tests green.

Do not use TODO handlers on production paths.

Do not mark a feature complete if core behavior is mocked.

============================================================
DEFINITION OF DONE
============================================================

A feature is not done because its screen exists.

It is done only when:

domain model exists
database persistence works
authorization works
API contract works
job behavior works where relevant
error behavior is defined
observability exists
unit tests exist
integration tests exist
auditability exists
relevant invariants pass

============================================================
ANTI-GAMBIARRA RULES
============================================================

Forbidden:

one giant prompts.py containing business logic
one giant service.py
PDF text stored only as giant string
eligibility decided by chatbot prompt
boolean fields that erase UNKNOWN state
catch-all exception handlers hiding failures
silent retries without accounting
hard-coded tenant IDs
hard-coded provider/model names throughout domain logic
fake async jobs
storing all state only in browser
production mocks
unversioned prompts
unversioned schemas
untraceable AI claims
dropping old rules after retification
overwriting user facts without history

============================================================
FIRST TASK
============================================================

Do NOT start by generating the entire application.

First:

1. create MASTER_SPEC.md based on this specification;
2. design architecture;
3. design complete relational/domain model;
4. define Constraint DSL;
5. define solver semantics;
6. define all invariants;
7. create ADRs for major choices;
8. define repository structure;
9. define implementation phases;
10. create representative fixtures.

Fixtures must include at minimum:

CASE A — simple AND eligibility

Brazil AND Public

CASE B — alternative path

Brazil AND
(
 Public
 OR
 (Private AND PublicICTPartner)
)

CASE C — exception

general rule
UNLESS exception

CASE D — retification

deadline 10/10
superseded by 17/10

CASE E — unknown fact

rule exists
organization fact absent

CASE F — conflicting facts

user declaration says public
verified document says private

CASE G — scope

rule applies to PROPONENT but not PARTNER

CASE H — cardinality

at least 2 PhD researchers

CASE I — budget percentage

third-party expenses <= 30%

CASE J — external dependency

rule references absent manual

CASE K — conflicting official documents

no proven precedence

CASE L — eliminatory document requirement

missing document makes submission invalid

After architecture and fixtures exist, begin FOUNDATION.

============================================================
ULTIMATE PRODUCT QUALITY BAR
============================================================

The system's goal is NOT:

"AI seems smart when asked questions."

The quality bar is:

"For any material conclusion, we can show:
what source text created the rule,
how the rule was formalized,
how it relates to other rules,
what facts were used,
where those facts came from,
how deterministic evaluation produced the status,
what is still unknown,
what conflicts exist,
and why the natural-language answer says what it says."

When forced to choose between:
a beautiful answer with unsupported certainty
and
an ugly but auditable UNKNOWN,

choose UNKNOWN.

When forced to choose between:
a fast shortcut
and
preserving evidence and semantics,

preserve evidence and semantics.

This is an evidence-first, constraint-driven system.
Build accordingly.
```

### O ponto final

Depois desta pesquisa, eu faria uma mudança até na forma de descrever o produto.

Eu não o venderia tecnicamente como:

> **“IA que lê editais.”**

Eu o definiria internamente como:

> **“Sistema que compila documentos de um edital em um modelo normativo verificável e compara esse modelo com evidências de uma organização e de um projeto.”**

A diferença parece semântica, mas muda toda a engenharia.

A Harvey já mostrou publicamente que processamento documental em escala exige representação intermediária versionada, componentes identificáveis, pipelines duráveis e agentes especializados; sua própria evolução do Playbook Review mostra que regras isoladas e prompts sequenciais têm dificuldades com dependências entre diferentes partes de um documento. citeturn20view0turn21view0turn21view1 A Enter mostra, em outro domínio jurídico, a mesma direção geral de **documentos → estruturação → dados/evidências → verificações → produto jurídico**, apoiada por jobs assíncronos e persistência intermediária. citeturn21view4turn22view0turn22view1

O que eu acrescentaria especificamente para editais é justamente a camada que você identificou:

> **requisito encontrado não é ainda decisão.**

Entre os dois precisa existir:

**lógica explícita + escopo + exceções + temporalidade + precedência + fatos comprovados + solver.**

E há uma melhoria adicional que considero tão importante quanto o Constraint Graph: **não basta citar cada requisito; também devemos provar as relações entre os requisitos**. `R1`, `R2` e `R3` podem estar perfeitamente extraídos e, ainda assim, um único `AND` convertido erroneamente em `OR` destruir toda a análise. A inspiração jurídica formal para tratar regras, condições, proveniência, temporalidade, exceções e relações explicitamente já existe em padrões como LegalRuleML. citeturn16view0turn17view1

Finalmente, Jev encaixa excepcionalmente bem **nas milhares de pequenas perguntas ao redor desse motor**, porque a própria TypeSafe recomenda decisões atômicas e a composição em código. Ele pode baixar custo e latência de classificação, roteamento, evidence triage e matching preliminar; porém o solver, os cálculos e o estado jurídico efetivo permanecem determinísticos. citeturn21view6turn21view7

O resultado é uma arquitetura em que a pergunta:

> **“Meu projeto pode participar deste edital?”**

não é enviada para uma IA esperando que ela “pense direito”.

Ela vira uma consulta sobre um sistema de evidências:

```text
EDITAL
→ 428 regras verificadas
→ 173 relações lógicas verificadas
→ 9 exceções
→ 3 retificações
→ grafo normativo vigente

                    ×

ORGANIZAÇÃO
→ 81 facts
→ 69 verificados
→ 10 declarados
→ 2 desconhecidos

                    ×

PROJETO
→ 114 facts
→ 103 verificados
→ 11 declarados

                    ↓

SOLVER

Elegibilidade institucional       SATISFIED
Elegibilidade do coordenador      SATISFIED
Área temática                     SATISFIED
TRL                               SATISFIED
Orçamento                         UNSATISFIED
Documentação                      UNKNOWN
Impedimentos                      SATISFIED

                    ↓

RESULTADO GLOBAL
UNSATISFIED

Porque:
despesa X = 34%
limite do edital = 30%

Adicionalmente:
não foi possível verificar documento Y.

                    ↓

FONTES EXATAS
```

**Esse é o desenho que eu consideraria próximo do melhor que podemos justificar hoje com o que é publicamente conhecido sobre Harvey, Enter, Jev e representação computável de regras — e é substancialmente mais robusto do que um RAG, um “chat com PDF” ou até uma arquitetura puramente multiagente.**