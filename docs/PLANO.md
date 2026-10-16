# PLANO — do gabarito ao app no ar

Plano de execução para um agente do Claude Code numa sessão nova, com esforço alto. Escrito em 16/10/2026 a partir da conversa com o dono do projeto. Junta o que já foi decidido, o estado do código e o que falta, fase por fase.

Para começar a sessão, o dono cola:

> Leia docs/PLANO.md inteiro e execute a partir da Fase 0. Parta de origin/claude/busy-einstein-87aa7b e trabalhe no branch indicado pela sessão.

## Como usar este plano

- Leia este arquivo inteiro, depois `docs/MASTER_SPEC.md`, `docs/JEV_POLICY.md`, `docs/GOLD_SET.md` e `README.md`. O `deep-research-report.md` é a visão longa; a MASTER_SPEC é o recorte que vale.
- Siga a ordem da seção "Ordem das fases". Uma fase só termina quando todos os itens de "Pronto quando" passam.
- No fim de cada fase, atualize a tabela "Estado" no fim deste arquivo (o que foi feito, números medidos, o que ficou pendente) e commite junto.
- Itens marcados **[DONO]** dependem do dono. Nunca simule nem invente o resultado deles: peça, e siga com o que não depende.

## O dono e como falar com ele

- Escreve em português informal, rápido, com erros de digitação. Não é programador. Quer ver as coisas funcionando.
- Responda curto, em português simples, sem jargão. Para decidir, dê de 2 a 4 opções e diga qual recomenda.
- Mostre telas: publique prévias como página do Claude (Artifact) ou mande imagens do app rodando, sempre com os dados reais dos editais.
- Ele pediu "sem mock": nenhum resultado fingido. Dublês de teste só dentro dos testes.
- Nunca peça chave no chat. A chave antiga do Jev foi colada no chat em 15/10 e precisa ser trocada; lembre isso uma vez.

## Produto: o que já foi decidido

- **O que é:** um app web que lê editais de fomento (FAPEMIG, CNPq e outros), lista as exigências em português simples com o trecho do edital e diz se um proponente pode concorrer.
- **Quem usa:** só o dono e a equipe dele. Acesso com senha; contas criadas por um admin; sem cadastro aberto.
- **Onde roda:** na internet, num serviço de hospedagem de custo baixo. O serviço ainda não foi escolhido (Fase 8).
- **Uso:** vários editais de uma vez; tem que ser fácil para qualquer pessoa entender; tem que funcionar no celular.
- **Telas:** Editais, Resumo do edital, Revisão e "Posso concorrer?" (detalhes na Fase 3 e na Fase 5).
- **IA:**
  - O Jev (TypeSafe) faz a triagem das cláusulas: perguntas curtas, com probabilidade.
  - Um modelo mais forte lê as cláusulas complicadas. O provedor ainda não foi escolhido: o dono disse "decido depois". Claude e Gemini passam na rede das sessões; o Grok (`api.x.ai`) precisa ter o domínio liberado.
  - O código confere tudo o que a IA disser, e quem decide a elegibilidade é o solver. A IA nunca decide.
- **Trava inegociável:** nunca dizer "pode concorrer" para quem não pode. Se sobrou cláusula de elegibilidade sem verificar, a resposta é "pode concorrer nos itens verificados; faltam N cláusulas", nunca um "pode" seco.

## Estado atual (16/10/2026)

- **Repositório:** `ccj33/Analisador`, branch `claude/busy-einstein-87aa7b` (último commit `976f62e`). O PR #1 (rascunho) vem do branch `claude/analisador-sem-mock-ojc8f8` e não tem os dois últimos commits.
- **Código:** Python ≥ 3.11, pacote `tender_intel` em `src/`, depende só de `pypdf`. `python -m pip install -e ".[dev]"` e `python -m pytest`: 46 testes passam.
- **O que já funciona:**
  - ingestão de PDF com texto, DOCX e Markdown, com cláusula, seção e página;
  - parsers de data, hora, R$ e CNPJ;
  - solver Kleene;
  - cobertura por cláusula (nada lido some sem aviso);
  - eval regra a regra e por perfil;
  - `src/tender_intel/explain.py`: frase em português simples gerada da própria expressão da regra;
  - `gold/export_review.py` e `gold/review_page.html`: a página de conferência do gabarito.
