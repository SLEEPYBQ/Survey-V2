# Survey-V2

A comprehensive tool for converting PDF research papers to Markdown format and automatically extracting structured information using Large Language Models (LLMs).

## Features

- **PDF to Markdown Conversion**: Convert PDF research papers to clean Markdown format using marker library
- **AI-Powered Question Answering**: Extract structured information from papers using LLM API (**Default: Deepseek-V3**)
- **Batch Processing**: Process multiple papers simultaneously with parallel processing
- **Flexible Execution Modes**: Choose between conversion-only, query-only, or full pipeline
- **GPU Acceleration**: Support for CUDA, MPS (Apple Silicon), and CPU processing
- **Structured Output**: Export results to CSV format for easy analysis
- **Customized Questions**: Support Customized Questions using YAML

## Requirements



### System Requirements

- Python 3.11
- Optional: CUDA-capable GPU or Apple Silicon for faster PDF processing
- API key for question answering functionality


## Installation

1. Clone the repository:
```bash
git clone https://github.com/SLEEPYBQ/Survey-V2.git
cd Survey-V2
```

2. Install dependencies:

```bash
conda create -n survey python=3.11
conda activate survey
pip install marker-pdf
```


## Usage

### Basic Usage

```bash
# Full pipeline: Convert PDFs and extract information
python main.py --api-key your_api_key

# Convert PDFs to Markdown only
python main.py --mode markdown

# Query existing Markdown files only
python main.py --mode query --api-key your_api_key
```

### Advanced Options

```bash
# Specify custom directories
python main.py --input-folder ./papers --markdown-folder ./converted --output-folder ./analysis

# Use specific GPU device
python main.py --device cuda
python main.py --device mps

# Force CPU processing
python main.py --no-gpu

# Increase parallel processing
python main.py --max-workers 8

# Verbose output
python main.py --verbose

# Dry run (see what files would be processed)
python main.py --dry-run
```

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

### Command Line Arguments

| Argument | Description | Default |
|----------|-------------|---------|
| `--input-folder`, `-i` | Input PDF folder path | `pdfs` |
| `--markdown-folder`, `-m` | Markdown output folder path | `markdowns` |
| `--output-folder`, `-o` | Results output folder path | `results` |
| `--mode` | Execution mode: `markdown`, `query`, or `all` | `all` |
| `--device` | Processing device: `auto`, `cpu`, `cuda`, `mps` | `auto` |
| `--no-gpu` | Force CPU processing | `False` |
| `--api-key` | API key | `xxx` |
| `--api-base` | API base URL | `https://api.openai-proxy.org/v1` |
| `--model` |  Language model to use | `deepseek-chat` |
| `--max-workers` | Maximum parallel processes for querying | `4` |
| `--verbose`, `-v` | Enable verbose output | `False` |
| `--dry-run` | Show files to process without executing | `False` |


## Output Format

Results are saved in CSV format with:
- Each row representing one research paper
- Each column representing one extracted data point
- Answers and source citations separated by newlines within cells
- Failed extractions marked with descriptive error messages


## Important Notes

- Prompt structure generated dynamically from YAML - format instructions are hardcoded in `query_engine.py`
- Each worker in ProcessPoolExecutor creates its own OpenAI client
- Raw LLM responses saved to `raw_responses/` for debugging with timestamps
- Failed parses marked as `[Parse failed]`, failed queries as `[Query failed]`
- Memory: Uses `gc.collect()` and GPU cache clearing between documents
- Output files include timestamped versions and a `_latest.xlsx` copy


## Acknowledgments

- [marker-pdf](https://github.com/VikParuchuri/marker) for PDF processing