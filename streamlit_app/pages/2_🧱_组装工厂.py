"""
🧱 组装工厂 - 重构版本
智能视频片段分析与处理中心

采用模块化设计，符合Streamlit最佳实践：
- 配置集中管理
- UI组件化
- 业务逻辑独立
- 多模型协同分析
"""

import streamlit as st
import logging
import sys
from pathlib import Path
from typing import Dict, Any, List, Optional

# 添加项目路径
sys.path.append(str(Path(__file__).parent.parent.parent))

# 导入配置和模块
from streamlit_app.config.factory_config import FactoryConfig
from streamlit_app.modules.factory.assembly_components import (
    render_video_upload_section,
    render_analysis_features,
    render_batch_analysis_settings,
    render_clustering_settings,
    render_video_selector,
    render_analysis_results_display,
    render_progress_tracking,
    render_credentials_check,
    render_action_buttons,
    render_error_display,
    render_model_selection,
    render_prompt_configuration
)
from streamlit_app.utils.factory.video_analysis_utils import (
    analyze_video_with_google_cloud,
    create_video_segments,
    validate_analysis_dependencies,
    # analyze_segments_with_qwen,
    # analyze_segments_with_intelligent_strategy,
)

# 🚀 导入优化版本的分析函数
from streamlit_app.utils.factory.optimized_video_analysis import analyze_segments_with_high_efficiency


