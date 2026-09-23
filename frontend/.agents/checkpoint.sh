#!/usr/bin/env bash
# ---------------------------------------------------------------------------
# Sahaay Setu — agent checkpoint CLI
#
# Chat history is not project state. When a session ends, crashes, or runs out
# of context, the next agent must not rebuild context by re-reading a
# conversation. It loads the latest checkpoint, reconciles it against actual git
# state, and resumes from `next_action`.
#
# Two layers, deliberately:
#   .checkpoints/   session-by-session working state — append-only history
#   context/        durable project truth — what the project IS, slow-changing
#
# See .agents/PROTOCOL.md §3–§4.
# ---------------------------------------------------------------------------
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
CHECKPOINT_DIR="$REPO_ROOT/.checkpoints"
LATEST_FILE="$CHECKPOINT_DIR/_latest.json"
PROJECT="sahaay-setu"

command -v jq >/dev/null 2>&1 || { echo "Error: jq is required (brew install jq)"; exit 1; }

usage() {
  cat <<'EOF'
Usage: bash .agents/checkpoint.sh <command> [options]

Commands:
  resume   Print the latest checkpoint + actual git state, ready to resume from
  save     Save a new checkpoint
  verify   Run npm run verify and record the result into a checkpoint
  list     List checkpoints, newest first
  show     Print a checkpoint (defaults to latest)
  diff     Compare the latest checkpoint against actual git state
  prune    Keep only the N most recent checkpoints (default 10)

Options for 'save':
  --agent <name>      claude-code | cursor | copilot | human      [required]
  --task <desc>       What you were working on                    [required]
  --status <s>        in_progress | blocked | completed           [default: in_progress]
  --next <desc>       Exactly what to do next
  --next-file <path>  File the next action targets
  --notes <text>      Free-form context for the next session
  --plan <a;b;c>      Semicolon-separated plan steps
  --done <a;b;c>      Semicolon-separated completed steps
  --verified <f=p;…>  Semicolon-separated fact=proof pairs

Examples:
  bash .agents/checkpoint.sh resume
  bash .agents/checkpoint.sh save --agent claude-code \
    --task "Wire the partner locator to the real backend" \
    --done "Swapped service to HTTP;Handled fallbackUsed banner" \
    --verified "Bundle builds=npx expo export --platform android" \
    --next "Add retry on 429" --next-file src/api/client.ts
EOF
  exit 1
}

mkdir -p "$CHECKPOINT_DIR"

# Split "a;b;c" into a JSON array of strings.
split_json_array() {
  local raw="${1:-}"
  [[ -z "$raw" ]] && { echo "[]"; return; }
  printf '%s' "$raw" | jq -R 'split(";") | map(select(length > 0) | ltrimstr(" "))'
}

