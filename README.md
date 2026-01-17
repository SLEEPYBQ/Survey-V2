# PaperQA

An AI-powered research paper analysis pipeline that converts PDF research papers to Markdown format and automatically extracts structured information using Large Language Models (LLMs). Designed for systematic literature reviews and research paper surveys.

## Overview

PaperQA provides a complete workflow for analyzing research papers:

1. **PDF to Markdown Conversion**: Converts PDF research papers to clean Markdown format using the `marker` library with GPU acceleration support
2. **AI-Powered Information Extraction**: Extracts structured data points from papers using LLM APIs (default: Deepseek-V3)
3. **Batch Processing**: Processes multiple papers simultaneously with parallel processing
4. **Structured Output**: Exports results to Excel format with answer and source citation rows

## Features

- **PDF to Markdown Conversion**: High-quality conversion using marker library with GPU acceleration (CUDA/MPS/CPU support)
- **AI-Powered Question Answering**: Extract structured information from papers using LLM API (default: Deepseek-V3)
- **Batch Processing**: Process multiple papers simultaneously with parallel processing
- **Flexible Execution Modes**: Choose between conversion-only, query-only, or full pipeline
- **GPU Acceleration**: Support for CUDA, MPS (Apple Silicon), and CPU processing
- **Structured Output**: Export results to Excel format with answer and source citations
- **Customizable Questions**: Define extraction questions via YAML configuration files
- **Domain Agnostic**: Easily adapt to different research domains by changing question configurations

## System Requirements

- Python 3.11 or higher
- Optional: CUDA-capable GPU or Apple Silicon for faster PDF processing
- API key for LLM service (OpenAI-compatible API)

## Installation

### 1. Clone the Repository

```bash
git clone https://github.com/SLEEPYBQ/Survey-V2.git
cd Survey-V2
```

### 2. Create Virtual Environment

```bash
conda create -n paperqa python=3.11
conda activate paperqa
```

### 3. Install Dependencies

```bash
# Install PDF conversion library
pip install marker-pdf

# Install other dependencies
pip install openai pandas openpyxl tqdm pyyaml
```

## Quick Start

### Basic Usage

```bash
# Full pipeline: Convert PDFs and extract information
python main.py --api-key your_api_key

# Convert PDFs to Markdown only
python main.py --mode markdown

# Query existing Markdown files only
python main.py --mode query --api-key your_api_key
```

### Specify Question Configuration

```bash
# Use a specific question configuration file
python main.py -q questions/hri_elderly.yaml --api-key your_api_key
```

## Usage Guide

### Execution Modes

- `markdown`: Convert PDFs to Markdown format only
- `query`: Query existing Markdown files and extract information
- `all`: Full pipeline (convert PDFs then query) - default mode

### Advanced Options

```bash
# Specify custom directories
python main.py -i ./papers -m ./converted -o ./analysis

# Use specific GPU device
python main.py --device cuda
python main.py --device mps  # Apple Silicon

# Force CPU processing
python main.py --no-gpu

# Increase parallel processing workers
python main.py --max-workers 8

# Enable verbose output
python main.py --verbose

# Dry run (preview files without processing)
python main.py --dry-run
```

### Question Configuration

Questions are defined in YAML files under the `questions/` directory. Each configuration file defines a set of questions to extract from research papers.

#### Configuration File Structure

```yaml
# questions/hri_elderly.yaml
survey:
  name: "HRI Elderly Care"
  description: "Human-Robot Interaction research papers"

questions:
  - id: involved_stakeholder
    display_name: "Involved Stakeholder"
    prompt: |
      What are the involved stakeholders in the study? 
      Stakeholders include primary subjects or interviewees. 
      Use the title of the role explicitly mentioned in the text 
      (e.g., care staff, elderly individuals).
  
  - id: sample_size
    display_name: "Sample Size"
    prompt: |
      What is the sample size of the study? 
      For example, if 100 people participated and only 90 
      consented to data collection, the sample size is 90.
```

#### Key Properties

- `id`: Internal identifier used in parsing and Excel column headers
- `display_name`: Human-readable name for reports and output
- `prompt`: Full question text sent to the LLM

