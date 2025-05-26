#!/usr/bin/env python3
"""
视频场景分段页面
实现视频场景边界检测和手动语义标签匹配功能
"""

import streamlit as st
import os
import sys
import json
import pandas as pd
from pathlib import Path

# 添加项目根目录到路径
ROOT_DIR = Path(__file__).parent.parent.parent
sys.path.append(str(ROOT_DIR))

from src.core.utils.scene_detector import SceneDetector
from src.core.utils.video_processor import VideoProcessor
import logging

# 设置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# 语义类型选项
SEMANTIC_TYPES = [
    "广告开场", "问题陈述", "产品介绍", "产品优势", "用户反馈", 
    "专家背书", "品牌理念", "行动号召", "总结收尾", "其他"
]

def main():
    st.set_page_config(
        page_title="视频场景分段",
        page_icon="🎬",
        layout="wide"
    )
    
    st.title("🎬 视频场景分段")
    st.markdown("---")
    
    # 侧边栏配置
    with st.sidebar:
        st.header("⚙️ 检测配置")
        
        # 场景检测参数
        threshold = st.slider(
            "场景变化阈值", 
            min_value=0.1, 
            max_value=0.8, 
            value=0.3, 
            step=0.05,
            help="阈值越低，检测到的场景变化越多"
        )
        
        min_scene_length = st.slider(
            "最小场景长度(秒)", 
            min_value=0.5, 
            max_value=5.0, 
            value=1.0, 
            step=0.5,
            help="过滤掉太短的场景"
        )
        
        # 添加检测精度设置
        detection_precision = st.selectbox(
            "检测精度",
            ["高精度 (0.1秒)", "超高精度 (0.05秒)", "标准精度 (0.2秒)"],
            index=0,
            help="🎯 高精度: 每0.1秒检测一次，平衡精度和性能\\n⚡ 超高精度: 每0.05秒检测一次，最高精度但较慢\\n📊 标准精度: 每0.2秒检测一次，速度快但精度较低"
        )
        
        # 解析精度设置
        precision_map = {
            "高精度 (0.1秒)": 0.1,
            "超高精度 (0.05秒)": 0.05,
            "标准精度 (0.2秒)": 0.2
        }
        precision_interval = precision_map[detection_precision]
        
        # 显示精度说明
        if detection_precision == "超高精度 (0.05秒)":
            st.warning("⚡ 超高精度模式处理时间较长，适合对精度要求极高的场景")
        elif detection_precision == "高精度 (0.1秒)":
            st.info("🎯 推荐设置，平衡精度和处理速度")
        else:
            st.success("📊 快速模式，适合快速预览和大文件处理")
        
        detection_method = st.selectbox(
            "检测方法",
            ["ffmpeg", "content", "histogram"],
            index=0,
            help="🔥 推荐: ffmpeg (专业级检测，精度高)\n📊 content: 基于内容变化\n🎨 histogram: 基于颜色直方图"
        )
        
        # 添加方法说明
        if detection_method == "ffmpeg":
            st.success("⚡ **FFmpeg专业滤镜**\n- 精度最高\n- 性能优化\n- 专业级算法")
            
            # FFmpeg高级选项
            with st.expander("🔧 FFmpeg高级选项"):
                use_adaptive_threshold = st.checkbox(
                    "自适应阈值", 
                    value=False,
                    help="根据视频内容自动调整检测阈值"
                )
                
                enable_motion_detection = st.checkbox(
                    "运动检测增强", 
                    value=True,
                    help="结合运动检测提高场景变化识别精度"
                )
                
                scene_detection_sensitivity = st.selectbox(
                    "检测敏感度",
                    ["低", "中", "高", "极高"],
                    index=1,
                    help="调整场景检测的敏感程度"
                )
                
        elif detection_method == "content":
            st.info("📊 **内容分析**\n- 检测画面变化\n- 适合镜头切换\n- 中等精度")
        else:
            st.info("🎨 **直方图分析**\n- 检测色彩变化\n- 适合环境变化\n- 对光照敏感")
        
        # 添加性能监控
        st.markdown("---")
        st.subheader("📊 性能监控")
        if st.button("🔍 测试检测性能"):
            test_detection_performance()
    
    # 主界面 - 改为单列布局
    st.header("📁 视频选择")
    
    # 视频文件选择
    video_files = get_available_videos()
    
    if not video_files:
        st.warning("没有找到可用的视频文件")
        st.info("请将视频文件上传到 `data/temp/uploads/` 目录")
        return
    
    selected_video = st.selectbox(
        "选择视频文件",
        video_files,
        format_func=lambda x: os.path.basename(x)
    )
    
    if st.button("🔍 开始场景检测", type="primary"):
        with st.spinner("正在检测视频场景..."):
            # 收集高级选项参数
            advanced_options = {}
            if detection_method == "ffmpeg":
                # 从session state获取FFmpeg高级选项
                advanced_options = {
                    'use_adaptive_threshold': st.session_state.get('use_adaptive_threshold', False),
                    'enable_motion_detection': st.session_state.get('enable_motion_detection', True),
                    'scene_detection_sensitivity': st.session_state.get('scene_detection_sensitivity', '中')
                }
            
            scenes = detect_video_scenes_advanced(
                selected_video, 
                threshold, 
                min_scene_length, 
                detection_method,
                precision_interval,
                **advanced_options
            )
            
            if scenes:
                st.session_state.scenes = scenes
                st.session_state.selected_video = selected_video
                st.session_state.detection_method = detection_method
                st.session_state.detection_params = {
                    'threshold': threshold,
                    'min_scene_length': min_scene_length,
                    'detection_interval': precision_interval,
                    **advanced_options
                }
                st.success(f"检测完成！发现 {len(scenes)} 个场景")
                
                # 显示检测统计信息
                if detection_method == "ffmpeg":
                    st.info(f"⚡ 使用FFmpeg专业检测 | 阈值: {threshold} | 敏感度: {advanced_options.get('scene_detection_sensitivity', '中')}")
                else:
                    st.info(f"📊 使用{detection_method}检测 | 阈值: {threshold}")
            else:
                st.error("场景检测失败")

    # 场景分段结果区域
    st.markdown("---")
    st.header("🎯 场景分段结果")
    
    if 'scenes' in st.session_state and st.session_state.scenes:
        display_scene_editor()
    else:
        st.info("请先选择视频并进行场景检测")

