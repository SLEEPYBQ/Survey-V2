# Survey-V2

A comprehensive tool for converting PDF research papers to Markdown format and automatically extracting structured information using Large Language Models (LLMs).

## 🚀 Features

- **PDF to Markdown Conversion**: Convert PDF research papers to clean Markdown format using marker library
- **AI-Powered Question Answering**: Extract structured information from papers using LLM API (**Default: Deepseek-V3**)
- **Batch Processing**: Process multiple papers simultaneously with parallel processing
- **Flexible Execution Modes**: Choose between conversion-only, query-only, or full pipeline
- **GPU Acceleration**: Support for CUDA, MPS (Apple Silicon), and CPU processing
- **Structured Output**: Export results to CSV format for easy analysis

## 📋 Requirements



### System Requirements

- Python 3.11
- Optional: CUDA-capable GPU or Apple Silicon for faster PDF processing
- API key for question answering functionality

## 🗂️ Project Structure

```
your_project/
├── main.py                 # Main program entry point
├── config.py              # Configuration and argument parsing
├── pdf_converter.py       # PDF conversion functionality
├── query_engine.py        # LLM querying and response parsing
├── utils.py               # Utility functions
├── pdfs/                  # Input PDF files (default)
├── markdowns/             # Generated Markdown files (default)
├── raw_responses/         # LLM Output results (default)
└── results/               # Query results and CSV output (default)
```

## 🔧 Installation

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


## 📚 Usage

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

## 🔍 Extracted Information

The tool extracts 26 structured data points from each research paper:

### Study Participants
- **Involved Stakeholder**: Study participants and their roles
- **Sample Size**: Number of participants in the study
- **Country**: Geographic location of the study
- **Age**: Age-related information of participants
- **Gender**: Gender distribution information
- **Demographic Background**: Socioeconomic and educational details
- **Cognitive and Physical Impairment**: Health status information

### Study Design
- **Methodology**: Research methods used
- **Care Type**: Type of care being studied
- **Testing Context**: Study environment and setting
- **Process of the Care**: Duration and stages of the care process

### Technology Focus
- **Robot Type**: Description of the robot used
- **Robot Name**: Specific robot model or name
- **Design Goal**: Intended objectives of the robot design
- **Robot Concern Function**: Robot functionalities demonstrated

### User Experience
- **Needs and Expectations**: User requirements and expectations
- **Facilitating Functions**: Positive robot features
- **Inhibitory Functions**: Negative robot features
- **Stakeholder Facilitating Characteristics**: Positive user traits
- **Stakeholder Inhibitory Characteristics**: Limiting user traits

### Outcomes
- **Engagement**: User engagement measurements
- **Acceptance**: User acceptance levels
- **Trust**: Trust in the robot technology
- **Key Findings**: Main study conclusions
- **Additional Info**: Limitations and other details

## 📊 Output Format

Results are saved in CSV format with:
- Each row representing one research paper
- Each column representing one extracted data point
- Answers and source citations separated by newlines within cells
- Failed extractions marked with descriptive error messages

## 🛠️ Technical Details

### PDF Processing
- Uses the `marker` library for high-quality PDF to Markdown conversion
- Supports OCR for scanned documents
- Handles mathematical formulas and complex layouts
- GPU acceleration for faster processing

### LLM Integration
- Combines all questions into a single API call for efficiency
- Uses structured prompts for consistent responses
- Implements flexible regex parsing for various response formats
- Handles different capitalization and formatting variations

### Error Handling
- Graceful handling of PDF conversion failures
- API error recovery and reporting
- Regex parsing fallbacks for malformed responses
- Comprehensive logging and progress tracking

## 🔧 Troubleshooting

### Common Issues

1. **PDF Conversion Fails**
   - Ensure sufficient system memory
   - Try forcing CPU mode with `--no-gpu`
   - Check if PDF is corrupted or password-protected

2. **API Errors**
   - Verify API key is correct
   - Check API rate limits and usage
   - Ensure network connectivity

3. **Parsing Errors**
   - Check the generated Markdown files manually
   - Review regex patterns in `query_engine.py`
   - Enable verbose mode for detailed debugging

### Performance Optimization

- Use GPU acceleration for PDF processing when available
- Adjust `--max-workers` based on your system and API limits
- Process smaller batches if encountering memory issues


## 🙏 Acknowledgments

- [marker-pdf](https://github.com/VikParuchuri/marker) for PDF processing
