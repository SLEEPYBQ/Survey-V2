# PDF Research Paper Analysis Tool

A comprehensive tool for converting PDF research papers to Markdown format and automatically extracting structured information using Large Language Models (LLMs).

## 🚀 Features

- **PDF to Markdown Conversion**: Convert PDF research papers to clean Markdown format using marker library
- **AI-Powered Question Answering**: Extract structured information from papers using OpenAI API
- **Batch Processing**: Process multiple papers simultaneously with parallel processing
- **Flexible Execution Modes**: Choose between conversion-only, query-only, or full pipeline
- **GPU Acceleration**: Support for CUDA, MPS (Apple Silicon), and CPU processing
- **Structured Output**: Export results to CSV format for easy analysis

## 📋 Requirements

### Dependencies

```bash
conda create -n survey python=3.10
conda activate survey
pip install marker
```

### System Requirements

- Python 3.11
- Optional: CUDA-capable GPU or Apple Silicon for faster PDF processing
- OpenAI API key for question answering functionality

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
└── results/               # Query results and CSV output (default)
```

## 🔧 Installation

1. Clone the repository:
```bash
git clone <your-repo-url>
cd pdf-research-analysis
```

2. Install dependencies:
```bash
pip install -r requirements.txt
```

3. Set up your OpenAI API key:
```bash
export OPENAI_API_KEY="your-api-key-here"
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
| `--api-key` | OpenAI API key | Environment variable |
| `--api-base` | OpenAI API base URL | `https://api.openai.com/v1` |
| `--model` | OpenAI model to use | `gpt-3.5-turbo` |
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
   - Verify OpenAI API key is correct
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

## 📄 License

[Add your license information here]

## 🤝 Contributing

[Add contribution guidelines here]

## 📧 Contact

[Add contact information here]

## 🙏 Acknowledgments

- [marker-pdf](https://github.com/VikParuchuri/marker) for PDF processing
- [OpenAI](https://openai.com/) for language model capabilities