def get_available_videos():
    """获取可用的视频文件列表"""
    video_dirs = [
        "data/temp/uploads",
        "data/input/test_videos"
    ]
    
    video_extensions = ['.mp4', '.avi', '.mov', '.mkv', '.wmv']
    video_files = []
    
    for video_dir in video_dirs:
        if os.path.exists(video_dir):
            for file in os.listdir(video_dir):
                if any(file.lower().endswith(ext) for ext in video_extensions):
                    video_files.append(os.path.join(video_dir, file))
    
    return video_files

def detect_video_scenes(video_path, threshold, min_scene_length, method, detection_interval=0.1):
    """检测视频场景"""
    try:
        detector = SceneDetector(
            threshold=threshold, 
            min_scene_length=min_scene_length,
            detection_interval=detection_interval
        )
        scenes = detector.detect_scenes(video_path, method=method)
        
        # 为每个场景添加默认的语义标签
        for i, scene in enumerate(scenes):
            scene['scene_id'] = i + 1
            scene['semantic_type'] = "其他"  # 默认标签
            scene['manual_adjusted'] = False
        
        return scenes
        
    except Exception as e:
        logger.error(f"场景检测失败: {e}")
        st.error(f"场景检测失败: {e}")
        return []

def display_scene_editor():
    """显示场景编辑器"""
    scenes = st.session_state.scenes
    video_path = st.session_state.selected_video
    detection_method = st.session_state.get('detection_method', 'unknown')
    
    # 显示视频信息和检测统计
    col1, col2, col3 = st.columns([2, 1, 1])
    with col1:
        st.info(f"📹 视频: {os.path.basename(video_path)} | 🎬 场景数: {len(scenes)}")
    with col2:
        st.metric("检测方法", detection_method.upper())
    with col3:
        total_duration = sum(scene['end_time'] - scene['start_time'] for scene in scenes)
        st.metric("总时长", f"{total_duration:.1f}s")
    
    # 批量操作工具栏
    st.markdown("---")
    st.subheader("🛠️ 批量操作")
    
    col1, col2, col3, col4 = st.columns([1, 1, 1, 1])
    
    with col1:
        if st.button("🎯 智能语义建议"):
            apply_smart_semantic_suggestions(scenes)
    
    with col2:
        batch_semantic_type = st.selectbox(
            "批量设置类型",
            SEMANTIC_TYPES,
            key="batch_semantic"
        )
        if st.button("📝 批量应用"):
            apply_batch_semantic_type(scenes, batch_semantic_type)
    
    with col3:
        if st.button("🔄 重置所有标签"):
            reset_all_semantic_types(scenes)
    
    with col4:
        if st.button("📊 场景统计"):
            show_scene_statistics(scenes)
    
    # 显示场景列表
    st.markdown("---")
    st.subheader("🎬 场景列表")
    
    # 创建编辑表格
    edited_scenes = []
    
    for i, scene in enumerate(scenes):
        col1, col2, col3, col4, col5 = st.columns([0.5, 2, 2, 0.5, 0.5])
        
        with col1:
            # 文件状态（对应红框中的"文件"列）
            if scene.get('manual_adjusted', False):
                st.success("✅")
            else:
                st.warning("⚠️")
        
        with col2:
            # 时间范围（对应红框中的"时间"列）
            time_range = f"{format_time(scene['start_time'])} - {format_time(scene['end_time'])}"
            duration = scene['end_time'] - scene['start_time']
            st.text(f"{time_range}")
            st.caption(f"时长: {duration:.2f}s | 置信度: {scene['confidence']:.3f}")
        
        with col3:
            # 语义类型选择（对应红框中的"语义类型"列）
            semantic_type = st.selectbox(
                f"场景 {i+1} 语义类型",
                SEMANTIC_TYPES,
                index=SEMANTIC_TYPES.index(scene['semantic_type']) if scene['semantic_type'] in SEMANTIC_TYPES else 0,
                key=f"semantic_{i}",
                label_visibility="collapsed"
            )
            
            # 更新场景的语义类型
            if semantic_type != scene['semantic_type']:
                scene['semantic_type'] = semantic_type
                scene['manual_adjusted'] = True
        
        with col4:
            # 预览按钮
            if st.button("👁️", key=f"preview_{i}", help="预览场景"):
                preview_scene(video_path, scene)
        
        with col5:
            # 删除按钮
            if st.button("🗑️", key=f"delete_{i}", help="删除场景"):
                if st.session_state.get(f"confirm_delete_{i}", False):
                    scenes.pop(i)
                    st.rerun()
                else:
                    st.session_state[f"confirm_delete_{i}"] = True
                    st.warning("再次点击确认删除")
        
        edited_scenes.append(scene)
    
    # 更新session state
    st.session_state.scenes = edited_scenes
    
    # 操作按钮
    st.markdown("---")
    col1, col2, col3, col4 = st.columns([1, 1, 1, 1])
    
    with col1:
        if st.button("💾 保存分段结果", type="primary"):
            save_scene_segments(video_path, edited_scenes)
    
    with col2:
        if st.button("🎬 生成视频片段"):
            generate_video_segments(video_path, edited_scenes)
    
    with col3:
        if st.button("📊 导出数据"):
            export_scene_data(edited_scenes)
    
    with col4:
        if st.button("🔄 重新检测"):
            # 清除当前结果，重新检测
            for key in ['scenes', 'selected_video', 'detection_method']:
                if key in st.session_state:
                    del st.session_state[key]
            st.rerun()