- **Gabarito:** três editais reais (FAPEMIG 018/2026 com 15 regras, CNPq 34/2026 com 13 e CNPq 32/2026 com 10) e um sintético. Em 16/10 uma pessoa conferiu as 38 regras: 31 estavam certas e 8 foram corrigidas (`docs/GOLD_SET.md`, seção "Conferência humana"). As 8 corrigidas esperam nova conferência do dono na página https://claude.ai/artifact/AuxmKTXqc81vm87ztECEke (coleção `reviews` do banco da página; marcação com `rev` diferente da versão atual da regra conta como pendente). A página está aberta para quem tiver o link.
- **Compilador atual:** são as regex do edital sintético; acha 0 das 38 regras nos editais reais. Bug conhecido: `src/tender_intel/compile/extract.py:118` só cria a regra de prazo se "Brasília" e a hora estiverem na mesma cláusula da data, e nos editais reais nunca estão.
- **Jev:** o `JevProvider` (`src/tender_intel/ai/provider.py`) ainda não faz chamada HTTP (levanta `NotImplementedError`); o padrão é o `AbstainProvider`. O Jev 1.14 saiu em 14/10 como prévia e trouxe ganho em outros idiomas além do inglês; imagens, caixas de posição e contexto longo são experimentais.
- **Ambiente das sessões:** a rede bloqueia `gov.br`, `cnpq.br`, `fapemig.br`, `api.typesafe.ai`, `api.x.ai` e `api.openai.com`, e libera pypi, npm, `api.anthropic.com` e `generativelanguage.googleapis.com`. As chaves entram por Network secrets: `JEV_API_KEY`, `XAI_API_KEY` (se usar o Grok) e a do modelo forte.

## Ordem das fases

0 → 1 → 3 (a base do app usa o motor atual e não depende de chave) → 2 → 4 (quando a chave do Jev existir) → 5 → 6 (quando chegar um edital com retificação) → 7 → 8.

A Fase 2 pode ir junto da 3. Se faltar algo do dono numa fase, avance na seguinte e volte quando chegar.

## Fase 0 — Começo da sessão

1. `git fetch origin claude/busy-einstein-87aa7b` e crie o branch da sessão a partir dele (`git checkout -B <branch-da-sessão> origin/claude/busy-einstein-87aa7b`).
2. `python -m pip install -e ".[dev]"` e `python -m pytest`: 46 testes têm de passar.
3. Rode `python -m tender_intel.cli eval --case gold/cases/<caso>.json` nos quatro casos e anote a linha de base.
4. Leia as marcações da página de conferência com a ferramenta `ArtifactData`: `list` na coleção `reviews`. Gere as versões atuais com `python gold/export_review.py /tmp/atual.json` e compare os campos `rev`. Diga ao dono quantas das 8 regras corrigidas ele já conferiu.
5. Confira se a chave do Jev existe sem imprimir o valor: `test -n "$JEV_API_KEY" && echo ok`. Confira se o domínio abre com `curl -sS -o /dev/null -w '%{http_code}' -X POST https://api.typesafe.ai/v1/systemone`: 401 quer dizer liberado; falha de túnel 403 quer dizer bloqueado.

**Pronto quando:** testes passando, linha de base anotada no "Estado" e o dono sabe o que falta da parte dele.

## Fase 1 — Fechar o gabarito e endurecer o eval

1. **Conferência das 8 regras.** Para cada regra que o dono marcar "Tem erro" ou "Não tenho certeza":
   - confira no texto do edital;
   - corrija em `gold/build.py` e rode `python gold/build.py`;
   - ajuste os perfis `fixtures/*/facts-*.json`, para os três perfis de cada edital continuarem com o resultado esperado;
   - acrescente o caso em `tests/test_gold_review.py`;
   - republique a página no mesmo link: `python gold/export_review.py <scratchpad>/conferencia-gabarito.html` e depois Artifact publish com `url` do link acima.
