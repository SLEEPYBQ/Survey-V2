import os
import glob
import re
import json
from datetime import datetime
from concurrent.futures import ProcessPoolExecutor
from openai import OpenAI
from tqdm import tqdm
from config import QUESTION_PATTERNS, QUESTION_IDS

def create_combined_prompt(markdown_content):
    """创建合并的提示词"""
    
    prompt_template = """Please analyze the provided research paper and answer the following questions. 

CRITICAL FORMAT REQUIREMENTS:
1. You MUST use the exact format shown below for EVERY question
2. Each question MUST start with ## followed by the exact question ID
3. The answer MUST start with "Answer: " on a new line
4. The source MUST start with "Source: " on a new line
5. DO NOT add any extra text, formatting, or explanations outside this format
6. If information is not available, write "Answer: N/A" and "Source: Not found in the paper"

EXACT FORMAT TEMPLATE (you must follow this precisely):
## question_id
Answer: [Your concise answer here]
Source: [Quote the relevant text from the paper]

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

RESPONSE FORMAT EXAMPLE:
## involved_stakeholder
Answer: Elderly individuals aged 65+, caregivers, and robotics experts
Source: Ten elderly individuals (four men and six women) aged 65 years or older participated

## sample_size
Answer: 20 elderly participants for preference evaluation, 10 for group interviews, and 10 robotics experts
Source: 20 prospective users aged 65+ participated in the preference evaluation

[Continue for all 26 questions using their exact question IDs]

IMPORTANT REMINDERS:
- Use the exact question IDs: involved_stakeholder, sample_size, country, age, gender, demographic_background, cognitive_and_physical_impairment, needs_and_expectations, application_context, process_of_the_care, methodology, care_type, robot_type, robot_name, design_goal, robot_concern_function, facilitating_functions, inhibitory_functions, stakeholder_facilitating_characteristics, stakeholder_inhibitory_characteristics, engagement, acceptance, trust, key_findings, additional_info, testing_context
- Each answer MUST start with "Answer: "
- Each source MUST start with "Source: "
- Do not use any other formatting

RESEARCH PAPER CONTENT:
{content}"""
    
    return prompt_template.format(content=markdown_content)

def save_raw_response(doc_name, response_text, raw_response_dir='raw_responses'):
    """保存LLM的原始响应到文件"""
    # 创建原始响应目录
    os.makedirs(raw_response_dir, exist_ok=True)
    
    # 生成文件名（移除.md扩展名，添加时间戳）
    base_name = os.path.splitext(doc_name)[0]
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"{base_name}_{timestamp}.txt"
    filepath = os.path.join(raw_response_dir, filename)
    
    # 保存原始响应
    with open(filepath, 'w', encoding='utf-8') as f:
        f.write(f"Document: {doc_name}\n")
        f.write(f"Timestamp: {timestamp}\n")
        f.write("="*80 + "\n\n")
        f.write(response_text)
    
    return filepath

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
        
        # 保存原始响应
        doc_name = os.path.basename(markdown_path)
        raw_response_path = save_raw_response(doc_name, result_text)
        
        if verbose:
            print(f"    ✅ 查询成功")
            print(f"    💾 原始响应已保存到: {raw_response_path}")
        
        return True, result_text
        
    except Exception as e:
        if verbose:
            print(f"    ❌ 查询失败: {e}")
        return False, str(e)

