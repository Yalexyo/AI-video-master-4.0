"""
短视频处理优化工具模块
专门针对小于1MB或短时长的视频进行优化分析
"""

import os
import logging
from typing import Dict, Any, Optional
from pathlib import Path

logger = logging.getLogger(__name__)

class ShortVideoOptimizer:
    """短视频处理优化器"""
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """
        初始化短视频优化器
        
        Args:
            config: 优化配置，如果为None则使用默认配置
        """
        self.config = config or self._get_default_config()
        logger.info("🎯 短视频优化器已初始化")
    
    def _get_default_config(self) -> Dict[str, Any]:
        """获取默认优化配置"""
        try:
            from config.factory_config import FactoryConfig
            return FactoryConfig.VISUAL_ANALYSIS_CONFIG.get("short_video_optimization", {})
        except ImportError:
            # 兜底配置
            return {
                "enabled": True,
                "file_size_threshold_mb": 1.0,
                "duration_threshold_sec": 5.0,
                "quality_threshold_reduction": 0.15,
                "frame_rate_boost": 2.0,
                "max_frame_rate": 8.0,
                "min_file_size_mb": 0.5  # 小于此大小的文件将被过滤
            }
    
    def should_process_video(self, video_path: str) -> bool:
        """
        判断视频是否应该被处理（过滤掉过小的文件）
        
        Args:
            video_path: 视频文件路径
            
        Returns:
            是否应该处理该视频
        """
        try:
            file_size_mb = os.path.getsize(video_path) / (1024 * 1024)
            min_size = self.config.get("min_file_size_mb", 0.5)
            
            if file_size_mb < min_size:
                logger.info(f"🚫 跳过过小文件: {video_path} ({file_size_mb:.2f}MB < {min_size}MB)")
                return False
            return True
        except Exception as e:
            logger.error(f"检查文件大小失败 {video_path}: {e}")
            return False
    
    def analyze_video_characteristics(self, video_path: str) -> Dict[str, Any]:
        """
        分析视频特征以确定优化策略
        
        Args:
            video_path: 视频文件路径
            
        Returns:
            视频特征分析结果
        """
        try:
            # 先检查文件是否应该被处理
            if not self.should_process_video(video_path):
                return {
                    "file_size_mb": 0,
                    "duration_sec": 0,
                    "video_type": "filtered",
                    "optimization_suggestion": {},
                    "needs_optimization": False,
                    "filtered": True,
                    "reason": "文件过小，已过滤"
                }
            
            # 获取文件大小
            file_size_mb = os.path.getsize(video_path) / (1024 * 1024)
            
            # 获取视频时长
            duration_sec = self._get_video_duration(video_path)
            
            # 分析视频类型
            video_type = self._classify_video_type(file_size_mb, duration_sec)
            
            # 生成优化建议
            optimization_suggestion = self._generate_optimization_suggestion(video_type, file_size_mb, duration_sec)
            
            return {
                "file_size_mb": file_size_mb,
                "duration_sec": duration_sec,
                "video_type": video_type,
                "optimization_suggestion": optimization_suggestion,
                "needs_optimization": video_type in ["short"],
                "filtered": False
            }
            
        except Exception as e:
            logger.error(f"分析视频特征失败: {e}")
            return {
                "file_size_mb": 0,
                "duration_sec": 0,
                "video_type": "unknown",
                "optimization_suggestion": {},
                "needs_optimization": False,
                "filtered": False
            }
    
    def _get_video_duration(self, video_path: str) -> float:
        """获取视频时长"""
        try:
            import cv2
            cap = cv2.VideoCapture(video_path)
            if cap.isOpened():
                fps = cap.get(cv2.CAP_PROP_FPS)
                frame_count = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
                duration = frame_count / fps if fps > 0 else 0
                cap.release()
                return duration
            return 0
        except Exception as e:
            logger.warning(f"获取视频时长失败: {e}")
            return 0
    
    def _classify_video_type(self, file_size_mb: float, duration_sec: float) -> str:
        """
        根据文件大小和时长分类视频类型
        
        Returns:
            视频类型: "short", "medium", "long"
        """
        if not self.config.get("enabled", True):
            return "normal"
        
        # 短视频判断
        if (file_size_mb < self.config.get("file_size_threshold_mb", 1.0) or
            duration_sec < self.config.get("duration_threshold_sec", 5.0)):
            return "short"
        
        # 中等视频
        if duration_sec < 30.0:
            return "medium"
        
        # 长视频
        return "long"
    
    def _generate_optimization_suggestion(
        self, 
        video_type: str, 
        file_size_mb: float, 
        duration_sec: float
    ) -> Dict[str, Any]:
        """生成针对性的优化建议"""
        
        base_frame_rate = 2.0
        base_quality_threshold = 0.6
        base_retry_count = 1
        
        if video_type == "short":
            optimized_frame_rate = min(
                base_frame_rate * self.config.get("frame_rate_boost", 2.0),
                self.config.get("max_frame_rate", 8.0)
            )
            optimized_quality_threshold = max(
                base_quality_threshold - self.config.get("quality_threshold_reduction", 0.15),
                0.3
            )
            
            return {
                "frame_rate": optimized_frame_rate,
                "quality_threshold": optimized_quality_threshold,
                "retry_count": 2,
                "special_handling": True,
                "reason": f"短视频({file_size_mb:.2f}MB, {duration_sec:.1f}s)启用优化策略"
            }
        
        elif video_type == "medium":
            return {
                "frame_rate": 3.0,
                "quality_threshold": 0.55,
                "retry_count": 1,
                "special_handling": False,
                "reason": "中等时长视频使用标准参数"
            }
        
        else:  # long
            return {
                "frame_rate": 1.5,
                "quality_threshold": 0.6,
                "retry_count": 1,
                "special_handling": False,
                "reason": "长视频使用保守参数节省资源"
            }
    
    def optimize_analysis_params(self, video_path: str, original_params: Dict[str, Any]) -> Dict[str, Any]:
        """
        基于视频特征优化分析参数
        
        Args:
            video_path: 视频文件路径
            original_params: 原始分析参数
            
        Returns:
            优化后的分析参数
        """
        if not self.config.get("enabled", True):
            logger.debug("短视频优化已禁用，使用原始参数")
            return original_params
        
        # 分析视频特征
        characteristics = self.analyze_video_characteristics(video_path)
        
        if not characteristics["needs_optimization"]:
            logger.debug(f"视频无需优化: {characteristics['video_type']}")
            return original_params
        
        # 应用优化建议
        optimized_params = original_params.copy()
        suggestion = characteristics["optimization_suggestion"]
        
        optimized_params.update({
            "frame_rate": suggestion.get("frame_rate", original_params.get("frame_rate", 2.0)),
            "quality_threshold": suggestion.get("quality_threshold", original_params.get("quality_threshold", 0.6)),
            "retry_count": suggestion.get("retry_count", original_params.get("retry_count", 1))
        })
        
        # 添加优化信息
        optimized_params["optimization_applied"] = True
        optimized_params["optimization_reason"] = suggestion.get("reason", "")
        optimized_params["video_characteristics"] = characteristics
        
        logger.info(f"🎯 应用短视频优化: {suggestion.get('reason', '')}")
        logger.info(f"   帧率: {original_params.get('frame_rate', 2.0)} → {optimized_params['frame_rate']}")
        logger.info(f"   质量阈值: {original_params.get('quality_threshold', 0.6)} → {optimized_params['quality_threshold']}")
        
        return optimized_params
    
    def get_optimization_report(self, video_paths: list) -> Dict[str, Any]:
        """
        生成多个视频的优化分析报告
        
        Args:
            video_paths: 视频文件路径列表
            
        Returns:
            优化分析报告
        """
        report = {
            "total_videos": len(video_paths),
            "filtered_count": 0,
            "short_count": 0,
            "medium_count": 0,
            "long_count": 0,
            "optimization_enabled": self.config.get("enabled", True),
            "detailed_analysis": []
        }
        
        for video_path in video_paths:
            try:
                characteristics = self.analyze_video_characteristics(video_path)
                video_type = characteristics["video_type"]
                
                # 统计各类型数量
                if video_type == "filtered":
                    report["filtered_count"] += 1
                elif video_type == "short":
                    report["short_count"] += 1
                elif video_type == "medium":
                    report["medium_count"] += 1
                else:
                    report["long_count"] += 1
                
                # 添加详细分析
                report["detailed_analysis"].append({
                    "video_path": video_path,
                    "video_name": Path(video_path).name,
                    "characteristics": characteristics
                })
                
            except Exception as e:
                logger.error(f"分析视频失败 {video_path}: {e}")
        
        # 计算优化效果预估
        optimizable_count = report["short_count"]
        report["optimization_coverage"] = optimizable_count / report["total_videos"] if report["total_videos"] > 0 else 0
        
        logger.info(f"📊 优化分析报告: 总计{report['total_videos']}个视频，{optimizable_count}个可优化，{report['filtered_count']}个已过滤")
        
        return report


# 便捷函数
def optimize_video_analysis_params(video_path: str, original_params: Dict[str, Any]) -> Dict[str, Any]:
    """
    便捷函数：优化单个视频的分析参数
    
    Args:
        video_path: 视频文件路径
        original_params: 原始分析参数
        
    Returns:
        优化后的分析参数
    """
    optimizer = ShortVideoOptimizer()
    return optimizer.optimize_analysis_params(video_path, original_params)


def get_video_optimization_report(video_paths: list) -> Dict[str, Any]:
    """
    便捷函数：获取多个视频的优化分析报告
    
    Args:
        video_paths: 视频文件路径列表
        
    Returns:
        优化分析报告
    """
    optimizer = ShortVideoOptimizer()
    return optimizer.get_optimization_report(video_paths) 