2. **Travas no eval** (`src/tender_intel/eval/harness.py`, `cli.py`):
   - Conte o falso elegível: perfil com resultado esperado diferente de SATISFIED que saiu SATISFIED. Qualquer falso elegível reprova o eval, tanto no caminho anotado quanto no compilado.
   - Separe três números por caso: decidiu certo (saiu igual ao esperado e não é UNKNOWN), não soube (saiu UNKNOWN quando se esperava outra coisa) e errou. Hoje o compilado "acerta" 3 de 9 perfis só porque responde "não sei" para todos.
   - A CLI imprime um resumo curto. Escreva os testes.
3. **Rótulos de cláusula para calibrar o Jev** (`gold/labels/<caso>.json`):
   - Seções que entram: FAPEMIG, itens 3, 5 e 13; CNPq, itens 1.3, 2, 3, 4 e 6.
   - Para cada cláusula dessas seções, anote: é exigência (sim/não), elimina a proposta (sim/não/o edital não diz), a quem se aplica e qual item do catálogo da Fase 2 ela usa (ou "nenhum").
   - Você faz a primeira marcação; o dono confere uma amostra. Para isso, estenda a página de conferência para mostrar cláusulas, com o mesmo mecanismo de `rev`.
4. **[DONO] Editais de prova.** Peça 2 ou 3 editais novos, de preferência de órgãos diferentes e um com retificação publicada. A rede bloqueia os sites do governo, então eles vêm como anexo do dono.
   - Ao chegar, monte a fixture e o gabarito como nos outros e marque `"split": "test"` em `gold/cases/*.json`. Os três atuais e o sintético ficam `"split": "dev"`.
   - O eval imprime os números de dev e de prova separados.
   - Regra: nada do extrator é ajustado olhando os editais de prova.

**Pronto quando:**
- as 8 regras estão resolvidas, ou o dono adiou explicitamente;
- o eval tem a trava de falso elegível e os três números separados;
- os rótulos de cláusula dos três editais estão feitos, com amostra conferida pelo dono;
- os editais de prova foram pedidos.

## Fase 2 — Catálogo de requisitos

O catálogo é a lista de fatos que o proponente pode responder. É a base de três coisas: as opções da pergunta de escolha do Jev, o formato da saída do modelo forte e as perguntas da tela "Posso concorrer?".

1. Crie `src/tender_intel/catalog.py`, com uma entrada por chave de fato. Mantenha as chaves atuais, porque o eval pareia por elas. Cada entrada tem:
   - a entidade (`organization`, `coordinator`, `subcoordinator`, `institution`, `project`, `event`, `proposal`, `submission`);
   - o tipo (`bool`, `enum`, `number`, `date`), os valores com rótulo e a unidade;
   - as frases de sim e não que hoje estão em `explain.py`;
   - a pergunta ao proponente em português simples ("Você tem doutorado?", "Qual é o seu vínculo com a instituição?") e um texto de ajuda;
   - o documento que costuma provar o fato (Lattes, CNPJ, declaração).
2. `explain.py` passa a ler os rótulos do catálogo, sem copiar.
3. Testes:
   - todo fato usado nos gabaritos está no catálogo;
   - toda entrada tem pergunta;
   - os rótulos de enum cobrem todos os valores do gabarito.

**Pronto quando:** os testes passam e as frases da página de conferência saem iguais às de antes.

## Fase 3 — App web: base, login, envio, Resumo e Revisão

Use a pilha abaixo, que é a recomendada. Só troque com motivo escrito no "Estado".

### Pilha

| Parte | Escolha |
| --- | --- |
| Servidor e telas | FastAPI e Uvicorn; páginas renderizadas no servidor com Jinja2 e HTMX. Um serviço só, mais simples de hospedar. O HTMX vai como arquivo em `static/`, numa versão fixa. |
| Visual | Sistema próprio, com os tokens de `gold/review_page.html`: Schibsted Grotesk, Source Serif 4 e IBM Plex Mono, carimbos, trecho com marca-texto, tema claro e escuro. |
| Banco | SQLAlchemy 2 e Alembic; Postgres em produção, SQLite local e nos testes. |
| Arquivos | Originais num diretório do disco configurado por variável de ambiente, guardados pelo sha256. |
| Fila | Tabela `jobs` e um processo `worker` (`python -m tender_intel.web.worker`): pega o job pendente com trava (`FOR UPDATE SKIP LOCKED` no Postgres), tenta de novo com espera crescente e mostra o status na tela. |
| Login | E-mail e senha (hash argon2); cookie de sessão `HttpOnly`, `Secure` e `SameSite=Lax`; token CSRF nos formulários; limite de tentativas. Admin cria contas e troca senhas. O primeiro admin sai de `tender-intel create-admin`. |

