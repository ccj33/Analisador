"""Exigência em português simples, para quem nunca leu um edital.

A frase sai da expressão da regra e do vocabulário de fatos, não de um resumo escrito à mão:
quem confere o gabarito lê exatamente o que o solver vai checar. Fato sem rótulo aparece cru
(`unlabeled_facts` lista quais), em vez de virar uma frase bonita e errada.
"""
from __future__ import annotations

from datetime import datetime
from typing import Any

from tender_intel.domain.ast import All, AnyOf, Compare, FactRef, Literal, Not, Unless, render_human

ACTORS = {
    "PROPONENT": "Proponente",
    "COORDINATOR": "Coordenador(a)",
    "SUBCOORDINATOR": "Subcoordenador(a)",
    "PROJECT": "Projeto",
    "INSTITUTION": "Instituição de execução",
}

# fato → (frase quando verdadeiro, frase quando falso)
BOOL_FACTS = {
    "organization.is_mei": ("a proponente é MEI (microempreendedor individual)", "a proponente não é MEI (microempreendedor individual)"),
    "organization.fapemig_registered": ("a proponente tem pré-cadastro ou cadastro regular na FAPEMIG", "a proponente não tem cadastro na FAPEMIG"),
    "organization.proposals_distinct_challenges": ("cada proposta da proponente é para um Desafio diferente", "a proponente tem mais de uma proposta para o mesmo Desafio"),
    "project.has_prior_interest_statement": ("a proposta traz a Manifestação de Interesse emitida pelo Órgão Demandante", "a proposta não traz a Manifestação de Interesse do Órgão Demandante"),
    "project.has_activities_outside_mg": ("o projeto tem atividades fora de Minas Gerais", "o projeto não tem atividades fora de Minas Gerais"),
    "project.outside_mg_activities_accessory": ("as atividades fora de Minas Gerais são só acessórias ou complementares, sem ser o núcleo do projeto", "as atividades fora de Minas Gerais incluem o núcleo do projeto"),
    "project.outside_mg_activities_justified": ("as atividades fora de Minas Gerais estão justificadas no Plano de Trabalho", "as atividades fora de Minas Gerais não estão justificadas no Plano de Trabalho"),
    "project.plans_technical_missions": ("o projeto prevê missões técnicas entre os grupos do Brasil e da França", "o projeto não prevê missões técnicas"),
    "project.all_institutions_di_registered": ("todas as instituições envolvidas estão cadastradas no Diretório de Instituições do CNPq", "nem todas as instituições envolvidas estão cadastradas no Diretório de Instituições do CNPq"),
    "project.only_operating_costs": ("o pedido é só de despesas de custeio", "o pedido inclui despesas que não são de custeio"),
    "project.has_french_team": ("o projeto tem cooperação com um grupo de pesquisa da França", "o projeto não tem cooperação com grupo de pesquisa da França"),
    "coordinator.bond_with_proponent": ("o(a) coordenador(a) tem vínculo com a proponente", "o(a) coordenador(a) não tem vínculo com a proponente"),
    "coordinator.everest_registered": ("o(a) coordenador(a) está cadastrado(a) no sistema EVEREST da FAPEMIG", "o(a) coordenador(a) não está cadastrado(a) no sistema EVEREST da FAPEMIG"),
    "coordinator.lattes_updated": ("o(a) coordenador(a) tem currículo Lattes atualizado até o prazo de envio", "o(a) coordenador(a) não tem currículo Lattes atualizado até o prazo de envio"),
    "coordinator.has_phd": ("o(a) coordenador(a) tem doutorado", "o(a) coordenador(a) não tem doutorado"),
    "coordinator.in_organizing_committee": ("o(a) coordenador(a) faz parte da comissão organizadora do evento", "o(a) coordenador(a) não faz parte da comissão organizadora do evento"),
    "coordinator.bond_with_institution": ("o(a) coordenador(a) tem vínculo formal com a instituição de execução", "o(a) coordenador(a) não tem vínculo formal com a instituição de execução"),
    "coordinator.declares_no_default": ("o(a) coordenador(a) declara que não tem dívidas (inadimplência) com o CNPq nem com a Administração Pública Federal", "o(a) coordenador(a) não declara que está em dia com o CNPq e a Administração Pública Federal"),
    "coordinator.is_retired": ("o(a) coordenador(a) é aposentado(a)", "o(a) coordenador(a) não é aposentado(a)"),
    "coordinator.academic_activity": ("o(a) coordenador(a) comprova que mantém atividade acadêmico-científica", "o(a) coordenador(a) não comprova atividade acadêmico-científica"),
    "coordinator.institution_agreement": ("a instituição de execução declara que concorda com a execução do projeto", "a instituição de execução não declara que concorda com a execução do projeto"),
    "subcoordinator.is_career_public_servant": ("o(a) subcoordenador(a) é servidor(a) ou empregado(a) público(a) de carreira", "o(a) subcoordenador(a) não é servidor(a) ou empregado(a) público(a) de carreira"),
    "subcoordinator.from_challenge_author_body": ("o(a) subcoordenador(a) é de órgão ou entidade do Estado de Minas Gerais autor do Desafio", "o(a) subcoordenador(a) não é do órgão ou entidade autor do Desafio"),
    "subcoordinator.only_commissioned_post": ("o(a) subcoordenador(a) ocupa só cargo em comissão", "o(a) subcoordenador(a) não ocupa só cargo em comissão"),
    "subcoordinator.signed_interest_statement": ("o(a) subcoordenador(a) assina a Manifestação de Interesse na Proposta Prévia", "o(a) subcoordenador(a) não assina a Manifestação de Interesse na Proposta Prévia"),
    "subcoordinator.works_in_challenge_area": ("o(a) subcoordenador(a) atua no Órgão Demandante, em área ligada ao Desafio", "o(a) subcoordenador(a) não atua no Órgão Demandante em área ligada ao Desafio"),
    "subcoordinator.has_authorization": ("o(a) subcoordenador(a) tem declaração do Órgão Demandante autorizando sua participação", "o(a) subcoordenador(a) não tem declaração do Órgão Demandante autorizando sua participação"),
    "subcoordinator.indicated_in_everest": ("o(a) subcoordenador(a) está indicado(a) como subcoordenador(a) da proposta no EVEREST", "o(a) subcoordenador(a) não está indicado(a) como subcoordenador(a) no EVEREST"),
    "institution.di_registered": ("a instituição de execução está cadastrada no Diretório de Instituições do CNPq", "a instituição de execução não está cadastrada no Diretório de Instituições do CNPq"),
    "event.already_funded_by_cnpq": ("o evento já recebeu apoio do CNPq em outra ação", "o evento ainda não recebeu apoio do CNPq em outra ação"),
    "proposal.has_attachment": ("a proposta leva o arquivo anexo obrigatório", "a proposta não leva o arquivo anexo"),
    "proposal.attachment_pdf_ocr": ("o arquivo anexo é um PDF com OCR (texto pesquisável)", "o arquivo anexo não é um PDF com OCR"),
}

