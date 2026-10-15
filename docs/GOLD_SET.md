# GOLD_SET

Protocolo de anotação da Fase 0. Sem gold set, Jev e frontier são chute.

## Pacote mínimo por caso

- `package_id`
- arquivos do pacote (chamada, FAQ, retificações)
- para cada regra: texto-fonte, `element_id`, predicado, operador, ator, camada (`PRE_SUBMISSION` | `MERIT`), se é exceção
- fatos de pelo menos dois perfis (elegível / incompleto ou inelegível)

## Métricas

- omissão vs invenção, por tipo de cláusula
- citation overlap: o span extraído é substring do documento
- acurácia do solver sem LLM
- valores numéricos e datas têm de aparecer na evidência

## Estado atual

`tender-intel eval` mede cada caso duas vezes: com o grafo anotado (só o solver) e com o grafo compilado do texto. O compilador é comparado à anotação regra a regra, pareando pelos fatos consultados: `MATCH`, `DIFFERENT_LOGIC` (mesmos fatos, operador ou valor diferente), `OMITTED` e `INVENTED`, agrupados por camada/ator, com sobreposição de evidência e números/datas que não aparecem na citação.

Quatro casos (um sintético, três reais):

| caso | regras anotadas | compilador de regex |
| --- | --- | --- |
| `cnpq-universal-sintetica` | 6 | 6 de 6 |
| `fapemig-sede-018-2026` (FAPEMIG/SEDE 018/2026, HubMG Gov) | 15 | 0 de 15 |
| `cnpq-arc-34-2026` (CNPq 34/2026, eventos) | 13 | 0 de 13 |
| `cnpq-anr-32-2026` (MCTI/CNPq/ANR 32/2026, Brasil–França) | 10 | 0 de 10 |

Cada caso real tem três perfis (elegível, incompleto, inelegível) e o grafo anotado acerta os três.

Os gabaritos reais são escritos em `gold/build.py`, citando seção (`3.2.1/b`) e trecho, não `element_id`. Depois de mudar a ingestão, `python gold/build.py` regenera os `graph.json`; se uma citação deixar de existir na seção, o script para.

Vocabulário de fatos: a mesma exigência usa a mesma chave em todas as chamadas (`coordinator.has_phd`, `coordinator.lattes_updated`, `institution.di_registered`, `submission.sent_at`, `project.requested_brl`…), senão o eval não pareia. Nas chamadas do CNPq o proponente é o coordenador, então requisitos da pessoa ficam em `coordinator.*`.

Próximo passo da Fase 0: chegar a 8–12 chamadas reais CNPq/FAPEMIG com o mesmo schema. Edital público é ato oficial (Lei 9.610/1998, art. 8º, IV) e pode ser versionado. Material com direitos restritos (manual de terceiro, norma técnica paga) entra por URL + hash, não por cópia.