### Pastas

- `src/tender_intel/web/`, com `app.py`, `db.py`, `models.py`, `auth.py`, `jobs.py`, `worker.py`, `routes/`, `templates/` e `static/`.

### Dados mínimos

- `users`
- `calls` (chamada: título, órgão, número, status)
- `documents` (arquivo, sha256, tipo: edital, anexo, retificação ou FAQ; data de envio)
- `processing_runs`
- `clauses` (cláusula, seção, página, classe de cobertura)
- `rules`: a regra em JSON e a origem (gabarito, compilador ou extrator). O status de conferência fica separado: conferido, precisa conferir ou não verificado. Tem também o `rev`.
- `reviews` (veredito, comentário, pessoa, `rev`)
- `profiles` e `facts` (perfil e fatos com `as_of` e fonte)
- `results`

### Telas

- **Editais**
  - Arrastar vários arquivos de uma vez.
  - O app sugere o agrupamento por chamada, pelo número no nome do arquivo ou na primeira página ("Chamada CNPq Nº 34/2026"). O usuário confirma os grupos e marca o que é retificação.
  - O processamento entra na fila e o status atualiza sozinho: lendo, pronto, com dúvidas para revisar ou erro.
- **Resumo do edital**
  - Topo com título, órgão, prazo de início e de envio e valor máximo.
  - As exigências agrupadas por quem precisa cumprir (proponente, coordenador, instituição, projeto), cada uma com a frase de `explain` e o trecho do edital que abre com marca-texto, item e página.
  - Selo em cada exigência: conferida, precisa conferir ou não verificada.
  - Aviso de cobertura: "N cláusulas da parte de elegibilidade ainda não foram lidas", com link para a Revisão.
- **Revisão**
  - Uma ficha por vez, no mesmo formato da página de conferência; atalhos C, E e D no teclado; funciona no celular.
  - A fila tem as regras a conferir e as cláusulas de elegibilidade ainda não classificadas.
  - Editar uma regra é escolher o fato do catálogo, a comparação e o valor. A edição humana prevalece sobre a IA.
- **Palavras na tela:** SATISFIED vira "Pode concorrer", UNSATISFIED vira "Não pode concorrer", UNKNOWN vira "Falta informar", CONFLICT vira "Informações em conflito" e NOT_APPLICABLE vira "Não se aplica". A camada MERIT aparece como "Critério de avaliação (não elimina)".

### Honestidade até a Fase 4

- Nos três editais reais, o Resumo mostra o gabarito conferido, com esse nome.
- Num edital novo, mostra só o que o compilador atual achou e marca o resto como "não verificado". Nenhuma exigência inventada.

### Testes

- pytest para serviços, login, envio e fila.
- Playwright de ponta a ponta, com o Chromium em `/opt/pw-browsers`, no computador e em 400 px de largura: entrar, enviar os três editais, ver o Resumo e marcar uma revisão.
- Acessibilidade básica: rótulos, foco visível e contraste.

**Pronto quando:**
- o app roda localmente com login, envio de vários arquivos, fila, Resumo e Revisão dos três editais reais;
- os testes e o Playwright passam;
- o dono viu a prévia.

## Fase 4 — Extrator: Jev, modelo forte e conferência

1. **Bug do prazo.** Em `extract.py:112–118`:
   - aceite a hora e o "horário de Brasília" numa cláusula vizinha ou da mesma seção. No CNPq, a data está no cronograma e a hora no item 6.2 ou 6.5.
   - crie também a regra de início, como no item 13.1 da FAPEMIG.
   - Meça antes e depois.
2. **Candidatos.** Busque por recall, e o Jev filtra depois:
   - as seções de elegibilidade e afins, pelo título ("Critérios de elegibilidade", "Quanto ao Proponente", "Da contrapartida", "Cronograma", "Da submissão");
   - toda cláusula com linguagem de obrigação ("deverá", "deve", "é vedado", "não poderá", "obrigatoriamente", "somente", "exclusivamente", "sob pena de", "implicará", "não serão elegíveis").
