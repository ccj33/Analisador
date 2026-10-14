# JEV_POLICY

Jev (TypeSafe, pin `jev-1.13.0`) é System-1 de volume. Não é o solver e não é dependência dura.

## Contrato

```text
DecisionProvider.decide(state, questions) → answers + usage
```

Implementações:

- `JevProvider` — só se houver credencial; senão abstain.
- `LlmSchemaProvider` — fallback (não implementado na Fase 1).
- `AbstainProvider` — padrão da v1: devolve `unclear` / `none` sem chamar rede.

Timeout, 402 ou ausência de chave → abstain. O produto funciona com Jev desligado.

## Regras de chamada

- Candidatos antes do modelo: regex/BM25 acha spans; `Choice` escolhe um ou `none`.
- Estado de 2–4k tokens. Nunca o edital inteiro.
- Uma hipótese por `Noul`.
- Todo `Choice` inclui `none` / `unclear`.
- `Score`: argmax das probabilities, não arredondar a média.
- Datas, prazos, percentuais, CNPJ, soma: código.
- Jev não gera o “por que”. Isso vem do grafo ou do frontier.
- Thresholds por `task_type` + `model_version` + `calibration_dataset_version`.

## Matriz v1

| detector | primitivo | fallback |
| --- | --- | --- |
| `rule_category` | Choice + unclear | abstain / LLM |
| `actor_role` | Choice + unclear | abstain / LLM |
| `contains_exception` | Noul | banda cinza → frontier |
| `contains_deadline` | Noul | parser de data manda |
| `is_eliminatory` | Noul | banda cinza → humano |
| `candidate_evidence_relevance` | Choice entre spans + none | se none, não inventar |
| `requires_frontier` | Score / Choice | só roteia |

Proibido: `PROJECT_ELIGIBILITY`, construir o grafo, resolver retificação, aritmética.

“0% alucinação” = aderência a schema, não acerto semântico.
