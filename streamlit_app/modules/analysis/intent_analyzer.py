import os
import json
import logging
import time
import traceback  # 添加traceback导入
import streamlit as st
from datetime import datetime
from typing import Dict, Any

from streamlit_app.config.config import get_config, TARGET_GROUPS, SELLING_POINTS, PRODUCT_TYPES, BRAND_KEYWORDS, get_semantic_segment_types, get_semantic_type_definitions, DEFAULT_SEMANTIC_SEGMENT_TYPES
from sentence_transformers import SentenceTransformer, util
import torch

# 设置日志
logger = logging.getLogger(__name__)

class SemanticAnalyzer:
    """语义分析器，使用DeepSeek模型进行语义理解"""
    
    def __init__(self, api_key=None, base_url=None, model="deepseek-chat"):
        """初始化语义分析器"""
        # 获取配置信息
        config = get_config()
        self.api_key = api_key or config.get("api_key") or os.environ.get("DEEPSEEK_API_KEY")
        self.base_url = base_url or "https://api.deepseek.com"
        self.model = model
        
        # 检查是否有API密钥
        if not self.api_key:
            logger.warning("缺少API密钥，使用测试模式")
            self.api_key = "sk-test-api-key-for-development-only"
        
        # 母婴奶粉领域的专业术语和同义词映射
        self.domain_terms = {
            "免疫力": ["自御力", "抵抗力", "抵抗能力", "保护力", "自身保护力", "抵御能力"],
            "过敏": ["过敏反应", "过敏现象", "敏感", "食物过敏", "蛋白过敏"],
            "便秘": ["大便干", "排便困难", "排便不畅", "肠胃不适"],
            "腹泻": ["拉肚子", "肚子不舒服", "水便", "消化不良", "消化问题"],
            "配方": ["奶粉配方", "牛奶配方", "营养配方", "特殊配方"],
            "母乳": ["母乳喂养", "纯母乳", "母奶"],
            "奶粉": ["配方奶", "牛奶粉", "婴儿奶粉", "配方奶粉"],
            "混合喂养": ["混喂", "混合喂奶", "母乳+奶粉", "混养"]
        }
        
        logger.info(f"语义分析器初始化完成，使用模型: {model}")
        
        # 导入requests库
        try:
            import requests
            self.requests = requests
        except ImportError:
            logger.error("请安装requests库: pip install requests")
            raise ImportError("缺少必要的requests库，请使用pip install requests安装")
        
        # 检查配置是否禁用了sentence-transformer
        self.similarity_model = None
        use_sentence_transformer = config.get("use_sentence_transformer", False)
        
        if not use_sentence_transformer:
            logger.info("根据配置已禁用SentenceTransformer模型，将使用difflib进行相似度计算")
            return
            
        # 初始化sentence-transformer模型（仅在配置允许的情况下）
        try:
            # 使用一个通用的多语言或中文模型，确保能处理中文
            # 'paraphrase-multilingual-MiniLM-L12-v2' 是一个不错的选择，支持多种语言包括中文
            self.similarity_model_name = 'paraphrase-multilingual-MiniLM-L12-v2'
            
            # 设置离线模式，避免下载模型导致的连接问题
            os.environ['HF_DATASETS_OFFLINE'] = '1'
            os.environ['TRANSFORMERS_OFFLINE'] = '1'
            
            device = 'cuda' if torch.cuda.is_available() else 'cpu'
            
            # 尝试加载模型，如果失败则跳过，不阻止程序运行
            try:
                from sentence_transformers import SentenceTransformer
                # 使用本地模型路径
                local_model_path = config.get("sentence_transformer_local_path")
                if local_model_path and os.path.exists(local_model_path):
                    logger.info(f"使用本地模型路径: {local_model_path}")
                    self.similarity_model = SentenceTransformer(self.similarity_model_name, cache_folder=local_model_path, device=device)
                else:
                    logger.warning(f"本地模型路径不存在: {local_model_path}，尝试从默认位置加载")
                    self.similarity_model = SentenceTransformer(self.similarity_model_name, device=device)
                logger.info(f"文本相似度模型 {self.similarity_model_name} 初始化完成，使用设备: {device}")
            except Exception as e:
                logger.error(f"初始化文本相似度模型失败: {e}")
                logger.warning("将使用备用方法进行相似度计算")
                self.similarity_model = None
        except Exception as e:
            logger.error(f"初始化文本相似度模型时发生异常: {e}")
            self.similarity_model = None
    
    def expand_query_with_synonyms(self, query):
        """使用同义词扩展查询内容"""
        expanded_terms = []
        for term, synonyms in self.domain_terms.items():
            if term in query:
                expanded_terms.append(term)
                expanded_terms.extend(synonyms)
            else:
                for synonym in synonyms:
                    if synonym in query:
                        expanded_terms.append(term)
                        expanded_terms.extend(synonyms)
                        break
        
        return list(set(expanded_terms))  # 去重
    
    def analyze_semantic_match(self, transcript, query, context=None):
        """
        分析文本与查询的语义匹配度
        
        Args:
            transcript: 待分析的文本
            query: 用户查询内容
            context: 附加上下文信息 (目标人群、产品类型等)
            
        Returns:
            匹配分数和匹配细节
        """
        if not query:
            return 1.0, {"reason": "无查询内容，默认匹配"}
        
        # 使用同义词扩展查询
        expanded_terms = self.expand_query_with_synonyms(query)
        expanded_query_info = f"扩展关键词: {', '.join(expanded_terms)}" if expanded_terms else ""
        
        system_prompt = """你是一个母婴行业专业视频内容分析专家，特别精通婴幼儿营养、喂养和奶粉产品信息。
你的任务是深入理解视频内容与用户查询之间的语义关联，提供专业的匹配分析。

你需要考虑以下因素:
1. 内容直接相关性 - 视频是否明确讨论了查询主题
2. 语义关联性 - 视频内容是否包含与查询相关的概念、术语或同义表达
3. 解决方案匹配度 - 视频是否提供了与用户查询相关的解决方案或建议
4. 目标人群适配性 - 视频内容是否适合查询所针对的人群
5. 产品适配性 - 视频中讨论的产品是否符合查询需求

你应当理解母婴行业的专业术语和同义词,例如:
- "免疫力"相关: 自御力、抵抗力、保护力等
- "配方"相关: 奶粉配方、营养配方、特殊配方等
- "消化问题"相关: 便秘、腹泻、肠胃不适、排便等

对于品牌术语,要特别注意:
- "启赋水奶": 指启赋品牌的即饮型液态奶
- "启赋蕴淳": 指启赋品牌的特定系列奶粉
- "HMO": 指人乳低聚糖,是一种重要的母乳成分
- "A2蛋白": 指一种特定的牛奶蛋白类型
"""
        
        # 准备上下文信息
        context_str = ""
        if context:
            if context.get("target_audience"):
                context_str += f"目标人群: {context['target_audience']}\n"
            if context.get("product_type") and context.get("product_type") != "-":
                context_str += f"产品类型: {context['product_type']}\n"
            if context.get("selling_points"):
                context_str += f"产品卖点: {', '.join(context['selling_points'])}\n"
        
        user_prompt = f"""
请深入分析以下视频内容转录文本，评估其与用户查询意图的匹配程度:

用户查询: {query}
{expanded_query_info if expanded_query_info else ""}

相关上下文:
{context_str if context_str else "无特定上下文"}

视频转录文本:
{transcript}

请从多个维度评估匹配度，返回一个详细的JSON格式分析结果:
{{
  "match_score": 0.85,  // 总体匹配分数，0-1之间
  "dimension_scores": {{
    "content_relevance": 0.9,  // 内容相关性
    "semantic_coherence": 0.8,  // 语义一致性
    "solution_fit": 0.7,  // 解决方案匹配度
    "audience_fit": 0.9,  // 目标人群匹配度
    "product_fit": 0.85   // 产品匹配度
  }},
  "matching_keywords": ["关键词1", "关键词2"],  // 匹配到的关键词
  "reason": "详细说明匹配原因，包括为什么这段内容与查询相关",
  "recommendation": "对于这段内容是否推荐给用户的专业建议"
}}

只返回JSON格式的分析结果，不包含其他说明。确保分析紧密结合母婴和奶粉领域的专业理解。
"""

        try:
            # 确保API密钥已设置
            if not self.api_key:
                logger.warning("缺少API密钥，使用测试模式")
                self.api_key = "sk-test-api-key-for-development-only"
                
            # 实际调用API
            headers = {
                "Content-Type": "application/json",
                "Authorization": f"Bearer {self.api_key}"
            }
            
            # 构建消息
            data = {
                "model": self.model,
                "messages": [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                "temperature": 0.1,  # 低温度使输出更确定性
                "max_tokens": 1500
            }
            
            # 调用API
            response = self.requests.post(
                f"{self.base_url}/v1/chat/completions", 
                headers=headers, 
                json=data,
                timeout=30
            )
            response.raise_for_status()
            result = response.json()
            
            # 解析结果
            content = result['choices'][0]['message']['content']
            logger.info("DeepSeek API调用成功")
            
            # 尝试解析JSON响应
            try:
                # 移除可能的Markdown代码块标记
                if "```json" in content and "```" in content:
                    content = content.split("```json")[1].split("```")[0].strip()
                elif "```" in content:
                    content = content.split("```")[1].split("```")[0].strip()
                
                result_json = json.loads(content)
                match_score = result_json.get("match_score", 0.0)
                
                # 提取其他有用信息
                dimension_scores = result_json.get("dimension_scores", {})
                matching_keywords = result_json.get("matching_keywords", [])
                reason = result_json.get("reason", "")
                recommendation = result_json.get("recommendation", "")
                
                details = {
                    "dimension_scores": dimension_scores,
                    "matching_keywords": matching_keywords,
                    "reason": reason,
                    "recommendation": recommendation
                }
                
                return match_score, details
                
            except json.JSONDecodeError as e:
                logger.error(f"无法解析模型响应为JSON: {content}")
                logger.error(f"错误信息: {str(e)}")
                return 0.5, {"reason": f"解析错误，使用默认分数。原始响应: {content[:100]}..."}
                
        except Exception as e:
            logger.error(f"调用DeepSeek模型时出错: {str(e)}")
            raise

    def calculate_similarity(self, text1: str, text2: str) -> float:
        """
        计算两个文本之间的相似度。
        如果已初始化 SentenceTransformer 模型则使用它，否则使用 difflib 进行计算。
        
        Args:
            text1: 第一个文本
            text2: 第二个文本
            
        Returns:
            相似度分数 (0.0-1.0)
        """
        if not text1 or not text2:
            return 0.0
        
        # 如果sentence-transformer模型可用，使用它
        if self.similarity_model:
            try:
                from sentence_transformers import util
                embeddings = self.similarity_model.encode([text1, text2], convert_to_tensor=True)
                cosine_scores = util.pytorch_cos_sim(embeddings[0], embeddings[1])
                similarity = cosine_scores.item()
                logger.debug(f"使用SentenceTransformer计算文本相似度: '{text1[:50]}...' vs '{text2[:50]}...' = {similarity:.4f}")
                return similarity
            except Exception as e:
                logger.error(f"使用sentence-transformer计算文本相似度时出错: {e}")
                logger.info("回退到difflib计算相似度...")
                # 如果出错，回退到基本方法
        else:
            logger.debug("SentenceTransformer模型未初始化，使用difflib计算相似度...")
        
        # 基本相似度计算方法
        try:
            # 导入difflib库用于字符串相似度计算
            import difflib
            # 使用SequenceMatcher计算相似度
            similarity = difflib.SequenceMatcher(None, text1, text2).ratio()
            logger.debug(f"使用difflib计算文本相似度: '{text1[:50]}...' vs '{text2[:50]}...' = {similarity:.4f}")
            return similarity
        except Exception as e:
            logger.error(f"使用difflib计算文本相似度时出错: {e}")
            return 0.0

    def _chat_completion(self, messages, model=None):
        """
        调用DeepSeek API执行聊天请求。

        Args:
            messages: 消息列表，格式为 [{"role": "system", "content": "..."}, {"role": "user", "content": "..."}]
            model: 要使用的模型，如果未指定则使用初始化时设置的模型

        Returns:
            API响应的JSON对象
        """
        if not self.api_key:
            logger.warning("_chat_completion: 缺少API密钥，使用测试模式")
            self.api_key = "sk-test-api-key-for-development-only"
            
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.api_key}"
        }
        
        data = {
            "model": model or self.model,
            "messages": messages,
            "temperature": 0.1,  # 低温度使输出更确定性
            "max_tokens": 1500
        }
        
        try:
            response = self.requests.post(
                f"{self.base_url}/v1/chat/completions", 
                headers=headers, 
                json=data,
                timeout=45
            )
            response.raise_for_status()
            return response.json()
        except Exception as e:
            logger.error(f"调用DeepSeek API时出错: {str(e)}")
            # 返回一个模拟的最小响应，以便调用代码可以继续运行
            return {
                "choices": [
                    {
                        "message": {
                            "content": '{"target_audience": [], "product_type": []}'
                        }
                    }
                ]
            }

    def analyze_video_summary(self, full_transcript: str) -> Dict[str, Any]:
        """
        使用DeepSeek模型分析视频完整转录文本，提取目标人群。

        Args:
            full_transcript: 完整的视频转录文本。

        Returns:
            一个包含分析结果的字典，例如:
            {
                "target_audience": ["人群1", "人群2"]
            }
            如果分析失败则返回空字典。
        """
        if not full_transcript:
            logger.warning("完整的转录文本为空，无法进行视频摘要分析。")
            return {}

        import json # 确保导入json
        # 从config中导入TARGET_GROUPS，以便在提示词中使用
        from streamlit_app.config.config import TARGET_GROUPS

        target_groups_json_array_for_prompt = json.dumps(TARGET_GROUPS, ensure_ascii=False)

        # 使用f-string结合多行字符串来构建SYSTEM_PROMPT_TEMPLATE
        # 注意：在f-string中要表示字面量的花括号 { 或 }，需要使用双花括号 {{ 或 }}
        SYSTEM_PROMPT_TEMPLATE = f'''你是一个专业的母婴视频内容分析师，擅长精确识别视频的目标人群。

你的任务是根据视频转录文本，从预定义的目标人群列表中选择**唯一一个最匹配**的分类。

目标人群列表及其详细定义：{target_groups_json_array_for_prompt}

**人群判断指导原则：**

1. **孕期妈妈**：
   - 关键词：怀孕、孕期、待产包、产检、建档、准妈妈、卸货、分娩、生产、产科
   - 场景：讨论孕期营养、待产准备、产前产后护理、新生儿喂养准备
   - 时间节点：怀孕期间、分娩前后、产后初期（0-42天）

2. **二胎妈妈**：
   - 关键词：二胎、老大、老二、两个孩子、大宝、二宝、再次怀孕
   - 场景：比较两胎经验、多孩子养育、二胎备孕/怀孕

3. **混养妈妈**：
   - 关键词：混合喂养、混喂、亲喂、奶粉混合、母乳不足、奶量不够
   - 场景：母乳与奶粉结合喂养、奶水不足补充

4. **新手爸妈**：
   - 关键词：新手、没有经验、第一次、新生儿、不知道怎么、学习、初次
   - 场景：初为父母、缺乏育儿经验、学习喂养知识
   - 包含：新手爸爸、新手妈妈、初次育儿的父母

5. **贵妇妈妈**：
   - 关键词：高端、奢华、精致、品质、贵、高价、进口、顶级
   - 场景：追求高品质产品、注重品牌档次、消费能力强

**优先级判断规则（按重要性排序）：**
1. 如果同时匹配多个人群，按以下优先级选择：
   - "二胎妈妈" > "孕期妈妈" > "混养妈妈" > "贵妇妈妈" > "新手爸妈"
2. 如果提到"刚生完"、"产后"、"新生宝宝"、"出生后"等产后早期关键词，优先考虑"孕期妈妈"
3. 如果明确提到"二胎"、"老大老二"等多孩经验，优先选择"二胎妈妈"
4. 如果明确提到"混合喂养"、"奶水不足"等，优先选择"混养妈妈"
5. 如果强调"高端"、"奢华"等品质追求，优先选择"贵妇妈妈"
6. 其他情况或无明确特征时，选择"新手爸妈"

**重要要求：**
- **必须且只能**选择一个最匹配的人群
- 不允许返回多个人群或空数组
- 必须基于内容特征进行判断，不能随意选择

输出格式：
{{{{
  "target_audience": "从上述列表中选择的唯一一个人群分类"
}}}}
'''

        # 准备用户提示模板
        user_prompt = f"""请仔细分析以下视频转录文本，识别出**唯一一个最匹配**的目标人群：

--- 转录文本开始 ---
{full_transcript}
--- 转录文本结束 ---

分析步骤：
1. 仔细阅读转录文本，识别关键词和场景描述
2. 对照人群判断指导原则，找出最匹配的人群特征
3. 如果匹配多个人群，按照优先级规则选择最重要的一个
4. 从目标人群列表中选择**唯一一个**最合适的分类
5. 确保必须选择一个人群，不能返回空值

重要提醒：
- 只能返回一个目标人群，不能返回多个
- 必须是预定义列表中的人群名称
- 基于内容特征做出最佳判断

请以JSON格式输出分析结果，确保target_audience字段是单个字符串值。
"""

        # 发送分析请求
        try:
            response = self._chat_completion(
                messages=[
                    {"role": "system", "content": SYSTEM_PROMPT_TEMPLATE},
                    {"role": "user", "content": user_prompt}
                ],
                model="deepseek-chat"
            )
            
            # 从响应中获取JSON格式结果
            if response and "choices" in response and response["choices"]:
                result_text = response["choices"][0].get("message", {}).get("content", "")
                logger.debug(f"DeepSeek API (analyze_video_summary) 原始响应: {result_text[:500]}...")
                
                # 尝试提取和解析JSON数据
                import re
                json_match = re.search(r'```json\s*([\s\S]*?)\s*```', result_text)
                if json_match:
                    json_str = json_match.group(1)
                else:
                    # 如果没有Markdown代码块，则尝试直接解析整个文本
                    json_str = result_text
                
                try:
                    result_dict = json.loads(json_str)
                    # 只返回目标人群信息
                    return {
                        "target_audience": result_dict.get("target_audience", "")
                    }
                except json.JSONDecodeError as e:
                    logger.error(f"JSON解析失败: {e}, 原始文本: {json_str[:500]}...")
                    
                    # 尝试修复双花括号问题
                    try:
                        # 移除开头和结尾的多余花括号
                        cleaned_json = json_str.strip()
                        if cleaned_json.startswith('{{') and cleaned_json.endswith('}}'):
                            cleaned_json = cleaned_json[1:-1]  # 移除外层花括号
                            logger.info(f"尝试修复双花括号JSON格式: {cleaned_json[:200]}...")
                            result_dict = json.loads(cleaned_json)
                            return {
                                "target_audience": result_dict.get("target_audience", "")
                            }
                    except json.JSONDecodeError as e2:
                        logger.error(f"修复双花括号后仍然JSON解析失败: {e2}")
                    
                    # 如果JSON解析完全失败，尝试正则表达式提取目标人群
                    try:
                        import re
                        # 尝试匹配 "target_audience": ["xxx", "yyy"] 格式
                        pattern = r'"target_audience"\s*:\s*\[(.*?)\]'
                        match = re.search(pattern, json_str, re.DOTALL)
                        if match:
                            audience_str = match.group(1)
                            # 提取引号内的内容
                            audience_pattern = r'"([^"]+)"'
                            audiences = re.findall(audience_pattern, audience_str)
                            logger.info(f"通过正则表达式提取到目标人群: {audiences}")
                            return {
                                "target_audience": audiences[0] if audiences else ""
                            }
                    except Exception as e3:
                        logger.error(f"正则表达式提取目标人群失败: {e3}")
                    
                    return {}
            
            # 如果解析失败，返回空结果
            logger.error(f"无法从DeepSeek响应中提取结构化数据: {response}")
            return {}
            
        except Exception as e:
            logger.error(f"视频内容分析失败: {str(e)}")
            return {}

    def segment_transcript_by_intent(self, srt_file_path: str) -> list:
        """
        使用DeepSeek模型将SRT文件内容按意图划分为语义区块。

        Args:
            srt_file_path: SRT字幕文件的路径。

        Returns:
            一个语义区块列表，每个区块是一个字典，包含:
            'semantic_type' (str): 来自 SEMANTIC_SEGMENT_TYPES 的类型。
            'text' (str): 该语义区块的文本内容 (由SRT行拼接而成)。
            'asr_matched_text' (str): 与 'text' 相同，因为直接来自SRT。
            'start_time' (float): 开始时间 (秒)。
            'end_time' (float): 结束时间 (秒)。
            如果LLM分析失败，则返回空列表。
        """
        if not srt_file_path or not os.path.exists(srt_file_path):
            logger.warning(f"SRT文件路径无效或文件不存在: {srt_file_path}，无法进行语义分段。")
            return []

        # 1. 读取并解析SRT文件
        srt_entries = []
        try:
            with open(srt_file_path, 'r', encoding='utf-8') as f:
                content = f.read().strip()
            
            srt_blocks_raw = content.split('\n\n')
            entry_id_counter = 1
            for block_raw in srt_blocks_raw:
                lines = block_raw.strip().split('\n')
                if len(lines) >= 2:
                    try:
                        time_line_index = 0
                        if lines[0].isdigit() and len(lines) >=3:
                             time_line_index = 1
                        
                        if '-->' not in lines[time_line_index]:
                            if len(lines) > time_line_index + 1 and '-->' in lines[time_line_index+1]:
                                time_line_index += 1
                            else:
                                logger.warning(f"无法在SRT区块中找到有效的时间行: {block_raw}")
                                continue

                        time_line = lines[time_line_index]
                        text_lines = lines[time_line_index+1:]
                        start_time_str, end_time_str = time_line.split(' --> ')
                        
                        def srt_time_to_seconds(t_str):
                            h, m, s_ms = t_str.split(':')
                            s, ms = s_ms.split(',')
                            return int(h) * 3600 + int(m) * 60 + int(s) + int(ms) / 1000.0

                        start_time_sec = srt_time_to_seconds(start_time_str)
                        end_time_sec = srt_time_to_seconds(end_time_str)
                        text_content = " ".join(text_lines).strip()

                        srt_entries.append({
                            "id": entry_id_counter,
                            "text": text_content,
                            "start_time": start_time_sec,
                            "end_time": end_time_sec,
                            "start_time_str": start_time_str,
                            "end_time_str": end_time_str
                        })
                        entry_id_counter += 1
                    except Exception as e:
                        logger.warning(f"解析SRT区块时出错: {str(e)}, 区块: {block_raw}")
            
            logger.info(f"成功从SRT文件 {srt_file_path} 解析出 {len(srt_entries)} 个条目。")
            if not srt_entries:
                logger.warning(f"未能从SRT文件 {srt_file_path} 中解析出任何有效条目。")
                return []
            
        except Exception as e:
            logger.error(f"解析SRT文件 {srt_file_path} 时出错: {str(e)}")
            return [] # 解析SRT文件失败，直接返回空列表

        # 2. 构建LLM提示
        srt_for_llm = [f"L{entry['id']}: {entry['text']}" for entry in srt_entries]
        srt_text_for_llm = "\n".join(srt_for_llm)
        preview_length = min(500, len(srt_text_for_llm))
        logger.info(f"准备传递给LLM的SRT文本预览 (前{preview_length}字符): {srt_text_for_llm[:preview_length]}...")

        # 3. 构建类型描述（使用动态配置）
        type_description_list = []
        semantic_segment_types = get_semantic_segment_types()
        semantic_definitions = get_semantic_type_definitions()
        
        for seg_type in semantic_segment_types:
            definition = semantic_definitions.get(seg_type, {})
            description = definition.get('description', f'{seg_type}类型的内容')
            
            type_description_list.append(f'- "{seg_type}": {description}')
        
        type_descriptions_formatted_str = "\n".join(type_description_list)

        # 4. 调用DeepSeek API进行语义分段
        try:
            logger.info("准备调用DeepSeek API进行基于SRT的语义分段")
            segments_result = self._call_deepseek_for_srt_segmentation(
                srt_text_for_llm, 
                type_descriptions_formatted_str
            )
            
            if not segments_result or "segments" not in segments_result:
                logger.error("DeepSeek API返回的分段结果无效或不包含segments键。")
                # 此处可以选择抛出异常，或者返回空列表并让调用者处理
                # raise ValueError("LLM分析返回结果无效") 
                return [] # 返回空列表表示分析失败
            
            llm_segments_info = segments_result.get("segments", [])
            if not llm_segments_info: # 进一步检查segments列表是否为空
                logger.warning("LLM返回的语义区块列表为空。")
                return [] # 返回空列表表示分析失败
            
            logger.info(f"成功获取 {len(llm_segments_info)} 个基于SRT的语义区块定义")

            # 5. 处理API返回结果，转换为Segment格式
            result_segments = []
            for segment_def in llm_segments_info:
                try:
                    segment_type = segment_def.get("segment_type", "其他")
                    start_line_id = segment_def.get("start_line_id") # 不设默认值，确保存在
                    end_line_id = segment_def.get("end_line_id")   # 不设默认值，确保存在

                    if start_line_id is None or end_line_id is None:
                        logger.warning(f"LLM返回的区块定义缺少 start_line_id 或 end_line_id: {segment_def}")
                        continue

                    if segment_type not in semantic_segment_types:
                        logger.warning(f"LLM返回了未知的语义类型 '{segment_type}', 将其归类为 '其他'. 区块: {segment_def}")
                        segment_type = "其他"
                    
                    relevant_entries = [entry for entry in srt_entries if start_line_id <= entry["id"] <= end_line_id]
                    if not relevant_entries:
                        logger.warning(f"根据LLM返回的行号范围 {start_line_id}-{end_line_id} 未找到匹配的SRT条目. 区块: {segment_def}")
                        continue
                    
                    start_time = min(entry["start_time"] for entry in relevant_entries)
                    end_time = max(entry["end_time"] for entry in relevant_entries)
                    text_content = " ".join(entry["text"] for entry in relevant_entries)
                    
                    segment_result = {
                        "semantic_type": segment_type,
                        "text": text_content,
                        "asr_matched_text": text_content,
                        "start_time": start_time,
                        "end_time": end_time,
                        "time_period": f"{self._format_seconds_to_time(start_time)} - {self._format_seconds_to_time(end_time)}",
                        "srt_line_ids": list(range(start_line_id, end_line_id + 1)),
                    }
                    result_segments.append(segment_result)
                except Exception as e_segment:
                    logger.warning(f"处理LLM返回的单个语义区块时出错: {str(e_segment)}. 区块定义: {segment_def}")
            
            if not result_segments:
                logger.warning("成功调用LLM，但未能从其响应中构建任何有效的语义分段对象。")
                return [] # 表示分析失败

            logger.info(f"成功将LLM分段结果转换为 {len(result_segments)} 个语义分段对象。")
            return result_segments
            
        except Exception as e_api_call: # 捕获 _call_deepseek_for_srt_segmentation 抛出的异常
            logger.error(f"调用DeepSeek API进行语义分段时发生严重错误: {str(e_api_call)}")
            logger.error(f"错误详情: {traceback.format_exc()}")
            # 根据您的要求，这里应该让程序出错并提示。返回空列表，让上层处理。
            # 如果需要程序在此处终止，可以 raise e_api_call
            return [] # 返回空列表表示分析失败

    def _format_seconds_to_time(self, seconds: float) -> str:
        """将秒转换为时间字符串格式 (HH:MM:SS)"""
        hours = int(seconds // 3600)
        minutes = int((seconds % 3600) // 60)
        secs = int(seconds % 60)
        return f"{hours:02d}:{minutes:02d}:{secs:02d}"

    def _call_deepseek_for_srt_segmentation(self, srt_text_for_llm, type_descriptions_formatted_str):
        """
        调用DeepSeek API进行SRT语义分段
        
        Args:
            srt_text_for_llm: 格式化的SRT文本
            type_descriptions_formatted_str: 语义类型描述
            
        Returns:
            包含分段信息的字典
        
        Raises:
            ValueError: 如果API响应无效或JSON解析失败。
            requests.exceptions.RequestException: 如果API请求失败。
        """
        import requests
        import json
        import re
        import traceback
        
        # 构建系统提示
        system_prompt = (
            "你是一位专业的视频内容结构分析师。你的任务是分析一个以SRT字幕行形式提供的视频转录文本，"
            "并将连续的SRT行组合成符合预定义语义类型的逻辑区块。"
            "每个SRT行都有一个唯一的行号（例如 L1, L2, ...）。你需要确定每个语义区块由哪些SRT行组成。"
            f"\n\n【预定义的语义区块类型及其说明】:\n{type_descriptions_formatted_str}"
            "\n\n请严格按照以下JSON格式输出一个列表，列表中的每个对象代表一个语义区块。确保区块覆盖所有SRT行，并且是连续的："
            '\n[\n  {\n    "segment_type": "广告开场",\n    "start_line_id": 1,\n    "end_line_id": 3\n  },\n'
            '  {\n    "segment_type": "问题陈述",\n    "start_line_id": 4,\n    "end_line_id": 10\n  }\n]'
        )

        # 构建用户提示
        user_prompt = (
            "请根据以下逐行标记的SRT转录文本进行语义区块划分。请严格遵守系统指令，特别是关于区块定义（连续的SRT行）、"
            "语义归类、完整覆盖、多样性与细致性的要求。输出的 `start_line_id` 和 `end_line_id` 必须准确对应输入文本中每行前的L{id}标记。"
            f"\n--- 带行号的SRT转录文本开始 ---\n{srt_text_for_llm}"
            "\n--- 带行号的SRT转录文本结束 ---\n请严格按照JSON格式输出。"
        )
        
        # 调用DeepSeek API
        try:
            headers = {
                "Content-Type": "application/json",
                "Authorization": f"Bearer {self.api_key}"
            }
            
            data = {
                "model": self.model,
                "messages": [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                "temperature": 0.3,
                "max_tokens": 4096
            }
            
            logger.debug(f"准备调用DeepSeek API，提示词长度: {len(system_prompt) + len(user_prompt)}")
            
            response = requests.post(
                f"{self.base_url}/v1/chat/completions",
                headers=headers,
                json=data,
                timeout=60
            )
            
            response.raise_for_status() # 如果请求失败(状态码 4xx 或 5xx)，将引发 HTTPError
            
            llm_response = response.json()
            
            if not llm_response or "choices" not in llm_response or not llm_response["choices"]:
                logger.error("DeepSeek API响应无效或不包含choices")
                raise ValueError("API响应无效: 响应中缺少 'choices' 字段")
            
            llm_output_text = llm_response['choices'][0]['message']['content']
            preview_length = min(500, len(llm_output_text))
            logger.info(f"DeepSeek API调用成功。原始输出预览: {llm_output_text[:preview_length]}...")

            # 从输出中提取JSON
            json_match = re.search(r'```json\s*([\s\S]*?)\s*```', llm_output_text)
            if json_match:
                json_str = json_match.group(1)
            else:
                json_start = llm_output_text.find('[')
                json_end = llm_output_text.rfind(']')
                if json_start != -1 and json_end != -1 and json_start < json_end:
                    json_str = llm_output_text[json_start:json_end+1]
                else:
                    json_str = llm_output_text # 假设整个输出是JSON
                
            logger.debug(f"尝试解析的JSON字符串: {json_str[:500]}...")
            
            segments = json.loads(json_str) # 如果解析失败，会抛出 json.JSONDecodeError
            
            if not isinstance(segments, list) or not segments: # 检查是否为非空列表
                logger.warning("解析后的JSON不是有效的区块列表或区块为空")
                raise ValueError("LLM返回的JSON不是有效的区块列表或区块为空")
                
            logger.info(f"成功解析LLM返回的JSON，获得 {len(segments)} 个基于SRT的语义区块定义。")
            return {"segments": segments}
            
        except requests.exceptions.RequestException as e_req:
            logger.error(f"调用DeepSeek API请求失败: {str(e_req)}")
            logger.error(f"错误详情: {traceback.format_exc()}")
            raise # 重新抛出请求异常
        except json.JSONDecodeError as e_json:
            logger.error(f"解析LLM语义分段结果失败: {e_json}. LLM原始输出 (前200字符): {llm_output_text[:200]}...")
            logger.error(f"错误详情: {traceback.format_exc()}")
            raise ValueError(f"LLM响应JSON解析错误: {e_json}. 原始文本: {llm_output_text[:200]}...")
        except ValueError as e_val:
            logger.error(f"处理API响应时发生值错误: {str(e_val)}")
            logger.error(f"错误详情: {traceback.format_exc()}")
            raise # 重新抛出值错误
        except Exception as e:
            logger.error(f"调用DeepSeek API或处理响应时发生未知错误: {str(e)}")
            logger.error(f"错误详情: {traceback.format_exc()}")
            raise Exception(f"DeepSeek API调用或处理时发生未知错误: {e}") # 抛出通用异常

class IntentAnalyzer:
    """视频意图分析类"""
    
    def __init__(self, segments=None, target_audience=None, product_type=None, selling_points=None):
        """
        初始化意图分析器
        
        Args:
            segments: 视频分段列表
            target_audience: 目标人群
            product_type: 产品类型
            selling_points: 产品卖点列表
        """
        self.segments_data = segments or []
        self.target_audience = target_audience or []
        self.product_type = product_type or []
        self.selling_points = selling_points or []
        self.semantic_analyzer = SemanticAnalyzer()
        
        logger.info(f"初始化意图分析器，目标人群: {target_audience}, 产品类型: {product_type}, 产品卖点: {selling_points}")
    
    def _contains_chinese(self, s: str) -> bool:
        """检查字符串是否包含中文字符"""
        if not s: # 处理空字符串或None的情况
            return False
        for char in s:
            if '\\u4e00' <= char <= '\\u9fff':
                return True
        return False
    
    def _format_time(self, seconds):
        """
        将秒数格式化为时:分:秒格式
        
        Args:
            seconds: 秒数
            
        Returns:
            格式化的时间字符串
        """
        hours = int(seconds // 3600)
        minutes = int((seconds % 3600) // 60)
        seconds = int(seconds % 60)
        
        return f"{hours:02d}:{minutes:02d}:{seconds:02d}"

    def analyze_segments(self, segments_data):
        """
        批量分析音频片段数据，将每个片段归类到特定的语义分类中。

        Args:
            segments_data (list): 包含多个音频片段的列表，每个片段应该有 'text' 字段。

        Returns:
            list: 包含分析结果的列表，每个元素对应一个片段的分类结果。
        """
        if not segments_data:
            logger.warning("没有提供音频片段数据。")
            return []

        from streamlit_app.config.config import get_semantic_type_definitions, DEFAULT_SEMANTIC_SEGMENT_TYPES

        # 动态获取语义类型定义
        semantic_definitions = get_semantic_type_definitions()
        available_types = DEFAULT_SEMANTIC_SEGMENT_TYPES

        logger.info(f"开始分析 {len(segments_data)} 个音频片段，语义类型数量: {len(available_types)}")

        results = []
        for i, segment in enumerate(segments_data):
            segment_text = segment.get('text', '')
            if not segment_text:
                logger.warning(f"片段 {i} 没有文本内容，跳过分析。")
                results.append({
                    'segment_index': i,
                    'text': segment_text,
                    'semantic_type': '其他',
                    'confidence': 0.0,
                    'analysis_result': '文本为空'
                })
                continue

            try:
                # 构建动态的类型描述
                type_descriptions = []
                for type_name in available_types:
                    definition = semantic_definitions.get(type_name, {})
                    description = definition.get('description', f'{type_name}类型的内容')
                    keywords = definition.get('keywords', [])
                    examples = definition.get('examples', [])
                    
                    # 组合描述信息
                    full_description = f"{type_name}: {description}"
                    if keywords:
                        full_description += f" 关键词：{', '.join(keywords[:3])}"  # 只显示前3个关键词
                    if examples:
                        full_description += f" 示例：{examples[0]}"  # 只显示第一个示例
                    
                    type_descriptions.append(full_description)

                # 构建系统提示词
                system_prompt = f"""你是一个专业的视频内容分析师，擅长将母婴奶粉营销视频的文本片段归类到合适的语义类型中。

可选的语义类型及其定义：
{chr(10).join([f"{i+1}. {desc}" for i, desc in enumerate(type_descriptions)])}

请根据文本内容，选择最合适的语义类型。如果文本内容不明确或难以归类，请选择"其他"。

返回格式要求：
- semantic_type: 选择的语义类型名称（必须是上述类型之一）
- confidence: 置信度（0.0-1.0之间的浮点数）
- reasoning: 简短的分析理由

请以JSON格式返回结果。"""

                user_prompt = f"请分析以下文本片段的语义类型：\n\n文本内容：{segment_text}"

                # 调用DeepSeek API
                response = self.deepseek_client.chat.completions.create(
                    model="deepseek-chat",
                    messages=[
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": user_prompt}
                    ],
                    temperature=0.1,
                    max_tokens=500,
                    stream=False
                )

                response_content = response.choices[0].message.content.strip()
                logger.debug(f"片段 {i} DeepSeek API 响应: {response_content}")

                # 解析JSON响应
                try:
                    result_json = json.loads(response_content)
                    semantic_type = result_json.get('semantic_type', '其他')
                    confidence = float(result_json.get('confidence', 0.5))
                    reasoning = result_json.get('reasoning', '自动分析')

                    # 验证语义类型是否在可选范围内
                    if semantic_type not in available_types:
                        logger.warning(f"片段 {i} 返回了无效的语义类型 '{semantic_type}'，设置为'其他'")
                        semantic_type = '其他'
                        confidence = 0.3

                except (json.JSONDecodeError, ValueError) as e:
                    logger.error(f"片段 {i} JSON解析失败: {e}, 原始响应: {response_content}")
                    # 尝试简单的文本匹配作为后备
                    semantic_type = self._fallback_semantic_classification(segment_text, available_types, semantic_definitions)
                    confidence = 0.4
                    reasoning = "JSON解析失败，使用后备分类"

                results.append({
                    'segment_index': i,
                    'text': segment_text,
                    'semantic_type': semantic_type,
                    'confidence': confidence,
                    'analysis_result': reasoning
                })

                logger.info(f"片段 {i} 分析完成: {semantic_type} (置信度: {confidence:.2f})")

            except Exception as e:
                logger.error(f"分析片段 {i} 时发生错误: {e}")
                results.append({
                    'segment_index': i,
                    'text': segment_text,
                    'semantic_type': '其他',
                    'confidence': 0.0,
                    'analysis_result': f'分析失败: {str(e)}'
                })

        logger.info(f"完成所有 {len(segments_data)} 个片段的语义分析")
        return results

    def _fallback_semantic_classification(self, text: str, available_types: list, semantic_definitions: dict) -> str:
        """
        后备的语义分类方法，基于关键词匹配
        
        Args:
            text: 要分类的文本
            available_types: 可用的语义类型列表
            semantic_definitions: 语义类型定义字典
            
        Returns:
            str: 分类结果
        """
        text_lower = text.lower()
        
        # 按类型检查关键词匹配
        for type_name in available_types:
            if type_name == '其他':
                continue
                
            definition = semantic_definitions.get(type_name, {})
            keywords = definition.get('keywords', [])
            
            # 检查关键词匹配
            for keyword in keywords:
                if keyword.lower() in text_lower:
                    logger.info(f"后备分类：基于关键词 '{keyword}' 将文本分类为 '{type_name}'")
                    return type_name
        
        # 如果没有匹配到任何关键词，返回"其他"
        return '其他'

def main_analysis_pipeline(video_path, target_audience=None, product_type=None, selling_points_config_representation=None, additional_info=None):
    """
    完整的视频分析流水线，将视频分段和意图分析结合起来
    
    Args:
        video_path: 视频文件路径
        target_audience: 目标人群，默认为None
        product_type: 产品类型，默认为None (此参数在此简化流程中不再用于产品类型匹配)
        selling_points_config_representation: 用于缓存控制的产品卖点表示 (例如元组)
        additional_info: 附加的分析信息，默认为None
        
    Returns:
        Tuple: (分析结果列表, 完整的转录数据字典) 或 ([], None) 如果失败
    """
    from streamlit_app.modules.data_process.video_segmenter import segment_video # 保持局部导入
    
    full_transcript_data = None # 初始化
    analysis_results_placeholder = [] # 返回一个空列表作为分析结果的占位符
    try:
        # 1. 视频分段，并获取完整转录数据 (包括SRT文件路径和内容)
        segments, full_transcript_data = segment_video(video_path)
        
        if not segments:
            logger.warning(f"视频分段结果为空或获取转录数据失败: {video_path}")
            # 即使分段为空，也返回转录数据和空分析结果占位符
            return analysis_results_placeholder, full_transcript_data 
        
        # 产品类型识别和目标人群识别将主要在 streamlit_app/app.py 中通过分析SRT文件内容进行。
        # IntentAnalyzer.analyze_segment 中的产品类型和人群匹配逻辑已大部分移除或不再核心。
        # 此处不再调用 analyze_video_segments 进行基于关键词的卖点等分析，
        # 因为其结果（如 matched_selling_points）当前未在UI上直接使用。
        # 如果将来需要这些详细的基于片段的分析，可以重新启用或调整此部分。
        
        # 当前，main_analysis_pipeline 的核心输出是 segments (用于UI显示分段视频)
        # 和 full_transcript_data (用于 app.py 中提取SRT路径/内容进行LLM分析)
        
        # 直接使用 segments 作为一种形式的 "分析结果" 返回给 app.py，
        # app.py 主要消费的是 segments 列表本身，而不是内部更细致的匹配字段。
        # 或者，如果 app.py 仅需 segments 和 full_transcript_data，可以让 analysis_results 为空。
        # 为了保持返回结构一致性，但表明这部分分析被跳过，我们返回原始的segments
        # 或者一个明确的空列表。考虑到 app.py 中对 analysis_results 的迭代，返回 segments 更合适。
        
        # logger.info(f"视频片段意图分析完成，找到 {len(analysis_results)} 个匹配片段 for {video_path}")
        # 返回 segments (语义分段结果) 和 full_transcript_data
        # app.py 将基于 segments 迭代显示，并使用 full_transcript_data 进行LLM分析
        return segments, full_transcript_data
    except Exception as e:
        logger.error(f"视频分析流水线执行失败 ({video_path}): {str(e)}")
        return analysis_results_placeholder, full_transcript_data # 尽量返回转录数据，即使后续分析失败 