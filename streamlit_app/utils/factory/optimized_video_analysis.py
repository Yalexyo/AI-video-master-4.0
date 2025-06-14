#!/usr/bin/env python3
"""
🚀 优化视频分析机制
大幅提升分析效率（用时/token）的智能分析系统
"""

import asyncio
import hashlib
import json
import logging
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import Dict, List, Any, Optional, Callable, Tuple
import threading

logger = logging.getLogger(__name__)


class HighEfficiencyVideoAnalyzer:
    """高效视频分析器"""
    
    def __init__(self):
        self.cache = {}  # 分析结果缓存
        self.cache_lock = threading.Lock()
        self.api_limiter = APIRateLimiter()
        
        # 效率统计
        self.stats = {
            "total_segments": 0,
            "cache_hits": 0,
            "api_calls": 0,
            "total_time": 0,
            "total_tokens": 0
        }
    
    def analyze_segments_optimized(
        self,
        segment_files: List[Path],
        video_id: str,
        strategy: str = "intelligent",
        max_workers: int = 3,
        progress_callback: Optional[Callable] = None
    ) -> Dict[str, Any]:
        """
        🚀 高效批量分析视频片段
        
        优化策略：
        1. 智能预分析分组
        2. 并行处理
        3. 缓存复用
        4. 动态帧率调整
        5. 智能API限流
        """
        start_time = time.time()
        self.stats["total_segments"] = len(segment_files)
        
        if progress_callback:
            progress_callback("🔍 预分析片段特征...")
        
        # 🔧 第一步：智能预分析 - 分组相似片段
        segment_groups = self._preanalyze_and_group_segments(segment_files)
        
        if progress_callback:
            progress_callback(f"📊 分组完成，{len(segment_groups)}个批次")
        
        # 🔧 第二步：检查缓存
        cached_results, uncached_segments = self._check_cache(segment_files)
        
        if cached_results:
            self.stats["cache_hits"] = len(cached_results)
            if progress_callback:
                progress_callback(f"💾 缓存命中 {len(cached_results)} 个片段")
        
        # 🔧 第三步：并行分析未缓存的片段
        analysis_results = []
        if uncached_segments:
            if progress_callback:
                progress_callback(f"🚀 并行分析 {len(uncached_segments)} 个片段...")
            
            analysis_results = self._parallel_analyze_segments(
                uncached_segments, segment_groups, strategy, max_workers, progress_callback
            )
        
        # 🔧 第四步：合并结果
        final_results = cached_results + analysis_results
        
        # 🔧 第五步：更新缓存
        self._update_cache(analysis_results)
        
        # 🔧 第六步：生成效率报告
        total_time = time.time() - start_time
        self.stats["total_time"] = total_time
        
        efficiency_report = self._generate_efficiency_report()
        
        return {
            "results": final_results,
            "efficiency_report": efficiency_report,
            "success": True
        }
    
    def _preanalyze_and_group_segments(self, segment_files: List[Path]) -> Dict[str, List[Path]]:
        """
        🔍 智能预分析：基于文件特征分组相似片段
        相似片段可以使用相同的分析参数，减少重复计算
        """
        groups = {
            "short": [],      # <5秒短片段 - 高帧率
            "medium": [],     # 5-15秒中等片段 - 标准帧率  
            "long": [],       # >15秒长片段 - 低帧率
            "similar": {}     # 按内容相似性分组
        }
        
        for segment_file in segment_files:
            try:
                # 基于文件大小和名称推测时长
                file_size_mb = segment_file.stat().st_size / (1024 * 1024)
                estimated_duration = self._estimate_duration_from_size(file_size_mb)
                
                if estimated_duration < 5:
                    groups["short"].append(segment_file)
                elif estimated_duration < 15:
                    groups["medium"].append(segment_file)
                else:
                    groups["long"].append(segment_file)
                    
            except Exception as e:
                logger.warning(f"预分析失败，使用默认分组: {e}")
                groups["medium"].append(segment_file)
        
        logger.info(f"🔍 预分析完成：短片段{len(groups['short'])}个，中等{len(groups['medium'])}个，长片段{len(groups['long'])}个")
        return groups
    
    def _estimate_duration_from_size(self, size_mb: float) -> float:
        """根据文件大小估算视频时长"""
        # 经验公式：1MB ≈ 30秒的低质量视频 或 5秒的高质量视频
        # 取中间值作为估算
        return size_mb * 10  # 假设1MB≈10秒
    
    def _check_cache(self, segment_files: List[Path]) -> Tuple[List[Dict], List[Path]]:
        """检查缓存，返回已缓存结果和需要分析的片段"""
        cached_results = []
        uncached_segments = []
        
        with self.cache_lock:
            for segment_file in segment_files:
                cache_key = self._get_cache_key(segment_file)
                
                if cache_key in self.cache:
                    cached_result = self.cache[cache_key].copy()
                    cached_result["from_cache"] = True
                    cached_results.append(cached_result)
                else:
                    uncached_segments.append(segment_file)
        
        return cached_results, uncached_segments
    
    def _get_cache_key(self, segment_file: Path) -> str:
        """生成缓存键：基于文件路径和修改时间"""
        try:
            mtime = segment_file.stat().st_mtime
            content = f"{segment_file}_{mtime}"
            return hashlib.md5(content.encode()).hexdigest()
        except Exception:
            return hashlib.md5(str(segment_file).encode()).hexdigest()
    
    def _parallel_analyze_segments(
        self,
        segments: List[Path],
        groups: Dict[str, List[Path]],
        strategy: str,
        max_workers: int,
        progress_callback: Optional[Callable]
    ) -> List[Dict[str, Any]]:
        """🚀 并行分析片段"""
        results = []
        completed_count = 0
        total_count = len(segments)
        
        # 根据分组确定最优分析参数
        analysis_params = self._get_optimal_analysis_params(groups, segments)
        
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            # 提交所有任务
            future_to_segment = {
                executor.submit(
                    self._analyze_single_segment_optimized,
                    segment,
                    analysis_params.get(segment, self._get_default_params()),
                    strategy
                ): segment
                for segment in segments
            }
            
            # 收集结果
            for future in as_completed(future_to_segment):
                segment = future_to_segment[future]
                completed_count += 1
                
                try:
                    result = future.result()
                    if result:
                        results.append(result)
                        self.stats["api_calls"] += 1
                        
                    if progress_callback:
                        progress = (completed_count / total_count) * 100
                        progress_callback(f"🔄 已完成 {completed_count}/{total_count} ({progress:.1f}%)")
                        
                except Exception as e:
                    logger.error(f"分析片段 {segment.name} 失败: {e}")
        
        return results
    
    def _get_optimal_analysis_params(self, groups: Dict, segments: List[Path]) -> Dict[Path, Dict]:
        """🎯 为每个片段确定最优分析参数"""
        params_map = {}
        
        # 🎯 NEW: 导入短视频优化器进行文件过滤
        try:
            from utils.short_video_optimizer import ShortVideoOptimizer
            optimizer = ShortVideoOptimizer()
        except ImportError:
            optimizer = None
        
        for segment in segments:
            # 🎯 NEW: 过滤过小的文件
            if optimizer and not optimizer.should_process_video(str(segment)):
                continue  # 跳过过小的文件
            
            # 🎯 NEW: 获取文件大小进行更精细的优化
            try:
                file_size_mb = segment.stat().st_size / (1024 * 1024)
            except:
                file_size_mb = 0
            
            if segment in groups.get("short", []):
                # 🎯 短视频：根据文件大小进行优化
                params_map[segment] = {
                    "frame_rate": 4.0,
                    "quality_threshold": 0.45,  # 适度降低质量阈值
                    "retry_count": 2
                }
            elif segment in groups.get("long", []):
                # 长片段：低帧率，节省token
                params_map[segment] = {
                    "frame_rate": 1.5,
                    "quality_threshold": 0.6,
                    "retry_count": 1
                }
            else:
                # 中等片段：标准参数
                params_map[segment] = self._get_default_params()
        
        return params_map
    
    def _get_default_params(self) -> Dict:
        """默认分析参数"""
        return {
            "frame_rate": 2.0,
            "quality_threshold": 0.65,
            "retry_count": 1
        }
    
    def _analyze_single_segment_optimized(
        self,
        segment_file: Path,
        params: Dict[str, Any],
        strategy: str
    ) -> Optional[Dict[str, Any]]:
        """🎯 优化的单片段分析"""
        
        # 智能API限流
        with self.api_limiter:
            try:
                if strategy == "qwen_only":
                    return self._analyze_with_qwen_optimized(segment_file, params)
                elif strategy == "intelligent":
                    return self._analyze_with_intelligent_strategy_optimized(segment_file, params)
                else:
                    return self._analyze_with_qwen_optimized(segment_file, params)
                    
            except Exception as e:
                logger.error(f"优化分析失败 {segment_file.name}: {e}")
                return None
    
    def _analyze_with_qwen_optimized(
        self,
        segment_file: Path,
        params: Dict[str, Any]
    ) -> Optional[Dict[str, Any]]:
        """🎯 优化的Qwen分析 - 支持双模型分工和品牌检测"""
        try:
            from modules.ai_analyzers import QwenVideoAnalyzer
            
            analyzer = QwenVideoAnalyzer()
            if not analyzer.is_available():
                return None
            
            # 🎯 使用新版本的双模型分工机制
            result = analyzer.analyze_video_segment(
                video_path=str(segment_file),
                tag_language="中文",
                frame_rate=params["frame_rate"]
            )
            
            if result and result.get("success"):
                # 估算token使用
                estimated_tokens = self._estimate_tokens_used(segment_file, params)
                self.stats["total_tokens"] += estimated_tokens
                
                # 🔧 修复：正确处理字段映射，保持与新版本一致
                return {
                    'file_name': segment_file.name,
                    'file_path': str(segment_file),
                    'file_size': segment_file.stat().st_size / (1024*1024),
                    'model': 'Qwen-VL-Max-Latest',
                    # 🎯 支持新的字段结构
                    'object': result.get('object', result.get('interaction', '')),  # 兼容新的interaction字段
                    'scene': result.get('scene', ''),
                    'emotion': result.get('emotion', ''),
                    'brand_elements': result.get('brand_elements', ''),  # 🔧 关键：不使用默认值'无'
                    'confidence': result.get('confidence', 0.0),
                    'success': True,
                    'analysis_params': params,
                    'estimated_tokens': estimated_tokens,
                    # 🎯 保留分析方法信息
                    'analysis_strategy': result.get('analysis_method', 'Qwen完整分析')
                }
            
            return None
            
        except Exception as e:
            logger.error(f"Qwen优化分析失败: {e}")
            return None
    
    def _analyze_with_intelligent_strategy_optimized(
        self,
        segment_file: Path,
        params: Dict[str, Any]
    ) -> Optional[Dict[str, Any]]:
        """🧠 优化的智能策略分析 - 使用新版本双模型分工机制"""
        
        # 🎯 直接使用QwenVideoAnalyzer的智能策略，它已经包含了双模型分工和品牌检测
        try:
            from modules.ai_analyzers import QwenVideoAnalyzer
            
            analyzer = QwenVideoAnalyzer()
            if not analyzer.is_available():
                return None
            
            # 🎯 使用新版本的智能策略（包含双模型分工和品牌检测）
            result = analyzer.analyze_video_segment(
                video_path=str(segment_file),
                tag_language="中文",
                frame_rate=params["frame_rate"]
            )
            
            if result and result.get("success"):
                # 估算token使用
                estimated_tokens = self._estimate_tokens_used(segment_file, params)
                self.stats["total_tokens"] += estimated_tokens
                
                # 🔧 修复：正确处理字段映射，保持与新版本一致
                return {
                    'file_name': segment_file.name,
                    'file_path': str(segment_file),
                    'file_size': segment_file.stat().st_size / (1024*1024),
                    'model': 'Qwen-VL-Max-Latest',
                    # 🎯 支持新的字段结构
                    'object': result.get('object', result.get('interaction', '')),  # 兼容新的interaction字段
                    'scene': result.get('scene', ''),
                    'emotion': result.get('emotion', ''),
                    'brand_elements': result.get('brand_elements', ''),  # 🔧 关键：不使用默认值'无'
                    'confidence': result.get('confidence', 0.0),
                    'success': True,
                    'analysis_params': params,
                    'estimated_tokens': estimated_tokens,
                    # 🎯 保留分析方法信息
                    'analysis_strategy': result.get('analysis_method', 'Qwen完整分析')
                }
            
            return None
            
        except Exception as e:
            logger.error(f"智能策略优化分析失败: {e}")
            return None
    
    def _is_result_sufficient(self, result: Dict[str, Any]) -> bool:
        """判断分析结果是否充分"""
        empty_count = 0
        check_fields = ['object', 'scene', 'emotion', 'brand_elements']
        
        for field in check_fields:
            value = result.get(field, '')
            if not value or value in ['无', 'N/A', '', 'null']:
                empty_count += 1
        
        return empty_count < 2  # 少于2个空字段视为充分
    
    def _enhance_insufficient_result(self, result: Dict[str, Any]) -> Dict[str, Any]:
        """增强不充分的结果 - 保持空字段为空，不填充无意义占位符"""
        enhanced = result.copy()
        
        # 🔧 重要修复：不再填充无意义的占位符
        # 保持空字段为空，这样在后续分析中更容易识别和处理
        # 占位符对后续分析没有任何作用，反而会干扰结果
        
        # 只标记进行了增强，但不改变内容
        enhanced['enhancement_applied'] = True
        
        # 如果确实需要推断，可以基于文件名、大小等进行简单推断
        # 但目前暂时保持为空更安全
        logger.info("🔧 保持不充分字段为空，避免无意义占位符干扰分析")
        return enhanced
    
    def _estimate_tokens_used(self, segment_file: Path, params: Dict) -> int:
        """估算token使用量"""
        # 基于帧率和文件大小估算
        frame_rate = params.get("frame_rate", 2.0)
        file_size_mb = segment_file.stat().st_size / (1024 * 1024)
        estimated_duration = self._estimate_duration_from_size(file_size_mb)
        
        # 每帧大约消耗100-200个token
        estimated_frames = frame_rate * estimated_duration
        estimated_tokens = int(estimated_frames * 150)  # 平均每帧150 token
        
        return estimated_tokens
    
    def _update_cache(self, results: List[Dict[str, Any]]):
        """更新分析结果缓存"""
        with self.cache_lock:
            for result in results:
                if result and result.get('file_path'):
                    segment_file = Path(result['file_path'])
                    cache_key = self._get_cache_key(segment_file)
                    
                    # 移除临时字段后缓存
                    cache_result = result.copy()
                    cache_result.pop('analysis_params', None)
                    cache_result.pop('estimated_tokens', None)
                    
                    self.cache[cache_key] = cache_result
    
    def _generate_efficiency_report(self) -> Dict[str, Any]:
        """生成效率报告"""
        cache_hit_rate = (self.stats["cache_hits"] / self.stats["total_segments"]) * 100 if self.stats["total_segments"] > 0 else 0
        avg_time_per_segment = self.stats["total_time"] / self.stats["total_segments"] if self.stats["total_segments"] > 0 else 0
        avg_tokens_per_segment = self.stats["total_tokens"] / self.stats["api_calls"] if self.stats["api_calls"] > 0 else 0
        
        return {
            "total_segments": self.stats["total_segments"],
            "cache_hits": self.stats["cache_hits"],
            "cache_hit_rate": f"{cache_hit_rate:.1f}%",
            "api_calls": self.stats["api_calls"],
            "total_time": f"{self.stats['total_time']:.2f}s",
            "avg_time_per_segment": f"{avg_time_per_segment:.2f}s",
            "total_tokens_estimated": self.stats["total_tokens"],
            "avg_tokens_per_segment": f"{avg_tokens_per_segment:.0f}",
            "efficiency_score": self._calculate_efficiency_score()
        }
    
    def _calculate_efficiency_score(self) -> float:
        """计算效率分数 (0-100)"""
        # 基于缓存命中率和处理速度计算
        cache_factor = (self.stats["cache_hits"] / self.stats["total_segments"]) * 40 if self.stats["total_segments"] > 0 else 0
        speed_factor = min(60, (1.0 / (self.stats["total_time"] / self.stats["total_segments"])) * 10) if self.stats["total_segments"] > 0 else 0
        
        return min(100, cache_factor + speed_factor)


