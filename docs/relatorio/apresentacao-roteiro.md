# Roteiro da apresentação (12 slides, ~15 minutos)

Público: banca de Sistemas Especialistas, com leitores leigos em mente. Regra: cada slide tem **uma** ideia.

1. **Título e pergunta.** "O que meu deputado fez, e quanto o sistema tem certeza disso?" Nomes, disciplina, Unimontes.
2. **Problema.** Dados públicos dispersos (Câmara, TSE, Receita, CGU), sem explicação, com armadilhas (homônimo, CPF mascarado, votação simbólica). Mostrar um exemplo de armadilha.
3. **Estado da arte.** Tabela: Serenata, Parlametria, Basômetro, Radar Parlamentar, Radar da República, Radar do Voto, Elas no Congresso. Lacuna: nenhum integra tudo com incerteza explícita. Eles viram os "especialistas" do projeto.
4. **Arquitetura em um desenho.** Diagrama mermaid de `docs/arquitetura.md`: fontes → resolução → fatos → motor (+ regras YAML) → API → web. Fato/conhecimento/inferência/explicação coloridos.
5. **Base de conhecimento.** Mostrar `R03.yaml` na tela. "Regra é dado, não código." 9 regras + R06b; 2 guardrails; 1 composta.
6. **Motor e fatores de certeza.** Fórmulas MYCIN (combinação, conjunção, penalidade) e o semáforo alta/média/indício. Exemplo numérico: R01 0,95 × 0,7 = 0,665.
7. **Forward e backward.** Forward: gera todos os findings. Backward: `/perguntar` "merece atenção da fiscalização?" com R09 e a trilha da prova; ciclo detectado (ADR-004).
8. **Explicação.** Demo do botão "Como sabemos disso?": trilha, guardrails, penalidades, link da fonte oficial.
9. **Incerteza do dado e ética.** Resolução de entidades com CF; R06 versus R06b (teto 0,4, nome não exposto; ADR-003); presunção de inocência (R08); LGPD.
10. **Resultados na amostra.** 20 deputados de MG: 40 findings (R01 14, R03 2, R04 5, R05 10, R07 9; CF médio da R07 0,384 por propagar o CF do link por nome). Resolução: 20/20 candidaturas e 20/20 PEP por CPF; emendas 2.083 no escopo (37.297/77.113 no total global CGU); 3.189 links empresa; 254 sanção.
11. **Honestidade metodológica.** CFs e limiares **não calibrados**; amostra pequena; R06 confirmado inalcançável (QSA sempre mascarado); sem validação com leigos. Trabalhos futuros.
12. **Demonstração e encerramento.** Ficha leiga, grafo, comparar (a web está em andamento: ter capturas de reserva; mencionar pseudonimização da base pública, ADR-006). Repositório, perguntas.

Dicas: ensaiar a demo com `make sample` + `make dev`; ter prints se a rede falhar; reservar 3 minutos para perguntas sobre calibração de CF.
