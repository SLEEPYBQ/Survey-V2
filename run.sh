#!/usr/bin/env bash
#
# run.sh - Run the PaperQA screening/classification pipeline and save a log.
#
# Usage:
#   ./run.sh                 # uses the settings below
#   MODE=query ./run.sh      # override any setting via env var, e.g. skip conversion
#
# The API key is read from $OPENAI_API_KEY if set, otherwise from the gitignored
# `.api_key` file in this directory. The key is NEVER hardcoded in this script.
#
set -uo pipefail

# ---------------------------- editable settings ----------------------------
QUESTIONS="${QUESTIONS:-questions/screening.yaml}"   # which question config
INPUT_FOLDER="${INPUT_FOLDER:-pdfs}"                  # source PDFs
MARKDOWN_FOLDER="${MARKDOWN_FOLDER:-markdowns_hri}"   # converted markdown (dedicated)
OUTPUT_FOLDER="${OUTPUT_FOLDER:-results_hri}"         # Excel output (dedicated)
MODEL="${MODEL:-qwen3.7-plus}"                        # LLM model id
MODE="${MODE:-all}"                                   # all | markdown | query
MAX_WORKERS="${MAX_WORKERS:-4}"                       # parallel query workers
FORCE_CONVERT="${FORCE_CONVERT:-0}"                   # 1 = re-convert even if .md exists
RELOAD_EVERY="${RELOAD_EVERY:-50}"                    # recycle conversion worker every N PDFs (OS reclaims memory; 0=in-process)
SKIP_TABLES="${SKIP_TABLES:-1}"                       # 1 = skip table model (text-only task; saves mem/time)
CONDA_ENV="${CONDA_ENV:-survey}"                      # conda env name
# ---------------------------------------------------------------------------
# Dedicated folders (markdowns_hri/, results_hri/) keep this screening run clean
# and separate from the repo's existing markdowns/ + results/. The query step
# processes EVERY *.md in MARKDOWN_FOLDER, so a dedicated folder avoids mixing.
# Conversion auto-skips PDFs already converted (resume); set FORCE_CONVERT=1 to redo.

# Always run from the directory this script lives in
cd "$(dirname "$0")"

# Resolve the API key: prefer env var, else the gitignored .api_key file
if [[ -z "${OPENAI_API_KEY:-}" ]]; then
  if [[ -f .api_key ]]; then
    OPENAI_API_KEY="$(tr -d ' \t\r\n' < .api_key)"
  else
    echo "[Error] No API key found. Set OPENAI_API_KEY or create a .api_key file." >&2
    exit 1
  fi
fi
export OPENAI_API_KEY

# Timestamped log (logs/ is gitignored)
mkdir -p logs
LOG="logs/run_$(date +%Y%m%d_%H%M%S).log"

FORCE_FLAG=""
[[ "$FORCE_CONVERT" == "1" ]] && FORCE_FLAG="--force-convert"
TABLES_FLAG=""
[[ "$SKIP_TABLES" == "1" ]] && TABLES_FLAG="--skip-tables"

echo "[Info] env=$CONDA_ENV  model=$MODEL  mode=$MODE  workers=$MAX_WORKERS  force_convert=$FORCE_CONVERT"
echo "[Info] questions=$QUESTIONS"
echo "[Info] $INPUT_FOLDER -> $MARKDOWN_FOLDER -> $OUTPUT_FOLDER"
echo "[Info] logging to $LOG"
echo "---------------------------------------------------------------"

# --no-capture-output + python -u  => output streams live AND is tee'd to the log
conda run --no-capture-output -n "$CONDA_ENV" python -u main.py \
  -q "$QUESTIONS" \
  -i "$INPUT_FOLDER" -m "$MARKDOWN_FOLDER" -o "$OUTPUT_FOLDER" \
  --mode "$MODE" --model "$MODEL" --max-workers "$MAX_WORKERS" \
  --reload-every "$RELOAD_EVERY" --verbose $FORCE_FLAG $TABLES_FLAG \
  2>&1 | tee "$LOG"

status="${PIPESTATUS[0]}"
echo "---------------------------------------------------------------"
echo "[Done] exit=$status  |  log saved to $LOG"
exit "$status"
