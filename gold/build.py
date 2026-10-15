"""Gabaritos anotados à mão, citando seção + trecho em vez de element_id.

O element_id depende da segmentação; a seção e a citação, não. Rode
`python gold/build.py` depois de mudar a ingestão para regenerar os graph.json.
Cada citação tem de existir, exatamente uma vez, na seção indicada.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from tender_intel.domain.evidence import check_span, normalize  # noqa: E402
from tender_intel.domain.rules import rules_from_dict  # noqa: E402
from tender_intel.ingest.text import ingest_package  # noqa: E402


def eq(fact, value):
    return {"op": "EQ", "left": {"fact": fact}, "right": {"literal": value}}


def cmp(op, fact, value):
    return {"op": op, "left": {"fact": fact}, "right": {"literal": value}}


def ALL(*args):
    return {"op": "ALL", "args": list(args)}


def ANY(*args):
    return {"op": "ANY", "args": list(args)}


def one_of(fact, *values):
    return ANY(*(eq(fact, value) for value in values))


def rule(rule_id, title, actor, expression, evidence, relation=(), layer="PRE_SUBMISSION"):
    data = {"id": rule_id, "title": title, "layer": layer, "actor": actor, "expression": expression, "evidence": list(evidence)}
    if relation:
        data["relation_evidence"] = list(relation)
    return data


class Annotator:
    def __init__(self, package_dir: Path, default_doc: str):
        self.package = ingest_package(package_dir)
        self.default_doc = default_doc

    def ev(self, span_id, section, quote, doc=None):
        doc = doc or self.default_doc
        path = tuple(section.split("/")) if section else ()
        hits = [
            element
            for document in self.package.documents
            if document.id == doc
            for element in document.elements
            if element.section_path == path and normalize(quote) in normalize(element.text)
        ]
        if len(hits) != 1:
            raise SystemExit(f"{span_id}: {len(hits)} elementos em {section!r} com a citação {quote!r}")
        return {"id": span_id, "element_id": hits[0].id, "quote": quote}


def fapemig_sede_018_2026(a: Annotator):
    ev = a.ev
    return [
        rule("FAP-TIPO", "Proponente é empresa, startup, cooperativa ou ICT-MG", "PROPONENT",
             ANY(*(eq("organization.type", t) for t in ("EMPRESA", "STARTUP", "COOPERATIVA", "ICT_MG"))),
             [ev("EV-TIPO", "3.1.1", "Poderão figurar como Proponente empresas, startups, cooperativas ou ICTs-MG")],
             [ev("EV-TIPO-OU", "3.1.1", "empresas, startups, cooperativas ou ICTs-MG")]),
        rule("FAP-MEI", "Proponente não é MEI", "PROPONENT", eq("organization.is_mei", False),
             [ev("EV-MEI", "3.1.1/d", "a Proponente não poderá ser enquadrada como Microempreendedor Individual (MEI)")]),
        rule("FAP-EXEC-MG", "Execução do projeto em Minas Gerais", "PROJECT", eq("project.execution_state", "MG"),
             [ev("EV-EXEC", "3.1.1/c", "a execução do projeto deverá ocorrer no Estado de Minas Gerais")]),
        rule("FAP-CADASTRO", "Pré-cadastro ou cadastro regular na FAPEMIG", "PROPONENT", eq("organization.fapemig_registered", True),
             [ev("EV-CAD", "3.1.2", "Todas as Proponentes deverão ter pré-cadastro ou cadastro regular na FAPEMIG")]),
        rule("FAP-LIMITE", "Uma proposta, ou até três com faturamento ≥ R$ 16 milhões", "PROPONENT",
             ANY(cmp("LTE", "organization.proposals_submitted", 1),
                 ALL(cmp("GTE", "organization.annual_gross_revenue_mg", 16000000), cmp("LTE", "organization.proposals_submitted", 3))),
             [ev("EV-LIM1", "3.1.5", "Cada Proponente poderá submeter 1 (uma) Proposta"),
              ev("EV-LIM3", "3.1.5.1", "faturamento bruto anual igual ou superior a R$ 16.000.000,00 (dezesseis milhões de reais) poderá submeter até 3 (três) propostas")],
             [ev("EV-LIM-EXC", "3.1.5", "ressalvado o disposto no item 3.1.5.1")]),
        rule("FAP-DESAFIO", "Proposta vinculada a um único Desafio", "PROJECT", eq("project.challenges_count", 1),
             [ev("EV-DES", "3.2.1", "Cada proposta deverá atender a um único Desafio")]),
        rule("FAP-MANIFESTACAO", "Manifestação de Interesse na Proposta Prévia", "PROJECT", eq("project.has_prior_interest_statement", True),
             [ev("EV-MAN", "3.2.2/a", "estar acompanhadas da Manifestação de Interesse na Proposta Prévia emitida pelo Órgão Demandante")]),
        rule("FAP-DURACAO", "Prazo de execução entre 18 e 30 meses", "PROJECT",
             ALL(cmp("GTE", "project.duration_months", 18), cmp("LTE", "project.duration_months", 30)),
             [ev("EV-DUR", "3.2.2/g", "apresentar prazo de execução de, no mínimo, 18 (dezoito) e, no máximo, 30 (trinta) meses")]),
        rule("FAP-CONTRAPARTIDA", "Contrapartida mínima de 10% do valor solicitado", "PROPONENT",
             cmp("GTE", "project.counterpart_pct", 10),
             [ev("EV-CP-EMP", "5.4.1", "contrapartida financeira mínima obrigatória equivalente a 10% (dez por cento) do valor total a ser solicitado à FAPEMIG"),
              ev("EV-CP-ICT", "5.4.2", "contrapartida econômica mínima obrigatória equivalente a 10% (dez por cento) do valor total a ser solicitado à FAPEMIG")]),
        rule("FAP-VALOR", "Valor solicitado dentro do teto da categoria", "PROJECT",
             ANY(ALL(eq("project.category", "A"), cmp("LTE", "project.requested_brl", 1000000)),
                 ALL(eq("project.category", "B"), cmp("LTE", "project.requested_brl", 2000000))),
             [ev("EV-VAL", "5.1", "A Projeto de pesquisa científica ou desenvolvimento de metodologias R$ 1.000.000,00 (um milhão de reais) B Projeto de desenvolvimento tecnológico R$ 2.000.000,00 (dois milhões de reais)")],
             [ev("EV-VAL-CAT", "5.1", "Esta Chamada contempla 2 (duas) categorias de apoio, conforme a natureza do projeto")]),
        rule("FAP-COORD-VINCULO", "Coordenador com vínculo com a Proponente", "COORDINATOR", eq("coordinator.bond_with_proponent", True),
             [ev("EV-CVIN", "3.3.1", "Possuir vínculo com a Proponente que celebrará instrumento jurídico com a FAPEMIG")]),
        rule("FAP-COORD-EVEREST", "Coordenador cadastrado no EVEREST", "COORDINATOR", eq("coordinator.everest_registered", True),
             [ev("EV-CEV", "3.3.3", "Estar cadastrado no sistema EVEREST da FAPEMIG.")]),
        rule("FAP-COORD-UMA", "Coordenador de no máximo uma proposta", "COORDINATOR", cmp("LTE", "coordinator.proposals_as_coordinator", 1),
             [ev("EV-CUMA", "3.3.4", "Submeter e ser responsável por apenas 1 (uma) Proposta, na condição de Coordenador")]),
        rule("FAP-SUBCOORD", "Subcoordenador atende 3.5.1 a–d", "SUBCOORDINATOR",
             ALL(eq("subcoordinator.is_career_public_servant", True), eq("subcoordinator.works_in_challenge_area", True),
                 eq("subcoordinator.has_authorization", True), eq("subcoordinator.indicated_in_everest", True)),
             [ev("EV-SUB-A", "3.5.1/a", "ser servidor público ou empregado público, de carreira ou concursado"),
              ev("EV-SUB-B", "3.5.1/b", "atuar no Órgão Demandante em área vinculada à temática do Desafio"),
              ev("EV-SUB-C", "3.5.1/c", "apresentar declaração formal do Órgão Demandante autorizando sua participação no projeto"),
              ev("EV-SUB-D", "3.5.1/d", "ser formalmente indicado como Subcoordenador da Proposta no sistema EVEREST da FAPEMIG")],
             [ev("EV-SUB-E", "3.5.1", "deverá atender, cumulativamente, aos seguintes requisitos")]),
        rule("FAP-DEADLINE", "Envio até 23h59 de 09/12/2026", "PROPONENT",
             cmp("LTE", "submission.sent_at", "2026-12-09T23:59:00-03:00"),
             [ev("EV-DL", "13.1", "até as 17h do dia 09 de dezembro de 2026, ficando o sistema disponível para a conclusão e o envio definitivo até as 23h59 do mesmo dia")]),
    ]


# Nas chamadas do CNPq o proponente é o coordenador (ARC 3.2.1/c, ANR 3.2.1): requisitos da pessoa
# usam coordinator.*, como na FAPEMIG, para o eval parear a mesma exigência entre chamadas.
def cnpq_arc_34_2026(a: Annotator):
    ev = a.ev
    return [
        rule("ARC-LATTES", "Currículo Lattes atualizado até a submissão", "COORDINATOR", eq("coordinator.lattes_updated", True),
             [ev("EV-LAT", "3.2.1/a", "ter seu currículo cadastrado na Plataforma Lattes, atualizado até a data limite para submissão da proposta")]),
        rule("ARC-PHD", "Proponente com doutorado", "COORDINATOR", eq("coordinator.has_phd", True),
             [ev("EV-PHD", "3.2.1/b", "possuir o título de Doutor")]),
        rule("ARC-COMISSAO", "Proponente na comissão organizadora", "COORDINATOR", eq("coordinator.in_organizing_committee", True),
             [ev("EV-COM", "3.2.1/d", "participar da comissão organizadora do evento")]),
        rule("ARC-VINCULO", "Vínculo formal com a instituição de execução", "COORDINATOR", eq("coordinator.bond_with_institution", True),
             [ev("EV-VIN", "3.2.1/e", "ter vínculo formal com a instituição de execução do projeto")]),
        rule("ARC-ADIMPLENTE", "Declara não ter inadimplência com CNPq e APF", "COORDINATOR", eq("coordinator.declares_no_default", True),
             [ev("EV-ADI", "3.2.2", "o proponente deverá declarar para os devidos fins de direito que não possui qualquer inadimplência com o CNPq e com a Administração Pública Federal")]),
        rule("ARC-INEDITO", "Evento ainda não apoiado pelo CNPq em outra ação", "PROJECT", eq("event.already_funded_by_cnpq", False),
             [ev("EV-INED", "3.2.3", "o evento objeto da proposta ainda não foi contemplado com auxílio financeiro do CNPq em outra ação de fomento")]),
        rule("ARC-INST", "Instituição de execução no Diretório e ICT, empresa pública ou OSC", "INSTITUTION",
             ALL(eq("institution.di_registered", True), one_of("institution.type", "ICT", "EMPRESA_PUBLICA", "OSC")),
             [ev("EV-INST", "3.3.1", "A instituição de execução do projeto deverá estar cadastrada no Diretório de Instituições do CNPq, devendo ser uma Instituição Científica, Tecnológica e de Inovação (ICT), empresa pública ou organização da sociedade civil sem fins lucrativos")],
             [ev("EV-INST-E", "3.3.1", "devendo ser")]),
        rule("ARC-PROMOTOR", "Promotor é sociedade científica ou unidade de ICT", "PROJECT",
             one_of("event.promoter_type", "SOCIEDADE_CIENTIFICA", "UNIDADE_ICT"),
             [ev("EV-PROM", "3.4.1", "Os eventos deverão ser promovidos por sociedades ou associações científicas e/ou tecnológicas ou unidades acadêmicas ou tecnológicas integrantes da estrutura de Instituições Científicas, Tecnológicas e de Inovação (ICTs)")]),
        rule("ARC-PORTE", "Evento de grande porte e abrangência nacional ou maior", "PROJECT",
             ALL(eq("event.size", "GRANDE"), one_of("event.scope", "MUNDIAL", "INTERNACIONAL", "NACIONAL")),
             [ev("EV-PORTE", "1.3.4/a", "eventos de médio e pequeno porte"), ev("EV-ABR", "1.3.4/b", "eventos de abrangência local ou regional")],
             [ev("EV-NAO", "1.3.4", "Não serão elegíveis a esta Chamada")]),
        rule("ARC-VALOR", "Valor dentro do teto da Linha", "PROJECT",
             ANY(ALL(eq("project.line", 1), cmp("LTE", "project.requested_brl", 200000)),
                 ALL(eq("project.line", 2), cmp("LTE", "project.requested_brl", 200000)),
                 ALL(eq("project.line", 3), cmp("LTE", "project.requested_brl", 150000))),
             [ev("EV-VAL", "4.3", "Linha 1 – Eventos Mundiais Até R$ 200.000,00 Linha 2 – Eventos Tradicionais Até R$ 200.000,00 Linha 3 – Eventos Não Tradicionais Até R$ 150.000,00")],
             [ev("EV-VAL-FX", "4.3", "de acordo com uma das seguintes faixas")]),
        rule("ARC-PERIODO", "Evento realizado no período da Linha", "PROJECT",
             ANY(ALL(eq("project.line", 1), cmp("GTE", "event.start_at", "2027-07-01T00:00:00-03:00"), cmp("LTE", "event.end_at", "2028-07-31T23:59:00-03:00")),
                 ALL(one_of("project.line", 2, 3), cmp("GTE", "event.start_at", "2027-07-01T00:00:00-03:00"), cmp("LTE", "event.end_at", "2028-06-30T23:59:00-03:00"))),
             [ev("EV-PER1", "2.1/a", "realizados no período de 01/07/2027 a 31/07/2028"),
              ev("EV-PER2", "2.1/b", "realizados no período de 01/07/2027 a 30/06/2028"),
              ev("EV-PER3", "2.1/c", "realizados no período de 01/07/2027 a 30/06/2028")]),
        rule("ARC-ARQUIVO", "Arquivo anexo enviado, PDF de até 1 Mb", "PROJECT",
             ALL(eq("proposal.has_attachment", True), cmp("LTE", "proposal.attachment_mb", 1)),
             [ev("EV-ARQ", "6.6.2", "O envio do arquivo é obrigatório e a ausência implicará no indeferimento da proposta"),
              ev("EV-ARQ-MB", "6.6.3", "limitando-se a 1Mb (um megabyte)")]),
        rule("ARC-DEADLINE", "Envio até 23h59 de 04/12/2026", "PROPONENT",
             cmp("LTE", "submission.sent_at", "2026-12-04T23:59:00-03:00"),
             [ev("EV-DL", "2.1/c", "Data limite para submissão das propostas 04/12/2026"),
              ev("EV-DL-H", "6.2", "será até às 23h59 (vinte e três horas e cinquenta e nove minutos), horário de Brasília")]),
    ]


def cnpq_anr_32_2026(a: Annotator):
    ev = a.ev
    return [
        rule("ANR-LATTES", "Currículo Lattes atualizado até a submissão", "COORDINATOR", eq("coordinator.lattes_updated", True),
             [ev("EV-LAT", "3.2.1/a", "ter seu currículo cadastrado na Plataforma Lattes, atualizado até a data limite para submissão da proposta")]),
        rule("ANR-PHD", "Proponente com doutorado", "COORDINATOR", eq("coordinator.has_phd", True),
             [ev("EV-PHD", "3.2.1/b", "possuir o título de doutor(a)")]),
        rule("ANR-VINCULO", "Vínculo celetista/estatutário, ou aposentado em atividade com concordância", "COORDINATOR",
             ANY(one_of("coordinator.bond_type", "CLT", "ESTATUTARIO"),
                 ALL(eq("coordinator.is_retired", True), eq("coordinator.academic_activity", True), eq("coordinator.institution_agreement", True))),
             [ev("EV-VIN", "3.2.1/c", "possuir vínculo celetista ou estatutário com a instituição de execução do projeto"),
              ev("EV-APOS", "3.2.1/c", "caso seja aposentado, comprovar que mantém atividade acadêmico-científica e apresentar declaração da instituição de execução do projeto concordando com a sua execução")],
             [ev("EV-VIN-OU", "3.2.1/c", "ou, caso seja aposentado")]),
        rule("ANR-ADIMPLENTE", "Declara não estar inadimplente com CNPq e APF", "COORDINATOR", eq("coordinator.declares_no_default", True),
             [ev("EV-ADI", "3.2.2", "não está inadimplente junto ao CNPq e à Administração Pública Federal")]),
        rule("ANR-INST", "Instituição de execução no Diretório e de tipo admitido", "INSTITUTION",
             ALL(eq("institution.di_registered", True), one_of("institution.type", "ICT", "EMPRESA_PRIVADA", "EMPRESA_PUBLICA", "OSC")),
             [ev("EV-INST", "3.3.1", "A instituição de execução do projeto deverá estar cadastrada no Diretório de Instituições do CNPq, devendo ser uma Instituição Científica, Tecnológica e de Inovação (ICT) e/ou empresa privada constituída sob as leis brasileiras, com sede e foro no Brasil, bem como empresa pública ou organização da sociedade civil sem fins lucrativos")]),
        rule("ANR-DI-TODAS", "Todas as instituições envolvidas no Diretório", "INSTITUTION", eq("project.all_institutions_di_registered", True),
             [ev("EV-DI", "6.7", "Todas as instituições de pesquisas envolvidas com o projeto, sejam nacionais ou internacionais, devem estar cadastradas previamente no Diretório de Instituições do CNPq")]),
        rule("ANR-VALOR", "Até R$ 1,5 milhão, só custeio", "PROJECT",
             ALL(cmp("LTE", "project.requested_brl", 1500000), eq("project.only_operating_costs", True)),
             [ev("EV-VAL", "4.1.1", "Cada proposta poderá solicitar até R$ 1.500.000,00 (um milhão e quinhentos mil reais), exclusivamente em despesas de custeio")]),
        rule("ANR-FRANCA", "Cooperação com grupo de pesquisa da França", "PROJECT", eq("project.has_french_team", True),
             [ev("EV-FR", "6.9.5", "Os projetos de pesquisa devem prever, obrigatoriamente, a cooperação entre grupos de pesquisa do Brasil e da França")]),
        rule("ANR-ARQUIVO", "Arquivo anexo enviado, PDF de até 1 Mb", "PROJECT",
             ALL(eq("proposal.has_attachment", True), cmp("LTE", "proposal.attachment_mb", 1)),
             [ev("EV-ARQ", "6.9.2", "O envio do arquivo é obrigatório"),
              ev("EV-ARQ-MB", "6.9.3", "limitando-se a 1 Mb (um megabyte)")]),
        rule("ANR-DEADLINE", "Envio até 23h59 de 31/03/2027", "PROPONENT",
             cmp("LTE", "submission.sent_at", "2027-03-31T23:59:00-03:00"),
             [ev("EV-DL", "2", "Data limite para submissão das propostas 31/03/2027"),
              ev("EV-DL-H", "6.5", "será até às 23h59 (vinte e três horas e cinquenta e nove minutos), horário de Brasília")]),
    ]


CASES = {
    "fapemig-sede-018-2026": ("edital", fapemig_sede_018_2026),
    "cnpq-arc-34-2026": ("chamada", cnpq_arc_34_2026),
    "cnpq-anr-32-2026": ("chamada", cnpq_anr_32_2026),
}


def main() -> None:
    for case, (doc, build) in CASES.items():
        package_dir = ROOT / "fixtures" / case
        annotator = Annotator(package_dir, doc)
        rules = build(annotator)
        for parsed in rules_from_dict({"rules": rules}):
            for span in (*parsed.evidence, *parsed.relation_evidence):
                check = check_span(annotator.package, span)
                if not check.found:
                    raise SystemExit(f"{case} {parsed.id} {span.id}: {check.reason}")
        (package_dir / "graph.json").write_text(json.dumps({"rules": rules}, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        print(f"{case}: {len(rules)} regras")


if __name__ == "__main__":
    main()
