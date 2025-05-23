import streamlit as st
import os
import sys
from pathlib import Path
import logging # 添加logging导入
import shutil # 添加shutil导入
# import json # 不再直接在此处使用json来保存元数据

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),  # 输出到控制台
        logging.FileHandler(os.path.join('logs', 'app.log'))  # 输出到文件
    ]
)
logger = logging.getLogger(__name__) # 在模块级别获取logger

# 添加项目根目录到Python路径
ROOT_DIR = Path(__file__).parent.parent
sys.path.append(str(ROOT_DIR))

# 修改导入路径
from streamlit_app.config.config import get_config, TARGET_GROUPS, SELLING_POINTS, PRODUCT_TYPES, SEMANTIC_SEGMENT_TYPES, SEMANTIC_MODULES
from streamlit_app.modules.data_loader.video_loader import find_videos
from streamlit_app.modules.analysis.intent_analyzer import main_analysis_pipeline, SemanticAnalyzer
# 添加视频组织器模块的导入
from streamlit_app.modules.data_process.video_organizer import organize_segments_by_type
# 新增：导入元数据处理器
from streamlit_app.modules.data_process.metadata_processor import save_detailed_segments_metadata, create_srt_files_for_segments
# 新增：导入结果展示界面函数
from streamlit_app.modules.visualization.result_display import display_results_interface

# --- 页面配置 ---
st.set_page_config(
    page_title="视频分析大师 1.0",
    page_icon="🎥",
    layout="wide"
)

# --- 自定义CSS ---
st.markdown("""
<style>
    .main .block-container {
        padding-top: 2rem;
        padding-bottom: 2rem;
    }
    .stButton button {
        height: 2.5rem;
        vertical-align: middle !important;
        margin-top: 0.2rem;
    }
    .stTextInput input {
        height: 2.5rem;
    }
    .upload-section {
        display: flex;
        align-items: center;
    }
    .video-card {
        border: 1px solid #e6e6e6;
        border-radius: 5px;
        padding: 10px;
        margin-bottom: 15px;
    }
    .segment-row {
        margin-bottom: 10px;
        padding: 5px;
    }
    .segment-row:hover {
        background-color: #f0f2f6;
    }
    .product-tag {
        display: inline-block;
        padding: 3px 10px;
        border-radius: 12px;
        margin-right: 6px;
        margin-bottom: 5px;
        font-size: 0.85em;
        font-weight: 500;
        color: white;
    }
    .tag {
        display: inline-block;
        padding: 3px 10px;
        border-radius: 12px;
        margin-right: 6px;
        margin-bottom: 5px;
        font-size: 0.85em;
        font-weight: 500;
        color: white;
    }
    .tag-水奶 {
        background-color: #4CAF50;
    }
    .tag-蕴淳 {
        background-color: #2196F3;
    }
    .tag-蓝钻 {
        background-color: #9C27B0;
    }
    .tag-default {
        background-color: #757575;
        color: #f0f0f0;
    }
    .tag-audience {
        background-color: white; /* 白色背景 */
        color: black; /* 黑色文字 */
        border: 1px solid black; /* 黑色边框 */
    }

    /* 所有自定义按钮的CSS规则均被移除 */

</style>
""", unsafe_allow_html=True)

# --- 应用状态初始化 ---
if 'uploaded_file_path' not in st.session_state:
    st.session_state.uploaded_file_path = None
if 'video_files' not in st.session_state:
    st.session_state.video_files = []
if 'current_folder' not in st.session_state:
    st.session_state.current_folder = None
if 'all_videos_analysis_data' not in st.session_state:
    st.session_state.all_videos_analysis_data = None
if 'selected_segment' not in st.session_state:
    st.session_state.selected_segment = None
if 'selected_selling_points' not in st.session_state:
    st.session_state.selected_selling_points = []
