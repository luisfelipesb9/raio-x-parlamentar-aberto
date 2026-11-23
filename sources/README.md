# sources/
Um plugin por órgão público. Cada um implementa `sources.base.Source` (`fetch` → bruto em data/raw, `normalize` → list[Fact]).
Plugins: `camara` (deputados, votações, votos, orientação, proposições/autorias opt-in), `ceap`, `tse` (candidaturas, doações,
votos por município; eleição 2022), `cgu` (CEIS/CNEP, emendas), `opensanctions` (br_pep, nested JSON; CC BY-NC 4.0) e
`rfb` (BrasilAPI, só CNPJs vistos). CPF do deputado via `GET /deputados/{id}` com `fetch(detalhar_deputados=True)` (`--detalhar-deputados`). Dono: Luis.
