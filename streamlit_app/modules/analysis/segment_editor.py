"""
视频片段编辑器模块
用于显示、编辑和管理视频语义片段
"""

import streamlit as st
import pandas as pd
import os
import json
import subprocess
import platform
from typing import List, Dict, Any, Optional
from datetime import datetime

from streamlit_app.config.config import get_semantic_segment_types, DEFAULT_SEMANTIC_SEGMENT_TYPES, get_config


class SegmentEditor:
    """视频片段编辑器类"""
    
    def __init__(self):
        """初始化片段编辑器"""
        self.semantic_types = get_semantic_segment_types()
        # 从配置文件获取产品类型和核心卖点
        config = get_config()
        self.product_types = config.get("PRODUCT_TYPES", ["启赋水奶", "启赋蕴淳", "启赋蓝钻"])
        self.selling_points = config.get("SELLING_POINTS", ["HMO & 母乳低聚糖", "A2奶源", "品牌实力", "开盖即饮", "有机认证", "营养全面"])
        self.target_groups = config.get("TARGET_GROUPS", ["新手爸妈", "贵妇妈妈", "孕期妈妈", "二胎妈妈", "混养妈妈"])
        
    def render_segment_list(self, segments: List[Dict[str, Any]], video_id: str) -> Optional[List[Dict[str, Any]]]:
        """
        渲染片段列表编辑界面
        
        Args:
            segments: 视频片段列表
            video_id: 视频ID
            
        Returns:
            更新后的片段列表，如果没有更新则返回None
        """
        if not segments:
            st.warning("📭 暂无视频片段数据")
            return None
            
        # 创建编辑状态
        if f"segments_editing_{video_id}" not in st.session_state:
            st.session_state[f"segments_editing_{video_id}"] = self._prepare_segments_for_editing(segments)
        
        editing_segments = st.session_state[f"segments_editing_{video_id}"]
        
        # 操作按钮区域
        col1, col2, col3, col4 = st.columns([3, 1, 1, 1])
        with col1:
            st.markdown(f"**视频ID**: {video_id} | **片段数量**: {len(editing_segments)}")
        with col2:
            # 添加打开原始视频按钮
            if st.button("🎬 原始视频", key=f"original_video_{video_id}", help="打开原始完整视频"):
                self._open_original_video(video_id)
        with col3:
            if st.button("🔄 重置", key=f"reset_{video_id}"):
                st.session_state[f"segments_editing_{video_id}"] = self._prepare_segments_for_editing(segments)
                st.rerun()
        with col4:
            save_button = st.button("💾 保存更新", key=f"save_{video_id}", type="primary")
        
        # 表格头部
        st.markdown("---")
        
        # 创建表格
        with st.container():
            # 表头
            header_cols = st.columns([1, 2, 2, 2, 2])
            with header_cols[0]:
                st.markdown("**文件**")
            with header_cols[1]:
                st.markdown("**时间**")
            with header_cols[2]:
                st.markdown("**语义类型**")
            with header_cols[3]:
                st.markdown("**产品类型**")
            with header_cols[4]:
                st.markdown("**人群**")
            
            # 数据行 - 使用相同的列宽比例
            updated_segments = []
            for idx, segment in enumerate(editing_segments):
                row_cols = st.columns([1, 2, 2, 2, 2])
                
                # 文件按钮
                with row_cols[0]:
                    # 文件路径和播放按钮
                    file_path = segment.get('file_path', '')
                    
                    # 强制转换为字符串并去除空格
                    file_path = str(file_path).strip() if file_path else ''
                    
                    if file_path and os.path.exists(file_path):
                        file_name = os.path.basename(file_path)
                        # 使用链接样式显示文件名
                        if st.button(f"📁", key=f"path_{video_id}_{idx}", help=f"打开文件位置: {file_name}"):
                            self._open_file_location(file_path)
                    else:
                        # 如果文件路径为空或文件不存在，显示警告并尝试打开目录
                        if file_path:
                            directory = os.path.dirname(file_path)
                            expected_filename = os.path.basename(file_path)
                            if st.button(f"⚠️", key=f"missing_{video_id}_{idx}", help=f"文件不存在，点击打开目录查找: {expected_filename}"):
                                if os.path.exists(directory):
                                    self._open_file_location(directory)
                                else:
                                    st.error(f"目录也不存在: {directory}")
                        else:
                            st.text("⚠️")
                
                # 时间编辑
                with row_cols[1]:
                    # 使用HH:MM:SS格式显示时间
                    start_time_formatted = self._format_time(segment['start_time'])
                    end_time_formatted = self._format_time(segment['end_time'])
                    time_str = f"{start_time_formatted} - {end_time_formatted}"
                    
                    new_time = st.text_input(
                        "时间范围",
                        value=time_str,
                        key=f"time_{video_id}_{idx}",
                        label_visibility="collapsed",
                        help="时间格式：HH:MM:SS - HH:MM:SS，例如：00:01:30 - 00:02:45"
                    )
                    
                    # 解析时间
                    try:
                        if " - " in new_time:
                            start_str, end_str = new_time.split(" - ")
                            # 解析HH:MM:SS格式
                            segment['start_time'] = self._parse_time_string(start_str.strip())
                            segment['end_time'] = self._parse_time_string(end_str.strip())
                    except:
                        pass  # 保持原值
                
                # 语义类型（多选）
                with row_cols[2]:
                    semantic_options = list(self.semantic_types)
                    current_semantic = segment.get('semantic_type', '其他')
                    
                    # 确保当前值在选项中
                    if current_semantic not in semantic_options:
                        semantic_options.append(current_semantic)
                    
                    selected_semantic = st.selectbox(
                        "语义类型",
                        options=semantic_options,
                        index=semantic_options.index(current_semantic) if current_semantic in semantic_options else 0,
                        key=f"semantic_{video_id}_{idx}",
                        label_visibility="collapsed"
                    )
                    segment['semantic_type'] = selected_semantic
                
                # 产品类型（单选）
                with row_cols[3]:
                    # 确保产品类型选项包含"未识别"
                    product_types = ["未识别"] + self.product_types
                    current_product = segment.get('product_type', '未识别')
                    
                    # 确保当前值在选项中
                    if current_product not in product_types:
                        product_types.append(current_product)
                    
                    selected_product = st.selectbox(
                        "产品类型",
                        options=product_types,
                        index=product_types.index(current_product) if current_product in product_types else 0,
                        key=f"product_type_{video_id}_{idx}",
                        label_visibility="collapsed",
                        help="选择产品类型"
                    )
                    segment['product_type'] = selected_product
                
                # 人群（单选）
                with row_cols[4]:
                    audience_options = self.target_groups
                    current_audience = segment.get('target_audience', '新手爸妈')
                    
                    if current_audience not in audience_options:
                        audience_options.append(current_audience)
                    
                    selected_audience = st.selectbox(
                        "目标人群",
                        options=audience_options,
                        index=audience_options.index(current_audience) if current_audience in audience_options else 0,
                        key=f"audience_{video_id}_{idx}",
                        label_visibility="collapsed"
                    )
                    segment['target_audience'] = selected_audience
                
                updated_segments.append(segment)
            
            # 更新session_state
            st.session_state[f"segments_editing_{video_id}"] = updated_segments
        
        # 处理保存按钮
        if save_button:
            # 调用保存方法，显示成功提示和保存路径
            saved_segments = self._save_segment_updates(updated_segments, video_id)
            if saved_segments:
                return saved_segments
            else:
                return None
        
        return None
    
    def _prepare_segments_for_editing(self, segments: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        准备片段数据用于编辑
        
        Args:
            segments: 原始片段列表
            
        Returns:
            准备好的编辑数据
        """
        editing_segments = []
        for i, segment in enumerate(segments):
            editing_segment = {
                'index': i,
                'original_semantic_type': segment.get('semantic_type', '其他'),
                'semantic_type': segment.get('semantic_type', '其他'),
                'start_time': segment.get('start_time', 0.0),
                'end_time': segment.get('end_time', 0.0),
                'time_period': segment.get('time_period', ''),
                'text': segment.get('text', ''),
                'file_path': segment.get('file_path', ''),
                'confidence': segment.get('confidence', 0.0),
                'product_type': segment.get('product_type', '-'),
                'target_audience': segment.get('target_audience', '新手爸妈'),
                'modified': False
            }
            editing_segments.append(editing_segment)
        
        return editing_segments
    
    def _render_segment_row(self, segment: Dict[str, Any], index: int, video_id: str):
        """
        渲染单个片段行
        
        Args:
            segment: 片段数据
            index: 片段索引
            video_id: 视频ID
        """
        row_cols = st.columns([3, 2, 3, 2, 2])
        
        with row_cols[0]:
            # 文件路径和播放按钮
            file_path = segment.get('file_path', '')
            if file_path and os.path.exists(file_path):
                file_name = os.path.basename(file_path)
                # 使用链接样式显示文件名
                if st.button(f"📁", key=f"path_{video_id}_{index}", help=f"打开文件位置: {file_name}"):
                    self._open_file_location(file_path)
            else:
                # 如果文件路径为空或文件不存在，显示警告并尝试打开目录
                if file_path:
                    directory = os.path.dirname(file_path)
                    expected_filename = os.path.basename(file_path)
                    if st.button(f"⚠️", key=f"missing_{video_id}_{index}", help=f"文件不存在，点击打开目录查找: {expected_filename}"):
                        if os.path.exists(directory):
                            self._open_file_location(directory)
                        else:
                            st.error(f"目录也不存在: {directory}")
                else:
                    st.text("⚠️")
        
        with row_cols[1]:
            # 时间编辑（紧凑布局）
            start_time = st.number_input(
                "开始时间",
                value=float(segment['start_time']),
                min_value=0.0,
                step=0.1,
                key=f"start_time_{video_id}_{index}",
                label_visibility="collapsed",
                help="开始时间(秒)"
            )
            
            end_time = st.number_input(
                "结束时间",
                value=float(segment['end_time']),
                min_value=start_time,
                step=0.1,
                key=f"end_time_{video_id}_{index}",
                label_visibility="collapsed",
                help="结束时间(秒)"
            )
            
            # 显示时间段
            time_display = f"{self._format_time(start_time)} - {self._format_time(end_time)}"
            st.caption(time_display)
        
        with row_cols[2]:
            # 语义类型多选
            current_types = [segment['semantic_type']] if segment['semantic_type'] else []
            
            selected_types = st.multiselect(
                "语义类型",
                options=list(self.semantic_types),
                default=current_types,
                key=f"semantic_types_{video_id}_{index}",
                label_visibility="collapsed",
                help="选择语义类型（可多选）"
            )
        
        with row_cols[3]:
            # 产品类型单选
            product_types = ["未识别"] + self.product_types
            current_product = segment.get('product_type', '未识别')
            
            # 确保当前值在选项中
            if current_product not in product_types:
                product_types.append(current_product)
            
            selected_product = st.selectbox(
                "产品类型",
                options=product_types,
                index=product_types.index(current_product) if current_product in product_types else 0,
                key=f"product_type_{video_id}_{index}",
                label_visibility="collapsed",
                help="选择产品类型"
            )
        
        with row_cols[4]:
            # 人群单选
            audience_options = self.target_groups
            current_audience = segment.get('target_audience', '新手爸妈')
            
            selected_audience = st.selectbox(
                "目标人群",
                options=audience_options,
                index=audience_options.index(current_audience) if current_audience in audience_options else 0,
                key=f"target_audience_{video_id}_{index}",
                label_visibility="collapsed",
                help="选择目标人群"
            )
        
        # 检查是否有修改并更新session_state
        if (start_time != segment['start_time'] or 
            end_time != segment['end_time'] or 
            selected_types != [segment['semantic_type']] or
            selected_product != segment.get('product_type', '-') or
            selected_audience != segment.get('target_audience', '新手爸妈')):
            
            # 更新session_state中的数据
            editing_segments = st.session_state[f"segments_editing_{video_id}"]
            editing_segments[index].update({
                'start_time': start_time,
                'end_time': end_time,
                'semantic_type': selected_types[0] if selected_types else '其他',
                'semantic_types': selected_types,
                'product_type': selected_product,
                'target_audience': selected_audience,
                'time_period': f"{self._format_time(start_time)} - {self._format_time(end_time)}",
                'modified': True
            })
            
            # 在行末显示修改标识
            st.markdown("✏️ *已修改*", help="此片段已被修改")
    
    def _save_segment_updates(self, editing_segments: List[Dict[str, Any]], video_id: str) -> Optional[List[Dict[str, Any]]]:
        """
        保存片段更新并记录用户反馈
        
        Args:
            editing_segments: 编辑后的片段列表
            video_id: 视频ID
            
        Returns:
            更新后的片段列表
        """
        try:
            # 检查是否有修改
            modified_segments = [seg for seg in editing_segments if seg.get('modified', False)]
            
            if not modified_segments:
                st.warning("⚠️ 没有检测到任何修改")
                return None
            
            # 保存用户反馈数据
            feedback_data = {
                'video_id': video_id,
                'timestamp': datetime.now().isoformat(),
                'modifications': []
            }
            
            for segment in modified_segments:
                modification = {
                    'segment_index': segment['index'],
                    'original_semantic_type': segment['original_semantic_type'],
                    'new_semantic_type': segment['semantic_type'],
                    'new_semantic_types': segment.get('semantic_types', []),
                    'original_start_time': segment.get('original_start_time', segment['start_time']),
                    'new_start_time': segment['start_time'],
                    'original_end_time': segment.get('original_end_time', segment['end_time']),
                    'new_end_time': segment['end_time'],
                    'text': segment['text']
                }
                feedback_data['modifications'].append(modification)
            
            # 保存反馈数据
            feedback_file = self._save_feedback_data(feedback_data)
            
            # 显示成功提示和保存路径
            st.success(f"✅ 保存成功！已保存 {len(modified_segments)} 个片段的修改")
            st.info(f"📁 保存路径: `{feedback_file}`")
            
            # 转换为标准片段格式
            updated_segments = []
            for segment in editing_segments:
                updated_segment = {
                    'semantic_type': segment['semantic_type'],
                    'start_time': segment['start_time'],
                    'end_time': segment['end_time'],
                    'time_period': segment['time_period'],
                    'text': segment['text'],
                    'file_path': segment['file_path'],
                    'confidence': segment.get('confidence', 0.0),
                    'user_modified': segment.get('modified', False)
                }
                updated_segments.append(updated_segment)
            
            return updated_segments
            
        except Exception as e:
            st.error(f"保存失败: {str(e)}")
            return None
    
    def _save_feedback_data(self, feedback_data: Dict[str, Any]) -> str:
        """
        保存用户反馈数据到文件
        
        Args:
            feedback_data: 反馈数据
            
        Returns:
            保存的文件路径
        """
        feedback_dir = "data/user_feedback"
        os.makedirs(feedback_dir, exist_ok=True)
        
        feedback_file = os.path.join(feedback_dir, "segment_corrections.json")
        
        # 读取现有数据
        existing_data = []
        if os.path.exists(feedback_file):
            try:
                with open(feedback_file, 'r', encoding='utf-8') as f:
                    existing_data = json.load(f)
            except (json.JSONDecodeError, FileNotFoundError):
                existing_data = []
        
        # 添加新数据
        existing_data.append(feedback_data)
        
        # 保存数据
        with open(feedback_file, 'w', encoding='utf-8') as f:
            json.dump(existing_data, f, ensure_ascii=False, indent=2)
        
        return feedback_file
    
    def _open_video_file(self, file_path: str):
        """
        打开视频文件
        
        Args:
            file_path: 视频文件路径
        """
        try:
            if platform.system() == "Darwin":  # macOS
                subprocess.run(["open", file_path])
            elif platform.system() == "Windows":
                os.startfile(file_path)
            else:  # Linux
                subprocess.run(["xdg-open", file_path])
        except Exception as e:
            st.error(f"无法打开文件: {str(e)}")
    
    def _open_original_video(self, video_id: str):
        """
        打开原始完整视频文件
        
        Args:
            video_id: 视频ID
        """
        try:
            # 更新后的视频文件路径（重组后的结构）
            possible_paths = [
                f"data/processed/segments/{video_id}/original_{video_id}.mp4",  # 重组后的主要路径
                f"data/processed/segments/{video_id}/{video_id}.mp4",           # 备用路径1
                f"data/temp/uploads/{video_id}.mp4",                            # 备用路径2（如果还在uploads）
                f"data/input/test_videos/{video_id}.mp4"                        # 备用路径3
            ]
            
            # 查找存在的视频文件
            video_path = None
            for path in possible_paths:
                if os.path.exists(path):
                    video_path = path
                    break
            
            if video_path:
                # 使用系统默认程序打开视频
                system = platform.system()
                if system == "Darwin":  # macOS
                    subprocess.run(["open", video_path])
                elif system == "Windows":
                    os.startfile(video_path)
                elif system == "Linux":
                    subprocess.run(["xdg-open", video_path])
                else:
                    st.warning(f"⚠️ 不支持的操作系统: {system}")
            else:
                # 如果找不到视频文件，尝试打开segments目录
                segments_dir = f"data/processed/segments/{video_id}"
                if os.path.exists(segments_dir):
                    # 使用文件定位功能打开目录
                    system = platform.system()
                    if system == "Darwin":  # macOS
                        subprocess.run(["open", segments_dir])
                    elif system == "Windows":
                        subprocess.run(["explorer", segments_dir])
                    elif system == "Linux":
                        subprocess.run(["xdg-open", segments_dir])
                    
                    st.info(f"📁 未找到原始视频文件，已打开视频目录: {segments_dir}")
                    
                    # 显示目录中的文件列表
                    try:
                        files = os.listdir(segments_dir)
                        st.write("📋 目录中的文件:")
                        for file in files:
                            st.write(f"  • {file}")
                    except:
                        pass
                else:
                    st.error(f"❌ 未找到视频ID {video_id} 对应的原始视频文件和目录")
                    
        except Exception as e:
            st.error(f"❌ 打开原始视频失败: {e}")
    
    def _open_segments_folder(self, video_id: str):
        """
        打开片段文件夹
        
        Args:
            video_id: 视频ID
        """
        folder_path = f"data/processed/segments/{video_id}"
        if os.path.exists(folder_path):
            try:
                if platform.system() == "Darwin":  # macOS
                    subprocess.run(["open", folder_path])
                elif platform.system() == "Windows":
                    os.startfile(folder_path)
                else:  # Linux
                    subprocess.run(["xdg-open", folder_path])
            except Exception as e:
                st.error(f"无法打开文件夹: {str(e)}")
        else:
            st.error(f"文件夹不存在: {folder_path}")
    
    def _format_time(self, seconds: float) -> str:
        """
        格式化时间显示
        
        Args:
            seconds: 秒数
            
        Returns:
            格式化的时间字符串 (HH:MM:SS)
        """
        hours = int(seconds // 3600)
        minutes = int((seconds % 3600) // 60)
        secs = int(seconds % 60)
        return f"{hours:02d}:{minutes:02d}:{secs:02d}"
    
    def _parse_time_string(self, time_str: str) -> float:
        """
        解析时间字符串为秒数
        
        Args:
            time_str: 时间字符串，格式为 HH:MM:SS 或 MM:SS 或纯秒数
            
        Returns:
            秒数
        """
        try:
            time_str = time_str.strip()
            
            # 如果是纯数字，直接返回
            if time_str.replace('.', '').isdigit():
                return float(time_str)
            
            # 解析 HH:MM:SS 或 MM:SS 格式
            if ':' in time_str:
                parts = time_str.split(':')
                if len(parts) == 3:  # HH:MM:SS
                    hours, minutes, seconds = map(float, parts)
                    return hours * 3600 + minutes * 60 + seconds
                elif len(parts) == 2:  # MM:SS
                    minutes, seconds = map(float, parts)
                    return minutes * 60 + seconds
            
            # 如果解析失败，返回0
            return 0.0
        except:
            return 0.0
    
    def _open_file_location(self, file_path: str) -> None:
        """
        打开文件所在位置并选中文件
        
        Args:
            file_path: 文件路径
        """
        try:
            import subprocess
            import platform
            
            # 检查文件是否存在
            if not os.path.exists(file_path):
                # 如果文件不存在，尝试打开预期的目录
                directory = os.path.dirname(file_path)
                if not os.path.exists(directory):
                    st.error(f"文件和目录都不存在: {file_path}")
                    return
                else:
                    # 只打开目录
                    system = platform.system()
                    if system == "Darwin":  # macOS
                        subprocess.run(["open", directory])
                    elif system == "Windows":
                        subprocess.run(["explorer", directory])
                    elif system == "Linux":
                        subprocess.run(["xdg-open", directory])
                    return
            
            # 根据操作系统打开文件夹并选中文件
            system = platform.system()
            if system == "Darwin":  # macOS
                # 使用 -R 参数在Finder中选中文件
                subprocess.run(["open", "-R", file_path])
            elif system == "Windows":
                # 使用 /select 参数在资源管理器中选中文件
                subprocess.run(["explorer", "/select,", file_path])
            elif system == "Linux":
                # Linux上大多数文件管理器不支持直接选中文件，只能打开目录
                directory = os.path.dirname(file_path)
                subprocess.run(["xdg-open", directory])
            else:
                st.warning(f"不支持的操作系统: {system}")
                
        except Exception as e:
            st.error(f"打开文件位置失败: {e}")
            # 兜底方案：尝试只打开目录
            try:
                directory = os.path.dirname(file_path)
                if os.path.exists(directory):
                    system = platform.system()
                    if system == "Darwin":
                        subprocess.run(["open", directory])
                    elif system == "Windows":
                        subprocess.run(["explorer", directory])
                    elif system == "Linux":
                        subprocess.run(["xdg-open", directory])
            except Exception as e2:
                st.error(f"兜底方案也失败了: {e2}")


def render_segment_editor(segments: List[Dict[str, Any]], video_id: str) -> Optional[List[Dict[str, Any]]]:
    """
    渲染片段编辑器的主函数
    
    Args:
        segments: 视频片段列表
        video_id: 视频ID
        
    Returns:
        更新后的片段列表
    """
    editor = SegmentEditor()
    return editor.render_segment_list(segments, video_id) 