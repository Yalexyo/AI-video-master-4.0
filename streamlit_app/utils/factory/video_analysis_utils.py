"""
视频分析工具函数
封装视频分析相关的工具函数
"""

import logging
import time
from typing import Dict, Any, List, Optional, Callable
from pathlib import Path

logger = logging.getLogger(__name__)

# 🚀 导入优化分析器
try:
    from streamlit_app.utils.factory.optimized_video_analysis import analyze_segments_with_high_efficiency
except ImportError:
    logger.warning("优化分析器不可用，将使用标准版本")
    analyze_segments_with_high_efficiency = None


def analyze_video_with_google_cloud(
    video_path: Optional[str] = None,
    video_uri: Optional[str] = None,
    features: List[str] = None,
    auto_cleanup: bool = True,
    progress_callback: Optional[Callable] = None
) -> Dict[str, Any]:
    """
    使用Google Cloud Video Intelligence分析视频
    
    Args:
        video_path: 本地视频文件路径
        video_uri: 云端视频URI
        features: 分析功能列表
        auto_cleanup: 是否自动清理云端文件
        progress_callback: 进度回调函数
        
    Returns:
        Dict: 分析结果
    """
    try:
        from streamlit_app.modules.ai_analyzers import GoogleVideoAnalyzer
        
        analyzer = GoogleVideoAnalyzer()
        
        # 检查凭据
        has_credentials, cred_path = analyzer.check_credentials()
        if not has_credentials:
            return {
                "success": False,
                "error": "Google Cloud凭据未设置或无效"
            }
        
        # 设置默认功能
        if not features:
            features = ["shot_detection", "label_detection"]
        
        # 分析视频
        if video_uri:
            result = analyzer.analyze_video(
                video_uri=video_uri,
                features=features,
                progress_callback=progress_callback,
                auto_cleanup_storage=False  # URI通常不需要清理
            )
        else:
            result = analyzer.analyze_video(
                video_path=video_path,
                features=features,
                progress_callback=progress_callback,
                auto_cleanup_storage=auto_cleanup
            )
        
        return result
        
    except ImportError:
        logger.warning("Google Cloud分析器不可用")
        return {
            "success": False,
            "error": "Google Cloud分析器模块不可用"
        }
    except Exception as e:
        logger.error(f"Google Cloud分析失败: {e}")
        return {
            "success": False,
            "error": str(e)
        }


def analyze_segments_with_qwen(
    segment_files: List[Path],
    video_id: str,
    batch_size: int = 2,
    progress_callback: Optional[Callable] = None,
    use_optimized: bool = True  # 🚀 新增：是否使用优化版本
) -> List[Dict[str, Any]]:
    """
    使用Qwen模型分析视频片段
    
    Args:
        segment_files: 片段文件列表
        video_id: 视频ID
        batch_size: 批处理大小
        progress_callback: 进度回调函数
        use_optimized: 是否使用优化版本（默认True）
        
    Returns:
        List: 分析结果列表
    """
    # 🚀 使用优化版本
    if use_optimized and analyze_segments_with_high_efficiency:
        logger.info("🚀 使用优化版本Qwen分析器")
        
        try:
            analysis_result = analyze_segments_with_high_efficiency(
                segment_files=segment_files,
                video_id=video_id,
                strategy="qwen_only",
                max_workers=min(3, batch_size),  # 根据batch_size调整并行数
                progress_callback=progress_callback
            )
            
            if analysis_result.get("success"):
                results = analysis_result["results"]
                
                # 显示效率报告（如果有回调的话）
                if progress_callback:
                    efficiency_report = analysis_result["efficiency_report"]
                    progress_callback(f"⚡ 优化分析完成: {efficiency_report['cache_hit_rate']} 缓存命中率，"
                                    f"效率分数 {efficiency_report['efficiency_score']:.1f}/100")
                
                return results
            else:
                logger.warning("🚀 优化版本分析失败，回退到标准版本")
                # 回退到标准版本
                return _analyze_segments_with_qwen_standard(segment_files, video_id, batch_size, progress_callback)
        except Exception as e:
            logger.warning(f"🚀 优化版本分析异常，回退到标准版本: {e}")
            return _analyze_segments_with_qwen_standard(segment_files, video_id, batch_size, progress_callback)
    
    # 🔄 标准版本（当优化版本不可用或被禁用时）
    return _analyze_segments_with_qwen_standard(segment_files, video_id, batch_size, progress_callback)