#### Creating a New Survey Configuration

1. Create a new YAML file in the `questions/` directory
2. Define your survey metadata and questions
3. Run with `-q questions/your_topic.yaml`

## Command Line Arguments

| Argument | Description | Default |
|----------|-------------|---------|
| `--input-folder`, `-i` | Input PDF folder path | `pdfs` |
| `--markdown-folder`, `-m` | Markdown output folder path | `markdowns` |
| `--output-folder`, `-o` | Results output folder path | `results` |
| `--mode` | Execution mode: `markdown`, `query`, or `all` | `all` |
| `--device` | Processing device: `auto`, `cpu`, `cuda`, `mps` | `mps` |
| `--no-gpu` | Force CPU processing | `False` |
| `--questions`, `-q` | Path to questions YAML config file | Auto-detect |
| `--api-key` | LLM API key | Required for query mode |
| `--api-base` | API base URL | `https://api.openai-proxy.org/v1` |
| `--model` | Language model to use | `deepseek-chat` |
| `--max-workers` | Maximum parallel processes for querying | `8` |
| `--verbose`, `-v` | Enable verbose output | `False` |
| `--dry-run` | Show files to process without executing | `False` |
| `--format-lines` | Format text lines, improve math formula quality | `False` |
| `--force-ocr` | Force OCR processing for entire document | `False` |

## Output Format

Results are exported to Excel (.xlsx) format with the following structure:

- **Two rows per document**: One row for answers, one row for source citations
- **Columns**: `document`, `content_type`, followed by question IDs from the loaded configuration
- **Answer format**: Concise answers extracted from the paper
- **Source format**: Direct quotes or derived text from the original paper with specific references (e.g., "Figure 1", "Table 2")
- **Error handling**: Failed extractions marked as `[Parse failed]` or `[Query failed]` with descriptive messages

Output files include:
- Timestamped versions: `query_results_YYYYMMDD_HHMMSS.xlsx`
- Latest copy: `query_results_latest.xlsx`
- Statistics file: `query_stats_YYYYMMDD_HHMMSS.json`

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

### Key Components

- `main.py`: Entry point, orchestrates the pipeline
- `config.py`: CLI argument parsing and device detection
- `question_loader.py`: Loads questions from YAML configuration files
- `pdf_converter.py`: PDF to Markdown conversion via marker library
- `query_engine.py`: LLM prompting (dynamic), response parsing
- `utils.py`: Excel export and statistics generation

## Technical Details

### PDF Conversion

- Uses `marker.converters.pdf.PdfConverter` with `create_model_dict()`
- Thread-safe via global `_model_lock`
- Supports CUDA/MPS/CPU with automatic fallback
- Sequential processing for PDF conversion

### Query Pipeline

- `create_combined_prompt()`: Builds prompt dynamically from loaded questions
- `query_document_with_combined_questions()`: Calls OpenAI-compatible API (temperature=0.0, max_tokens=10000)
- `parse_combined_response()`: Uses regex pattern matching to extract structured answers
- ProcessPoolExecutor for parallel processing (default: 8 workers)
- Each worker creates its own OpenAI client

### Memory Management

- Uses `gc.collect()` and GPU cache clearing between documents
- Automatic memory cleanup after each document

## Important Notes

- Prompt structure is generated dynamically from YAML configuration
- Format instructions are hardcoded in `query_engine.py`
- Raw LLM responses are saved to `raw_responses/` directory with timestamps for debugging
- Failed parses are marked as `[Parse failed]`, failed queries as `[Query failed]`
- The system automatically detects and uses available GPU resources (CUDA -> MPS -> CPU fallback)

## Dependencies

- `marker-pdf`: PDF to Markdown conversion (requires torch)
- `openai`: LLM API client
- `pandas`: Data manipulation
- `openpyxl`: Excel file generation
- `tqdm`: Progress bars
- `pyyaml`: YAML configuration parsing
- `torch`: Deep learning framework (for marker-pdf)

## Acknowledgments

- [marker-pdf](https://github.com/VikParuchuri/marker) for high-quality PDF processing

## License

[Add your license information here]
