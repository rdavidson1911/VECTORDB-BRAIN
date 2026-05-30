#!/usr/bin/env bash
# ----------------------------------------------------------------------------
# scan-vectordb-staging.sh
#
# Pre-push leak scanner for VECTORDB-BRAIN (or any repo).
# Scans files for:
#   1. HIGH-severity patterns: real secrets (API keys, private keys, tokens,
#      connection strings with credentials)
#   2. MED-severity patterns: PII, personal paths, suspicious comments, former
#      employer names, non-localhost IPs
#   3. Risky filenames: *.pem, id_rsa, .env, *.har, *.log, *.kdbx, etc.
#   4. (Optional) Diff between staged files and a manifest — flags files that
#      are staged but NOT in your approved manifest.
#
# Designed for Git Bash on Windows, WSL, or Linux. Uses POSIX-ish bash + GNU
# grep (-E) features. No external deps beyond git and grep.
#
# Usage:
#   bash scan-vectordb-staging.sh                                # scan staged files
#   bash scan-vectordb-staging.sh --manifest path/to/manifest.md # scan files listed in a manifest
#   bash scan-vectordb-staging.sh --files f1 f2 ...              # scan explicit files
#   bash scan-vectordb-staging.sh --all                          # scan every tracked file
#   bash scan-vectordb-staging.sh --diff-manifest path/to/manifest.md
#                                                                # also flag staged-but-not-on-manifest
#
# Exit codes:
#   0  clean
#   1  one or more HIGH findings (do not commit)
#   2  only MED findings (review before committing)
#   3  usage error
#
# Extend it: add patterns to PATTERNS_HIGH / PATTERNS_MED arrays below.
# Add allow-listed values to ALLOWLIST_RE.
# ----------------------------------------------------------------------------

set -uo pipefail

# ----------------------------------------------------------------------------
# CONFIGURATION — edit these to taste
# ----------------------------------------------------------------------------

# Values that are already public (on your resume, GitHub profile, etc.) — these
# are ignored when matched alongside MED-severity PII patterns.
ALLOWLIST_RE='(rdavidson1911@gmail\.com|414-316-1249|Cross Plains, WI|Robert Davidson)'

# HIGH-severity patterns. Format: "LABEL|||REGEX"
# These represent things that are almost certainly a real secret if matched.
PATTERNS_HIGH=(
  "AWS access key|||AKIA[0-9A-Z]{16}"
  "AWS secret key (likely)|||aws_secret_access_key[[:space:]]*=[[:space:]]*[A-Za-z0-9/+=]{30,}"
  "OpenAI key|||sk-[A-Za-z0-9]{32,}"
  "Anthropic key|||sk-ant-[A-Za-z0-9_-]{40,}"
  "GitHub personal access token|||gh[pousr]_[A-Za-z0-9]{36}"
  "GitHub fine-grained PAT|||github_pat_[A-Za-z0-9_]{20,}"
  "Slack token|||xox[baprs]-[A-Za-z0-9-]{10,}"
  "Slack webhook|||https://hooks\.slack\.com/services/T[A-Za-z0-9/]+"
  "Stripe live key|||sk_live_[A-Za-z0-9]{20,}"
  "Stripe restricted key|||rk_live_[A-Za-z0-9]{20,}"
  "Google API key|||AIza[0-9A-Za-z_-]{35}"
  "JWT (looks signed)|||eyJ[A-Za-z0-9_-]+\.eyJ[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+"
  "PEM private key block|||-----BEGIN [A-Z ]*PRIVATE KEY-----"
  "OpenSSH private key block|||-----BEGIN OPENSSH PRIVATE KEY-----"
  "DB connection string w/ credentials|||(mongodb|postgres|postgresql|mysql|redis)://[^[:space:]:/]+:[^[:space:]@]+@"
  "Hardcoded password assignment|||(password|passwd|pwd)[[:space:]]*[:=][[:space:]]*[\"'\''][^\"'\''\$<{][^\"'\'']{4,}[\"'\'']"
  "Bearer token (long)|||[Bb]earer[[:space:]]+[A-Za-z0-9_.\-]{30,}"
)