def parse_combined_response(response_text):
    """解析合并响应，提取各个问题的答案 - 使用简化的正则表达式"""
    results = {}
    
    # 简化的正则表达式 - 只匹配严格的格式
    # 匹配模式: ## question_id\nAnswer: xxx\nSource: xxx
    pattern = r'##\s*(\w+)\s*\n\s*Answer:\s*(.*?)\n\s*Source:\s*(.*?)(?=\n\s*##|\Z)'
    
    matches = re.findall(pattern, response_text, re.DOTALL | re.MULTILINE)
    
    # 将匹配结果转换为字典
    for question_id, answer, source in matches:
        # 清理答案和源文本中的多余空白
        answer = answer.strip()
        source = source.strip()
        
        # 组合答案和源
        results[question_id] = f"{answer}\nSource: {source}"
    
    # 检查是否所有问题都被解析
    missing_questions = []
    for _, question_id in QUESTION_PATTERNS:
        if question_id not in results:
            missing_questions.append(question_id)
            results[question_id] = "[解析失败] - 无法从响应中提取答案"
    
    if missing_questions and len(missing_questions) < 26:  # 如果只是部分失败
        # 尝试备用解析方法 - 更宽松的匹配
        for question_id in missing_questions:
            # 尝试匹配变体格式
            alt_patterns = [
                # 标准格式但可能有细微差异
                rf'##\s*{re.escape(question_id)}\s*\n(.*?)(?=\n\s*##|\Z)',
                # 可能Answer和Source在同一段落
                rf'##\s*{re.escape(question_id)}\s*\n\s*Answer:\s*(.*?)\s*Source:\s*(.*?)(?=\n\s*##|\Z)',
            ]
            
            for alt_pattern in alt_patterns:
                match = re.search(alt_pattern, response_text, re.DOTALL | re.MULTILINE | re.IGNORECASE)
                if match:
                    if len(match.groups()) == 1:
                        # 整段匹配，需要分离Answer和Source
                        content = match.group(1).strip()
                        answer_match = re.search(r'Answer:\s*(.*?)(?=Source:|$)', content, re.DOTALL)
                        source_match = re.search(r'Source:\s*(.*?)$', content, re.DOTALL)
                        
                        if answer_match and source_match:
                            answer = answer_match.group(1).strip()
                            source = source_match.group(1).strip()
                            results[question_id] = f"{answer}\nSource: {source}"
                            break
                    else:
                        # 已经分离的Answer和Source
                        answer = match.group(1).strip()
                        source = match.group(2).strip()
                        results[question_id] = f"{answer}\nSource: {source}"
                        break
    
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
            
            # 验证解析结果
            parse_failures = sum(1 for v in parsed_results.values() if "[解析失败]" in v)
            if parse_failures > 0:
                print(f"  ⚠️  {doc_name}: {parse_failures}个问题解析失败")
            
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
    
    # 创建原始响应目录
    os.makedirs('raw_responses', exist_ok=True)
    print(f"📁 原始响应将保存到: raw_responses/")
    
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
    parse_stats = {'total': 0, 'failures': 0}
    
    # 并行执行查询
    with ProcessPoolExecutor(max_workers=args.max_workers) as executor:
        for doc_name, success, results, error in tqdm(
            executor.map(query_documents_wrapper, query_args),
            total=len(query_args),
            desc="查询进度"
        ):
            if success:
                # 统计解析失败
                for v in results.values():
                    if "[解析失败]" in v:
                        parse_stats['failures'] += 1
                parse_stats['total'] += len(results)
                
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
    
    if parse_stats['total'] > 0:
        success_rate = (parse_stats['total'] - parse_stats['failures']) / parse_stats['total'] * 100
        print(f"📈 解析成功率: {success_rate:.1f}% ({parse_stats['total'] - parse_stats['failures']}/{parse_stats['total']} 个问题)")
    
    if failed_queries:
        print(f"\n❌ 失败的查询详情:")
        for doc_name, error in failed_queries[:5]:  # 只显示前5个错误
            print(f"  • {doc_name}: {error}")
        if len(failed_queries) > 5:
            print(f"  ... 还有 {len(failed_queries) - 5} 个失败的查询")
    
    # 调试：如果有解析失败，显示一些细节
    if parse_stats['failures'] > 0:
        print(f"\n⚠️  解析失败调试信息:")
        # 找出哪些问题最容易失败
        question_failure_count = {}
        for doc_result in all_results.values():
            for question_id in QUESTION_IDS:
                if question_id in doc_result and "[解析失败]" in doc_result[question_id]:
                    question_failure_count[question_id] = question_failure_count.get(question_id, 0) + 1
        
        if question_failure_count:
            sorted_failures = sorted(question_failure_count.items(), key=lambda x: x[1], reverse=True)
            print("  最常失败的问题:")
            for question_id, count in sorted_failures[:5]:
                print(f"    • {question_id}: {count}次失败")
    
    return all_results