"""
视频片段分析模块

此模块专门用于分析视频片段，提取产品类型和核心卖点信息。
使用DeepSeek API进行智能分析，支持并行处理以提高效率。
"""

import json
import logging
import asyncio
import concurrent.futures
from typing import List, Dict, Any, Tuple
import streamlit as st
from pathlib import Path

from streamlit_app.config.config import PRODUCT_TYPES, SELLING_POINTS, get_config

# 设置日志
logger = logging.getLogger(__name__)

class SegmentAnalyzer:
    """片段分析器，专门用于分析单个视频片段的产品类型和核心卖点"""
    
    def __init__(self):
        """初始化片段分析器"""
        config = get_config()
        self.api_key = config.get("api_key") or "sk-test-api-key-for-development-only"
        self.base_url = "https://api.deepseek.com"
        self.model = "deepseek-chat"
        
        # 导入requests库
        try:
            import requests
            self.requests = requests
        except ImportError:
            logger.error("请安装requests库: pip install requests")
            raise ImportError("缺少必要的requests库")
        
        logger.info("片段分析器初始化完成")
    
    def analyze_single_segment(self, segment_text: str, semantic_type: str) -> Dict[str, Any]:
        """
        分析单个片段，提取产品类型和核心卖点
        
        Args:
            segment_text: 片段文本内容
            semantic_type: 片段的语义类型
            
        Returns:
            包含分析结果的字典: {"product_type": str, "selling_points": List[str]}
        """
        if not segment_text or not segment_text.strip():
            return {"product_type": "", "selling_points": []}
        
        # 构建针对产品类型和卖点识别的专业提示词
        system_prompt = f"""你是一个专业的母婴奶粉产品分析专家。你的任务是分析视频片段文本，准确识别以下信息：

1. 【产品类型】: 从文本中识别具体提到的奶粉产品类型，可选项目包括：{json.dumps(PRODUCT_TYPES, ensure_ascii=False)}
   - 只有在文本中明确提到或暗示特定产品时才输出产品类型
   - 每个片段最多只能识别1种产品类型
   - 如果没有明确的产品信息，则输出空字符串

2. 【核心卖点】: 从文本中识别提到的产品核心卖点，可选项目包括：{json.dumps(SELLING_POINTS, ensure_ascii=False)}
   - 可以识别多个卖点
   - 只有在文本中明确提到或暗示相关概念时才输出
   - 如果没有相关卖点信息，则输出空数组

注意识别要点：
- "启赋水奶"相关表述: "水奶"、"液态奶"、"打开盖子就能喝"、"开盖即饮"、"不用冲调"
- "启赋蕴淇"相关表述: "蕴淇"、"高端配方"、"旗舰产品"
- "启赋蓝钻"相关表述: "蓝钻"、"超高端"、"顶级配方"
- "HMO & 母乳低聚糖"相关表述: "HMO"、"母乳低聚糖"、"人乳寡糖"
- "A2奶源"相关表述: "A2蛋白"、"A2型蛋白"、"A2奶牛"
- "自愈力"相关表述: "自护力"、"自御力"、"免疫力"、"抵抗力"

请严格按照以下JSON格式输出：
{{
  "product_type": "启赋水奶", 
  "selling_points": ["HMO & 母乳低聚糖", "开盖即饮"]
}}"""

        user_prompt = f"""请分析以下视频片段文本（语义类型：{semantic_type}），识别其中的产品类型和核心卖点：

文本内容：
{segment_text}

请按照指定的JSON格式输出分析结果。"""

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
                "temperature": 0.1,  # 低温度确保一致性
                "max_tokens": 500
            }
            
            response = self.requests.post(
                f"{self.base_url}/v1/chat/completions",
                headers=headers,
                json=data,
                timeout=30
            )
            response.raise_for_status()
            result = response.json()
            
            content = result['choices'][0]['message']['content']
            
            # 解析JSON响应
            try:
                # 清理Markdown格式
                if "```json" in content:
                    content = content.split("```json")[1].split("```")[0].strip()
                elif "```" in content:
                    content = content.split("```")[1].split("```")[0].strip()
                
                analysis_result = json.loads(content)
                
                # 验证和清理结果
                product_type = analysis_result.get("product_type", "")
                selling_points = analysis_result.get("selling_points", [])
                
                # 确保产品类型在允许列表中
                if product_type and product_type not in PRODUCT_TYPES:
                    logger.warning(f"识别到未知产品类型: {product_type}，将其置为空")
                    product_type = ""
                
                # 确保卖点在允许列表中
                valid_selling_points = [sp for sp in selling_points if sp in SELLING_POINTS]
                if len(valid_selling_points) != len(selling_points):
                    logger.warning(f"过滤了一些无效的卖点，原始: {selling_points}，有效: {valid_selling_points}")
                
                return {
                    "product_type": product_type,
                    "selling_points": valid_selling_points
                }
                
            except json.JSONDecodeError as e:
                logger.error(f"JSON解析失败: {e}，原始内容: {content[:200]}...")
                return {"product_type": "", "selling_points": []}
                
        except Exception as e:
            logger.error(f"分析片段时出错: {e}")
            return {"product_type": "", "selling_points": []}