# MED-severity patterns. Worth a human look but not automatic blockers.
PATTERNS_MED=(
  "Personal Windows path|||[Cc]:\\\\[Uu]sers\\\\rdavi"
  "Personal Unix-style home path|||/home/(rdavidson|rdavi|robert)/"
  "Personal macOS path|||/Users/(rdavidson|rdavi|robert)/"
  "Email address|||[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}"
  "US phone (XXX-XXX-XXXX or (XXX) XXX-XXXX)|||(\\([0-9]{3}\\)[[:space:]]?|[0-9]{3}[-.])[0-9]{3}[-.][0-9]{4}"
  "Non-loopback IPv4|||(^|[^0-9])(10|172|192|169)\.[0-9]{1,3}\.[0-9]{1,3}\.[0-9]{1,3}"
  "Former employer — Engendren|||[Ee]ngendren"
  "Former employer — RathGibson|||[Rr]ath[Gg]ibson"
  "Former employer — AAA Sales|||AAA Sales"
  "Former employer — HK Logistics|||HK Logistics"
  "Former employer — Virchow Krause|||[Vv]irchow.{0,3}[Kk]rause"
  "Former employer — Lutheran Social Services|||Lutheran Social Services"
  "Suspicious leak-y comment|||(TODO|FIXME|XXX|HACK).*(remove|delete|leak|secret|password|token|key|before publish)"
  "Hardcoded localhost with port (informational)|||(127\.0\.0\.1|localhost):[0-9]{2,5}"
)

# Filenames that should NEVER be in a public repo.
FILENAME_RED_FLAGS=(
  "*.pem"
  "*.key"
  "*.p12"
  "*.pfx"
  "*.kdbx"
  "*.netrc"
  ".netrc"
  "id_rsa"
  "id_dsa"
  "id_ecdsa"
  "id_ed25519"
  "*.ovpn"
  "wallet.dat"
  "secrets.*"
  "credentials.*"
  "*.har"
  "*.log"
)

# Files where MED-severity matches are expected and should NOT count toward
# the final exit status (we still print them, just don't fail on them).
EXPECTED_MED_FILES_RE='(^|/)(README\.md|PROJECT-CHARTER\.md|pyproject\.toml|package\.json|web/package\.json|\.env\.example)$'

# ----------------------------------------------------------------------------
# INTERNAL — usually no need to edit below
# ----------------------------------------------------------------------------

RED=$'\033[31m'
YELLOW=$'\033[33m'
GREEN=$'\033[32m'
DIM=$'\033[2m'
BOLD=$'\033[1m'
RESET=$'\033[0m'

usage() {
  sed -n '2,40p' "$0" | sed 's/^# \{0,1\}//'
  exit 3
}

extract_manifest_paths() {
  # Extract lines from ```text fenced code blocks in a markdown manifest.
  local file="$1"
  awk '
    /^```text[[:space:]]*$/ { flag=1; next }
    /^```[[:space:]]*$/      { flag=0; next }
    flag && NF                { print }
  ' "$file"
}

collect_staged() {
  git diff --cached --name-only --diff-filter=ACM 2>/dev/null
}

collect_all_tracked() {
  git ls-files 2>/dev/null
}