# fato → (sujeito, rótulo de cada valor)
ENUM_FACTS = {
    "organization.type": ("a proponente é", {"EMPRESA": "empresa", "STARTUP": "startup", "COOPERATIVA": "cooperativa", "ICT_MG": "ICT de Minas Gerais"}),
    "project.execution_state": ("o projeto é executado em", {"MG": "Minas Gerais"}),
    "project.category": ("o projeto é da", {"A": "Categoria A (pesquisa científica ou metodologias)", "B": "Categoria B (desenvolvimento tecnológico)"}),
    "project.line": ("a proposta é da", {1: "Linha 1 (eventos mundiais)", 2: "Linha 2 (eventos tradicionais)", 3: "Linha 3 (eventos não tradicionais)"}),
    "institution.type": ("a instituição de execução é", {
        "ICT": "ICT (instituição científica, tecnológica e de inovação)",
        "EMPRESA_PUBLICA": "empresa pública",
        "EMPRESA_PRIVADA": "empresa privada brasileira",
        "OSC": "organização da sociedade civil sem fins lucrativos",
    }),
    "event.promoter_type": ("quem promove o evento é", {"SOCIEDADE_CIENTIFICA": "uma sociedade ou associação científica ou tecnológica", "UNIDADE_ICT": "uma unidade acadêmica ou tecnológica de uma ICT"}),
    "event.size": ("o evento é de", {"GRANDE": "grande porte", "MEDIO": "médio porte", "PEQUENO": "pequeno porte"}),
    "event.scope": ("a abrangência do evento é", {"MUNDIAL": "mundial", "INTERNACIONAL": "internacional", "NACIONAL": "nacional", "REGIONAL": "regional", "LOCAL": "local"}),
    "coordinator.bond_type": ("o vínculo do(a) coordenador(a) com a instituição de execução é", {"CLT": "celetista (CLT)", "ESTATUTARIO": "estatutário"}),
}

