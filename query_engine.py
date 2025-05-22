import os
import glob
import re
from concurrent.futures import ProcessPoolExecutor
from openai import OpenAI
from tqdm import tqdm
from config import QUESTION_PATTERNS, QUESTION_IDS

def create_combined_prompt(markdown_content):
    """创建合并的提示词"""
    
    prompt_template = """Please analyze the provided research paper and answer the following questions. For each question, provide a concise answer followed by the relevant source text.

QUESTIONS:
1. Involved Stakeholder: What are the involved stakeholders (e.g., elderly people, caregivers, technical solution providers) in the study? Stakeholders must meet one of the following criteria: 1. Participate in experiments or studies; 2. Not participate directly but expressed opinions or perspectives (e.g., via interviews, focus groups); 3. Play a role in shaping the findings or conclusions of the paper.

2. Sample Size: What is the sample size of the study? For example, if 100 people participated and only 90 consented to data collection, the sample size is 90. For multi-study papers, specify the sample size for each study group.

3. Country: What is the country or region of the participants as explicitly stated in the paper (do not infer from the authors' affiliations)?

4. Age: What age-related information is provided in the study (e.g., age range, mean, or median age)?

5. Gender: What gender-related information is reported in the study?

6. Demographic Background: What demographic background information is reported? (For example, socioeconomic status, educational level, and living context for elderly people or working context for caregivers; also include any additional details such as language proficiency, professional background, or technology literacy if mentioned.)

7. Cognitive And Physical Impairment: What cognitive and physical impairments are described among the elderly participants? If standardized measurement tools were used, report the specific scores and the name of the scale; if qualitative terms (e.g., 'mild', 'severe') were used, report them accordingly.

8. Needs And Expectations: What are the explicitly stated or inferred needs and expectations of users, primarily elderly people and caregivers? This includes both directly expressed needs and user preferences accompanied by explanatory comments during interviews or post-trial reflections.

9. Application Context: What is the envisioned application context for the robot as explicitly mentioned in the paper?

10. Process Of The Care: What information is provided about the duration and stage of the care process? Specify whether the study involved a first encounter, short-term use, or long-term deployment, and include session duration and frequency if available.

11. Methodology: What research methodology was used in the study (e.g., qualitative interviews, quantitative surveys, randomized controlled trials)?

12. Care Type: What type of care is the study focused on?

13. Robot Type: What type of robot is used in the study? (If the paper uses terms like 'human-like' or 'animal-like', use those directly; otherwise, provide a short description of the robot's appearance.)

14. Robot Name: What is the name of the robot used in the study?

15. Design Goal: What design goals were set by the solution provider when designing the robot or its interaction functions?

16. Robot Concern Function: What functionalities of the robot were demonstrated, deployed, or introduced to users during the study?

17. Facilitating Functions: What specific robot functions or features are reported to enhance the user experience (i.e., positive features)? Please provide brief explanations for why these features are considered beneficial.

18. Inhibitory Functions: What specific robot functions or features are reported to hinder the user experience (i.e., negative features)? Please provide brief explanations for why these features are considered detrimental.

19. Stakeholder Facilitating Characteristics: What characteristics of the stakeholders are associated with better robot use, acceptance, or trust? Include brief explanations where available.

20. Stakeholder Inhibitory Characteristics: What characteristics of the stakeholders are associated with reduced robot use, lower acceptance, or lower trust? Include brief explanations where available.

21. Engagement: What evaluation of user engagement in the robot is reported in the study? This may include quantitative measurements (e.g., rating scales) or qualitative descriptions (e.g., 'high engagement', 'low acceptance', 'gradual trust development').

22. Acceptance: What evaluation of user acceptance trust in the robot is reported in the study? This may include quantitative measurements (e.g., rating scales) or qualitative descriptions (e.g., 'high engagement', 'low acceptance', 'gradual trust development').

23. Trust: What evaluation of user trust in the robot is reported in the study? This may include quantitative measurements (e.g., rating scales) or qualitative descriptions (e.g., 'high engagement', 'low acceptance', 'gradual trust development').

24. Key Findings: What are the key findings of the study, as typically summarized in the conclusion or discussion section?

25. Additional Info: What additional information is provided about the study, such as limitations or other relevant details?

26. Testing Context: What is the testing context of the study? (For example, was the test conducted in a lab, care home, hospital, private residence, or another setting?)

RESPONSE FORMAT:
Please respond using markdown headers for each question. Use the exact question IDs as headers, followed by your answer and source. Format exactly like this:

## Involved Stakeholder
[Your concise answer. If information is not available, write 'N/A']

Source: [Quote the relevant text from the paper]

## Sample Size
[Your concise answer. If information is not available, write 'N/A']

Source: [Quote the relevant text from the paper]

... continue for all 26 questions using their respective IDs as headers.

RESEARCH PAPER CONTENT:
{content}"""
    
    return prompt_template.format(content=markdown_content)

