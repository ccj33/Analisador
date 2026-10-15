import json
from pathlib import Path

from tender_intel.domain.rules import rules_from_dict
from tender_intel.explain import explain, format_brl, section_label, unlabeled_facts

ROOT = Path(__file__).resolve().parents[1]
REAL_CASES = ("fapemig-sede-018-2026", "cnpq-arc-34-2026", "cnpq-anr-32-2026")


def _rules(case: str) -> dict:
    data = json.loads((ROOT / "fixtures" / case / "graph.json").read_text(encoding="utf-8"))
    return {rule.id: rule for rule in rules_from_dict(data)}


def test_every_gold_fact_has_plain_language():
    for case in REAL_CASES:
        for rule in _rules(case).values():
            assert unlabeled_facts(rule.expression) == [], (case, rule.id)


def test_single_conditions_read_as_sentences():
    fapemig = _rules("fapemig-sede-018-2026")
    assert explain(fapemig["FAP-MEI"].expression) == {"text": "A proponente não é MEI (microempreendedor individual)"}
    assert explain(fapemig["FAP-DURACAO"].expression) == {"text": "O prazo de execução é de 18 a 30 meses"}
    assert explain(fapemig["FAP-TIPO"].expression) == {"text": "A proponente é empresa, startup, cooperativa ou ICT de Minas Gerais"}
    assert explain(fapemig["FAP-DEADLINE"].expression) == {"text": "A proposta é enviada até 09/12/2026, às 23h59 (horário de Brasília)"}


def test_alternatives_keep_their_logic():
    limit = explain(_rules("fapemig-sede-018-2026")["FAP-LIMITE"].expression)
    assert limit == {"any": [
        {"text": "A proponente envia no máximo 1 proposta"},
        {"text": "O faturamento bruto anual da proponente é de pelo menos R$ 16.000.000,00 e a proponente envia no máximo 3 propostas"},
    ]}
    bond = explain(_rules("cnpq-anr-32-2026")["ANR-VINCULO"].expression)
    assert bond["any"][0] == {"text": "O vínculo do(a) coordenador(a) com a instituição de execução é celetista (CLT) ou estatutário"}
    assert len(bond["any"][1]["all"]) == 3
    period = explain(_rules("cnpq-arc-34-2026")["ARC-PERIODO"].expression)
    assert period["any"][0] == {"text": "A proposta é da Linha 1 (eventos mundiais) e o evento acontece entre 01/07/2027 e 31/07/2028"}


def test_labels():
    assert section_label(("3.2.1", "b")) == "item 3.2.1, alínea b"
    assert section_label(("13.1",)) == "item 13.1"
    assert format_brl(1500000) == "R$ 1.500.000,00"
