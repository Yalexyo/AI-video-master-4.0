"""
🧪 混剪工厂 - 重构版本
母婴奶粉种草短片自动化工厂 - 实现视频片段映射与合成

采用模块化设计，符合Streamlit最佳实践：
- 配置集中管理
- 功能模块化
- UI组件化
- 状态管理规范
- 缓存机制优化
"""

import streamlit as st

# 🔧 修复：将页面配置移到最顶部，避免StreamlitSetPageConfigMustBeFirstCommandError
st.set_page_config(
    page_title="🧪 混剪工厂",
    page_icon="🧪",
    layout="wide",
    initial_sidebar_state="expanded"
)
import logging
import sys
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple
import json
from datetime import datetime
import os

# 添加项目根目录到Python路径
current_dir = Path(__file__).parent.absolute()
project_root = current_dir.parent.parent
sys.path.insert(0, str(project_root))

# 导入配置和模块
from config.mixing_config import MixingConfig
from modules.mixing.ui_components import (
    render_quality_settings,
    render_strategy_selection,
    render_duration_ratio_config,
    render_sidebar_config,
    render_file_management,
    render_progress_display,
    display_srt_based_ratios,
    render_mapping_statistics
)
from utils.mixing.srt_utils import (
    calculate_srt_annotated_duration,
    get_marketing_hints,
    parse_srt_content
)

# 导入现有模块
from modules.mapper import VideoSegmentMapper, get_cached_mapping_results
from modules.composer import VideoComposer, create_output_filename, SelectionMode

# 导入selection_logger模块
try:
    from modules.selection_logger import start_new_session, get_selection_logger
except ImportError:
    from modules.selection_logger import start_new_session, get_selection_logger


