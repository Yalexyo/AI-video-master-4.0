import streamlit as st
import os
import sys
from pathlib import Path
import logging # 添加logging导入
import shutil # 添加shutil导入

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),  # 输出到控制台
        logging.FileHandler(os.path.join('logs', 'app.log'))  # 输出到文件
    ]
)
logger = logging.getLogger(__name__)

# 添加项目根目录到Python路径
ROOT_DIR = Path(__file__).parent.parent
sys.path.append(str(ROOT_DIR))

# 修改导入路径
from streamlit_app.config.config import get_config, TARGET_GROUPS, SELLING_POINTS, PRODUCT_TYPES, SEMANTIC_SEGMENT_TYPES, SEMANTIC_MODULES
from streamlit_app.modules.data_loader.video_loader import find_videos
from streamlit_app.modules.analysis.intent_analyzer import main_analysis_pipeline, SemanticAnalyzer
# 添加视频组织器模块的导入
from streamlit_app.modules.data_process.video_organizer import organize_segments_by_type

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
</style>
""", unsafe_allow_html=True)

# --- 应用状态初始化 ---
if 'uploaded_file_path' not in st.session_state:
    st.session_state.uploaded_file_path = None
if 'video_files' not in st.session_state:
    st.session_state.video_files = []
if 'current_folder' not in st.session_state:
    st.session_state.current_folder = None
if 'analysis_results' not in st.session_state:
    st.session_state.analysis_results = None
if 'selected_segment' not in st.session_state:
    st.session_state.selected_segment = None
if 'selected_selling_points' not in st.session_state:
    st.session_state.selected_selling_points = []

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
        
        # 将 SELLING_POINTS (列表) 转换为元组，以便用作缓存键
        # 从配置中导入 SELLING_POINTS
        from streamlit_app.config.config import SELLING_POINTS as current_selling_points_config
        selling_points_for_cache = tuple(current_selling_points_config) 
        
        for video_path in st.session_state.video_files:
            video_file_name = os.path.basename(video_path)
            st.write(f"--- 开始处理视频: {video_file_name} ---")
            
            # 调用主分析流水线，获取原始语义分段列表和完整转录数据
            raw_segments, full_transcript_data = main_analysis_pipeline(
                video_path,
                None,  # target_audience - 不再由此处传递
                None,  # product_type - 不再由此处传递
                selling_points_config_representation=selling_points_for_cache,
                additional_info=""  # 不使用用户输入的具体提取信息
            )
            
            # 组织按语义模块分类的片段
            # raw_segments 本身就是 segment_video 返回的列表，其结构应与之前 analysis_results 相似
            # 每个元素是一个字典，包含 "semantic_type", "text", "start_time", "end_time" 等
            semantic_segments_for_ui = {module: [] for module in SEMANTIC_MODULES}
            if raw_segments: # 确保 raw_segments 不是 None 或空列表
                for segment_data in raw_segments:
                    semantic_type = segment_data.get("semantic_type", "未知")
                    if semantic_type in SEMANTIC_MODULES:
                        # 此处 segment_data 就是可以直接用于UI展示的片段信息
                        semantic_segments_for_ui[semantic_type].append(segment_data)
            
            video_product_types = set()
            video_target_audiences = set() # 用于存储当前视频的目标人群

            # 主要的产品类型和目标人群识别逻辑：通过LLM分析SRT文件内容
            srt_content_for_llm = None
            if full_transcript_data:
                if 'srt_content' in full_transcript_data and full_transcript_data['srt_content']:
                    srt_content_for_llm = full_transcript_data['srt_content']
                    logger.info(f"使用 full_transcript_data 中的SRT内容进行LLM产品类型分析: {video_file_name}")
                elif 'srt_file_path' in full_transcript_data and full_transcript_data['srt_file_path']:
                    srt_path = full_transcript_data['srt_file_path']
                    logger.info(f"尝试从 srt_file_path 读取SRT内容: {srt_path} for video: {video_file_name}") # 新增日志
                    if os.path.exists(srt_path) and os.path.isfile(srt_path): # 确保是文件
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
                    # sa_analyzer 已在应用启动时初始化
                    summary_results = sa_analyzer.analyze_video_summary(srt_content_for_llm)
                    
                    if summary_results and 'product_type' in summary_results:
                        for pt in summary_results['product_type']:
                            if pt and pt in PRODUCT_TYPES: # 确保产品类型有效
                                video_product_types.add(pt)
                    if summary_results and 'target_audience' in summary_results: # 提取目标人群
                        for aud in summary_results['target_audience']:
                            if aud and aud in TARGET_GROUPS: # 确保目标人群有效
                                video_target_audiences.add(aud)

                    log_msg_parts = []
                    if video_product_types:
                        log_msg_parts.append(f"产品类型: {video_product_types}")
                    if video_target_audiences:
                        log_msg_parts.append(f"目标人群: {video_target_audiences}")
                    
                    if log_msg_parts:
                        logger.info(f"LLM对SRT的分析结果 - {video_file_name} - {' , '.join(log_msg_parts)}")
                    else:
                        logger.info(f"LLM对SRT的分析未能从 'product_type' 或 'target_audience' 字段中识别出有效信息，或字段缺失: {video_file_name}")
                except Exception as e_llm_srt:
                    logger.error(f"LLM分析SRT内容以识别产品类型时发生错误 - {video_file_name}: {str(e_llm_srt)}")
            else:
                logger.warning(f"没有可供分析的SRT内容，无法识别产品类型: {video_file_name}")
            
            # print(f"DEBUG: Semantic segments BEFORE filtering for video {video_file_name}: {semantic_segments}") 

            # 过滤掉没有内容的分类
            semantic_segments_for_ui = {k: v for k, v in semantic_segments_for_ui.items() if v}
            
            # print(f"DEBUG: Semantic segments AFTER filtering for video {video_file_name}: {semantic_segments}") 
            
            all_videos_analysis_data.append({
                "video_id": os.path.splitext(video_file_name)[0],
                "video_path": video_path,
                "semantic_segments": semantic_segments_for_ui, # 使用新的变量名
                "full_transcript_data": full_transcript_data,
                "product_types": list(video_product_types) if video_product_types else [], 
                "target_audiences": list(video_target_audiences) if video_target_audiences else [] # 使用新的变量存储和传递
            })
        
        st.session_state.all_videos_analysis_data = all_videos_analysis_data
        
        if not st.session_state.all_videos_analysis_data:
            st.warning("所有视频均分析完成，但未获得任何有效结果。")
        
        # 分析完成后，调用函数按语义类型组织视频片段
        try:
            logger.info("开始调用 organize_segments_by_type() 函数组织视频片段...")
            success = organize_segments_by_type()
            if success:
                st.success("已按语义类型组织视频片段到data/output目录")
                logger.info("视频片段已成功按语义类型组织")
            else:
                st.warning("视频片段组织过程中遇到问题，请查看日志了解详情")
                logger.warning("视频片段组织失败")
        except Exception as e:
            st.error(f"组织视频片段时出错: {str(e)}")
            logger.error(f"调用 organize_segments_by_type() 函数出错: {str(e)}", exc_info=True)

# 创建结果显示容器
results_container = st.container()
with results_container:
    if st.session_state.get('all_videos_analysis_data'):
        st.markdown("## 候选视频列表：")

        # 将视频数据分组，每组4个视频用于一行展示
        grouped_videos = [st.session_state.all_videos_analysis_data[i:i + 4] for i in range(0, len(st.session_state.all_videos_analysis_data), 4)]
        
        for video_group in grouped_videos:
            cols = st.columns(len(video_group))
            for i, video_data in enumerate(video_group):
                with cols[i]:
                    # 使用视频卡片样式
                    st.markdown(f"""    
                    <div class="video-card">
                        <h3>视频{video_data['video_id']}</h3>
                    </div>
                    """, unsafe_allow_html=True)
                    
                    # 显示产品类型和目标人群标签
                    product_types = video_data.get('product_types', [])
                    target_audiences = video_data.get('target_audiences', [])
                    
                    tags_html = '<div style="margin-bottom: 10px; display: flex; flex-wrap: wrap; align-items: center;">' # 使用flex布局

                    if product_types:
                        tags_html += '<div style="margin-right: 10px;">' # 产品类型组容器
                        for p_type in product_types:
                            tag_class = "tag-default"
                            if "水奶" in p_type:
                                tag_class = "tag-水奶"
                            elif "蕴淳" in p_type:
                                tag_class = "tag-蕴淳"
                            elif "蓝钻" in p_type: # 假设有蓝钻的样式
                                tag_class = "tag-蓝钻"
                            tags_html += f'<span class="tag {tag_class}">{p_type}</span> '
                        tags_html += '</div>'

                    if target_audiences:
                        tags_html += '<div>' # 目标人群组容器
                        # 根据config中的TARGET_GROUPS动态生成颜色或类别 (简化版，仅使用通用样式)
                        for audience in target_audiences:
                            # 查找audience在TARGET_GROUPS中的索引以分配不同颜色，或使用固定样式
                            # 这里我们使用统一的 tag-audience 样式，颜色在CSS中定义
                            audience_tag_class = "tag-audience" 
                            tags_html += f'<span class="tag {audience_tag_class}">{audience}</span> '
                        tags_html += '</div>'
                    
                    tags_html += '</div>' # 关闭flex容器
                    
                    if product_types or target_audiences:
                        st.markdown(tags_html, unsafe_allow_html=True)

                    # 检查语义分段结果是否为空
                    if not video_data['semantic_segments']:
                        st.warning(f"视频 {video_data['video_id']}: 未能成功进行语义分段。可能是由于API调用失败或模型无法处理该视频内容。请检查日志了解详情。")
                    else:
                        # 折叠框显示每个模块的分析结果
                        for module, segments_in_module in video_data['semantic_segments'].items():
                            if segments_in_module: # 确保该模块下有片段才显示
                                # 显示模块标题 (例如：广告开场：)
                                st.markdown(f"**{module}：**")
                                
                                # 遍历该模块下的所有片段
                                for segment in segments_in_module:
                                    # 显示匹配转录和时间段
                                    asr_text = segment.get('asr_matched_text', "(无匹配文本)")
                                    time_period = segment.get('time_period', "00:00:00 - 00:00:00")
                                    
                                    st.markdown(f"匹配转录：") # 固定文本
                                    st.markdown(f"{time_period}") # 实际时间戳
                                    
                                    # 显示实际的ASR文本
                                    st.markdown(f"\"{asr_text}\"")
                                    
                                    # 每个片段后可以加一个小的分隔，或者不加，根据视觉效果决定
                                    st.markdown("----", unsafe_allow_html=True) # 轻量级分隔
                                # 每个模块的所有片段显示完毕后，可以加一个更明显的分隔
                                st.markdown("<hr style='margin: 0.5rem 0;'>", unsafe_allow_html=True)
    elif analyze_button and not st.session_state.video_files:
        st.error("请先上传或指定一个视频文件/文件夹再进行分析！")

# --- 页脚或其他信息 ---
# st.sidebar.info("这是一个视频分析工具")

# 运行: streamlit run streamlit_app/app.py 