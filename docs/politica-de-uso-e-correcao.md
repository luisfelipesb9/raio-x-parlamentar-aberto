# Política de uso e correção

## Princípios
- **Não é acusação.** O Raio-X Parlamentar mostra o que os dados públicos indicam. Um achado é uma pista para
  quem quiser investigar, não uma conclusão sobre a conduta de alguém.
- **Presunção de inocência.** Processo sem condenação definitiva não é culpa. O guardrail R08 impede que a
  ausência de dado vire "não há problema" e que processo em andamento vire "culpado".
- **Votação simbólica não é voto individual.** O guardrail R02 retira essas votações das contas de votos.
- **A certeza é sempre declarada.** Cada achado traz um fator de certeza e o caminho de raciocínio; indício
  de identidade não confirmada tem teto baixo de certeza.
- **Rastreável.** Cada fato aponta para a fonte oficial e para a data da coleta.

## Como contestar ou corrigir um dado
1. Abra uma issue com o modelo **"Correção de dado"**.
2. Diga qual deputado e qual informação está errada, e indique a **fonte oficial** (com link) que mostra o correto.
3. **Nunca cole CPF** (nem o seu, nem o de terceiros). Descreva o dado sem o número; se for preciso identificar
   alguém, use o nome e a fonte oficial.
4. Se a questão envolve dado pessoal exposto, use o relato privado descrito em [SECURITY.md](../SECURITY.md).

## O que o projeto faz
- Verifica a informação na fonte oficial.
- Corrige em prazo razoável (é um projeto voluntário, sem prazo contratual).
- Registra a correção no [CHANGELOG](../CHANGELOG.md).
- Remove o dado quando for erro de identidade (homônimo, ligação errada entre pessoas ou empresas).

## LGPD em linguagem simples
- Só entram dados de **fontes oficiais abertas**. Não coletamos dados de parentes ou de terceiros que não sejam públicos.
- CPF de terceiros (doadores, sócios, fornecedores) é trocado por um código irreversível sem a chave
  (pseudonimização HMAC, [ADR-006](adr/ADR-006-pseudonimizacao.md)).
- A base publicada **não tem CPF íntegro**; uma varredura confere isso antes de publicar. Bancos com CPF
  não são versionados.

## O que o projeto NÃO faz
- Não é fonte oficial: confirme sempre na fonte indicada em cada achado.
- Não é parecer jurídico nem substitui a Justiça ou os órgãos de controle.
- Não faz ranking de "piores deputados", nem dá nota moral.
