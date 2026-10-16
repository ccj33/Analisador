# Chamada FAPEMIG-SEDE 018/2026 — HubMG Gov

Primeira chamada real do gold set. Processo SEI 2070.01.0004193/2026-74, publicada em 09/10/2026.

- `edital.txt`: camada de texto do PDF oficial (SEI 150716523), como extraída. Inclui os anexos I–XIII que vêm dentro do PDF.
- `anexo-*.docx`: anexos I–IX como publicados em DOCX.
- `graph.json`: gabarito anotado à mão, gerado por `gold/build.py`. Cobre só o que dá para verificar na submissão: itens 3.1, 3.2, 3.3, 3.5, 5.1, 5.4 e 13.1. Mérito, contratação e prestação de contas ficam de fora.
- `facts-*.json`: três perfis (startup completa, sem subcoordenador informado, MEI com duas propostas).

Edital é ato oficial; não tem proteção de direito autoral (Lei 9.610/1998, art. 8º, IV).

O gabarito cita seção + trecho; se a segmentação mudar, rode `python gold/build.py`.
