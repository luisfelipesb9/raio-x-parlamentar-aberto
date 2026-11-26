#!/usr/bin/env bash
# Configura o repositório no GitHub para o dia em que ele ficar PÚBLICO.
#
# Padrão: DRY-RUN (só mostra o que faria; faz apenas leituras pela API). Escreve só com --aplicar.
# Idempotente: rodar de novo deixa tudo no mesmo estado (PUT/PATCH; ruleset e rótulo são
# procurados pelo nome e atualizados em vez de duplicados).
#
# Passos (detalhes e o que continua manual: docs/operacao-github.md):
#   1. relato privado de vulnerabilidades      PUT   /repos/{r}/private-vulnerability-reporting
#   2. secret scanning + push protection       PATCH /repos/{r}  (security_and_analysis)
#   3. alertas do Dependabot                   PUT   /repos/{r}/vulnerability-alerts
#   4. correções automáticas do Dependabot     PUT   /repos/{r}/automated-security-fixes
#   5. apagar a branch ao mesclar              PATCH /repos/{r}  (delete_branch_on_merge)
#   6. rótulo `dependencias` (dependabot.yml)  POST  /repos/{r}/labels  (se não existir)
#   7. ruleset da main                         POST/PUT /repos/{r}/rulesets
#
# Uso:
#   scripts/gh_publicar.sh [owner/repo]                         # dry-run
#   scripts/gh_publicar.sh [owner/repo] --aplicar               # aplica
#   scripts/gh_publicar.sh [owner/repo] --aplicar --historico-linear
#   scripts/gh_publicar.sh [owner/repo] --aplicar --exigir-seo-smoke   # só depois dos PRs de SEO
# Checks obrigatórios: python, web, gitleaks (+ seo-smoke com --exigir-seo-smoke).
# Administradores do repositório podem contornar o ruleset em PR (nunca ficam travados).
# Requer: gh autenticado com permissão de admin no repositório (gh auth status).
set -euo pipefail

REPO_PADRAO="luisfelipesb9/raio-x-parlamentar-aberto"
NOME_RULESET="main protegida"
CHECKS=(python web gitleaks)  # nomes dos jobs em .github/workflows/ci.yml (seo-smoke: --exigir-seo-smoke)
ID_PAPEL_ADMIN=5              # RepositoryRole "admin" (maintain=2, write=4)
ID_GITHUB_ACTIONS=15368                  # app "GitHub Actions": só ela pode satisfazer os checks
ROTULO="dependencias"

APLICAR=0
LINEAR=0
SEO_SMOKE=0
REPO=""
FALHAS=0

# Imprime o cabeçalho de comentários (da linha 2 até a primeira linha que não é comentário).
uso() { awk 'NR == 1 { next } /^#/ { sub(/^# ?/, ""); print; next } { exit }' "$0"; }

for arg in "$@"; do
  case "$arg" in
    --aplicar) APLICAR=1 ;;
    --historico-linear) LINEAR=1 ;;
    --exigir-seo-smoke) SEO_SMOKE=1 ;;
    -h|--help) uso; exit 0 ;;
    -*) echo "opção desconhecida: $arg" >&2; uso >&2; exit 64 ;;
    *)
      if [[ -n "$REPO" ]]; then echo "repositório informado duas vezes: $arg" >&2; exit 64; fi
      REPO="$arg" ;;
  esac