is_binary() {
  # Treat as binary if `file -b --mime` says it's not text.
  if command -v file >/dev/null 2>&1; then
    case "$(file -b --mime "$1" 2>/dev/null)" in
      text/*|*xml*|*json*|*javascript*) return 1 ;;
      *) return 0 ;;
    esac
  fi
  return 1
}

scan_filename_flags() {
  local f="$1"
  for pat in "${FILENAME_RED_FLAGS[@]}"; do
    # Don't flag legitimate .env.example
    [[ "$pat" == ".env" && "$(basename "$f")" == ".env.example" ]] && continue
    case "$(basename "$f")" in
      $pat)
        printf "%sHIGH%s [filename] %s — matches risky pattern %s\n" \
          "$RED$BOLD" "$RESET" "$f" "$pat"
        return 0
        ;;
    esac
  done
  return 1
}

scan_file_contents() {
  local f="$1"
  local sev="$2"
  local -n patterns="$3"
  local found_any=1

  for entry in "${patterns[@]}"; do
    local label="${entry%%|||*}"
    local re="${entry##*|||}"
    # Find matches, skipping the allow-list.
    local hits
    hits=$(grep -nIE "$re" "$f" 2>/dev/null \
           | grep -vE "$ALLOWLIST_RE" || true)
    if [[ -n "$hits" ]]; then
      found_any=0
      while IFS= read -r line; do
        local lineno="${line%%:*}"
        local snippet="${line#*:}"
        snippet="${snippet#*:}"
        # Trim snippet for readability
        if [[ ${#snippet} -gt 140 ]]; then
          snippet="${snippet:0:137}..."
        fi
        if [[ "$sev" == "HIGH" ]]; then
          printf "%sHIGH%s %s:%s — %s%s%s\n  %s%s%s\n" \
            "$RED$BOLD" "$RESET" "$f" "$lineno" \
            "$BOLD" "$label" "$RESET" \
            "$DIM" "$snippet" "$RESET"
        else
          printf "%sMED%s  %s:%s — %s%s%s\n  %s%s%s\n" \
            "$YELLOW$BOLD" "$RESET" "$f" "$lineno" \
            "$BOLD" "$label" "$RESET" \
            "$DIM" "$snippet" "$RESET"
        fi
      done <<< "$hits"
    fi
  done
  return $found_any
}

diff_manifest_vs_staged() {
  local manifest_file="$1"
  local manifest_paths staged_paths
  manifest_paths=$(extract_manifest_paths "$manifest_file" | sort -u)
  staged_paths=$(collect_staged | sort -u)

  echo
  echo "${BOLD}Manifest diff (staged but not on approved manifest):${RESET}"
  local extras
  extras=$(comm -23 <(echo "$staged_paths") <(echo "$manifest_paths"))
  if [[ -z "$extras" ]]; then
    printf "  %sNone.%s\n" "$GREEN" "$RESET"
  else
    while IFS= read -r path; do
      printf "  %s+ %s%s\n" "$YELLOW" "$path" "$RESET"
    done <<< "$extras"
  fi

  echo
  echo "${BOLD}Manifest paths NOT staged (not yet added):${RESET}"
  local missing
  missing=$(comm -13 <(echo "$staged_paths") <(echo "$manifest_paths"))
  if [[ -z "$missing" ]]; then
    printf "  %sAll manifest paths are staged.%s\n" "$GREEN" "$RESET"
  else
    while IFS= read -r path; do
      printf "  %s- %s%s\n" "$DIM" "$path" "$RESET"
    done <<< "$missing"
  fi
}

# ----------------------------------------------------------------------------
# Argument parsing
# ----------------------------------------------------------------------------

MODE="staged"
MANIFEST=""
EXPLICIT_FILES=()
DIFF_MANIFEST=""

while [[ $# -gt 0 ]]; do
  case "$1" in
    -h|--help) usage ;;
    --manifest)
      MODE="manifest"
      MANIFEST="${2:-}"
      [[ -z "$MANIFEST" ]] && { echo "Error: --manifest needs a path"; exit 3; }
      shift 2
      ;;
    --files)
      MODE="explicit"
      shift
      while [[ $# -gt 0 && "$1" != --* ]]; do
        EXPLICIT_FILES+=("$1")
        shift
      done
      ;;
    --all) MODE="all"; shift ;;
    --diff-manifest)
      DIFF_MANIFEST="${2:-}"
      [[ -z "$DIFF_MANIFEST" ]] && { echo "Error: --diff-manifest needs a path"; exit 3; }
      shift 2
      ;;
    *) echo "Unknown arg: $1"; usage ;;
  esac
done

# ----------------------------------------------------------------------------
# Gather targets
# ----------------------------------------------------------------------------

declare -a TARGETS=()
case "$MODE" in
  staged)
    while IFS= read -r f; do
      [[ -n "$f" ]] && TARGETS+=("$f")
    done < <(collect_staged)
    ;;
  all)
    while IFS= read -r f; do
      [[ -n "$f" ]] && TARGETS+=("$f")
    done < <(collect_all_tracked)
    ;;
  manifest)
    [[ ! -f "$MANIFEST" ]] && { echo "Manifest not found: $MANIFEST"; exit 3; }
    while IFS= read -r f; do
      [[ -n "$f" ]] && TARGETS+=("$f")
    done < <(extract_manifest_paths "$MANIFEST")
    ;;
  explicit)
    TARGETS=("${EXPLICIT_FILES[@]}")
    ;;
esac

if [[ ${#TARGETS[@]} -eq 0 ]]; then
  echo "No files to scan in mode: $MODE"
  exit 0
fi

# ----------------------------------------------------------------------------
# Run
# ----------------------------------------------------------------------------

printf "%s== Scanning %d file(s) in mode: %s ==%s\n\n" "$BOLD" "${#TARGETS[@]}" "$MODE" "$RESET"

HIGH_COUNT=0
MED_COUNT=0
MED_BLOCKING_COUNT=0
SCANNED=0
SKIPPED_MISSING=0
SKIPPED_BINARY=0

for f in "${TARGETS[@]}"; do
  if [[ ! -f "$f" ]]; then
    SKIPPED_MISSING=$((SKIPPED_MISSING+1))
    continue
  fi

  # Filename check applies to everything (incl. binaries).
  if scan_filename_flags "$f"; then
    HIGH_COUNT=$((HIGH_COUNT+1))
  fi

  if is_binary "$f"; then
    SKIPPED_BINARY=$((SKIPPED_BINARY+1))
    continue
  fi

  SCANNED=$((SCANNED+1))

  if scan_file_contents "$f" "HIGH" PATTERNS_HIGH; then
    HIGH_COUNT=$((HIGH_COUNT+1))
  fi
  if scan_file_contents "$f" "MED" PATTERNS_MED; then
    MED_COUNT=$((MED_COUNT+1))
    if ! [[ "$f" =~ $EXPECTED_MED_FILES_RE ]]; then
      MED_BLOCKING_COUNT=$((MED_BLOCKING_COUNT+1))
    fi
  fi
done

# Optional manifest diff
if [[ -n "$DIFF_MANIFEST" ]]; then
  diff_manifest_vs_staged "$DIFF_MANIFEST"
fi

# ----------------------------------------------------------------------------
# Summary + exit code
# ----------------------------------------------------------------------------

echo
printf "%s== Summary ==%s\n" "$BOLD" "$RESET"
printf "  scanned (text):   %d\n" "$SCANNED"
printf "  skipped (binary): %d\n" "$SKIPPED_BINARY"
printf "  skipped (missing):%d\n" "$SKIPPED_MISSING"
printf "  HIGH findings:    %s%d%s\n" "$([[ $HIGH_COUNT -gt 0 ]] && echo "$RED$BOLD" || echo "$GREEN")" "$HIGH_COUNT" "$RESET"
printf "  MED findings:     %s%d%s  (of which %d are in unexpected files)\n" "$([[ $MED_COUNT -gt 0 ]] && echo "$YELLOW" || echo "$GREEN")" "$MED_COUNT" "$RESET" "$MED_BLOCKING_COUNT"

echo
if [[ $HIGH_COUNT -gt 0 ]]; then
  printf "%sDO NOT COMMIT.%s Fix HIGH findings before pushing.\n" "$RED$BOLD" "$RESET"
  exit 1
elif [[ $MED_BLOCKING_COUNT -gt 0 ]]; then
  printf "%sReview MED findings%s in unexpected files before pushing.\n" "$YELLOW$BOLD" "$RESET"
  exit 2
else
  printf "%sClean. Safe to commit.%s\n" "$GREEN$BOLD" "$RESET"
  exit 0
fi
