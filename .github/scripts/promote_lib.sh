#!/usr/bin/env bash

# Promotion helper library for Bookverse AppTrust workflows.
# This file is sourced by GitHub Actions steps.
#
# Expected environment (set by workflow steps):
# - APPLICATION_KEY: e.g., bookverse-inventory
# - APP_VERSION: SemVer of the application version
# - JFROG_URL: base URL to JFrog platform (https://...)
# - PROJECT_KEY: project key (e.g., bookverse)
# - APPTRUST_ACCESS_TOKEN: OAuth access token (exchanged via OIDC)
# - STAGES_STR: space-separated display stage names (e.g., "DEV QA STAGING PROD")
# - FINAL_STAGE: display name of release stage (usually PROD)
# - ALLOW_RELEASE: "true" to allow release when at FINAL_STAGE
# - RELEASE_INCLUDED_REPO_KEYS: JSON array string of repository keys for release (optional)
#
# Provided functions:
# - display_stage_for <stage>
# - fetch_summary
# - advance_one_step

__bv__trim_base() {
  # Ensure JFROG_URL has no trailing slash
  local base="${JFROG_URL:-}"
  base="${base%/}"
  printf "%s" "$base"
}


__api_stage_for() {
  # Convert display stage (e.g., STAGING) to API stage (project-prefixed when applicable)
  local d="${1:-}"
  local p="${PROJECT_KEY:-}"
  if [[ -z "$d" || "$d" == "UNASSIGNED" ]]; then
    printf "\n"
    return 0
  fi
  if [[ "$d" == "PROD" ]]; then
    printf "%s\n" "PROD"
    return 0
  fi
  # If already prefixed, return as-is
  if [[ -n "$p" && "$d" == "$p-"* ]]; then printf "%s\n" "$d"; return 0; fi
  if [[ -n "$p" ]]; then printf "%s\n" "$p-$d"; else printf "%s\n" "$d"; fi
}

__persist_env() {
  # Persist VAR=VALUE to both current shell and GitHub actions env
  # Usage: __persist_env VAR VALUE
  local k="$1"; shift
  local v="$*"
  export "$k"="$v"
  if [[ -n "${GITHUB_ENV:-}" ]]; then
    printf "%s=%s\n" "$k" "$v" >> "$GITHUB_ENV"
  fi
}

fetch_summary() {
  # Refresh CURRENT_STAGE and RELEASE_STATUS from AppTrust Content API.
  # Falls back to existing env values if API is unavailable.
  local base="$(__bv__trim_base)"
  local app="${APPLICATION_KEY:-}"
  local ver="${APP_VERSION:-}"
  local tok="${APPTRUST_ACCESS_TOKEN:-}"
  local url
  url="$base/apptrust/api/v1/applications/$app/versions/$ver/content"

  # If essentials missing, keep current env and return success.
  if [[ -z "$base" || -z "$app" || -z "$ver" || -z "$tok" ]]; then
    return 0
  fi

  local tmp; tmp="$(mktemp)"
  local code
  code=$(curl -sS -L -o "$tmp" -w "%{http_code}" \
    -H "Authorization: Bearer ${tok}" -H "Accept: application/json" \
    "$url" 2>/dev/null || echo 000)

  if [[ "$code" -ge 200 && "$code" -lt 300 ]]; then
    local curr rel
    curr=$(jq -r '.current_stage // empty' <"$tmp" 2>/dev/null || true)
    rel=$(jq -r '.release_status // empty' <"$tmp" 2>/dev/null || true)
    rm -f "$tmp"
    if [[ -n "$curr" ]]; then __persist_env CURRENT_STAGE "$curr"; fi
    if [[ -n "$rel" ]]; then __persist_env RELEASE_STATUS "$rel"; fi
    return 0
  fi
  rm -f "$tmp" || true
  # Keep existing env on failure
  return 0
}

