import os
import glob
import gc
import time
import logging
import threading
import multiprocessing as mp
from marker.converters.pdf import PdfConverter
from marker.models import create_model_dict
from marker.output import text_from_rendered
import pypdfium2 as pdfium
import torch

# Global lock for synchronizing model creation
_model_lock = threading.Lock()


try:
    import psutil
    _PROC = psutil.Process()

    def _rss_mb():
        """Current resident memory of this process, in MB."""
        return _PROC.memory_info().rss / (1024 * 1024)
except Exception:
    def _rss_mb():
        return 0.0


def _empty_cache(device):
    """Release cached GPU/MPS memory for the given device."""
    if device == 'cuda' and torch.cuda.is_available():
        torch.cuda.empty_cache()
    elif device == 'mps' and torch.backends.mps.is_available():
        if hasattr(torch.mps, 'empty_cache'):
            torch.mps.empty_cache()


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
    """Create PDF converter, optionally without the table-recognition model."""
    with _model_lock:
        try:
            skip_tables = config.get('skip_tables', False)

            if skip_tables:
                # Silence the one-time 'TableRecEncoderDecoderModel not compatible with
                # mps' notice, since we drop that model immediately below.
                surya_logger = logging.getLogger('surya')
                prev_level = surya_logger.level
                surya_logger.setLevel(logging.ERROR)
                try:
                    models = create_model_dict()
                finally:
                    surya_logger.setLevel(prev_level)

                # Drop the table-recognition model (frees memory) and remove the table
                # processors so the table step is skipped entirely. Tables degrade to
                # plain text, which is fine for text-only extraction.
                models.pop('table_rec_model', None)
                gc.collect()
                processor_list = [
                    f"{p.__module__}.{p.__name__}"
                    for p in PdfConverter.default_processors
                    if 'Table' not in p.__name__
                ]
                converter = PdfConverter(artifact_dict=models, processor_list=processor_list)
            else:
                converter = PdfConverter(artifact_dict=create_model_dict())

            if config.get('verbose', False):
                extra = " (tables skipped)" if skip_tables else ""
                print(f"    [Thread {thread_id}] Converter created successfully{extra}")

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

        # Drop large per-document objects so the cleanup below can reclaim them
        del rendered, markdown_text, metadata, images

    except Exception as e:
        result['error'] = str(e)
        result['time_taken'] = time.time() - start_time
        if config.get('verbose', False):
            print(f"    [Error] Conversion failed: {e}")

    finally:
        # Light per-PDF cleanup. The converter is SHARED across all PDFs, so it is
        # NOT deleted here; only transient per-document tensors are released.
        gc.collect()
        _empty_cache(device)

    return result


# --- Isolated-worker conversion (recycled to bound memory) ---------------------
# A single worker process converts PDFs and is recycled every N files via the pool's
# maxtasksperchild. When the worker is recycled the OS reclaims ALL of its memory,
# which in-process gc/empty_cache cannot do. Each new worker reloads the models once.
_WORKER = {}


def _conv_worker_init(config, device):
    """Pool initializer: build the converter once per (recycled) worker process."""
    _WORKER['config'] = config
    _WORKER['device'] = device
    _WORKER['converter'] = create_converter(config)


def _conv_worker_task(task):
    """Convert one PDF inside the worker; returns picklable primitives."""
    idx, total, pdf_path, output_folder = task
    filename = os.path.basename(pdf_path)
    print(f"[{idx}/{total}] [Processing] Converting: {filename}", flush=True)
    result = convert_single_pdf(
        pdf_path, output_folder, _WORKER['config'], _WORKER['converter'], _WORKER['device']
    )
    if result['success']:
        print(f"  [OK] Success ({result['time_taken']:.1f}s, RSS {_rss_mb():.0f} MB)", flush=True)
    else:
        print(f"  [Error] Failed: {result['error']}", flush=True)
    return (filename, result['success'], result.get('output_path'), result.get('error'))


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
        'skip_tables': getattr(args, 'skip_tables', False),
    }

    print(f"[Info] Output directory: {args.markdown_folder}")

    # Resume support: skip any PDF whose markdown already exists, so an interrupted
    # batch can be restarted without re-converting everything (use --force-convert to
    # redo). Already-converted files are still returned so 'all' mode queries them.
    force = getattr(args, 'force_convert', False)
    successful_conversions = []
    pending = []
    for pdf_path in pdf_files:
        base_name = os.path.splitext(os.path.basename(pdf_path))[0]
        out_md = os.path.join(args.markdown_folder, f"{base_name}.md")
        if not force and os.path.exists(out_md):
            successful_conversions.append(out_md)
        else:
            pending.append(pdf_path)

    skipped = len(pdf_files) - len(pending)
    if skipped:
        print(f"[Info] Skipping {skipped} already-converted file(s) "
              f"(use --force-convert to redo them)")

    if not pending:
        print("[Info] All PDFs already converted - nothing to do.")
        return successful_conversions

    # `reload_every` controls memory: the worker is recycled every N files so the OS
    # reclaims all accumulated memory (marker/surya grow in-process in ways that gc +
    # empty_cache cannot fully reclaim). 0 = run in-process with no recycling.
    reload_every = getattr(args, 'reload_every', 50)

    failed_conversions = []
    total_start_time = time.time()

    if reload_every and reload_every > 0:
        # Robust memory bound: convert inside a single isolated worker process that is
        # recycled every `reload_every` files (each new worker reloads the models once).
        print(f"[Info] {len(pending)} file(s) to convert in an isolated worker, "
              f"recycled every {reload_every} files to cap memory...")
        print("-" * 50)
        ctx = mp.get_context('spawn')
        tasks = [(i, len(pending), p, args.markdown_folder)
                 for i, p in enumerate(pending, 1)]
        with ctx.Pool(processes=1, maxtasksperchild=reload_every,
                      initializer=_conv_worker_init, initargs=(config, device)) as pool:
            for filename, ok, outpath, err in pool.imap(_conv_worker_task, tasks):
                if ok:
                    successful_conversions.append(outpath)
                else:
                    failed_conversions.append((filename, err))
    else:
        # In-process: load the models once and reuse them (no recycling). Use when you
        # have plenty of RAM and want to avoid per-recycle model reloads.
        print(f"[Info] {len(pending)} file(s) to convert. Loading marker models (one-time)...")
        converter = create_converter(config)
        print(f"[Info] Models loaded (RSS {_rss_mb():.0f} MB)")
        print("-" * 50)
        for i, pdf_path in enumerate(pending, 1):
            filename = os.path.basename(pdf_path)
            print(f"[{i}/{len(pending)}] [Processing] Converting: {filename}")
            result = convert_single_pdf(pdf_path, args.markdown_folder, config, converter, device)
            if result['success']:
                print(f"  [OK] Success ({result['time_taken']:.1f}s, RSS {_rss_mb():.0f} MB)")
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
    print(f"[OK] Converted this run: {len(pending) - len(failed_conversions)} files "
          f"(+{skipped} skipped, already done)")
    print(f"[Error] Failed: {len(failed_conversions)} files")
    print(f"[Time] Total time: {total_time:.1f} seconds")
    if pending:
        print(f"[Info] Average speed: {total_time/len(pending):.1f} seconds/file")

    if failed_conversions:
        print(f"\n[Error] Failed file details:")
        for filename, error in failed_conversions:
            print(f"  - {filename}: {error}")

    return successful_conversions
