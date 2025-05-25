import os
import json
import logging
from pathlib import Path
from streamlit_app.config.config import get_paths_config

# Logger will be passed from the calling module (e.g., app.py)
# logger = logging.getLogger(__name__) # Avoid creating a new logger instance here

def format_ms_time(ms_value):
    """将毫秒时间转换为 HH:MM:SS.mmm 格式"""
    if ms_value is None:
        return "时间未知"
    try:
        # Ensure ms_value is an integer or float
        ms_value = float(ms_value)
    except (ValueError, TypeError):
        return "时间格式无效"

    s, ms_part = divmod(ms_value, 1000)
    m, s = divmod(s, 60)
    h, m = divmod(m, 60)
    return f"{int(h):02d}:{int(m):02d}:{int(s):02d}.{int(ms_part):03d}"

def save_detailed_segments_metadata(all_videos_analysis_data, root_dir, logger):
    """
    保存所有视频片段的详细元数据到 JSON 文件。

    Args:
        all_videos_analysis_data (list): 包含所有视频分析数据的列表。
                                         每个视频数据字典应包含 "video_id" 和 "semantic_segments"。
                                         "semantic_segments" 是一个字典，键是语义类型，值是片段详情列表。
                                         每个片段详情字典应包含 "segment_path", "asr_matched_text" (或 "text"),
                                         "start_time" (秒), "end_time" (秒)。
        root_dir (str): 项目的根目录路径。
        logger (logging.Logger): 用于日志记录的Logger实例。
    """
    if not all_videos_analysis_data:
        logger.info("没有分析数据可供保存元数据。")
        return False # 返回 False 表示没有数据或未执行保存

    current_run_segments_metadata = [] # 存储当前运行分析得出的元数据
    output_root_dir = os.path.join(root_dir, "data", "output")

    for video_data in all_videos_analysis_data:
        original_video_id = video_data.get("video_id", "N/A")
        semantic_segments = video_data.get("semantic_segments", {})
        
        # 修正：确保从 video_data 中获取目标人群时使用 "target_audiences" 键
        llm_analyzed_target_audiences = video_data.get("target_audiences", []) # 默认为空列表  
        target_audiences_str = ", ".join(llm_analyzed_target_audiences) if llm_analyzed_target_audiences else "未知"

        if not semantic_segments:
            logger.debug(f"视频 {original_video_id} 没有语义分段信息，跳过元数据保存。")
            continue

        for semantic_type, segments_in_module in semantic_segments.items():
            for segment_detail in segments_in_module:
                transcript_text = segment_detail.get('asr_matched_text', segment_detail.get('text', "转录待定"))
                
                # start_time 和 end_time 从 segment_detail 中获取的是秒
                start_time_seconds = segment_detail.get('start_time')
                end_time_seconds = segment_detail.get('end_time')

                # 转换为毫秒以供 format_ms_time 使用
                start_time_ms = start_time_seconds * 1000 if start_time_seconds is not None else None
                end_time_ms = end_time_seconds * 1000 if end_time_seconds is not None else None
                
                time_info_str = f"{format_ms_time(start_time_ms)} - {format_ms_time(end_time_ms)}"

                segment_full_path = segment_detail.get("segment_path")
                segment_filename = os.path.basename(segment_full_path) if segment_full_path else f"{original_video_id}_seg_UNKNOWN_{semantic_type}.mp4"
                
                if not segment_full_path:
                    logger.warning(f"片段详情缺少 segment_path: {segment_detail}, 使用占位文件名: {segment_filename}")

                current_run_segments_metadata.append({
                    "type": semantic_type,
                    "filename": segment_filename,
                    "original_video_id": original_video_id,
                    "time_info": time_info_str,
                    "transcript": transcript_text,
                    # 保留 start_time_ms 和 end_time_ms 以便 SRT 生成更精确
                    "start_time_ms": start_time_ms,
                    "end_time_ms": end_time_ms,
                    # 移除视频级产品类型字段，因为现在只在片段级分析产品类型
                    "target_audiences": target_audiences_str # 保留目标人群字段（视频级分析）
                })
    
    if not current_run_segments_metadata:
        logger.info("当前分析运行没有产生有效的片段元数据可保存。")
        return True # 逻辑上没有失败，只是没新东西，但可能需要保存旧数据（如果存在）

    metadata_file_path = os.path.join(output_root_dir, "video_segments_metadata.json")
    final_metadata_to_save = []
    processed_video_ids_in_current_run = {item['original_video_id'] for item in current_run_segments_metadata}

    # 1. 尝试加载现有元数据
    existing_metadata = []
    if os.path.exists(metadata_file_path):
        try:
            with open(metadata_file_path, 'r', encoding='utf-8') as f:
                existing_metadata = json.load(f)
            logger.info(f"已加载现有的元数据，共 {len(existing_metadata)} 条记录。")
        except json.JSONDecodeError:
            logger.warning(f"现有的元数据文件 {metadata_file_path} 格式不正确，将作为空文件处理。")
        except Exception as e_load:
            logger.error(f"加载现有元数据文件 {metadata_file_path} 失败: {e_load}", exc_info=True)
            # 如果加载失败，为了数据安全，可以选择不继续，或者只保存当前运行的数据
            # 这里选择继续，但只使用当前运行的数据，以避免损坏旧数据（如果文件存在但无法读取）
            pass # 将 existing_metadata 保持为空列表

    # 2. 合并元数据：保留未在当前运行中处理的旧视频的元数据
    if existing_metadata:
        for old_item in existing_metadata:
            if old_item.get('original_video_id') not in processed_video_ids_in_current_run:
                final_metadata_to_save.append(old_item)
        logger.info(f"保留了 {len(final_metadata_to_save)} 条来自未被本次分析覆盖的旧视频的元数据。")

    # 3. 添加/替换当前运行分析的视频的元数据
    final_metadata_to_save.extend(current_run_segments_metadata)
    logger.info(f"合并后，最终元数据共 {len(final_metadata_to_save)} 条记录。")

    if not final_metadata_to_save:
        logger.info("最终没有元数据可保存（可能是初始运行且无数据，或合并后为空）。")
        # 确保空文件也被写入，以便下游知道是空的
        # os.makedirs(output_root_dir, exist_ok=True)
        # with open(metadata_file_path, 'w', encoding='utf-8') as f:
        #     json.dump([], f, ensure_ascii=False, indent=4)
        return True # 没有失败，只是没内容

    try:
        os.makedirs(output_root_dir, exist_ok=True) # 确保输出目录存在
        with open(metadata_file_path, 'w', encoding='utf-8') as f:
            json.dump(final_metadata_to_save, f, ensure_ascii=False, indent=4)
        logger.info(f"已将合并后的详细片段元数据保存到: {metadata_file_path}")
        return True
    except Exception as e:
        logger.error(f"保存详细片段元数据失败: {e}", exc_info=True)
        return False

