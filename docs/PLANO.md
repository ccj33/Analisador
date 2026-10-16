# PLANO — Analisador de editais (versão 2, 16/10/2026)

Plano de execução para um agente do Claude Code numa sessão nova. Foi escrito para ser seguido sem adivinhar, inclusive por um modelo menor que o que o escreveu. Cada fase diz:

- **Por quê:** a razão e de onde veio a ideia.
- **Onde achar:** arquivos, bibliotecas, sites e documentos.
- **Como fazer:** passos, nomes de arquivo, formatos e testes.
- **Pronto quando** e **Armadilhas.**

Se algo não bater com o que está escrito aqui, pare e pergunte ao dono antes de improvisar.

Para começar a sessão, o dono cola:

> Leia docs/PLANO.md inteiro e execute a partir da Fase 0. Parta de origin/claude/busy-einstein-87aa7b e trabalhe no branch indicado pela sessão.

## Sumário

- Parte A — Contexto: decisões do dono, constituição, estado atual e glossário
- Parte B — A arquitetura alvo e por que é esta
- Parte C — Fases 0 a 11
- Parte D — Regras para todas as fases
- Parte E — Onde achar: links, bibliotecas e licenças
- Parte F — Pendências do dono e Estado

---

## Parte A — Contexto

### A1. O produto

Um app web que lê editais de fomento (FAPEMIG, CNPq, FINEP e outros), lista as exigências em português simples com o trecho do edital que prova cada uma e diz se um proponente pode concorrer.

Numa busca de 16/10/2026 não apareceu nenhuma plataforma no Brasil que faça análise de elegibilidade em editais de fomento. O que existe de mais próximo:

- um trabalho acadêmico para licitação (LICITA.AI);
- resumidores de edital de concurso;
- uma IA que ajuda a redigir projetos para leis de incentivo;
- um protótipo acadêmico que coleta editais de CAPES, CNPq e FINEP.

### A2. Decisões do dono (não reabrir sem ele pedir)

| Tema | Decisão |
| --- | --- |
| Quem usa | Só o dono e a equipe. Acesso com senha; um admin cria as contas; sem cadastro aberto. |
| Onde roda | Na internet, numa hospedagem de custo baixo (Fase 10). |
| Telas | Editais, Resumo do edital, Revisão e "Posso concorrer?". |
| Uso | Vários editais de uma vez. Qualquer pessoa precisa entender. Tem que funcionar no celular. |
| IA | O Jev (TypeSafe) faz a triagem. O modelo forte ainda não foi escolhido ("decido depois"): Claude, Gemini ou Grok. |
| Estilo | "Sem mock": nenhum resultado fingido. Dublês só dentro dos testes. |
| Trava | Nunca dizer "pode concorrer" para quem não pode. Se sobrou cláusula de elegibilidade sem verificar, a resposta é "pode concorrer nos itens verificados; faltam N cláusulas". |

### A3. A constituição do projeto, com o porquê

Vem de `docs/MASTER_SPEC.md`.

1. **A IA trabalha na linha de produção; nunca decide a elegibilidade.**
   - Um artigo de 2026 testou regras do tipo "exigido, a não ser que, a não ser que": o motor determinístico acertou 20 de 20 casos e três de quatro configurações de modelos de ponta erraram o mesmo caso. É um preprint da empresa que vende essa arquitetura.
   - O mesmo artigo viu o resultado de um modelo mudar sem troca de versão.
   - Quem decide é o solver (`src/tender_intel/domain/solver.py`).
2. **Toda regra e toda ligação entre condições têm um trecho do edital, conferido pelo código.** Em relatos de quem roda isso em produção (Hacker News, Reddit), o maior risco é a IA inventar ou deslocar citações. A prática recomendada é ligar cada valor a página, trecho, posição e confiança, e marcar o que não tem apoio no texto.
3. **Entre uma resposta bonita sem prova e um "não sei" que mostra o que falta, fique com o "não sei".**
4. **Nada do que foi lido some em silêncio.** Cada cláusula vira regra, descoberta ou "sem classificação" (`src/tender_intel/compile/coverage.py`).
5. **A edição humana prevalece sobre a IA.**
6. **Falso "pode concorrer" é zero, sempre.**

### A4. Estado atual (16/10/2026)

- **Repositório:** `ccj33/Analisador`, branch `claude/busy-einstein-87aa7b`. O PR #1 (rascunho) vem do branch `claude/analisador-sem-mock-ojc8f8` e não tem os últimos commits.
- **Pacote:** Python ≥ 3.11, `tender_intel` em `src/`, depende só de `pypdf`.
  - Instalar: `python -m pip install -e ".[dev]"`.
  - Testar: `python -m pytest` (46 testes passam).
  - Medir: `python -m tender_intel.cli eval --case gold/cases/<caso>.json`.
- **Ingestão** (`src/tender_intel/ingest/`):
  - `pdf.py` lê a camada de texto com o `pypdf`;
  - `docx.py` lê DOCX sem dependência;
  - `clauses.py` junta linhas em cláusulas (item, alínea, título), tira o rodapé do SEI e guarda a página;
  - `text.py:ingest_package` monta o pacote a partir de `package.json`.
- **Compilador** (`src/tender_intel/compile/`):
  - `extract.py` tem as regex do edital sintético e acha 0 das 38 regras nos editais reais. Bug: na linha 118, a regra de prazo só nasce se "Brasília" e a hora estiverem na mesma cláusula da data.
  - `discover.py` acha prazo, referências externas e efeitos.
  - `coverage.py` classifica todas as cláusulas.
- **Domínio** (`src/tender_intel/domain/`): `ast.py` (expressões), `solver.py` (Kleene), `rules.py`, `evidence.py` (`check_span` confere a citação), `facts.py`.
- **Eval** (`src/tender_intel/eval/`): `harness.py:measure_case` mede o caso com o grafo anotado e com o compilado; `rules.py:compare_rules` compara regra a regra (MATCH, DIFFERENT_LOGIC, OMITTED, INVENTED); `values_missing_from_evidence` confere números e datas na citação.
- **Explicação:** `src/tender_intel/explain.py` gera a frase em português simples a partir da expressão.
- **Gabarito:** `gold/build.py` escreve os gabaritos citando seção e trecho e gera os `fixtures/*/graph.json`.
  - São três editais reais: `fapemig-sede-018-2026` (15 regras), `cnpq-arc-34-2026` (13) e `cnpq-anr-32-2026` (10). Há também o sintético `cnpq-universal-sintetica`.
  - Cada edital real tem três perfis de teste: elegível, incompleto e inelegível.
  - Em 16/10 o dono conferiu as 38 regras: 31 certas e 8 corrigidas (`docs/GOLD_SET.md`, "Conferência humana"). As 8 corrigidas esperam nova conferência dele.
- **Página de conferência:** `gold/export_review.py` com `gold/review_page.html`, publicada em https://claude.ai/artifact/AuxmKTXqc81vm87ztECEke e aberta para quem tiver o link.
  - Guarda as marcações no banco da página, coleção `reviews`, com os campos `verdict`, `note`, `by`, `at`, `rev` e `via`.
  - Marcação com `rev` diferente da versão atual da regra conta como pendente.
- **IA:** `src/tender_intel/ai/provider.py` tem o `AbstainProvider` (padrão) e o `JevProvider`, que ainda não faz chamada HTTP. Sobre o Jev 1.14, que saiu em 14/10 como prévia:
  - trouxe ganho em idiomas além do inglês;
  - imagens, o tipo Box e o contexto longo são experimentais e ficam desligados aqui.