def query_document_with_combined_questions(markdown_path, client, model, verbose=False):
    """使用合并问题查询单个文档"""
    try:
        # 读取Markdown文件
        with open(markdown_path, 'r', encoding='utf-8') as f:
            markdown_content = f.read()
        
        # 创建合并的提示词
        combined_prompt = create_combined_prompt(markdown_content)
        
        if verbose:
            print(f"    发送查询请求...")
        
        # 发送请求到OpenAI
        response = client.chat.completions.create(
            model=model,
            messages=[
                {"role": "user", "content": combined_prompt}
            ],
            temperature=0.1,
            max_tokens=4000
        )
        
        result_text = response.choices[0].message.content
        
        if verbose:
            print(f"    ✅ 查询成功")
        
        return True, result_text
        
    except Exception as e:
        if verbose:
            print(f"    ❌ 查询失败: {e}")
        return False, str(e)

def parse_combined_response(response_text):
    """解析合并响应，提取各个问题的答案"""
    results = {}
    
    # 为每个问题创建灵活的正则表达式模式
    for display_name, question_id in QUESTION_PATTERNS:
        # 预先处理转义字符串，避免f-string中使用反斜杠
        escaped_display_name = re.escape(display_name)
        escaped_question_id = re.escape(question_id)
        flexible_name = escaped_display_name.replace(r"\ ", r"\s+")
        
        patterns_to_try = [
            # 标准格式: ## Display Name
            rf'##\s*{escaped_display_name}\s*\n(.*?)(?=\n\s*##|\Z)',
            # 全小写: ## display name  
            rf'##\s*{re.escape(display_name.lower())}\s*\n(.*?)(?=\n\s*##|\Z)',
            # 全大写: ## DISPLAY NAME
            rf'##\s*{re.escape(display_name.upper())}\s*\n(.*?)(?=\n\s*##|\Z)',
            # 下划线格式: ## display_name
            rf'##\s*{escaped_question_id}\s*\n(.*?)(?=\n\s*##|\Z)',
            # 混合格式: 允许额外的空格和标点
            rf'##\s*{flexible_name}\s*[:\s]*\n(.*?)(?=\n\s*##|\Z)',
        ]
        
        matched = False
        for pattern in patterns_to_try:
            match = re.search(pattern, response_text, re.DOTALL | re.IGNORECASE)
            if match:
                content = match.group(1).strip()
                
                # 更完整的Source分离逻辑
                # 匹配各种可能的Source格式
                source_patterns = [
                    r'\n\s*Source:\s*(.*?)(?=\n\s*$|\Z)',  # 标准格式: Source: xxx (行尾)
                    r'Source:\s*(.*?)(?=\n|$)',           # 行内Source: xxx
                    r'\n\s*source:\s*(.*?)(?=\n\s*$|\Z)', # 小写source (行尾)
                    r'source:\s*(.*?)(?=\n|$)',           # 行内小写source
                    r'\n\s*SOURCE:\s*(.*?)(?=\n\s*$|\Z)', # 大写SOURCE (行尾)
                    r'SOURCE:\s*(.*?)(?=\n|$)',           # 行内大写SOURCE
                ]
                
                source_found = False
                for source_pattern in source_patterns:
                    source_match = re.search(source_pattern, content, re.DOTALL | re.MULTILINE)
                    if source_match:
                        source = source_match.group(1).strip()
                        # 移除Source部分，获取纯答案
                        answer = re.sub(source_pattern, '', content, flags=re.DOTALL | re.MULTILINE).strip()
                        # 使用换行符分隔答案和Source
                        results[question_id] = f"{answer}\nSource: {source}"
                        source_found = True
                        break
                
                if not source_found:
                    # 如果没有找到Source，直接使用全部内容
                    results[question_id] = content
                
                matched = True
                break
        
        if not matched:
            results[question_id] = "[解析失败] - 无法从响应中提取答案"
    
    return results

