import streamlit as st
import os
import sys
from pathlib import Path
import logging # 添加logging导入
import shutil # 添加shutil导入
from datetime import datetime
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
from streamlit_app.config.config import get_config, get_semantic_segment_types, get_semantic_modules, TARGET_GROUPS
from streamlit_app.modules.data_loader.video_loader import find_videos
from streamlit_app.modules.analysis.intent_analyzer import main_analysis_pipeline, SemanticAnalyzer
# 添加视频组织器模块的导入
from streamlit_app.modules.data_process.video_organizer import organize_segments_by_type
# 新增：导入元数据处理器
from streamlit_app.modules.data_process.metadata_processor import save_detailed_segments_metadata, create_srt_files_for_segments, update_metadata_with_analysis_results
# 新增：导入结果展示界面函数
from streamlit_app.modules.visualization.result_display import display_results_interface
# 新增：导入片段分析器
from streamlit_app.modules.analysis.segment_analyzer import analyze_segments_batch

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
    
    /* 目标人群标签样式 */
    .tag-孕期妈妈 {
        background-color: #E91E63; /* 粉红色 */
    }
    .tag-二胎妈妈 {
        background-color: #FF9800; /* 橙色 */
    }
    .tag-混养妈妈 {
        background-color: #4CAF50; /* 绿色 */
    }
    .tag-新手爸妈 {
        background-color: #2196F3; /* 蓝色 */
    }
    .tag-贵妇妈妈 {
        background-color: #9C27B0; /* 紫色 */
    }
    
    /* 产品类型标签样式 */
    .tag-启赋水奶 {
        background-color: #4CAF50; /* 绿色 */
    }
    .tag-启赋蕴淳 {
        background-color: #2196F3; /* 蓝色 */
    }
    .tag-启赋蓝钻 {
        background-color: #9C27B0; /* 紫色 */
    }
    
    /* 侧边栏宽度控制 */
    .css-1d391kg {
        width: 180px !important;
        min-width: 180px !important;
        max-width: 180px !important;
    }
    
    /* 侧边栏内容区域 */
    .css-1lcbmhc {
        width: 180px !important;
        min-width: 180px !important;
        max-width: 180px !important;
    }
    
    /* 主内容区域自适应 */
    .css-18e3th9 {
        padding-left: 200px !important;
    }
    
    /* 更通用的侧边栏样式控制 */
    section[data-testid="stSidebar"] {
        width: 180px !important;
        min-width: 180px !important;
        max-width: 180px !important;
    }
    
    section[data-testid="stSidebar"] > div {
        width: 180px !important;
        min-width: 180px !important;
        max-width: 180px !important;
    }
    
    /* 侧边栏导航链接样式优化 */
    .css-1v0mbdj a {
        font-size: 0.9rem !important;
        padding: 0.5rem 0.75rem !important;
    }
    
    /* 隐藏侧边栏调整手柄 */
    .css-1cypcdb {
        display: none !important;
    }
    
    /* 转录编辑相关样式 */
    .transcript-container {
        border: 1px solid #e6e6e6;
        border-radius: 8px;
        padding: 10px;
        margin: 5px 0;
    }
    
    .transcript-changes {
        background-color: #fff3cd;
        border: 1px solid #ffeaa7;
        border-radius: 4px;
        padding: 8px;
        margin-top: 5px;
    }
    
    .transcript-save-btn {
        background-color: #28a745 !important;
        color: white !important;
        border: none !important;
        border-radius: 4px !important;
        padding: 5px 10px !important;
        font-size: 0.85em !important;
    }
    
    .transcript-reset-btn {
        background-color: #6c757d !important;
        color: white !important;
        border: none !important;
        border-radius: 4px !important;
        padding: 5px 10px !important;
        font-size: 0.85em !important;
    }
    
    /* 🆕 片段编辑器表格样式 */
    .segment-editor-table {
        border: 1px solid #e6e6e6;
        border-radius: 8px;
        padding: 10px;
        margin: 10px 0;
        background-color: #fafafa;
    }
    
    .segment-row {
        padding: 8px 0;
        border-bottom: 1px solid #e6e6e6;
    }
    
    .segment-row:last-child {
        border-bottom: none;
    }
    
    .segment-row:hover {
        background-color: #f0f2f6;
        border-radius: 4px;
    }
    
    .segment-file-button {
        background-color: #f8f9fa !important;
        border: 1px solid #dee2e6 !important;
        color: #495057 !important;
        font-size: 0.85em !important;
        padding: 4px 8px !important;
        border-radius: 4px !important;
    }
    
    .segment-file-button:hover {
        background-color: #e9ecef !important;
        border-color: #adb5bd !important;
    }
    
    .segment-modified {
        color: #28a745;
        font-style: italic;
        font-size: 0.85em;
    }
    
    /* 紧凑的输入框样式 */
    .stNumberInput > div > div > input {
        height: 35px !important;
        font-size: 0.85em !important;
    }
    
    .stMultiSelect > div > div {
        min-height: 35px !important;
    }
    
    .stSelectbox > div > div {
        min-height: 35px !important;
    }