# Split "fact=proof;fact=proof" into [{fact, proof, verified_at}]
split_verified_array() {
  local raw="${1:-}" now="$2"
  [[ -z "$raw" ]] && { echo "[]"; return; }
  printf '%s' "$raw" | jq -R --arg now "$now" '
    split(";")
    | map(select(length > 0) | ltrimstr(" "))
    | map(
        (index("=") // -1) as $i
        | if $i < 0
          then { fact: ., proof: "NO PROOF GIVEN — see PROTOCOL.md §3", verified_at: $now }
          else { fact: .[0:$i], proof: .[$i+1:], verified_at: $now }
          end
      )'
}

cmd_save() {
  local agent="" task="" status="in_progress"
  local next_desc="" next_file="" notes="" plan="" done_steps="" verified=""

  while [[ $# -gt 0 ]]; do
    case "$1" in
      --agent)     agent="$2"; shift 2 ;;
      --task)      task="$2"; shift 2 ;;
      --status)    status="$2"; shift 2 ;;
      --next)      next_desc="$2"; shift 2 ;;
      --next-file) next_file="$2"; shift 2 ;;
      --notes)     notes="$2"; shift 2 ;;
      --plan)      plan="$2"; shift 2 ;;
      --done)      done_steps="$2"; shift 2 ;;
      --verified)  verified="$2"; shift 2 ;;
      *) shift ;;
    esac
  done

  [[ -z "$agent" ]] && { echo "Error: --agent is required"; exit 1; }
  [[ -z "$task"  ]] && { echo "Error: --task is required";  exit 1; }

  local timestamp now short_hash chk_id filename
  timestamp="$(date -u +%Y%m%dT%H%M%S)"
  now="$(date -u +%Y-%m-%dT%H:%M:%SZ)"
  short_hash="$(head -c 8 /dev/urandom | xxd -p | head -c 6)"
  chk_id="chk_${timestamp}_${agent}_${short_hash}"
  filename="${PROJECT}_${timestamp}_${agent}.json"

  local git_branch="unknown" git_commit="unknown" git_msg="" diff_stat=""
  local has_uncommitted="false" files_json="[]"

  if [[ -d "$REPO_ROOT/.git" ]]; then
    git_branch="$(git -C "$REPO_ROOT" branch --show-current 2>/dev/null || echo unknown)"
    git_commit="$(git -C "$REPO_ROOT" rev-parse HEAD 2>/dev/null || echo unknown)"
    git_msg="$(git -C "$REPO_ROOT" log -1 --format='%s' 2>/dev/null || echo '')"
    diff_stat="$(git -C "$REPO_ROOT" diff --stat 2>/dev/null || echo '')"
    [[ -n "$(git -C "$REPO_ROOT" status --porcelain 2>/dev/null)" ]] && has_uncommitted="true"
    if [[ "$has_uncommitted" == "true" ]]; then
      files_json="$(git -C "$REPO_ROOT" status --porcelain 2>/dev/null \
        | sed 's/^...//' | jq -R . | jq -s . 2>/dev/null || echo '[]')"
    fi
  fi

  jq -n \
    --arg id "$chk_id" \
    --arg created "$now" \
    --arg agent "$agent" \
    --arg project "$PROJECT" \
    --arg task "$task" \
    --arg status "$status" \
    --argjson plan "$(split_json_array "$plan")" \
    --argjson completed "$(split_json_array "$done_steps")" \
    --argjson verified "$(split_verified_array "$verified" "$now")" \
    --arg branch "$git_branch" \
    --arg commit "$git_commit" \
    --arg commit_msg "$git_msg" \
    --argjson files "$files_json" \
    --argjson uncommitted "$has_uncommitted" \
    --arg diff_summary "$diff_stat" \
    --arg next_desc "$next_desc" \
    --arg next_file "$next_file" \
    --arg notes "$notes" \
    '{
      schema_version: 1,
      id: $id,
      created_at: $created,
      agent: $agent,
      project: $project,
      task: { description: $task, plan: $plan, status: $status },
      progress: {
        completed: ($completed | map({ step: ., verified: false, proof: "" })),
        in_progress: [],
        pending: []
      },
      verified_facts: $verified,
      workspace: {
        git_branch: $branch,
        git_commit: $commit,
        git_commit_message: $commit_msg,
        files_changed: $files,
        has_uncommitted: $uncommitted,
        diff_summary: $diff_summary
      },
      tool_results: [],
      next_action: { description: $next_desc, target_file: $next_file, context: "" },
      context_notes: $notes
    }' > "$CHECKPOINT_DIR/$filename"

  jq -n --arg latest "$filename" --arg by "$agent" --arg at "$now" \
    '{ latest: $latest, by: $by, at: $at }' > "$LATEST_FILE"

  echo "Checkpoint saved: $filename"
  echo
  echo "Reminder: if this completed something durable, also update context/state.json"
  echo "(done / next / verified) — checkpoints are session history, context/ is project truth."
}

