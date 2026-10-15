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

Dois casos:

- `cnpq-universal-sintetica`: fixture sintética de desenvolvimento.
- `fapemig-sede-018-2026`: primeira chamada real (FAPEMIG/SEDE 018/2026, HubMG Gov), com 15 regras anotadas e três perfis. Linha de base do compilador de regex: 0 de 15 regras (15 omitidas, 0 inventadas).

Próximo passo da Fase 0: chegar a 8–12 chamadas reais CNPq/FAPEMIG com o mesmo schema. Edital público é ato oficial (Lei 9.610/1998, art. 8º, IV) e pode ser versionado. Material com direitos restritos (manual de terceiro, norma técnica paga) entra por URL + hash, não por cópia.
