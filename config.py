import argparse
import os
import torch

def parse_args():
    """解析命令行参数"""
    parser = argparse.ArgumentParser(description='PDF to Markdown 转换及批量问答工具')
    
    # 基本参数
    parser.add_argument('--input-folder', '-i', default='pdfs', 
                       help='输入PDF文件夹路径 (默认: pdfs)')
    parser.add_argument('--markdown-folder', '-m', default='markdowns', 
                       help='Markdown文件夹路径 (默认: markdowns)')
    parser.add_argument('--output-folder', '-o', default='results', 
                       help='输出结果文件夹路径 (默认: results)')
    
    # 模式选择
    parser.add_argument('--mode', default='all', choices=['markdown', 'query', 'all'],
                       help='执行模式: markdown(只生成markdown), query(只查询), all(生成markdown后查询) (默认: all)')
    
    # 设备参数 (用于PDF转换)
    parser.add_argument('--device', default='auto', choices=['auto', 'cpu', 'cuda', 'mps'],
                       help='指定设备 (默认: auto自动检测)')
    parser.add_argument('--no-gpu', action='store_true',
                       help='强制使用CPU，不使用任何GPU')
    
    # 转换参数
    parser.add_argument('--format-lines', action='store_true',
                       help='格式化文本行，提高数学公式质量')
    parser.add_argument('--force-ocr', action='store_true',
                       help='强制OCR处理整个文档')
    
    # OpenAI API参数
    parser.add_argument('--api-key', default='xxx',
                       help='OpenAI API密钥')
    parser.add_argument('--api-base', default='https://api.openai-proxy.org/v1',
                       help='OpenAI API Base URL')
    parser.add_argument('--model', default='deepseek-chat',
                       help='使用的模型')
    
    # 并发参数
    parser.add_argument('--max-workers', type=int, default=8,
                       help='查询时的最大并发数 (默认: 4)')
    
    # 其他参数
    parser.add_argument('--verbose', '-v', action='store_true',
                       help='显示详细输出')
    parser.add_argument('--dry-run', action='store_true',
                       help='试运行，只显示要处理的文件但不实际转换')
    
    return parser.parse_args()

def detect_device(args):
    """检测和设置设备"""
    if args.no_gpu or args.device == 'cpu':
        device = 'cpu'
        print("💻 使用CPU模式")
    elif args.device == 'cuda':
        if torch.cuda.is_available():
            device = 'cuda'
            print("🚀 使用CUDA GPU模式")
        else:
            device = 'cpu'
            print("⚠️  CUDA不可用，回退到CPU模式")
    elif args.device == 'mps':
        if torch.backends.mps.is_available():
            device = 'mps'
            print("🍎 使用MPS（苹果GPU）模式")
        else:
            device = 'cpu'
            print("⚠️  MPS不可用，回退到CPU模式")
    else:  # auto
        if torch.cuda.is_available():
            device = 'cuda'
            print("🚀 自动检测到CUDA GPU，使用CUDA模式")
        elif torch.backends.mps.is_available():
            device = 'mps'
            print("🍎 自动检测到MPS，使用苹果GPU模式")
        else:
            device = 'cpu'
            print("💻 使用CPU模式")
    
    # 设置环境变量
    os.environ['TORCH_DEVICE'] = device
    return device

# 问题ID列表 - 用于CSV列名（使用下划线格式，与提示词中的格式一致）
QUESTION_IDS = [
    "involved_stakeholder", "sample_size", "country", "age", "gender",
    "demographic_background", "cognitive_and_physical_impairment", "needs_and_expectations",
    "application_context", "process_of_the_care", "methodology", "care_type",
    "robot_type", "robot_name", "design_goal", "robot_concern_function",
    "facilitating_functions", "inhibitory_functions", "stakeholder_facilitating_characteristics",
    "stakeholder_inhibitory_characteristics", "engagement", "acceptance", "trust",
    "key_findings", "additional_info", "testing_context"
]

# 问题显示名称和对应ID的映射（保持向后兼容）
QUESTION_PATTERNS = [
    ("Involved Stakeholder", "involved_stakeholder"),
    ("Sample Size", "sample_size"),
    ("Country", "country"),
    ("Age", "age"),
    ("Gender", "gender"),
    ("Demographic Background", "demographic_background"),
    ("Cognitive And Physical Impairment", "cognitive_and_physical_impairment"),
    ("Needs And Expectations", "needs_and_expectations"),
    ("Application Context", "application_context"),
    ("Process Of The Care", "process_of_the_care"),
    ("Methodology", "methodology"),
    ("Care Type", "care_type"),
    ("Robot Type", "robot_type"),
    ("Robot Name", "robot_name"),
    ("Design Goal", "design_goal"),
    ("Robot Concern Function", "robot_concern_function"),
    ("Facilitating Functions", "facilitating_functions"),  
    ("Inhibitory Functions", "inhibitory_functions"),
    ("Stakeholder Facilitating Characteristics", "stakeholder_facilitating_characteristics"),
    ("Stakeholder Inhibitory Characteristics", "stakeholder_inhibitory_characteristics"),
    ("Engagement", "engagement"),
    ("Acceptance", "acceptance"),
    ("Trust", "trust"),
    ("Key Findings", "key_findings"),
    ("Additional Info", "additional_info"),
    ("Testing Context", "testing_context")
]