cmd_verify() {
  local agent="${1:-unknown}"
  echo "Running npm run verify…"
  local output exit_code=0
  output="$(cd "$REPO_ROOT" && npm run verify 2>&1)" || exit_code=$?

  echo "$output" | tail -20
  echo
  if [[ $exit_code -eq 0 ]]; then
    echo "PASS — recording checkpoint"
    cmd_save --agent "$agent" --task "Verification run" --status completed \
      --verified "npm run verify passes=typecheck + lint + i18n coverage all clean"
  else
    echo "FAIL (exit $exit_code) — recording as blocked"
    cmd_save --agent "$agent" --task "Verification run" --status blocked \
      --notes "npm run verify failed. Fix before claiming anything works."
    exit $exit_code
  fi
}

cmd_resume() {
  echo "=== RESUME CONTEXT — $PROJECT ==="
  echo

  if [[ ! -f "$LATEST_FILE" ]]; then
    cat <<'EOF'
No checkpoint found. This is a fresh start.

Bootstrap by reading, in order:
  1. context/context.json           what the project is, ownership, conventions
  2. context/state.json             where the build stands, with proofs
  3. context/problem-statement.json the brief, mapped to code
  4. context/domain.json            channel-finance glossary and rules
  5. context/decisions.json         ADR log — why things are the way they are
  6. .agents/PROTOCOL.md            this working protocol

Then: git log -10 --oneline
EOF
    exit 0
  fi

  local latest chk_path
  latest="$(jq -r '.latest' "$LATEST_FILE")"
  chk_path="$CHECKPOINT_DIR/$latest"
  [[ -f "$chk_path" ]] || { echo "Error: checkpoint $latest is missing"; exit 1; }

  echo "--- Latest checkpoint: $latest ---"
  jq '.' "$chk_path"
  echo

  if [[ -d "$REPO_ROOT/.git" ]]; then
    echo "--- Actual git state ---"
    echo "Branch: $(git -C "$REPO_ROOT" branch --show-current 2>/dev/null)"
    echo "HEAD:   $(git -C "$REPO_ROOT" log -1 --oneline 2>/dev/null)"
    echo
    echo "Working tree:"
    git -C "$REPO_ROOT" status --short 2>/dev/null || echo "  (clean)"
    echo
    echo "Recent commits:"
    git -C "$REPO_ROOT" log -5 --oneline 2>/dev/null
    echo
  fi

  echo "--- Reconciliation ---"
  cmd_diff | tail -n +2
  echo
  echo "--- Durable project state ---"
  if [[ -f "$REPO_ROOT/context/state.json" ]]; then
    echo "context/state.json — milestone: $(jq -r '.milestone' "$REPO_ROOT/context/state.json")"
    echo "  last updated $(jq -r '.updatedAt' "$REPO_ROOT/context/state.json") by $(jq -r '.updatedBy' "$REPO_ROOT/context/state.json")"
    echo "  next up:"
    jq -r '.next[] | "    [\(.id)] \(.task) — owner: \(.owner)"' "$REPO_ROOT/context/state.json"
  fi
  echo
  echo "=== END RESUME CONTEXT ==="
  echo
  echo "Now announce: \"Resuming from {id}. Last: {task}. Next: {next_action}.\""
}