class APIRateLimiter:
    """智能API限流器"""
    
    def __init__(self, initial_delay: float = 0.2):
        self.delay = initial_delay
        self.last_call_time = 0
        self.consecutive_successes = 0
        self.consecutive_failures = 0
        self.lock = threading.Lock()
    
    def __enter__(self):
        with self.lock:
            current_time = time.time()
            time_since_last_call = current_time - self.last_call_time
            
            if time_since_last_call < self.delay:
                sleep_time = self.delay - time_since_last_call
                time.sleep(sleep_time)
            
            self.last_call_time = time.time()
            return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        # 根据成功/失败调整延时
        if exc_type is None:
            self.consecutive_successes += 1
            self.consecutive_failures = 0
            
            # 连续成功时减少延时
            if self.consecutive_successes > 5:
                self.delay = max(0.1, self.delay * 0.9)
        else:
            self.consecutive_failures += 1
            self.consecutive_successes = 0
            
            # 连续失败时增加延时
            if self.consecutive_failures > 2:
                self.delay = min(2.0, self.delay * 1.5)


# 便捷接口函数
def analyze_segments_with_high_efficiency(
    segment_files: List[Path],
    video_id: str,
    strategy: str = "intelligent",
    max_workers: int = 3,
    progress_callback: Optional[Callable] = None
) -> Dict[str, Any]:
    """
    🚀 高效视频片段分析入口函数
    
    Args:
        segment_files: 片段文件列表
        video_id: 视频ID
        strategy: 分析策略 ("qwen_only", "intelligent")
        max_workers: 最大并行工作线程数
        progress_callback: 进度回调函数
        
    Returns:
        包含分析结果和效率报告的字典
    """
    analyzer = HighEfficiencyVideoAnalyzer()
    return analyzer.analyze_segments_optimized(
        segment_files=segment_files,
        video_id=video_id,
        strategy=strategy,
        max_workers=max_workers,
        progress_callback=progress_callback
    ) 