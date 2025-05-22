import os
import csv
from config import QUESTION_IDS

def save_results_to_csv(all_results, output_dir):
    """保存结果到CSV文件"""
    
    # 创建输出目录
    os.makedirs(output_dir, exist_ok=True)
    
    # 构建CSV的字段名（表头）- 与静态提示词中的问题顺序一致
    fieldnames = ['document'] + QUESTION_IDS
    
    # 保存路径
    csv_path = os.path.join(output_dir, "query_results.csv")
    
    # 将结果保存为CSV
    with open(csv_path, 'w', newline='', encoding='utf-8') as csvfile:
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
        writer.writeheader()
        
        # 写入每个文档的所有问题结果
        for doc_name, results in all_results.items():
            writer.writerow(results)
    
    print(f"\n💾 查询结果已保存到: {csv_path}")
    return csv_path