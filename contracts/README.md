# contracts/
Tipos compartilhados entre camadas (Pydantic v2). Não importa nenhuma outra pasta.
- Entradas: nenhuma. Saídas: `Fact`, `Entity`, `Finding`, `Explanation`, `GraphNode`, `GraphEdge`.
- Versão atual: `0.2.0` (ADR-007). Mudança aqui = ADR + bump de `CONTRACT_VERSION`. Dono: Luis.
- `cnpj.py`: forma e DV do CNPJ numérico e alfanumérico (função pura, só stdlib). Não é tipo do contrato: não muda `CONTRACT_VERSION`.