def analyze_segments_batch(segments_data: List[Dict[str, Any]], max_workers: int = 5) -> List[Dict[str, Any]]:
    """
    批量分析多个片段，使用并行处理提高效率
    
    Args:
        segments_data: 片段数据列表
        max_workers: 最大并发工作线程数
        
    Returns:
        包含分析结果的片段数据列表
    """
    if not segments_data:
        return []
    
    analyzer = SegmentAnalyzer()
    
    def analyze_segment_wrapper(segment: Dict[str, Any]) -> Dict[str, Any]:
        """包装函数，用于并行处理"""
        try:
            text = segment.get("transcript", "") or segment.get("text", "")
            semantic_type = segment.get("semantic_type", "") or segment.get("type", "")
            
            # 执行分析
            analysis_result = analyzer.analyze_single_segment(text, semantic_type)
            
            # 将结果添加到片段数据中
            segment_copy = segment.copy()
            segment_copy.update({
                "analyzed_product_type": analysis_result["product_type"],
                "analyzed_selling_points": analysis_result["selling_points"]
            })
            
            return segment_copy
            
        except Exception as e:
            logger.error(f"分析片段时出错: {e}")
            # 返回原始片段数据，添加空的分析结果
            segment_copy = segment.copy()
            segment_copy.update({
                "analyzed_product_type": "",
                "analyzed_selling_points": []
            })
            return segment_copy
    
    # 使用Streamlit的进度条
    progress_bar = st.progress(0)
    status_text = st.empty()
    
    analyzed_segments = []
    
    # 使用并发处理
    with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
        # 提交所有任务
        future_to_segment = {
            executor.submit(analyze_segment_wrapper, segment): i 
            for i, segment in enumerate(segments_data)
        }
        
        # 收集结果
        for i, future in enumerate(concurrent.futures.as_completed(future_to_segment)):
            try:
                result = future.result()
                analyzed_segments.append(result)
                
                # 更新进度
                progress = (i + 1) / len(segments_data)
                progress_bar.progress(progress)
                status_text.text(f"正在分析片段... ({i + 1}/{len(segments_data)})")
                
            except Exception as e:
                logger.error(f"处理片段分析结果时出错: {e}")
                # 添加一个带错误标记的结果
                original_segment = segments_data[future_to_segment[future]]
                error_segment = original_segment.copy()
                error_segment.update({
                    "analyzed_product_type": "",
                    "analyzed_selling_points": [],
                    "analysis_error": str(e)
                })
                analyzed_segments.append(error_segment)
    
    # 清理进度条
    progress_bar.empty()
    status_text.empty()
    
    # 按原始顺序排序（因为并发完成顺序可能不同）
    analyzed_segments.sort(key=lambda x: segments_data.index(
        next(seg for seg in segments_data 
             if seg.get("filename") == x.get("filename") or 
             seg.get("start_time", 0) == x.get("start_time", 0))
    ))
    
    logger.info(f"完成 {len(analyzed_segments)} 个片段的分析")
    return analyzed_segments

@st.cache_data(ttl=3600)  # 缓存1小时
def cached_analyze_segments(segments_key: str, segments_data: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    带缓存的片段分析函数
    
    Args:
        segments_key: 用于缓存的唯一键值
        segments_data: 片段数据列表
        
    Returns:
        分析结果列表
    """
    return analyze_segments_batch(segments_data) 