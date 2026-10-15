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

Há um caso sintético versionado em `fixtures/cnpq-universal-sintetica/` e anotado em `gold/cases/cnpq-universal-sintetica.json`.

Próximo passo da Fase 0: anotar 8–12 chamadas reais CNPq/FAPEMIG com o mesmo schema. Não colar editais com direitos restritos neste repositório sem autorização; ligar por URL + hash.
