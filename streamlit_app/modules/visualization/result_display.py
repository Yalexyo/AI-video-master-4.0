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

from streamlit_app.config.config import get_paths_config, get_config, get_semantic_segment_types # 修改导入：使用动态获取的语义类型

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

def update_segment_transcript(filename, new_transcript):
    """
    更新指定片段的转录文本到元数据文件，并重新生成对应的SRT文件
    
    Args:
        filename: 片段文件名
        new_transcript: 新的转录文本
    """
    try:
        # 1. 更新元数据文件
        if METADATA_FILE.exists():
            with open(METADATA_FILE, 'r', encoding='utf-8') as f:
                metadata_list = json.load(f)
            
            # 找到对应的元数据条目并更新
            updated = False
            for item in metadata_list:
                if item['filename'] == filename:
                    item['transcript'] = new_transcript
                    updated = True
                    break
            
            if updated:
                # 保存更新后的元数据
                with open(METADATA_FILE, 'w', encoding='utf-8') as f:
                    json.dump(metadata_list, f, ensure_ascii=False, indent=2)
                
                # 2. 重新生成对应的SRT文件
                regenerate_srt_for_segment(item)
                
                st.success(f"✅ 已更新片段 {filename} 的转录文本并同步到SRT文件")
                return True
            else:
                st.warning(f"未找到文件名为 {filename} 的元数据条目")
                return False
        else:
            st.error("元数据文件不存在，无法更新")
            return False
            
    except Exception as e:
        st.error(f"更新转录文本失败: {str(e)}")
        return False

def regenerate_srt_for_segment(segment_metadata):
    """
    为单个片段重新生成SRT文件
    
    Args:
        segment_metadata: 片段的元数据字典
    """
    try:
        import logging
        logger = logging.getLogger(__name__)
        
        filename = segment_metadata.get('filename')
        transcript = segment_metadata.get('transcript', '')
        start_time_ms = segment_metadata.get('start_time_ms', 0)
        end_time_ms = segment_metadata.get('end_time_ms', 0)
        semantic_type = segment_metadata.get('type', '其他')
        
        if not transcript.strip():
            logger.warning(f"片段 {filename} 的转录文本为空，跳过SRT生成")
            return
        
        # 计算片段时长
        duration_ms = end_time_ms - start_time_ms if end_time_ms > start_time_ms else 5000  # 默认5秒
        
        # 生成SRT内容（从0开始计时）
        srt_content = f"""1
00:00:00,000 --> {format_duration_to_srt(duration_ms)}
{transcript}

"""
        
        # 确定SRT文件路径
        segment_dir = OUTPUT_DIR / semantic_type
        srt_file_path = segment_dir / f"{filename.replace('.mp4', '.srt')}"
        
        # 确保目录存在
        segment_dir.mkdir(parents=True, exist_ok=True)
        
        # 写入SRT文件
        with open(srt_file_path, 'w', encoding='utf-8') as f:
            f.write(srt_content)
        
        logger.info(f"已为片段 {filename} 重新生成SRT文件: {srt_file_path}")
        
    except Exception as e:
        st.error(f"重新生成SRT文件失败: {str(e)}")

