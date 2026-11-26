# Avaliação heurística de usabilidade (10 heurísticas de Nielsen)

Avaliação do `web/` do Raio-X Parlamentar feita por inspeção do código e uso das telas, sem teste com pessoas
(a validação com leigos continua pendente; ver `docs/HANDOFF.md`). Severidade de 0 a 4 (0 = não é problema,
1 = cosmético, 2 = menor, 3 = grave, 4 = catastrófico). Os commits abaixo estão no branch da faixa U.

| # | Heurística | Problema observado antes | Sev. | O que foi corrigido | Pendente |
|---|---|---|---|---|---|
| 1 | Visibilidade do estado do sistema | `components/Perguntar.tsx`: a resposta aparecia sem aviso para leitor de tela e sem foco, fora da vista em telas pequenas. | 3 | Resposta anunciada (`aria-live="polite"`), com foco e rolagem até o bloco, só depois de a pessoa apertar "Perguntar" (`fe95d09`). Rolagem respeita reduced-motion e o botão de pausa. | Nenhuma. |
| 2 | Correspondência com o mundo real | "Fator de certeza (CF)", "guardrail" e "janela" apareciam sem explicação (`AlertaCard.tsx`, `Perguntar.tsx`, `Comparar.tsx`, `lib/glossario.ts`). | 3 | Rótulo principal "Nível de certeza (CF)", termo técnico mantido como `Termo`/tooltip; verbetes novos: cobertura dos dados, janela de votação, nível de certeza máximo, votos válidos, impressão digital (`e616450`, `8c3361a`). | Termos do grafo (nó, aresta) ficam no glossário do mapa. |
| 3 | Controle e liberdade do usuário | Trilha da prova sempre aberta e sem atalho (`Perguntar.tsx`); resultado vazio sem saída (`Busca.tsx`, `Picker.tsx`). | 2 | Passos da trilha abrem e fecham (setas, Enter, clique); "Limpar filtros e ver todos" no vazio da busca (`fe95d09`, `7c8387e`). | Desfazer a escolha de deputado em `/comparar` continua só por trocar o seletor. |
| 4 | Consistência e padrões | Nomes diferentes para o mesmo número ("CF", "Fator de certeza", "certeza máxima") entre telas; botões de ação com alturas diferentes. | 2 | Mesmo rótulo "Nível de certeza" em ficha, alerta, comparar e perguntar; botões novos usam `.btn` (44 px) (`e616450`, `7c8387e`). | Revisar a tela do mapa na faixa do grafo. |
| 5 | Prevenção de erros | Pergunta sem deputado e consultas sem dados levavam a "Inconclusivo" genérico, parecendo veredito (`lib/nivel.ts`, `Perguntar.tsx`). | 3 | Texto do inconclusivo sem juízo ("nem que haja algo errado"); resposta explica o motivo com números do diagnóstico da API (`6bd5197`). Aviso "isto não é acusação" mantido em todas as telas. | Nenhuma. |
| 6 | Reconhecer em vez de lembrar | Mapa de relações: lista e direção das ligações pouco reconhecíveis. Fora do grafo: ficha não mostrava de onde veio cada número. | 3 | Ficha: painel "Dados e verificação" com janela de votos, números por regra e fontes com data de coleta (`8c3361a`); página `/fontes` (`6189ade`). | Heurística 6 no mapa: tratada na faixa do grafo. |
| 7 | Flexibilidade e eficiência | Trilha da prova só com mouse e sem ordem de Tab útil (`role="tree"` sem teclado). | 3 | Navegação por teclado no padrão ARIA tree: setas, Home/End, direita/esquerda para abrir/fechar, `tabindex` gerenciado, `aria-label="Trilha da prova"` mantido (`fe95d09`). | Atalhos globais (por exemplo, `/` para buscar) não foram feitos. |
| 8 | Estética e design minimalista | `Perguntar.tsx`: a explicação do método de combinar certezas aparecia duas vezes; mensagem de inconclusivo repetida em três lugares. | 2 | Repetição removida; a resposta mostra uma frase por motivo, sem repetir o texto genérico (`6bd5197`, `7c8387e`). | Densidade do mapa: tratada na faixa do grafo. |
| 9 | Ajudar a reconhecer, diagnosticar e corrigir erros | Mensagem "Nenhuma regra se confirmou" não dizia por quê nem o que fazer. | 3 | Frases concretas ("Só encontramos N votos válidos… precisa de pelo menos 10"; "Com N votos válidos, X% acompanharam… só conclui a partir de 70%") e botões "Fazer outra pergunta" e "Ver a cobertura dos dados" (`6bd5197`). Estados de carregando e erro do painel usam `Estados.tsx`. | Só a R01 tem diagnóstico; as outras regras caem no texto "Os dados atuais não ativam esta regra". |
| 10 | Ajuda e documentação | Não havia página explicando fontes, cobertura e método; o leitor não sabia como conferir. | 3 | Página `/fontes` (link no menu e no rodapé): tabela de fontes com datas de coleta, janela de votos vinda da API, por que o teto da R01 é 0,665 e que ampliar a janela é possível, como conferir (`make verifica`); "Verificar na fonte" em cada alerta (`6189ade`, `8c3361a`). | Teste com leigos e vídeo/tour curto não feitos. |

## Acessibilidade adicional

`prefers-contrast: more` e `forced-colors: active` em `web/src/app/ux.css` (focos, bordas, selos e medidor sem depender de cor);
alvos de 44 px nos links do menu e nos controles novos; efeitos respeitam reduced-motion e o botão de pausa (`7c8387e`).
Decisão mantida: tema claro por padrão, escuro só por escolha no botão (sem modo "sistema").

## O que não foi verificado

- Os testes e2e (Playwright) foram adaptados e estendidos, mas não rodados nesta faixa.
- Nenhum teste com pessoas; severidades são julgamento de quem avaliou.
- Leitores de tela reais (NVDA, VoiceOver) não foram usados; o comportamento do `aria-live` e da árvore foi conferido só pelo código e pelo navegador.