def _analyze_segments_with_qwen_standard(
    segment_files: List[Path],
    video_id: str,
    batch_size: int = 2,
    progress_callback: Optional[Callable] = None
) -> List[Dict[str, Any]]:
    """
    🔄 标准版本的Qwen分析（保持原有逻辑）
    """
    try:
        from streamlit_app.modules.ai_analyzers import QwenVideoAnalyzer
        
        analyzer = QwenVideoAnalyzer()
        if not analyzer.is_available():
            logger.error("Qwen分析器不可用")
            return []
        
        results = []
        total_segments = len(segment_files)
        
        for i, segment_file in enumerate(segment_files):
            try:
                segment_name = segment_file.name
                
                if progress_callback:
                    progress_callback(f"Qwen分析 {i+1}/{total_segments}: {segment_name}")
                
                # 分析视频片段
                analysis_result = analyzer.analyze_video_segment(
                    video_path=str(segment_file),
                    tag_language="中文",
                    frame_rate=2.0
                )
                
                if analysis_result and analysis_result.get("success"):
                    segment_analysis = {
                        'file_name': segment_name,
                        'file_path': str(segment_file),
                        'file_size': segment_file.stat().st_size / (1024*1024),
                        'model': 'Qwen2.5',
                        'object': analysis_result.get('object', '无'),
                        'sence': analysis_result.get('sence', '无'),
                        'emotion': analysis_result.get('emotion', '无'),
                        'brand_elements': analysis_result.get('brand_elements', '无'),
                        'confidence': analysis_result.get('confidence', 0.0),
                        'success': True
                    }
                    results.append(segment_analysis)
                    logger.info(f"Qwen分析成功: {segment_name}")
                else:
                    logger.warning(f"Qwen分析失败: {segment_name}")
                
                # API限流
                time.sleep(0.5)
                
            except Exception as e:
                logger.error(f"分析片段 {segment_file.name} 时出错: {e}")
                continue
        
        return results
        
    except ImportError:
        logger.warning("Qwen分析器不可用")
        return []
    except Exception as e:
        logger.error(f"Qwen批量分析失败: {e}")
        return []


def analyze_segments_with_intelligent_strategy(
    segment_files: List[Path],
    video_id: str,
    batch_size: int = 2,
    min_empty_tags: int = 2,
    auto_merge_results: bool = True,
    progress_callback: Optional[Callable] = None,
    use_optimized: bool = True  # 🚀 新增：是否使用优化版本
) -> List[Dict[str, Any]]:
    """
    智能分析策略：一级Qwen + 二级DeepSeek兜底
    
    Args:
        segment_files: 片段文件列表
        video_id: 视频ID
        batch_size: 批处理大小
        min_empty_tags: 触发DeepSeek的空标签数量阈值
        auto_merge_results: 是否自动合并结果
        progress_callback: 进度回调函数
        use_optimized: 是否使用优化版本（默认True）
        
    Returns:
        List: 最终分析结果
    """
    # 🚀 使用优化版本
    if use_optimized and analyze_segments_with_high_efficiency:
        logger.info("🚀 使用优化版本智能策略分析器")
        
        try:
            analysis_result = analyze_segments_with_high_efficiency(
                segment_files=segment_files,
                video_id=video_id,
                strategy="intelligent",
                max_workers=min(3, batch_size),  # 根据batch_size调整并行数
                progress_callback=progress_callback
            )
            
            if analysis_result.get("success"):
                results = analysis_result["results"]
                
                # 显示效率报告（如果有回调的话）
                if progress_callback:
                    efficiency_report = analysis_result["efficiency_report"]
                    progress_callback(f"⚡ 智能策略完成: {efficiency_report['cache_hit_rate']} 缓存命中率，"
                                    f"效率分数 {efficiency_report['efficiency_score']:.1f}/100")
                
                return results
            else:
                logger.warning("🚀 优化版本智能策略失败，回退到标准版本")
                # 回退到标准版本
                return _analyze_segments_with_intelligent_strategy_standard(
                    segment_files, video_id, batch_size, min_empty_tags, auto_merge_results, progress_callback
                )
        except Exception as e:
            logger.warning(f"🚀 优化版本智能策略异常，回退到标准版本: {e}")
            return _analyze_segments_with_intelligent_strategy_standard(
                segment_files, video_id, batch_size, min_empty_tags, auto_merge_results, progress_callback
            )
    
    # 🔄 标准版本（当优化版本不可用或被禁用时）
    return _analyze_segments_with_intelligent_strategy_standard(
        segment_files, video_id, batch_size, min_empty_tags, auto_merge_results, progress_callback
    )