def format_duration_to_srt(duration_ms):
    """
    将毫秒时长转换为SRT时间格式
    
    Args:
        duration_ms: 毫秒时长
        
    Returns:
        SRT格式的时间字符串
    """
    total_seconds = int(duration_ms // 1000)
    milliseconds = int(duration_ms % 1000)
    
    hours = total_seconds // 3600
    minutes = (total_seconds % 3600) // 60
    seconds = total_seconds % 60
    
    return f"{hours:02d}:{minutes:02d}:{seconds:02d},{milliseconds:03d}"

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

    # 使用动态获取的语义类型
    semantic_types = get_semantic_segment_types()
    for segment_type_folder in OUTPUT_DIR.iterdir():
        if segment_type_folder.is_dir() and segment_type_folder.name in semantic_types:
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
                        target_audiences = metadata.get("target_audiences", "未分析") # 保留目标人群字段
                        start_time_ms = metadata.get("start_time_ms") # 获取开始毫秒数
                        end_time_ms = metadata.get("end_time_ms")     # 获取结束毫秒数
                        # 新增：获取分析结果字段（片段级产品类型和卖点）
                        analyzed_product_type = metadata.get("analyzed_product_type", "")
                        analyzed_selling_points = metadata.get("analyzed_selling_points", [])
                        
                        segment_info = {
                            "type": semantic_type, # 或者 metadata.get("type")，应该是一致的
                            "path": video_file,
                            "filename": filename,
                            "original_video_id": original_video_id,
                            "time_info": time_info,
                            "transcript": transcript_text,
                            "target_audiences": target_audiences, # 保留目标人群字段（视频级）
                            "start_time_ms": start_time_ms,
                            "end_time_ms": end_time_ms,
                            # 新增：添加分析结果字段（片段级产品类型和卖点）
                            "analyzed_product_type": analyzed_product_type,
                            "analyzed_selling_points": analyzed_selling_points
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
                            "target_audiences": "N/A", # 确保占位符也有此字段
                            "start_time_ms": None,  # 占位符也应包含新字段
                            "end_time_ms": None,     # 占位符也应包含新字段
                            # 新增：为占位符添加分析结果字段
                            "analyzed_product_type": "",
                            "analyzed_selling_points": []
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
    """
    segments_data = get_all_segments_data()

    if not segments_data:
        st.info("没有找到可显示的视频片段。请先执行分析。")
        return

    # --- 初始化会话状态 ---
    if 'selected_target_audience_filter' not in st.session_state:
        st.session_state.selected_target_audience_filter = "全部目标人群" # 默认目标人群筛选
    if 'selected_segment_filter' not in st.session_state:
        st.session_state.selected_segment_filter = "显示全部" # 默认语义类型筛选
    if 'time_sort_order' not in st.session_state:
        st.session_state.time_sort_order = None

    # --- 第一层筛选：按目标人群 ---    
    st.subheader("按目标人群筛选")
    target_audience_cols_per_row = 5 
    ta_filter_buttons_cols = st.columns(target_audience_cols_per_row)
    
    current_target_audience_filter = st.session_state.selected_target_audience_filter

    # "全部目标人群" 按钮
    if ta_filter_buttons_cols[0].button("全部目标人群", 
                                        key="target_audience_all_btn", 
                                        use_container_width=True, 
                                        type="primary" if current_target_audience_filter == "全部目标人群" else "secondary"):
        st.session_state.selected_target_audience_filter = "全部目标人群"
        st.rerun()

    ta_col_idx = 1
    config = get_config()  # 获取完整配置
    for ta_type in config.get("TARGET_GROUPS", []): # 使用配置中的 TARGET_GROUPS
        if ta_col_idx >= target_audience_cols_per_row:
            ta_filter_buttons_cols = st.columns(target_audience_cols_per_row)
            ta_col_idx = 0
        
        if ta_filter_buttons_cols[ta_col_idx].button(ta_type, 
                                                    key=f"target_audience_{ta_type}_btn", 
                                                    use_container_width=True, 
                                                    type="primary" if current_target_audience_filter == ta_type else "secondary"):
            st.session_state.selected_target_audience_filter = ta_type
            st.rerun()
        ta_col_idx += 1

    # 应用目标人群筛选
    segments_after_target_audience_filter = []
    if current_target_audience_filter == "全部目标人群":
        segments_after_target_audience_filter = segments_data
    else:
        for segment in segments_data:
            # target_audiences 在元数据中是逗号分隔的字符串，或者列表
            # 确保能正确处理 "未知" 或 "N/A" 等情况
            segment_ta_str = segment.get("target_audiences", "")
            if isinstance(segment_ta_str, str):
                 # 假设 target_audiences 是逗号分隔的字符串，例如 "孕期妈妈, 新手爸妈"
                if current_target_audience_filter in [s.strip() for s in segment_ta_str.split(',')]:
                    segments_after_target_audience_filter.append(segment)
            elif isinstance(segment_ta_str, list): # 如果已经是列表
                if current_target_audience_filter in segment_ta_str:
                    segments_after_target_audience_filter.append(segment)
    
    if not segments_after_target_audience_filter:
        st.info(f"在目标人群 '{current_target_audience_filter}' 下没有找到片段。")
        # return # 不直接返回，允许用户更改语义类型筛选

    st.markdown("---", help="Semantic type filter below") # 分隔线

    # --- 第二层筛选：按语义类型 (基于上一层筛选结果) ---
    st.subheader("按语义类型筛选")
    cols_per_row = 5 
    filter_buttons_cols = st.columns(cols_per_row)
    
    current_semantic_filter = st.session_state.selected_segment_filter

    if filter_buttons_cols[0].button("显示全部", 
                                     key="sem_type_all_btn", 
                                     use_container_width=True, 
                                     type="primary" if current_semantic_filter == "显示全部" else "secondary"):
        st.session_state.selected_segment_filter = "显示全部"
        st.rerun() 

    col_idx = 1
    for seg_type in get_semantic_segment_types():
        if col_idx >= cols_per_row: 
            filter_buttons_cols = st.columns(cols_per_row)
            col_idx = 0
        
        if filter_buttons_cols[col_idx].button(seg_type, 
                                              key=f"sem_type_{seg_type}_btn", 
                                              use_container_width=True, 
                                              type="primary" if current_semantic_filter == seg_type else "secondary"):
            st.session_state.selected_segment_filter = seg_type
            st.rerun() 
        col_idx += 1
    
    # 应用语义类型筛选 (作用于已被目标人群筛选过的数据)
    filtered_segments = []
    if current_semantic_filter == "显示全部":
        filtered_segments = segments_after_target_audience_filter
    else:
        filtered_segments = [s for s in segments_after_target_audience_filter if s["type"] == current_semantic_filter]

    if not filtered_segments:
        st.info(f"在目标人群 '{current_target_audience_filter}' 和语义类型 '{current_semantic_filter}' 下没有找到视频片段。")
        return
        
    # 时长排序逻辑 (作用于最终筛选结果)
    def get_duration_ms(segment):
        """计算片段时长（毫秒）"""
        start_ms = segment.get('start_time_ms')
        end_ms = segment.get('end_time_ms')
        if start_ms is not None and end_ms is not None:
            try:
                return float(end_ms) - float(start_ms)
            except (ValueError, TypeError):
                return float('inf')  # 如果计算出错，放到最后
        return float('inf')  # 如果数据缺失，放到最后
    
    if st.session_state.time_sort_order == 'asc':
        # 升序：时长从小到大
        filtered_segments.sort(key=get_duration_ms)
    elif st.session_state.time_sort_order == 'desc':
        # 降序：时长从大到小
        filtered_segments.sort(key=get_duration_ms, reverse=True)

    # 定义列权重，用于按钮、表头和行数据，以确保对齐
    list_column_weights = [1.2, 1.0, 0.6, 1.8, 1.2, 1.2]  # 视频ID, 时间, 时长, 转录, 产品类型, 核心卖点

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

    # Duration header with sort selectbox - moved from time column for better UX
    with header_display_cols[2]:
        # 根据当前排序状态确定selectbox的默认选项
        current_sort = st.session_state.time_sort_order
        if current_sort is None:
            default_index = 0  # "⚪️ 不排序"
        elif current_sort == 'asc':
            default_index = 1  # "⬆️ 升序"
        else:  # 'desc'
            default_index = 2  # "⬇️ 降序"
        
        sort_option = st.selectbox(
            "时长排序",
            options=["⚪️ 不排序", "⬆️ 升序", "⬇️ 降序"],
            index=default_index,
            label_visibility="collapsed",
            key="time_sort_selectbox"
        )
        
        # 根据selectbox的选择更新session_state
        if sort_option == "⚪️ 不排序":
            new_sort_order = None
        elif sort_option == "⬆️ 升序":
            new_sort_order = 'asc'
        else:  # "⬇️ 降序"
            new_sort_order = 'desc'
        
        # 如果排序状态发生变化，更新并重新运行
        if st.session_state.time_sort_order != new_sort_order:
            st.session_state.time_sort_order = new_sort_order
            st.rerun()

    header_display_cols[3].markdown("**转录**")
    header_display_cols[4].markdown("**产品类型**")
    header_display_cols[5].markdown("**核心卖点**")

    st.divider()

    for index, row_data in enumerate(filtered_segments): # Iterate over original segment data
        data_row_cols = st.columns(list_column_weights) # 使用与表头相同的列权重
        
        # 视频ID - 显示 {视频ID名称}
        data_row_cols[0].markdown(f"**{{{row_data['original_video_id']}}}**")
        
        # 时间
        data_row_cols[1].write(row_data['time_info'])

        # 时长
        start_ms = row_data.get("start_time_ms")
        end_ms = row_data.get("end_time_ms")
        duration_str = "N/A"
        if start_ms is not None and end_ms is not None:
            try:
                duration_seconds = (float(end_ms) - float(start_ms)) / 1000.0
                duration_str = f"{duration_seconds:.2f} s" # 保留两位小数
            except (ValueError, TypeError):
                duration_str = "计算错误"
        data_row_cols[2].write(duration_str)
        
        # 转录
        original_transcript = row_data['transcript']
        
        # 为每个片段创建一个唯一的key用于on_change回调
        transcript_input_key = f"transcript_input_{index}_{row_data['filename']}"
        
        # 转录文本编辑区（带实时保存）
        current_transcript = data_row_cols[3].text_area(
            label=f"transcript_{index}_{row_data['filename']}",
            value=original_transcript,
            height=100,
            label_visibility='collapsed',
            key=transcript_input_key,
            help="转录文本会在您编辑完成后自动保存并同步到SRT文件"
        )
        
        # 检查是否有变化并自动保存
        if current_transcript != original_transcript:
            success = update_segment_transcript(row_data['filename'], current_transcript)
            if success:
                # 更新原始数据（这会在下次重新运行时生效）
                row_data['transcript'] = current_transcript
                # 显示保存状态提示
                data_row_cols[3].caption("💾 已自动保存")

        # 产品类型
        analyzed_product_type = row_data.get("analyzed_product_type", "")
        if analyzed_product_type:
            # 为产品类型创建标签
            tag_class = "tag-default"
            if "启赋水奶" in analyzed_product_type: 
                tag_class = "tag-启赋水奶"
            elif "启赋蕴淳" in analyzed_product_type: 
                tag_class = "tag-启赋蕴淳"
            elif "启赋蓝钻" in analyzed_product_type: 
                tag_class = "tag-启赋蓝钻"
            
            product_tag_html = f'<span class="tag {tag_class}" style="font-size: 0.75em; padding: 2px 6px;">{analyzed_product_type}</span>'
            data_row_cols[4].markdown(product_tag_html, unsafe_allow_html=True)
        else:
            data_row_cols[4].write("未识别")

        # 核心卖点
        analyzed_selling_points = row_data.get("analyzed_selling_points", [])
        if analyzed_selling_points:
            selling_points_text = "、".join(analyzed_selling_points)
            data_row_cols[5].text_area(
                label=f"selling_points_{index}_{row_data['filename']}",
                value=selling_points_text, 
                height=80, 
                label_visibility='collapsed'
            )
        else:
            data_row_cols[5].write("未识别")

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
        for stype in get_semantic_segment_types():
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