- **Rede das sessões:**
  - bloqueia `gov.br`, `cnpq.br`, `fapemig.br`, `api.typesafe.ai`, `api.x.ai` e `api.openai.com`;
  - libera pypi, npm, `api.anthropic.com` e `generativelanguage.googleapis.com`.

  As chaves entram como Network secrets nas configurações do ambiente.
- **Navegador para testes:** o Chromium está em `/opt/pw-browsers/chromium-1194/chrome-linux/chrome`, e o Playwright para Node (1.56.1) já está instalado globalmente e funciona. Não rode `playwright install`.

### A5. Glossário

| Termo | O que é |
| --- | --- |
| Pacote | Edital, anexos, retificações e FAQ de uma chamada |
| Cláusula (elemento) | Trecho numerado do documento ("3.2.1, alínea b"), com página |
| Regra | Expressão lógica sobre fatos (`coordinator.has_phd == true`), com trechos do edital que a provam |
| Fato | Informação do proponente, por uma chave do catálogo, com data e fonte |
| Gabarito (gold) | Regras anotadas e conferidas por pessoa; é a régua de medição |
| dev / prova | Editais usados para desenvolver / editais guardados só para medir no fim |
| Kleene | Lógica de três valores: sim, não e não sei |
| rev | Versão do que a pessoa conferiu numa regra; mudou a regra, a conferência antiga perde a validade |

---

## Parte B — A arquitetura alvo e por que é esta

```
[Fontes] CNPq · FAPEMIG · FINEP · Diário Oficial (INLABS)     ← Fase 9; ou envio manual no app
      ▼
[1 Ingestão]     arquivo original, sha256, tipo (edital/anexo/retificação), versão       ← Fase 4
      ▼
[2 Leitura]      texto em cláusulas (pypdf, já existe) + posição de cada trecho
                 na página (pdfplumber) + segundo leitor para tabelas e páginas
                 escaneadas (Docling)                                                     ← Fase 3
      ▼
[3 Triagem]      Jev: é exigência? elimina? de quem? qual item do catálogo?               ← Fase 5
      ▼
[4 Extração]     modelo forte, só no que a triagem marcou como difícil; por seção;
                 duas passadas independentes                                              ← Fase 5
      ▼
[5 Conferência]  código: o trecho existe, os números batem, o fato existe no catálogo
                 Z3: as regras não se contradizem, nenhuma é impossível ou vazia          ← Fases 5 e 6
                 falhou → fila de Revisão (pessoa)
      ▼
[6 Grafo normativo verificado]  regras + trechos + posição + versão (rev)
      ▼
[7 Solver Kleene] + fatos do perfil → Pode / Não pode (motivo e trecho) / Falta informar  ← Fase 7
      ▼
[8 Telas]        Resumo com o trecho marcado no PDF · Revisão · Posso concorrer? · Avisos
```

Por que cada camada, e de onde veio a ideia:

| Camada | Por quê | Fonte da ideia |
| --- | --- | --- |
| Fila em fases, estado no banco, arquivos guardados | Trabalho pesado não pode travar a tela; cada etapa precisa ser refeita sem refazer tudo | Blog de engenharia da Enter: valida antes do LLM, jobs assíncronos, fases, etapa cara em paralelo, arquivos no S3 e estado no PostgreSQL (resumo no `deep-research-report.md`) |
| Posição do trecho na página | Quem lê confia quando vê o trecho marcado no PDF original; também evita citação deslocada | Relatos de produção (Ask HN): página, trecho, caixa de posição e confiança em cada campo |
| Segundo leitor para tabelas | Hoje as tabelas viram uma linha corrida (FAPEMIG 5.1, CNPq 34 item 4.3). Em 2026, leitores que leem a página como imagem lideram os testes de tabela, mas os rankings variam | ParseBench, olmOCR-Bench e PDF Parse Bench (Parte E) |
| Triagem barata antes da extração cara | O Jev responde perguntas curtas rápido e por centavos; o modelo forte só lê o que precisa | `docs/JEV_POLICY.md`; preço divulgado do Jev |
| Extração por seção, juntada no fim | Cada parte é menor e mais fácil; a junção resolve "ressalvado o disposto no item X" | A Harvey trocou a revisão de contratos por um orquestrador com agentes por regra; diz que a classificação de riscos subiu de 59% para 77%, com mais tempo de resposta (números da própria Harvey) |
| Duas passadas independentes | Onde duas leituras discordam, há chance de erro: vai para pessoa | Prática de redução de erro silencioso; a mesma ideia já usamos para os leitores de texto e tabela |
| Posição exata de cada valor | Permite conferir na hora se o valor saiu daquele trecho | LangExtract (biblioteca de código aberto): cada valor ligado ao trecho exato do texto |
| Z3 ao lado do solver | Acha regras contraditórias ou impossíveis (sinal de leitura errada), gera perfis de teste e calcula o mínimo que falta para ser elegível | Artigos de 2026 que juntam LLM e solver formal (Aethis, compliance em Taiwan, direito penal coreano, PolicyLLM no ICML) |
| Solver decide | Modelos erram exceções encadeadas e mudam sem aviso | Artigo "Confidently Wrong" (Aethis, 2026) |
| Monitoramento das fontes | O valor está em saber primeiro que saiu edital novo ou retificação | A Enter liga-se às fontes e estrutura em escala; o protótipo acadêmico SBC já coleta editais de CAPES, CNPq e FINEP |

O que **não** fazer, e por quê:

- **Chat com o PDF como centro do produto:** não dá prova nem cobertura.
- **Treinar um modelo próprio:** caro, e não resolve verificação.
- **Agentes em tudo:** mais custo e mais tempo, sem ganho onde a tarefa é simples.
- **Busca vetorial no edital inteiro para decidir:** perde exceções e referências cruzadas.
- **Funções experimentais do Jev:** a própria TypeSafe diz que não estão prontas para produção.
- **Deixar a IA dar o veredito:** viola a constituição.

---

## Parte C — Fases

Ordem: 0 → 1 → 2 → 3A → 4 → 5 → 6 → 7 → 3B → 8 → 9 → 10, com a 11 contínua.

- Pode adiantar a 4 junto da 2 e da 3A.
- Se uma fase esperar algo do dono, siga para a próxima e volte quando chegar.
- O que depende do dono está marcado **[DONO]**.

### Fase 0 — Começo da sessão

**Por quê:** partir do estado certo e saber o que já chegou do dono.

**Como fazer:**

1. Crie o branch da sessão a partir do código atual:
   - `git fetch origin claude/busy-einstein-87aa7b`
   - `git checkout -B <branch-da-sessão> origin/claude/busy-einstein-87aa7b`
2. Instale e teste: `python -m pip install -e ".[dev]"` e `python -m pytest`. Os 46 testes têm de passar.
3. Linha de base: rode o eval nos quatro casos de `gold/cases/` e anote no "Estado":
   - regras do compilador por caso (MATCH, OMITTED, INVENTED);
   - resultado de cada perfil.
4. Marcações do dono:
   - Com a ferramenta `ArtifactData`, faça `list` na coleção `reviews` do link da página.
   - Gere as versões atuais com `python gold/export_review.py <scratchpad>/atual.json` e compare os campos `rev`.
   - Diga ao dono quantas das 8 corrigidas ele já conferiu e o que marcou.
5. Chaves e rede (nunca imprima o valor de uma chave):
   - `test -n "$JEV_API_KEY" && echo ok`;
   - `curl -sS -o /dev/null -w '%{http_code}' -X POST https://api.typesafe.ai/v1/systemone`: 401 quer dizer liberado; falha de túnel 403 quer dizer bloqueado.
   - Faça o mesmo para o provedor do modelo forte, se o dono já tiver escolhido.

**Pronto quando:** testes passando, linha de base anotada e o dono sabe o que falta da parte dele.

