"""
视频分析结果表格组件

提供视频分析结果的表格展示和CSV导出功能
"""

import streamlit as st
import pandas as pd
import io
from typing import List, Dict, Any
from datetime import datetime


def create_analysis_dataframe(segments_data: List[Dict[str, Any]]) -> pd.DataFrame:
    """
    将视频分析结果转换为DataFrame
    
    Args:
        segments_data: 片段分析数据列表
        
    Returns:
        pandas DataFrame
    """
    rows = []
    
    for i, segment in enumerate(segments_data):
        # 基础信息
        row = {
            '镜头序号': i + 1,
            '时长范围': f"{segment.get('start_time', 0):.1f}s-{segment.get('end_time', 0):.1f}s",
            '持续时间': f"{segment.get('duration', 0):.1f}s",
            '镜头类型': segment.get('type', '未知'),
            '置信度': f"{segment.get('confidence', 0):.2f}"
        }
        
        # 分析结果
        analysis = segment.get('analysis', {})
        if analysis and analysis.get('success'):
            # 对象（使用emoji表示）
            objects = analysis.get('objects', [])
            object_str = ' '.join([f"{obj}🍼" if any(keyword in obj for keyword in ['奶瓶', '奶粉', '妈妈', '宝宝']) else obj for obj in objects[:3]])
            
            # 场景（使用emoji表示）
            scenes = analysis.get('scenes', [])
            scene_str = ' '.join([f"{scene}🏠" if any(keyword in scene for keyword in ['客厅', '厨房', '卧室', '家']) else scene for scene in scenes[:2]])
            
            # 表情/情绪（使用emoji表示）
            emotions = analysis.get('emotions', [])
            emotion_str = ' '.join([
                f"{emotion}😊" if emotion in ['开心', '微笑', '大笑', '愉悦'] else
                f"{emotion}😢" if emotion in ['哭泣', '难过', '悲伤'] else
                f"{emotion}😠" if emotion in ['生气', '愤怒'] else
                f"{emotion}😮" if emotion in ['惊讶', '兴奋'] else
                emotion for emotion in emotions[:2]
            ])
            
            row.update({
                'Object (对象)': object_str or '无',
                'Scene (场景)': scene_str or '无',
                'Expression (表情)': emotion_str or '无'
            })
        else:
            row.update({
                'Object (对象)': '分析失败',
                'Scene (场景)': '分析失败', 
                'Expression (表情)': '分析失败'
            })
        
        # 文件信息
        row.update({
            '文件路径': segment.get('file_path', ''),
            '文件大小(MB)': f"{segment.get('file_size', 0):.2f}",
            '分析状态': '成功' if analysis.get('success') else '失败'
        })
        
        rows.append(row)
    
    return pd.DataFrame(rows)


def display_analysis_table(segments_data: List[Dict[str, Any]], title: str = "📊 视频分析结果"):
    """
    显示视频分析结果表格
    
    Args:
        segments_data: 片段分析数据列表
        title: 表格标题
    """
    if not segments_data:
        st.warning("没有分析结果可显示")
        return
    
    st.markdown(f"### {title}")
    
    # 创建DataFrame
    df = create_analysis_dataframe(segments_data)
    
    # 统计信息
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric("总片段数", len(segments_data))
    
    with col2:
        successful_count = sum(1 for seg in segments_data if seg.get('analysis', {}).get('success'))
        st.metric("分析成功", successful_count)
    
    with col3:
        total_duration = sum(seg.get('duration', 0) for seg in segments_data)
        st.metric("总时长", f"{total_duration:.1f}s")
    
    with col4:
        total_size = sum(seg.get('file_size', 0) for seg in segments_data)
        st.metric("总文件大小", f"{total_size:.2f}MB")
    
    # 显示表格
    st.dataframe(
        df,
        use_container_width=True,
        column_config={
            "镜头序号": st.column_config.NumberColumn(
                "镜头序号",
                help="视频片段的序号",
                width="small"
            ),
            "时长范围": st.column_config.TextColumn(
                "时长范围",
                help="片段在原视频中的时间范围",
                width="medium"
            ),
            "Object (对象)": st.column_config.TextColumn(
                "Object (对象)",
                help="识别到的主要物体或人物",
                width="large"
            ),
            "Scene (场景)": st.column_config.TextColumn(
                "Scene (场景)",
                help="拍摄场景或环境",
                width="medium"
            ),
            "Expression (表情)": st.column_config.TextColumn(
                "Expression (表情)",
                help="人物的情绪或表情",
                width="medium"
            ),
            "置信度": st.column_config.ProgressColumn(
                "置信度",
                help="分析结果的置信度",
                min_value=0,
                max_value=1,
                width="small"
            ),
            "分析状态": st.column_config.TextColumn(
                "分析状态",
                help="视觉分析是否成功",
                width="small"
            )
        },
        hide_index=True
    )
    
    # CSV导出功能
    st.markdown("---")
    col1, col2 = st.columns([2, 1])
    
    with col1:
        st.markdown("### 📥 导出数据")
        st.write("点击下方按钮下载分析结果的CSV文件")
    
    with col2:
        # 准备CSV数据
        csv_data = prepare_csv_data(segments_data)
        csv_string = csv_data.to_csv(index=False, encoding='utf-8-sig')
        
        # 生成文件名
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"video_analysis_results_{timestamp}.csv"
        
        st.download_button(
            label="📄 下载CSV文件",
            data=csv_string,
            file_name=filename,
            mime="text/csv",
            type="primary",
            help="下载包含所有分析结果的CSV文件"
        )


