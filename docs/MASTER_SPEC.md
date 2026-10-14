# MASTER_SPEC — Analisador de editais

Sistema que **compila** o pacote de uma chamada de fomento num modelo normativo verificável e compara esse modelo com fatos datados de uma organização e de um projeto.

Não é ChatPDF, RAG jurídico, parecer de advogado, Harvey para contratos, Enter para contencioso, nem analisador de licitação 14.133.

**Recorte v1:** Chamada CNPq via PICC (pacote = chamada + retificações + FAQ + manual se estiver no pacote).

## Constituição

- LLM é trabalhador da pipeline. Nunca é a autoridade de elegibilidade.
- Todo elemento documental tem ID permanente.
- Quatro grafos: fonte, normativo, fatos, decisão. Requisito encontrado não é decisão.
- Solver devolve `SATISFIED`, `UNSATISFIED`, `UNKNOWN`, `CONFLICT`, `NOT_APPLICABLE`.
- Evidência em todo nó e em toda aresta lógica. Campo não encontrado ≠ campo vazio.
- Coverage operacional, nunca “100% do significado jurídico”.
- Fatos são assertions append-only, com `as_of` e `source_system`.
- Extrator trocável; a conferência determinística não muda.
- Célula editada pelo humano prevalece sobre a IA.
- Assistente de conformidade ≠ parecer jurídico.
- Entre resposta bonita sem prova e `UNKNOWN` auditável, escolher `UNKNOWN`.

## Famílias (só fomento na v1)

- Fomento — este produto.
- Licitação 14.133 / PNCP — outro produto.
- Convênio / Transferegov — outro produto.

## Eventos e autoridade

Eventos: `PUBLICACAO`, `RETIFICACAO`, `ERRATA`, `ESCLARECIMENTO`, `FAQ`, `RESPOSTA_IMPUGNACAO`, `RETIFICACAO_RESULTADO`.

Autoridade: `LEI` → `EDITAL_CORPO` → `ANEXO_EDITAL` → `MANUAL_INCORPORADO` → `FAQ_OPERACIONAL` → `COMUNICADO`.

Manual citado e ausente = `EXTERNAL_DEPENDENCY` / `UNRESOLVED`. Nunca inferir o conteúdo.

Camadas: `PRE_SUBMISSION` (solver v1) e `MERIT` (exibido, sem SAT).

## Arquitetura v1

1. Ingestão nativa (OCR só se não houver text layer).
2. Parsers determinísticos (datas, R$, CNPJ, itens).
3. `DecisionProvider` (Jev opcional) para triagem e escolha de evidência.
4. Grafo normativo com evidência verificada.
5. Review Table humana.
6. Solver Kleene sobre fatos resolvidos.

Três papéis no mesmo job: Structure, NormativeCandidate, Verification.

## Fora da v1

16 agentes, DSL LegalRuleML-completo, OPA/Rego canônico, PNCP, scoring de mérito, redline, planilha FINEP, Catala como runtime.