### Fase 1 — Fechar o gabarito e endurecer a medição

**Por quê:** sem uma régua confiável, nenhum número de acerto vale.

- O gabarito foi escrito pela IA e conferido pelo dono; 8 regras mudaram depois disso e ainda não foram conferidas.
- O eval de hoje "aprova" respostas "não sei" por acaso: 3 de 9 perfis batem só porque o compilador responde "não sei" para todos.

**Onde achar:**
- `gold/build.py`, `fixtures/*/facts-*.json` e `tests/test_gold_review.py`;
- `src/tender_intel/eval/harness.py` e `src/tender_intel/cli.py` (`_eval`);
- `gold/export_review.py` e `gold/review_page.html`.

**Como fazer:**

1. **As 8 regras.** Para cada marcação "Tem erro" ou "Não tenho certeza":
   - confira o texto com o script que imprime as cláusulas da seção (padrão usado em `gold/export_review.py`: `ingest_package` e filtro por `section_path`);
   - corrija em `gold/build.py` e rode `python gold/build.py`, que para se uma citação não existir;
   - acrescente aos perfis os fatos novos, sem mudar o resultado esperado de nenhum deles;
   - escreva um teste em `tests/test_gold_review.py` com o caso que o dono apontou;
   - republique a página no mesmo link: `python gold/export_review.py <scratchpad>/conferencia-gabarito.html` e depois a ferramenta Artifact, ação publish, com `url` = o link da página.
2. **Travas do eval**, em `harness.py:measure_case`:
   - acrescente `false_eligible`: a contagem de perfis com resultado esperado diferente de SATISFIED que saíram SATISFIED. Se for maior que zero, `ok = False`, nos dois caminhos (anotado e compilado);
   - acrescente por caso `decided_right` (saiu igual ao esperado e não é UNKNOWN), `abstained` (saiu UNKNOWN quando se esperava outra coisa) e `wrong`;
   - em `cli.py:_eval`, imprima antes do JSON um resumo de uma linha por caso;
   - testes em `tests/test_eval.py`: um perfil inventado que sai SATISFIED por engano tem de reprovar.
3. **Rótulos de cláusula para calibrar o Jev.** Arquivo `gold/labels/<caso>.json`:
   ```json
   {"case": "cnpq-arc-34-2026", "labels_version": 1, "clauses": [
     {"section": "3.2.1/b", "text_sha": "<sha256 do texto normalizado>",
      "is_requirement": true, "is_eliminatory": "sim", "actor": "COORDINATOR",
      "catalog_item": "coordinator.has_phd", "has_exception": false,
      "labeled_by": "agente", "checked_by_owner": false}
   ]}
   ```
   - Use seção e sha do texto, não `element_id`, porque o `element_id` muda quando a leitura muda (lição já aprendida no gabarito).
   - Seções que entram: FAPEMIG, itens 3, 5 e 13; CNPq 34, itens 1.3, 2, 3, 4 e 6; CNPq 32, itens 2, 3, 4 e 6. Vão dar algo como 150 a 250 cláusulas.
   - `is_eliminatory` aceita "sim", "nao" ou "nao_diz".
   - Você faz a primeira marcação. Para o dono conferir uma amostra (umas 40 cláusulas, misturando exigências e não exigências), estenda a página de conferência com uma aba "Cláusulas" que usa o mesmo mecanismo de `rev` e grava na coleção `labels`.
4. **Separar dev e prova.**
   - Em cada `gold/cases/*.json`, acrescente `"split": "dev"`.
   - Os editais que o dono mandar entram com `"split": "test"`.
   - Acrescente `--split dev|test` ao comando de eval.
   - **[DONO]** Peça 2 ou 3 editais novos, de órgãos diferentes e um com retificação publicada. Onde achar: Parte E, "Fontes de editais".
   - Monte a fixture e o gabarito de cada um como nos outros, mas sem ajustar nada do extrator olhando esses editais.
5. **Registro de execuções:** salve cada eval em `gold/runs/<data>-<motor>.json`, com a versão do motor e dos modelos. É a base para detectar mudança de comportamento de modelo (Fase 11).

**Testes:** `tests/test_eval.py` com a trava de falso elegível e os três números.

**Pronto quando:**
- as 8 regras estão resolvidas (ou o dono adiou explicitamente);
- o eval tem a trava e os três números;
- os rótulos dos três editais estão feitos, com amostra conferida pelo dono;
- os editais de prova foram pedidos.

**Armadilhas:**
- As aspas tipográficas do edital (“ ”) precisam ser copiadas iguais nas citações.
- Nunca mude o resultado esperado de um perfil para "fazer passar". Se ele mudou, foi porque a regra mudou: explique no commit.

### Fase 2 — Catálogo de exigências

**Por quê:** o catálogo é a lista de fatos que o proponente pode responder. Ele vira três coisas:
- as opções da pergunta de escolha do Jev;
- o formato da saída do modelo forte;
- as perguntas da tela "Posso concorrer?".

Hoje esse vocabulário está espalhado em `explain.py`.

**Onde achar:**
- `src/tender_intel/explain.py` (`BOOL_FACTS`, `ENUM_FACTS`, `NUMBER_FACTS`, `DATE_FACTS`);
- as chaves usadas em `gold/build.py`.

**Como fazer:**

1. Crie `src/tender_intel/catalog.py`:
   ```python
   @dataclass(frozen=True)
   class FactSpec:
       key: str                      # "coordinator.has_phd"; nunca renomear (o eval pareia por ela)
       entity: str                   # organization | coordinator | subcoordinator | institution | project | event | proposal | submission
       kind: str                     # bool | enum | number | date
       question: str                 # "Você tem doutorado?"
       help: str = ""                # o que conta, em uma frase
       yes: str = ""                 # bool: frase quando verdadeiro (hoje em BOOL_FACTS)
       no: str = ""
       subject: str = ""             # enum, number, date: "o valor pedido é de"
       values: dict = field(default_factory=dict)   # enum: valor → rótulo
       unit: object = None           # "brl" | "pct" | "mb" | ("mês", "meses")
       show_time: bool = False       # date: mostrar a hora
       proof: str = ""               # documento que costuma provar: "Currículo Lattes"

   CATALOG: dict[str, FactSpec] = {...}
   ```
2. Passe para o catálogo tudo o que está hoje em `explain.py` e faça o `explain.py` ler do catálogo, sem copiar.
3. Escreva a pergunta de cada fato em português simples, na segunda pessoa, com no máximo 12 palavras. Exemplos:
   - "Você tem doutorado?"
   - "Seu currículo Lattes está atualizado?"
   - "Qual é o seu vínculo com a instituição?" (as opções vêm de `values`)
   - "Quanto você vai pedir, em reais?"
4. Testes em `tests/test_catalog.py`:
   - todo fato usado em `fixtures/*/graph.json` está no catálogo;
   - toda entrada tem `question`;
   - os rótulos de enum cobrem os valores do gabarito;
   - as frases geradas para as 38 regras saem iguais às de antes (compare com `python gold/export_review.py` gerado antes da mudança).

**Pronto quando:** os testes passam e a página de conferência sai igual.

**Armadilhas:** não invente fatos que o gabarito não usa. O catálogo cresce quando aparecer uma exigência nova num edital real.

### Fase 3A — Posição de cada trecho na página

**Por quê:** para o app mostrar o trecho marcado em amarelo no PDF original e para conferir a citação pela posição. É o que fazem os sistemas de produção relatados no Hacker News: página, trecho, caixa e confiança em cada campo.

