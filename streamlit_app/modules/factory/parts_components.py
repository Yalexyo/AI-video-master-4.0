"""
零件工厂UI组件模块
提取和封装零件工厂的用户界面组件
"""

import streamlit as st
import os
import subprocess
from typing import Dict, Any, Optional
from pathlib import Path
import logging

# 导入配置
from streamlit_app.config.factory_config import FactoryConfig
from streamlit_app.utils.factory.transcription_utils import validate_transcription_dependencies


logger = logging.getLogger(__name__)


@st.cache_data(ttl=3600)  # 缓存1小时
def get_preset_vocabulary_info(preset_hotword_id: str) -> Dict[str, Any]:
    """
    获取预设词汇表信息（带缓存）
    
    Args:
        preset_hotword_id: 预设热词ID
        
    Returns:
        词汇表信息字典
    """
    try:
        from streamlit_app.modules.ai_analyzers.dashscope_audio_analyzer import DashScopeAudioAnalyzer
        
        analyzer = DashScopeAudioAnalyzer()
        if analyzer.is_available():
            return analyzer.get_vocabulary_content(preset_hotword_id)
        else:
            return {
                "success": False,
                "error": "DashScope API不可用",
                "content": []
            }
    except Exception as e:
        return {
            "success": False,
            "error": str(e),
            "content": []
        }


def render_video_upload_section() -> Optional[Any]:
    """渲染视频上传区域
    
    Returns:
        上传的视频文件对象或None
    """
    st.markdown("### 📤 上传标杆视频")
    
    config = FactoryConfig.get_parts_config()
    
    uploaded_video = st.file_uploader(
        "选择标杆视频文件",
        type=config["supported_video_formats"],
        help="上传标杆视频，系统将自动提取语音并生成SRT字幕文件"
    )
    
    return uploaded_video


def render_video_info(uploaded_video: Any) -> Dict[str, Any]:
    """渲染视频信息
    
    Args:
        uploaded_video: 上传的视频文件对象
        
    Returns:
        Dict: 视频信息字典
    """
    if not uploaded_video:
        return {}
    
    # 提取视频信息
    video_info = {
        "filename": uploaded_video.name,
        "video_id": Path(uploaded_video.name).stem,
        "size_mb": uploaded_video.size / (1024 * 1024),
        "type": uploaded_video.type
    }
    
    st.markdown("### 📊 视频信息")
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.metric("文件名", video_info["video_id"])
    
    with col2:
        st.metric("文件大小", f"{video_info['size_mb']:.1f} MB")
    
    with col3:
        st.metric("文件类型", video_info["type"])
    
    return video_info


def render_output_settings() -> Dict[str, Any]:
    """渲染输出设置
    
    Returns:
        Dict: 输出设置字典
    """
    st.markdown("### ⚙️ 输出设置")
    
    config = FactoryConfig.get_parts_config()
    
    col1, col2 = st.columns(2)
    
    with col1:
        output_dir = st.text_input(
            "输出目录",
            value=config["default_output_dir"],
            help="SRT字幕文件的保存目录"
        )
    
    with col2:
        # 🎯 新增：人群分析选项
        analyze_audience = st.checkbox(
            "🎯 启用人群分析",
            value=True,
            help="对转录文本进行目标人群分析，为后续营销策略提供指导"
        )
    
    return {
        "output_dir": output_dir,
        "analyze_audience": analyze_audience
    }


