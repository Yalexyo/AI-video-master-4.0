#!/usr/bin/env python3
"""
视频分析结果格式化工具
将分析结果转换为标准化的表格格式
"""

import pandas as pd
from typing import List, Dict, Any
from pathlib import Path
import json

def get_confidence_indicator(confidence: float) -> str:
    """
    根据置信度返回颜色指示器
    
    Args:
        confidence: 置信度值 (0.0-1.0)
        
    Returns:
        颜色指示器字符串
    """
    if confidence >= 0.8:
        return "🟢"  # 高置信度 - 绿色
    elif confidence >= 0.5:
        return "🟡"  # 中等置信度 - 黄色
    else:
        return "🔴"  # 低置信度 - 红色

def format_confidence_with_indicator(confidence: float) -> str:
    """
    格式化置信度，包含颜色指示器
    
    Args:
        confidence: 置信度值
        
    Returns:
        带颜色指示器的置信度字符串
    """
    indicator = get_confidence_indicator(confidence)
    return f"{indicator} {confidence:.3f}"

def format_analysis_results_to_separated_table(
    analysis_results: List[Dict[str, Any]], 
    video_id: str = "1.mp4",
    include_confidence_indicator: bool = True
) -> pd.DataFrame:
    """
    将视频分析结果转换为分离字段的表格格式
    
    Args:
        analysis_results: 分析结果列表
        video_id: 视频ID
        include_confidence_indicator: 是否包含置信度颜色指示器
        
    Returns:
        pandas DataFrame with columns: video_id, start_time, end_time, objects, scenes, emotions, confidence
    """
    table_data = []
    
    for result in analysis_results:
        file_name = result.get('file_name', '')
        labels = result.get('labels', [])
        
        # 从文件名提取时间信息（如果可能）
        start_time, end_time = extract_time_from_filename(file_name)
        
        # 按类型分离标签
        objects = []
        scenes = []
        emotions = []
        all_confidences = []
        
        for label in labels:
            if isinstance(label, dict):
                label_name = label.get('name', '')
                confidence = label.get('confidence', 0.0)
                label_type = label.get('type', '物体')  # 默认为物体类型
                
                # 只包含高置信度的标签
                if confidence > 0.3:
                    all_confidences.append(confidence)
                    
                    # 根据类型分类
                    if label_type == '物体' or label_type == 'object':
                        objects.append(label_name)
                    elif label_type == '场景' or label_type == 'scene':
                        scenes.append(label_name)
                    elif label_type == '情绪' or label_type == 'emotion':
                        emotions.append(label_name)
                    else:
                        # 未知类型默认归为物体
                        objects.append(label_name)
                        
            elif isinstance(label, str):
                # 字符串标签默认归为物体
                objects.append(label)
                all_confidences.append(1.0)
        
        # 创建表格行（即使某些字段为空也创建行）
        if objects or scenes or emotions:
            # 计算平均置信度
            avg_confidence = sum(all_confidences) / len(all_confidences) if all_confidences else 0.0
            
            # 格式化置信度显示
            if include_confidence_indicator:
                confidence_display = format_confidence_with_indicator(avg_confidence)
            else:
                confidence_display = round(avg_confidence, 3)
            
            table_data.append({
                'video_id': video_id,
                'start_time': format_time(start_time),
                'end_time': format_time(end_time),
                'objects': ', '.join(objects) if objects else '',
                'scenes': ', '.join(scenes) if scenes else '',
                'emotions': ', '.join(emotions) if emotions else '',
                'confidence': confidence_display,
                'confidence_raw': round(avg_confidence, 3)  # 原始数值用于排序和过滤
            })
    
    # 创建DataFrame
    df = pd.DataFrame(table_data)
    
    # 如果没有数据，创建空的结构
    if df.empty:
        df = pd.DataFrame(columns=['video_id', 'start_time', 'end_time', 'objects', 'scenes', 'emotions', 'confidence', 'confidence_raw'])
    
    return df

