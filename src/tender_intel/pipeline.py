from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field, replace
from pathlib import Path
from typing import Any

from tender_intel.ai.provider import AbstainProvider, DecisionProvider, Question
from tender_intel.compile.coverage import clause_coverage, clauses_to_dict, coverage_counts
from tender_intel.compile.discover import discover
from tender_intel.compile.extract import compile_rules
from tender_intel.domain.ast import render_human
from tender_intel.domain.documents import TenderPackage
from tender_intel.domain.evidence import check_span
from tender_intel.domain.facts import store_from_dict
from tender_intel.domain.rules import NormativeRule, rules_from_dict
from tender_intel.domain.solver import solve
from tender_intel.domain.types import DecisionLayer, Status
from tender_intel.ingest.parsers import extract_deterministic
from tender_intel.ingest.text import ingest_package


@dataclass
class RuleEvaluation:
    rule_id: str
    title: str
    layer: str
    actor: str
    rendered: str
    status: str
    reason: str
    human_override: str | None
    evidence_ok: bool
    evidence_notes: list[str]
    blocking_facts: list[str]


@dataclass
class CompareResult:
    package_id: str
    title: str
    overall: str
    disclaimer: str
    coverage: dict[str, int]
    extracted: list[dict[str, str]]
    evaluations: list[RuleEvaluation]
    provider: str
    deadlines: list[dict]
    dependencies: list[dict]
    effects: list[dict]
    needs_ocr: list[dict]
    rule_source: str = "annotated"
    clauses: list[dict] = field(default_factory=list)


DISCLAIMER = (
    "Assistente de conformidade. Não é parecer jurídico nem garantia de aprovação "
    "pela agência. Campo não encontrado é diferente de campo vazio."
)


def compare_paths(
    package_dir: Path,
    facts_path: Path,
    provider: DecisionProvider | None = None,
    review_path: Path | None = None,
    source: str = "annotated",
) -> CompareResult:
    package = ingest_package(package_dir)
    facts_raw = json.loads(facts_path.read_text(encoding="utf-8"))
    if source == "compiled":
        rules = compile_rules(package)
    elif source == "annotated":
        graph = json.loads((package_dir / "graph.json").read_text(encoding="utf-8"))
        rules = rules_from_dict(graph)
    else:
        raise ValueError("source deve ser annotated ou compiled")
    if review_path is not None:
        rules = apply_review(rules, json.loads(review_path.read_text(encoding="utf-8")))
    return compare(package, rules, facts_raw, provider or AbstainProvider(), source)


def apply_review(rules: list[NormativeRule], review: dict[str, Any]) -> list[NormativeRule]:
    overrides = {item["rule_id"]: item["status"] for item in review.get("overrides", [])}
    return [replace(rule, human_override=overrides[rule.id]) if rule.id in overrides else rule for rule in rules]


def compare(
    package: TenderPackage,
    rules: list[NormativeRule],
    facts_raw: dict[str, Any],
    provider: DecisionProvider,
    rule_source: str = "annotated",
) -> CompareResult:
    store = store_from_dict(facts_raw)
    facts = store.current()
    extracted = extract_deterministic(package)
    _triage(package, provider)
    evaluations: list[RuleEvaluation] = []
    for rule in rules:
        notes = []
        evidence_ok = True
        for span in (*rule.evidence, *rule.relation_evidence):
            check = check_span(package, span)
            notes.append(f"{span.id}: {check.reason}")
            if not check.found:
                evidence_ok = False
        if rule.human_override:
            status = rule.human_override
            reason = "célula editada pelo humano prevalece"
        elif not evidence_ok:
            status = Status.UNKNOWN.value
            reason = "evidência não ancorada no documento"
        elif rule.layer != DecisionLayer.PRE_SUBMISSION:
            status = Status.NOT_APPLICABLE.value
            reason = "camada MERIT não entra no SAT da v1"
        else:
            result = solve(rule.expression, facts)
            status = result.status
            reason = result.reason
        blocking = [] if rule.human_override else list(solve(rule.expression, facts).blocking_facts)
        evaluations.append(
            RuleEvaluation(
                rule_id=rule.id,
                title=rule.title,
                layer=rule.layer.value,
                actor=rule.actor,
                rendered=render_human(rule.expression),
                status=status,
                reason=reason,
                human_override=rule.human_override,
                evidence_ok=evidence_ok,
                evidence_notes=notes,
                blocking_facts=blocking,
            )
        )
    draft = discover(package)
    clauses = clause_coverage(package, rules, draft)
    pre = [item for item in evaluations if item.layer == DecisionLayer.PRE_SUBMISSION.value]
    overall = _overall([item.status for item in pre])
    coverage = {
        "documents": len(package.documents),
        "elements": sum(len(document.elements) for document in package.documents),
        "rules": len(rules),
        "rules_with_grounded_evidence": sum(1 for item in evaluations if item.evidence_ok),
        "extracted_values": len(extracted),
        **coverage_counts(clauses),
    }
    return CompareResult(
        package_id=package.id,
        title=package.title,
        overall=overall,
        disclaimer=DISCLAIMER,
        coverage=coverage,
        extracted=[asdict(item) for item in extracted],
        evaluations=evaluations,
        provider=provider.__class__.__name__,
        deadlines=draft.to_dict()["deadlines"],
        dependencies=draft.to_dict()["dependencies"],
        effects=draft.to_dict()["effects"],
        needs_ocr=draft.to_dict()["needs_ocr"],
        rule_source=rule_source,
        clauses=clauses_to_dict(clauses),
    )


def _triage(package: TenderPackage, provider: DecisionProvider) -> None:
    sample = next((element.text for document in package.documents for element in document.elements if element.kind == "item"), "")
    if not sample:
        return
    provider.decide(
        {"passage": sample[:2000]},
        [
            Question("rule_category", "choice", "Qual a categoria desta cláusula?", ("ELIGIBILITY", "DEADLINE", "FAQ", "unclear")),
            Question("contains_deadline", "noul", "Esta cláusula contém prazo de submissão?"),
        ],
    )


def _overall(statuses: list[str]) -> str:
    # Nenhuma regra extraída não é "nada a cumprir": é não saber.
    if not statuses:
        return Status.UNKNOWN.value
    if any(status == Status.UNSATISFIED.value for status in statuses):
        return Status.UNSATISFIED.value
    if any(status == Status.CONFLICT.value for status in statuses):
        return Status.CONFLICT.value
    if any(status == Status.UNKNOWN.value for status in statuses):
        return Status.UNKNOWN.value
    return Status.SATISFIED.value


def result_to_dict(result: CompareResult) -> dict[str, Any]:
    return {
        "package_id": result.package_id,
        "title": result.title,
        "overall": result.overall,
        "disclaimer": result.disclaimer,
        "coverage": result.coverage,
        "extracted": result.extracted,
        "evaluations": [asdict(item) for item in result.evaluations],
        "provider": result.provider,
        "deadlines": result.deadlines,
        "dependencies": result.dependencies,
        "effects": result.effects,
        "needs_ocr": result.needs_ocr,
        "rule_source": result.rule_source,
        "clauses": result.clauses,
    }
