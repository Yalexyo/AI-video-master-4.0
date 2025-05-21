"""
视频分析结果展示模块

此模块负责在 Streamlit 应用中以用户友好的方式展示视频分析的结果，
包括按语义类型筛选视频片段、显示片段详情（路径、时间、转录）等。
"""
import streamlit as st
import pandas as pd
import os
import platform
import subprocess
from pathlib import Path

from streamlit_app.config.config import SEMANTIC_SEGMENT_TYPES, get_paths_config

# 获取项目根目录和数据目录的配置
paths_config = get_paths_config()
PROJECT_ROOT = Path(paths_config.get("project_root", Path(__file__).parent.parent.parent.parent))
OUTPUT_DIR = PROJECT_ROOT / "data" / "output"

def get_all_segments_data():
    """
    从 data/output 目录收集所有按语义类型组织的视频片段信息。

    Returns:
        list: 包含所有视频片段信息的列表，每个元素是一个字典，
              格式如: {'type': '广告开场', 'path': Path_object, 'filename': 'filename.mp4', 
                       'time_info': '解析自文件名或元数据', 'transcript': '对应的转录文本'}
    """
    all_segments = []
    if not OUTPUT_DIR.exists():
        st.warning(f"输出目录 {OUTPUT_DIR} 不存在，无法加载结果。")
        return all_segments

    for segment_type_folder in OUTPUT_DIR.iterdir():
        if segment_type_folder.is_dir() and segment_type_folder.name in SEMANTIC_SEGMENT_TYPES:
            semantic_type = segment_type_folder.name
            for video_file in segment_type_folder.iterdir():
                if video_file.is_file() and video_file.suffix.lower() == '.mp4':
                    # TODO: 解析文件名获取原视频ID、分段索引、时间信息
                    # TODO: 根据视频ID和分段索引获取对应的转录文本
                    # 假设文件名格式为: {video_id}_semantic_seg_{segment_index}_{type_name}.mp4
                    # 或 {video_id}_seg_{segment_index}_..._{start_ms}_{end_ms}.mp4 (需要确认实际格式)
                    
                    # 临时占位符 - 需要替换为真实逻辑
                    time_info = "00:00:00.000 - 00:00:00.000" 
                    transcript_text = "转录文本待获取..."
                    
                    # 从文件名提取 video_id 和 segment_index (示例性，需调整)
                    parts = video_file.name.split('_')
                    original_video_id = parts[0] if parts else "N/A"
                    
                    segment_info = {
                        "type": semantic_type,
                        "path": video_file,
                        "filename": video_file.name,
                        "original_video_id": original_video_id,
                        "time_info": time_info, # 占位符
                        "transcript": transcript_text, # 占位符
                    }
                    all_segments.append(segment_info)
    
    # 去重（基于路径）
    unique_segments_dict = {segment['path']: segment for segment in all_segments}
    return list(unique_segments_dict.values())

def open_folder_in_file_explorer(folder_path: str):
    """
    在操作系统的文件浏览器中打开指定的文件夹。
    """
    try:
        if platform.system() == "Windows":
            subprocess.Popen(["explorer", os.path.normpath(folder_path)])
        elif platform.system() == "Darwin": # macOS
            subprocess.Popen(["open", os.path.normpath(folder_path)])
        elif platform.system() == "Linux":
            subprocess.Popen(["xdg-open", os.path.normpath(folder_path)])
        else:
            st.error(f"不支持的操作系统: {platform.system()}")
            return
        st.toast(f"已尝试打开文件夹: {folder_path}", icon="📂")
    except Exception as e:
        st.error(f"打开文件夹失败: {e}")