def render_advanced_settings() -> Dict[str, Any]:
    """渲染高级设置
    
    Returns:
        Dict: 高级设置字典
    """
    st.markdown("### 🔧 高级设置")
    
    config = FactoryConfig.get_parts_config()
    
    # 清理临时文件设置
    cleanup_temp = st.checkbox(
        "清理临时文件",
        value=config["cleanup_temp_default"],
        help="处理完成后自动清理临时文件"
    )
    
    # 热词配置 - 互斥选择
    st.markdown("#### 🎯 热词配置")
    
    hotword_mode = st.radio(
        "选择热词模式",
        options=["use_preset", "use_custom", "no_hotwords"],
        format_func=lambda x: {
            "use_preset": "🏭 使用预设热词ID（推荐，已针对母婴行业优化）",
            "use_custom": "✏️ 使用自定义热词",
            "no_hotwords": "🚫 不使用热词优化"
        }[x],
        index=0,  # 默认选择预设热词
        help="选择热词优化策略以提高语音识别准确率"
    )
    
    # 根据选择显示相应的配置选项
    hotwords_text = ""
    preset_hotword_id = ""
    
    if hotword_mode == "use_preset":
        preset_hotword_id = "vocab-aivideo-4d73bdb1b5ef496d94f5104a957c012b"
        
        # 🔍 动态获取热词内容
        with st.spinner("正在获取预设热词内容..."):
            vocab_info = get_preset_vocabulary_info(preset_hotword_id)
            
            if vocab_info.get("success"):
                st.success(f"🔧 **预设热词ID**: `{preset_hotword_id}`")
                
                # 显示词汇表基本信息
                col1, col2, col3 = st.columns(3)
                with col1:
                    st.metric("词汇表名称", vocab_info.get("name", "未知"))
                with col2:
                    st.metric("词汇数量", vocab_info.get("word_count", 0))
                with col3:
                    st.metric("状态", vocab_info.get("status", "未知"))
                
                # 显示描述
                if vocab_info.get("description"):
                    st.info(f"📝 **描述**: {vocab_info['description']}")
                
                # 显示部分热词内容
                content = vocab_info.get("content", [])
                if content:
                    # 限制显示数量，避免界面过长
                    display_count = min(20, len(content))
                    displayed_words = content[:display_count]
                    
                    st.markdown(f"📋 **热词内容预览** (显示前{display_count}个，共{len(content)}个)：")
                    
                    # 按行显示热词，每行最多8个
                    words_per_row = 8
                    for i in range(0, len(displayed_words), words_per_row):
                        row_words = displayed_words[i:i+words_per_row]
                        # 提取热词文本（适配字典格式）
                        word_texts = []
                        for word in row_words:
                            if isinstance(word, dict):
                                word_text = word.get('text', str(word))
                            else:
                                word_text = str(word)
                            word_texts.append(word_text)
                        st.code(" | ".join(word_texts))
                    
                    if len(content) > display_count:
                        st.caption(f"...还有{len(content) - display_count}个热词")
                        
                        # 添加展开按钮显示更多热词
                        if st.button("🔍 查看完整热词列表", key="expand_hotwords"):
                            st.markdown("📋 **完整热词列表**：")
                            # 分组显示所有热词
                            all_words_per_row = 10
                            for i in range(0, len(content), all_words_per_row):
                                row_words = content[i:i+all_words_per_row]
                                # 提取热词文本（适配字典格式）
                                word_texts = []
                                for word in row_words:
                                    if isinstance(word, dict):
                                        word_text = word.get('text', str(word))
                                    else:
                                        word_text = str(word)
                                    word_texts.append(word_text)
                                st.code(" | ".join(word_texts))
                else:
                    st.warning("⚠️ 未获取到热词内容")
            else:
                # 获取失败时显示基本信息
                error_msg = vocab_info.get('error', '未知错误')
                if "API不可用" in error_msg:
                    st.info(f"🔧 **预设热词ID**: `{preset_hotword_id}`")
                    st.caption("DashScope API暂不可用，无法获取热词详情，但仍可使用该ID进行语音识别优化")
                else:
                    st.warning(f"⚠️ 无法获取热词详情: {error_msg}")
                    st.info(f"🔧 **预设热词ID**: `{preset_hotword_id}`")
                    st.caption("将使用该ID进行语音识别优化")
        
    elif hotword_mode == "use_custom":
        st.markdown("✏️ **自定义热词设置**")
        hotwords_text = st.text_area(
            "输入自定义热词",
            value=", ".join(config["hotwords"]),
            help="每行一个热词，或用逗号分隔。这些热词将用于创建专属词汇表。",
            height=120,
            placeholder="例如：启赋蕴淳A2, DHA, 低聚糖HMO, 自愈力, OPN蛋白"
        )
        
        if hotwords_text:
            # 解析并预览热词
            hotwords_list = [word.strip() for word in hotwords_text.replace('\n', ',').split(',') if word.strip()]
            if hotwords_list:
                st.markdown(f"📝 **预览热词** ({len(hotwords_list)} 个)：")
                st.code(", ".join(hotwords_list))
        
    else:  # no_hotwords
        st.warning("⚠️ **注意**：不使用热词优化可能导致专业术语识别准确率降低")
    
    return {
        "hotword_mode": hotword_mode,
        "cleanup_temp": cleanup_temp,
        "hotwords_text": hotwords_text,
        "preset_hotword_id": preset_hotword_id,
        # 为了向后兼容，保留原有字段
        "use_hotwords": hotword_mode != "no_hotwords"
    }


