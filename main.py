#!/usr/bin/env python3
"""
PDF to Markdown 转换及批量问答工具
主程序文件
"""

from config import parse_args, detect_device
from pdf_converter import convert_pdfs_to_markdown
from query_engine import query_all_documents
from utils import save_results_to_csv

def main():
    """主函数"""
    args = parse_args()
    
    print("🚀 PDF to Markdown 转换及批量问答工具")
    print("=" * 60)
    
    if args.mode in ['markdown', 'all']:
        print("\n🔄 开始PDF到Markdown转换...")
        # 检测设备
        device = detect_device(args)
        
        # 显示配置
        if args.verbose:
            print("⚙️  转换配置:")
            print(f"   输入文件夹: {args.input_folder}")
            print(f"   Markdown文件夹: {args.markdown_folder}")
            print(f"   设备: {device}")
            print(f"   格式化行: {args.format_lines}")
            print(f"   强制OCR: {args.force_ocr}")
            print("-" * 50)
        
        # 执行转换
        successful_markdowns = convert_pdfs_to_markdown(args, device)
        
        if not successful_markdowns and args.mode == 'all':
            print("❌ 没有成功转换的Markdown文件，跳过查询步骤")
            return
    
    if args.mode in ['query', 'all']:
        print("\n🔍 开始文档查询...")
        
        # 显示查询配置
        if args.verbose:
            print("⚙️  查询配置:")
            print(f"   Markdown文件夹: {args.markdown_folder}")
            print(f"   输出文件夹: {args.output_folder}")
            print(f"   API模型: {args.model}")
            print(f"   最大并发数: {args.max_workers}")
            print("-" * 50)
        
        # 执行查询
        all_results = query_all_documents(args)
        
        # 保存结果到CSV
        if all_results:
            save_results_to_csv(all_results, args.output_folder)
    
    print("\n🎉 所有任务完成！")

if __name__ == "__main__":
    main()