# --- 新增 SRT 生成功能 ---

def _time_str_to_seconds(time_str: str) -> float:
    """将 HH:MM:SS.mmm 或 HH:MM:SS,mmm 格式的时间字符串转换为总秒数"""
    if not time_str or not isinstance(time_str, str):
        return 0.0
    time_str = time_str.replace(',', '.') # 兼容逗号作为毫秒分隔符
    parts = time_str.split(':')
    try:
        if len(parts) == 3:
            h = int(parts[0])
            m = int(parts[1])
            s_ms = parts[2].split('.')
            s = int(s_ms[0])
            ms = int(s_ms[1]) if len(s_ms) > 1 else 0
            return h * 3600 + m * 60 + s + ms / 1000.0
        elif len(parts) == 2: # MM:SS.mmm
            m = int(parts[0])
            s_ms = parts[1].split('.')
            s = int(s_ms[0])
            ms = int(s_ms[1]) if len(s_ms) > 1 else 0
            return m * 60 + s + ms / 1000.0
        elif len(parts) == 1: # SS.mmm
            s_ms = parts[0].split('.')
            s = int(s_ms[0])
            ms = int(s_ms[1]) if len(s_ms) > 1 else 0
            return s + ms / 1000.0
    except ValueError:
        # 如果解析失败，可以记录一个警告或返回0
        # logger.warning(f"无法解析时间字符串: {time_str}") # logger 需要传递进来
        return 0.0
    return 0.0


