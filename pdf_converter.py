import os
import glob
import gc
import time
import threading
from marker.converters.pdf import PdfConverter
from marker.models import create_model_dict
from marker.output import text_from_rendered
import torch

# 全局锁，用于同步模型创建
_model_lock = threading.Lock()

def create_converter(config, thread_id=None):
    """创建PDF转换器"""
    with _model_lock:
        try:
            converter = PdfConverter(
                artifact_dict=create_model_dict()
            )
            
            if config.get('verbose', False):
                print(f"    [线程{thread_id}] 创建转换器成功")
            
            return converter
            
        except Exception as e:
            print(f"    [线程{thread_id}] 创建转换器失败: {e}")
            raise e

def convert_single_pdf(pdf_path, output_folder, config, device='cpu'):
    """转换单个PDF文件为Markdown"""
    result = {
        'success': False,
        'output_path': None,
        'error': None,
        'text_length': 0,
        'filename': os.path.basename(pdf_path)
    }
    
    converter = None
    start_time = time.time()
    
    try:
        if config.get('verbose', False):
            print(f"    使用设备: {device}")
        
        # 创建转换器
        converter = create_converter(config)
        
        # 内存清理
        gc.collect()
        if device == 'cuda' and torch.cuda.is_available():
            torch.cuda.empty_cache()
        elif device == 'mps' and torch.backends.mps.is_available():
            if hasattr(torch.mps, 'empty_cache'):
                torch.mps.empty_cache()
        
        # 转换PDF
        if config.get('verbose', False):
            print(f"    开始转换PDF...")
        
        rendered = converter(pdf_path)
        markdown_text, metadata, images = text_from_rendered(rendered)
        
        # 生成输出文件名
        filename = os.path.basename(pdf_path)
        base_name = os.path.splitext(filename)[0]
        output_path = os.path.join(output_folder, f"{base_name}.md")
        
        # 保存Markdown文件
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(markdown_text)
        
        if config.get('verbose', False):
            print(f"    ✅ Markdown保存成功")
            if images:
                print(f"    📷 检测到 {len(images)} 个图片（已忽略）")
        
        result['success'] = True
        result['output_path'] = output_path
        result['text_length'] = len(markdown_text)
        result['time_taken'] = time.time() - start_time
        
    except Exception as e:
        result['error'] = str(e)
        result['time_taken'] = time.time() - start_time
        if config.get('verbose', False):
            print(f"    ❌ 转换失败: {e}")
    
    finally:
        # 强制清理资源
        if converter:
            del converter
        
        # 内存清理
        for _ in range(2):
            gc.collect()
        
        if device == 'cuda' and torch.cuda.is_available():
            torch.cuda.empty_cache()
            torch.cuda.synchronize()
        elif device == 'mps' and torch.backends.mps.is_available():
            if hasattr(torch.mps, 'empty_cache'):
                torch.mps.empty_cache()
            if hasattr(torch.mps, 'synchronize'):
                torch.mps.synchronize()
    
    return result

def convert_pdfs_to_markdown(args, device):
    """批量转换PDF文件为Markdown"""
    
    # 创建输出文件夹
    os.makedirs(args.markdown_folder, exist_ok=True)
    
    # 查找所有PDF文件
    pdf_files = glob.glob(os.path.join(args.input_folder, "*.pdf"))
    pdf_files.extend(glob.glob(os.path.join(args.input_folder, "*.PDF")))
    
    if not pdf_files:
        print(f"❌ 在 {args.input_folder} 文件夹中没有找到PDF文件")
        return []
    
    print(f"📁 找到 {len(pdf_files)} 个PDF文件")
    
    if args.dry_run:
        print("🔍 试运行模式 - 将要处理的文件:")
        for i, pdf_path in enumerate(pdf_files, 1):
            print(f"  {i}. {os.path.basename(pdf_path)}")
        return []
    
    # 准备配置
    config = {
        'verbose': args.verbose,
        'format_lines': args.format_lines,
        'force_ocr': args.force_ocr,
    }
    
    print(f"📤 输出目录: {args.markdown_folder}")
    print("-" * 50)
    
    # 转换统计
    successful_conversions = []
    failed_conversions = []
    total_start_time = time.time()
    
    # 单线程处理PDF转换
    for i, pdf_path in enumerate(pdf_files, 1):
        filename = os.path.basename(pdf_path)
        print(f"[{i}/{len(pdf_files)}] 🔄 转换中: {filename}")
        
        result = convert_single_pdf(pdf_path, args.markdown_folder, config, device)
        
        if result['success']:
            print(f"  ✅ 成功 ({result['time_taken']:.1f}s)")
            if args.verbose:
                print(f"     📄 文本: {result['text_length']} 字符")
            successful_conversions.append(result['output_path'])
        else:
            print(f"  ❌ 失败: {result['error']}")
            failed_conversions.append((filename, result['error']))
    
    # 输出总结
    total_time = time.time() - total_start_time
    print("\n" + "=" * 50)
    print("📊 转换完成统计:")
    print(f"✅ 成功转换: {len(successful_conversions)} 个文件")
    print(f"❌ 转换失败: {len(failed_conversions)} 个文件") 
    print(f"⏱️  总耗时: {total_time:.1f}秒")
    if successful_conversions:
        print(f"📈 平均速度: {total_time/len(pdf_files):.1f}秒/文件")
    
    if failed_conversions:
        print(f"\n❌ 失败的文件详情:")
        for filename, error in failed_conversions:
            print(f"  • {filename}: {error}")
    
    return successful_conversions