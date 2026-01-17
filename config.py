import argparse
import os
import torch


def parse_args():
    """Parse command line arguments"""
    parser = argparse.ArgumentParser(description='PDF to Markdown conversion and batch query tool')

    # Basic arguments
    parser.add_argument('--input-folder', '-i', default='pdfs',
                        help='Input PDF folder path (default: pdfs)')
    parser.add_argument('--markdown-folder', '-m', default='markdowns',
                        help='Markdown folder path (default: markdowns)')
    parser.add_argument('--output-folder', '-o', default='results',
                        help='Output results folder path (default: results)')

    # Mode selection
    parser.add_argument('--mode', default='all', choices=['markdown', 'query', 'all'],
                        help='Execution mode: markdown (PDF to MD only), query (query only), '
                             'all (convert then query) (default: all)')

    # Device arguments (for PDF conversion)
    parser.add_argument('--device', default='mps', choices=['auto', 'cpu', 'cuda', 'mps'],
                        help='Specify device (default: mps)')
    parser.add_argument('--no-gpu', action='store_true',
                        help='Force CPU mode, do not use any GPU')

    # Conversion arguments
    parser.add_argument('--format-lines', action='store_true',
                        help='Format text lines, improve math formula quality')
    parser.add_argument('--force-ocr', action='store_true',
                        help='Force OCR processing for entire document')

    # Question configuration
    parser.add_argument('--questions', '-q', default=None,
                        help='Path to questions YAML config file '
                             '(default: questions/default.yaml or first .yaml in questions/)')

    # OpenAI API arguments
    parser.add_argument('--api-key', default='xxx',
                        help='OpenAI API key')
    parser.add_argument('--api-base', default='https://api.openai-proxy.org/v1',
                        help='OpenAI API Base URL')
    parser.add_argument('--model', default='deepseek-chat',
                        help='Model to use')

    # Concurrency arguments
    parser.add_argument('--max-workers', type=int, default=8,
                        help='Maximum concurrent workers for querying (default: 8)')

    # Other arguments
    parser.add_argument('--verbose', '-v', action='store_true',
                        help='Show verbose output')
    parser.add_argument('--dry-run', action='store_true',
                        help='Dry run, only show files to process without actual conversion')

    return parser.parse_args()


def detect_device(args):
    """Detect and configure compute device"""
    if args.no_gpu or args.device == 'cpu':
        device = 'cpu'
        print("[Device] Using CPU mode")
    elif args.device == 'cuda':
        if torch.cuda.is_available():
            device = 'cuda'
            print("[Device] Using CUDA GPU mode")
        else:
            device = 'cpu'
            print("[Warning] CUDA not available, falling back to CPU")
    elif args.device == 'mps':
        if torch.backends.mps.is_available():
            device = 'mps'
            print("[Device] Using MPS (Apple GPU) mode")
        else:
            device = 'cpu'
            print("[Warning] MPS not available, falling back to CPU")
    else:  # auto
        if torch.cuda.is_available():
            device = 'cuda'
            print("[Device] Auto-detected CUDA GPU")
        elif torch.backends.mps.is_available():
            device = 'mps'
            print("[Device] Auto-detected MPS (Apple GPU)")
        else:
            device = 'cpu'
            print("[Device] Using CPU mode")

    # Set environment variable
    os.environ['TORCH_DEVICE'] = device
    return device