if 'selected_segment_filter' not in st.session_state: # 为 result_display.py 初始化筛选器状态
    st.session_state.selected_segment_filter = "显示全部"

# --- 加载配置 ---
app_config = get_config()
# 初始化 SemanticAnalyzer 单例
sa_analyzer = SemanticAnalyzer()

# --- 设置默认视频目录 ---
DEFAULT_VIDEO_DIR = os.path.join(ROOT_DIR, "data/input/test_videos")
if 'folder_path' not in st.session_state:
    st.session_state.folder_path = DEFAULT_VIDEO_DIR

# --- 自动加载默认目录下的视频文件 ---
if not st.session_state.video_files and os.path.exists(DEFAULT_VIDEO_DIR):
    video_files = find_videos(DEFAULT_VIDEO_DIR)
    if video_files:
        st.session_state.video_files = video_files
        st.session_state.current_folder = DEFAULT_VIDEO_DIR
        print(f"DEBUG: Initial video files loaded: {st.session_state.video_files}") # 添加日志

# --- UI 界面 ---
st.title("🔍分析")

# 显示已加载的视频文件数量
if st.session_state.video_files:
    file_count = len(st.session_state.video_files)
    st.success(f"已加载 {file_count} 个视频文件 - 来自目录: {st.session_state.current_folder}")

# --- 顶部输入区域，使用容器确保紧凑 ---
input_container = st.container()
with input_container:
    # 使用一行布局
    col1, col2, col3 = st.columns([6, 3, 1])
    
    with col1:
        # 文件上传区
        if 'folder_path' not in st.session_state:
            st.session_state.folder_path = ""
            
        uploaded_files = st.file_uploader(
            "视频文件",
            type=["mp4", "avi", "mov", "mkv", "mpeg4"],
            accept_multiple_files=True,
            label_visibility="collapsed"
        )
        
        if uploaded_files:
            temp_dir = os.path.join(app_config.get("temp_dir", "data/temp"), "uploads")
            os.makedirs(temp_dir, exist_ok=True)
            
            st.session_state.video_files = []
            for uploaded_file in uploaded_files:
                file_path = os.path.join(temp_dir, uploaded_file.name)
                with open(file_path, "wb") as f:
                    f.write(uploaded_file.getbuffer())
                st.session_state.video_files.append(file_path)
            
            st.session_state.current_folder = temp_dir
            st.session_state.folder_path = temp_dir
            st.info(f"已上传 {len(uploaded_files)} 个视频文件")
    
    with col2:
        # 添加输入路径的文本框，显示默认目录
        folder_path = st.text_input(
            "视频路径",
            value=st.session_state.folder_path,
            placeholder="或输入视频文件夹路径",
            label_visibility="hidden"
        )
    
    with col3:
        # 导入按钮
        import_btn = st.button("导入", use_container_width=True)
        
        if import_btn and folder_path:
            if os.path.exists(folder_path):
                if os.path.isdir(folder_path):
                    video_files = find_videos(folder_path)
                    if video_files:
                        st.session_state.video_files = video_files
                        st.session_state.current_folder = folder_path
                        st.session_state.folder_path = folder_path
                        print(f"DEBUG: Video files after import button: {st.session_state.video_files}") # 添加日志
                        st.success(f"成功导入文件夹: {folder_path}，找到{len(video_files)}个视频文件")
                    else:
                        st.warning(f"在{folder_path}中未找到视频文件")
                else:
                    if any(folder_path.lower().endswith(ext) for ext in ['.mp4', '.avi', '.mov', '.mkv']):
                        st.session_state.uploaded_file_path = folder_path
                        st.session_state.video_files = [folder_path]
                        st.success(f"成功导入单个文件: {folder_path}")
                    else:
                        st.error("请选择视频文件或文件夹！")
            else:
                st.error("文件路径不存在！")