done
REPO="${REPO:-$REPO_PADRAO}"
if [[ ! "$REPO" =~ ^[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+$ ]]; then
  echo "repositório inválido: '$REPO' (use owner/repo)" >&2
  exit 64
fi

if ! command -v gh >/dev/null 2>&1; then
  if [[ $APLICAR -eq 1 ]]; then echo "gh (GitHub CLI) não encontrado no PATH." >&2; exit 69; fi
  echo "aviso: gh não encontrado; o dry-run mostra o plano sem consultar o estado atual." >&2
  TEM_GH=0
elif gh auth status >/dev/null 2>&1; then
  TEM_GH=1
else
  if [[ $APLICAR -eq 1 ]]; then echo "gh não está autenticado: rode 'gh auth login'." >&2; exit 69; fi
  echo "aviso: gh sem autenticação; o dry-run mostra o plano sem consultar o estado atual." >&2
  TEM_GH=0
fi

# Leitura (permitida também no dry-run). Imprime a resposta; falha silenciosa vira código != 0.
ler() {
  [[ $TEM_GH -eq 1 ]] || return 1
  gh api -H "Accept: application/vnd.github+json" "$@" 2>/dev/null
}

# Explica erros comuns em linguagem clara (sem esconder a resposta original).
explicar_erro() {
  local saida="$1"
  case "$saida" in
    *"HTTP 404"*) echo "    recurso não encontrado ou sem permissão de admin (404)." ;;
    *"HTTP 403"*) echo "    recusado (403): em repositório PRIVADO de conta gratuita este recurso não existe" \
                       "(ou o token não tem escopo de admin). Rode de novo depois de tornar o repo público." ;;
    *"HTTP 422"*) echo "    recusado (422): o recurso não está disponível neste repositório (comum em repo" \
                       "PRIVADO sem GitHub Advanced Security) ou o corpo foi rejeitado." ;;
    *) ;;
  esac
  echo "    resposta: $(printf '%s' "$saida" | tr '\n' ' ' | cut -c1-300)"
}

# executar "descrição" MÉTODO caminho [corpo-json]
executar() {
  local desc="$1" metodo="$2" caminho="$3" corpo="${4:-}" saida
  if [[ $APLICAR -eq 0 ]]; then
    echo "[dry-run] $desc"
    echo "          gh api -X $metodo $caminho${corpo:+ --input - <<< '$corpo'}"
    return 0
  fi
  echo "[aplicar] $desc"
  if [[ -n "$corpo" ]]; then
    if saida=$(printf '%s' "$corpo" | gh api -X "$metodo" -H "Accept: application/vnd.github+json" \
                 "$caminho" --input - 2>&1); then
      echo "    ok"; return 0
    fi
  else
    if saida=$(gh api -X "$metodo" -H "Accept: application/vnd.github+json" "$caminho" 2>&1 </dev/null); then
      echo "    ok"; return 0
    fi
  fi
  echo "    FALHOU"
  explicar_erro "$saida"
  FALHAS=$((FALHAS + 1))
  return 0  # segue para os próximos passos; o código de saída final reflete as falhas
}

echo "Repositório: $REPO  (modo: $([[ $APLICAR -eq 1 ]] && echo APLICAR || echo DRY-RUN))"
if visibilidade=$(ler "repos/$REPO" --jq .visibility); then
  echo "Visibilidade atual: $visibilidade"
  if [[ "$visibilidade" != "public" ]]; then
    echo "aviso: o repositório não é público; relato privado, secret scanning e ruleset podem ser" \
         "recusados até ele ficar público (o script explica cada recusa e segue)."
  fi
fi
echo

# 1. Relato privado de vulnerabilidades (aba Security > Advisories > Report a vulnerability)
executar "1. ativar o relato privado de vulnerabilidades" PUT "repos/$REPO/private-vulnerability-reporting"

# 2. Secret scanning + push protection (bloqueia o push que contém segredo conhecido)
executar "2. ativar secret scanning e push protection" PATCH "repos/$REPO" \
  '{"security_and_analysis":{"secret_scanning":{"status":"enabled"},"secret_scanning_push_protection":{"status":"enabled"}}}'

# 3 e 4. Dependabot: alertas de vulnerabilidade e PRs automáticos de correção
executar "3. ativar alertas do Dependabot" PUT "repos/$REPO/vulnerability-alerts"
executar "4. ativar correções automáticas de segurança do Dependabot" PUT "repos/$REPO/automated-security-fixes"

# 5. Apagar a branch do PR depois do merge
executar "5. apagar a branch ao mesclar" PATCH "repos/$REPO" '{"delete_branch_on_merge":true}'