def _seconds_to_srt_time_format(total_seconds: float) -> str:
    """将总秒数转换为 SRT 的 HH:MM:SS,mmm 格式"""
    if total_seconds < 0:
        total_seconds = 0
    hours = int(total_seconds // 3600)
    minutes = int((total_seconds % 3600) // 60)
    seconds = int(total_seconds % 60)
    milliseconds = int((total_seconds - int(total_seconds)) * 1000)
    return f"{hours:02d}:{minutes:02d}:{seconds:02d},{milliseconds:03d}"

def create_srt_files_for_segments(root_dir, logger):
    """
    根据 video_segments_metadata.json 为每个片段创建 SRT 字幕文件。
    SRT 文件将保存在 data/output/{语义类型}/{segment_filename_without_ext}.srt
    
    🆕 修复：SRT文件现在保持原始视频的时间偏移，而不是从00:00:00重新开始

    Args:
        root_dir (Path or str): 项目的根目录。
        logger: 日志记录器实例。
    """
    root_dir = Path(root_dir)
    output_dir = root_dir / "data" / "output"
    metadata_file_path = output_dir / "video_segments_metadata.json"

    if not metadata_file_path.exists():
        logger.warning(f"元数据文件 {metadata_file_path} 不存在，无法生成 SRT 文件。")
        return

    try:
        with open(metadata_file_path, 'r', encoding='utf-8') as f:
            segments_metadata = json.load(f)
    except Exception as e:
        logger.error(f"加载元数据文件 {metadata_file_path} 失败: {e}", exc_info=True)
        return

    if not segments_metadata:
        logger.info("元数据为空，没有 SRT 文件可生成。")
        return

    srt_files_created_count = 0
    for segment_meta in segments_metadata:
        try:
            segment_filename = segment_meta.get("filename")
            original_video_id = segment_meta.get("original_video_id")
            time_info_str = segment_meta.get("time_info") # "HH:MM:SS.mmm - HH:MM:SS.mmm"
            transcript_text = segment_meta.get("transcript")
            semantic_type = segment_meta.get("type") # 获取语义类型
            start_time_ms = segment_meta.get("start_time_ms")
            end_time_ms = segment_meta.get("end_time_ms")

            if not all([segment_filename, original_video_id, transcript_text, semantic_type]):
                logger.warning(f"片段元数据不完整，跳过 SRT 生成: {segment_meta.get('filename', '未知文件名')}")
                continue

            # 🆕 修复：使用原始视频中的实际时间，而不是从0开始
            if start_time_ms is not None and end_time_ms is not None:
                # 使用毫秒时间戳
                original_start_seconds = float(start_time_ms) / 1000.0
                original_end_seconds = float(end_time_ms) / 1000.0
            elif time_info_str and " - " in time_info_str:
                # 从时间字符串解析
                time_parts = time_info_str.split(" - ")
                if len(time_parts) != 2:
                    logger.warning(f"时间信息格式不正确 '{time_info_str}' for {segment_filename}，跳过 SRT 生成。")
                    continue
                original_start_seconds = _time_str_to_seconds(time_parts[0])
                original_end_seconds = _time_str_to_seconds(time_parts[1])
            else:
                logger.warning(f"无法获取时间信息 for {segment_filename}，跳过 SRT 生成。")
                continue

            # 🆕 关键修复：SRT文件保持原始视频的时间偏移
            srt_start_time = _seconds_to_srt_time_format(original_start_seconds)
            srt_end_time = _seconds_to_srt_time_format(original_end_seconds)

            # 生成SRT内容，使用原始视频的时间戳
            srt_content = f"1\n{srt_start_time} --> {srt_end_time}\n{transcript_text}\n\n"

            # 构建SRT文件的目标路径
            srt_parent_dir = output_dir / semantic_type
            srt_parent_dir.mkdir(parents=True, exist_ok=True)

            srt_filename = Path(segment_filename).stem + ".srt"
            srt_file_path = srt_parent_dir / srt_filename

            with open(srt_file_path, 'w', encoding='utf-8') as f:
                f.write(srt_content)
            
            srt_files_created_count += 1
            logger.debug(f"已生成SRT文件: {srt_file_path} (时间: {srt_start_time} --> {srt_end_time})")

        except Exception as e:
            logger.error(f"为片段 {segment_meta.get('filename', '未知')} 生成 SRT 时出错: {e}", exc_info=True)
            continue
    
    if srt_files_created_count > 0:
        logger.info(f"SRT 文件生成完成。共创建 {srt_files_created_count} 个 SRT 文件，现在保持原始视频时间偏移。")
    else:
        logger.info("没有新的 SRT 文件被创建（可能元数据为空或已处理）。")

def update_metadata_with_analysis_results(analyzed_segments, root_dir, logger):
    """
    更新元数据文件，添加片段分析结果（产品类型和核心卖点）
    
    Args:
        analyzed_segments (list): 包含分析结果的片段列表
        root_dir (str): 项目根目录
        logger: 日志记录器
    """
    if not analyzed_segments:
        logger.info("没有分析结果需要保存到元数据中。")
        return False
    
    output_root_dir = os.path.join(root_dir, "data", "output")
    metadata_file_path = os.path.join(output_root_dir, "video_segments_metadata.json")
    
    # 加载现有元数据
    existing_metadata = []
    if os.path.exists(metadata_file_path):
        try:
            with open(metadata_file_path, 'r', encoding='utf-8') as f:
                existing_metadata = json.load(f)
        except Exception as e:
            logger.error(f"加载现有元数据失败: {e}")
            return False
    
    if not existing_metadata:
        logger.warning("没有找到现有元数据，无法更新分析结果。")
        return False
    
    # 创建分析结果的查找字典，使用视频ID+开始时间+结束时间作为键
    analysis_lookup = {}
    for segment in analyzed_segments:
        video_id = segment.get("video_id", "")
        start_time = segment.get("start_time", 0)
        end_time = segment.get("end_time", 0)
        key = f"{video_id}_{start_time}_{end_time}"
        analysis_lookup[key] = {
            "analyzed_product_type": segment.get("analyzed_product_type", ""),
            "analyzed_selling_points": segment.get("analyzed_selling_points", [])
        }
    
    # 更新元数据
    updated_count = 0
    for metadata_item in existing_metadata:
        # 从文件名中尝试提取视频ID和时间信息
        filename = metadata_item.get("filename", "")
        original_video_id = metadata_item.get("original_video_id", "")
        
        # 从元数据中获取毫秒时间并转换为秒
        start_time_ms = metadata_item.get("start_time_ms")
        end_time_ms = metadata_item.get("end_time_ms")
        
        if start_time_ms is not None and end_time_ms is not None:
            start_time_seconds = start_time_ms / 1000.0
            end_time_seconds = end_time_ms / 1000.0
            
            # 构建查找键
            lookup_key = f"{original_video_id}_{start_time_seconds}_{end_time_seconds}"
            
            # 如果找到匹配的分析结果，更新元数据
            if lookup_key in analysis_lookup:
                analysis_result = analysis_lookup[lookup_key]
                metadata_item["analyzed_product_type"] = analysis_result["analyzed_product_type"]
                metadata_item["analyzed_selling_points"] = analysis_result["analyzed_selling_points"]
                updated_count += 1
    
    # 保存更新后的元数据
    try:
        with open(metadata_file_path, 'w', encoding='utf-8') as f:
            json.dump(existing_metadata, f, ensure_ascii=False, indent=4)
        logger.info(f"已更新 {updated_count} 个片段的分析结果到元数据文件。")
        return True
    except Exception as e:
        logger.error(f"保存更新后的元数据失败: {e}")
        return False

# Example usage (for testing, not to be run directly usually)
if __name__ == '__main__':
    # This is a dummy logger for standalone testing
    import logging
    logging.basicConfig(level=logging.DEBUG)
    test_logger = logging.getLogger(__name__ + "_test")
    
    # Assume project root is two levels up from streamlit_app/modules/data_process
    project_root_for_test = Path(__file__).parent.parent.parent.parent 
    
    # You might need to create a dummy video_segments_metadata.json in 
    # <project_root_for_test>/data/output/ for this test to run.
    # And ensure a config.py exists that get_paths_config can use.
    
    # Dummy metadata for testing _time_str_to_seconds and _seconds_to_srt_time_format
    # print(_time_str_to_seconds("00:01:15.345"))
    # print(_seconds_to_srt_time_format(75.345))
    # print(_time_str_to_seconds("01:15.345"))
    # print(_time_str_to_seconds("15.345"))


    # create_srt_files_for_segments(project_root_for_test, test_logger)
    pass 