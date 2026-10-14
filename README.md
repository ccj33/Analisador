# Analisador de editais

Compila o pacote de uma chamada de fomento num grafo normativo verificável e compara esse grafo com fatos da organização e do projeto.

Não é chat com PDF. LLM, quando existir, é trabalhador da pipeline. O solver é determinístico. Jev é opcional e hoje o padrão é `AbstainProvider`.

Specs: [docs/MASTER_SPEC.md](docs/MASTER_SPEC.md), [docs/JEV_POLICY.md](docs/JEV_POLICY.md), [docs/GOLD_SET.md](docs/GOLD_SET.md).

## Rodar

```powershell
cd analisador-editais
python -m pip install -e ".[dev]"
python -m pytest
python -m tender_intel.cli compare --package fixtures/cnpq-universal-sintetica --facts fixtures/cnpq-universal-sintetica/facts-elegivel.json --source compiled
python -m tender_intel.cli compile --package fixtures/cnpq-universal-sintetica
python -m tender_intel.cli eval --case gold/cases/cnpq-universal-sintetica.json
```

A Review Table sai em `.out/review-table.html`.

## O que já existe

- Solver Kleene (`SATISFIED`, `UNSATISFIED`, `UNKNOWN`, `CONFLICT`)
- Ingestão de Markdown com IDs permanentes por linha
- Conferência de evidência por substring
- Parsers de CNPJ, data, hora e R$
- `DecisionProvider` com Jev desligável
- Fixture CNPq sintética + gold set de três perfis
- Camada `MERIT` visível e fora do SAT
- PDF com camada de texto (`pypdf`); página vazia fica marcada para OCR, sem OCR automático
- Compilação do grafo a partir do texto: elegibilidade, doutorado, Diretório, prazo vigente e mérito. Frase sem padrão não vira regra. Manual citado e ausente fica `UNRESOLVED`
- Revisão humana por `--review`, e a célula editada prevalece

## Ainda não

OCR e tabelas (Docling), chamada HTTP do Jev, cláusulas fora dos padrões determinísticos, Lattes/DI ao vivo, 8–12 chamadas reais anotadas, Review Table interativa.