class MixingFactory:
    """混剪工厂主类 - 封装所有核心功能"""
    
    def __init__(self):
        self.config = MixingConfig()
        self.logger = self._setup_logging()
        self._initialize_session_state()
    
    def _setup_logging(self) -> logging.Logger:
        """设置日志记录"""
        logger = logging.getLogger(__name__)
        if not logger.handlers:
            handler = logging.StreamHandler()
            formatter = logging.Formatter(
                '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
            )
            handler.setFormatter(formatter)
            logger.addHandler(handler)
            logger.setLevel(getattr(logging, self.config.LOG_LEVEL))
        return logger
    
    def _initialize_session_state(self) -> None:
        """初始化会话状态"""
        if "mapped_segments" not in st.session_state:
            st.session_state.mapped_segments = []
        if "mapping_statistics" not in st.session_state:
            st.session_state.mapping_statistics = {}
        if "composition_result" not in st.session_state:
            st.session_state.composition_result = None
        if "selection_strategy" not in st.session_state:
            st.session_state.selection_strategy = None
        if "target_ratios" not in st.session_state:
            st.session_state.target_ratios = {}
        if "srt_entries" not in st.session_state:
            st.session_state.srt_entries = []
        if "srt_annotations" not in st.session_state:
            st.session_state.srt_annotations = {}
        if "pool_scanned" not in st.session_state:
            st.session_state.pool_scanned = False
    
    def render_main_page(self) -> None:
        """渲染主页面"""
        # 页面标题
        st.title("🧪 混剪工厂")
        st.markdown("**母婴奶粉种草短片自动化工厂** - 视频片段映射与合成")
        
        # 侧边栏配置
        sidebar_config = render_sidebar_config()
        
        # 主要工作流
        self._render_main_workflow(sidebar_config)
    
    def _render_main_workflow(self, sidebar_config: Dict[str, Any]) -> None:
        """渲染主要工作流程"""
        
        # 🔧 优化：添加标杆视频SRT文件检测和加载
        self._detect_and_load_benchmark_srt()
        
        # 🔧 修复：根据侧边栏配置和SRT文件检测来设置pool_scanned状态
        has_video_pool_data = sidebar_config.get('path_exists', False)
        has_srt_data = bool(st.session_state.get('srt_entries'))
        
        # 如果有视频池数据或SRT数据，就认为可以开始工作
        if has_video_pool_data or has_srt_data:
            st.session_state.pool_scanned = True
        
        if not st.session_state.pool_scanned and not has_srt_data:
            self._render_no_data_guidance()
            return
        
        st.header("🎬 视频混剪工作流程")
        
        # 缓存管理
        st.markdown("---")
        with st.expander("🛠️ 缓存与调试工具"):
            col1, col2 = st.columns(2)
            
            with col1:
                if st.button("🔄 清除所有缓存并重新加载", help="点击此按钮将清除所有缓存数据（如片段映射结果），并刷新页面。当您更新了视频素材或修复了代码逻辑后，建议执行此操作。"):
                    # 清理所有缓存
                    st.cache_data.clear()
                    st.cache_resource.clear()
                    
                    # 🔧 核心修复：清理选片去重状态和日志实例
                    from modules.selection_logger import close_current_session
                    
                    # 关闭当前的日志会话
                    try:
                        close_current_session()
                    except Exception as e:
                        self.logger.warning(f"关闭日志会话失败: {e}")
                    
                    # 清理会话状态中的数据
                    keys_to_clear = [
                        "mapped_segments", 
                        "mapping_statistics", 
                        "composition_result",
                        "srt_entries",
                        "srt_annotations",
                        "pool_scanned",
                        # 🔧 新增：清理选片去重相关状态
                        "composition_used_segment_ids",
                        "selection_logger_instance"
                    ]
                    for key in keys_to_clear:
                        if key in st.session_state:
                            del st.session_state[key]
                    
                    st.success("✅ 所有缓存和会话状态已清除！页面将自动重新加载。")
                    # 强制重新运行以刷新状态
                    st.rerun()
            
            with col2:
                # 🆕 引导到调试工厂
                if st.button("🔧 前往调试工厂", 
                           help="前往调试工厂使用适配分类机制功能"):
                    st.info("💡 **提示**: 请前往 🐛 调试工厂 → 选择调试模式 → 适配分类机制")

        # 🔧 检查并执行映射（如果需要）
        if has_video_pool_data and not st.session_state.get('mapped_segments'):
            self._execute_mapping(sidebar_config)
        
        # 创建三个主要步骤的标签页
        tab1, tab2, tab3 = st.tabs(["📋 步骤1: 片段匹配策略", "⚙️ 步骤2: 策略配置", "🎬 步骤3: 视频合成"])
        
        with tab1:
            self._render_strategy_selection()
        
        with tab2:
            strategy = st.session_state.get('matching_strategy', 'algorithm_optimization')
            self._render_strategy_config(strategy)
        
        with tab3:
            self._render_video_composition()
    
    def _detect_and_load_benchmark_srt(self) -> None:
        """检测并加载标杆视频的SRT文件"""
        try:
            # 检查data/input/test_videos/目录下的SRT文件
            srt_files = []
            
            # 尝试多个可能的路径
            possible_paths = [
                Path("data/input/test_videos"),           # 当前目录下
                Path("../data/input/test_videos"),       # 上级目录下
                Path.cwd() / "data/input/test_videos",   # 当前工作目录
                Path.cwd().parent / "data/input/test_videos"  # 父目录
            ]
            
            self.logger.info(f"🔍 当前工作目录: {Path.cwd()}")
            
            test_videos_dir = None
            for path in possible_paths:
                self.logger.info(f"📁 检查路径: {path} (存在: {path.exists()})")
                if path.exists():
                    test_videos_dir = path
                    srt_files = list(path.glob("*.srt"))
                    self.logger.info(f"📄 在 {path} 找到SRT文件: {srt_files}")
                    if srt_files:
                        break
            
            if not test_videos_dir:
                self.logger.warning("⚠️ 未找到test_videos目录")
            
            # 如果找到SRT文件且还没有加载，则加载第一个
            if srt_files and not st.session_state.get('srt_entries'):
                srt_file = srt_files[0]  # 使用第一个找到的SRT文件
                self.logger.info(f"🎯 准备加载SRT文件: {srt_file}")
                
                try:
                    # 读取并解析SRT文件
                    with open(srt_file, 'r', encoding='utf-8') as f:
                        srt_content = f.read()
                    
                    srt_entries = parse_srt_content(srt_content)
                    
                    if srt_entries:
                        st.session_state.srt_entries = srt_entries
                        st.session_state.benchmark_srt_file = str(srt_file)
                        
                        # 🔧 初始化标注数据（如果不存在）并尝试加载已保存的标注
                        if not st.session_state.get('srt_annotations'):
                            st.session_state.srt_annotations = {}
                        
                        # 🔧 尝试加载已保存的标注文件
                        self._load_existing_annotations(srt_file.stem)
                        
                        self.logger.info(f"✅ 成功加载标杆视频SRT文件: {srt_file.name} ({len(srt_entries)} 个条目)")
                    else:
                        self.logger.warning(f"SRT文件解析结果为空: {srt_file}")
                        
                except Exception as e:
                    self.logger.error(f"加载SRT文件失败: {e}")
        
        except Exception as e:
            self.logger.error(f"检测标杆视频SRT文件时出错: {e}")
    
    def _execute_mapping(self, sidebar_config: Dict[str, Any]) -> None:
        """执行视频片段映射 - 使用AI智能分类"""
        try:
            st.markdown("### 🎯 AI智能分类")
            st.info("""
            **使用DeepSeek AI进行智能分类**
            - 深度理解标签语义和业务含义
            - 综合分析情绪、场景、品牌等多维度信息  
            - 更准确的模块分类决策
            """)
            
            video_pool_path = sidebar_config.get('video_pool_path')
            if video_pool_path:
                if st.button("🔄 开始AI智能扫描片段库", type="primary"):
                    with st.spinner("🎯 正在使用DeepSeek AI智能分类扫描视频片段库..."):
                        from modules.mapper import get_cached_mapping_results
                        
                        mapped_segments, statistics = get_cached_mapping_results(video_pool_path)
                        
                        st.session_state.mapped_segments = mapped_segments
                        st.session_state.mapping_statistics = statistics
                        st.session_state.classification_method = "AI智能分类"
                        
                        if mapped_segments:
                            st.success(f"✅ AI智能分类成功加载 {len(mapped_segments)} 个视频片段")
                            
                            # 显示分类统计
                            st.markdown("#### 📊 AI分类结果统计")
                            stats_by_category = statistics.get('by_category', {})
                            
                            cols = st.columns(4)
                            for i, (module, stats) in enumerate(stats_by_category.items()):
                                with cols[i % 4]:
                                    st.metric(module, stats.get('count', 0))
                            
                        else:
                            st.warning("⚠️ 未找到有效的视频片段")
        
        except Exception as e:
            self.logger.error(f"映射执行失败: {e}")
            st.error(f"映射失败: {e}")
    
    def _render_strategy_selection(self) -> None:
        """渲染片段匹配策略选择"""
        st.subheader("🎯 选择片段匹配策略")
        
        # 检查是否有SRT数据可用（只要有SRT条目就可以）
        has_srt_data = bool(st.session_state.get('srt_entries'))
        
        col1, col2 = st.columns(2)
        
        with col1:
            # SRT标注模式
            st.markdown("### 📋 SRT标注模式")
            
            if has_srt_data:
                st.success("✅ 适合：有清晰的SRT标注，希望精确控制")
                # 显示当前加载的SRT文件信息
                benchmark_file = st.session_state.get('benchmark_srt_file', '')
                srt_entries = st.session_state.get('srt_entries', [])
                if benchmark_file and srt_entries:
                    from pathlib import Path
                    st.info(f"📄 已加载: {Path(benchmark_file).name} ({len(srt_entries)} 个条目)")
            else:
                st.info("📝 需要：标杆视频的SRT标注文件")
                
                # 添加手动刷新按钮
                if st.button("🔄 重新扫描SRT文件", key="refresh_srt"):
                    # 清除现有的SRT数据
                    if 'srt_entries' in st.session_state:
                        del st.session_state.srt_entries
                    if 'benchmark_srt_file' in st.session_state:
                        del st.session_state.benchmark_srt_file
                    if 'srt_annotations' in st.session_state:
                        del st.session_state.srt_annotations
                    
                    # 显示检测信息
                    with st.spinner("🔍 正在扫描SRT文件..."):
                        # 重新检测和加载
                        self._detect_and_load_benchmark_srt()
                        
                        # 显示扫描结果
                        if st.session_state.get('srt_entries'):
                            st.success("✅ SRT文件扫描成功！")
                            # 检查是否有标注被加载
                            if st.session_state.get('srt_annotations'):
                                annotations_count = sum(1 for ann in st.session_state.srt_annotations.values() if ann != "未标注")
                                if annotations_count > 0:
                                    st.info(f"📋 已自动加载 {annotations_count} 个已保存的标注")
                        else:
                            # 显示调试信息
                            st.error("❌ 未找到SRT文件")
                            with st.expander("🔧 调试信息"):
                                from pathlib import Path
                                possible_paths = [
                                    Path("data/input/test_videos"),
                                    Path("../data/input/test_videos"),
                                    Path.cwd() / "data/input/test_videos",
                                    Path.cwd().parent / "data/input/test_videos"
                                ]
                                
                                st.write(f"**当前工作目录**: {Path.cwd()}")
                                st.write("**检查的路径**:")
                                for i, path in enumerate(possible_paths, 1):
                                    exists = path.exists()
                                    if exists:
                                        srt_files = list(path.glob("*.srt"))
                                        st.write(f"{i}. ✅ `{path}` - 找到 {len(srt_files)} 个SRT文件: {[f.name for f in srt_files]}")
                                    else:
                                        st.write(f"{i}. ❌ `{path}` - 路径不存在")
                    
                    st.rerun()
            
            st.markdown("""
            **特点：**
            - 🎯 严格按照您的时间配置
            - 📊 自动从SRT标注计算时长比例
            - 🎚️ 支持细致的时间调整
            - 🎭 完整的音乐场景化控制
            """)
            
            srt_disabled = not has_srt_data
            if st.button("🎬 选择SRT标注模式", disabled=srt_disabled, key="select_srt_mode"):
                st.session_state.matching_strategy = 'manual_annotation'
                
                if has_srt_data:
                    st.success("✅ 已选择 - SRT标注模式 - 基于手动编辑的时间配置")
                    st.rerun()
        
        with col2:
            # 算法优化模式  
            st.markdown("### 🧠 算法优化模式")
            st.success("✅ 适合：希望AI自动化，效率最佳组合")
            
            st.markdown("""
            **特点：**
            - 🤖 使用AI质量评估进行智能片段筛选
            - 📈 手动设置权重（语义，质量，时长）
            - 🚀 支持多种预设的质量优化功能
            - 📝 支持智能质量评估算法支持功能
            """)
            
            if st.button("🎬 选择算法优化模式", key="select_algorithm_mode"):
                st.session_state.matching_strategy = 'algorithm_optimization'
                st.success("✅ 已选择 - 算法优化模式")
                st.rerun()
        
        # 显示当前选择的策略
        current_strategy = st.session_state.get('matching_strategy')
        if current_strategy:
            if current_strategy == 'manual_annotation':
                st.info("🎯 **当前策略**: SRT标注模式")
            else:
                st.info("🧠 **当前策略**: 算法优化模式")
        
        # 🆕 添加标杆视频模块划分功能
        if has_srt_data:
            st.markdown("---")
            self._render_benchmark_annotation_tool()
    
    def _render_benchmark_annotation_tool(self) -> None:
        """渲染标杆视频模块划分工具"""
        st.subheader("📝 标杆视频模块划分")
        
        srt_entries = st.session_state.get('srt_entries', [])
        srt_annotations = st.session_state.get('srt_annotations', {})
        benchmark_file = st.session_state.get('benchmark_srt_file', '')
        
        if not srt_entries:
            st.warning("⚠️ 未找到可标注的SRT条目")
            return
        
        # 显示SRT文件信息
        st.info(f"📄 **标杆视频**: {Path(benchmark_file).name if benchmark_file else '未知文件'} | **条目数**: {len(srt_entries)}")
        
        # 模块类型定义
        module_types = ["未标注", "痛点", "解决方案", "卖点", "促销"]
        module_colors = {
            "未标注": "⚪", 
            "痛点": "🔴", 
            "解决方案": "🟢", 
            "卖点": "🟡", 
            "促销": "🟠"
        }
        
        # 统计信息
        col1, col2, col3, col4 = st.columns(4)
        
        annotated_count = sum(1 for annotation in srt_annotations.values() if annotation != "未标注")
        total_annotated_duration = 0
        
        for entry in srt_entries:
            entry_index = entry['index']
            annotation = srt_annotations.get(entry_index, "未标注")
            if annotation != "未标注":
                total_annotated_duration += entry.get('duration', 0)
        
        with col1:
            st.metric("总条目数", len(srt_entries))
        with col2:
            st.metric("已标注条目", annotated_count)
        with col3:
            st.metric("标注进度", f"{annotated_count/len(srt_entries)*100:.1f}%")
        with col4:
            st.metric("已标注时长", f"{total_annotated_duration:.1f}s")
        
        # 批量标注工具
        st.markdown("#### 🛠️ 批量标注工具")
        
        col1, col2, col3 = st.columns([2, 1, 1])
        
        with col1:
            bulk_module = st.selectbox("选择模块类型", module_types[1:], key="bulk_module")
        
        with col2:
            start_index = st.number_input("起始条目", min_value=1, max_value=len(srt_entries), value=1, key="bulk_start")
        
        with col3:
            end_index = st.number_input("结束条目", min_value=1, max_value=len(srt_entries), value=min(5, len(srt_entries)), key="bulk_end")
        
        if st.button("🎯 批量标注", key="bulk_annotate"):
            for i in range(start_index, min(end_index + 1, len(srt_entries) + 1)):
                srt_annotations[i] = bulk_module
            st.session_state.srt_annotations = srt_annotations
            st.success(f"✅ 已将条目 {start_index}-{end_index} 标注为「{bulk_module}」")
            st.rerun()
        
        # 快速操作按钮
        st.markdown("#### ⚡ 快速操作")
        
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            if st.button("🗑️ 清除所有标注", key="clear_all"):
                st.session_state.srt_annotations = {}
                st.success("已清除所有标注")
                st.rerun()
        
        with col2:
            if st.button("📋 自动推荐标注", key="auto_suggest"):
                # TODO: 集成AI自动标注功能
                st.info("🚧 AI自动标注功能正在开发中")
        
        with col3:
            if st.button("💾 保存标注", key="save_annotations"):
                self._save_srt_annotations()
        
        with col4:
            if st.button("📤 导出SRT", key="export_srt"):
                self._export_annotated_srt()
        
        # 详细标注界面
        st.markdown("#### 📋 详细标注")
        
        # 分页显示
        entries_per_page = 10
        total_pages = (len(srt_entries) + entries_per_page - 1) // entries_per_page
        
        if total_pages > 1:
            current_page = st.selectbox("选择页面", range(1, total_pages + 1), key="annotation_page") - 1
        else:
            current_page = 0
        
        start_idx = current_page * entries_per_page
        end_idx = min(start_idx + entries_per_page, len(srt_entries))
        
        for i in range(start_idx, end_idx):
            entry = srt_entries[i]
            entry_index = entry['index']
            
            current_annotation = srt_annotations.get(entry_index, "未标注")
            
            with st.container():
                col1, col2, col3 = st.columns([1, 4, 2])
                
                with col1:
                    st.markdown(f"**#{entry_index}**")
                    st.markdown(f"⏱️ {entry.get('duration', 0):.1f}s")
                
                with col2:
                    st.markdown(f"**{entry.get('timestamp', '')}**")
                    # 限制文本显示长度
                    text = entry.get('text', '')
                    if len(text) > 100:
                        text = text[:100] + "..."
                    st.markdown(f"🗣️ {text}")
                
                with col3:
                    new_annotation = st.selectbox(
                        "模块", 
                        module_types, 
                        index=module_types.index(current_annotation),
                        key=f"annotation_{entry_index}",
                        label_visibility="collapsed"
                    )
                    
                    if new_annotation != current_annotation:
                        srt_annotations[entry_index] = new_annotation
                        st.session_state.srt_annotations = srt_annotations
                        st.rerun()
                
                # 显示状态指示器
                color_indicator = module_colors.get(current_annotation, "⚪")
                st.markdown(f"{color_indicator} **{current_annotation}**")
                
                st.markdown("---")
    
    def _save_srt_annotations(self) -> None:
        """保存SRT标注数据到指定目录"""
        try:
            # 🔧 修改保存路径到用户指定目录
            target_dir = Path("/Users/sshlijy/Desktop/AI-video-master-4.0/data/input/test_videos")
            
            # 如果绝对路径不存在，尝试相对路径
            if not target_dir.exists():
                possible_paths = [
                    Path("data/input/test_videos"),
                    Path("../data/input/test_videos"),
                    Path.cwd() / "data/input/test_videos",
                    Path.cwd().parent / "data/input/test_videos"
                ]
                
                for path in possible_paths:
                    if path.exists():
                        target_dir = path
                        break
                else:
                    # 如果都不存在，创建相对路径
                    target_dir = Path("data/input/test_videos")
                    target_dir.mkdir(parents=True, exist_ok=True)
            
            benchmark_file = st.session_state.get('benchmark_srt_file', '')
            if benchmark_file:
                base_name = Path(benchmark_file).stem
                annotation_file = target_dir / f"{base_name}_annotations.json"
                
                annotation_data = {
                    "benchmark_file": benchmark_file,
                    "timestamp": datetime.now().isoformat(),
                    "annotations": st.session_state.get('srt_annotations', {}),
                    "entries_count": len(st.session_state.get('srt_entries', []))
                }
                
                with open(annotation_file, 'w', encoding='utf-8') as f:
                    json.dump(annotation_data, f, ensure_ascii=False, indent=2)
                
                self.logger.info(f"标注数据已保存到: {annotation_file}")
                st.success(f"✅ 标注已保存到: {annotation_file}")
        
        except Exception as e:
            self.logger.error(f"保存标注数据失败: {e}")
            st.error(f"保存失败: {e}")
    
    def _load_existing_annotations(self, base_name: str) -> None:
        """加载已存在的标注文件"""
        try:
            # 查找标注文件的可能路径
            possible_paths = [
                Path("/Users/sshlijy/Desktop/AI-video-master-4.0/data/input/test_videos"),
                Path("data/input/test_videos"),
                Path("../data/input/test_videos"),
                Path.cwd() / "data/input/test_videos",
                Path.cwd().parent / "data/input/test_videos"
            ]
            
            annotation_file = None
            for path in possible_paths:
                potential_file = path / f"{base_name}_annotations.json"
                if potential_file.exists():
                    annotation_file = potential_file
                    break
            
            if annotation_file:
                with open(annotation_file, 'r', encoding='utf-8') as f:
                    annotation_data = json.load(f)
                
                # 加载标注数据到session_state
                saved_annotations = annotation_data.get('annotations', {})
                if saved_annotations:
                    # 转换键为整数（JSON中键是字符串）
                    converted_annotations = {}
                    for key, value in saved_annotations.items():
                        try:
                            converted_annotations[int(key)] = value
                        except ValueError:
                            converted_annotations[key] = value
                    
                    st.session_state.srt_annotations = converted_annotations
                    self.logger.info(f"✅ 成功加载已保存的标注: {annotation_file} ({len(saved_annotations)} 个标注)")
                    
                    # 在UI中显示加载成功信息
                    if hasattr(st, 'session_state') and not st.session_state.get('annotation_load_shown'):
                        st.info(f"📋 已加载保存的标注: {len(saved_annotations)} 个条目已标注")
                        st.session_state.annotation_load_shown = True
                else:
                    self.logger.info(f"标注文件存在但无标注数据: {annotation_file}")
            else:
                self.logger.info(f"未找到现有标注文件: {base_name}_annotations.json")
                
        except Exception as e:
            self.logger.error(f"加载标注文件失败: {e}")
    
    def _export_annotated_srt(self) -> None:
        """导出带标注的SRT文件"""
        try:
            srt_entries = st.session_state.get('srt_entries', [])
            srt_annotations = st.session_state.get('srt_annotations', {})
            
            if not srt_entries:
                st.warning("没有SRT条目可导出")
                return
            
            # 生成带标注的SRT内容
            srt_content = []
            
            for entry in srt_entries:
                entry_index = entry['index']
                annotation = srt_annotations.get(entry_index, "未标注")
                
                srt_content.append(str(entry_index))
                srt_content.append(entry.get('timestamp', ''))
                
                # 在文本中添加标注信息
                text = entry.get('text', '')
                if annotation != "未标注":
                    text = f"[{annotation}] {text}"
                
                srt_content.append(text)
                srt_content.append("")  # 空行
            
            # 提供下载
            srt_string = "\n".join(srt_content)
            
            st.download_button(
                label="📤 下载带标注的SRT文件",
                data=srt_string,
                file_name=f"annotated_{Path(st.session_state.get('benchmark_srt_file', 'unknown')).name}",
                mime="text/plain"
            )
        
        except Exception as e:
            self.logger.error(f"导出标注SRT失败: {e}")
            st.error(f"导出失败: {e}")
    
    def _render_no_data_guidance(self) -> None:
        """渲染无数据指导界面"""
        st.warning("### 🆘 需要先准备视频片段数据")
        
        tab1, tab2 = st.tabs(["🎯 推荐方案", "🔧 手动方案"])
        
        with tab1:
            st.markdown("""
            #### 📹 **使用视频分析模块（推荐）**
            
            **步骤**：
            1. 🏠 回到首页，选择"视频分析"模块
            2. 📤 上传达人视频文件到系统
            3. 🤖 让AI自动分析视频内容和片段
            4. 💾 分析结果会自动保存到video_pool目录
            5. 🔄 回到这里进行片段映射
            
            **优势**：
            - ✅ 全自动化处理
            - ✅ 标准化的分析结果
            - ✅ 包含完整的标签和质量信息
            """)
            
            col1, col2, col3 = st.columns([1, 1, 1])
            with col2:
                if st.button("🏠 前往视频分析模块", type="primary", use_container_width=True):
                    st.info("💡 请前往视频分析模块完成视频处理")
        
        with tab2:
            st.markdown("""
            #### 🛠️ **手动准备数据**
            
            **如果您已有分析好的JSON文件**：
            1. 📁 确保文件格式正确（包含视频片段的标签、质量分等信息）
            2. 📋 将JSON文件复制到 `data/output/google_video/` 对应的子目录中
            3. 🔄 刷新页面，然后选择对应的切片目录开始映射
            """)
            
            # 文件管理组件
            render_file_management()
    
    def _render_strategy_config(self, strategy: str) -> None:
        """渲染策略配置"""
        st.subheader("🎛️ 策略配置")
        
        if strategy == 'manual_annotation':
            st.success("📊 **自动计算**: 将根据您的SRT标注直接计算时长比例")
            
            # SRT标注模式配置
            srt_entries = st.session_state.get('srt_entries', [])
            srt_annotations = st.session_state.get('srt_annotations', {})
            
            if srt_entries and srt_annotations:
                auto_target_duration = calculate_srt_annotated_duration(srt_entries, srt_annotations)
                
                if auto_target_duration > 0:
                    st.success(f"⏱️ **自动计算目标时长**: {auto_target_duration:.1f}秒")
                    
                    # 允许微调
                    enable_adjust = st.checkbox("🎛️ 允许微调目标时长", value=False)
                    if enable_adjust:
                        target_duration = st.number_input(
                            "微调目标时长 (秒)",
                            min_value=10,
                            max_value=300,
                            value=int(auto_target_duration),
                            key='srt_target_duration_adjust'
                        )
                    else:
                        target_duration = auto_target_duration
                    
                    st.session_state.target_duration = target_duration
                
                # 显示预估比例
                display_srt_based_ratios(srt_entries, srt_annotations)
            else:
                st.warning("⚠️ 无法计算SRT标注时长，使用默认值")
                st.session_state.target_duration = self.config.DEFAULT_TARGET_DURATION
        else:
            st.warning("⚙️ **手动配置**: 请设置各模块时长比例")
            
            # 算法优化模式配置
            target_duration = st.number_input(
                "目标时长 (秒)",
                min_value=10,
                max_value=300,
                value=st.session_state.get('target_duration', self.config.DEFAULT_TARGET_DURATION),
                key='manual_target_duration'
            )
            st.session_state.target_duration = target_duration
            
            # 配置比例
            target_ratios = render_duration_ratio_config()
            st.session_state.target_ratios = target_ratios
    
    def _render_video_composition(self) -> None:
        """渲染视频合成"""
        st.header("🎬 步骤3: 视频合成")
        
        # 质量设置
        quality_settings = render_quality_settings()
        
        # 合成按钮
        if st.button("🎬 开始视频合成", type="primary"):
            self._execute_composition(st.session_state.get('matching_strategy', 'algorithm_optimization'), quality_settings)
    
    def _execute_composition(self, strategy: str, quality_settings: Dict[str, Any]) -> None:
        """执行视频合成"""
        try:
            with st.spinner("🎬 正在合成视频..."):
                # 获取参数
                mapped_segments = st.session_state.mapped_segments
                target_ratios = st.session_state.get('target_ratios', {})
                target_duration = st.session_state.get('target_duration', self.config.DEFAULT_TARGET_DURATION)
                
                # 创建composer实例
                composer = VideoComposer()
                
                # 🔧 第一步：初始化会话级别的状态管理
                if 'composition_used_segment_ids' not in st.session_state:
                    st.session_state.composition_used_segment_ids = set()
                else:
                    # 清空之前的记录，开始新的合成会话
                    st.session_state.composition_used_segment_ids.clear()
                
                self.logger.info("🔧 初始化会话级别的片段去重集合")
                
                # 🔧 第二步：启动选片日志记录（使用session_state管理）
                self.logger.info("启动选片决策日志记录...")
                selection_logger = start_new_session()
                
                # 🔧 第三步：选择片段
                self.logger.info("第一步：根据策略选择片段...")
                
                if strategy == 'manual_annotation':
                    # SRT标注模式：使用标注比例
                    ratios_list = [
                        target_ratios.get("痛点", 0.25) * 100,
                        target_ratios.get("解决方案", 0.25) * 100,
                        target_ratios.get("卖点", 0.25) * 100,
                        target_ratios.get("促销", 0.25) * 100
                    ]
                else:
                    # 算法优化模式：使用默认比例
                    ratios_list = [25, 25, 25, 25]
                
                # 🔧 核心修复：传入会话级别的used_segment_ids集合，确保真正的全局去重
                selection_result = composer.select_segments_by_duration(
                    mapped_segments=mapped_segments,
                    target_ratios=ratios_list,
                    total_target_duration=target_duration,
                    used_segment_ids=st.session_state.composition_used_segment_ids
                )
                
                if not selection_result.get("selected_segments"):
                    raise Exception("片段选择失败：没有找到合适的片段")
                
                # 🔧 选片记录已在composer.py中完成，无需重复记录
                # 选片详细日志和去重验证已在select_segments_by_duration中处理
                
                # 🔧 第三步：合成视频
                self.logger.info("第二步：合成视频...")
                
                # 生成输出文件名
                from modules.composer import create_output_filename
                output_filename = create_output_filename("混剪工厂")
                # 不需要重复添加路径前缀，create_output_filename已经包含完整路径
                output_path = output_filename
                
                # 确保输出目录存在
                os.makedirs(os.path.dirname(output_path), exist_ok=True)
                
                # 🎯 检查是否有标杆视频音频文件
                benchmark_audio_path = self._find_benchmark_audio()
                
                if not benchmark_audio_path:
                    # ❌ 无标杆音频时直接报错
                    error_msg = (
                        "❌ 未找到标杆音频文件！\n\n"
                        "请确保在 `data/input/test_videos/` 目录下放置标杆音频或视频文件。\n"
                        "支持的格式：\n"
                        "• 音频文件：MP3, WAV, M4A, AAC\n"
                        "• 视频文件：MP4, AVI, MOV, MKV\n\n"
                        "标杆音频是保证视频质量和音频一致性的关键要素。"
                    )
                    self.logger.error("合成失败：缺少标杆音频文件")
                    st.error(error_msg)
                    raise Exception("缺少标杆音频文件，无法进行视频合成")
                
                # 🎵 使用标杆音频合成（SRT模式和算法模式都使用标杆音频）
                self.logger.info(f"使用标杆音频进行合成: {benchmark_audio_path}")
                st.info("🎵 检测到标杆视频音频，将使用标杆音频替换片段音频")
                
                result = composer.compose_video_with_benchmark_audio(
                    selected_segments=selection_result["selected_segments"],
                    output_path=output_path,
                    benchmark_audio_path=benchmark_audio_path,
                    resolution=quality_settings["resolution"],
                    bitrate=quality_settings["bitrate"],
                    fps=quality_settings["fps"],
                    use_segment_audio=False  # 完全使用标杆音频，不使用片段原音频
                )
                
                # 保存结果到 session state
                st.session_state.composition_result = result
                
                # 💾 保存详细合成结果到JSON文件
                if result and result.get('success'):
                    self._save_composition_result_json(result, selection_result, strategy, quality_settings)
                    st.success("✅ 视频合成完成！")
                    self._display_composition_result(result)
                    
                    # 🔧 记录合成完成并关闭日志记录器
                    summary = selection_logger.get_session_summary()
                    self.logger.info(f"📋 选片日志会话总结: {summary}")
                    # 🔧 使用统一的session_state关闭方式
                    from modules.selection_logger import close_current_session
                    close_current_session()
                else:
                    st.error(f"❌ 视频合成失败: {result.get('error', '未知错误')}")
                    # 即使失败也要关闭日志记录器
                    from modules.selection_logger import close_current_session
                    close_current_session()
        
        except Exception as e:
            st.error(f"❌ 合成过程发生错误: {str(e)}")
            self.logger.error(f"合成失败: {str(e)}")
            # 🔧 确保异常情况下也关闭日志记录器（优先使用session_state中的实例）
            try:
                from modules.selection_logger import close_current_session
                close_current_session()
            except Exception as cleanup_error:
                self.logger.warning(f"异常情况下关闭日志会话失败: {cleanup_error}")
                # 备用方案：尝试关闭局部变量
            try:
                if 'selection_logger' in locals():
                    selection_logger.close()
            except:
                pass
    
    def _find_benchmark_audio(self) -> str:
        """查找标杆视频音频文件"""
        try:
            # 尝试多个可能的路径
            possible_paths = [
                Path("data/input/test_videos"),           # 当前目录下
                Path("../data/input/test_videos"),       # 上级目录下
                Path("../../data/input/test_videos")     # 上上级目录下
            ]
            
            for test_videos_dir in possible_paths:
                self.logger.info(f"🔍 检查音频文件路径: {test_videos_dir} (存在: {test_videos_dir.exists()})")
                
                if test_videos_dir.exists():
                    # 查找常见音频格式（移除重复的mp4）
                    audio_extensions = ['*.mp3', '*.wav', '*.m4a', '*.aac']
                    
                    for extension in audio_extensions:
                        audio_files = list(test_videos_dir.glob(extension))
                        if audio_files:
                            audio_file = audio_files[0]  # 使用第一个找到的音频文件
                            self.logger.info(f"✅ 找到标杆音频文件: {audio_file}")
                            return str(audio_file)
                    
                    # 如果没有找到音频文件，检查是否有视频文件可以提取音频
                    video_extensions = ['*.mp4', '*.avi', '*.mov', '*.mkv']
                    for extension in video_extensions:
                        video_files = list(test_videos_dir.glob(extension))
                        if video_files:
                            video_file = video_files[0]
                            self.logger.info(f"✅ 找到标杆视频文件，将提取音频: {video_file}")
                            return str(video_file)  # 直接返回视频文件路径，composer会处理音频提取
                    
                    # 如果在这个路径下没找到文件，继续尝试下一个路径
                    self.logger.warning(f"⚠️ 在 {test_videos_dir} 中未找到音频或视频文件")
            
            self.logger.error("❌ 在所有可能路径中都未找到标杆音频文件")
            return None
        
        except Exception as e:
            self.logger.error(f"查找标杆音频文件时出错: {e}")
            return None
    
    def _apply_duration_control(self, selected_segments: Dict[str, List[Dict]], target_duration: float) -> Dict[str, List[Dict]]:
        """对选择的片段进行精确时长控制"""
        try:
            # 计算当前总时长
            current_total_duration = 0
            for module_segments in selected_segments.values():
                for segment in module_segments:
                    current_total_duration += segment.get('duration', 0)
            
            self.logger.info(f"当前片段总时长: {current_total_duration:.1f}s, 目标时长: {target_duration:.1f}s")
            
            # 如果当前时长接近目标时长（误差在±2秒内），直接返回
            if abs(current_total_duration - target_duration) <= 2.0:
                self.logger.info("时长已接近目标，无需调整")
                return selected_segments
            
            # 计算缩放比例
            scale_factor = target_duration / current_total_duration if current_total_duration > 0 else 1.0
            self.logger.info(f"时长缩放比例: {scale_factor:.3f}")
            
            # 应用缩放到每个片段
            controlled_segments = {}
            
            for module_name, module_segments in selected_segments.items():
                controlled_segments[module_name] = []
                
                for segment in module_segments:
                    # 创建新的片段副本
                    controlled_segment = segment.copy()
                    
                    # 计算新的时长
                    original_duration = segment.get('duration', 0)
                    new_duration = original_duration * scale_factor
                    
                    # 更新片段信息
                    controlled_segment['duration'] = new_duration
                    controlled_segment['controlled_duration'] = new_duration
                    controlled_segment['original_duration'] = original_duration
                    controlled_segment['scale_factor'] = scale_factor
                    
                    controlled_segments[module_name].append(controlled_segment)
            
            # 验证调整后的总时长
            new_total_duration = sum(
                segment.get('controlled_duration', 0) 
                for module_segments in controlled_segments.values() 
                for segment in module_segments
            )
            
            self.logger.info(f"调整后总时长: {new_total_duration:.1f}s")
            return controlled_segments
        
        except Exception as e:
            self.logger.error(f"时长控制调整失败: {e}")
            return selected_segments
    
    def _save_composition_result_json(self, result: Dict[str, Any], selection_result: Dict[str, Any], strategy: str, quality_settings: Dict[str, Any]) -> None:
        """保存合成结果到JSON文件，供调试工厂使用"""
        try:
            from datetime import datetime
            import json
            
            # 获取输出视频路径，从中提取文件名
            output_path = result.get('output_path', '')
            if not output_path:
                self.logger.warning("无法保存JSON：缺少输出路径")
                return
            
            # 生成同名JSON文件路径
            video_path = Path(output_path)
            json_filename = video_path.stem + "_composition_result.json"
            json_path = video_path.parent / json_filename
            
            # 构建完整的合成结果数据
            composition_data = {
                # 基本信息
                "metadata": {
                    "timestamp": datetime.now().isoformat(),
                    "strategy": strategy,
                    "quality_settings": quality_settings,
                    "video_filename": video_path.name,
                    "video_path": str(video_path),
                    "json_version": "1.0"
                },
                
                # 合成结果信息
                "composition_result": {
                    "success": result.get('success', False),
                    "duration": result.get('duration', 0),
                    "segment_count": result.get('segment_count', 0),
                    "file_size": result.get('file_size', 0),
                    "output_path": result.get('output_path', ''),
                    "error": result.get('error'),
                    "audio_strategy": result.get('audio_strategy'),
                    "output_quality": result.get('output_quality', {})
                },
                
                # 片段选择结果
                "selection_result": {
                    "total_duration": selection_result.get('total_duration', 0),
                    "target_duration": selection_result.get('target_duration', 0),
                    "module_details": selection_result.get('module_details', {}),
                    "selection_mode": strategy
                },
                
                # 详细片段信息 - 这是调试工厂最需要的数据
                "selected_segments": {}
            }
            
            # 提取每个模块的详细片段信息
            selected_segments = selection_result.get('selected_segments', {})
            for module_name, segments in selected_segments.items():
                composition_data["selected_segments"][module_name] = []
                
                for segment in segments:
                    segment_info = {
                        "file_name": segment.get('file_name', ''),
                        "video_id": segment.get('video_id', ''),
                        "segment_id": segment.get('segment_id', ''),
                        "duration": segment.get('duration', 0),
                        "start_time": segment.get('start_time', 0),
                        "end_time": segment.get('end_time', 0),
                        "category": segment.get('category', module_name),
                        "all_tags": segment.get('all_tags', []),
                        "combined_quality": segment.get('combined_quality', 0),
                        "file_path": segment.get('file_path', ''),
                        "transcription": segment.get('transcription', ''),
                        # 添加其他可能需要的字段
                        "original_duration": segment.get('original_duration'),
                        "controlled_duration": segment.get('controlled_duration'),
                        "scale_factor": segment.get('scale_factor')
                    }
                    composition_data["selected_segments"][module_name].append(segment_info)
            
            # 保存JSON文件
            with open(json_path, 'w', encoding='utf-8') as f:
                json.dump(composition_data, f, ensure_ascii=False, indent=2)
            
            self.logger.info(f"✅ 合成结果JSON已保存: {json_path}")
            st.info(f"📄 **合成详情已保存**: `{json_filename}`")
            
        except Exception as e:
            self.logger.error(f"保存合成结果JSON失败: {e}")
            st.warning(f"⚠️ 保存合成详情失败: {e}")



    def _display_composition_result(self, result: Dict[str, Any]) -> None:
        """显示合成结果"""
        st.subheader("🎉 合成结果")
        
        if result.get('output_path'):
            st.success(f"📁 输出文件: {result['output_path']}")
        
        if result.get('duration'):
            st.info(f"⏱️ 视频时长: {result['duration']:.1f}秒")
        
        if result.get('selected_segments'):
            st.info(f"🎬 使用片段数: {len(result['selected_segments'])}")
        
        # 详细信息
        with st.expander("📊 详细信息", expanded=False):
            st.json(result)
    
    def _render_debug_tools(self) -> None:
        """渲染调试工具"""
        st.header("🔧 调试工具")
        
        # 配置验证
        st.subheader("⚙️ 配置验证")
        
        if st.button("🔍 验证配置"):
            checks = self.config.validate_config()
            
            for check_name, status in checks.items():
                if status:
                    st.success(f"✅ {check_name}")
                else:
                    st.error(f"❌ {check_name}")
        
        # 缓存管理
        st.subheader("🗑️ 缓存管理")
        
        col1, col2 = st.columns(2)
        
        with col1:
            if st.button("清除映射缓存"):
                st.cache_data.clear()
                st.success("映射缓存已清除")
        
        with col2:
            if st.button("清除所有缓存"):
                st.cache_data.clear()
                st.cache_resource.clear()
                st.success("所有缓存已清除")
        
        # 状态查看
        st.subheader("📊 状态查看")
        
        if st.checkbox("显示Session State", value=False):
            st.json(dict(st.session_state))


def main():
    """主函数"""
    # 创建并运行混剪工厂（页面配置已在文件顶部设置）
    factory = MixingFactory()
    factory.render_main_page()


if __name__ == "__main__":
    main() 