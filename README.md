# PaperQA

[![Python 3.11+](https://img.shields.io/badge/python-3.11%2B-3776AB.svg)](https://www.python.org/)
[![License: MIT](https://img.shields.io/badge/license-MIT-2383E2.svg)](LICENSE)

PaperQA turns a collection of research papers into a structured Excel workbook. It converts PDFs to Markdown, asks an OpenAI-compatible language model a reusable set of questions, and keeps the answer and supporting source text side by side for review.

> PaperQA accelerates evidence extraction; it does not replace researcher verification. Check generated answers and citations against the original paper before using them in a review.

## What it does

```text
PDF papers ── marker-pdf ──> Markdown ── question schema + LLM ──> Excel
                                                   └────────────> raw responses
```

- Run the full workflow from a browser or the command line.
- Process folders of papers and resume interrupted PDF conversion.
- Use CUDA, Apple Silicon MPS, or CPU for local conversion.
- Define domain-specific extraction schemas in readable YAML.
- Send requests to OpenAI or another OpenAI-compatible endpoint.
- Export two rows per paper: extracted answers and their reported sources.
- Keep every Web UI run isolated in its own local workspace.

## Quick start: Web UI

Python 3.11 or newer is recommended.

```bash
git clone https://github.com/SLEEPYBQ/PaperQA.git
cd PaperQA

python -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt

streamlit run web_app.py
```

On Windows PowerShell, activate the environment with `.venv\Scripts\Activate.ps1`.

The browser interface follows a document-first, Notion-inspired workspace design:

1. **Add papers**: upload PDFs for the complete pipeline or Markdown to skip conversion.
2. **Choose what to extract**: select a YAML question set and inspect its extraction fields.
3. **Build the workbook**: confirm run readiness, follow conversion and extraction progress, preview the results, and download Excel.

Provider credentials and advanced request settings stay in the sidebar. The primary action remains disabled until papers, a valid question set, and a model connection are ready. During a run, the interface streams CLI output and identifies the current pipeline stage instead of leaving the page in an indeterminate loading state.

API keys entered in the interface are passed to the pipeline through the child process environment. They are not written to the run folder. Local runs are stored under `.paperqa_runs/`, which is ignored by Git.

The interface tokens, responsive behavior, interaction states, and contribution guardrails are documented in [DESIGN.md](DESIGN.md).

## Quick start: command line

Set your credentials without putting secrets in shell history:

```bash
export OPENAI_API_KEY="your-api-key"
```

Then choose one of the three modes:

```bash
# Convert PDFs and extract answers
python main.py --mode all -q questions/default.yaml

# Convert PDFs only; no API key or LLM call is needed
python main.py --mode markdown -q questions/default.yaml

# Query Markdown files that already exist
python main.py --mode query -q questions/default.yaml
```

For a non-default provider or model, set both explicitly:

```bash
python main.py --mode query \
  --api-base https://api.openai.com/v1 \
  --model gpt-4.1-mini \
  -q questions/default.yaml
```

Run `python main.py --help` for the complete option list.

## Write a question set

Question sets live in `questions/*.yaml`. A minimal configuration looks like this:

```yaml
survey:
  name: "Study Characteristics"
  description: "Basic properties of empirical research papers"

questions:
  - id: sample_size
    display_name: "Sample Size"
    prompt: |
      What is the final analyzed sample size? Report each study separately.
      If the paper does not state it, answer N/A.

  - id: study_method
    display_name: "Study Method"
    prompt: |
      What research method did the authors use? Use the authors' own terminology.
```

Each question requires:

- `id`: a unique identifier containing letters, numbers, and underscores;
- `display_name`: the label shown to people reviewing the schema;
- `prompt`: the extraction instruction sent to the model.

Run it with `python main.py -q questions/your_schema.yaml` or select it in the Web UI.

## Inputs and outputs

The command-line defaults are:

| Path | Purpose |
| --- | --- |
| `pdfs/` | input PDF papers |
| `markdowns/` | converted Markdown or direct Markdown inputs |
| `results/` | timestamped Excel workbooks and extraction statistics |
| `raw_responses/` | unparsed model responses for auditing and debugging |

The workbook contains `document` and `content_type` columns followed by one column per question. Every document produces an `answer` row and a `source` row. A timestamped workbook is retained alongside `query_results_latest.xlsx`.

Use custom paths when you want each project to remain separate:

```bash
python main.py \
  -i ./my_review/pdfs \
  -m ./my_review/markdowns \
  -o ./my_review/results \
  --raw-response-folder ./my_review/raw_responses \
  -q questions/default.yaml
```

## Useful options

| Option | Purpose |
| --- | --- |
| `--device auto` | choose CUDA, MPS, or CPU automatically |
| `--no-gpu` | force CPU conversion |
| `--max-workers 4` | limit concurrent model requests |
| `--skip-tables` | skip table recognition to reduce conversion memory |
| `--force-ocr` | OCR the full document |
| `--force-convert` | rebuild Markdown that already exists |
| `--reload-every 50` | recycle the conversion worker to bound memory use |
| `--dry-run` | list PDFs without converting them |
| `--verbose` | print detailed progress and paths |

`run.sh` is an opinionated batch example for the included screening workflow. Most new users should start with the Web UI or `main.py` directly.

## Project structure

```text
PaperQA/
├── web_app.py           # Streamlit browser interface
├── .streamlit/          # native control theme
├── DESIGN.md            # UI tokens, interaction states, and design guardrails
├── main.py              # command-line orchestration
├── config.py            # command-line arguments and device selection
├── pdf_converter.py     # marker-pdf conversion
├── query_engine.py      # prompt, model request, and response parsing
├── question_loader.py   # YAML schema loading and validation
├── utils.py             # workbook and statistics export
├── questions/           # reusable extraction schemas
└── requirements.txt     # installable dependencies
```

The CLI is the shared interface for both terminal and browser workflows. The Web UI calls that same interface, so it does not duplicate extraction behavior.

## Privacy and cost

- Papers queried through a hosted model are sent to the endpoint configured by `--api-base`. Review that provider's data policy before processing confidential or unpublished work.
- PDF-to-Markdown conversion runs locally. LLM extraction may incur provider charges.
- Do not commit `.api_key`, `.env`, raw responses, private papers, or generated review workbooks.
- Model output may contain unsupported claims, missing evidence, or malformed citations. Always verify important fields manually.

## Contributing

Issues and focused pull requests are welcome. See [CONTRIBUTING.md](CONTRIBUTING.md) for setup, scope, and lightweight validation guidance.

## License

PaperQA is released under the [MIT License](LICENSE).

## Acknowledgments

PaperQA uses [marker](https://github.com/datalab-to/marker) for PDF conversion and the [OpenAI Python library](https://github.com/openai/openai-python) for OpenAI-compatible model requests.
