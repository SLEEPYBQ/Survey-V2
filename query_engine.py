import os
import glob
import re
from datetime import datetime
from concurrent.futures import ProcessPoolExecutor
from openai import OpenAI
from tqdm import tqdm
from question_loader import get_config, set_config


def _init_worker(config):
    """Initialize worker process with question configuration."""
    set_config(config)


# Marker embeds the true PDF page count as an HTML comment at the top of each markdown.
PAGE_COUNT_RE = re.compile(r'<!--\s*PAGE_COUNT:\s*(\d+)\s*-->')


def _is_reasoning_model(model):
    """Reasoning-class models (GPT-5 / o-series) reject temperature != 1."""
    m = (model or "").lower()
    return m.startswith(("gpt-5", "o1", "o3", "o4"))


def extract_page_count(markdown_content):
    """Return (page_count or None, content with the PAGE_COUNT marker removed)."""
    match = PAGE_COUNT_RE.search(markdown_content)
    if not match:
        return None, markdown_content
    page_count = int(match.group(1))
    cleaned = PAGE_COUNT_RE.sub('', markdown_content, count=1).lstrip('\n')
    return page_count, cleaned


def build_auto_exclude_results(config, page_count):
    """Result dict for a paper auto-excluded by the page-count rule (no LLM call)."""
    screening = config.screening
    decision_id = screening['decision_id']
    max_excluded = screening['min_pages'] - 1
    results = {}
    for question_id in config.question_ids:
        if question_id == decision_id:
            results[question_id] = (
                f"Exclude\nSource: Auto-excluded - paper has {page_count} "
                f"page(s) (<={max_excluded}); not sent to the LLM"
            )
        else:
            results[question_id] = (
                f"N/A\nSource: Skipped - paper auto-excluded "
                f"({page_count} page(s), <={max_excluded})"
            )
    return results


def create_combined_prompt(markdown_content):
    """Create combined prompt with all questions from loaded config"""
    config = get_config()

    # Build questions section dynamically
    questions_text = []
    for i, question in enumerate(config.questions, 1):
        questions_text.append(f"{i}. {question.id}: {question.prompt}")

    questions_section = "\n\n".join(questions_text)

    # Build list of question IDs for the reminder section
    question_ids_list = ", ".join(config.question_ids)

    # Build a worked example from the ACTUAL configured questions (not a hardcoded
    # domain), so the example IDs always match the questions being asked.
    example_questions = config.questions[:2] if config.questions else []
    example_block = "\n\n".join(
        f"## {q.id}\nAnswer: [concise answer for {q.display_name}]\n"
        f"Source: [exact quote from the paper supporting the answer]"
        for q in example_questions
    )

    prompt_template = f"""Please analyze the provided research paper and answer the following questions.

CRITICAL FORMAT REQUIREMENTS:
1. You MUST use the exact format shown below for EVERY question
2. Each question MUST start with ## followed by the exact question ID
3. The answer MUST start with "Answer: " on a new line
4. The source MUST start with "Source: " on a new line
5. DO NOT add any extra text, formatting, or explanations outside this format
6. If information is not available, write "Answer: N/A" and "Source: Not found in the paper"
7. The Source MUST include the specific sources of all key information, including figure or table numbers (e.g., "Figure 1", "Table 2") if applicable
8. All content of the Source Must be directly quoted or derived from the original text of the paper.

EXACT FORMAT TEMPLATE (you must follow this precisely):
## question_id
Answer: [Your concise answer here]
Source: [Quote the relevant text from the paper]

QUESTIONS:
{questions_section}

RESPONSE FORMAT EXAMPLE:
{example_block}

[Continue for all {len(config.questions)} questions using their exact question IDs]

IMPORTANT REMINDERS:
- Use the exact question IDs: {question_ids_list}
- Each answer MUST start with "Answer: "
- Each source MUST start with "Source: "
- Do not use any other formatting

RESEARCH PAPER CONTENT:
{{content}}"""

    return prompt_template.format(content=markdown_content)


def save_raw_response(doc_name, response_text, raw_response_dir='raw_responses'):
    """Save raw LLM response to file"""
    # Create raw response directory
    os.makedirs(raw_response_dir, exist_ok=True)

    # Generate filename (remove .md extension, add timestamp)
    base_name = os.path.splitext(doc_name)[0]
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"{base_name}_{timestamp}.txt"
    filepath = os.path.join(raw_response_dir, filename)

    # Save raw response
    with open(filepath, 'w', encoding='utf-8') as f:
        f.write(f"Document: {doc_name}\n")
        f.write(f"Timestamp: {timestamp}\n")
        f.write("=" * 80 + "\n\n")
        f.write(response_text)

    return filepath


