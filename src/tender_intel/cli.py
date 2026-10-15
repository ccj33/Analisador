from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from tender_intel.ai.provider import JevProvider
from tender_intel.compile.coverage import UNCLASSIFIED, clause_coverage, clauses_to_dict
from tender_intel.compile.discover import discover
from tender_intel.compile.extract import compile_rules
from tender_intel.domain.rules import rules_to_dict
from tender_intel.eval.harness import measure_case
from tender_intel.ingest.text import ingest_package
from tender_intel.pipeline import compare_paths, result_to_dict
from tender_intel.report import write_review_table


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Compilador de editais de fomento.")
    sub = parser.add_subparsers(dest="command", required=True)

    compare = sub.add_parser("compare", help="Compara grafo do pacote com fatos.")
    compare.add_argument("--package", required=True, type=Path)
    compare.add_argument("--facts", required=True, type=Path)
    compare.add_argument("--review", type=Path)
    compare.add_argument("--source", choices=("annotated", "compiled"), default="compiled")
    compare.add_argument("--out", type=Path, default=Path(".out"))

    compile_cmd = sub.add_parser("compile", help="Descobre prazos, retificações e referências externas.")
    compile_cmd.add_argument("--package", required=True, type=Path)
    compile_cmd.add_argument("--out", type=Path, default=Path(".out"))

    eval_cmd = sub.add_parser("eval", help="Mede um caso do gold set.")
    eval_cmd.add_argument("--case", required=True, type=Path)

    args = parser.parse_args(argv)
    if args.command == "compare":
        return _compare(args)
    if args.command == "compile":
        return _compile(args)
    return _eval(args)


def _compare(args: argparse.Namespace) -> int:
    provider = JevProvider()
    result = compare_paths(args.package, args.facts, provider, args.review, args.source)
    args.out.mkdir(parents=True, exist_ok=True)
    json_path = args.out / "compare.json"
    html_path = args.out / "review-table.html"
    json_path.write_text(json.dumps(result_to_dict(result), ensure_ascii=False, indent=2), encoding="utf-8")
    write_review_table(result, html_path)
    print(f"{result.overall}")
    print(result.disclaimer)
    print(f"JSON: {json_path}")
    print(f"Review Table: {html_path}")
    return 0 if result.overall != "CONFLICT" else 2


def _compile(args: argparse.Namespace) -> int:
    package = ingest_package(args.package)
    draft = discover(package)
    rules = compile_rules(package)
    args.out.mkdir(parents=True, exist_ok=True)
    path = args.out / "compile.json"
    graph_path = args.out / "compile-graph.json"
    payload = draft.to_dict()
    payload["rules"] = rules_to_dict(rules)["rules"]
    clauses = clause_coverage(package, rules, draft)
    payload["clauses"] = clauses_to_dict(clauses)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    graph_path.write_text(json.dumps(rules_to_dict(rules), ensure_ascii=False, indent=2), encoding="utf-8")
    effective = [item.iso_date for item in draft.deadlines if item.effective]
    unresolved = [item.target for item in draft.dependencies if item.status == "UNRESOLVED"]
    print(f"Regras compiladas: {len(rules)}")
    print(f"Prazo vigente: {effective[0] if effective else 'nenhum'}")
    print(f"Referências não resolvidas: {len(unresolved)}")
    unclassified = sum(1 for item in clauses if item.status == UNCLASSIFIED)
    print(f"Cláusulas sem classificação: {unclassified} de {len(clauses)}")
    print(f"JSON: {path}")
    print(f"Grafo: {graph_path}")
    return 0


def _eval(args: argparse.Namespace) -> int:
    report = measure_case(args.case)
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0 if report["ok"] else 1


if __name__ == "__main__":
    sys.exit(main())