def display_results_interface(analysis_results=None):
    """
    主函数，用于在 Streamlit 页面上渲染分析结果界面。

    Args:
        analysis_results: 分析流程传递过来的结果数据，可能包含转录、时间等详细信息。
                         目前暂时未使用，后续用于填充转录和精确时间。
    """
    st.header("📊 分析结果可视化")

    segments_data = get_all_segments_data()

    if not segments_data:
        st.info("没有找到可显示的视频片段。请先执行分析。")
        return

    # 1. 语义类型筛选按钮
    st.subheader("按语义类型筛选")
    
    # 创建列用于筛选按钮，"显示全部" + 各个语义类型
    # 每行最多放 5 个筛选器（4个类型 + 1个可能的占位或下一个）
    cols_per_row = 5 
    filter_buttons_cols = st.columns(cols_per_row)
    
    selected_filter = st.session_state.get('selected_segment_filter', "显示全部")

    if filter_buttons_cols[0].button("显示全部", use_container_width=True, type="primary" if selected_filter == "显示全部" else "secondary"):
        selected_filter = "显示全部"
        st.session_state.selected_segment_filter = "显示全部"
        st.rerun() # 重新运行以应用筛选

    col_idx = 1
    for seg_type in SEMANTIC_SEGMENT_TYPES:
        if col_idx >= cols_per_row: # 简单处理换行逻辑，实际可能需要更复杂的布局
            filter_buttons_cols = st.columns(cols_per_row)
            col_idx = 0
        
        if filter_buttons_cols[col_idx].button(seg_type, use_container_width=True, type="primary" if selected_filter == seg_type else "secondary"):
            selected_filter = seg_type
            st.session_state.selected_segment_filter = seg_type
            st.rerun() # 重新运行以应用筛选
        col_idx += 1
    
    # 筛选数据
    if selected_filter == "显示全部":
        filtered_segments = segments_data
    else:
        filtered_segments = [s for s in segments_data if s["type"] == selected_filter]

    if not filtered_segments:
        st.info(f"没有找到类型为 '{selected_filter}' 的视频片段。")
        return
        
    # 2. 视频片段列表
    st.subheader("视频片段列表")

    # 为表格准备数据
    display_data = []
    for idx, segment in enumerate(filtered_segments):
        display_data.append({
            "片段ID": f"{segment['original_video_id']}_{segment['filename']}", # 确保唯一性
            "路径": str(segment['path']),
            "时间": segment['time_info'],
            "转录": segment['transcript'],
        })
    
    df = pd.DataFrame(display_data)

    if df.empty:
        st.info("没有可显示的片段数据。")
        return

    # 使用 st.columns 创建自定义表格布局以支持按钮
    # 表头
    header_cols = st.columns([3, 1, 2, 3]) # 权重：路径、操作、时间、转录
    header_cols[0].markdown("**路径**")
    header_cols[1].markdown("**操作**") # 用于"打开文件夹"按钮
    header_cols[2].markdown("**时间**")
    header_cols[3].markdown("**转录**")
    st.divider()

    for index, row_data in enumerate(filtered_segments): # Iterate over original segment data
        row_cols = st.columns([3, 1, 2, 3])
        
        # 路径 - 使用markdown模拟链接感，实际点击通过按钮
        row_cols[0].markdown(f"`{str(row_data['path'])}`")
        
        # 操作按钮
        folder_to_open = str(row_data['path'].parent)
        if row_cols[1].button("打开", key=f"open_folder_{index}_{row_data['filename']}", help=f"打开文件夹: {folder_to_open}", use_container_width=True):
            open_folder_in_file_explorer(folder_to_open)
            
        row_cols[2].write(row_data['time_info'])
        
        # 转录 - 使用st.expander来处理可能较长的文本
        with row_cols[3].expander("查看转录", expanded=False):
            st.markdown(f"```
{row_data['transcript']}
```")
        st.divider()

# --- 用于独立测试此模块的示例代码 ---
if __name__ == "__main__":
    # 模拟 Streamlit 会话状态
    if 'selected_segment_filter' not in st.session_state:
        st.session_state.selected_segment_filter = "显示全部"

    # 创建一些假的 output 数据用于测试
    test_output_dir = Path(__file__).parent.parent.parent.parent / "data" / "output_test_display"
    if not test_output_dir.exists():
        test_output_dir.mkdir(parents=True, exist_ok=True)
        for stype in SEMANTIC_SEGMENT_TYPES:
            type_folder = test_output_dir / stype
            type_folder.mkdir(exist_ok=True)
            for i in range(2):
                # 确保文件名包含可解析的 video_id 和 segment_index
                fake_video_id = f"vid{i+1}"
                fake_seg_idx = i
                fake_time_start = i * 1000
                fake_time_end = (i+1) * 1000 -1
                # 假设文件名包含这些信息用于解析
                # (fake_video_id, fake_seg_idx, stype, fake_time_start, fake_time_end)
                # 例如: vid1_seg0_广告开场_0_999.mp4 (这里的格式是假设的，get_all_segments_data 需要适配)
                # 为了简单，我们用基础格式
                (type_folder / f"{fake_video_id}_semantic_seg_{fake_seg_idx}_{stype.replace('/', '_')}.mp4").touch()

    # 替换真实的 OUTPUT_DIR 进行测试
    original_output_dir = OUTPUT_DIR
    OUTPUT_DIR = test_output_dir
    
    st.title("测试结果展示模块")
    display_results_interface()

    # 恢复 OUTPUT_DIR
    OUTPUT_DIR = original_output_dir
    # 清理测试数据 (可选)
    # import shutil
    # shutil.rmtree(test_output_dir) 