def render_conversion_button() -> bool:
    """渲染转换按钮
    
    Returns:
        bool: 是否点击了转换按钮
    """
    st.markdown("### 🚀 开始转换")
    
    return st.button(
        "🎤 开始语音转录",
        type="primary",
        use_container_width=True,
        help="开始将视频转换为SRT字幕文件"
    )


def render_conversion_progress(progress: float, status: str) -> None:
    """渲染转换进度
    
    Args:
        progress: 进度值 (0.0 - 1.0)
        status: 状态文本
    """
    progress_bar = st.progress(progress)
    status_text = st.text(status)
    
    return progress_bar, status_text


def render_conversion_result(result_data: Dict[str, Any]) -> None:
    """渲染转换结果
    
    Args:
        result_data: 包含转换结果信息的字典
    """
    if result_data.get("success"):
        st.success("🎉 SRT字幕文件已成功生成！")
        
        # 显示文件信息
        srt_path = result_data["srt_path"]
        video_id = result_data["video_id"]
        output_dir = result_data["output_dir"]
        
        if os.path.exists(srt_path):
            srt_file_size = Path(srt_path).stat().st_size
            
            col1, col2, col3 = st.columns(3)
            with col1:
                st.metric("SRT文件", f"{video_id}.srt")
            with col2:
                st.metric("文件大小", f"{srt_file_size / 1024:.1f} KB")
            with col3:
                st.metric("保存位置", output_dir)
            
            # 🎯 显示人群分析结果
            _render_audience_analysis_result(result_data)
            
            # 预览SRT内容
            _render_srt_preview(srt_path)
            
            # 操作按钮
            _render_result_actions(srt_path, output_dir, video_id)
    
    else:
        # 转录失败处理
        error_msg = result_data.get('error', '未知错误')
        error_type = result_data.get('error_type', 'unknown')
        hotword_mode = result_data.get('hotword_mode', 'unknown')
        suggestions = result_data.get('suggestions', [])
        
        if error_type == 'no_timestamps':
            # 专门处理时间戳缺失错误
            st.error("❌ **SRT字幕文件生成失败：时间戳信息缺失**")
            
            # 详细错误说明
            with st.expander("🔍 **问题详情**", expanded=True):
                st.markdown(f"""
                **错误原因：** {error_msg}
                
                **使用的热词模式：** {hotword_mode}
                
                **问题分析：**
                - 转录服务未返回精确的时间戳信息
                - 无法生成与语音同步的SRT字幕文件
                - 系统已停用低精度的兜底方案
                """)
            
            # 解决建议
            st.markdown("### 💡 **解决建议**")
            col1, col2 = st.columns(2)
            
            with col1:
                st.markdown("""
                **🔧 API配置检查：**
                - 确认 DASHSCOPE_API_KEY 已正确设置
                - 验证API Key有录音文件识别权限
                - 检查网络连接是否正常
                """)
                
            with col2:
                st.markdown("""
                **🎵 音频文件检查：**
                - 确认音频清晰度良好
                - 尝试较短的音频片段
                - 检查音频格式是否支持
                """)
                
        elif error_type == 'import_error':
            # SDK导入错误
            st.error("❌ **DashScope SDK导入失败**")
            
            with st.expander("🔍 **问题详情**", expanded=True):
                st.markdown(f"""
                **错误原因：** {error_msg}
                
                **问题分析：**
                - DashScope SDK未正确安装或版本过旧
                - Python环境配置问题
                """)
            
            st.markdown("### 💡 **解决方案**")
            st.code("pip install dashscope --upgrade", language="bash")
            st.info("📌 安装完成后请重启应用")
            
        elif error_type == 'api_error':
            # API调用错误
            status_code = result_data.get('status_code', 'unknown')
            
            st.error(f"❌ **DashScope API调用失败** (状态码: {status_code})")
            
            with st.expander("🔍 **问题详情**", expanded=True):
                st.markdown(f"""
                **错误原因：** {error_msg}
                
                **状态码：** {status_code}
                
                **使用的热词模式：** {hotword_mode}
                """)
            
            # 根据状态码提供具体建议
            st.markdown("### 💡 **解决建议**")
            if str(status_code) == "401":
                st.warning("🔑 **认证失败**：请检查DASHSCOPE_API_KEY是否正确")
            elif str(status_code) == "403":
                st.warning("🚫 **权限不足**：API Key可能没有录音文件识别权限")
            elif str(status_code) == "429":
                st.warning("⏱️ **请求频率过高**：请稍后重试")
            elif str(status_code) == "500":
                st.warning("🔧 **服务器错误**：DashScope服务暂时不可用")
            else:
                st.info("🔍 请检查网络连接和API配置")
                
        elif error_type == 'exception' and suggestions:
            # 通用异常错误，有具体建议
            st.error("❌ **转录过程发生异常**")
            
            with st.expander("🔍 **问题详情**", expanded=True):
                st.markdown(f"""
                **错误原因：** {error_msg}
                
                **使用的热词模式：** {hotword_mode}
                """)
            
            # 显示针对性建议
            st.markdown("### 💡 **解决建议**")
            for i, suggestion in enumerate(suggestions, 1):
                st.markdown(f"{i}. {suggestion}")
        else:
            # 通用错误处理
            st.error("❌ **转录失败**")
            
            with st.expander("🔍 **错误详情**"):
                st.text(error_msg)
                if hotword_mode != 'unknown':
                    st.text(f"热词模式: {hotword_mode}")
        
        # 通用的重试建议
        st.markdown("---")
        st.markdown("### 🔄 **重试建议**")
        
        col1, col2, col3 = st.columns(3)
        
        with col1:
            if st.button("🔄 重新转录", help="使用相同配置重新尝试转录"):
                st.rerun()
        
        with col2:
            if st.button("🎯 切换热词模式", help="尝试不同的热词配置"):
                # 可以触发热词配置的重置
                st.session_state.pop('hotword_mode', None)
                st.rerun()
        
        with col3:
            if st.button("📞 联系支持", help="获取技术支持"):
                st.info("""
                **技术支持渠道：**
                - 📧 提交工单至阿里云控制台
                - 💬 访问DashScope官方文档
                - 🔗 查看GitHub示例代码
                """)