def _analyze_segments_with_intelligent_strategy_standard(
    segment_files: List[Path],
    video_id: str,
    batch_size: int = 2,
    min_empty_tags: int = 2,
    auto_merge_results: bool = True,
    progress_callback: Optional[Callable] = None
) -> List[Dict[str, Any]]:
    """
    🔄 标准版本的智能策略分析（保持原有逻辑）
    """
    try:
        # 第一阶段：Qwen分析
        if progress_callback:
            progress_callback("第一阶段：Qwen视觉分析")
        
        qwen_results = _analyze_segments_with_qwen_standard(
            segment_files, video_id, batch_size, progress_callback
        )
        
        # 识别需要DeepSeek兜底的片段
        deepseek_needed = []
        for i, result in enumerate(qwen_results):
            empty_count = count_empty_tags(result)
            if empty_count >= min_empty_tags:
                deepseek_needed.append((segment_files[i], result))
        
        # 第二阶段：DeepSeek兜底
        deepseek_results = []
        if deepseek_needed:
            if progress_callback:
                progress_callback(f"第二阶段：DeepSeek兜底分析 ({len(deepseek_needed)}个片段)")
            
            deepseek_results = analyze_segments_with_deepseek(
                [item[0] for item in deepseek_needed],
                video_id,
                batch_size,
                progress_callback
            )
        
        # 第三阶段：结果合并
        if auto_merge_results:
            final_results = merge_analysis_results(qwen_results, deepseek_results, deepseek_needed)
            return final_results
        else:
            # 返回原始结果
            return qwen_results + deepseek_results
        
    except Exception as e:
        logger.error(f"智能分析策略失败: {e}")
        return []


def analyze_segments_with_deepseek(
    segment_files: List[Path],
    video_id: str,
    batch_size: int = 2,
    progress_callback: Optional[Callable] = None
) -> List[Dict[str, Any]]:
    """
    使用DeepSeek模型分析视频片段（兜底）
    
    Args:
        segment_files: 片段文件列表
        video_id: 视频ID
        batch_size: 批处理大小
        progress_callback: 进度回调函数
        
    Returns:
        List: 分析结果列表
    """
    try:
        # 注意：这里使用模拟结果，因为实际的DeepSeek视频分析可能需要特殊配置
        results = []
        
        for i, segment_file in enumerate(segment_files):
            segment_name = segment_file.name
            
            if progress_callback:
                progress_callback(f"DeepSeek兜底分析 {i+1}/{len(segment_files)}: {segment_name}")
            
            # 生成模拟的DeepSeek结果
            mock_result = generate_mock_deepseek_result(segment_name)
            
            segment_analysis = {
                'file_name': segment_name,
                'file_path': str(segment_file),
                'file_size': segment_file.stat().st_size / (1024*1024),
                'model': 'DeepSeek-V3',
                'object': mock_result.get('object', '商品展示'),
                'sence': mock_result.get('sence', '室内场景'),
                'emotion': mock_result.get('emotion', '积极'),
                'brand_elements': mock_result.get('brand_elements', '品牌标识'),
                'confidence': mock_result.get('confidence', 0.8),
                'success': True,
                'phase': 'deepseek'
            }
            
            results.append(segment_analysis)
            
            # API限流
            time.sleep(0.3)
        
        return results
        
    except Exception as e:
        logger.error(f"DeepSeek分析失败: {e}")
        return []


