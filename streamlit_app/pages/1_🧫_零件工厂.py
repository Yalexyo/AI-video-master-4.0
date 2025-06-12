"""
🧫 零件工厂 - 重构版本
标杆视频转字幕工厂

采用模块化设计，符合Streamlit最佳实践：
- 配置集中管理
- UI组件化
- 业务逻辑独立
- 错误处理完善
"""

import streamlit as st
import logging
import sys
from pathlib import Path
from typing import Dict, Any

# 添加项目路径
sys.path.append(str(Path(__file__).parent.parent.parent))

# 导入配置和模块
from config.factory_config import FactoryConfig
from modules.factory.parts_components import (
    render_video_upload_section,
    render_video_info,
    render_output_settings,
    render_advanced_settings,
    render_conversion_button,
    render_conversion_result,
    render_error_display,
    render_dependencies_check
)
from utils.factory.transcription_utils import (
    convert_video_to_srt,
    validate_transcription_dependencies
)


class PartsFactory:
    """零件工厂主类 - 封装所有核心功能"""
    
    def __init__(self):
        self.config = FactoryConfig()
        self.logger = self._setup_logging()
        self.parts_config = self.config.get_parts_config()
    
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
    
    def render_main_page(self) -> None:
        """渲染主页面"""
        # 页面标题和说明
        st.title("🧫 零件工厂")
        
        st.markdown("""
        🎯 **零件工厂** - 标杆视频转字幕专用工厂
        
        将标杆视频快速转换为SRT字幕文件，并智能分析目标人群，为后续的视频分析和制作提供基础素材。
        
        **🔧 核心功能**:
        - 📤 标杆视频上传
        - 🎤 自动语音识别 (ASR)
        - 📝 生成标准SRT字幕文件
        - 🎯 智能目标人群分析 ⭐**新功能**
        - 💾 自动保存到指定目录
        
        **📋 支持格式**: MP4, AVI, MOV, WMV, MKV 等常见视频格式
        """)
        
        st.markdown("---")
        
        # 主要工作流
        self._render_main_workflow()
    
    def _render_main_workflow(self) -> None:
        """渲染主要工作流程"""
        
        # 系统依赖检查
        render_dependencies_check()
        
        st.markdown("---")
        
        # 步骤1: 视频上传
        uploaded_video = render_video_upload_section()
        
        if uploaded_video:
            # 步骤2: 视频信息显示
            video_info = render_video_info(uploaded_video)
            
            # 步骤3: 输出设置（包含人群分析选项）
            output_settings = render_output_settings()
            
            # 步骤4: 高级设置
            advanced_settings = render_advanced_settings()
            
            # 步骤5: 开始转换
            if render_conversion_button():
                self._execute_conversion(
                    uploaded_video=uploaded_video,
                    video_info=video_info,
                    output_settings=output_settings,
                    advanced_settings=advanced_settings
                )
        else:
            st.info("👆 请先上传标杆视频文件以开始处理")
    
    def _execute_conversion(
        self,
        uploaded_video: Any,
        video_info: Dict[str, Any],
        output_settings: Dict[str, Any],
        advanced_settings: Dict[str, Any]
    ) -> None:
        """执行视频转换"""
        try:
            # 显示进度
            progress_container = st.container()
            status_container = st.container()
            result_container = st.container()
            
            with progress_container:
                progress_bar = st.progress(0)
            
            with status_container:
                status_text = st.empty()
            
            # 进度更新
            self._update_progress(progress_bar, status_text, 0.1, "📁 正在保存视频文件...")
            
            # 获取人群分析设置
            analyze_audience = output_settings.get("analyze_audience", True)
            
            if analyze_audience:
                self._update_progress(progress_bar, status_text, 0.3, "🎤 正在进行语音转录...")
            else:
                self._update_progress(progress_bar, status_text, 0.3, "🎤 正在进行语音转录（不含人群分析）...")
            
            # 执行转换
            result = convert_video_to_srt(
                uploaded_video=uploaded_video,
                video_id=video_info["video_id"],
                output_dir=output_settings["output_dir"],
                hotword_mode=advanced_settings["hotword_mode"],
                hotwords_text=advanced_settings["hotwords_text"],
                preset_hotword_id=advanced_settings["preset_hotword_id"],
                use_hotwords=advanced_settings["use_hotwords"],
                cleanup_temp=advanced_settings["cleanup_temp"],
                hotword_id=self.parts_config["default_hotword_id"],
                analyze_target_audience=analyze_audience  # 🎯 传递人群分析参数
            )
            
            # 根据是否进行人群分析显示不同进度
            if analyze_audience and result.get("success"):
                self._update_progress(progress_bar, status_text, 0.8, "🎯 正在分析目标人群...")
                # 短暂延迟模拟分析过程
                import time
                time.sleep(1)
            
            # 更新进度
            self._update_progress(progress_bar, status_text, 1.0, "✅ 转换完成！")
            
            # 显示结果
            with result_container:
                render_conversion_result(result)
                
                # 🎯 如果进行了人群分析，显示工厂流程建议
                if analyze_audience and result.get("target_audience_analysis", {}).get("success"):
                    self._render_workflow_suggestions(result)
                
        except Exception as e:
            self.logger.error(f"转换过程中出错: {e}")
            render_error_display(e)
    
    def _render_workflow_suggestions(self, result: Dict[str, Any]) -> None:
        """
        🎯 渲染工厂流程建议
        
        Args:
            result: 包含人群分析结果的字典
        """
        st.markdown("---")
        st.markdown("### 🏭 **下一步工厂流程建议**")
        
        target_audience = result.get("target_audience_analysis", {}).get("target_audience", "")
        
        col1, col2 = st.columns(2)
        
        with col1:
            st.markdown("#### 🧱 **组装工厂**")
            st.info("""
            **建议操作**：
            1. 上传**素材视频**（非标杆视频）
            2. 进行视觉分析和智能切分
            3. 生成视频片段标签
            
            ⚠️ **注意**：组装工厂专注于视觉分析，不进行语音转录
            """)
        
        with col2:
            st.markdown("#### 🧪 **混剪工厂**")
            st.success(f"""
            **基于人群分析结果**：
            - 🎯 目标人群：**{target_audience}**
            - 📋 使用相应的营销策略模板
            - 🎬 选择匹配的视频片段进行合成
            
            ✅ **已具备人群分析基础**，可直接使用
            """)
        
        # 流程图提示
        st.markdown("#### 🔄 **优化后的工厂流程**")
        st.code("""
🧫 零件工厂：标杆视频 → SRT字幕 + 人群分析 ✅ 
    ↓
🧱 组装工厂：素材视频 → 视觉分析 + 智能切分（无需转录）
    ↓
🧪 混剪工厂：片段映射 + 视频合成（基于人群分析）
        """)
    
    def _update_progress(self, progress_bar, status_text, progress: float, message: str) -> None:
        """更新进度显示"""
        progress_bar.progress(progress)
        status_text.text(message)
    
    def render_debug_tools(self) -> None:
        """渲染调试工具"""
        st.header("🔧 调试工具")
        
        # 配置验证
        st.subheader("⚙️ 配置验证")
        
        if st.button("🔍 验证配置"):
            # 验证基本配置
            parts_checks = self.config.validate_parts_config()
            
            for check_name, status in parts_checks.items():
                if status:
                    st.success(f"✅ {check_name}")
                else:
                    st.error(f"❌ {check_name}")
            
            # 验证转录依赖
            st.markdown("**转录依赖检查:**")
            transcription_checks = validate_transcription_dependencies()
            
            for check_name, status in transcription_checks.items():
                if status:
                    st.success(f"✅ {check_name}")
                else:
                    st.warning(f"⚠️ {check_name}")
        
        # 日志级别设置
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
            index=list(log_levels.values()).index(current_level)
        )
        
        if st.button("应用日志级别"):
            self.logger.setLevel(log_levels[selected_level])
            st.success(f"✅ 日志级别已设置为: {selected_level}")


def main():
    """主函数"""
    # 设置页面配置
    st.set_page_config(
        page_title="🧫 零件工厂",
        page_icon="🧫",
        layout="wide",
        initial_sidebar_state="expanded"
    )
    
    # 创建并运行工厂
    factory = PartsFactory()
    factory.render_main_page()


if __name__ == "__main__":
    main() 