**Onde achar:**
- `pdfplumber` (PyPI; licença MIT, conferir no PyPI). Ele dá as palavras com caixa: `page.extract_words()` devolve `x0`, `x1`, `top` e `bottom` em pontos, com `page.width` e `page.height`. Documentação: https://github.com/jsvine/pdfplumber
- Os PDFs reais do gabarito: `fixtures/cnpq-arc-34-2026/chamada.pdf` e `fixtures/cnpq-anr-32-2026/chamada.pdf`. O FAPEMIG só tem o texto (`edital.txt`); sem o PDF dele, a posição fica de fora nesse caso.

**Como fazer:**

1. **Não troque o leitor de texto.** As cláusulas e o gabarito dependem do `pypdf`. A posição é uma camada a mais.
2. Crie `src/tender_intel/ingest/positions.py`:
   ```python
   @dataclass(frozen=True)
   class Box:
       page: int          # 1 = primeira página
       x0: float; top: float; x1: float; bottom: float   # 0..1, frações da largura e da altura da página

   def locate(pdf_path: Path, page: int, quote: str) -> list[Box]:
       """Uma caixa por linha do trecho; lista vazia se não achar."""
   ```
   - Normalize palavras e trecho do mesmo jeito: espaços colapsados, ligaduras ("ﬁ" vira "fi"), hífen de quebra de linha ("obri-" mais "gatório" vira "obrigatório") e aspas iguais.
   - Procure a sequência de palavras do trecho na sequência de palavras da página. Se não achar, tente a página seguinte, porque o trecho pode quebrar de página.
   - Junte as caixas por linha (mesmo `top`, com tolerância de 2 pt) e divida pelo tamanho da página.
3. Guarde as caixas junto da evidência quando o documento for PDF. Na exportação da página de conferência e no app, cada trecho ganha `boxes`.
4. Para DOCX não há geometria. O app mostra o parágrafo destacado numa vista de texto.

**Testes** (`tests/test_positions.py`): para três citações do gabarito do CNPq 34 ("possuir o título de Doutor", a tabela do 4.3 e "limitando-se a 1Mb (um megabyte)"), `locate` acha a página certa e caixas dentro de 0..1.

**Pronto quando:** pelo menos 95% das citações dos dois PDFs do CNPq têm caixa.

**Armadilhas:** não use PyMuPDF. A licença dele (AGPL) obrigaria a abrir o código do app.

### Fase 3B — Segundo leitor para tabelas e páginas escaneadas

**Por quê:** hoje as tabelas viram uma linha corrida, e páginas sem texto ficam marcadas para OCR sem serem lidas. Os testes públicos de 2026 mostram leitores visuais muito melhores em tabelas, mas o ranking muda de um teste para outro. Por isso é preciso medir nos nossos editais.

**Onde achar:**
- **Docling** (IBM; código com licença MIT; os modelos que ele baixa têm licenças próprias, que é preciso conferir). Usa TableFormer para a estrutura de tabelas e RapidOCR para páginas escaneadas.
  - PyPI: `docling`. Código: https://github.com/docling-project/docling
  - Confira a versão no PyPI. As fontes divergem: 2.95 em maio, 2.112 em julho de 2026.
- Alternativas e por que não são o padrão:
  - Chandra 2 (Datalab): os pesos têm licença OpenRAIL-M modificada, que só libera uso comercial para empresas com menos de US$ 2 milhões de receita ou captação e proíbe concorrer com a API deles. Só use com o dono ciente.
  - MinerU: confira a licença antes.
  - Um modelo de visão por API (Gemini passa na rede): opção para páginas difíceis.

**Como fazer:**

1. Instale o Docling como extra opcional (`[project.optional-dependencies] tables = ["docling==<versão conferida>"]`). Ele é pesado (usa torch) e só roda no worker, nunca nos testes rápidos.
2. Crie `src/tender_intel/ingest/tables.py` com `read_tables(pdf_path, pages) -> list[Table]`, em que `Table = {page, rows: list[list[str]], boxes}`. As páginas lidas são as que têm tabela (detectada pelo layout do Docling) ou estão em `needs_ocr_pages`.
3. Para cada tabela, compare os números (R$, %, datas) com a cláusula correspondente do texto. Se baterem, a tabela vira um elemento a mais (`kind="table"`) com as linhas estruturadas. Se divergirem, marque a cláusula para revisão.
4. Meça antes e depois na tabela do 4.3 do CNPq 34 e na do 5.1 do FAPEMIG (quando o dono mandar o PDF). Só adote se melhorar.

**Pronto quando:** as linhas da tabela do 4.3 saem com Linha, descrição e valor separados, e a extração da Fase 5 usa a tabela.

**Armadilhas:**
- Não substitua a camada de texto nos casos do gabarito.
- O Docling baixa modelos na primeira execução, e a rede da sessão pode bloquear. Rode no worker de produção ou peça ao dono para liberar o domínio de download.

### Fase 4 — App web: base, login, envio, Resumo e Revisão

**Por quê:** é o produto que o dono e a equipe vão usar. Começa com o motor atual, para não esperar as chaves de IA.

**Onde achar:**

| Biblioteca | Para quê |
| --- | --- |
| FastAPI e Uvicorn | Servidor |
| Jinja2 e HTMX | Páginas renderizadas no servidor. Um serviço só, mais fácil de hospedar. O HTMX vai como arquivo em `static/`, numa versão fixa como 2.0.4. |
| SQLAlchemy 2 e Alembic | Banco e migrações |
| argon2-cffi | Senhas |
| python-multipart | Envio de arquivos |
| httpx | Chamadas externas |
| pdf.js (`pdfjs-dist` no npm, Apache-2.0) | Visualizador de PDF. Copie `pdf.min.mjs` e `pdf.worker.min.mjs` de uma versão fixa para `static/`. |
| Fontes | Schibsted Grotesk, Source Serif 4 e IBM Plex Mono, em woff2 servidos de `static/` (baixados do Google Fonts ou do Fontsource) |

O visual vem dos tokens de cor, das fontes, dos carimbos e do marca-texto de `gold/review_page.html`.

**Como fazer:**

1. **Pastas:** `src/tender_intel/web/`, com `app.py` (cria a app), `settings.py` (lê as variáveis de ambiente), `db.py`, `models.py`, `auth.py`, `jobs.py`, `worker.py`, `routes/` (`editais.py`, `revisao.py`, `perfis.py`, `admin.py`), `templates/` e `static/`. As migrações ficam em `migrations/`.
2. **Variáveis de ambiente:** `DATABASE_URL` (padrão `sqlite:///./dev.db`), `SECRET_KEY`, `STORAGE_PATH` (padrão `./storage`), `JEV_API_KEY`, `EXTRACTOR_PROVIDER` (`none`, `anthropic`, `gemini` ou `xai`; padrão `none`) e a chave do provedor escolhido.
3. **Tabelas:**
   - `users`: id, email único, nome, password_hash, is_admin, created_at
   - `calls`: id, título, órgão, número, ano, status (`recebido`, `lendo`, `pronto`, `revisar` ou `erro`), created_by, created_at
   - `documents`: id, call_id, nome do arquivo, sha256, mime, tamanho, tipo (`edital`, `anexo`, `retificacao` ou `faq`), storage_path, uploaded_at
   - `jobs`: id, call_id, tipo, status (`na_fila`, `rodando`, `feito` ou `falhou`), tentativas, erro, created_at, started_at, finished_at
   - `processing_runs`: id, call_id, versão do motor, versões dos modelos, iniciado, terminado, resumo em JSON
   - `clauses`: id, document_id, element_id, seção, página, texto, sha do texto, cobertura, boxes em JSON
   - `rules`: id, call_id, regra em JSON (o mesmo formato de `rules_to_dict`), origem (`gabarito`, `compilador`, `extrator` ou `pessoa`), status (`conferida`, `a_conferir` ou `nao_verificada`), rev
   - `reviews`: id, rule_id ou clause_id, veredito, comentário, user_id, rev, created_at
   - `profiles`: id, owner_id, nome, tipo
   - `facts`: id, profile_id, chave, valor em JSON, fonte, as_of, valid_until; nunca apagados, só substituídos por um mais novo
   - `results`: id, profile_id, call_id, status, fatos que bloqueiam em JSON, computed_at