def query_documents_wrapper(args_tuple):
    """并行查询文档的包装函数"""
    markdown_path, api_key, api_base, model, verbose = args_tuple
    
    try:
        # 创建OpenAI客户端
        client = OpenAI(
            api_key=api_key,
            base_url=api_base
        )
        
        doc_name = os.path.basename(markdown_path)
        
        if verbose:
            print(f"  🔄 查询文档: {doc_name}")
        
        # 查询文档
        success, response = query_document_with_combined_questions(
            markdown_path, client, model, verbose
        )
        
        if success:
            # 解析响应
            parsed_results = parse_combined_response(response)
            
            if verbose:
                print(f"  ✅ 完成: {doc_name}")
            
            return doc_name, True, parsed_results, None
        else:
            if verbose:
                print(f"  ❌ 失败: {doc_name}")
            return doc_name, False, None, response
            
    except Exception as e:
        doc_name = os.path.basename(markdown_path) if markdown_path else "未知文档"
        return doc_name, False, None, str(e)

def query_all_documents(args):
    """查询所有Markdown文档"""
    
    # 查找所有Markdown文件
    markdown_files = glob.glob(os.path.join(args.markdown_folder, "*.md"))
    
    if not markdown_files:
        print(f"❌ 在 {args.markdown_folder} 文件夹中没有找到Markdown文件")
        return
    
    print(f"📄 找到 {len(markdown_files)} 个Markdown文件")
    
    # API配置
    api_key = args.api_key or os.getenv('OPENAI_API_KEY')
    if not api_key:
        print("❌ 请提供OpenAI API密钥 (通过--api-key参数或OPENAI_API_KEY环境变量)")
        return
    
    # 准备查询参数
    query_args = [
        (md_path, api_key, args.api_base, args.model, args.verbose)
        for md_path in markdown_files
    ]
    
    print(f"🚀 使用 {args.max_workers} 个工作进程并行查询...")
    print("-" * 50)
    
    # 存储所有结果
    all_results = {}
    failed_queries = []
    
    # 并行执行查询
    with ProcessPoolExecutor(max_workers=args.max_workers) as executor:
        for doc_name, success, results, error in tqdm(
            executor.map(query_documents_wrapper, query_args),
            total=len(query_args),
            desc="查询进度"
        ):
            if success:
                # 构建结果字典
                doc_result = {"document": doc_name}
                doc_result.update(results)
                all_results[doc_name] = doc_result
            else:
                print(f"❌ {doc_name}: {error}")
                failed_queries.append((doc_name, error))
                # 为失败的查询添加占位符
                doc_result = {"document": doc_name}
                for question_id in QUESTION_IDS:
                    doc_result[question_id] = f"[查询失败] - {error}"
                all_results[doc_name] = doc_result
    
    # 输出统计
    print("\n" + "=" * 50)
    print("📊 查询完成统计:")
    print(f"✅ 成功查询: {len(all_results) - len(failed_queries)} 个文档")
    print(f"❌ 查询失败: {len(failed_queries)} 个文档")
    
    if failed_queries:
        print(f"\n❌ 失败的查询详情:")
        for doc_name, error in failed_queries:
            print(f"  • {doc_name}: {error}")
    
    return all_results