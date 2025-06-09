## 使用方法
# # 1. 无参数 - 默认处理 results_bq/query_results_latest.xlsx
# python simple_sort.py

# # 2. 指定文件夹 - 自动拼接 query_results_latest.xlsx
# python simple_sort.py results_bq
# python simple_sort.py results_test
# python simple_sort.py /path/to/folder

# # 3. 指定具体文件
# python simple_sort.py results_bq/query_results_latest.xlsx
# python simple_sort.py /path/to/file.xlsx

# # 4. 查看帮助
# python simple_sort.py --help

#!/usr/bin/env python3
import pandas as pd
import re
import argparse
from pathlib import Path

def extract_number(document_name):
    """从document名称中提取开头的数字"""
    match = re.match(r'^(\d+)', str(document_name))
    return int(match.group(1)) if match else 0

def sort_by_document_number(file_path):
    """按document开头的数字排序"""
    # 读取文件
    df = pd.read_excel(file_path)
    
    # 提取数字并创建排序键
    df['sort_key'] = df['document'].apply(extract_number)
    
    # 按数字和content_type排序
    sorted_df = df.sort_values(['sort_key', 'content_type']).drop('sort_key', axis=1)
    
    # 保存文件
    output_path = Path(file_path).parent / f"{Path(file_path).stem}_sorted.xlsx"
    sorted_df.to_excel(output_path, index=False)
    
    print(f"排序完成，保存到: {output_path}")
    return output_path

def main():
    parser = argparse.ArgumentParser(description='按document开头数字排序Excel文件')
    parser.add_argument('path', nargs='?', default='results_bq',
                       help='Excel文件路径或包含query_results_latest.xlsx的文件夹路径 (默认: results_bq)')
    
    args = parser.parse_args()
    
    # 判断输入的是文件还是文件夹
    input_path = Path(args.path)
    
    if input_path.is_dir():
        # 如果是文件夹，自动拼接query_results_latest.xlsx
        file_path = input_path / 'query_results_latest.xlsx'
    elif input_path.is_file():
        # 如果是文件，直接使用
        file_path = input_path
    else:
        # 如果路径不存在，尝试作为文件夹处理
        file_path = input_path / 'query_results_latest.xlsx'
    
    # 检查文件是否存在
    if not file_path.exists():
        print(f"错误: 文件不存在 {file_path}")
        return
    
    print(f"处理文件: {file_path}")
    sort_by_document_number(file_path)

if __name__ == "__main__":
    main() 