4. **Login:**
   - e-mail e senha;
   - cookie de sessão assinado, `HttpOnly`, `Secure` em produção e `SameSite=Lax`;
   - token CSRF em todo formulário;
   - 5 tentativas erradas bloqueiam por 15 minutos;
   - o comando `tender-intel create-admin --email ...` cria o primeiro admin;
   - a tela de admin cria contas e troca senhas.
5. **Envio:**
   - `POST /editais/enviar` recebe vários arquivos de uma vez.
   - O app sugere o agrupamento por chamada, lendo o nome do arquivo e a primeira página com a regex `(?i)(chamada|edital)[^0-9]{0,60}?(\d{1,3})\s*/\s*(20\d{2})`, o órgão (CNPq, FAPEMIG, FINEP, CAPES…) e a palavra "retifica".
   - A pessoa confirma os grupos e o tipo de cada arquivo.
   - Os arquivos vão para `STORAGE_PATH/<sha256>`, nunca pelo nome original, e um job entra na fila.
6. **Fila:**
   - O `python -m tender_intel.web.worker` pega um job com `SELECT ... FOR UPDATE SKIP LOCKED` no Postgres (no SQLite, uma trava simples).
   - Etapas: ingestão → posições (3A) → tabelas (3B, se houver) → triagem (Fase 5, se houver chave) → extração (Fase 5, se houver provedor) → conferência → pronto.
   - Cada etapa grava em `processing_runs`. Em caso de falha, tenta de novo até 3 vezes com espera crescente e depois marca `erro`, com a mensagem visível.
7. **Telas** (HTMX para atualizar pedaços sem recarregar):
   - **Editais** (`GET /`): lista com status. Enquanto lê, atualiza a cada 3 segundos por `hx-trigger="every 3s"`, só nos itens em andamento.
   - **Resumo** (`GET /editais/{id}`):
     - topo com título, órgão, prazo de início e de envio, valor máximo e o aviso de cobertura ("N cláusulas da parte de elegibilidade ainda não foram lidas");
     - exigências agrupadas por quem precisa cumprir, cada uma com a frase de `explain` e o selo (conferida, a conferir ou não verificada);
     - "Ver no edital" abre o trecho com marca-texto. Em PDF, o botão "Abrir no PDF" abre o visualizador do pdf.js na página, com as caixas desenhadas por cima.
   - **Revisão** (`GET /editais/{id}/revisao`):
     - uma ficha por vez, no formato da página de conferência; atalhos C (está certo), E (tem erro) e D (não tenho certeza);
     - para editar uma regra, a pessoa escolhe o fato do catálogo, a comparação e o valor. A edição grava uma regra com origem `pessoa`, que prevalece.
   - **Palavras na tela:** SATISFIED vira "Pode concorrer", UNSATISFIED vira "Não pode concorrer", UNKNOWN vira "Falta informar", CONFLICT vira "Informações em conflito" e NOT_APPLICABLE vira "Não se aplica". A camada MERIT aparece como "Critério de avaliação (não elimina)".
8. **Honestidade até a Fase 5:**
   - Nos três editais do gabarito, as regras vêm do gabarito com o selo "conferida".
   - Num edital novo, entra só o que o compilador achar, com o selo "a conferir", e o resto aparece como "não verificado".
   - Nenhuma exigência inventada.
9. **Testes:**
   - pytest para login, CSRF, envio, agrupamento, fila e permissões (quem não é admin não cria conta);
   - de ponta a ponta com Playwright para Node, em `e2e/fluxo.mjs`, rodado com `node e2e/fluxo.mjs`: entrar, enviar os PDFs do CNPq, esperar "pronto", abrir o Resumo, abrir "Abrir no PDF" e marcar uma revisão. Rode em 1280 px e em 400 px, conferindo que não há rolagem lateral nem erro no console.

**Pronto quando:**
- o app roda localmente (`uvicorn tender_intel.web.app:app` mais o worker) com tudo acima;
- os testes passam;
- o dono viu a prévia: publique uma página com imagens das telas ou mande as imagens.

**Armadilhas:**
- Não sirva os arquivos pelo caminho do disco; sirva por rota com login.
- Não guarde senha nem chave em log.
- HTMX com CSRF: mande o token no cabeçalho com `hx-headers`.

### Fase 5 — Extrator: Jev, modelo forte e conferência pelo código

**Por quê:**
- O compilador de regex não generaliza: acha 0 de 38 regras nos editais reais.
- O desenho é triagem barata (Jev), leitura cara só no difícil (modelo forte) e conferência pelo código.
- Leitura por seção e juntada no fim vem do caso da Harvey.
- Duas passadas reduzem erro silencioso.
- A posição exata vem da LangExtract.

**Onde achar:**
- `docs/JEV_POLICY.md`, `src/tender_intel/ai/provider.py` (`Question`, `Answer`, `DecisionResult`) e `src/tender_intel/compile/extract.py`.
- **Jev.** Dados de tutoriais de terceiros; confirme na documentação oficial da TypeSafe antes de codar:
  - `POST https://api.typesafe.ai/v1/systemone`, cabeçalho `Authorization: Bearer $JEV_API_KEY`, corpo `{model, state, questions}`;
  - Choice tem até 255 opções e devolve a opção, a probabilidade de cada uma e a confiança;
  - Score usa escala de 2 a 10 níveis;
  - Noul devolve a probabilidade de "sim";
  - limite padrão de 64 mil tokens por chamada e 32 mil por pergunta;
  - preço divulgado de cerca de US$ 0,042 por milhão de tokens de entrada, saída grátis.
  - A LiteLLM anunciou suporte ao Jev 1.14 e pode servir de cliente, mas um cliente próprio com `httpx` é mais simples.
- **Modelo forte:**
  - Claude: API Messages da Anthropic, com saída estruturada por ferramenta ou esquema;
  - Gemini: API com `response_schema`;
  - Grok: API da xAI, compatível com o formato da OpenAI.
  - Confira na documentação oficial de cada um como pedir saída em JSON Schema.
