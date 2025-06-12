"""
DeepSeek分析器

专门处理DeepSeek模型分析功能的模块
"""

import os
import json
import logging
from typing import Dict, Any, List, Optional

logger = logging.getLogger(__name__)


class DeepSeekAnalyzer:
    """DeepSeek模型分析器"""
    
    def __init__(self, api_key: Optional[str] = None):
        """
        初始化DeepSeek分析器
        
        Args:
            api_key: DeepSeek API密钥
        """
        self.api_key = api_key or os.environ.get("DEEPSEEK_API_KEY")
        self.base_url = "https://api.deepseek.com"
        self.model = "deepseek-chat"
        
        if not self.api_key:
            logger.warning("未设置DEEPSEEK_API_KEY，DeepSeek分析器不可用")
    
    def is_available(self) -> bool:
        """检查分析器是否可用"""
        return self.api_key is not None
    
    def translate_text(self, english_text: str, target_language: str = "中文") -> Optional[str]:
        """
        翻译英文文本（增强版：优先翻译为业务词表中的词汇）
        
        Args:
            english_text: 英文文本
            target_language: 目标语言
            
        Returns:
            翻译后的文本，失败时返回None
        """
        if not self.is_available():
            logger.warning("DeepSeek API不可用")
            return None
        
        try:
            # 尝试获取业务词表，用于翻译参考
            try:
                from utils.keyword_config import load_keywords_config
                config = load_keywords_config()
                business_words = []
                for module in config.values():
                    if "ai_batch" in module:
                        for category in module["ai_batch"].values():
                            for item in category:
                                if isinstance(item, dict):
                                    business_words.append(item.get("word", ""))
                                else:
                                    business_words.append(str(item))
                business_words_text = f"\n优先参考业务词汇: {list(set(business_words))}"
            except:
                business_words_text = ""
            
            system_prompt = f"""你是一个专业的英{target_language}翻译专家，专门翻译视频内容识别中的物体和场景标签。

翻译要求：
1. 只翻译标签内容，返回简洁的{target_language}词汇
2. 不要添加任何解释、标点符号或额外文字
3. 对于动物、物品、场景等标签使用常见的{target_language}表达
4. 保持翻译的准确性和简洁性{business_words_text}

示例：
- cat → 猫
- dog → 狗  
- animal → 动物
- pet → 宠物
- kitten → 小猫
- whiskers → 胡须

只返回翻译后的{target_language}词汇，不要任何其他内容。"""
            
            user_prompt = f"翻译这个英文标签：{english_text}"
            
            response = self._chat_completion([
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ])
            
            if response and "choices" in response and response["choices"]:
                translation = response["choices"][0].get("message", {}).get("content", "").strip()
                # 清理可能的引号、标点和多余字符
                translation = translation.strip('"\'.,，。').strip()
                
                # 验证翻译结果是否合理（不应该包含英文或过长）
                if translation and len(translation) <= 10 and not any(c.isalpha() and ord(c) < 128 for c in translation):
                    return translation
            
            return None
            
        except Exception as e:
            logger.error(f"DeepSeek翻译失败: {str(e)}")
            return None
    
    def analyze_video_summary(self, transcript: str) -> Dict[str, Any]:
        """
        分析视频转录内容，提取目标人群信息
        
        Args:
            transcript: 视频转录文本
            
        Returns:
            分析结果字典，包含目标人群信息
        """
        if not self.is_available():
            logger.warning("DeepSeek API不可用")
            return {"error": "DeepSeek API不可用"}
        
        if not transcript.strip():
            return {"error": "转录文本为空"}
        
        try:
            # 构建分析提示词
            system_prompt = """你是专业的母婴产品营销分析师。
请分析视频转录文本，识别目标用户群体。

重点关注：
1. 语言风格和内容特点
2. 关注的问题和需求
3. 产品使用场景
4. 决策考虑因素

常见目标人群类型：
- 孕期妈妈：关注安全性、营养价值、专业认证
- 新手爸妈：需要指导、教育、专业支持
- 二胎妈妈：重视便利性、性价比、经验分享
- 职场妈妈：注重效率、品质、时间管理
- 年轻父母：关注潮流、社交、个性化

请以JSON格式输出分析结果，确保target_audience字段是单个字符串值。"""

            user_prompt = f"请分析以下视频转录文本并确定目标人群：\n\n{transcript[:2000]}"  # 限制长度
            
            response = self._chat_completion([
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ])
            
            if response and "choices" in response and response["choices"]:
                result_text = response["choices"][0].get("message", {}).get("content", "")
                
                # 尝试提取和解析JSON数据
                import re
                json_match = re.search(r'```json\s*([\s\S]*?)\s*```', result_text)
                if json_match:
                    json_str = json_match.group(1)
                else:
                    json_str = result_text
                
                try:
                    result_dict = json.loads(json_str)
                    return {
                        "target_audience": result_dict.get("target_audience", "")
                    }
                except json.JSONDecodeError as e:
                    logger.error(f"JSON解析失败: {e}, 原始文本: {json_str[:500]}...")
                    
                    # 如果JSON解析失败，尝试正则表达式提取
                    try:
                        pattern = r'"target_audience"\s*:\s*"([^"]+)"'
                        match = re.search(pattern, result_text)
                        if match:
                            return {"target_audience": match.group(1)}
                    except Exception as e2:
                        logger.error(f"正则表达式提取失败: {e2}")
                
                return {"error": "无法解析分析结果"}
            
            return {"error": "DeepSeek API响应无效"}
            
        except Exception as e:
            logger.error(f"视频内容分析失败: {str(e)}")
            return {"error": str(e)}
    
    def analyze_transcription_content(self, transcript: str, module: str = None) -> Dict[str, Any]:
        """
        专门分析语音转录内容，提取业务标签（使用新的业务词表机制）
        
        Args:
            transcript: 视频转录文本
            module: 指定业务模块（如pain_points），为None时使用全部模块
            
        Returns:
            分析结果字典，包含object/scene/emotion/brand标签
        """
        if not self.is_available():
            logger.warning("DeepSeek API不可用")
            return {"error": "DeepSeek API不可用", "success": False}
        
        if not transcript.strip():
            return {"error": "转录文本为空", "success": False}
        
        try:
            # 使用新的DeepSeek语音分析Prompt
            from utils.keyword_config import get_deepseek_audio_prompt
            analysis_prompt = get_deepseek_audio_prompt(module)
            
            # 在Prompt中添加实际转录文本
            analysis_prompt += f"\n\n📝 需要分析的转录文本：\n{transcript}"
            
            # 使用专门的system提示词
            system_prompt = """你是专业的母婴产品语音内容分析师，专门从语音转录文本中提取语义信息。
请基于转录内容的语义理解进行分析，严格从业务词表中选择匹配的标签。
重点分析转录中体现的物品、场景、情感和品牌信息。"""
            
            response = self._chat_completion([
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": analysis_prompt}
            ])
            
            if response and "choices" in response and response["choices"]:
                result_text = response["choices"][0].get("message", {}).get("content", "")
                logger.info(f"🤖 DeepSeek转录内容分析结果: {result_text}")
                
                # 解析结果
                parsed_result = self._parse_transcription_analysis(result_text)
                
                if parsed_result:
                    parsed_result["success"] = True
                    parsed_result["analysis_method"] = "deepseek_transcription"
                    return parsed_result
                else:
                    return {"error": "解析分析结果失败", "success": False}
            
            return {"error": "DeepSeek API响应无效", "success": False}
            
        except Exception as e:
            logger.error(f"DeepSeek转录内容分析失败: {str(e)}")
            return {"error": str(e), "success": False}

    def _parse_transcription_analysis(self, analysis_text: str) -> Optional[Dict[str, Any]]:
        """
        解析DeepSeek转录分析结果
        """
        try:
            import re
            
            result = {
                'object': '',
                'scene': '', 
                'emotion': '',
                'brand_elements': '',
                'confidence': 0.7
            }
            
            logger.info(f"🎯 开始解析DeepSeek转录分析文本: {analysis_text}")
            
            # 按行处理分析结果
            lines = analysis_text.strip().split('\n')
            
            for line in lines:
                line = line.strip()
                if not line:
                    continue
                
                # 提取各个字段
                if line.lower().startswith('object:'):
                    result['object'] = line[7:].strip()
                elif line.lower().startswith('scene:'):
                    result['scene'] = line[6:].strip()
                elif line.lower().startswith('emotion:'):
                    result['emotion'] = line[8:].strip()
                elif line.lower().startswith('brand:') or line.lower().startswith('brand_elements:'):
                    if line.lower().startswith('brand:'):
                        result['brand_elements'] = line[6:].strip()
                    else:
                        result['brand_elements'] = line[15:].strip()
                elif line.lower().startswith('confidence:'):
                    confidence_text = line[11:].strip()
                    try:
                        confidence_match = re.search(r'([0-9.]+)', confidence_text)
                        if confidence_match:
                            result['confidence'] = float(confidence_match.group(1))
                    except:
                        result['confidence'] = 0.7
            
            # 清理和过滤结果
            for key in ['object', 'scene', 'emotion', 'brand_elements']:
                if result[key]:
                    # 基础清理
                    cleaned = result[key].strip().replace('"', '').replace("'", '')
                    # 过滤无意义内容
                    if cleaned.lower() in ['无', '不确定', '空', 'none', '']:
                        result[key] = ''
                    else:
                        result[key] = cleaned
            
            # 创建all_tags
            all_tags = []
            for value in [result['object'], result['scene'], result['emotion'], result['brand_elements']]:
                if value:
                    tags = [tag.strip() for tag in value.split(',') if tag.strip()]
                    all_tags.extend(tags)
            
            result['all_tags'] = list(set(filter(None, all_tags)))
            
            return result
            
        except Exception as e:
            logger.error(f"解析DeepSeek转录分析结果失败: {str(e)}")
            return None
    
    def _chat_completion(self, messages: List[Dict[str, str]]) -> Optional[Dict[str, Any]]:
        """
        调用DeepSeek API执行聊天请求
        
        Args:
            messages: 消息列表
            
        Returns:
            API响应的JSON对象
        """
        if not self.api_key:
            logger.warning("DeepSeek API密钥未设置")
            return None
        
        try:
            import requests
            
            headers = {
                "Content-Type": "application/json",
                "Authorization": f"Bearer {self.api_key}"
            }
            
            data = {
                "model": self.model,
                "messages": messages,
                "temperature": 0.1,
                "max_tokens": 1500
            }
            
            response = requests.post(
                f"{self.base_url}/v1/chat/completions",
                headers=headers,
                json=data,
                timeout=45
            )
            response.raise_for_status()
            return response.json()
            
        except Exception as e:
            logger.error(f"调用DeepSeek API失败: {str(e)}")
            return None
    
    def analyze_text(self, transcript: str, module: str = None) -> Dict[str, Any]:
        """
        兼容旧流程的分析方法，直接调用analyze_transcription_content
        """
        return self.analyze_transcription_content(transcript, module) 