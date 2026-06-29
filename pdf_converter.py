import os
import glob
import gc
import time
import threading
from marker.converters.pdf import PdfConverter
from marker.models import create_model_dict
from marker.output import text_from_rendered
import pypdfium2 as pdfium
import torch

# Global lock for synchronizing model creation
_model_lock = threading.Lock()


def get_pdf_page_count(pdf_path):
    """Read the true page count directly from the PDF (independent of markdown)."""
    try:
        pdf = pdfium.PdfDocument(pdf_path)
        n = len(pdf)
        pdf.close()
        return n
    except Exception as e:
        print(f"    [Warning] Could not read page count for "
              f"{os.path.basename(pdf_path)}: {e}")
        return None


def create_converter(config, thread_id=None):
    """Create PDF converter"""
    with _model_lock:
        try:
            converter = PdfConverter(
                artifact_dict=create_model_dict()
            )

            if config.get('verbose', False):
                print(f"    [Thread {thread_id}] Converter created successfully")

            return converter

        except Exception as e:
            print(f"    [Thread {thread_id}] Failed to create converter: {e}")
            raise e


def convert_single_pdf(pdf_path, output_folder, config, converter, device='cpu'):
    """Convert single PDF file to Markdown using a shared (reused) converter"""
    result = {
        'success': False,
        'output_path': None,
        'error': None,
        'text_length': 0,
        'page_count': None,
        'filename': os.path.basename(pdf_path)
    }

    start_time = time.time()

    try:
        if config.get('verbose', False):
            print(f"    Using device: {device}")

        # Read the true page count from the PDF (for downstream screening)
        page_count = get_pdf_page_count(pdf_path)

        # Convert PDF
        if config.get('verbose', False):
            print(f"    Starting PDF conversion...")

        rendered = converter(pdf_path)
        markdown_text, metadata, images = text_from_rendered(rendered)

        # Embed the page count so the query/screening stage can read it without the PDF
        if page_count is not None:
            markdown_text = f"<!-- PAGE_COUNT: {page_count} -->\n\n{markdown_text}"

        # Generate output filename
        filename = os.path.basename(pdf_path)
        base_name = os.path.splitext(filename)[0]
        output_path = os.path.join(output_folder, f"{base_name}.md")

        # Save Markdown file
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(markdown_text)

        if config.get('verbose', False):
            print(f"    [OK] Markdown saved successfully ({page_count} pages)")
            if images:
                print(f"    [Info] Detected {len(images)} images (ignored)")

        result['success'] = True
        result['output_path'] = output_path
        result['text_length'] = len(markdown_text)
        result['page_count'] = page_count
        result['time_taken'] = time.time() - start_time

    except Exception as e:
        result['error'] = str(e)
        result['time_taken'] = time.time() - start_time
        if config.get('verbose', False):
            print(f"    [Error] Conversion failed: {e}")

    finally:
        # Light per-PDF cleanup. The converter is SHARED across all PDFs, so it is
        # NOT deleted here; only transient per-document tensors are released.
        gc.collect()
        if device == 'cuda' and torch.cuda.is_available():
            torch.cuda.empty_cache()
        elif device == 'mps' and torch.backends.mps.is_available():
            if hasattr(torch.mps, 'empty_cache'):
                torch.mps.empty_cache()

    return result


def convert_pdfs_to_markdown(args, device):
    """Batch convert PDF files to Markdown"""

    # Create output folder
    os.makedirs(args.markdown_folder, exist_ok=True)

    # Find all PDF files
    pdf_files = glob.glob(os.path.join(args.input_folder, "*.pdf"))
    pdf_files.extend(glob.glob(os.path.join(args.input_folder, "*.PDF")))

    if not pdf_files:
        print(f"[Error] No PDF files found in {args.input_folder}")
        return []

    print(f"[Info] Found {len(pdf_files)} PDF files")

    if args.dry_run:
        print("[Info] Dry run mode - files to be processed:")
        for i, pdf_path in enumerate(pdf_files, 1):
            print(f"  {i}. {os.path.basename(pdf_path)}")
        return []

    # Prepare configuration
    config = {
        'verbose': args.verbose,
        'format_lines': args.format_lines,
        'force_ocr': args.force_ocr,
    }

    print(f"[Info] Output directory: {args.markdown_folder}")

    # Build the marker model suite ONCE and reuse it for every PDF. Reloading it per
    # file would reload several hundred MB of weights each iteration. (Single-threaded
    # is intentional: marker models cannot be built in parallel on Apple MPS.)
    print("[Info] Loading marker models (one-time)...")
    converter = create_converter(config)
    print("-" * 50)

    # Conversion statistics
    successful_conversions = []
    failed_conversions = []
    total_start_time = time.time()

    # Single-threaded PDF conversion (converter reused across all files)
    for i, pdf_path in enumerate(pdf_files, 1):
        filename = os.path.basename(pdf_path)
        print(f"[{i}/{len(pdf_files)}] [Processing] Converting: {filename}")

        result = convert_single_pdf(pdf_path, args.markdown_folder, config, converter, device)

        if result['success']:
            print(f"  [OK] Success ({result['time_taken']:.1f}s)")
            if args.verbose:
                print(f"     [Info] Text: {result['text_length']} characters")
            successful_conversions.append(result['output_path'])
        else:
            print(f"  [Error] Failed: {result['error']}")
            failed_conversions.append((filename, result['error']))

    # Output summary
    total_time = time.time() - total_start_time
    print("\n" + "=" * 50)
    print("[Stats] Conversion completed:")
    print(f"[OK] Successfully converted: {len(successful_conversions)} files")
    print(f"[Error] Failed: {len(failed_conversions)} files")
    print(f"[Time] Total time: {total_time:.1f} seconds")
    if successful_conversions:
        print(f"[Info] Average speed: {total_time/len(pdf_files):.1f} seconds/file")

    if failed_conversions:
        print(f"\n[Error] Failed file details:")
        for filename, error in failed_conversions:
            print(f"  - {filename}: {error}")

    return successful_conversions