cmd_list() {
  echo "Checkpoints (newest first):"
  echo
  ls -1t "$CHECKPOINT_DIR"/*.json 2>/dev/null | grep -v '_latest.json' | while read -r f; do
    printf "  %-46s  %-12s  %-14s  %s\n" \
      "$(basename "$f")" \
      "$(jq -r '.agent // "?"' "$f")" \
      "[$(jq -r '.task.status // "?"' "$f")]" \
      "$(jq -r '.task.description // "?"' "$f")"
  done
}

cmd_show() {
  local id=""
  while [[ $# -gt 0 ]]; do
    case "$1" in
      --id) id="$2"; shift 2 ;;
      *) shift ;;
    esac
  done
  if [[ -z "$id" ]]; then
    [[ -f "$LATEST_FILE" ]] || { echo "No checkpoints yet"; exit 1; }
    id="$(jq -r '.latest' "$LATEST_FILE")"
  fi
  [[ -f "$CHECKPOINT_DIR/$id" ]] || { echo "Not found: $id"; exit 1; }
  jq '.' "$CHECKPOINT_DIR/$id"
}

cmd_diff() {
  [[ -f "$LATEST_FILE" ]] || { echo "No checkpoint to diff against"; exit 1; }

  local latest chk_path chk_commit chk_branch
  latest="$(jq -r '.latest' "$LATEST_FILE")"
  chk_path="$CHECKPOINT_DIR/$latest"
  [[ -f "$chk_path" ]] || { echo "Checkpoint file missing: $latest"; exit 1; }

  chk_commit="$(jq -r '.workspace.git_commit' "$chk_path")"
  chk_branch="$(jq -r '.workspace.git_branch' "$chk_path")"

  echo "Checkpoint $(basename "$chk_path"): $chk_branch @ ${chk_commit:0:8}"

  [[ -d "$REPO_ROOT/.git" ]] || { echo "No git repo here"; return; }

  local actual_commit actual_branch uncommitted
  actual_commit="$(git -C "$REPO_ROOT" rev-parse HEAD 2>/dev/null)"
  actual_branch="$(git -C "$REPO_ROOT" branch --show-current 2>/dev/null)"
  echo "Actual:     $actual_branch @ ${actual_commit:0:8}"
  echo

  if [[ "$chk_commit" == "$actual_commit" ]]; then
    uncommitted="$(git -C "$REPO_ROOT" status --porcelain 2>/dev/null)"
    if [[ -n "$uncommitted" ]]; then
      echo "SAME COMMIT, but the working tree has changes:"
      echo "$uncommitted" | sed 's/^/    /'
      echo
      echo "→ Someone (another agent, or you) edited files after this checkpoint."
      echo "  Inspect them before resuming. If they conflict with next_action, flag it."
    else
      echo "SAME COMMIT, clean tree."
      echo "→ Checkpoint is current. Resume from next_action."
    fi
  else
    echo "COMMITS DIVERGED."
    echo
    echo "Commits since the checkpoint:"
    git -C "$REPO_ROOT" log --oneline "$chk_commit..HEAD" 2>/dev/null \
      | sed 's/^/    /' \
      || echo "    (cannot compute — the commit may have been rebased or force-pushed)"
    echo
    echo "→ Read those commits, mark the matching steps done, then resume."
  fi
}

cmd_prune() {
  local keep=10
  while [[ $# -gt 0 ]]; do
    case "$1" in
      --keep) keep="$2"; shift 2 ;;
      *) shift ;;
    esac
  done

  local files=()
  while IFS= read -r line; do files+=("$line"); done \
    < <(ls -1t "$CHECKPOINT_DIR"/*.json 2>/dev/null | grep -v '_latest.json' || true)

  local total=${#files[@]}
  if (( total <= keep )); then
    echo "$total checkpoint(s), keeping all (threshold $keep)"
    exit 0
  fi

  echo "Removing $(( total - keep )) old checkpoint(s), keeping the $keep newest…"
  for f in "${files[@]:$keep}"; do
    echo "  removing $(basename "$f")"
    rm "$f"
  done
  echo "Done."
}

[[ $# -lt 1 ]] && usage
command="$1"; shift
case "$command" in
  save)   cmd_save "$@" ;;
  verify) cmd_verify "${1:-unknown}" ;;
  resume) cmd_resume ;;
  list)   cmd_list ;;
  show)   cmd_show "$@" ;;
  diff)   cmd_diff ;;
  prune)  cmd_prune "$@" ;;
  *)      usage ;;
esac
