import os
import csv
import json
import glob
from datetime import datetime
from config import QUESTION_IDS
import pandas as pd

def save_results_to_xlsx(all_results, output_dir):
    """保存结果到XLSX文件，将答案和源信息分为两行"""
    
    # 创建输出目录
    os.makedirs(output_dir, exist_ok=True)
    
    # 构建表头：添加类型标识符列
    fieldnames = ['document', 'content_type'] + QUESTION_IDS
    
    # 生成带时间戳的文件名
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    xlsx_filename = f"query_results_{timestamp}.xlsx"
    xlsx_path = os.path.join(output_dir, xlsx_filename)
    
    # 同时创建一个最新结果的链接（覆盖）
    latest_xlsx_path = os.path.join(output_dir, "query_results_latest.xlsx")
    
    # 统计信息
    stats = {
        'total_documents': len(all_results),
        'parse_failures': 0,
        'query_failures': 0,
        'empty_answers': 0
    }
    
    # 构建DataFrame - 每个文档产生两行：一行答案，一行源信息
    rows = []
    for doc_name, results in all_results.items():
        # 分离答案和源信息
        answer_row = {'document': doc_name, 'content_type': 'answer'}
        source_row = {'document': doc_name, 'content_type': 'source'}
        
        for question_id in QUESTION_IDS:
            if question_id in results:
                full_content = results[question_id]
                
                # 统计信息
                if "[解析失败]" in full_content:
                    stats['parse_failures'] += 1
                elif "[查询失败]" in full_content:
                    stats['query_failures'] += 1
                
                # 分离答案和源信息
                if "\nSource:" in full_content:
                    answer_part, source_part = full_content.split("\nSource:", 1)
                    answer_row[question_id] = answer_part.strip()
                    source_row[question_id] = source_part.strip()
                    
                    # 检查是否为空答案
                    if answer_part.strip() in ["N/A", ""]:
                        stats['empty_answers'] += 1
                else:
                    # 如果没有Source标记，整个内容作为答案
                    answer_row[question_id] = full_content.strip()
                    source_row[question_id] = ""
                    
                    if full_content.strip() in ["N/A", ""]:
                        stats['empty_answers'] += 1
            else:
                answer_row[question_id] = ""
                source_row[question_id] = ""
        
        # 添加答案行和源信息行
        rows.append(answer_row)
        rows.append(source_row)
    
    # 创建DataFrame
    df = pd.DataFrame(rows, columns=fieldnames)
    
    # 保存为xlsx
    df.to_excel(xlsx_path, index=False)
    # 复制到最新结果文件
    df.to_excel(latest_xlsx_path, index=False)
    
    # 保存统计信息
    stats_path = os.path.join(output_dir, f"query_stats_{timestamp}.json")
    with open(stats_path, 'w', encoding='utf-8') as f:
        json.dump(stats, f, indent=2)
    
    print(f"\n💾 查询结果已保存到:")
    print(f"   - 主文件: {xlsx_path}")
    print(f"   - 最新结果: {latest_xlsx_path}")
    print(f"   - 统计信息: {stats_path}")
    
    # 显示统计摘要
    if stats['total_documents'] > 0:
        total_questions = stats['total_documents'] * len(QUESTION_IDS)
        successful_parses = total_questions - stats['parse_failures'] - stats['query_failures']
        print(f"\n📊 数据质量统计:")
        print(f"   - 成功解析: {successful_parses}/{total_questions} ({successful_parses/total_questions*100:.1f}%)")
        print(f"   - 空值/N/A: {stats['empty_answers']} ({stats['empty_answers']/total_questions*100:.1f}%)")
        print(f"   - 解析失败: {stats['parse_failures']} ({stats['parse_failures']/total_questions*100:.1f}%)")
        print(f"   - 总行数: {len(rows)} (每个文档2行：答案行+源信息行)")
    
    return xlsx_path

def validate_raw_responses(raw_response_dir='raw_responses'):
    """验证原始响应目录中的文件"""
    if not os.path.exists(raw_response_dir):
        print(f"⚠️  原始响应目录不存在: {raw_response_dir}")
        return
    
    response_files = glob.glob(os.path.join(raw_response_dir, "*.txt"))
    
    if not response_files:
        print(f"⚠️  原始响应目录为空: {raw_response_dir}")
        return
    
    print(f"\n📁 原始响应验证:")
    print(f"   - 找到 {len(response_files)} 个响应文件")
    
    # 检查文件大小
    total_size = 0
    min_size = float('inf')
    max_size = 0
    
    for file_path in response_files:
        size = os.path.getsize(file_path)
        total_size += size
        min_size = min(min_size, size)
        max_size = max(max_size, size)
    
    avg_size = total_size / len(response_files) if response_files else 0
    
    print(f"   - 平均大小: {avg_size/1024:.1f} KB")
    print(f"   - 最小/最大: {min_size/1024:.1f} KB / {max_size/1024:.1f} KB")
    
    # 检查最近的响应
    latest_file = max(response_files, key=os.path.getctime)
    print(f"   - 最新文件: {os.path.basename(latest_file)}")

def create_summary_report(all_results, output_dir):
    """创建汇总报告"""
    report_path = os.path.join(output_dir, "summary_report.txt")
    
    with open(report_path, 'w', encoding='utf-8') as f:
        f.write("PDF Research Paper Analysis Summary Report\n")
        f.write("=" * 60 + "\n")
        f.write(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
        f.write(f"Total Documents: {len(all_results)}\n\n")
        
        # 为每个问题创建摘要
        for question_id in QUESTION_IDS:
            f.write(f"\n{question_id.replace('_', ' ').title()}:\n")
            f.write("-" * 40 + "\n")
            
            # 收集该问题的所有答案
            answers = []
            for doc_name, results in all_results.items():
                if question_id in results:
                    full_content = results[question_id]
                    # 提取答案部分（Source之前的内容）
                    if "\nSource:" in full_content:
                        answer = full_content.split('\nSource:')[0].strip()
                    else:
                        answer = full_content.strip()
                    
                    if answer and "[解析失败]" not in answer and "[查询失败]" not in answer and answer != "N/A":
                        answers.append(f"• {doc_name}: {answer[:100]}{'...' if len(answer) > 100 else ''}")
            
            if answers:
                for answer in answers[:5]:  # 只显示前5个答案
                    f.write(f"{answer}\n")
                if len(answers) > 5:
                    f.write(f"... and {len(answers) - 5} more\n")
            else:
                f.write("No valid answers found\n")
    
    print(f"📄 汇总报告已保存到: {report_path}")
    return report_path