def format_analysis_results_to_table(
    analysis_results: List[Dict[str, Any]], 
    video_id: str = "1.mp4",
    include_confidence_indicator: bool = True
) -> pd.DataFrame:
    """
    将视频分析结果转换为表格格式
    
    Args:
        analysis_results: 分析结果列表
        video_id: 视频ID
        include_confidence_indicator: 是否包含置信度颜色指示器
        
    Returns:
        pandas DataFrame with columns: video_id, start_time, end_time, visual_label, confidence
    """
    table_data = []
    
    for result in analysis_results:
        file_name = result.get('file_name', '')
        labels = result.get('labels', [])
        
        # 从文件名提取时间信息（如果可能）
        start_time, end_time = extract_time_from_filename(file_name)
        
        # 提取标签和置信度
        visual_labels = []
        confidences = []
        
        for label in labels:
            if isinstance(label, dict):
                label_name = label.get('name', '')
                confidence = label.get('confidence', 0.0)
                
                # 只包含高置信度的标签
                if confidence > 0.3:  # 降低阈值以包含更多标签
                    visual_labels.append(label_name)
                    confidences.append(confidence)
            elif isinstance(label, str):
                visual_labels.append(label)
                confidences.append(1.0)  # 字符串标签默认置信度为1.0
        
        # 创建表格行
        if visual_labels:
            # 计算平均置信度
            avg_confidence = sum(confidences) / len(confidences) if confidences else 0.0
            
            # 格式化置信度显示
            if include_confidence_indicator:
                confidence_display = format_confidence_with_indicator(avg_confidence)
            else:
                confidence_display = round(avg_confidence, 3)
            
            table_data.append({
                'video_id': video_id,
                'start_time': format_time(start_time),
                'end_time': format_time(end_time),
                'visual_label': ','.join(visual_labels[:5]),  # 最多5个标签
                'confidence': confidence_display,
                'confidence_raw': round(avg_confidence, 3)  # 原始数值用于排序和过滤
            })
    
    # 创建DataFrame
    df = pd.DataFrame(table_data)
    
    # 如果没有数据，创建空的结构
    if df.empty:
        df = pd.DataFrame(columns=['video_id', 'start_time', 'end_time', 'visual_label', 'confidence', 'confidence_raw'])
    
    return df

def extract_time_from_filename(filename: str) -> tuple:
    """
    从文件名中提取时间信息
    例如：1_semantic_seg_1_镜头2.mp4 -> (0, 4)
    """
    try:
        # 尝试从文件名中提取片段编号
        if 'seg_' in filename and '镜头' in filename:
            # 提取片段编号
            import re
            seg_match = re.search(r'seg_(\d+)', filename)
            shot_match = re.search(r'镜头(\d+)', filename)
            
            if seg_match:
                seg_num = int(seg_match.group(1))
                # 假设每个片段4秒
                start_time = (seg_num - 1) * 4
                end_time = seg_num * 4
                return start_time, end_time
    except Exception:
        pass
    
    # 默认值
    return 0, 4

def format_time(seconds: int) -> str:
    """
    将秒数转换为 HH:MM:SS 格式
    """
    hours = seconds // 3600
    minutes = (seconds % 3600) // 60
    secs = seconds % 60
    return f"{hours:02d}:{minutes:02d}:{secs:02d}"

def create_separated_analysis_summary_table(
    segment_results: List[Dict[str, Any]], 
    video_id: str = "1.mp4",
    output_path: str = None
) -> pd.DataFrame:
    """
    创建分离字段的分析摘要表格
    
    Args:
        segment_results: 片段分析结果
        video_id: 视频ID
        output_path: 输出文件路径（可选）
        
    Returns:
        格式化的DataFrame（包含objects、scenes、emotions分离字段）
    """
    # 转换为分离字段表格格式
    df = format_analysis_results_to_separated_table(segment_results, video_id)
    
    # 如果指定了输出路径，保存为CSV
    if output_path:
        Path(output_path).parent.mkdir(parents=True, exist_ok=True)
        df.to_csv(output_path, index=False, encoding='utf-8-sig')
    
    return df

def create_analysis_summary_table(
    segment_results: List[Dict[str, Any]], 
    video_id: str = "1.mp4",
    output_path: str = None
) -> pd.DataFrame:
    """
    创建分析摘要表格
    
    Args:
        segment_results: 片段分析结果
        video_id: 视频ID
        output_path: 输出文件路径（可选）
        
    Returns:
        格式化的DataFrame
    """
    # 转换为表格格式
    df = format_analysis_results_to_table(segment_results, video_id)
    
    # 如果指定了输出路径，保存为CSV
    if output_path:
        Path(output_path).parent.mkdir(parents=True, exist_ok=True)
        df.to_csv(output_path, index=False, encoding='utf-8-sig')
    
    return df