3. **Adaptador do Jev** (`src/tender_intel/ai/jev.py`), com chamada HTTP de verdade:
   - **Endpoint, a confirmar na documentação oficial antes de codar** (estes dados vêm de tutoriais de terceiros): `POST https://api.typesafe.ai/v1/systemone`, cabeçalho `Authorization: Bearer $JEV_API_KEY`, corpo `{model, state, questions}`. Os tipos de pergunta são:
     - Choice: até 255 opções; devolve a opção, a probabilidade de cada uma e a confiança;
     - Score: escala de 2 a 10 níveis;
     - Noul: probabilidade de "sim".
   - **Versão:** chame a 1.14 pelo nome exato (por exemplo `jev-1.14.0`), nunca `jev-latest`, porque esse nome muda de versão sozinho e invalida a calibração. Sem os cabeçalhos experimentais (imagens, Box, contexto longo).
   - **Estado enviado:** a cláusula, o título da seção e a cláusula anterior e a seguinte quando forem curtas; de 2 a 4 mil tokens. Nunca o edital inteiro.
   - **Perguntas** (`JEV_POLICY.md`): é exigência (Noul), elimina (Noul), a quem se aplica (Choice, com "outro" e "não sei"), qual item do catálogo (Choice, com o catálogo, "nenhum" e "não sei"), tem exceção (Noul) e cita outro item ou documento (Noul).
   - **Falhas:** tempo esgotado, erro 402 ou falta de chave fazem o adaptador se abster.
   - **Registro:** guarde cada chamada com tipo de tarefa, versão do modelo, hash da entrada, perguntas, saída, probabilidades, latência e custo estimado.
   - **Testes:** com respostas gravadas, sem rede.
4. **Calibração.**
   - Rode o Jev nos rótulos da Fase 1, só no dev, e meça acerto contra confiança em cada pergunta.
   - O limite de aceite automático é a menor confiança acima da qual não houve erro no dev, com um mínimo de exemplos. Sem isso, a pergunta vai sempre para revisão.
   - Grave em `gold/calibration/jev-1.14.0.json`, com a versão do conjunto de rótulos.
   - Mostre ao dono em linguagem simples ("o Jev acertou X de Y; acima de 95% de certeza, não errou nenhuma").
5. **Modelo forte [DONO escolhe: Claude, Gemini ou Grok].**
   - Interface `RuleExtractor` em `src/tender_intel/ai/extractor.py`, que não depende do provedor.
   - A saída segue um JSON Schema: lista de condições (fato do catálogo, comparação, valor e citação), a lógica (todas ou uma), as exceções e a opção "não sei".
   - O prompt leva o catálogo, a cláusula e o contexto.
   - Só é chamado para cláusula que o Jev marcou como exigência e cujo item do catálogo ou cuja lógica ficou incerta ou complexa (exceção, "ou", várias condições).
6. **Conferência pelo código** (princípio do projeto):
   - a citação existe na cláusula;
   - números e datas aparecem na citação (`values_missing_from_evidence`);
   - o fato existe no catálogo e o valor tem o tipo certo;
   - a comparação é válida.
   Se algo falhar, a regra vai para a Revisão e não entra no solver.
7. **Medição.**
   - Rode o eval no dev: regra a regra, perfis e falso elegível igual a 0.
   - Depois rode uma única vez nos editais de prova e reporte os números como saírem.
   - Registre tudo em `docs/GOLD_SET.md`.

**Pronto quando:** o extrator está ligado ao app, os números de dev e de prova estão registrados e o falso elegível é 0 em todos os perfis.

## Fase 5 — "Posso concorrer?"

1. Perfis de organização, coordenador e projeto, com fatos.
   - O app pergunta só o que as regras daquele edital precisam, com as perguntas do catálogo.
   - Cada resposta vira um fato que nunca é apagado (só substituído por um mais novo), com data e a fonte "declarado pelo usuário".
2. Resultado:
   - "Pode concorrer";
   - "Não pode concorrer", com os itens que eliminam e o trecho de cada um;
   - "Falta informar", com as perguntas pendentes.
   Sempre com a trava das cláusulas não verificadas.