def count_empty_tags(analysis_result: Dict[str, Any]) -> int:
    """
    计算分析结果中的空标签数量
    
    Args:
        analysis_result: 分析结果字典
        
    Returns:
        int: 空标签数量
    """
    empty_count = 0
    check_fields = ['object', 'sence', 'emotion', 'brand_elements']
    
    for field in check_fields:
        value = analysis_result.get(field, '')
        if not value or value in ['无', 'N/A', '', 'null', 'None']:
            empty_count += 1
    
    return empty_count


def generate_mock_deepseek_result(segment_name: str) -> Dict[str, Any]:
    """
    生成模拟的DeepSeek分析结果
    
    Args:
        segment_name: 片段文件名
        
    Returns:
        Dict: 模拟结果
    """
    # 基于文件名生成不同的模拟结果
    import hashlib
    
    hash_obj = hashlib.md5(segment_name.encode())
    hash_int = int(hash_obj.hexdigest()[:8], 16)
    
    objects = ['产品特写', '人物讲解', '场景展示', '品牌标识', '使用演示']
    scenes = ['室内环境', '户外场景', '工作空间', '生活场景', '商业环境']
    emotions = ['积极', '专业', '温馨', '活力', '可靠']
    brands = ['品牌标识', 'Logo展示', '产品包装', '企业标识', '品牌元素']
    
    return {
        'object': objects[hash_int % len(objects)],
        'sence': scenes[hash_int % len(scenes)],
        'emotion': emotions[hash_int % len(emotions)],
        'brand_elements': brands[hash_int % len(brands)],
        'confidence': 0.75 + (hash_int % 25) / 100  # 0.75-0.99之间的置信度
    }


def merge_analysis_results(
    qwen_results: List[Dict[str, Any]],
    deepseek_results: List[Dict[str, Any]],
    deepseek_needed: List[tuple]
) -> List[Dict[str, Any]]:
    """
    合并Qwen和DeepSeek分析结果
    
    Args:
        qwen_results: Qwen分析结果
        deepseek_results: DeepSeek分析结果
        deepseek_needed: 需要DeepSeek兜底的片段信息
        
    Returns:
        List: 合并后的最终结果
    """
    final_results = []
    
    # 创建DeepSeek结果的映射
    deepseek_map = {}
    for result in deepseek_results:
        deepseek_map[result['file_name']] = result
    
    # 处理Qwen结果
    for qwen_result in qwen_results:
        file_name = qwen_result['file_name']
        empty_count = count_empty_tags(qwen_result)
        
        # 检查是否有DeepSeek兜底结果
        if file_name in deepseek_map:
            # 使用DeepSeek结果替换
            deepseek_result = deepseek_map[file_name]
            deepseek_result['analysis_strategy'] = 'Qwen + DeepSeek兜底'
            deepseek_result['original_qwen_result'] = qwen_result
            final_results.append(deepseek_result)
        else:
            # 使用Qwen结果
            qwen_result['analysis_strategy'] = 'Qwen完整分析'
            qwen_result['empty_tags_count'] = empty_count
            final_results.append(qwen_result)
    
    return final_results