- **LangExtract** (https://github.com/google/langextract, Apache-2.0): referência de como ligar cada valor ao trecho exato e fazer várias passadas em documento longo. O padrão dela é o Gemini.

**Como fazer:**

1. **Bug do prazo** (`extract.py:112–118`):
   - Ache a hora ("23h59", "17h") e o "horário de Brasília" na cláusula da data, na seção do cronograma ou nas cláusulas de submissão (CNPq 34: 6.2; CNPq 32: 6.5).
   - Gere a regra de envio e, quando houver, a de início (FAPEMIG 13.1: "devem ser iniciadas no sistema EVEREST até as 17h").
   - O resultado tem de bater com `ARC-DEADLINE`, `ANR-DEADLINE` e `FAP-DEADLINE` no eval.
2. **Candidatos** (`src/tender_intel/compile/candidates.py`): busque por recall, e o Jev filtra depois.
   - Toda cláusula das seções com título de elegibilidade, proponente, instituição, proposta, contrapartida, valores, cronograma ou submissão.
   - Toda cláusula com linguagem de obrigação: `deverá`, `deve`, `devem`, `é vedad`, `não poderá`, `obrigatori`, `somente`, `exclusivamente`, `sob pena de`, `implicará`, `não serão elegíveis`, `inabilita` e `indeferi`.
3. **Adaptador do Jev** (`src/tender_intel/ai/jev.py`):
   - **Versão:** `model` com o nome exato da 1.14 (por exemplo `jev-1.14.0`; confira a grafia), nunca `jev-latest`. Sem cabeçalhos experimentais.
   - **Estado enviado:** nome do edital, título da seção, a cláusula e as cláusulas vizinhas quando curtas; no máximo uns 3 mil tokens.
   - **Perguntas por cláusula:**
     - `is_requirement` (Noul)
     - `is_eliminatory` (Noul)
     - `actor` (Choice entre os papéis de `explain.ACTORS`, mais `OTHER` e `UNCLEAR`)
     - `catalog_item` (Choice com as chaves do catálogo, mais `NONE` e `UNCLEAR`)
     - `has_exception` (Noul)
     - `has_cross_reference` (Noul)
   - **Falhas:** tempo limite de 20 segundos, uma nova tentativa só em erro temporário, e abstenção em erro 402, falta de chave ou falha de rede. O produto funciona sem o Jev.
   - **Registro:** cada chamada vai para `jev_calls` (tabela ou JSONL) com tipo de tarefa, versão do modelo, hash da entrada, perguntas, saída, probabilidades, latência e custo estimado.
   - **Testes:** respostas gravadas em `tests/fixtures/jev/*.json`, sem rede nos testes.
4. **Calibração** (`gold/calibrate.py`):
   - Rode o Jev nos rótulos da Fase 1, só no dev.
   - Para cada pergunta, ordene as respostas pela confiança. O limite de aceite automático é a menor confiança acima da qual não houve nenhum erro, com pelo menos 20 exemplos acima dela. Sem isso, a pergunta vai sempre para revisão.
   - Grave em `gold/calibration/jev-1.14.0.json` com `labels_version`.
   - Mostre ao dono em linguagem simples ("acertou 182 de 200; acima de 0,95 de certeza não errou nenhuma").
5. **Modelo forte** **[DONO escolhe o provedor]** (`src/tender_intel/ai/extractor.py`):
   - Interface `RuleExtractor.extract(section_title, clauses, catalog) -> ExtractionResult`. Uma classe por provedor; a escolhida vem de `EXTRACTOR_PROVIDER`.
   - Só é chamado para cláusula que o Jev marcou como exigência e em que `catalog_item` ficou abaixo do limite, `has_exception` deu sim, a cláusula tem "ou" ou tem várias condições.
   - Esquema de saída:
     ```json
     {"status": "ok | nao_sei | nao_e_exigencia",
      "logic": "todas | uma",
      "conditions": [{"fact": "<chave do catálogo>", "op": "EQ|NEQ|LT|LTE|GT|GTE",
                      "value": "<valor no tipo do fato>", "quote": "<trecho literal da cláusula>"}],
      "exceptions": [{"ref": "3.1.1/e", "conditions": ["..."], "quote": "..."}],
      "notes": "<por que, em uma frase>"}
     ```
   - O prompt (em português) leva o catálogo (chave, tipo, valores), a seção e as cláusulas. A instrução é copiar o trecho literalmente e responder "nao_sei" quando a cláusula não couber no catálogo.
   - Peça a posição pelo trecho, nunca por números. As posições são calculadas pelo código.
   - **Duas passadas independentes:** um segundo provedor, ou o mesmo com outro prompt e ordem das cláusulas embaralhada. Mesmos fatos, comparação e valor nas duas: vale. Diferente: vai para revisão.
   - **Junção por seção:** "ressalvado o disposto no item X" e "conforme o item X" ligam a regra ao item X. A exceção vira ANY ou UNLESS, como em `FAP-EXEC-MG`.
6. **Conferência pelo código** (`src/tender_intel/compile/verify.py`). Uma regra só entra no solver se:
   - cada `quote` existe na cláusula (`check_span`);
   - números e datas aparecem no trecho (`values_missing_from_evidence`);
   - o fato existe no catálogo e o valor tem o tipo certo;
   - a comparação faz sentido para o tipo (por exemplo, não pode haver LT em bool).

   O que falhar vai para a Revisão com o motivo.
7. **Medição:**
   - eval no dev: regra a regra, perfis e falso elegível igual a zero;
   - depois, uma única rodada no conjunto de prova, com os números registrados como saírem;
   - tudo vai para `docs/GOLD_SET.md`.

**Pronto quando:** o extrator está ligado ao app, os números de dev e de prova estão registrados, o falso elegível é 0 e o custo por edital está medido.

**Armadilhas:**
- Não mande o edital inteiro ao Jev.
- Não confie em posição numérica devolvida pelo modelo.
- Não ajuste o prompt olhando os editais de prova.
- Não deixe a regra "não verificada" entrar no solver.

### Fase 6 — Verificação formal com Z3

**Por quê:** os trabalhos de 2026 que juntam LLM e solver formal mostram três ganhos que nosso solver Kleene sozinho não dá:

1. achar regras que se contradizem ou que ninguém cumpre, o que costuma ser leitura errada;
2. gerar perfis de teste automaticamente;
3. calcular o mínimo que falta mudar ou responder para ficar elegível (o trabalho de Taiwan calcula "a menor modificação dos fatos").

O solver Kleene continua decidindo. O Z3 confere.

**Onde achar:** `z3-solver` (PyPI, licença MIT). Tutorial: https://microsoft.github.io/z3guide/ (conferir o endereço). Use a classe `Optimize` para restrições suaves.

**Como fazer** (`src/tender_intel/verify/smt.py`):

1. **Tradução da expressão para Z3:**
   - fato bool vira `z3.Bool`;
   - número vira `z3.Real`;
   - enum vira `z3.Int` com um código por valor do catálogo, mais uma restrição de domínio;
   - data vira `z3.Int` em minutos desde 1970, já no fuso do texto (−03:00);
   - All vira `And`, AnyOf vira `Or` e Not vira `Not`;
   - Unless(corpo, exceção) vira `Or(corpo, exceção)`; confira a semântica em `solver.py`.
2. `check_consistency(rules)`: junte todas as regras de um edital. Se não houver solução (`unsat`), pegue o núcleo de conflito (`unsat_core`) e marque essas regras para revisão como "regras incompatíveis".
3. `vacuity(rule)`: regra impossível sozinha, ou que vale sempre (a negação é `unsat`), também vai para revisão.
4. `counterfactuals(rules)`: para cada regra, ache um perfil em que todas as outras valem e ela não. Converta em fatos e passe no solver Kleene: tem de dar "Não pode concorrer". Se der outra coisa, há bug no solver ou na tradução. É um teste cruzado.
5. `minimal_change(rules, facts)`:
   - com `Optimize`, mantenha os fatos atuais como restrições suaves de peso 1 e exija todas as regras;
   - a solução mostra quais fatos mudar ou responder;
   - fatos desconhecidos ficam livres e contam como "falta informar".
   - Isso alimenta a próxima pergunta (Fase 7).

**Testes:**
- os três editais do gabarito são consistentes;
- os perfis contrafactuais dão "Não pode concorrer";
- no perfil incompleto, `minimal_change` aponta só os fatos que faltam.

**Pronto quando:** a conferência Z3 roda depois da extração, e o que ela marcar vai para a Revisão.

**Armadilhas:**
- Datas como texto não funcionam no Z3: converta.
- Não use o Z3 para decidir a elegibilidade. Quem decide é o solver Kleene, que trata o "não sei" do jeito certo.

### Fase 7 — "Posso concorrer?"

**Por quê:** é a pergunta que o usuário final faz. Tem de responder com prova e dizer o que falta.

**Onde achar:** o catálogo (Fase 2), `solver.py`, `smt.py:minimal_change` e as tabelas `profiles`, `facts` e `results`.

**Como fazer:**

1. **Perfis:** organização, coordenador e projeto, cada um com fatos. Cada resposta grava um fato novo com `source = "declarado"`, `as_of` e, quando fizer sentido, `valid_until`. Exemplos:
   - "Lattes atualizado" vale até a data limite do edital;
   - uma certidão vale até a validade escrita nela.

   Fato vencido conta como desconhecido.
2. **Perguntas:** só as dos fatos que as regras daquele edital usam e que o perfil ainda não tem.
   - Ordem: primeiro o fato que resolve mais regras, pelo `minimal_change` ou, mais simples, pela contagem de regras em que o fato aparece.
   - Uma pergunta por tela, com a ajuda do catálogo e o documento que prova.
3. **Resultado:**
   - "Pode concorrer";
   - "Não pode concorrer", com a lista do que elimina, cada item com a frase e o trecho;
   - "Falta informar", com as perguntas pendentes.

   Sempre com a trava: se o edital tem cláusulas de elegibilidade não verificadas, o "Pode concorrer" vira "Pode concorrer nos itens verificados; faltam N cláusulas".
4. **Matriz:** um perfil contra todos os editais, ordenada por "pode", "falta informar" e "não pode".

**Testes:**
- de ponta a ponta com os três perfis de cada edital real, dando o resultado do gabarito pela tela;
- a trava aparece num edital com cláusula não verificada.

**Pronto quando:** isso passa e o dono testou com um perfil dele.

### Fase 8 — Retificações **[DONO: edital com retificação]**

**Por quê:** a retificação muda prazos e exigências, e quem não vê perde a chamada. A MASTER_SPEC define a ordem de autoridade (lei → corpo do edital → anexo → manual incorporado → FAQ → comunicado) e os eventos (`PUBLICACAO`, `RETIFICACAO`, `ERRATA` e outros).

**Onde achar:**
- `src/tender_intel/domain/types.py` (EventType e AuthorityTier);
- `discover.py` (prazo vigente e "Permanecem inalteradas");
- nas páginas de chamada do CNPq, a lista de documentos costuma incluir as retificações.

**Como fazer:**

1. A retificação entra como documento do pacote, com evento `RETIFICACAO` e data.
2. Detecte as alterações com regex: "Onde se lê … Leia-se …", "Fica alterado o item X", "Fica incluído", "Fica excluído", "passa a vigorar com a seguinte redação" e "Permanecem inalteradas as demais disposições".
3. Ligue cada alteração à cláusula do item X. A regra vigente é a mais nova, respeitando a autoridade. Guarde as duas versões.
4. Na tela, o item mostra "alterado pela retificação de dd/mm", com o trecho antigo riscado e o novo marcado. Na lista de editais, aparece o aviso "Saiu retificação".
5. Monte o gabarito do caso real e escreva os testes, incluindo o prazo vigente.

**Pronto quando:** o caso real passa no eval e o prazo vigente aparece certo na tela.

### Fase 9 — Monitoramento das fontes

**Por quê:** saber primeiro que saiu um edital novo ou uma retificação é o que mais vale para quem capta recursos. Numa busca de 16/10/2026 não apareceu ninguém fazendo análise de elegibilidade de fomento no Brasil; o mais próximo é um protótipo acadêmico que coleta editais de agências.

**Onde achar:**
- **CNPq:** chamadas abertas em https://www.gov.br/cnpq/pt-br/chamadas/abertas-para-submissao. Cada chamada tem página própria em `.../chamadas/todas-as-chamadas/chamadas-<ano>/...`.
- **FAPEMIG:** site https://fapemig.br. Os PDFs ficam em `api.site.fapemig.br/wp-content/uploads/...`.
- **FINEP:** seção de chamadas públicas em finep.gov.br. O endereço exato não foi conferido.
- **Diário Oficial da União:** edições completas em XML e PDF, grátis desde 2020, pelo INLABS da Imprensa Nacional (repositório `inlabs` em https://github.com/Imprensa-Nacional; acesso com cadastro, conferir no README). Avisos de chamada e retificações saem na Seção 3.

**Como fazer** (`src/tender_intel/sources/`):

1. Um coletor por fonte, com `fetch()` que devolve a lista de chamadas com título, número, link e documentos. Use `httpx` com identificação do app no User-Agent, uma requisição a cada 3 segundos, respeito ao `robots.txt` e cache por `ETag` e `Last-Modified`.
2. Faça o parser do HTML com `selectolax` ou `beautifulsoup4`. Escreva os testes com páginas salvas em `tests/fixtures/sources/*.html`.
3. Novidade é chamada nova ou documento novo (sha256 novo) numa chamada conhecida. O documento entra com o tipo provável (`retificacao` se o nome ou a primeira página disser) e vai para a fila de leitura.
4. Avisos: lista "Novidades" no app e, se o dono quiser, e-mail por um serviço de envio.
5. Agendamento: uma tarefa periódica na hospedagem, a cada 6 horas (Cron Job no Render).

**Armadilhas:**
- A rede da sessão bloqueia os sites do governo. Desenvolva com páginas salvas pelo dono, ou peça que ele libere `gov.br`, `fapemig.br`, `finep.gov.br` e `in.gov.br` nas configurações.
- Em produção a rede é livre.

### Fase 10 — Publicar na internet

**Por quê:** o dono escolheu "na internet", para só ele e a equipe.

**Onde achar:**
- **Render (recomendado):** worker como recurso de primeira classe, Postgres gerenciado com recuperação no tempo, disco persistente e Cron Job.
- **Railway (alternativa):** costuma ser mais barato quando o app fica parado, mas o worker é menos direto. Confira se o Postgres é gerenciado.
- Os preços mudam. Uma comparação de 2026 cita US$ 7 por mês por serviço no Render e disco por GB. Confira nas páginas de preço.

**Como fazer:**

1. **[DONO]** Criar a conta, ligar ao GitHub e criar os serviços pelo `render.yaml`.
2. Do seu lado:
   - `Dockerfile` (Python 3.11 slim, `pip install .`, usuário sem root);
   - `render.yaml` com o serviço web (`uvicorn`), o worker (`python -m tender_intel.web.worker`), o Postgres, o disco em `STORAGE_PATH` e o Cron Job da Fase 9;
   - rota `/saude`;
   - migrações na subida (`alembic upgrade head`).
3. Variáveis: `DATABASE_URL`, `SECRET_KEY`, `STORAGE_PATH`, `JEV_API_KEY`, `EXTRACTOR_PROVIDER` e a chave do provedor. Ficam cadastradas no painel da hospedagem, nunca no repositório.
4. Crie o primeiro admin com `tender-intel create-admin` e ajude o dono a convidar a equipe.
5. Rode `e2e/fluxo.mjs` contra o endereço publicado.
6. Backup: confira a recuperação do Postgres e faça cópia periódica do disco.

**Pronto quando:** o dono e a equipe entram pelo endereço publicado, enviam um edital e veem o Resumo.

### Fase 11 — Operação contínua

**Por quê:** modelos mudam (o artigo da Aethis viu resultado mudar sem troca de versão), editais mudam e o gabarito cresce.

**Como fazer:**

1. **CI no GitHub** (`.github/workflows/ci.yml`): Python 3.11, `pip install -e ".[dev]"`, `pytest` e o eval do dev. Reprova com qualquer falso elegível. O Playwright no CI precisa de `npx playwright install --with-deps chromium`, porque lá não há o Chromium da sessão.
2. **Troca de modelo** (novo Jev ou novo modelo forte):
   - rode o eval com o modelo novo ao lado do atual e compare os registros em `gold/runs/`;
   - troque só se melhorar e o falso elegível continuar zero;
   - recalibre os limites do Jev.
3. **Correções viram gabarito:** cada correção na Revisão vira candidata a item de gabarito. Com o aceite do dono, entra no dev, e o gabarito cresce sozinho.
4. **Custo:** mostre no admin o custo de IA por edital e por mês, a partir dos registros de chamadas.

---

## Parte D — Regras para todas as fases

1. **Constituição (A3):**
   - a IA não decide;
   - toda regra tem trecho conferido;
   - "não sei" com prova é melhor que resposta bonita;
   - nada some sem aviso;
   - a pessoa prevalece;
   - falso "pode concorrer" é zero.
2. **Nada fingido:** sem resultado inventado na tela ou nos relatórios. Dublês só dentro dos testes.
3. **Chaves:** só por variável de ambiente. Nunca no código, no chat ou nos logs. A chave antiga do Jev foi exposta no chat em 15/10: lembre o dono uma vez de trocar.
4. **Medição:** meça antes de afirmar e diga a fonte de cada número. Nunca ajuste nada olhando o conjunto de prova.
5. **Modelos com versão fixa:** grave a versão em cada chamada e meça de novo a cada troca.
6. **Licenças.** O app é fechado, então evite AGPL e GPL:
   - nada de PyMuPDF (AGPL) nem Marker (GPL);
   - confira a licença dos pesos de modelo (o Chandra restringe uso comercial).
   - Prefira MIT, BSD e Apache: Docling, pdfplumber, pdf.js, z3, LangExtract.
7. **Dados pessoais (LGPD):** guarde só o necessário do proponente. Acesso só com login. Apague quando o dono pedir.
8. **Código:**
   - identificadores em inglês; comentários, documentação e textos da tela em português;
   - siga o estilo do repositório: dataclasses, funções curtas, poucas dependências;
   - dependência pesada (Docling) vai como extra opcional.
9. **Commits e push:**
   - commits pequenos, mensagens em português como as que já existem;
   - `pytest` antes de cada push;
   - push no branch da sessão;
   - PR só se o dono pedir.
10. **Com o dono:**
    - português simples e curto;
    - decisões com 2 a 4 opções e uma recomendação;
    - mostre telas com dados reais;
    - nunca peça chave no chat;
    - a rede da sessão bloqueia os sites do governo, então peça os editais a ele ou peça que libere os domínios.
11. **Ao fim de cada fase:** atualize a Parte F e o `docs/GOLD_SET.md`.

---

## Parte E — Onde achar

### Fontes de editais (para o dono baixar, ou para a Fase 9)

| Fonte | Onde | Observação |
| --- | --- | --- |
| CNPq | https://www.gov.br/cnpq/pt-br/chamadas/abertas-para-submissao | Página oficial das chamadas abertas; cada chamada tem página com os documentos e as retificações |
| FAPEMIG | https://fapemig.br | PDFs em `api.site.fapemig.br/wp-content/uploads/...`; submissão pelo EVEREST |
| FINEP | finep.gov.br, seção de chamadas públicas | Endereço exato não conferido |
| Diário Oficial | https://github.com/Imprensa-Nacional (repositório `inlabs`) | XML e PDF grátis desde 2020; cadastro no INLABS |

### Bibliotecas

| Biblioteca | Para quê | Licença |
| --- | --- | --- |
| pypdf (já usada) | Texto do PDF | BSD |
| pdfplumber | Posição das palavras | MIT (conferir) |
| Docling | Tabelas e páginas escaneadas | MIT no código; modelos com licença própria |
| pdf.js (`pdfjs-dist`) | Ver o PDF com o trecho marcado | Apache-2.0 |
| z3-solver | Verificação formal | MIT |
| LangExtract | Referência de extração com posição exata | Apache-2.0 |
| FastAPI, Jinja2, HTMX, SQLAlchemy, Alembic, argon2-cffi, httpx | App web | Permissivas (conferir) |
| Evitar | PyMuPDF (AGPL), Marker (GPL); pesos do Chandra só com licença | — |

### Pesquisa que embasa as decisões

- **Harvey, revisão de contratos como multiagente:**
  - resumo da ZenML: https://www.zenml.io/llmops-database/multi-agent-contract-playbook-review
  - post da Harvey: https://www.harvey.ai/blog/rebuilding-playbook-review-as-a-multi-agent-system
- **Harvey, orquestração do trabalho jurídico:** https://www.harvey.ai/blog/legal-work-orchestration
- **"Confidently Wrong"** (Aethis, 2026), exceções encadeadas e motor determinístico: https://arxiv.org/pdf/2607.23386
- **LLM e SMT em compliance financeiro** (Taiwan): https://arxiv.org/abs/2601.06181v1
- **Direito penal coreano com SMT:** https://huggingface.co/papers/2607.19740
- **PolicyLLM** (ICML 2026): https://icml.cc/virtual/2026/78632
- **Ask HN, processamento de documentos com LLM em produção:** https://hn.nuxt.dev/item/46319267
- **Testes de leitura de PDF:**
  - ParseBench: https://www.codesota.com/benchmark/parsebench
  - olmOCR-Bench: https://www.codesota.com/browse/computer-vision/document-parsing/olmocr-bench
  - PDF Parse Bench: https://huggingface.co/datasets/piushorn/pdf-parse-bench
- **Docling:** relatório técnico https://arxiv.org/html/2408.09869v5
- **Chandra** (licença dos pesos): https://github.com/datalab-to/chandra
- **Jev 1.14:**
  - https://www.marktechpost.com/2026/10/14/typesafe-ai-jev-1-14-images-box-long-context/
  - https://docs.litellm.ai/blog/typesafe_jev_images
- **Render e Railway em 2026:** https://selfhost.dev/railway-vs-render-pricing-2026-verdict/
- **Enter:** `deep-research-report.md`, seção "Enter mostra como transformar leitura massiva em infraestrutura operacional".

---

## Parte F — Pendências do dono e Estado

### Pendências do dono

- [ ] Conferir as 8 regras corrigidas na página de conferência.
- [ ] Trocar a chave do Jev, cadastrar como `JEV_API_KEY` e liberar `api.typesafe.ai` nas configurações do ambiente.
- [ ] Escolher o modelo forte (Claude, Gemini ou Grok) e cadastrar a chave. O Grok precisa liberar `api.x.ai`.
- [ ] Mandar 2 ou 3 editais de prova, um com retificação publicada, e o PDF original do FAPEMIG 018/2026.
- [ ] Para a Fase 9: liberar `gov.br`, `fapemig.br`, `finep.gov.br` e `in.gov.br`, ou mandar as páginas salvas.
- [ ] Escolher a hospedagem e criar a conta (Fase 10).

### Estado

| Fase | Situação | Notas |
| --- | --- | --- |
| 0. Começo da sessão | a fazer | |
| 1. Gabarito e medição | em andamento | 38 regras conferidas pelo dono em 16/10: 31 certas, 8 corrigidas, que esperam nova conferência |
| 2. Catálogo | a fazer | o vocabulário está em `explain.py` |
| 3A. Posição na página | a fazer | |
| 3B. Tabelas e escaneados | a fazer | |
| 4. App web | a fazer | a página de conferência já define o visual |
| 5. Extrator | a fazer | depende da chave do Jev e da escolha do modelo forte |
| 6. Z3 | a fazer | |
| 7. Posso concorrer? | a fazer | |
| 8. Retificações | a fazer | depende de edital com retificação |
| 9. Monitoramento | a fazer | depende de liberar os domínios ou de páginas salvas |
| 10. Publicar | a fazer | depende da hospedagem |
| 11. Operação | a fazer | |
