# Brief: Para estudantes de Sistemas Especialistas

- **URL sugerida:** `/estudantes`
- **Tipo:** pilar para público técnico (material didático)
- **Prompts que atende:** P22, P23, P24, P25, P26
- **Público:** estudante de graduação em computação e sistemas de informação; professor que procura exemplo real e pequeno
- **Intenção:** descoberta e decisão ("quero ver um exemplo completo")

## Primeira frase citável

"O Raio-X Parlamentar é um sistema especialista pequeno e aberto que separa base de fatos, base de conhecimento em regras YAML, motor de inferência com encadeamento progressivo e regressivo, fatores de certeza no estilo MYCIN e módulo de explicação, aplicados a dados públicos sobre deputados federais."

## Estrutura de H2

1. **Os cinco blocos de um sistema especialista e onde estão no código** (tabela conceito-arquivo do relatório, seção 4: base de fatos, base de conhecimento, motor, explicação, interface; links para os arquivos no repositório, a confirmar com os autores)
2. **A base de conhecimento: regras em YAML** (anatomia de uma regra: `se`, `entao`, `cf`, `penalidades`, `por_que`, `limitacoes`, `fonte_metodologica`; mostrar o arquivo da R01 inteiro, que é curto)
3. **Fatores de certeza, com conta feita à mão** (as três fórmulas do relatório 3.4: combinar duas evidências, conjunção de premissas, penalidades; exemplo trabalhado: R01, 0,95 x 0,7 = 0,665, nível "média"; e R06b, 0,85 x 0,4 = 0,34, "indício")
4. **Encadeamento progressivo: dos fatos às conclusões** (como `forward` executa guardrails, regras e gera findings)
5. **Encadeamento regressivo: de um objetivo aos fatos** (como `prove(objetivo, deputado)` resolve sub-objetivos com `requer`, combina regras e detecta ciclos; exemplo: R09 requer `risco_integridade`; ADR-004)
6. **Guardrails: regras que impedem conclusões** (R02 e R08 como regras de prioridade alta que podam fatos antes das regras de inferência)
7. **Explicação: o "como" e o "por quê"** (trilha de `Explanation`, `PassoProva`; link para `/perguntar`)
8. **Engenharia do conhecimento: de onde vieram as regras** (elicitação por análise documental, não por entrevista; cada regra declara fonte metodológica e limitações; validação com especialistas é trabalho futuro)
9. **O que este sistema não é** (sem calibração dos CFs; sem validação com leigos; comparação externa só da R01; amostra de 20 deputados)
10. **Exercícios** (3 a 5 propostas: calcular o CF de uma regra com duas penalidades; escrever uma regra nova no formato do `_schema.md`; mostrar por que um ciclo em `requer` vale CF 0; discutir limiar 0,7 de R01 como escolha do especialista; abrir issue "Nova regra")
11. **Referências** (Shortliffe e Buchanan 1975; Buchanan e Shortliffe 1984; Giarratano e Riley 2004; CF/88 art. 5º, LVII; LGPD; as referências completas do relatório)

## Dados e fontes a citar (com link)

| Afirmação | Fonte | Link |
|---|---|---|
| MYCIN foi um sistema especialista de Stanford, com regras SE-ENTÃO e fatores de certeza | Buchanan e Shortliffe, 1984, capítulo 10 | PDF da Universidade Columbia (apareceu em busca de 2026-11-26): https://impact.dbmi.columbia.edu/~ehs7001/Buchanan-Shortliffe-1984/Chapter-10.pdf (abrir antes de citar) |
| Modelo de fatores de certeza | "The Certainty-Factor Model", publicação da Microsoft Research (resultado de busca; autoria não lida, ler na página) | https://www.microsoft.com/en-us/research/publication/certainty-factor-model/ (abrir; confirmar autoria) |
| Análise de sensibilidade mostrou pouca dependência do desempenho do MYCIN em mudanças dos CFs | arXiv 1304.3419 (resultado de busca) | https://arxiv.org/pdf/1304.3419 (abrir; só citar se confirmar; serve para a ressalva sobre calibração) |
| Arquitetura e CFs do projeto | `docs/relatorio/relatorio.md` seções 3 e 4; ADR-004 | repositório (link a confirmar) |

## Schema.org

- `Article` + `LearningResource` (`educationalLevel: "graduação"`, `learningResourceType: "material de estudo"`, `inLanguage: pt-BR`), com `teaches` listando os conceitos.
- `BreadcrumbList`.
- Se a página tiver um tutorial passo a passo (calcular CF), um `HowTo` só para essa seção, com os passos visíveis.
- Código de exemplo marcado com `SoftwareSourceCode` apenas se houver link estável do repositório (a confirmar).

## O que NÃO afirmar

- Que o sistema é "o MYCIN do Brasil" ou comparação de qualidade com sistemas históricos.
- Que os fatores de certeza são probabilidades ou foram calibrados.
- Que o conhecimento foi elicitado com especialistas humanos (foi por análise documental).
- Que o motor é "inteligência artificial" no sentido de aprendizado. Ele não aprende: aplica regras. Dizer isso em uma frase evita confusão.
- Que é referência acadêmica validada. É trabalho de disciplina de graduação.

## Aviso de não acusação

Linha curta no rodapé da página: "Os exemplos usam dados fictícios. Os dados reais mostram pistas, não acusações; veja `/metodo`."

## Links internos

`/metodo`, `/regras` (R01, R06, R09 como exemplos), `/glossario/fator-de-certeza`, `/glossario/encadeamento-progressivo`, `/glossario/guardrail`, `/perguntar`, `/dados-e-api`.

## Notas de redação

- Todo exemplo numérico é refeito à mão no texto, para o leitor conferir.
- Usar a base fictícia da demonstração (`make demo`, `docs/demo.md`) nas telas e capturas.
- Frescor: revisar quando o motor mudar de regra ou de limiar.
