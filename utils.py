import os
import json
import glob
from datetime import datetime
from question_loader import get_config
import pandas as pd


def save_results_to_xlsx(all_results, output_dir):
    """Save results to XLSX file with answer and source rows"""
    config = get_config()

    # Create output directory
    os.makedirs(output_dir, exist_ok=True)

    # Build headers: add content type identifier column
    fieldnames = ['document', 'content_type'] + config.question_ids

    # Generate timestamped filename
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    xlsx_filename = f"query_results_{timestamp}.xlsx"
    xlsx_path = os.path.join(output_dir, xlsx_filename)

    # Also create a latest results link (overwrite)
    latest_xlsx_path = os.path.join(output_dir, "query_results_latest.xlsx")

    # Statistics
    stats = {
        'total_documents': len(all_results),
        'parse_failures': 0,
        'query_failures': 0,
        'empty_answers': 0
    }

    # Build DataFrame - each document produces two rows: answer row and source row
    rows = []
    for doc_name, results in all_results.items():
        # Separate answer and source information
        answer_row = {'document': doc_name, 'content_type': 'answer'}
        source_row = {'document': doc_name, 'content_type': 'source'}

        for question_id in config.question_ids:
            if question_id in results:
                full_content = results[question_id]

                # Statistics
                if "[Parse failed]" in full_content:
                    stats['parse_failures'] += 1
                elif "[Query failed]" in full_content:
                    stats['query_failures'] += 1

                # Separate answer and source information
                if "\nSource:" in full_content:
                    answer_part, source_part = full_content.split("\nSource:", 1)
                    answer_row[question_id] = answer_part.strip()
                    source_row[question_id] = source_part.strip()

                    # Check for empty answers
                    if answer_part.strip() in ["N/A", ""]:
                        stats['empty_answers'] += 1
                else:
                    # If no Source marker, entire content is the answer
                    answer_row[question_id] = full_content.strip()
                    source_row[question_id] = ""

                    if full_content.strip() in ["N/A", ""]:
                        stats['empty_answers'] += 1
            else:
                answer_row[question_id] = ""
                source_row[question_id] = ""

        # Add answer row and source row
        rows.append(answer_row)
        rows.append(source_row)

    # Create DataFrame
    df = pd.DataFrame(rows, columns=fieldnames)

    # Save as xlsx
    df.to_excel(xlsx_path, index=False)
    # Copy to latest results file
    df.to_excel(latest_xlsx_path, index=False)

    # Save statistics
    stats_path = os.path.join(output_dir, f"query_stats_{timestamp}.json")
    with open(stats_path, 'w', encoding='utf-8') as f:
        json.dump(stats, f, indent=2)

    print(f"\n[Saved] Query results saved to:")
    print(f"   - Main file: {xlsx_path}")
    print(f"   - Latest results: {latest_xlsx_path}")
    print(f"   - Statistics: {stats_path}")

    # Display statistics summary
    if stats['total_documents'] > 0:
        total_questions = stats['total_documents'] * len(config.question_ids)
        successful_parses = total_questions - stats['parse_failures'] - stats['query_failures']
        print(f"\n[Stats] Data quality statistics:")
        print(f"   - Successfully parsed: {successful_parses}/{total_questions} ({successful_parses/total_questions*100:.1f}%)")
        print(f"   - Empty/N/A: {stats['empty_answers']} ({stats['empty_answers']/total_questions*100:.1f}%)")
        print(f"   - Parse failures: {stats['parse_failures']} ({stats['parse_failures']/total_questions*100:.1f}%)")
        print(f"   - Total rows: {len(rows)} (2 rows per document: answer + source)")

    return xlsx_path


def validate_raw_responses(raw_response_dir='raw_responses'):
    """Validate files in raw response directory"""
    if not os.path.exists(raw_response_dir):
        print(f"[Warning] Raw response directory does not exist: {raw_response_dir}")
        return

    response_files = glob.glob(os.path.join(raw_response_dir, "*.txt"))

    if not response_files:
        print(f"[Warning] Raw response directory is empty: {raw_response_dir}")
        return

    print(f"\n[Info] Raw response validation:")
    print(f"   - Found {len(response_files)} response files")

    # Check file sizes
    total_size = 0
    min_size = float('inf')
    max_size = 0

    for file_path in response_files:
        size = os.path.getsize(file_path)
        total_size += size
        min_size = min(min_size, size)
        max_size = max(max_size, size)

    avg_size = total_size / len(response_files) if response_files else 0

    print(f"   - Average size: {avg_size/1024:.1f} KB")
    print(f"   - Min/Max: {min_size/1024:.1f} KB / {max_size/1024:.1f} KB")

    # Check most recent response
    latest_file = max(response_files, key=os.path.getctime)
    print(f"   - Latest file: {os.path.basename(latest_file)}")


def create_summary_report(all_results, output_dir):
    """Create summary report"""
    config = get_config()
    report_path = os.path.join(output_dir, "summary_report.txt")

    with open(report_path, 'w', encoding='utf-8') as f:
        f.write("PDF Research Paper Analysis Summary Report\n")
        f.write("=" * 60 + "\n")
        f.write(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
        f.write(f"Total Documents: {len(all_results)}\n\n")

        # Create summary for each question
        for question_id in config.question_ids:
            f.write(f"\n{question_id.replace('_', ' ').title()}:\n")
            f.write("-" * 40 + "\n")

            # Collect all answers for this question
            answers = []
            for doc_name, results in all_results.items():
                if question_id in results:
                    full_content = results[question_id]
                    # Extract answer part (content before Source)
                    if "\nSource:" in full_content:
                        answer = full_content.split('\nSource:')[0].strip()
                    else:
                        answer = full_content.strip()

                    if answer and "[Parse failed]" not in answer and "[Query failed]" not in answer and answer != "N/A":
                        answers.append(f"- {doc_name}: {answer[:100]}{'...' if len(answer) > 100 else ''}")

            if answers:
                for answer in answers[:5]:  # Only show first 5 answers
                    f.write(f"{answer}\n")
                if len(answers) > 5:
                    f.write(f"... and {len(answers) - 5} more\n")
            else:
                f.write("No valid answers found\n")

    print(f"[Info] Summary report saved to: {report_path}")
    return report_path