3. Matriz de um perfil contra todos os editais: em quais a pessoa pode concorrer.
4. Teste de ponta a ponta.

**Pronto quando:** os três perfis de teste de cada edital real dão o resultado do gabarito pela tela, e o dono testou com um perfil dele.

## Fase 6 — Retificações [DONO: edital com retificação]

1. A retificação entra como documento do pacote (evento `RETIFICACAO`).
   - Detecte "Onde se lê… Leia-se…" e "Fica alterado o item X" e ligue ao item alterado.
   - A precedência segue a ordem de autoridade da MASTER_SPEC e a data. O prazo vigente sai daí.
2. Na tela, o item mostra "alterado pela retificação de dd/mm", com os dois trechos.
3. Monte o gabarito do caso real e os testes.

## Fase 7 — Fatos com data de validade e a próxima pergunta

1. Fatos com data de validade, como o Lattes atualizado até a data limite ou certidões. Fato vencido conta como desconhecido.
2. A próxima pergunta: entre os fatos que faltam, pergunte primeiro o que resolve mais regras.

## Fase 8 — Publicar na internet

1. **[DONO]** Escolher a hospedagem. A recomendação é um serviço com Postgres gerenciado e disco, como Render ou Railway; confira os preços no site na hora.
   - Criar a conta e ligar ao GitHub.
   - Cadastrar as variáveis: `DATABASE_URL`, `SECRET_KEY`, `STORAGE_PATH`, `JEV_API_KEY` e a chave do modelo forte.
2. Do seu lado:
   - `Dockerfile`, verificação de saúde, migrações na subida, o processo `worker`, logs e notas de backup;
   - criar o primeiro admin, ajudar o dono a convidar a equipe;
   - rodar o teste de ponta a ponta contra o endereço publicado.

## Regras para o agente

1. Respeite a constituição da MASTER_SPEC:
   - a IA não decide elegibilidade;
   - toda regra e toda ligação entre condições têm evidência no edital;
   - entre uma resposta bonita sem prova e "não sei" com prova do que falta, fique com o "não sei".
2. Nada de resultado fingido. Dublês só dentro dos testes.
3. Chaves só por variável de ambiente. Nunca no código, no chat ou nos logs.
4. Meça antes de afirmar e diga de onde vêm os números. Nunca ajuste nada olhando os editais de prova.
5. Falso "pode concorrer" é zero, sempre.
6. Commits pequenos, com mensagens em português como as que já existem. Rode o pytest antes de cada push. Faça push no branch da sessão. PR só se o dono pedir.
7. Identificadores de código em inglês; comentários, documentação e textos da tela em português, como hoje. Siga o estilo do repositório e não acrescente dependência sem necessidade.
8. A rede bloqueia os sites do governo, então peça os editais ao dono.
9. Quando faltar uma decisão do dono, siga com o que não depende dela e pergunte com opções.
10. Atualize o "Estado" e o `docs/GOLD_SET.md` a cada fase.

## Pendências do dono

- [ ] Conferir as 8 regras corrigidas na página de conferência.
- [ ] Trocar a chave do Jev, cadastrar como `JEV_API_KEY` e liberar o domínio `api.typesafe.ai`.
- [ ] Escolher o modelo forte (Claude, Gemini ou Grok) e cadastrar a chave.
- [ ] Mandar 2 ou 3 editais de prova, um deles com retificação publicada.
- [ ] Escolher a hospedagem e criar a conta (Fase 8).

## Estado

| Fase | Situação | Notas |
| --- | --- | --- |
| 0. Começo da sessão | a fazer | |
| 1. Gabarito e eval | em andamento | 38 regras conferidas pelo dono em 16/10: 31 certas, 8 corrigidas, que esperam nova conferência |
| 2. Catálogo | a fazer | o vocabulário está em `explain.py` |
| 3. App: base, envio, Resumo, Revisão | a fazer | a página de conferência já define o visual |
| 4. Extrator | a fazer | depende da chave do Jev; o modelo forte depende da escolha do dono |
| 5. Posso concorrer? | a fazer | |
| 6. Retificações | a fazer | depende de edital com retificação |
| 7. Validade e próxima pergunta | a fazer | |
| 8. Publicar | a fazer | depende da hospedagem |