def query_document_with_combined_questions(markdown_content, client, model, doc_name, verbose=False):
    """Query a single document (page marker already stripped) with combined questions"""
    try:
        # Create combined prompt
        combined_prompt = create_combined_prompt(markdown_content)

        if verbose:
            print(f"    Sending query request...")

        # GPT-5 / o-series reasoning models only accept the default temperature (1);
        # passing temperature=0.0 returns an HTTP 400, so omit it for those models.
        create_kwargs = {
            "model": model,
            "messages": [{"role": "user", "content": combined_prompt}],
        }
        if not _is_reasoning_model(model):
            create_kwargs["temperature"] = 0.0

        response = client.chat.completions.create(**create_kwargs)

        # content can legitimately be None (refusal / reasoning-budget truncation)
        result_text = response.choices[0].message.content or ""

        # Save raw response
        raw_response_path = save_raw_response(doc_name, result_text)

        if verbose:
            print(f"    [OK] Query successful")
            print(f"    [Saved] Raw response: {raw_response_path}")

        return True, result_text

    except Exception as e:
        if verbose:
            print(f"    [Error] Query failed: {e}")
        return False, str(e)


def parse_combined_response(response_text):
    """Parse combined response, extract answers for each question"""
    config = get_config()
    results = {}

    # Simplified regex - only match strict format
    # Pattern: ## question_id\nAnswer: xxx\nSource: xxx
    pattern = r'##\s*(\w+)\s*\n\s*Answer:\s*(.*?)\n\s*Source:\s*(.*?)(?=\n\s*##|\Z)'
    matches = re.findall(pattern, response_text, re.DOTALL | re.MULTILINE)

    # Convert matches to dictionary
    for question_id, answer, source in matches:
        # Clean extra whitespace from answer and source
        answer = answer.strip()
        source = source.strip()

        # Combine answer and source
        results[question_id] = f"{answer}\nSource: {source}"

    # Check if all questions were parsed
    missing_questions = []
    for question_id in config.question_ids:
        if question_id not in results:
            missing_questions.append(question_id)
            results[question_id] = "[Parse failed] - Unable to extract answer from response"

    if missing_questions:
        # Try a lenient fallback parse for any question the strict regex missed
        for question_id in missing_questions:
            # Try variant format matching
            alt_patterns = [
                # Standard format with minor variations
                rf'##\s*{re.escape(question_id)}\s*\n(.*?)(?=\n\s*##|\Z)',
                # Answer and Source might be in same paragraph
                rf'##\s*{re.escape(question_id)}\s*\n\s*Answer:\s*(.*?)\s*Source:\s*(.*?)(?=\n\s*##|\Z)',
            ]

            for alt_pattern in alt_patterns:
                match = re.search(alt_pattern, response_text, re.DOTALL | re.MULTILINE | re.IGNORECASE)
                if match:
                    if len(match.groups()) == 1:
                        # Full paragraph match, need to separate Answer and Source
                        content = match.group(1).strip()
                        answer_match = re.search(r'Answer:\s*(.*?)(?=Source:|$)', content, re.DOTALL)
                        source_match = re.search(r'Source:\s*(.*?)$', content, re.DOTALL)

                        if answer_match and source_match:
                            answer = answer_match.group(1).strip()
                            source = source_match.group(1).strip()
                            results[question_id] = f"{answer}\nSource: {source}"
                            break
                    else:
                        # Already separated Answer and Source
                        answer = match.group(1).strip()
                        source = match.group(2).strip()
                        results[question_id] = f"{answer}\nSource: {source}"
                        break

    return results


def query_documents_wrapper(args_tuple):
    """Wrapper function for parallel document querying"""
    markdown_path, api_key, api_base, model, verbose = args_tuple
    doc_name = os.path.basename(markdown_path) if markdown_path else "Unknown document"

    try:
        config = get_config()

        # Read the markdown and split off the embedded page-count marker
        with open(markdown_path, 'r', encoding='utf-8') as f:
            markdown_content = f.read()
        page_count, markdown_content = extract_page_count(markdown_content)

        # Screening pre-check: auto-exclude short papers WITHOUT calling the LLM
        screening = config.screening
        if screening and page_count is not None and page_count < screening['min_pages']:
            if verbose:
                print(f"  [Screen] {doc_name}: {page_count} pages "
                      f"<= {screening['min_pages'] - 1} -> auto-Exclude (no LLM call)")
            return doc_name, True, build_auto_exclude_results(config, page_count), None

        if screening and page_count is None:
            print(f"  [Warning] {doc_name}: no PAGE_COUNT marker found; "
                  f"page-count screening rule not applied")

        # Create OpenAI client
        client = OpenAI(
            api_key=api_key,
            base_url=api_base
        )

        if verbose:
            print(f"  [Processing] Querying document: {doc_name}")

        # Query document
        success, response = query_document_with_combined_questions(
            markdown_content, client, model, doc_name, verbose
        )

        if success:
            # Parse response
            parsed_results = parse_combined_response(response)

            # Validate parse results
            parse_failures = sum(1 for v in parsed_results.values() if "[Parse failed]" in v)
            if parse_failures > 0:
                print(f"  [Warning] {doc_name}: {parse_failures} questions failed to parse")

            if verbose:
                print(f"  [OK] Completed: {doc_name}")

            return doc_name, True, parsed_results, None
        else:
            if verbose:
                print(f"  [Error] Failed: {doc_name}")
            return doc_name, False, None, response

    except Exception as e:
        return doc_name, False, None, str(e)


