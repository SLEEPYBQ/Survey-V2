#!/usr/bin/env python3
"""
PDF to Markdown conversion and batch question-answering tool
Main program file
"""

import sys

from config import parse_args, detect_device
from pdf_converter import convert_pdfs_to_markdown
from query_engine import query_all_documents
from utils import save_results_to_xlsx
from question_loader import (
    load_questions,
    set_config,
    find_default_config,
    QuestionLoaderError
)


def main():
    """Main function"""
    args = parse_args()

    print("PDF to Markdown Conversion and Batch Query Tool")
    print("=" * 60)

    # Load question configuration
    question_config_path = args.questions
    if question_config_path is None:
        # Try to find default config
        default_config = find_default_config()
        if default_config is None:
            print("[Error] No question configuration found.")
            print("  Please specify a config file with --questions or")
            print("  create questions/default.yaml")
            sys.exit(1)
        question_config_path = default_config
        print(f"[Info] Using default question config: {question_config_path}")

    try:
        config = load_questions(question_config_path)
        set_config(config)
        print(f"[Info] Loaded {len(config.questions)} questions from '{config.survey_name}'")
    except QuestionLoaderError as e:
        print(f"[Error] Failed to load question configuration: {e}")
        sys.exit(1)

    if args.mode in ['markdown', 'all']:
        print("\n[Info] Starting PDF to Markdown conversion...")
        # Detect device
        device = detect_device(args)

        # Display configuration
        if args.verbose:
            print("[Config] Conversion settings:")
            print(f"   Input folder: {args.input_folder}")
            print(f"   Markdown folder: {args.markdown_folder}")
            print(f"   Device: {device}")
            print(f"   Format lines: {args.format_lines}")
            print(f"   Force OCR: {args.force_ocr}")
            print("-" * 50)

        # Execute conversion
        successful_markdowns = convert_pdfs_to_markdown(args, device)

        if not successful_markdowns and args.mode == 'all':
            print("[Error] No Markdown files converted, skipping query step")
            return

    if args.mode in ['query', 'all']:
        print("\n[Info] Starting document queries...")

        # Display query configuration
        if args.verbose:
            print("[Config] Query settings:")
            print(f"   Markdown folder: {args.markdown_folder}")
            print(f"   Output folder: {args.output_folder}")
            print(f"   API model: {args.model}")
            print(f"   Max workers: {args.max_workers}")
            print(f"   Question config: {question_config_path}")
            print("-" * 50)

        # Execute queries
        all_results = query_all_documents(args)

        # Save results to Excel
        if all_results:
            save_results_to_xlsx(all_results, args.output_folder)

    print("\n[Done] All tasks completed!")


if __name__ == "__main__":
    main()