def _render_audience_analysis_result(result_data: Dict[str, Any]) -> None:
    """
    🎯 显示人群分析结果
    
    Args:
        result_data: 包含转换结果的字典
    """
    audience_analysis = result_data.get("target_audience_analysis")
    
    if not audience_analysis:
        return
    
    st.markdown("---")
    st.markdown("### 🎯 **目标人群分析结果**")
    
    if audience_analysis.get("success"):
        target_audience = audience_analysis.get("target_audience", "未识别")
        confidence = audience_analysis.get("confidence", 0.0)
        method = audience_analysis.get("analysis_method", "unknown")
        
        # 主要结果展示
        col1, col2, col3 = st.columns(3)
        
        with col1:
            st.metric(
                "🎯 目标人群", 
                target_audience,
                help="基于视频转录内容智能识别的目标人群"
            )
        
        with col2:
            confidence_percent = f"{confidence * 100:.1f}%"
            confidence_color = "🟢" if confidence > 0.7 else "🟡" if confidence > 0.4 else "🔴"
            st.metric(
                "📊 置信度", 
                f"{confidence_color} {confidence_percent}",
                help="人群识别的可信度"
            )
        
        with col3:
            method_display = {
                "deepseek_api": "🤖 DeepSeek AI",
                "keyword_fallback": "🔤 关键词匹配",
                "default_fallback": "📝 兜底分析"
            }.get(method, method)
            
            st.metric(
                "🔧 分析方法", 
                method_display,
                help="使用的分析方法"
            )
        
        # 详细分析报告
        report = audience_analysis.get("report", {})
        if report:
            st.markdown("#### 📋 **分析详情**")
            
            col1, col2 = st.columns(2)
            
            with col1:
                st.markdown("**📊 转录文本统计**")
                stats = report.get("transcript_stats", {})
                st.text(f"总字符数: {stats.get('total_length', 0)}")
                st.text(f"词汇数量: {stats.get('word_count', 0)}")
                st.text(f"内容质量: {'✅ 有效' if stats.get('has_content') else '❌ 空白'}")
            
            with col2:
                st.markdown("**🎯 营销建议**")
                recommendation = report.get("recommendation", "")
                if recommendation:
                    st.info(recommendation)
                else:
                    st.text("暂无特定建议")
        
        # 成功提示
        st.success("🎯 **人群分析完成！** 结果已保存，可用于后续营销策略制定。")
        
    else:
        # 分析失败处理
        error_msg = audience_analysis.get("error", "未知错误")
        st.warning(f"⚠️ **人群分析失败**: {error_msg}")
        st.info("💡 **建议**: 请检查视频内容是否包含清晰的语音，或稍后重试。")