def query_all_documents(args):
    """Query all Markdown documents"""
    config = get_config()

    # Find all Markdown files
    markdown_files = glob.glob(os.path.join(args.markdown_folder, "*.md"))

    if not markdown_files:
        print(f"[Error] No Markdown files found in {args.markdown_folder}")
        return

    print(f"[Info] Found {len(markdown_files)} Markdown files")

    # API configuration
    api_key = args.api_key or os.getenv('OPENAI_API_KEY')
    if not api_key:
        print("[Error] Please provide OpenAI API key (via --api-key argument or OPENAI_API_KEY environment variable)")
        return

    # Create raw response directory
    os.makedirs('raw_responses', exist_ok=True)
    print(f"[Info] Raw responses will be saved to: raw_responses/")

    # Prepare query arguments
    query_args = [
        (md_path, api_key, args.api_base, args.model, args.verbose)
        for md_path in markdown_files
    ]

    print(f"[Info] Using {args.max_workers} worker processes for parallel queries...")
    print("-" * 50)

    # Store all results
    all_results = {}
    failed_queries = []
    parse_stats = {'total': 0, 'failures': 0}

    # Execute queries in parallel
    with ProcessPoolExecutor(
        max_workers=args.max_workers,
        initializer=_init_worker,
        initargs=(config,)
    ) as executor:
        for doc_name, success, results, error in tqdm(
            executor.map(query_documents_wrapper, query_args),
            total=len(query_args),
            desc="Query progress"
        ):
            if success:
                # Count parse failures
                for v in results.values():
                    if "[Parse failed]" in v:
                        parse_stats['failures'] += 1
                parse_stats['total'] += len(results)

                # Build result dictionary
                doc_result = {"document": doc_name}
                doc_result.update(results)
                all_results[doc_name] = doc_result
            else:
                print(f"[Error] {doc_name}: {error}")
                failed_queries.append((doc_name, error))
                # Add placeholder for failed queries
                doc_result = {"document": doc_name}
                for question_id in config.question_ids:
                    doc_result[question_id] = f"[Query failed] - {error}"
                all_results[doc_name] = doc_result

    # Output statistics
    print("\n" + "=" * 50)
    print("[Stats] Query completed:")
    print(f"[OK] Successful queries: {len(all_results) - len(failed_queries)} documents")
    print(f"[Error] Failed queries: {len(failed_queries)} documents")

    if parse_stats['total'] > 0:
        success_rate = (parse_stats['total'] - parse_stats['failures']) / parse_stats['total'] * 100
        print(f"[Info] Parse success rate: {success_rate:.1f}% ({parse_stats['total'] - parse_stats['failures']}/{parse_stats['total']} questions)")

    if failed_queries:
        print(f"\n[Error] Failed query details:")
        for doc_name, error in failed_queries[:5]:  # Only show first 5 errors
            print(f"  - {doc_name}: {error}")
        if len(failed_queries) > 5:
            print(f"  ... and {len(failed_queries) - 5} more failed queries")

    # Debug: if there are parse failures, show some details
    if parse_stats['failures'] > 0:
        print(f"\n[Warning] Parse failure debug info:")
        # Find which questions fail most often
        question_failure_count = {}
        for doc_result in all_results.values():
            for question_id in config.question_ids:
                if question_id in doc_result and "[Parse failed]" in doc_result[question_id]:
                    question_failure_count[question_id] = question_failure_count.get(question_id, 0) + 1

        if question_failure_count:
            sorted_failures = sorted(question_failure_count.items(), key=lambda x: x[1], reverse=True)
            print("  Most frequently failed questions:")
            for question_id, count in sorted_failures[:5]:
                print(f"    - {question_id}: {count} failures")
    return all_results
