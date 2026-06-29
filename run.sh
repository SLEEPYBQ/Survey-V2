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
MARKDOWN_FOLDER="${MARKDOWN_FOLDER:-markdowns}"       # converted markdown
OUTPUT_FOLDER="${OUTPUT_FOLDER:-results}"             # Excel output
MODEL="${MODEL:-qwen3.7-plus}"                        # LLM model id
MODE="${MODE:-all}"                                   # all | markdown | query
MAX_WORKERS="${MAX_WORKERS:-4}"                       # parallel query workers
CONDA_ENV="${CONDA_ENV:-survey}"                      # conda env name
# ---------------------------------------------------------------------------
# NOTE: in `all`/`query` mode the query step processes EVERY *.md in
# MARKDOWN_FOLDER. If that folder already holds markdown from another topic,
# point MARKDOWN_FOLDER/OUTPUT_FOLDER at a clean folder to avoid mixing.

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

echo "[Info] env=$CONDA_ENV  model=$MODEL  mode=$MODE  workers=$MAX_WORKERS"
echo "[Info] questions=$QUESTIONS"
echo "[Info] $INPUT_FOLDER -> $MARKDOWN_FOLDER -> $OUTPUT_FOLDER"
echo "[Info] logging to $LOG"
echo "---------------------------------------------------------------"

# --no-capture-output + python -u  => output streams live AND is tee'd to the log
conda run --no-capture-output -n "$CONDA_ENV" python -u main.py \
  -q "$QUESTIONS" \
  -i "$INPUT_FOLDER" -m "$MARKDOWN_FOLDER" -o "$OUTPUT_FOLDER" \
  --mode "$MODE" --model "$MODEL" --max-workers "$MAX_WORKERS" --verbose \
  2>&1 | tee "$LOG"

status="${PIPESTATUS[0]}"
echo "---------------------------------------------------------------"
echo "[Done] exit=$status  |  log saved to $LOG"
exit "$status"
