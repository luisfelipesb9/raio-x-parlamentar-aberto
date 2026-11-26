# sources/
Um plugin por órgão público. Cada um implementa `sources.base.Source` (`fetch` → bruto em data/raw, `normalize` → list[Fact]).
Plugins: `camara` (deputados, votações, votos, orientação, proposições/autorias opt-in), `ceap`, `tse` (candidaturas, doações,
votos por município; eleição 2022), `cgu` (CEIS/CNEP, emendas), `opensanctions` (br_pep, nested JSON; CC BY-NC 4.0) e
`rfb` (BrasilAPI, só CNPJs vistos). CPF do deputado via `GET /deputados/{id}` com `fetch(detalhar_deputados=True)` (`--detalhar-deputados`). Dono: Luis.

## Manifesto do bruto (`data/raw/manifest.json`)
`Source.save_raw` e `Source.registrar_raw` gravam, por arquivo bruto, `{fonte, arquivo, sha256, bytes, coletado_em,
origem}` (escrita atômica; ver `sources/manifest.py`). Fonte nova que baixa arquivo sem `save_raw` deve chamar
`self.registrar_raw(nome_do_arquivo)` depois do download e declarar em `fontes_fato` os `Fact.fonte` que produz.
`origem` é `coleta` ou `retroativo` (arquivo que já existia: hash e data de modificação; ver `scripts/verifica.py --gerar-manifesto`).
Limite: `Evidence.sha256_bruto` só é preenchido quando a fonte do fato tem UM arquivo no manifesto; Câmara (votações e
proposições), CGU (três zips) e RFB (um JSON por CNPJ) têm vários e ficam sem hash na evidência.