def _render_srt_preview(srt_path: str) -> None:
    """渲染SRT预览
    
    Args:
        srt_path: SRT文件路径
    """
    st.markdown("### 👀 SRT内容预览")
    
    try:
        with open(srt_path, 'r', encoding='utf-8') as f:
            content = f.read()
            
        # 限制预览长度
        preview_content = content[:1000] + "..." if len(content) > 1000 else content
            
        st.code(preview_content, language="srt")
            
        if len(content) > 1000:
            st.info(f"📄 完整文件包含 {len(content)} 字符，此处仅显示前1000字符")
        
    except Exception as e:
        st.error(f"❌ 无法读取SRT文件: {e}")


def _render_result_actions(srt_path: str, output_dir: str, video_id: str) -> None:
    """渲染结果操作按钮
    
    Args:
        srt_path: SRT文件路径
        output_dir: 输出目录
        video_id: 视频ID
    """
    col1, col2, col3 = st.columns(3)
    
    with col1:
        if st.button("📂 打开文件夹", key="open_output_folder"):
            _open_directory(output_dir)
    
    with col2:
        if st.button("📋 复制路径", key="copy_srt_path"):
            st.code(str(srt_path))
            st.info("✅ 文件路径已显示，可手动复制")
    
    with col3:
        # 下载按钮
        try:
            with open(srt_path, 'r', encoding='utf-8') as f:
                srt_content = f.read()
            
            st.download_button(
                label="💾 下载SRT",
                data=srt_content,
                file_name=f"{video_id}.srt",
                mime="text/plain",
                key="download_srt"
            )
        except Exception as e:
            st.error(f"❌ 准备下载失败: {e}")


def _open_directory(directory_path: str) -> None:
    """在文件管理器中打开目录
    
    Args:
        directory_path: 目录路径
    """
    try:
        import platform
        
        system = platform.system()
        
        if system == "Windows":
            os.startfile(directory_path)
        elif system == "Darwin":  # macOS
            subprocess.run(["open", directory_path])
        else:  # Linux
            subprocess.run(["xdg-open", directory_path])
            
        st.success("✅ 已在文件管理器中打开目录")
        
    except Exception as e:
        st.error(f"❌ 无法打开目录: {e}")
        st.info(f"📁 手动打开路径: {directory_path}")


def render_error_display(error: Exception, context: str = "转换") -> None:
    """渲染错误显示
    
    Args:
        error: 异常对象
        context: 错误上下文
    """
    st.error(f"❌ {context}过程中出错")
    
    with st.expander("🔍 查看错误详情"):
        st.code(str(error))
        
        # 常见问题解决建议
        st.markdown("### 💡 常见问题解决建议")
        
        suggestions = [
            "🔧 检查视频文件是否完整且未损坏",
            "📁 确认有足够的磁盘空间用于临时文件",
            "🎤 验证视频是否包含音频轨道",
            "🔌 检查网络连接（如果使用在线转录服务）",
            "⚙️ 确认所需的依赖软件已正确安装"
        ]
        
        for suggestion in suggestions:
            st.text(suggestion)


def render_dependencies_check() -> None:
    """渲染依赖检查"""
    st.markdown("### 🔍 系统依赖检查")
    
    checks = validate_transcription_dependencies()
    
    all_passed = all(checks.values())
    
    if all_passed:
        st.success("✅ 所有依赖检查通过")
    else:
        st.warning("⚠️ 部分依赖检查未通过")
    
    # 显示详细检查结果
    for check_name, status in checks.items():
        status_icon = "✅" if status else "❌"
        status_text = "正常" if status else "异常"
        
        display_name = {
            "transcribe_core_available": "转录核心模块",
            "deepseek_analyzer_available": "DeepSeek人群分析器",
            "ffmpeg_available": "FFmpeg音频处理"
        }.get(check_name, check_name)
        
        st.text(f"{status_icon} {display_name}: {status_text}")
    
    if not all_passed:
        st.info("💡 **建议**: 请检查相关依赖的安装情况，确保系统正常运行。") 