# 分析按钮区域
st.markdown("<div style='margin-top: 1rem;'></div>", unsafe_allow_html=True)
col1, col2, col3 = st.columns([1, 1, 1])
with col2:
    analyze_button = st.button("🔍 分析", use_container_width=True, type="primary")

st.markdown("---")

# --- 分析与结果展示区域 ---
if analyze_button and st.session_state.video_files:
    with st.spinner("正在分析视频，请稍候..."):
        all_videos_analysis_data = [] # 用于存储每个视频的完整分析数据
        
        from streamlit_app.config.config import SELLING_POINTS as current_selling_points_config
        selling_points_for_cache = tuple(current_selling_points_config) 
        
        for video_path in st.session_state.video_files:
            video_file_name = os.path.basename(video_path)
            st.write(f"--- 开始处理视频: {video_file_name} ---")
            
            raw_segments, full_transcript_data = main_analysis_pipeline(
                video_path,
                None, 
                None, 
                selling_points_config_representation=selling_points_for_cache,
                additional_info=""  
            )
            
            semantic_segments_for_ui = {module: [] for module in SEMANTIC_MODULES}
            if raw_segments:
                for segment_data in raw_segments:
                    semantic_type = segment_data.get("semantic_type", "未知")
                    if semantic_type in SEMANTIC_MODULES:
                        semantic_segments_for_ui[semantic_type].append(segment_data)
            
            video_product_types = set()
            video_target_audiences = set()

            srt_content_for_llm = None
            if full_transcript_data:
                if 'srt_content' in full_transcript_data and full_transcript_data['srt_content']:
                    srt_content_for_llm = full_transcript_data['srt_content']
                    logger.info(f"使用 full_transcript_data 中的SRT内容进行LLM产品类型分析: {video_file_name}")
                elif 'srt_file_path' in full_transcript_data and full_transcript_data['srt_file_path']:
                    srt_path = full_transcript_data['srt_file_path']
                    logger.info(f"尝试从 srt_file_path 读取SRT内容: {srt_path} for video: {video_file_name}")
                    if os.path.exists(srt_path) and os.path.isfile(srt_path):
                        try:
                            with open(srt_path, 'r', encoding='utf-8') as f_srt:
                                srt_content_for_llm = f_srt.read()
                            if srt_content_for_llm:
                                logger.info(f"成功从文件 {srt_path} 读取SRT内容进行LLM产品类型分析: {video_file_name}")
                            else:
                                logger.warning(f"SRT文件 {srt_path} 为空。")
                        except Exception as e_read_srt:
                            logger.error(f"读取SRT文件 {srt_path} 失败: {e_read_srt}")
                    else:
                        logger.warning(f"SRT文件路径存在于full_transcript_data中，但文件未找到或不是一个有效文件: {srt_path}")
                else:
                    logger.warning(f"在 full_transcript_data 中未找到 'srt_content' 或 'srt_file_path' 键，或者路径无效: {video_file_name}. Keys: {list(full_transcript_data.keys()) if full_transcript_data else 'N/A'}")
            else:
                logger.warning(f"full_transcript_data 为空，无法获取SRT内容进行LLM产品类型分析: {video_file_name}")

            if srt_content_for_llm:
                try:
                    logger.info(f"对SRT内容进行LLM分析以识别产品类型: {video_file_name}")
                    summary_results = sa_analyzer.analyze_video_summary(srt_content_for_llm)
                    
                    if summary_results and 'product_type' in summary_results:
                        for pt in summary_results['product_type']:
                            if pt and pt in PRODUCT_TYPES:
                                video_product_types.add(pt)
                    if summary_results and 'target_audience' in summary_results:
                        for aud in summary_results['target_audience']:
                            if aud and aud in TARGET_GROUPS:
                                video_target_audiences.add(aud)

                    log_msg_parts = []
                    if video_product_types:
                        log_msg_parts.append(f"产品类型: {video_product_types}")
                    if video_target_audiences:
                        log_msg_parts.append(f"目标人群: {video_target_audiences}")
                    
                    if log_msg_parts:
                        logger.info(f"LLM对SRT的分析结果 - {video_file_name} - {', '.join(log_msg_parts)}")
                    else:
                        logger.info(f"LLM对SRT的分析未能从 'product_type' 或 'target_audience' 字段中识别出有效信息，或字段缺失: {video_file_name}")
                except Exception as e_llm_srt:
                    logger.error(f"LLM分析SRT内容以识别产品类型时发生错误 - {video_file_name}: {str(e_llm_srt)}")
            else:
                logger.warning(f"没有可供分析的SRT内容，无法识别产品类型: {video_file_name}")
            
            semantic_segments_for_ui = {k: v for k, v in semantic_segments_for_ui.items() if v}
            
            all_videos_analysis_data.append({
                "video_id": os.path.splitext(video_file_name)[0],
                "video_path": video_path,
                "semantic_segments": semantic_segments_for_ui, 
                "full_transcript_data": full_transcript_data,
                "product_types": list(video_product_types) if video_product_types else [], 
                "target_audiences": list(video_target_audiences) if video_target_audiences else [] 
            })
        
        st.session_state.all_videos_analysis_data = all_videos_analysis_data
        
        if not st.session_state.all_videos_analysis_data:
            st.warning("所有视频均分析完成，但未获得任何有效结果。")
        
        try:
            logger.info("开始调用 organize_segments_by_type() 函数组织视频片段...")
            success = organize_segments_by_type() # 此函数现在只负责复制物理文件
            if success:
                st.success("已按语义类型组织视频片段到data/output目录")
                logger.info("视频片段已成功按语义类型组织")
            else:
                st.warning("视频片段组织过程中遇到问题，请查看日志了解详情")
                logger.warning("视频片段组织失败")
        except Exception as e:
            st.error(f"组织视频片段时出错: {str(e)}")
            logger.error(f"调用 organize_segments_by_type() 函数出错: {str(e)}", exc_info=True)

        # --- 调用新的元数据保存函数 ---
        # if st.session_state.get('all_videos_analysis_data'): # 这段逻辑似乎重复了，且位置不太对，先注释掉以避免混淆
        #     try:
        #         save_detailed_segments_metadata(st.session_state.all_videos_analysis_data, ROOT_DIR, logger)
        #     except Exception as e_save_meta:
        #         logger.error(f"调用 save_detailed_segments_metadata 失败: {e_save_meta}", exc_info=True)
        #         st.error(f"保存分析结果元数据时发生错误: {e_save_meta}")

        # --- 确保在分析流程的末尾正确保存元数据和生成SRT ---
        if analyze_button and st.session_state.video_files: # 确保这些操作在分析完成后执行
            if st.session_state.all_videos_analysis_data:
                logger.info("准备（再次确认）保存所有视频片段的详细元数据...")
                if save_detailed_segments_metadata(st.session_state.all_videos_analysis_data, ROOT_DIR, logger):
                    logger.info("详细片段元数据（再次确认）保存成功。")
                    logger.info("准备（再次确认）为所有片段生成SRT字幕文件...")
                    create_srt_files_for_segments(ROOT_DIR, logger)
                    logger.info("SRT字幕文件（再次确认）生成流程调用完毕。")
                else:
                    logger.error("详细片段元数据（再次确认）保存失败。")
            else:
                logger.warning("分析后没有有效的分析数据可用于保存元数据。all_videos_analysis_data 为空或不存在。")

# 总是尝试调用 display_results_interface。
# 它会从 video_segments_metadata.json 加载数据。
display_results_interface(analysis_results=st.session_state.get('all_videos_analysis_data'))

# 错误消息：仅当用户明确点击分析按钮但没有选择任何视频文件时显示。
if analyze_button and not st.session_state.video_files:
    st.error("请先上传或指定一个视频文件/文件夹再进行分析！") 