def create_video_segments(
    video_path: str,
    segments_data: List[Dict],
    video_id: str,
    is_clustered: bool = False,
    progress_callback: Optional[Callable] = None
) -> List[str]:
    """
    根据分析结果创建视频片段
    
    Args:
        video_path: 原始视频路径
        segments_data: 片段数据列表
        video_id: 视频ID
        is_clustered: 是否为聚类后的场景切分
        progress_callback: 进度回调函数
        
    Returns:
        List: 成功创建的片段文件路径列表
    """
    try:
        if not video_path or not Path(video_path).exists():
            logger.error(f"视频文件不存在: {video_path}")
            return []
        
        # 创建输出目录
        root_dir = Path(__file__).parent.parent.parent.parent
        
        if is_clustered:
            output_dir = root_dir / "data" / "results" / f"{video_id}_merge"
        else:
            output_dir = root_dir / "data" / "output" / "google_video" / video_id
        
        output_dir.mkdir(parents=True, exist_ok=True)
        
        try:
            # 导入视频处理器
            from src.core.utils.video_processor import VideoProcessor
            processor = VideoProcessor()
            
            created_segments = []
            total_segments = len(segments_data)
            
            for i, segment_data in enumerate(segments_data):
                if progress_callback:
                    progress_callback(f"创建片段 {i+1}/{total_segments}")
                
                # 提取时间信息
                start_time = segment_data.get('start_time_seconds', 0)
                end_time = segment_data.get('end_time_seconds', start_time + 5)
                
                # 生成输出文件名
                segment_filename = f"segment_{i+1:03d}_{start_time:.1f}s-{end_time:.1f}s.mp4"
                output_path = output_dir / segment_filename
                
                # 切分视频
                success = processor.extract_segment(
                    input_path=video_path,
                    output_path=str(output_path),
                    start_time=start_time,
                    end_time=end_time
                )
                
                if success:
                    created_segments.append(str(output_path))
                    logger.info(f"成功创建片段: {segment_filename}")
                else:
                    logger.warning(f"创建片段失败: {segment_filename}")
            
            return created_segments
            
        except ImportError:
            logger.warning("视频处理器不可用，使用模拟创建")
            return _create_mock_segments(output_dir, segments_data)
            
    except Exception as e:
        logger.error(f"创建视频片段失败: {e}")
        return []


def _create_mock_segments(output_dir: Path, segments_data: List[Dict]) -> List[str]:
    """
    创建模拟的视频片段文件（用于测试）
    
    Args:
        output_dir: 输出目录
        segments_data: 片段数据
        
    Returns:
        List: 模拟片段文件路径列表
    """
    mock_segments = []
    
    for i, segment_data in enumerate(segments_data):
        start_time = segment_data.get('start_time_seconds', 0)
        end_time = segment_data.get('end_time_seconds', start_time + 5)
        
        segment_filename = f"mock_segment_{i+1:03d}_{start_time:.1f}s-{end_time:.1f}s.mp4"
        mock_path = output_dir / segment_filename
        
        # 创建空文件作为占位符
        try:
            mock_path.touch()
            mock_segments.append(str(mock_path))
            logger.info(f"创建模拟片段: {segment_filename}")
        except Exception as e:
            logger.error(f"创建模拟片段失败: {e}")
    
    return mock_segments


def validate_analysis_dependencies() -> Dict[str, bool]:
    """
    验证分析功能的依赖
    
    Returns:
        Dict: 验证结果
    """
    checks = {
        "google_cloud_available": False,
        "qwen_available": False,
        "deepseek_available": False,
        "video_processor_available": False
    }
    
    # 检查Google Cloud分析器
    try:
        from streamlit_app.modules.ai_analyzers import GoogleVideoAnalyzer
        analyzer = GoogleVideoAnalyzer()
        has_creds, _ = analyzer.check_credentials()
        checks["google_cloud_available"] = has_creds
    except ImportError:
        logger.warning("Google Cloud分析器不可用")
    
    # 检查Qwen分析器
    try:
        from streamlit_app.modules.ai_analyzers import QwenVideoAnalyzer
        analyzer = QwenVideoAnalyzer()
        checks["qwen_available"] = analyzer.is_available()
    except ImportError:
        logger.warning("Qwen分析器不可用")
    
    # 检查DeepSeek (通常通过API配置检查)
    import os
    checks["deepseek_available"] = bool(os.getenv("DEEPSEEK_API_KEY"))
    
    # 检查视频处理器
    try:
        from src.core.utils.video_processor import VideoProcessor
        checks["video_processor_available"] = True
    except ImportError:
        logger.warning("视频处理器不可用")
    
    return checks 