def merge_similar_labels(df: pd.DataFrame, time_threshold: int = 8) -> pd.DataFrame:
    """
    合并相似的标签（时间相近且标签相似的行）
    
    Args:
        df: 分析结果DataFrame
        time_threshold: 时间阈值（秒）
        
    Returns:
        合并后的DataFrame
    """
    if df.empty:
        return df
    
    merged_data = []
    
    # 按时间排序
    df_sorted = df.sort_values('start_time').reset_index(drop=True)
    
    current_group = None
    
    for idx, row in df_sorted.iterrows():
        # 获取原始置信度数值
        confidence_raw = row.get('confidence_raw', 0.0)
        if confidence_raw == 0.0:
            # 如果没有confidence_raw，尝试从confidence列解析
            confidence_str = str(row.get('confidence', '0.0'))
            try:
                confidence_raw = float(confidence_str.split()[-1])
            except:
                confidence_raw = 0.0
        
        if current_group is None:
            current_group = {
                'video_id': row['video_id'],
                'start_time': row['start_time'],
                'end_time': row['end_time'],
                'labels': set(row['visual_label'].split(',')),
                'confidences': [confidence_raw]
            }
        else:
            # 检查是否可以合并
            current_end_seconds = time_to_seconds(current_group['end_time'])
            row_start_seconds = time_to_seconds(row['start_time'])
            
            if row_start_seconds - current_end_seconds <= time_threshold:
                # 可以合并
                current_group['end_time'] = row['end_time']
                current_group['labels'].update(row['visual_label'].split(','))
                current_group['confidences'].append(confidence_raw)
            else:
                # 不能合并，保存当前组并开始新组
                avg_confidence = sum(current_group['confidences']) / len(current_group['confidences']) if current_group['confidences'] else 0.0
                
                merged_data.append({
                    'video_id': current_group['video_id'],
                    'start_time': current_group['start_time'],
                    'end_time': current_group['end_time'],
                    'visual_label': ','.join(sorted(current_group['labels'])),
                    'confidence': format_confidence_with_indicator(avg_confidence),
                    'confidence_raw': round(avg_confidence, 3)
                })
                
                current_group = {
                    'video_id': row['video_id'],
                    'start_time': row['start_time'],
                    'end_time': row['end_time'],
                    'labels': set(row['visual_label'].split(',')),
                    'confidences': [confidence_raw]
                }
    
    # 添加最后一个组
    if current_group:
        avg_confidence = sum(current_group['confidences']) / len(current_group['confidences']) if current_group['confidences'] else 0.0
        
        merged_data.append({
            'video_id': current_group['video_id'],
            'start_time': current_group['start_time'],
            'end_time': current_group['end_time'],
            'visual_label': ','.join(sorted(current_group['labels'])),
            'confidence': format_confidence_with_indicator(avg_confidence),
            'confidence_raw': round(avg_confidence, 3)
        })
    
    return pd.DataFrame(merged_data)

def time_to_seconds(time_str: str) -> int:
    """
    将 HH:MM:SS 格式转换为秒数
    """
    try:
        parts = time_str.split(':')
        return int(parts[0]) * 3600 + int(parts[1]) * 60 + int(parts[2])
    except:
        return 0

def export_results_multiple_formats(
    df: pd.DataFrame, 
    base_filename: str,
    output_dir: str = "data/results"
):
    """
    将结果导出为多种格式
    
    Args:
        df: 结果DataFrame
        base_filename: 基础文件名（不含扩展名）
        output_dir: 输出目录
    """
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)
    
    # CSV格式
    csv_path = output_path / f"{base_filename}.csv"
    df.to_csv(csv_path, index=False, encoding='utf-8-sig')
    
    # JSON格式
    json_path = output_path / f"{base_filename}.json"
    df.to_json(json_path, orient='records', force_ascii=False, indent=2)
    
    # Excel格式
    excel_path = None
    try:
        excel_path = output_path / f"{base_filename}.xlsx"
        df.to_excel(excel_path, index=False, engine='openpyxl')
        excel_path = str(excel_path)
    except ImportError:
        excel_path = None  # 如果没有openpyxl，跳过Excel导出
    
    return {
        'csv': str(csv_path),
        'json': str(json_path),
        'excel': excel_path
    }

# 示例使用
if __name__ == "__main__":
    # 示例数据
    sample_results = [
        {
            'file_name': '1_semantic_seg_1_镜头2.mp4',
            'labels': [
                {'name': 'baby', 'confidence': 0.95},
                {'name': 'chair', 'confidence': 0.88}
            ]
        },
        {
            'file_name': '1_semantic_seg_2_镜头3.mp4',
            'labels': [
                {'name': 'garden', 'confidence': 0.92},
                {'name': 'baby', 'confidence': 0.85},
                {'name': 'laugh', 'confidence': 0.78}
            ]
        }
    ]
    
    # 创建表格
    df = create_analysis_summary_table(sample_results, "1.mp4")
    print("生成的分析结果表格：")
    print(df.to_string(index=False)) 