</style>""", unsafe_allow_html=True)

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
            
            semantic_segments_for_ui = {module: [] for module in get_semantic_modules()}
            if raw_segments:
                for segment_data in raw_segments:
                    semantic_type = segment_data.get("semantic_type", "未知")
                    if semantic_type in get_semantic_segment_types():
                        semantic_segments_for_ui[semantic_type].append(segment_data)
            
            video_target_audiences = set()

            srt_content_for_llm = None
            if full_transcript_data:
                if 'srt_content' in full_transcript_data and full_transcript_data['srt_content']:
                    srt_content_for_llm = full_transcript_data['srt_content']
                    logger.info(f"使用 full_transcript_data 中的SRT内容进行LLM目标人群分析: {video_file_name}")
                elif 'srt_file_path' in full_transcript_data and full_transcript_data['srt_file_path']:
                    srt_path = full_transcript_data['srt_file_path']
                    logger.info(f"尝试从 srt_file_path 读取SRT内容: {srt_path} for video: {video_file_name}")
                    if os.path.exists(srt_path) and os.path.isfile(srt_path):
                        try:
                            with open(srt_path, 'r', encoding='utf-8') as f_srt:
                                srt_content_for_llm = f_srt.read()
                            if srt_content_for_llm:
                                logger.info(f"成功从文件 {srt_path} 读取SRT内容进行LLM目标人群分析: {video_file_name}")
                            else:
                                logger.warning(f"SRT文件 {srt_path} 为空。")
                        except Exception as e_read_srt:
                            logger.error(f"读取SRT文件 {srt_path} 失败: {e_read_srt}")
                    else:
                        logger.warning(f"SRT文件路径存在于full_transcript_data中，但文件未找到或不是一个有效文件: {srt_path}")
                else:
                    logger.warning(f"在 full_transcript_data 中未找到 'srt_content' 或 'srt_file_path' 键，或者路径无效: {video_file_name}. Keys: {list(full_transcript_data.keys()) if full_transcript_data else 'N/A'}")
            else:
                logger.warning(f"full_transcript_data 为空，无法获取SRT内容进行LLM目标人群分析: {video_file_name}")

            if srt_content_for_llm:
                try:
                    logger.info(f"对SRT内容进行LLM分析以识别目标人群: {video_file_name}")
                    summary_results = sa_analyzer.analyze_video_summary(srt_content_for_llm)
                    
                    if summary_results and 'target_audience' in summary_results:
                        target_audience = summary_results['target_audience']
                        # 确保只返回一个目标人群
                        if target_audience and target_audience in TARGET_GROUPS:
                            video_target_audiences.add(target_audience)

                    # 兜底机制：如果LLM没有识别出目标人群，基于关键词进行兜底分析
                    if not video_target_audiences:
                        logger.warning(f"LLM未能识别出目标人群，启用关键词兜底机制: {video_file_name}")
                        srt_lower = srt_content_for_llm.lower()
                        
                        # 关键词映射规则（按优先级排序）
                        priority_mapping = [
                            ("二胎妈妈", ["二胎", "老大", "老二", "两个孩子", "大宝", "二宝"]),
                            ("孕期妈妈", ["刚生完", "产后", "待产包", "产检", "建档", "准妈妈", "卸货", "分娩", "生产", "产科", "新生宝宝", "出生后"]),
                            ("混养妈妈", ["混合喂养", "混喂", "亲喂", "母乳不足", "奶量不够", "奶水不足"]),
                            ("贵妇妈妈", ["高端", "奢华", "精致", "品质", "贵", "高价", "进口", "顶级"]),
                            ("新手爸妈", ["新手", "没有经验", "第一次", "不知道怎么", "学习", "初次", "新手爸爸", "新手妈妈"])
                        ]
                        
                        # 按优先级检查关键词匹配，找到第一个匹配的就停止
                        target_found = False
                        for target_group, keywords in priority_mapping:
                            if not target_found:
                                for keyword in keywords:
                                    if keyword in srt_lower:
                                        video_target_audiences.add(target_group)
                                        logger.info(f"通过关键词 '{keyword}' 识别目标人群 '{target_group}': {video_file_name}")
                                        target_found = True
                                        break
                        
                        # 如果仍然没有识别出目标人群，使用最终兜底
                        if not target_found:
                            # 检查是否包含产品相关内容，如果有则默认分配给"新手爸妈"
                            product_keywords = ["奶粉", "启赋", "蕴淳", "水奶", "母乳低聚糖", "hmo", "a2奶源"]
                            has_product_content = any(keyword in srt_lower for keyword in product_keywords)
                            
                            if has_product_content:
                                video_target_audiences.add("新手爸妈")
                                logger.info(f"基于产品内容特征，默认分配给'新手爸妈': {video_file_name}")
                            else:
                                # 最终兜底：分配给最通用的"新手爸妈"
                                video_target_audiences.add("新手爸妈")
                                logger.info(f"最终兜底机制，分配给'新手爸妈': {video_file_name}")

                    if video_target_audiences:
                        logger.info(f"最终目标人群分析结果 - {video_file_name} - 目标人群: {list(video_target_audiences)}")
                    else:
                        logger.error(f"严重错误：兜底机制失败，仍未识别出目标人群: {video_file_name}")
                except Exception as e_llm_srt:
                    logger.error(f"LLM分析SRT内容以识别目标人群时发生错误 - {video_file_name}: {str(e_llm_srt)}")
                    # 异常情况的兜底：分配给"新手爸妈"
                    video_target_audiences.add("新手爸妈")
                    logger.info(f"异常情况兜底，分配给'新手爸妈': {video_file_name}")
            else:
                logger.warning(f"没有可供分析的SRT内容，无法识别目标人群: {video_file_name}")
                # 没有SRT内容的兜底：分配给"新手爸妈"
                video_target_audiences.add("新手爸妈")
                logger.info(f"无SRT内容兜底，分配给'新手爸妈': {video_file_name}")
            
            semantic_segments_for_ui = {k: v for k, v in semantic_segments_for_ui.items() if v}
            
            all_videos_analysis_data.append({
                "video_id": os.path.splitext(video_file_name)[0],
                "video_path": video_path,
                "semantic_segments": semantic_segments_for_ui, 
                "full_transcript_data": full_transcript_data,
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

        # --- 确保在分析流程的末尾正确保存元数据和生成SRT ---
        if analyze_button and st.session_state.video_files: # 确保这些操作在分析完成后执行
            if st.session_state.all_videos_analysis_data:
                logger.info("准备（再次确认）保存所有视频片段的详细元数据...")
                if save_detailed_segments_metadata(st.session_state.all_videos_analysis_data, ROOT_DIR, logger):
                    logger.info("详细片段元数据（再次确认）保存成功。")
                    
                    # --- 新增：片段分析功能 ---
                    st.subheader("🔍 智能分析片段内容")
                    with st.spinner("正在分析各片段的产品类型和核心卖点..."):
                        try:
                            # 收集所有片段数据
                            all_segments_for_analysis = []
                            for video_data in st.session_state.all_videos_analysis_data:
                                for semantic_type, segments in video_data.get("semantic_segments", {}).items():
                                    for segment in segments:
                                        # 准备片段数据用于分析
                                        segment_data = {
                                            'semantic_type': semantic_type,
                                            'start_time': segment.get('start_time_ms', 0.0) / 1000.0,
                                            'end_time': segment.get('end_time_ms', 0.0) / 1000.0,
                                            'time_period': segment.get('time_info', ''),
                                            'text': segment.get('transcript', ''),
                                            'confidence': 1.0,
                                            'analyzed_product_type': segment.get('analyzed_product_type', '未识别'),
                                            'analyzed_selling_points': segment.get('analyzed_selling_points', []),
                                            'file_path': os.path.join(ROOT_DIR, "data", "output", semantic_type, segment.get('filename', ''))
                                        }
                                        all_segments_for_analysis.append(segment_data)
                            
                            if all_segments_for_analysis:
                                logger.info(f"开始分析 {len(all_segments_for_analysis)} 个片段...")
                                
                                # 使用缓存键避免重复分析
                                segments_cache_key = f"segments_analysis_{len(all_segments_for_analysis)}_{hash(str(all_segments_for_analysis[:3]))}"
                                
                                # 执行并行分析
                                analyzed_segments = analyze_segments_batch(all_segments_for_analysis, max_workers=3)
                                
                                # 统计分析结果
                                product_types_found = {}
                                selling_points_found = {}
                                
                                for segment in analyzed_segments:
                                    product_type = segment.get("analyzed_product_type", "")
                                    selling_points = segment.get("analyzed_selling_points", [])
                                    
                                    if product_type:
                                        product_types_found[product_type] = product_types_found.get(product_type, 0) + 1
                                    
                                    for sp in selling_points:
                                        selling_points_found[sp] = selling_points_found.get(sp, 0) + 1
                                
                                # 显示分析结果统计
                                col1, col2 = st.columns(2)
                                
                                with col1:
                                    st.write("**识别到的产品类型:**")
                                    if product_types_found:
                                        for pt, count in product_types_found.items():
                                            st.write(f"- {pt}: {count} 个片段")
                                    else:
                                        st.write("未识别到明确的产品类型")
                                
                                with col2:
                                    st.write("**识别到的核心卖点:**")
                                    if selling_points_found:
                                        for sp, count in selling_points_found.items():
                                            st.write(f"- {sp}: {count} 个片段")
                                    else:
                                        st.write("未识别到明确的核心卖点")
                                
                                logger.info(f"片段分析完成。产品类型: {list(product_types_found.keys())}，卖点: {list(selling_points_found.keys())}")
                                st.success(f"✅ 已完成 {len(analyzed_segments)} 个片段的智能分析")
                                
                                # 将分析结果保存到元数据文件
                                try:
                                    logger.info("开始将片段分析结果保存到元数据文件...")
                                    if update_metadata_with_analysis_results(analyzed_segments, ROOT_DIR, logger):
                                        logger.info("片段分析结果已成功保存到元数据文件。")
                                        st.success("🔖 分析结果已保存到元数据")
                                    else:
                                        logger.warning("保存片段分析结果到元数据文件失败。")
                                        st.warning("⚠️ 分析结果保存失败")
                                except Exception as e_save_analysis:
                                    logger.error(f"保存片段分析结果时出错: {str(e_save_analysis)}")
                                    st.error(f"保存分析结果失败: {str(e_save_analysis)}")
                                
                                # 将分析结果合并回原始数据结构
                                # TODO: 这里可以扩展将分析结果保存到元数据文件中
                                
                            else:
                                st.info("没有找到可分析的片段数据")
                                
                        except Exception as e_segment_analysis:
                            logger.error(f"片段分析过程中出错: {str(e_segment_analysis)}")
                            st.error(f"片段分析失败: {str(e_segment_analysis)}")
                    
                    logger.info("准备（再次确认）为所有片段生成SRT字幕文件...")
                    create_srt_files_for_segments(ROOT_DIR, logger)
                    logger.info("SRT字幕文件（再次确认）生成流程调用完毕。")
                else:
                    logger.error("详细片段元数据（再次确认）保存失败。")
            else:
                logger.warning("分析后没有有效的分析数据可用于保存元数据。all_videos_analysis_data 为空或不存在。")

# 🆕 片段编辑器 - 作为主要功能
# 总是尝试加载完整的数据（包括新分析和历史数据）
def load_complete_analysis_data():
    """加载完整的分析数据，包括新分析和历史数据"""
    complete_data = {}
    
    # 1. 首先加载历史数据
    try:
        import json
        metadata_file = "data/output/video_segments_metadata.json"
        if os.path.exists(metadata_file):
            with open(metadata_file, 'r', encoding='utf-8') as f:
                metadata = json.load(f)
            
            if metadata:
                logger.info(f"从元数据文件加载了 {len(metadata)} 个片段的历史数据")
                
                # 转换元数据为标准格式
                for segment in metadata:
                    video_id = segment.get('original_video_id', 'unknown')
                    if video_id not in complete_data:
                        complete_data[video_id] = {
                            'video_id': video_id,
                            'video_path': segment.get('video_path', ''),
                            'semantic_segments': {},
                            'target_audiences': [segment.get('target_audiences', '新手爸妈')]
                        }
                    
                    semantic_type = segment.get('type', '其他')
                    if semantic_type not in complete_data[video_id]['semantic_segments']:
                        complete_data[video_id]['semantic_segments'][semantic_type] = []
                    
                    segment_data = {
                        'semantic_type': semantic_type,
                        'start_time': segment.get('start_time_ms', 0.0) / 1000.0,
                        'end_time': segment.get('end_time_ms', 0.0) / 1000.0,
                        'time_period': segment.get('time_info', ''),
                        'text': segment.get('transcript', ''),
                        'confidence': 1.0,
                        'analyzed_product_type': segment.get('analyzed_product_type', '未识别'),
                        'analyzed_selling_points': segment.get('analyzed_selling_points', []),
                        'file_path': os.path.join(ROOT_DIR, "data", "output", semantic_type, segment.get('filename', ''))
                    }
                    
                    complete_data[video_id]['semantic_segments'][semantic_type].append(segment_data)
    except Exception as e:
        logger.error(f"加载历史数据失败: {e}")
    
    # 2. 然后合并新分析的数据（如果有的话）
    if st.session_state.get('all_videos_analysis_data'):
        logger.info(f"合并新分析的 {len(st.session_state.all_videos_analysis_data)} 个视频数据")
        
        for video_data in st.session_state.all_videos_analysis_data:
            video_id = video_data.get("video_id", "unknown")
            
            # 如果是新视频，直接添加；如果是已存在的视频，更新数据
            complete_data[video_id] = video_data
    
    return list(complete_data.values())

# 加载完整的分析数据
complete_analysis_data = load_complete_analysis_data()

if complete_analysis_data:
    st.markdown("### ✏️ 片段编辑器")
    st.markdown("在这里您可以调整视频片段的时间、语义类型等信息，您的修改将用于改进模型的分析准确性。")
    
    # 导入片段编辑器
    try:
        from streamlit_app.modules.analysis.segment_editor import SegmentEditor
        
        # 创建片段编辑器实例
        segment_editor = SegmentEditor()
        
        # 为每个视频显示片段编辑器
        for video_data in complete_analysis_data:
            video_id = video_data.get("video_id", "unknown")
            video_path = video_data.get("video_path", "")
            semantic_segments = video_data.get("semantic_segments", {})
            target_audiences = video_data.get("target_audiences", ["新手爸妈"])
            
            # 将语义片段转换为扁平列表
            all_segments = []
            
            # 计算全局片段索引
            global_segment_index = 0
            
            # 确保semantic_segments是字典格式
            if isinstance(semantic_segments, dict):
                # 首先收集所有片段以确定正确的索引
                all_segments_with_types = []
                for semantic_type, segments in semantic_segments.items():
                    if isinstance(segments, list):
                        for segment in segments:
                            all_segments_with_types.append((semantic_type, segment))
                
                # 现在处理每个片段，使用正确的全局索引
                for idx, (semantic_type, segment) in enumerate(all_segments_with_types):
                    # 确保片段包含必要的信息
                    segment_data = {
                        'semantic_type': semantic_type,
                        'start_time': segment.get('start_time', 0.0),
                        'end_time': segment.get('end_time', 0.0),
                        'time_period': segment.get('time_period', ''),
                        'text': segment.get('text', ''),
                        'confidence': segment.get('confidence', 0.0),
                        'product_type': segment.get('analyzed_product_type', '未识别'),
                        'target_audience': target_audiences[0] if target_audiences else '新手爸妈',
                        'selling_points': segment.get('analyzed_selling_points', [])
                    }
                    
                    # 直接使用segment中已有的file_path，如果没有则构建
                    if 'file_path' in segment and segment['file_path']:
                        segment_data['file_path'] = segment['file_path']
                    else:
                        # 构建文件路径，使用全局索引
                        segment_filename = f"{video_id}_semantic_seg_{idx}_{semantic_type}.mp4"
                        segment_data['file_path'] = os.path.join(ROOT_DIR, "data", "output", semantic_type, segment_filename)
                    
                    all_segments.append(segment_data)
            elif isinstance(semantic_segments, list):
                # 如果semantic_segments是列表，直接处理
                for i, segment in enumerate(semantic_segments):
                    segment_data = {
                        'semantic_type': segment.get('semantic_type', '其他'),
                        'start_time': segment.get('start_time', 0.0),
                        'end_time': segment.get('end_time', 0.0),
                        'time_period': segment.get('time_period', ''),
                        'text': segment.get('text', ''),
                        'confidence': segment.get('confidence', 0.0),
                        'product_type': segment.get('analyzed_product_type', '未识别'),
                        'target_audience': target_audiences[0] if target_audiences else '新手爸妈',
                        'selling_points': segment.get('analyzed_selling_points', [])
                    }
                    
                    # 构建文件路径
                    semantic_type = segment.get('semantic_type', '其他')
                    segment_filename = f"{video_id}_semantic_seg_{i}_{semantic_type}.mp4"
                    segment_data['file_path'] = os.path.join(ROOT_DIR, "data", "output", semantic_type, segment_filename)
                    
                    all_segments.append(segment_data)
            
            if all_segments:
                st.markdown(f"#### 🎬 视频: {video_id} ({len(all_segments)} 个片段)")
                
                # 调试信息：显示文件路径
                with st.expander("🔍 调试信息 - 文件路径", expanded=False):
                    for i, seg in enumerate(all_segments[:3]):  # 只显示前3个
                        st.write(f"片段 {i+1}:")
                        st.write(f"  语义类型: {seg.get('semantic_type')}")
                        st.write(f"  文件路径: {seg.get('file_path')}")
                        st.write(f"  文件存在: {os.path.exists(seg.get('file_path', ''))}")
                
                # 渲染片段编辑器（表格形式）
                updated_segments = segment_editor.render_segment_list(all_segments, video_id)
                
                # 如果有更新，保存反馈数据
                if updated_segments:
                    try:
                        from streamlit_app.modules.analysis.feedback_manager import get_feedback_manager
                        feedback_manager = get_feedback_manager()
                        
                        # 保存用户反馈
                        feedback_data = {
                            'video_id': video_id,
                            'original_segments': all_segments,
                            'updated_segments': updated_segments,
                            'timestamp': datetime.now().isoformat()
                        }
                        
                        feedback_manager.save_segment_correction(feedback_data)
                        
                    except Exception as e:
                        st.warning(f"保存反馈数据失败: {e}")
            else:
                st.info(f"视频 {video_id} 暂无片段数据")
    
    except ImportError as e:
        st.error(f"无法加载片段编辑器: {e}")
    except Exception as e:
        st.error(f"片段编辑器出错: {e}")
        st.exception(e)  # 显示详细错误信息
else:
    st.info("暂无视频分析数据，请先上传视频并进行分析。")

# 错误消息：仅当用户明确点击分析按钮但没有选择任何视频文件时显示。
if analyze_button and not st.session_state.video_files:
    st.error("请先上传或指定一个视频文件/文件夹再进行分析！") 