class AssemblyFactory:
    """组装工厂主类 - 封装所有核心功能"""
    
    def __init__(self):
        self.config = FactoryConfig()
        self.logger = self._setup_logging()
        self.assembly_config = self.config.get_assembly_config()
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
        if "analysis_results" not in st.session_state:
            st.session_state.analysis_results = {}
        if "current_video_id" not in st.session_state:
            st.session_state.current_video_id = None
        if "segment_files" not in st.session_state:
            st.session_state.segment_files = []
    
    def render_main_page(self) -> None:
        """渲染主页面"""
        st.title("🧱 组装工厂")
        
        st.markdown("""
        🎯 **组装工厂** - 智能视频片段分析与处理中心
        
        **🔄 完整工作流程**:
        1. **🎬 视频分析与切分** → 使用Google Cloud对原始视频进行分析和切分
        2. **🏷️ 智能标签工厂** → 使用Qwen+DeepSeek对片段进行深度标签分析
        3. **🧠 场景聚合** → 智能合并相似片段，优化场景连贯性
        
        **⚙️ 技术架构**:
        - **Google Cloud**: 专用于原始视频的镜头检测和基础分析
        - **Qwen模型**: 轻量化视觉理解，快速标签提取
        - **DeepSeek模型**: 智能兜底分析，处理复杂场景
        
        **📋 使用建议**: 
        - 新视频 → 先用"视频分析与切分"
        - 已有片段 → 直接用"智能标签工厂"
        """)
        
        st.markdown("---")
        
        # 功能选择标签页
        tab1, tab2, tab3, tab4, tab5 = st.tabs([
            "🎬 视频分析与切分", 
            "🧠 场景聚合",
            "🏷️ 智能标签工厂", 
            "🤖 Prompt配置",
            "⚙️ 设置"
        ])
        
        with tab1:
            self._render_video_analysis_tab()
        
        with tab2:
            self._render_scene_clustering_tab()
        
        with tab3:
            self._render_intelligent_labeling_tab()
        
        with tab4:
            self._render_prompt_configuration_tab()
        
        with tab5:
            self._render_settings_tab()
    
    def _render_video_analysis_tab(self) -> None:
        """渲染视频分析标签页"""
        st.header("🎬 视频分析与切分")
        
        st.info("💡 **视频分析与切分**负责原始视频的智能分析和自动切分，主要使用Google Cloud进行镜头检测、物体识别等基础分析。")
        
        # 检查凭据
        if not render_credentials_check():
            st.stop()
        
        # 视频上传
        uploaded_video, use_sample_video = render_video_upload_section()
        
        if uploaded_video or use_sample_video:
            # 分析功能选择
            analysis_features = render_analysis_features()
            
            st.markdown("### 📊 分析说明")
            st.info("""
            🎯 **此模块的作用**：
            - 🎬 **镜头检测**：识别视频中的场景切换点
            - 🏷️ **基础标签**：识别视频中的物体、场景、活动
            - 📍 **对象跟踪**：跟踪特定物体的移动轨迹
            - ✂️ **自动切分**：基于镜头检测结果切分视频片段
            
            💡 切分后的片段将进入**智能标签工厂**进行深度标签分析
            """)
            
            # 操作按钮
            buttons = render_action_buttons("video_analysis")
            
            if buttons["start_analysis"]:
                self._execute_video_analysis(
                    uploaded_video=uploaded_video,
                    use_sample_video=use_sample_video,
                    features=analysis_features
                )
    
    def _render_intelligent_labeling_tab(self) -> None:
        """渲染智能标签工厂标签页"""
        st.header("🏷️ 智能标签工厂")
        
        st.info("💡 **智能标签工厂**专注于对已切分的视频片段进行AI标签分析，使用轻量化模型组合提供高效标注。")
        
        # 视频选择
        selected_video_id, segment_files = render_video_selector("intelligent_labeling")
        
        if selected_video_id and segment_files:
            # 批量分析设置
            batch_settings = render_batch_analysis_settings()
            
            # 分析策略选择 - 重新设计更清晰的说明
            st.markdown("### 🎯 分析策略选择")
            
            strategy_options = {
                "intelligent_strategy": {
                    "label": "🧠 智能策略 (推荐)",
                    "description": "Qwen视觉分析 + DeepSeek智能兜底，自动处理空标签情况"
                },
                "qwen_only": {
                    "label": "🔍 仅Qwen分析", 
                    "description": "仅使用Qwen模型进行视觉理解分析，速度快"
                },
                "google_cloud_only": {
                    "label": "☁️ 仅Google Cloud",
                    "description": "使用Google Cloud Video Intelligence，需要额外费用"
                },
                "comparison_analysis": {
                    "label": "🆚 对比分析",
                    "description": "多模型同时分析对比，用于效果评估（开发中）"
                }
            }
            
            strategy = st.selectbox(
                "选择分析策略",
                options=list(strategy_options.keys()),
                format_func=lambda x: strategy_options[x]["label"],
                key="assembly_strategy_selector"
            )
            
            # 显示策略说明
            st.info(f"📋 **策略说明**: {strategy_options[strategy]['description']}")
            
            # 策略特定的设置
            if strategy == "intelligent_strategy":
                st.markdown("#### ⚙️ 智能策略设置")
                col1, col2 = st.columns(2)
                with col1:
                    st.metric("主分析模型", "Qwen")
                with col2:
                    st.metric("兜底模型", "DeepSeek")
                    
            elif strategy == "google_cloud_only":
                st.warning("⚠️ 注意：Google Cloud Video Intelligence会产生API调用费用")
            
            # 操作按钮
            buttons = render_action_buttons("intelligent_labeling")
            
            if buttons["start_analysis"]:
                self._execute_intelligent_labeling(
                    video_id=selected_video_id,
                    segment_files=segment_files,
                    strategy=strategy,
                    batch_settings=batch_settings,
                    model_selection={}  # 不再使用混淆的model_selection
                )
            
            # 显示历史结果
            if st.session_state.analysis_results.get(selected_video_id):
                st.markdown("---")
                st.markdown("### 📊 分析结果")
                render_analysis_results_display(
                    st.session_state.analysis_results[selected_video_id],
                    "intelligent_labeling"
                )
    
    def _render_scene_clustering_tab(self) -> None:
        """渲染场景聚合标签页"""
        st.header("🧠 场景聚合")
        
        st.info("场景聚合功能将相似的视频片段进行智能分组，生成更连贯的场景片段")
        
        # 视频选择
        selected_video_id, segment_files = render_video_selector("scene_clustering")
        
        if selected_video_id and segment_files:
            # 聚类设置
            clustering_settings = render_clustering_settings()
            
            # 操作按钮
            buttons = render_action_buttons("scene_clustering")
            
            if buttons["start_analysis"]:
                self._execute_scene_clustering(
                    video_id=selected_video_id,
                    segment_files=segment_files,
                    clustering_settings=clustering_settings
                )
    
    def _render_settings_tab(self) -> None:
        """渲染设置标签页"""
        st.header("⚙️ 设置")
        
        # 依赖检查
        st.subheader("🔍 依赖检查")
        
        if st.button("检查所有依赖", key="assembly_check_dependencies"):
            dependencies = validate_analysis_dependencies()
            
            for dep_name, status in dependencies.items():
                if status:
                    st.success(f"✅ {dep_name}")
                else:
                    st.error(f"❌ {dep_name}")
        
        # 配置验证
        st.subheader("⚙️ 配置验证")
        
        col1, col2 = st.columns(2)
        
        with col1:
            if st.button("验证组装工厂配置", key="assembly_validate_config"):
                assembly_checks = self.config.validate_assembly_config()
                
                for check_name, status in assembly_checks.items():
                    if status:
                        st.success(f"✅ {check_name}")
                    else:
                        st.error(f"❌ {check_name}")
        
        with col2:
            if st.button("验证Prompt配置", key="assembly_validate_prompt_config"):
                try:
                    from streamlit_app.utils.keyword_config import validate_config, get_config_summary
                    
                    # 配置完整性验证
                    validation_results = validate_config()
                    
                    st.markdown("#### 🔍 配置完整性检查")
                    for check_name, status in validation_results.items():
                        if status:
                            st.success(f"✅ {check_name}")
                        else:
                            st.error(f"❌ {check_name}")
                    
                    # 配置摘要
                    st.markdown("#### 📊 配置摘要")
                    summary = get_config_summary()
                    
                    col1, col2 = st.columns(2)
                    for i, (key, value) in enumerate(summary.items()):
                        if i % 2 == 0:
                            with col1:
                                st.metric(key, value)
                        else:
                            with col2:
                                st.metric(key, value)
                
                except Exception as e:
                    st.error(f"❌ Prompt配置验证失败: {e}")
        
        # 日志设置
        st.subheader("📊 日志设置")
        
        current_level = self.logger.level
        log_levels = {
            "DEBUG": logging.DEBUG,
            "INFO": logging.INFO,
            "WARNING": logging.WARNING,
            "ERROR": logging.ERROR
        }
        
        selected_level = st.selectbox(
            "日志级别",
            options=list(log_levels.keys()),
            index=list(log_levels.values()).index(current_level),
            key="assembly_log_level_selector"
        )
        
        if st.button("应用日志级别", key="assembly_apply_log_level"):
            self.logger.setLevel(log_levels[selected_level])
            st.success(f"✅ 日志级别已设置为: {selected_level}")
    
    def _execute_video_analysis(
        self,
        uploaded_video: Any,
        use_sample_video: bool,
        features: Dict[str, bool]
    ) -> None:
        """执行视频分析"""
        try:
            # 准备分析参数
            feature_list = [key for key, value in features.items() if value and key != "auto_cleanup"]
            
            if not feature_list:
                st.warning("⚠️ 请至少选择一个分析功能！")
                return
            
            # 创建进度容器
            progress_container = st.container()
            result_container = st.container()
            
            with progress_container:
                progress_bar = st.progress(0)
                status_text = st.empty()
            
            def progress_callback(progress, message):
                progress_bar.progress(progress / 100.0 if progress <= 1 else progress)
                status_text.text(message)
            
            # 执行分析
            if use_sample_video:
                video_uri = "gs://cloud-samples-data/video/cat.mp4"
                st.info("📡 使用云端示例视频进行分析")
                
                analysis_result = analyze_video_with_google_cloud(
                    video_uri=video_uri,
                    features=feature_list,
                    auto_cleanup=False,
                    progress_callback=progress_callback
                )
                
                current_video_id = "google_sample_cat"
                current_video_path = None
            else:
                # 保存上传的视频
                temp_dir = Path("data/temp/assembly_factory")
                temp_dir.mkdir(parents=True, exist_ok=True)
                
                video_filename = uploaded_video.name
                video_path = temp_dir / video_filename
                
                with open(video_path, "wb") as f:
                    f.write(uploaded_video.read())
                
                current_video_path = str(video_path)
                current_video_id = Path(video_filename).stem
                
                st.info(f"📊 正在分析 {len(feature_list)} 个功能，视频大小: {uploaded_video.size/(1024*1024):.1f}MB")
                
                analysis_result = analyze_video_with_google_cloud(
                    video_path=current_video_path,
                    features=feature_list,
                    auto_cleanup=features.get("auto_cleanup", True),
                    progress_callback=progress_callback
                )
            
            # 显示结果
            with result_container:
                if analysis_result.get("success"):
                    st.success("✅ 视频分析完成！")
                    
                    # 保存到会话状态
                    st.session_state.current_video_id = current_video_id
                    st.session_state.current_video_path = current_video_path
                    st.session_state.analysis_results[current_video_id] = analysis_result
                    
                    # 显示结果详情
                    render_analysis_results_display(analysis_result, "video_analysis")
                    
                    # 提供切分选项
                    if "shot_detection" in feature_list and st.button("🔪 创建视频片段", key="assembly_create_segments"):
                        self._create_segments_from_analysis(
                            analysis_result, current_video_path, current_video_id
                        )
                else:
                    st.error(f"❌ 分析失败: {analysis_result.get('error', '未知错误')}")
                    
        except Exception as e:
            self.logger.error(f"视频分析失败: {e}")
            render_error_display(e, "视频分析")
    
    def _execute_intelligent_labeling(
        self,
        video_id: str,
        segment_files: List[Path],
        strategy: str,
        batch_settings: Dict[str, Any],
        model_selection: Dict[str, bool]
    ) -> None:
        """执行智能标签分析"""
        try:
            # 创建进度容器
            progress_container = st.container()
            result_container = st.container()
            
            with progress_container:
                st.info(f"🚀 开始{strategy}分析，共{len(segment_files)}个片段")
                progress_bar = st.progress(0)
                status_text = st.empty()
            
            def progress_callback(message):
                status_text.text(message)
            
            # 根据策略执行分析 - 🚀 使用优化版本
            if strategy == "intelligent_strategy":
                # 使用高效分析器，智能策略
                analysis_result = analyze_segments_with_high_efficiency(
                    segment_files=segment_files,
                    video_id=video_id,
                    strategy="intelligent",
                    max_workers=batch_settings.get("max_workers", 3),
                    progress_callback=progress_callback
                )
                
                if analysis_result.get("success"):
                    results = analysis_result["results"]
                    efficiency_report = analysis_result["efficiency_report"]
                    
                    # 显示效率报告
                    st.info(f"⚡ **效率报告**: 总计 {efficiency_report['total_segments']} 个片段，"
                           f"缓存命中率 {efficiency_report['cache_hit_rate']}，"
                           f"总用时 {efficiency_report['total_time']}，"
                           f"效率分数 {efficiency_report['efficiency_score']:.1f}/100")
                else:
                    results = []
                    st.error("🚫 智能分析失败")
                    
            elif strategy == "qwen_only":
                # 使用高效分析器，仅Qwen策略
                analysis_result = analyze_segments_with_high_efficiency(
                    segment_files=segment_files,
                    video_id=video_id,
                    strategy="qwen_only",
                    max_workers=batch_settings.get("max_workers", 3),
                    progress_callback=progress_callback
                )
                
                if analysis_result.get("success"):
                    results = analysis_result["results"]
                    efficiency_report = analysis_result["efficiency_report"]
                    
                    # 显示效率报告
                    st.info(f"⚡ **效率报告**: 总计 {efficiency_report['total_segments']} 个片段，"
                           f"缓存命中率 {efficiency_report['cache_hit_rate']}，"
                           f"总用时 {efficiency_report['total_time']}，"
                           f"效率分数 {efficiency_report['efficiency_score']:.1f}/100")
                else:
                    results = []
                    st.error("🚫 Qwen分析失败")
            else:
                st.warning(f"⚠️ 策略 {strategy} 暂未实现")
                return
            
            progress_bar.progress(1.0)
            
            # 显示结果
            with result_container:
                if results:
                    st.success(f"✅ 智能标签分析完成！成功分析 {len(results)} 个片段")
                    
                    # 保存JSON结果文件
                    try:
                        # 保存到原选中目录
                        config = FactoryConfig.get_assembly_config()
                        video_pool_path = Path(config["default_video_pool_path"])
                        source_video_dir = video_pool_path / video_id
                        
                        # 生成带时间戳的文件名
                        from datetime import datetime
                        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                        json_filename = f"{video_id}_analysis_{strategy}_{timestamp}.json"
                        
                        # 构建JSON数据
                        json_data = {
                            "video_id": video_id,
                            "analysis_strategy": strategy,
                            "timestamp": timestamp,
                            "batch_settings": batch_settings,
                            "total_segments": len(results),
                            "segments": results
                        }
                        
                        # 保存到原始目录
                        source_json_path = source_video_dir / json_filename
                        source_video_dir.mkdir(parents=True, exist_ok=True)
                        
                        with open(source_json_path, 'w', encoding='utf-8') as f:
                            import json
                            json.dump(json_data, f, ensure_ascii=False, indent=2)
                        
                        st.info(f"📄 **JSON文件已保存**: `{source_json_path}`")
                        
                        # 自动复制到video_pool目录
                        from streamlit_app.utils.path_utils import get_video_pool_path
                        video_pool_dir = get_video_pool_path()
                        video_pool_dir.mkdir(parents=True, exist_ok=True)
                        
                        import shutil
                        dest_json_path = video_pool_dir / json_filename
                        shutil.copy2(source_json_path, dest_json_path)
                        
                        st.success(f"✅ **自动复制到混剪工厂**: `{dest_json_path}`")
                        st.info("💡 现在可以前往混剪工厂使用这些分析结果进行视频合成！")
                        
                    except Exception as e:
                        st.error(f"❌ 保存JSON文件失败: {e}")
                        self.logger.error(f"保存JSON文件失败: {e}")
                    
                    # 保存结果到session state
                    st.session_state.analysis_results[video_id] = results
                    
                    # 显示结果
                    render_analysis_results_display(results, "intelligent_labeling")
                else:
                    st.warning("⚠️ 未获得有效的分析结果")
                    
        except Exception as e:
            self.logger.error(f"智能标签分析失败: {e}")
            render_error_display(e, "智能标签分析")
    
    def _execute_scene_clustering(
        self,
        video_id: str,
        segment_files: List[Path],
        clustering_settings: Dict[str, float]
    ) -> None:
        """执行场景聚类"""
        try:
            st.info("🧠 场景聚类功能开发中...")
            
            # 这里可以实现实际的聚类逻辑
            # 目前显示占位符
            st.markdown("""
            ### 🎯 场景聚类计划
            
            **聚类参数**:
            - 相似度阈值: {similarity_threshold}
            - 最小场景时长: {min_scene_duration}秒
            - 最大场景数: {max_scenes}
            
            **聚类流程**:
            1. 提取视频片段特征
            2. 计算片段间相似度
            3. 基于相似度进行聚类
            4. 生成优化的场景片段
            """.format(**clustering_settings))
            
        except Exception as e:
            self.logger.error(f"场景聚类失败: {e}")
            render_error_display(e, "场景聚类")
    
    def _create_segments_from_analysis(
        self,
        analysis_result: Dict[str, Any],
        video_path: str,
        video_id: str
    ) -> None:
        """从分析结果创建视频片段"""
        try:
            if not video_path:
                st.warning("⚠️ 无法创建片段：视频路径不可用")
                return
            
            # 提取镜头信息
            result = analysis_result.get("result")
            if not result or not hasattr(result, "annotation_results"):
                st.warning("⚠️ 无有效的镜头检测结果")
                return
            
            annotation = result.annotation_results[0]
            
            # 提取镜头变化点
            segments_data = []
            if hasattr(annotation, "shot_annotations"):
                for i, shot in enumerate(annotation.shot_annotations):
                    start_time = shot.start_time_offset.total_seconds()
                    end_time = shot.end_time_offset.total_seconds()
                    
                    segments_data.append({
                        "start_time_seconds": start_time,
                        "end_time_seconds": end_time,
                        "shot_index": i
                    })
            
            if not segments_data:
                st.warning("⚠️ 未检测到镜头变化点")
                return
            
            # 创建进度显示
            progress_container = st.container()
            with progress_container:
                progress_bar = st.progress(0)
                status_text = st.empty()
            
            def progress_callback(message):
                status_text.text(message)
            
            # 创建片段
            created_segments = create_video_segments(
                video_path=video_path,
                segments_data=segments_data,
                video_id=video_id,
                is_clustered=False,
                progress_callback=progress_callback
            )
            
            progress_bar.progress(1.0)
            
            if created_segments:
                st.success(f"✅ 成功创建 {len(created_segments)} 个视频片段！")
                st.info(f"📁 片段保存位置: data/output/google_video/{video_id}/")
                
                # 显示前几个片段名
                if len(created_segments) <= 5:
                    for segment in created_segments:
                        st.text(f"• {Path(segment).name}")
                else:
                    for segment in created_segments[:3]:
                        st.text(f"• {Path(segment).name}")
                    st.text(f"... 还有 {len(created_segments) - 3} 个片段")
            else:
                st.warning("⚠️ 未能创建视频片段")
                
        except Exception as e:
            self.logger.error(f"创建视频片段失败: {e}")
            render_error_display(e, "创建视频片段")

    def _render_prompt_configuration_tab(self) -> None:
        """渲染Prompt配置标签页"""
        st.header("🤖 Prompt配置管理")
        
        st.markdown("""
        💡 **Prompt配置中心**：统一管理Qwen和DeepSeek模型的提示词配置
        
        **🎯 功能特点**：
        - 📊 **关键词配置**：管理所有AI模型使用的基础词汇
        - 👁️ **Qwen视觉Prompt**：配置视频画面分析的提示词模板  
        - 🧠 **DeepSeek语音Prompt**：配置音频转录分析的提示词模板
        - 🔄 **实时生效**：修改配置后即时应用到所有分析任务
        
        **🔧 最佳实践**：
        - 所有配置统一存储在 `config/keywords.yml` 文件中
        - 遵循单一数据源原则，避免配置分散
        - 支持热重载，无需重启应用
        """)
        
        # 渲染Prompt配置界面
        render_prompt_configuration()


def main():
    """主函数"""
    # 设置页面配置
    config = FactoryConfig.get_assembly_config()
    st.set_page_config(
        page_title=config["app_name"],
        page_icon=config["page_icon"],
        layout=config["layout"]
    )
    
    # 创建并运行组装工厂
    factory = AssemblyFactory()
    factory.render_main_page()


if __name__ == "__main__":
    main() 