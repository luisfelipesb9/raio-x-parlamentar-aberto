# Política de segurança

## Como relatar
Use o **relato privado de vulnerabilidade do GitHub** (aba "Security" do repositório, botão
"Report a vulnerability"). **Não abra issue pública** para falha de segurança nem para CPF ou dado
pessoal exposto: o relato público espalharia o problema.

O relato deve ter:
- o que você encontrou e onde (arquivo, rota da API, tela ou banco);
- passos para reproduzir;
- o impacto que você enxerga;
- **sem CPF real**: descreva o formato ("CPF íntegro na tabela X, coluna Y"), não cole o número.

## O que esperar
O projeto é mantido por voluntários, sem prazo contratual. A meta é confirmar o recebimento em poucos dias,
corrigir com prioridade quando houver exposição de dado pessoal, e registrar a correção no
[CHANGELOG](CHANGELOG.md), dando crédito a quem relatou se a pessoa quiser.

## Versões suportadas
Só a versão mais recente (série 0.2.x) recebe correções.

## O que conta
- CPF íntegro de terceiros em qualquer artefato publicado (banco público, API, site, arquivos versionados).
- Falha no pseudonimizador (`ingest/pseudonimizar.py`) ou na varredura (`ingest/varredura.py`) que deixe passar CPF ou permita reverter o pseudônimo sem o sal.
- Vazamento do sal `RAIO_X_ID_SALT` ou de qualquer segredo.
- Injeção (SQL ou de conteúdo), execução de código e acesso de escrita ao banco pela API, que deve ser somente leitura.
- Falha que faça o site ou a API apresentar conclusão sem o aviso de certeza, ou tratar processo sem condenação como culpa, de forma que cause dano concreto: relate como bug ou correção de dado, a menos que envolva dado pessoal.

## O que não conta
Erro de dado público da fonte oficial (siga a [política de uso e correção](docs/politica-de-uso-e-correcao.md)),
limitação documentada (veja o README) e ataques que exijam acesso físico à máquina de quem roda o projeto.