# fato → (sujeito, unidade): "brl", "pct", "mb" ou (singular, plural)
NUMBER_FACTS = {
    "organization.proposals_submitted": ("a proponente envia", ("proposta", "propostas")),
    "organization.annual_gross_revenue_mg": ("o faturamento bruto anual da proponente é de", "brl"),
    "project.challenges_count": ("a proposta atende a", ("Desafio", "Desafios")),
    "project.duration_months": ("o prazo de execução é de", ("mês", "meses")),
    "project.financial_counterpart_pct": ("a contrapartida financeira é de", "pct"),
    "project.total_counterpart_pct": ("a contrapartida, somando a econômica e a financeira, é de", "pct"),
    "project.subcoordinators_count": ("a proposta tem", ("subcoordenador(a)", "subcoordenadores(as)")),
    "project.requested_brl": ("o valor pedido é de", "brl"),
    "coordinator.proposals_as_coordinator": ("o(a) coordenador(a) coordena", ("proposta", "propostas")),
    "proposal.attachment_mb": ("o arquivo anexo tem", "mb"),
}

# fato → (sujeito, mostra a hora)
DATE_FACTS = {
    "submission.started_at": ("a proposta é iniciada no sistema", True),
    "submission.sent_at": ("a proposta é enviada", True),
    "event.start_at": ("o evento começa", False),
    "event.end_at": ("o evento termina", False),
}

NUMBER_OPS = {"EQ": "exatamente", "NEQ": "um valor diferente de", "LTE": "no máximo", "GTE": "pelo menos", "LT": "menos de", "GT": "mais de"}
DATE_OPS = {"EQ": "em", "NEQ": "fora de", "LTE": "até", "GTE": "a partir de", "LT": "antes de", "GT": "depois de"}


def explain(node: Any, nested: bool = False) -> dict[str, Any]:
    """Árvore para a tela: {"text"} numa folha, {"all": [...]} ou {"any": [...]} num grupo.

    Grupo "todas" de até duas folhas, dentro de um "pelo menos uma", vira uma frase só.
    """
    if isinstance(node, AnyOf):
        merged = _one_of(node)
        if merged is not None:
            return {"text": _sentence(merged)}
        return {"any": [explain(arg, nested=True) for arg in node.args]}
    if isinstance(node, All):
        parts = _merge_all(list(node.args))
        items = [part if isinstance(part, dict) else explain(part, nested=True) for part in parts]
        if len(items) == 1:
            return items[0]
        if nested and len(items) <= 2 and all("text" in item for item in items):
            return {"text": _sentence(" e ".join(_lower_first(item["text"]) for item in items))}
        return {"all": items}
    if isinstance(node, Compare):
        return {"text": _sentence(_compare(node))}
    if isinstance(node, Not):
        inner = explain(node.arg, nested=True)
        if "text" in inner:
            return {"text": _sentence("não é verdade que " + _lower_first(inner["text"]))}
        return {"not": inner}
    if isinstance(node, Unless):
        return {"unless": {"rule": explain(node.body, nested=True), "except": explain(node.exception, nested=True)}}
    return {"text": render_human(node)}


def unlabeled_facts(node: Any) -> list[str]:
    """Fatos que a expressão consulta e que o vocabulário não sabe dizer em português."""
    if isinstance(node, (All, AnyOf)):
        return [fact for arg in node.args for fact in unlabeled_facts(arg)]
    if isinstance(node, Not):
        return unlabeled_facts(node.arg)
    if isinstance(node, Unless):
        return unlabeled_facts(node.body) + unlabeled_facts(node.exception)
    if isinstance(node, Compare) and isinstance(node.left, FactRef):
        key = node.left.key
        known = key in BOOL_FACTS or key in ENUM_FACTS or key in NUMBER_FACTS or key in DATE_FACTS
        if key in ENUM_FACTS and isinstance(node.right, Literal):
            known = node.right.value in ENUM_FACTS[key][1]
        return [] if known else [key]
    return []


def section_label(path: tuple[str, ...] | list[str]) -> str:
    if not path:
        return "início do documento"
    label = f"item {path[0]}"
    if len(path) > 1:
        label += f", alínea {path[1]}"
    return label


def format_brl(value: float) -> str:
    whole, cents = f"{value:,.2f}".split(".")
    return f"R$ {whole.replace(',', '.')},{cents}"


def format_datetime(value: str, with_time: bool) -> str:
    moment = datetime.fromisoformat(value)
    text = moment.strftime("%d/%m/%Y")
    if with_time:
        text += f", às {moment.hour:02d}h{moment.minute:02d}"
        offset = moment.strftime("%z")
        text += " (horário de Brasília)" if offset == "-0300" else f" (UTC{offset[:3]}:{offset[3:]})"
    return text


