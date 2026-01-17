# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Survey-PQE is an AI-powered research paper analysis pipeline that:
1. Converts PDF research papers to Markdown using the `marker` library
2. Extracts structured data points from papers using LLMs (default: Deepseek-V3)
3. Exports results to Excel with answer and source citation rows

**Current Domain**: Configurable via YAML files in `questions/` directory. Default is HRI elderly care research.

## Common Commands

```bash
# Full pipeline with default question config
python main.py --api-key your_api_key

# Specify a question config file
python main.py -q questions/hri_elderly.yaml --api-key your_api_key

# Convert PDFs to Markdown only
python main.py --mode markdown

# Query existing Markdown files only
python main.py --mode query --api-key your_api_key

# Custom directories
python main.py -i ./papers -m ./converted -o ./analysis

# Device options: auto, cpu, cuda, mps (default: mps on Apple Silicon)
python main.py --device cuda --max-workers 8

# Dry run to preview files
python main.py --dry-run
```

## Architecture

```
PDFs (pdfs/)
    | pdf_converter.py (marker + GPU)
    v
Markdowns (markdowns/)
    | query_engine.py (LLM API, parallel)
    v
Raw Responses (raw_responses/)
    | utils.py (parsing)
    v
Excel Results (results/)
```

### Key Files

| File | Role |
|------|------|
| main.py | Entry point, orchestrates pipeline |
| config.py | CLI args, device detection |
| question_loader.py | Load questions from YAML config |
| pdf_converter.py | PDF->Markdown via marker library |
| query_engine.py | LLM prompting (dynamic), response parsing |
| utils.py | Excel export, statistics generation |

### Question Configuration

Questions are defined in YAML files under `questions/` directory:

```yaml
# questions/hri_elderly.yaml
survey:
  name: "HRI Elderly Care"
  description: "Human-Robot Interaction research papers"

questions:
  - id: involved_stakeholder
    display_name: "Involved Stakeholder"
    prompt: |
      What are the involved stakeholders in the study?...
```

**Key properties:**
- `id`: Internal identifier (used in parsing, Excel columns)
- `display_name`: Human-readable name (for reports)
- `prompt`: Full question text sent to LLM

**To add a new survey topic:**
1. Create `questions/your_topic.yaml` with your questions
2. Run with `-q questions/your_topic.yaml`

### Data Flow Details

1. **Question Loading**: `question_loader.py` loads YAML at startup, provides `get_config()` singleton with `question_ids`, `question_patterns` properties

2. **PDF Conversion**: Uses `marker.converters.pdf.PdfConverter` with `create_model_dict()`. Thread-safe via global `_model_lock`. Supports CUDA/MPS/CPU. Sequential processing.

3. **Query Pipeline**:
   - `create_combined_prompt()` builds prompt dynamically from loaded questions
   - `query_document_with_combined_questions()` calls OpenAI-compatible API (temp=0.0, max_tokens=10000)
   - `parse_combined_response()` uses regex: `##\s*(\w+)\s*\n\s*Answer:\s*(.*?)\n\s*Source:\s*(.*?)(?=\n\s*##|\Z)`
   - ProcessPoolExecutor for parallel processing (default: 8 workers)

4. **Output Format**: Excel (.xlsx) with 2 rows per document (answer row + source row). Columns: `document`, `content_type`, then question IDs from loaded config.

## Configuration

- **Question config**: YAML files in `questions/` directory (default: `questions/default.yaml`)
- **API defaults**: `api.openai-proxy.org/v1`, model `deepseek-chat`
- **Device detection**: Checks CUDA -> MPS -> CPU fallback

## Dependencies

- `marker-pdf`: PDF to Markdown (requires torch)
- `openai`: LLM API client
- `pandas`, `openpyxl`: Excel output
- `tqdm`: Progress bars
- `pyyaml`: YAML config parsing

Python 3.11 required. GPU (CUDA/MPS) optional for faster PDF processing.

## Important Notes

- Prompt structure generated dynamically from YAML - format instructions are hardcoded in `query_engine.py`
- Each worker in ProcessPoolExecutor creates its own OpenAI client
- Raw LLM responses saved to `raw_responses/` for debugging with timestamps
- Failed parses marked as `[Parse failed]`, failed queries as `[Query failed]`
- Memory: Uses `gc.collect()` and GPU cache clearing between documents
- Output files include timestamped versions and a `_latest.xlsx` copy
