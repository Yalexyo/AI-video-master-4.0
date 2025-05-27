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
        翻译英文文本
        
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
            system_prompt = f"""你是一个专业的英{target_language}翻译专家，专门翻译视频内容识别中的物体和场景标签。

翻译要求：
1. 只翻译标签内容，返回简洁的{target_language}词汇
2. 不要添加任何解释、标点符号或额外文字
3. 对于动物、物品、场景等标签使用常见的{target_language}表达
4. 保持翻译的准确性和简洁性

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
        分析视频转录文本，提取目标人群和产品信息
        
        Args:
            transcript: 视频转录文本
            
        Returns:
            分析结果字典
        """
        if not self.is_available():
            return {"error": "DeepSeek API不可用"}
        
        if not transcript.strip():
            return {"error": "转录文本为空"}
        
        try:
            # 从config中导入目标人群列表
            from streamlit_app.config.config import TARGET_GROUPS
            target_groups_str = json.dumps(TARGET_GROUPS, ensure_ascii=False)
            
            system_prompt = f"""你是一个专业的视频内容分析师，擅长分析母婴奶粉营销视频的内容特征。

预定义的目标人群列表：
{target_groups_str}

请根据视频转录文本，分析并返回最匹配的目标人群。

要求：
- 基于内容特征（如提到的年龄段、需求、场景等）进行判断
- 只能返回一个目标人群，不能返回多个
- 必须是预定义列表中的人群名称
- 基于内容特征做出最佳判断

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
    
    def analyze_semantic_segments(self, transcript_segments: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        分析转录片段的语义类型
        
        Args:
            transcript_segments: 转录片段列表
            
        Returns:
            带有语义分析的片段列表
        """
        if not self.is_available():
            logger.warning("DeepSeek API不可用，跳过语义分析")
            return transcript_segments
        
        analyzed_segments = []
        
        for segment in transcript_segments:
            try:
                segment_text = segment.get('text', '')
                if not segment_text.strip():
                    analyzed_segments.append(segment)
                    continue
                
                # 分析语义类型
                semantic_result = self._analyze_segment_semantic(segment_text)
                
                # 合并结果
                enhanced_segment = segment.copy()
                enhanced_segment.update(semantic_result)
                analyzed_segments.append(enhanced_segment)
                
            except Exception as e:
                logger.error(f"分析片段语义失败: {str(e)}")
                analyzed_segments.append(segment)
        
        return analyzed_segments
    
    def _analyze_segment_semantic(self, text: str) -> Dict[str, Any]:
        """分析单个片段的语义类型"""
        try:
            # 从config中导入语义类型定义
            from streamlit_app.config.config import SEMANTIC_SEGMENT_TYPES
            
            type_descriptions = []
            for i, semantic_type in enumerate(SEMANTIC_SEGMENT_TYPES.keys()):
                description = SEMANTIC_SEGMENT_TYPES[semantic_type].get('description', '')
                type_descriptions.append(f"{i+1}. {semantic_type}: {description}")
            
            system_prompt = f"""你是一个专业的视频内容分析师，擅长将母婴奶粉营销视频的文本片段归类到合适的语义类型中。

可选的语义类型及其定义：
{chr(10).join(type_descriptions)}

请根据文本内容，选择最合适的语义类型。如果文本内容不明确或难以归类，请选择"其他"。

返回格式要求：
- semantic_type: 选择的语义类型名称（必须是上述类型之一）
- confidence: 置信度（0.0-1.0之间的浮点数）
- reasoning: 简短的分析理由

请以JSON格式返回结果。"""

            user_prompt = f"请分析以下文本片段的语义类型：\n\n文本内容：{text}"

            response = self._chat_completion([
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ])

            if response and "choices" in response and response["choices"]:
                result_text = response["choices"][0].get("message", {}).get("content", "")
                
                # 解析JSON响应
                import re
                json_match = re.search(r'```json\s*([\s\S]*?)\s*```', result_text)
                if json_match:
                    json_str = json_match.group(1)
                else:
                    json_str = result_text
                
                try:
                    result = json.loads(json_str)
                    return {
                        "semantic_type": result.get("semantic_type", "其他"),
                        "confidence": float(result.get("confidence", 0.5)),
                        "reasoning": result.get("reasoning", "")
                    }
                except (json.JSONDecodeError, ValueError) as e:
                    logger.error(f"解析语义分析结果失败: {e}")
            
            return {
                "semantic_type": "其他",
                "confidence": 0.5,
                "reasoning": "分析失败，使用默认类型"
            }
            
        except Exception as e:
            logger.error(f"语义分析失败: {str(e)}")
            return {
                "semantic_type": "其他",
                "confidence": 0.0,
                "reasoning": f"分析错误: {str(e)}"
            }
    
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