def prepare_csv_data(segments_data: List[Dict[str, Any]]) -> pd.DataFrame:
    """
    准备用于CSV导出的数据
    
    Args:
        segments_data: 片段分析数据列表
        
    Returns:
        pandas DataFrame for CSV export
    """
    rows = []
    
    for i, segment in enumerate(segments_data):
        analysis = segment.get('analysis', {})
        
        row = {
            '镜头序号': i + 1,
            '开始时间(秒)': segment.get('start_time', 0),
            '结束时间(秒)': segment.get('end_time', 0),
            '持续时间(秒)': segment.get('duration', 0),
            '镜头类型': segment.get('type', '未知'),
            '置信度': segment.get('confidence', 0),
            '文件路径': segment.get('file_path', ''),
            '文件大小(MB)': segment.get('file_size', 0),
            '分析状态': '成功' if analysis.get('success') else '失败'
        }
        
        if analysis.get('success'):
            # 详细的分析结果
            row.update({
                '对象列表': '|'.join(analysis.get('objects', [])),
                '场景列表': '|'.join(analysis.get('scenes', [])),
                '人物列表': '|'.join(analysis.get('people', [])),
                '情绪列表': '|'.join(analysis.get('emotions', [])),
                '所有标签': '|'.join(analysis.get('all_tags', [])),
                '主要对象': analysis.get('objects', ['无'])[0] if analysis.get('objects') else '无',
                '主要场景': analysis.get('scenes', ['无'])[0] if analysis.get('scenes') else '无',
                '主要情绪': analysis.get('emotions', ['无'])[0] if analysis.get('emotions') else '无',
                '错误信息': ''
            })
        else:
            row.update({
                '对象列表': '',
                '场景列表': '',
                '人物列表': '',
                '情绪列表': '',
                '所有标签': '',
                '主要对象': '分析失败',
                '主要场景': '分析失败',
                '主要情绪': '分析失败',
                '错误信息': analysis.get('error', '未知错误')
            })
        
        rows.append(row)
    
    return pd.DataFrame(rows)


def display_analysis_summary(segments_data: List[Dict[str, Any]]):
    """
    显示分析结果摘要
    
    Args:
        segments_data: 片段分析数据列表
    """
    if not segments_data:
        return
    
    st.markdown("### 📈 分析摘要")
    
    # 收集所有标签进行统计
    all_objects = []
    all_scenes = []
    all_emotions = []
    
    for segment in segments_data:
        analysis = segment.get('analysis', {})
        if analysis.get('success'):
            all_objects.extend(analysis.get('objects', []))
            all_scenes.extend(analysis.get('scenes', []))
            all_emotions.extend(analysis.get('emotions', []))
    
    # 显示高频标签
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.markdown("#### 🍼 高频对象")
        if all_objects:
            object_counts = pd.Series(all_objects).value_counts().head(5)
            for obj, count in object_counts.items():
                st.write(f"• {obj}: {count}次")
        else:
            st.write("无数据")
    
    with col2:
        st.markdown("#### 🏠 高频场景")
        if all_scenes:
            scene_counts = pd.Series(all_scenes).value_counts().head(5)
            for scene, count in scene_counts.items():
                st.write(f"• {scene}: {count}次")
        else:
            st.write("无数据")
    
    with col3:
        st.markdown("#### 😊 高频情绪")
        if all_emotions:
            emotion_counts = pd.Series(all_emotions).value_counts().head(5)
            for emotion, count in emotion_counts.items():
                st.write(f"• {emotion}: {count}次")
        else:
            st.write("无数据")


def create_compact_table_view(segments_data: List[Dict[str, Any]]):
    """
    创建紧凑的表格视图（类似您图片中的格式）
    
    Args:
        segments_data: 片段分析数据列表
    """
    if not segments_data:
        st.warning("没有分析结果可显示")
        return
    
    st.markdown("### 📋 视频片段分析结果")
    
    # 创建紧凑格式的数据
    compact_data = []
    for i, segment in enumerate(segments_data):
        analysis = segment.get('analysis', {})
        
        # 获取主要标签（每类最多显示2个）
        objects = analysis.get('objects', [])[:2] if analysis.get('success') else []
        scenes = analysis.get('scenes', [])[:2] if analysis.get('success') else []
        emotions = analysis.get('emotions', [])[:2] if analysis.get('success') else []
        
        # 格式化显示
        object_display = '、'.join([f"{obj}🍼" for obj in objects]) if objects else '无'
        scene_display = '🏠'.join(scenes) if scenes else '无'
        emotion_display = '😊'.join(emotions) if emotions else '无'
        
        compact_data.append({
            '镜头序号': i + 1,
            '时长范围': f"{segment.get('start_time', 0):.1f}-{segment.get('end_time', 0):.1f}s",
            'Object (对象)': object_display,
            'Scene (场景)': scene_display,
            'Expression (表情)': emotion_display
        })
    
    # 显示紧凑表格
    df_compact = pd.DataFrame(compact_data)
    
    # 使用样式化的表格
    st.dataframe(
        df_compact,
        use_container_width=True,
        column_config={
            "镜头序号": st.column_config.NumberColumn(
                "镜头序号",
                width="small",
                help="片段序号"
            ),
            "时长范围": st.column_config.TextColumn(
                "时长范围", 
                width="medium",
                help="时间范围"
            ),
            "Object (对象)": st.column_config.TextColumn(
                "Object (对象)",
                width="large",
                help="检测到的主要物体"
            ),
            "Scene (场景)": st.column_config.TextColumn(
                "Scene (场景)",
                width="medium", 
                help="场景环境"
            ),
            "Expression (表情)": st.column_config.TextColumn(
                "Expression (表情)",
                width="medium",
                help="人物情绪表情"
            )
        },
        hide_index=True
    )
    
    return df_compact 