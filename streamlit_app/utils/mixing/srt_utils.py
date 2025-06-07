"""
SRT处理工具函数
提取和处理SRT字幕相关的工具函数
"""

import logging
from typing import Dict, List, Any

logger = logging.getLogger(__name__)


def parse_srt_content(srt_content: str) -> List[Dict[str, Any]]:
    """解析SRT内容为结构化数据
    
    Args:
        srt_content: SRT文件内容
        
    Returns:
        List[Dict]: 解析后的SRT条目列表
    """
    entries = []
    
    # 按空行分割条目
    blocks = srt_content.strip().split('\n\n')
    
    for block in blocks:
        lines = block.strip().split('\n')
        if len(lines) >= 3:
            try:
                # 解析索引
                index = int(lines[0])
                
                # 解析时间戳
                timestamp = lines[1]
                start_time, end_time = parse_srt_timestamp(timestamp)
                
                # 解析文本内容（可能多行）
                text = '\n'.join(lines[2:])
                
                entry = {
                    'index': index,
                    'timestamp': timestamp,
                    'start_time': start_time,
                    'end_time': end_time,
                    'text': text,
                    'duration': end_time - start_time
                }
                
                entries.append(entry)
                
            except (ValueError, IndexError) as e:
                logger.warning(f"解析SRT条目失败: {block[:50]}..., 错误: {e}")
                continue
    
    logger.info(f"成功解析 {len(entries)} 个SRT条目")
    return entries


def parse_srt_timestamp(timestamp: str) -> tuple:
    """解析SRT时间戳
    
    Args:
        timestamp: SRT时间戳格式 "00:00:01,000 --> 00:00:03,500"
        
    Returns:
        tuple: (start_time_seconds, end_time_seconds)
    """
    try:
        if '-->' not in timestamp:
            raise ValueError(f"无效的时间戳格式: {timestamp}")
        
        start_str, end_str = timestamp.split(' --> ')
        
        def time_to_seconds(time_str):
            # 格式: "00:00:01,000"
            time_part, ms_part = time_str.split(',')
            h, m, s = map(int, time_part.split(':'))
            ms = int(ms_part)
            return h * 3600 + m * 60 + s + ms / 1000
        
        start_time = time_to_seconds(start_str.strip())
        end_time = time_to_seconds(end_str.strip())
        
        return start_time, end_time
        
    except Exception as e:
        logger.error(f"解析SRT时间戳失败: {timestamp}, 错误: {e}")
        return 0.0, 3.0  # 默认3秒


def parse_srt_timestamp_duration(timestamp: str) -> float:
    """从SRT时间戳解析时长
    
    Args:
        timestamp: SRT时间戳格式 "00:00:01,000 --> 00:00:03,500"
        
    Returns:
        float: 时长（秒）
    """
    try:
        start_time, end_time = parse_srt_timestamp(timestamp)
        return end_time - start_time
    except Exception as e:
        logger.warning(f"解析SRT时间戳时长失败: {timestamp}, 错误: {e}")
        return 3.0  # 默认3秒


def calculate_srt_annotated_duration(srt_entries: List[Dict], srt_annotations: Dict) -> float:
    """计算SRT标注的实际总时长
    
    Args:
        srt_entries: SRT条目列表（包含start_time和end_time）
        srt_annotations: SRT标注字典（支持多种格式）
        
    Returns:
        float: 标注内容的总时长（秒）
    """
    total_duration = 0
    
    for entry in srt_entries:
        entry_index = entry['index']
        annotation = None
        
        # 处理多种标注数据格式
        # 格式1：直接根据index查找 {1: "痛点", 2: "解决方案", ...}
        if entry_index in srt_annotations:
            annotation = srt_annotations[entry_index]
        
        # 格式2：根据"srt_X"键查找 {"srt_1": {"module": "痛点"}, ...}
        srt_key = f"srt_{entry_index}"
        if srt_key in srt_annotations:
            annotation_data = srt_annotations[srt_key]
            if isinstance(annotation_data, dict):
                annotation = annotation_data.get('module')
            else:
                annotation = annotation_data
        
        # 只计算已标注且不为"未标注"的条目
        if annotation and annotation != '未标注':
            # 优先使用预解析的时间字段
            if 'start_time' in entry and 'end_time' in entry:
                duration = entry['end_time'] - entry['start_time']
            else:
                # 备用：从timestamp解析
                timestamp = entry.get('timestamp', '')
                duration = parse_srt_timestamp_duration(timestamp)
            
            total_duration += duration
    
    return total_duration


def get_marketing_hints(text: str) -> List[str]:
    """根据文本内容获取营销标签提示
    
    Args:
        text: 文本内容
        
    Returns:
        List[str]: 营销标签建议列表
    """
    hints = []
    text_lower = text.lower()
    
    # 痛点相关关键词
    pain_keywords = ["困扰", "问题", "担心", "焦虑", "难受", "不适", "烦恼", "难题"]
    if any(keyword in text_lower for keyword in pain_keywords):
        hints.append("痛点")
    
    # 解决方案相关关键词  
    solution_keywords = ["解决", "改善", "缓解", "帮助", "效果", "有用", "管用"]
    if any(keyword in text_lower for keyword in solution_keywords):
        hints.append("解决方案")
    
    # 卖点相关关键词
    selling_keywords = ["优质", "纯净", "天然", "营养", "配方", "成分", "品质", "安全"]
    if any(keyword in text_lower for keyword in selling_keywords):
        hints.append("卖点")
    
    # 促销相关关键词
    promo_keywords = ["优惠", "折扣", "活动", "限时", "特价", "福利", "赠送", "免费"]
    if any(keyword in text_lower for keyword in promo_keywords):
        hints.append("促销")
    
    return hints 