# 6. Rótulo usado pelo .github/dependabot.yml (sem ele o Dependabot comenta erro nos PRs)
if ler "repos/$REPO/labels/$ROTULO" >/dev/null; then
  echo "[ok]      6. rótulo '$ROTULO' já existe"
else
  executar "6. criar o rótulo '$ROTULO'" POST "repos/$REPO/labels" \
    "{\"name\":\"$ROTULO\",\"color\":\"0366d6\",\"description\":\"Atualização de dependências (Dependabot)\"}"
fi

# 7. Ruleset da branch padrão: PR obrigatório (0 aprovações: são 2 mantenedores e um deles pode
#    ser quem abriu o PR), checks do CI obrigatórios, sem force-push e sem apagar a branch.
#    Bypass: papel admin, só em PR ("pull_request"): um admin pode mesclar um PR com check
#    vermelho numa emergência, mas nem ele faz push direto, force-push ou apaga a main.
[[ $SEO_SMOKE -eq 1 ]] && CHECKS+=(seo-smoke)
checks_json=""
for c in "${CHECKS[@]}"; do
  checks_json+="${checks_json:+,}{\"context\":\"$c\",\"integration_id\":$ID_GITHUB_ACTIONS}"
done
regra_linear=""
[[ $LINEAR -eq 1 ]] && regra_linear=',{"type":"required_linear_history"}'
ruleset=$(cat <<JSON
{"name":"$NOME_RULESET","target":"branch","enforcement":"active",
 "bypass_actors":[{"actor_id":$ID_PAPEL_ADMIN,"actor_type":"RepositoryRole","bypass_mode":"pull_request"}],
 "conditions":{"ref_name":{"include":["~DEFAULT_BRANCH"],"exclude":[]}},
 "rules":[
  {"type":"deletion"},
  {"type":"non_fast_forward"},
  {"type":"pull_request","parameters":{"required_approving_review_count":0,"dismiss_stale_reviews_on_push":true,
   "require_code_owner_review":false,"require_last_push_approval":false,"required_review_thread_resolution":true}},
  {"type":"required_status_checks","parameters":{"strict_required_status_checks_policy":false,
   "required_status_checks":[$checks_json]}}$regra_linear
 ]}
JSON
)
ruleset=$(printf '%s' "$ruleset" | tr -d '\n')
echo "          checks obrigatórios: ${CHECKS[*]}"
id_ruleset=""
if lista=$(ler "repos/$REPO/rulesets" --jq ".[] | select(.name == \"$NOME_RULESET\") | .id"); then
  id_ruleset=$(printf '%s' "$lista" | head -n1)
elif [[ $APLICAR -eq 1 ]]; then
  # Sem a listagem não dá para saber se o ruleset já existe: criar às cegas o duplicaria.
  echo "[aplicar] 7. ABORTADO: não consegui listar os rulesets (repo privado sem rulesets, ou sem"
  echo "          permissão de admin). Nada foi criado para não duplicar o '$NOME_RULESET'."
  echo "$((FALHAS + 1)) passo(s) falharam (veja acima)."
  exit 1
else
  echo "[dry-run] (não consegui listar os rulesets agora; no --aplicar o passo 7 aborta se a listagem falhar)"
fi
if [[ -n "$id_ruleset" ]]; then
  executar "7. atualizar o ruleset '$NOME_RULESET' (id $id_ruleset)" PUT "repos/$REPO/rulesets/$id_ruleset" "$ruleset"
else
  executar "7. criar o ruleset '$NOME_RULESET'" POST "repos/$REPO/rulesets" "$ruleset"
fi

echo
echo "Manual (sem API estável): social preview (Settings > General > Social preview, imagem 1280x640),"
echo "Discussions (Settings > General > Features), convites de colaboradores. Ver docs/operacao-github.md."
if [[ $APLICAR -eq 0 ]]; then
  echo "Nada foi alterado (dry-run). Para aplicar: $0 $REPO --aplicar"
  exit 0
fi
if [[ $FALHAS -gt 0 ]]; then
  echo "$FALHAS passo(s) falharam (veja acima)."
  exit 1
fi
echo "Tudo aplicado."
