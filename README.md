# Analisador de editais

Compila o pacote de uma chamada de fomento num grafo normativo verificável e compara esse grafo com fatos da organização e do projeto.

Não é chat com PDF. LLM, quando existir, é trabalhador da pipeline. O solver é determinístico. Jev é opcional e hoje o padrão é `AbstainProvider`.

Specs: [docs/MASTER_SPEC.md](docs/MASTER_SPEC.md), [docs/JEV_POLICY.md](docs/JEV_POLICY.md), [docs/GOLD_SET.md](docs/GOLD_SET.md). Plano de execução, fase por fase: [docs/PLANO.md](docs/PLANO.md).

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
- Ingestão de Markdown, DOCX (sem dependência externa) e texto extraído de PDF. Linhas quebradas pelo PDF voltam a ser uma cláusula (item numerado, alínea, título), rodapé do SEI sai e cada cláusula guarda a página
- Conferência de evidência por substring
- Parsers de CNPJ, data, hora e R$
- `DecisionProvider` com Jev desligável
- Fixture CNPq sintética + gold set de três perfis
- Camada `MERIT` visível e fora do SAT
- PDF com camada de texto (`pypdf`); página vazia fica marcada para OCR, sem OCR automático
- Compilação do grafo a partir do texto: elegibilidade, doutorado, Diretório, prazo vigente e mérito. Frase sem padrão não vira regra. Manual citado e ausente fica `UNRESOLVED`
- Cobertura por cláusula: toda cláusula lida sai como `RULE`, `DISCOVERY` (prazo, referência ou efeito) ou `UNCLASSIFIED`. As não classificadas aparecem na Review Table e no `compile.json`, em vez de sumir
- Eval do compilador regra a regra contra a anotação (omissão, invenção, lógica diferente, valor fora da citação)
- Revisão humana por `--review`, e a célula editada prevalece
- Cada regra em português simples (`tender_intel.explain`), gerado da própria expressão, sem resumo escrito à mão
- Página de conferência do gabarito: `python gold/export_review.py conferencia-gabarito.html` monta a página com as regras dos editais reais e o trecho de cada uma

## Ainda não

OCR e tabelas (Docling), chamada HTTP do Jev, cláusulas fora dos padrões determinísticos, Lattes/DI ao vivo, 8–12 chamadas reais anotadas (há 3), Review Table interativa.
