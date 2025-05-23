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
import json # 新增导入

from streamlit_app.config.config import SEMANTIC_SEGMENT_TYPES, get_paths_config

# 获取项目根目录和数据目录的配置
paths_config = get_paths_config()
PROJECT_ROOT = Path(paths_config.get("project_root", Path(__file__).parent.parent.parent.parent))
OUTPUT_DIR = PROJECT_ROOT / "data" / "output"
METADATA_FILE = OUTPUT_DIR / "video_segments_metadata.json" # 定义元数据文件路径

def load_segments_metadata():
    """加载视频片段元数据文件"""
    if METADATA_FILE.exists():
        try:
            with open(METADATA_FILE, 'r', encoding='utf-8') as f:
                metadata_list = json.load(f)
                # 将列表转换为以 filename 为键的字典，方便查找
                metadata_dict = {item['filename']: item for item in metadata_list}
                return metadata_dict
        except Exception as e:
            st.error(f"加载元数据文件失败: {METADATA_FILE}, 错误: {e}")
            return {}
    else:
        st.warning(f"元数据文件未找到: {METADATA_FILE}。请先运行分析以生成元数据。")
        return {}

def get_all_segments_data():
    """
    从 data/output 目录收集所有按语义类型组织的视频片段信息，并结合元数据。
    """
    all_segments = []
    segments_metadata = load_segments_metadata()

    if not OUTPUT_DIR.exists():
        st.warning(f"输出目录 {OUTPUT_DIR} 不存在，无法加载结果。")
        return all_segments

    if not segments_metadata:
        # 如果元数据加载失败或为空，可以提前返回或仅依赖文件系统（但会缺少详细信息）
        # 这里选择如果元数据为空，则不继续，因为时间等信息将无法获取
        st.info("元数据为空，无法加载片段的详细信息。")
        return all_segments

    for segment_type_folder in OUTPUT_DIR.iterdir():
        if segment_type_folder.is_dir() and segment_type_folder.name in SEMANTIC_SEGMENT_TYPES:
            semantic_type = segment_type_folder.name
            for video_file in segment_type_folder.iterdir():
                if video_file.is_file() and video_file.suffix.lower() == '.mp4':
                    filename = video_file.name
                    metadata = segments_metadata.get(filename)
                    
                    if metadata:
                        # 从元数据获取信息
                        time_info = metadata.get("time_info", "时间未知")
                        transcript_text = metadata.get("transcript", "转录待获取...")
                        original_video_id = metadata.get("original_video_id", "N/A")
                        product_types = metadata.get("product_types", "未分析") # 新增：获取产品类型
                        
                        segment_info = {
                            "type": semantic_type, # 或者 metadata.get("type")，应该是一致的
                            "path": video_file,
                            "filename": filename,
                            "original_video_id": original_video_id,
                            "time_info": time_info,
                            "transcript": transcript_text,
                            "product_types": product_types # 新增
                        }
                        all_segments.append(segment_info)
                    else:
                        # 如果元数据中没有此文件，可以选择跳过，或用占位符填充
                        st.warning(f"在元数据中未找到文件 {filename} 的信息，将使用占位符。")
                        # 占位符逻辑 (可选，或者直接跳过)
                        time_info_placeholder = "00:00:00.000 - 00:00:00.000"
                        transcript_placeholder = "元数据缺失，转录文本待获取..."
                        original_video_id_placeholder = filename.split('_')[0] if '_' in filename else "N/A_placeholder"
                        
                        segment_info_placeholder = {
                            "type": semantic_type,
                            "path": video_file,
                            "filename": filename,
                            "original_video_id": original_video_id_placeholder,
                            "time_info": time_info_placeholder,
                            "transcript": transcript_placeholder,
                        }
                        all_segments.append(segment_info_placeholder)
    
    # 去重（基于路径）- 实际上如果元数据是唯一的，这一步可能不需要了
    # 但保留以防万一
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
    # st.header("📊 分析结果可视化")

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
    # st.subheader("视频片段列表")

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

    # 定义列权重，用于按钮、表头和行数据，以确保对齐
    list_column_weights = [1.5, 1, 2, 1]  # 路径, 时间, 转录, 视频类型

    # --- "打开目录" Button (置于路径列头之上) ---
    button_row_cols = st.columns(list_column_weights)
    with button_row_cols[0]: # 将按钮放置在与"视频ID"列对应的位置
        st.markdown('<div class="custom-gray-open-dir-button-container">', unsafe_allow_html=True) # 新增的包裹div - 开始
        folder_to_open_for_button = OUTPUT_DIR
        current_filter = st.session_state.get('selected_segment_filter', "显示全部")
        potential_filtered_path = OUTPUT_DIR / current_filter
        if current_filter != "显示全部" and potential_filtered_path.is_dir():
            folder_to_open_for_button = potential_filtered_path
        
        if st.button("📁 打开目录", 
                      key="global_open_dir_button", 
                      help=f"打开目录: {folder_to_open_for_button}"): # 移除了 use_container_width 和 type
            open_folder_in_file_explorer(str(folder_to_open_for_button))
        st.markdown('</div>', unsafe_allow_html=True) # 新增的包裹div - 结束
    # 其他 button_row_cols (button_row_cols[1]到[3]) 保持空白，为按钮下方对应的表头留出空间感
    # 如果不希望按钮下方有大片空白，可以只为按钮定义一个更窄的列，但这可能导致与下方表头不对齐
    # 当前方式是让按钮行和表头行共享相同的列布局，按钮只在第一列显示。
    # 若要按钮行的其他列不留白，可以将按钮行独立于表头列定义，例如：
    # btn_col, _ = st.columns([1.5, sum(list_column_weights[1:])]) # 按钮列与路径列同宽，其余为空白
    # with btn_col: ... (button code) ...
    # 但目前的实现方式（共享列定义）能确保按钮严格在"路径"列头之上。

    # --- 列表头 ---
    header_display_cols = st.columns(list_column_weights)
    header_display_cols[0].markdown("**视频ID**")
    header_display_cols[1].markdown("**时间**")
    header_display_cols[2].markdown("**转录**")
    header_display_cols[3].markdown("**视频类型**")
    st.divider()

    for index, row_data in enumerate(filtered_segments): # Iterate over original segment data
        # r_col_path_id, r_col_button_spacer, r_col_time, r_col_transcript, r_col_type = st.columns([1.5, 0.9, 1, 2, 1]) # Match header column structure
        data_row_cols = st.columns(list_column_weights) # 使用与表头相同的列权重
        
        # 路径 - 显示 {视频ID名称}
        data_row_cols[0].markdown(f"**{{{row_data['original_video_id']}}}**")
        
        # 时间
        data_row_cols[1].write(row_data['time_info'])
        
        # 转录
        data_row_cols[2].text_area(
            label=f"transcript_{index}_{row_data['filename']}",
            value=row_data['transcript'], 
            height=100, 
            label_visibility='collapsed'
        )
        
        # 视频类型标签
        product_types_str = row_data.get("product_types", "N/A")
        if product_types_str and product_types_str != "N/A" and product_types_str != "未知":
            product_type_list = [pt.strip() for pt in product_types_str.split(',')]
            tags_html_list = []
            for p_type in product_type_list:
                tag_class = "tag-default"
                if "水奶" in p_type: tag_class = "tag-水奶"
                elif "蕴淳" in p_type: tag_class = "tag-蕴淳"
                elif "蓝钻" in p_type: tag_class = "tag-蓝钻"
                tags_html_list.append(f'<span class="tag {tag_class}" style="font-size: 0.75em; padding: 2px 6px;">{p_type}</span>')
            data_row_cols[3].markdown(" ".join(tags_html_list), unsafe_allow_html=True)
        else:
            data_row_cols[3].write(product_types_str)

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