def _compare(node: Compare) -> str:
    if not (isinstance(node.left, FactRef) and isinstance(node.right, Literal)):
        return render_human(node)
    key, value, op = node.left.key, node.right.value, node.op
    if key in BOOL_FACTS and isinstance(value, bool) and op in ("EQ", "NEQ"):
        yes, no = BOOL_FACTS[key]
        return yes if value == (op == "EQ") else no
    if key in ENUM_FACTS and op in ("EQ", "NEQ") and value in ENUM_FACTS[key][1]:
        subject, labels = ENUM_FACTS[key]
        return f"{subject} {labels[value]}" if op == "EQ" else f"{subject.replace(' é', ' não é', 1)} {labels[value]}"
    if key in NUMBER_FACTS and isinstance(value, (int, float)) and op in NUMBER_OPS:
        subject, unit = NUMBER_FACTS[key]
        return f"{subject} {NUMBER_OPS[op]} {_amount(value, unit)}"
    if key in DATE_FACTS and isinstance(value, str) and op in DATE_OPS:
        subject, with_time = DATE_FACTS[key]
        return f"{subject} {DATE_OPS[op]} {format_datetime(value, with_time)}"
    return render_human(node)


def _amount(value: float, unit: Any) -> str:
    if unit == "brl":
        return format_brl(value)
    if unit == "pct":
        return f"{_number(value)}% do valor pedido"
    if unit == "mb":
        return f"{_number(value)} MB"
    singular, plural = unit
    return f"{_number(value)} {singular if value == 1 else plural}"


def _number(value: float) -> str:
    return str(int(value)) if float(value).is_integer() else str(value).replace(".", ",")


def _one_of(node: AnyOf) -> str | None:
    """`ANY(EQ(f, a), EQ(f, b))` sobre um fato com rótulos → "f é a ou b"."""
    keys, values = set(), []
    for arg in node.args:
        if not (isinstance(arg, Compare) and arg.op == "EQ" and isinstance(arg.left, FactRef) and isinstance(arg.right, Literal)):
            return None
        keys.add(arg.left.key)
        values.append(arg.right.value)
    key = next(iter(keys)) if len(keys) == 1 else None
    if key not in ENUM_FACTS or any(value not in ENUM_FACTS[key][1] for value in values):
        return None
    subject, labels = ENUM_FACTS[key]
    return f"{subject} {_join_or([labels[value] for value in values])}"


def _merge_all(args: list[Any]) -> list[Any]:
    """Junta o que se lê melhor numa frase: mínimo e máximo do mesmo número, início e fim do evento."""
    out: list[Any] = []
    used: set[int] = set()
    for index, arg in enumerate(args):
        if index in used:
            continue
        pair = _find_pair(args, index, used)
        if pair is not None:
            used.update(pair[0])
            out.append({"text": _sentence(pair[1])})
            continue
        out.append(arg)
    return out


def _find_pair(args: list[Any], index: int, used: set[int]) -> tuple[tuple[int, int], str] | None:
    first = args[index]
    if not (isinstance(first, Compare) and isinstance(first.left, FactRef) and isinstance(first.right, Literal) and first.op == "GTE"):
        return None
    for other_index, other in enumerate(args):
        if other_index == index or other_index in used:
            continue
        if not (isinstance(other, Compare) and isinstance(other.left, FactRef) and isinstance(other.right, Literal) and other.op == "LTE"):
            continue
        low, high = first.right.value, other.right.value
        if first.left.key == other.left.key and first.left.key in NUMBER_FACTS:
            subject, unit = NUMBER_FACTS[first.left.key]
            if isinstance(unit, tuple):
                return (index, other_index), f"{subject} {_number(low)} a {_number(high)} {unit[1]}"
            return (index, other_index), f"{subject} {_amount(low, unit)} a {_amount(high, unit)}"
        if first.left.key == "event.start_at" and other.left.key == "event.end_at":
            return (index, other_index), f"o evento acontece entre {format_datetime(low, False)} e {format_datetime(high, False)}"
    return None


def _join_or(labels: list[str]) -> str:
    if len(labels) == 1:
        return labels[0]
    # rótulo que já tem "ou" pede vírgula antes do "ou" que separa as opções
    last = ", ou " if any(" ou " in label for label in labels) else " ou "
    return ", ".join(labels[:-1]) + last + labels[-1]


def _sentence(text: str) -> str:
    return text[:1].upper() + text[1:] if text else text


def _lower_first(text: str) -> str:
    # "ICT", "MEI" e siglas no começo ficam como estão
    if len(text) > 1 and text[1].isupper():
        return text
    return text[:1].lower() + text[1:]