def format_time(seconds):
    """格式化时间显示"""
    hours = int(seconds // 3600)
    minutes = int((seconds % 3600) // 60)
    secs = seconds % 60
    return f"{hours:02d}:{minutes:02d}:{secs:06.3f}"

def preview_scene(video_path, scene):
    """预览场景"""
    st.info(f"🎬 场景预览")
    st.write(f"**时间范围**: {format_time(scene['start_time'])} - {format_time(scene['end_time'])}")
    st.write(f"**时长**: {scene['end_time'] - scene['start_time']:.2f} 秒")
    st.write(f"**语义类型**: {scene['semantic_type']}")
    st.write(f"**置信度**: {scene['confidence']:.3f}")
    
    # 这里可以添加视频预览功能
    # 由于Streamlit的限制，暂时显示信息
    st.info("💡 提示: 视频预览功能将在后续版本中实现")

def save_scene_segments(video_path, scenes):
    """保存场景分段结果"""
    try:
        # 创建输出目录
        output_dir = "data/output/scene_segments"
        os.makedirs(output_dir, exist_ok=True)
        
        # 保存场景数据
        video_name = os.path.splitext(os.path.basename(video_path))[0]
        output_file = os.path.join(output_dir, f"{video_name}_scenes.json")
        
        scene_data = {
            "video_path": video_path,
            "video_name": video_name,
            "total_scenes": len(scenes),
            "scenes": scenes
        }
        
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(scene_data, f, ensure_ascii=False, indent=2)
        
        st.success(f"✅ 场景分段结果已保存到: {output_file}")
        
    except Exception as e:
        logger.error(f"保存失败: {e}")
        st.error(f"保存失败: {e}")

def generate_video_segments(video_path, scenes):
    """生成视频片段"""
    try:
        processor = VideoProcessor()
        
        # 创建输出目录
        output_base_dir = "data/output/scene_segments"
        video_name = os.path.splitext(os.path.basename(video_path))[0]
        
        progress_bar = st.progress(0)
        status_text = st.empty()
        
        generated_files = []
        
        for i, scene in enumerate(scenes):
            # 更新进度
            progress = (i + 1) / len(scenes)
            progress_bar.progress(progress)
            status_text.text(f"正在生成场景 {i+1}/{len(scenes)}: {scene['semantic_type']}")
            
            # 创建语义类型目录
            semantic_dir = os.path.join(output_base_dir, scene['semantic_type'])
            os.makedirs(semantic_dir, exist_ok=True)
            
            # 生成片段
            segment_file = processor.extract_segment(
                video_path=video_path,
                start_time=scene['start_time'],
                end_time=scene['end_time'],
                segment_index=scene['scene_id'],
                semantic_type=scene['semantic_type'],
                video_id=video_name,
                output_dir=semantic_dir
            )
            
            if segment_file:
                generated_files.append(segment_file)
                logger.info(f"生成场景片段: {segment_file}")
        
        progress_bar.progress(1.0)
        status_text.text("✅ 所有场景片段生成完成！")
        
        st.success(f"🎉 成功生成 {len(generated_files)} 个视频片段")
        
        # 显示生成的文件列表
        with st.expander("📁 生成的文件列表"):
            for file_path in generated_files:
                st.text(file_path)
        
    except Exception as e:
        logger.error(f"视频片段生成失败: {e}")
        st.error(f"视频片段生成失败: {e}")

def export_scene_data(scenes):
    """导出场景数据"""
    try:
        # 创建DataFrame
        export_data = []
        for scene in scenes:
            export_data.append({
                "场景ID": scene['scene_id'],
                "开始时间": format_time(scene['start_time']),
                "结束时间": format_time(scene['end_time']),
                "时长(秒)": round(scene['end_time'] - scene['start_time'], 3),
                "语义类型": scene['semantic_type'],
                "置信度": round(scene['confidence'], 3),
                "检测方法": scene.get('method', 'unknown'),
                "手动调整": "是" if scene.get('manual_adjusted', False) else "否"
            })
        
        df = pd.DataFrame(export_data)
        
        # 转换为CSV
        csv = df.to_csv(index=False, encoding='utf-8-sig')
        
        st.download_button(
            label="📥 下载CSV文件",
            data=csv,
            file_name="scene_segments.csv",
            mime="text/csv"
        )
        
        st.success("✅ 数据导出准备完成，点击上方按钮下载")
        
    except Exception as e:
        logger.error(f"数据导出失败: {e}")
        st.error(f"数据导出失败: {e}")

def test_detection_performance():
    """测试不同检测方法的性能"""
    video_files = get_available_videos()
    if not video_files:
        st.warning("没有可用的视频文件进行测试")
        return
    
    test_video = video_files[0]  # 使用第一个视频进行测试
    
    st.info(f"🎯 正在测试视频: {os.path.basename(test_video)}")
    
    methods = ["ffmpeg", "content", "histogram"]
    results = {}
    
    progress_bar = st.progress(0)
    
    for i, method in enumerate(methods):
        with st.spinner(f"测试 {method} 方法..."):
            import time
            start_time = time.time()
            
            try:
                detector = SceneDetector(threshold=0.3, min_scene_length=1.0)
                scenes = detector.detect_scenes(test_video, method=method)
                
                end_time = time.time()
                processing_time = end_time - start_time
                
                results[method] = {
                    "scenes_count": len(scenes),
                    "processing_time": processing_time,
                    "success": True
                }
                
            except Exception as e:
                results[method] = {
                    "scenes_count": 0,
                    "processing_time": 0,
                    "success": False,
                    "error": str(e)
                }
        
        progress_bar.progress((i + 1) / len(methods))
    
    # 显示结果
    st.subheader("📈 性能测试结果")
    
    for method, result in results.items():
        if result["success"]:
            st.success(f"**{method.upper()}**: {result['scenes_count']} 个场景, {result['processing_time']:.2f}秒")
        else:
            st.error(f"**{method.upper()}**: 失败 - {result.get('error', '未知错误')}")

def detect_video_scenes_advanced(video_path, threshold, min_scene_length, method, detection_interval=0.1, **kwargs):
    """高级场景检测，支持更多配置选项"""
    try:
        detector = SceneDetector(
            threshold=threshold, 
            min_scene_length=min_scene_length,
            detection_interval=detection_interval
        )
        
        # 根据方法和高级选项调整参数
        if method == "ffmpeg":
            # 处理FFmpeg高级选项
            use_adaptive_threshold = kwargs.get('use_adaptive_threshold', False)
            enable_motion_detection = kwargs.get('enable_motion_detection', True)
            sensitivity = kwargs.get('scene_detection_sensitivity', '中')
            
            # 根据敏感度调整阈值
            sensitivity_map = {
                "低": threshold * 1.5,
                "中": threshold,
                "高": threshold * 0.7,
                "极高": threshold * 0.4
            }
            
            adjusted_threshold = sensitivity_map.get(sensitivity, threshold)
            detector.threshold = adjusted_threshold
            
            logger.info(f"FFmpeg高级检测: 阈值={adjusted_threshold:.3f}, 自适应={use_adaptive_threshold}, 运动检测={enable_motion_detection}, 精度={detection_interval}s")
        
        scenes = detector.detect_scenes(video_path, method=method)
        
        # 为每个场景添加默认的语义标签
        for i, scene in enumerate(scenes):
            scene['scene_id'] = i + 1
            scene['semantic_type'] = "其他"  # 默认标签
            scene['manual_adjusted'] = False
        
        return scenes
        
    except Exception as e:
        logger.error(f"高级场景检测失败: {e}")
        st.error(f"高级场景检测失败: {e}")
        return []

def apply_smart_semantic_suggestions(scenes):
    """应用智能语义建议"""
    # 基于场景时长和位置的简单启发式规则
    total_scenes = len(scenes)
    
    for i, scene in enumerate(scenes):
        duration = scene['end_time'] - scene['start_time']
        position_ratio = i / total_scenes
        
        # 简单的启发式规则
        if i == 0:
            scene['semantic_type'] = "广告开场"
        elif i == total_scenes - 1:
            scene['semantic_type'] = "总结收尾"
        elif duration < 3:
            scene['semantic_type'] = "其他"
        elif position_ratio < 0.3:
            scene['semantic_type'] = "问题陈述"
        elif position_ratio < 0.7:
            scene['semantic_type'] = "产品介绍"
        else:
            scene['semantic_type'] = "行动号召"
        
        scene['manual_adjusted'] = True
    
    st.success("✅ 已应用智能语义建议")

def apply_batch_semantic_type(scenes, semantic_type):
    """批量应用语义类型"""
    for scene in scenes:
        scene['semantic_type'] = semantic_type
        scene['manual_adjusted'] = True
    
    st.success(f"✅ 已将所有场景设置为: {semantic_type}")

def reset_all_semantic_types(scenes):
    """重置所有语义类型"""
    for scene in scenes:
        scene['semantic_type'] = "其他"
        scene['manual_adjusted'] = False
    
    st.success("✅ 已重置所有语义标签")

def show_scene_statistics(scenes):
    """显示场景统计信息"""
    st.subheader("📈 场景统计")
    
    # 统计各语义类型的数量
    semantic_counts = {}
    total_duration = 0
    
    for scene in scenes:
        semantic_type = scene['semantic_type']
        duration = scene['end_time'] - scene['start_time']
        
        if semantic_type not in semantic_counts:
            semantic_counts[semantic_type] = {'count': 0, 'duration': 0}
        
        semantic_counts[semantic_type]['count'] += 1
        semantic_counts[semantic_type]['duration'] += duration
        total_duration += duration
    
    # 显示统计表格
    stats_data = []
    for semantic_type, stats in semantic_counts.items():
        percentage = (stats['duration'] / total_duration) * 100 if total_duration > 0 else 0
        stats_data.append({
            "语义类型": semantic_type,
            "场景数量": stats['count'],
            "总时长(秒)": f"{stats['duration']:.2f}",
            "占比(%)": f"{percentage:.1f}%"
        })
    
    df = pd.DataFrame(stats_data)
    st.dataframe(df, use_container_width=True)

if __name__ == "__main__":
    main() 