__compute_next_display_stage() {
  # Determine next display stage from CURRENT_STAGE and STAGES_STR
  local curr_disp stages next=""
  curr_disp="$(display_stage_for "${CURRENT_STAGE:-}")"
  stages=( )
  # shellcheck disable=SC2206
  stages=(${STAGES_STR:-})
  if [[ -z "$curr_disp" || "$curr_disp" == "UNASSIGNED" ]]; then
    next="${stages[0]:-}"
  else
    local i
    for ((i=0; i<${#stages[@]}; i++)); do
      if [[ "${stages[$i]}" == "$curr_disp" ]]; then
        if (( i+1 < ${#stages[@]} )); then next="${stages[$((i+1))]}"; fi
        break
      fi
    done
  fi
  printf "%s\n" "$next"
}

advance_one_step() {
  # Promote to the next stage, or release if ALLOW_RELEASE and at FINAL_STAGE
  fetch_summary || true

  local next_disp; next_disp="$(__compute_next_display_stage)"
  if [[ -z "$next_disp" ]]; then
    # Nothing to do
    return 0
  fi

  local base app ver tok mode
  base="$(__bv__trim_base)"
  app="${APPLICATION_KEY:-}"
  ver="${APP_VERSION:-}"
  tok="${APPTRUST_ACCESS_TOKEN:-}"
  mode="promote"

  if [[ "${ALLOW_RELEASE:-false}" == "true" && "$next_disp" == "${FINAL_STAGE:-}" ]]; then
    mode="release"
  fi

  # Attempt real API calls first; fallback to optimistic local state on failure.
  if [[ -n "$base" && -n "$app" && -n "$ver" && -n "$tok" ]]; then
    if [[ "$mode" == "promote" ]]; then
      # Use the proper promote_to_stage function instead of inline logic
      echo "🚀 Promoting to ${next_disp} via AppTrust"
      if promote_to_stage "$next_disp"; then
        echo "✅ Promotion to ${next_disp} successful"
        return 0
      else
        echo "❌ Promotion to ${next_disp} failed - see above for details" >&2
        return 1
      fi
    else
      # Release mode - use release_version function for proper error handling
      echo "🚀 Releasing to ${next_disp} via AppTrust"
      if release_version; then
        echo "✅ Release to ${next_disp} successful"
        return 0
      else
        echo "❌ Release to ${next_disp} failed - see above for details" >&2
        return 1
      fi
    fi
  else
    echo "❌ Missing required parameters for AppTrust API call" >&2
    echo "   base='$base' app='$app' ver='$ver' tok='${tok:+[SET]}'" >&2
    return 1
  fi
}

#!/usr/bin/env bash
set -euo pipefail

# Promote/Release helper library sourced by the promotion workflow.
#
# Flow overview (how release is triggered):
# - The workflow step "Release to PROD" (in .github/workflows/promote.yml)
#   sets ALLOW_RELEASE=true and calls advance_one_step.
# - advance_one_step() computes the next stage. If that next stage equals
#   FINAL_STAGE (PROD) AND ALLOW_RELEASE=true, it invokes release_version().
# - release_version() performs the AppTrust Release API call:
#     POST /apptrust/api/v1/applications/{application_key}/versions/{version}/release
#   with a JSON payload (promotion_type copy + included_repository_keys)
#   to move the application version to the global release stage (PROD).
# - For non-final stages, advance_one_step() calls promote_to_stage() instead.

# Minimal debug printer
print_request_info() {
  local method="$1"; local url="$2"; local body="${3:-}"
  echo "---- HTTP Request ----"
  echo "Method: ${method}"
  echo "URL: ${url}"
  echo "Headers: Authorization: Bearer ***REDACTED***, Accept: application/json"
  if [[ "$method" == "POST" && -n "$body" ]]; then
    echo "Body: ${body}"
  fi
  echo "---------------------"
}

# Translate a display stage name (e.g., DEV) to the API stage identifier:
# - Non-PROD stages must be project-prefixed for API calls (bookverse-DEV, etc.)
# - PROD remains the global release stage (no prefix)
api_stage_for() {
  local s="${1:-}"
  if [[ "$s" == "PROD" ]]; then
    echo "PROD"
  elif [[ "$s" == "${PROJECT_KEY:-}-"* ]]; then
    echo "$s"
  else
    echo "${PROJECT_KEY:-}-$s"
  fi
}

# Translate an API stage identifier to a display name used internally:
# - bookverse-DEV → DEV, bookverse-STAGING → STAGING
# - PROD remains PROD
display_stage_for() {
  local s="${1:-}"
  if [[ "$s" == "PROD" || "$s" == "${PROJECT_KEY:-}-PROD" ]]; then
    echo "PROD"
  elif [[ "$s" == "${PROJECT_KEY:-}-"* ]]; then
    echo "${s#${PROJECT_KEY:-}-}"
  else
    echo "$s"
  fi
}

# Query the AppTrust Version Summary to determine current stage and release status.
# On success, exports CURRENT_STAGE and RELEASE_STATUS to the environment, with
# CURRENT_STAGE in API form (e.g., bookverse-STAGING, PROD). Callers should wrap
# it with display_stage_for when comparing against human readable names.
fetch_summary() {
  local body url code
  body=$(mktemp)
  url="${JFROG_URL}/apptrust/api/v1/applications/${APPLICATION_KEY}/versions/${APP_VERSION}/content"
  code=$(curl -sS -L -o "$body" -w "%{http_code}" \
    -H "Authorization: Bearer ${APPTRUST_ACCESS_TOKEN}" \
    -H "Accept: application/json" \
    "$url" || echo 000)
  if [[ "$code" -ge 200 && "$code" -lt 300 ]] && jq -e . >/dev/null 2>&1 < "$body"; then
    CURRENT_STAGE=$(jq -r '.current_stage // empty' "$body" 2>/dev/null || echo "")
    RELEASE_STATUS=$(jq -r '.release_status // empty' "$body" 2>/dev/null || echo "")
  else
    echo "❌ Failed to fetch version summary" >&2
    print_request_info "GET" "$url"
    cat "$body" || true
    rm -f "$body"
    return 1
  fi
  rm -f "$body"
  echo "CURRENT_STAGE=${CURRENT_STAGE:-}" >> "$GITHUB_ENV"
  echo "RELEASE_STATUS=${RELEASE_STATUS:-}" >> "$GITHUB_ENV"
  echo "🔎 Current stage: $(display_stage_for "${CURRENT_STAGE:-UNASSIGNED}") (release_status=${RELEASE_STATUS:-unknown})"
}

# Small helper to POST JSON to AppTrust endpoints, capturing HTTP status and body.
# NOTE: Callers are responsible for printing request context (via print_request_info)
# upon errors and for interpreting success/failure semantics.
apptrust_post() {
  local path="${1:-}"; local data="${2:-}"; local out_file="${3:-}"
  local url="${JFROG_URL}${path}"
  local code
  code=$(curl -sS -L -X POST -o "$out_file" -w "%{http_code}" \
    -H "Authorization: Bearer ${APPTRUST_ACCESS_TOKEN}" \
    -H "Content-Type: application/json" \
    -H "Accept: application/json" \
    -d "$data" "$url" || echo 000)
  if [[ "$code" -ge 200 && "$code" -lt 300 ]]; then
    return 0
  else
    return 1
  fi
}

# Call the AppTrust Promote API to move the version to a non-final stage
promote_to_stage() {
  local target_stage_display="${1:-}"
  local resp_body
  resp_body=$(mktemp)
  local api_stage
  api_stage=$(api_stage_for "$target_stage_display")
  echo "🚀 Promoting to ${target_stage_display} via AppTrust"
  if apptrust_post \
    "/apptrust/api/v1/applications/${APPLICATION_KEY}/versions/${APP_VERSION}/promote?async=false" \
    "{\"target_stage\": \"${api_stage}\", \"promotion_type\": \"move\"}" \
    "$resp_body"; then
    echo "HTTP OK"; cat "$resp_body" || true; echo
  else
    echo "❌ Promotion to ${target_stage_display} failed" >&2
    print_request_info "POST" "${JFROG_URL}/apptrust/api/v1/applications/${APPLICATION_KEY}/versions/${APP_VERSION}/promote?async=false" "{\"target_stage\": \"${api_stage}\", \"promotion_type\": \"move\"}"
    cat "$resp_body" || true; echo
    rm -f "$resp_body"
    return 1
  fi
  rm -f "$resp_body"
  PROMOTED_STAGES="${PROMOTED_STAGES:-}${PROMOTED_STAGES:+ }${target_stage_display}"
  echo "PROMOTED_STAGES=${PROMOTED_STAGES}" >> "$GITHUB_ENV"
  fetch_summary
}

# Call the AppTrust Release API to move the version to the final release stage (PROD)
# NOTE: This function is NOT called directly by the workflow. The workflow
#       sets ALLOW_RELEASE=true and calls advance_one_step(); only when the
#       computed next stage equals FINAL_STAGE (PROD) will advance_one_step()
#       invoke release_version(). See advance_one_step() below.
# Call the AppTrust Release API to move the version to the final release stage (PROD)
#
# Payload selection rules (included_repository_keys):
# - If RELEASE_INCLUDED_REPO_KEYS is provided (JSON array), it is used verbatim.
# - Otherwise, infer repository keys from APPLICATION_KEY and PROJECT_KEY.
#   These should point to release-local repositories attached to PROD.
release_version() {
  local resp_body
  resp_body=$(mktemp)
  echo "🚀 Releasing to ${FINAL_STAGE} via AppTrust Release API"
  # Build included repositories list if provided or infer from APPLICATION_KEY and PROJECT_KEY
  local payload
  if [[ -n "${RELEASE_INCLUDED_REPO_KEYS:-}" ]]; then
    payload=$(printf '{"promotion_type":"move","included_repository_keys":%s}' "${RELEASE_INCLUDED_REPO_KEYS}")
  else
    # Derive service name from application key: bookverse-<service>
    local service_name
    service_name="${APPLICATION_KEY#${PROJECT_KEY}-}"
    local repo_docker repo_python
    # Use exact internal release repositories for final PROD release
    repo_docker="${PROJECT_KEY}-${service_name}-internal-docker-release-local"
    repo_python="${PROJECT_KEY}-${service_name}-internal-python-release-local"
    payload=$(printf '{"promotion_type":"move","included_repository_keys":["%s","%s"]}' "$repo_docker" "$repo_python")
  fi
  if apptrust_post \
    "/apptrust/api/v1/applications/${APPLICATION_KEY}/versions/${APP_VERSION}/release?async=false" \
    "$payload" \
    "$resp_body"; then
    echo "HTTP OK"; cat "$resp_body" || true; echo
  else
    echo "❌ Release to ${FINAL_STAGE} failed" >&2
    print_request_info "POST" "${JFROG_URL}/apptrust/api/v1/applications/${APPLICATION_KEY}/versions/${APP_VERSION}/release?async=false" "{\"promotion_type\":\"move\"}"
    rm -f "$resp_body"
    return 1
  fi
  rm -f "$resp_body"
  DID_RELEASE=true
  echo "DID_RELEASE=${DID_RELEASE}" >> "$GITHUB_ENV"
  PROMOTED_STAGES="${PROMOTED_STAGES:-}${PROMOTED_STAGES:+ }${FINAL_STAGE}"
  echo "PROMOTED_STAGES=${PROMOTED_STAGES}" >> "$GITHUB_ENV"
  fetch_summary
}

emit_json() {
  local out_file="${1:-}"; shift
  local content="$*"
  printf "%b\n" "$content" > "$out_file"
}

evd_create() {
  local predicate_file="${1:-}"; local predicate_type="${2:-}"; local markdown_file="${3:-}"
  local md_args=()
  if [[ -n "$markdown_file" ]]; then md_args+=(--markdown "$markdown_file"); fi
  jf evd create-evidence \
    --predicate "$predicate_file" \
    "${md_args[@]}" \
    --predicate-type "$predicate_type" \
    --release-bundle "$APPLICATION_KEY" \
    --release-bundle-version "$APP_VERSION" \
    --project "${PROJECT_KEY}" \
    --provider-id github-actions \
    --key "${EVIDENCE_PRIVATE_KEY:-}" \
    --key-alias "${EVIDENCE_KEY_ALIAS:-${EVIDENCE_KEY_ALIAS_VAR:-}}" || true
}

attach_evidence_qa() {
  local now_ts scan_id med coll pass
  now_ts=$(date -u +%Y-%m-%dT%H:%M:%SZ)
  scan_id=$(cat /proc/sys/kernel/random/uuid)
  med=$((2 + RANDOM % 5))
  emit_json dast-qa.json "{\n    \"environment\": \"QA\",\n    \"scanId\": \"${scan_id}\",\n    \"status\": \"PASSED\",\n    \"findings\": { \"critical\": 0, \"high\": 0, \"medium\": ${med} },\n    \"attachStage\": \"QA\", \"gateForPromotionTo\": \"STAGING\",\n    \"timestamp\": \"${now_ts}\"\n  }"
  printf "# dast-scan\n" > dast-scan.md
  evd_create dast-qa.json "https://invicti.com/evidence/dast/v3" dast-scan.md
  coll=$(cat /proc/sys/kernel/random/uuid)
  pass=$((100 + RANDOM % 31))
  emit_json postman-qa.json "{\n    \"environment\": \"QA\",\n    \"collectionId\": \"${coll}\",\n    \"status\": \"PASSED\",\n    \"assertionsPassed\": ${pass},\n    \"assertionsFailed\": 0,\n    \"attachStage\": \"QA\", \"gateForPromotionTo\": \"STAGING\",\n    \"timestamp\": \"${now_ts}\"\n  }"
  printf "# api-tests\n" > api-tests.md
  evd_create postman-qa.json "https://postman.com/evidence/collection/v2.2" api-tests.md
}

attach_evidence_staging() {
  local now_ts med_iac low_iac pent tid
  now_ts=$(date -u +%Y-%m-%dT%H:%M:%SZ)
  med_iac=$((1 + RANDOM % 3)); low_iac=$((8 + RANDOM % 7))
  # Disabled: staging gate evidence is attached explicitly in workflow to avoid duplicates
  :
  pent=$(cat /proc/sys/kernel/random/uuid)
  # Disabled duplicate pentest evidence; handled by workflow
  :
  tid=$((3000000 + RANDOM % 1000000))
  # Disabled duplicate ServiceNow approval; handled by workflow
  :
}

attach_evidence_prod() {
  local now_ts rev short
  now_ts=$(date -u +%Y-%m-%dT%H:%M:%SZ)
  rev="${GITHUB_SHA:-${GITHUB_SHA:-}}"; short=${rev:0:8}
  emit_json argocd-prod.json "{ \"tool\": \"ArgoCD\", \"status\": \"Synced\", \"revision\": \"${short}\", \"deployedAt\": \"${now_ts}\", \"attachStage\": \"PROD\" }"
  printf "# argocd-deploy\n" > argocd-deploy.md
  # Use a shortened predicate-type to ensure type slug < 16 chars
  evd_create argocd-prod.json "https://argo.cd/ev/deploy/v1" argocd-deploy.md
}

attach_evidence_for() {
  local stage_name="${1:-}"
  case "$stage_name" in
    UNASSIGNED)
      echo "ℹ️ No evidence for UNASSIGNED" ;;
    DEV)
      echo "ℹ️ No evidence configured for DEV in demo" ;;
    QA)
      attach_evidence_qa ;;
    STAGING)
      attach_evidence_staging ;;
    PROD)
      attach_evidence_prod ;;
    *)
      echo "ℹ️ No evidence rule for stage '$stage_name'" ;;
  esac
}



