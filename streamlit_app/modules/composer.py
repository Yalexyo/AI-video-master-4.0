"""
视频合成模块
用于按照25:28:32:15的时长比例从四大模块中选择高质量片段，并进行视频拼接
"""

import os
import subprocess
import tempfile
import logging
import datetime
from typing import List, Dict, Any, Optional, Tuple
import json
from pathlib import Path
from enum import Enum
import random
import difflib  # 添加用于计算文本相似度
import time  # 添加时间模块

logger = logging.getLogger(__name__)

class SelectionMode(Enum):
    """片段选择模式枚举"""
    OPTIMAL = "optimal"  # 最优化选择
    MANUAL = "manual"    # 手动选择

class VideoComposer:
    """视频合成器"""
    
    def __init__(self):
        """初始化合成器"""
        self.four_modules = ["痛点", "解决方案导入", "卖点·成分&配方", "促销机制"]
        self.default_ratios = [25, 28, 32, 15]  # 默认时长比例
    
    def _get_max_segments_per_module(self) -> int:
        """从配置文件读取每个模块的最大片段数限制"""
        try:
            import json
            config_file = "config/matching_rules.json"
            with open(config_file, 'r', encoding='utf-8') as f:
                config = json.load(f)
            max_segments_limit = config.get("GLOBAL_SETTINGS", {}).get("max_segments_per_module", 3)
            return max_segments_limit
        except Exception as e:
            logger.warning(f"无法读取配置文件，使用默认限制3个片段: {e}")
            return 3
        
    def select_segments_by_duration(
        self, 
        mapped_segments: List[Dict[str, Any]], 
        target_ratios: List[int] = None,
        total_target_duration: float = 100.0,
        selection_mode: SelectionMode = SelectionMode.OPTIMAL,
        randomness_level: str = "适中",
        random_seed: Optional[int] = None,
        manual_selections: Optional[Dict[str, List[str]]] = None
    ) -> Dict[str, Any]:
        """
        按时长比例精确选择片段
        
        Args:
            mapped_segments: 映射后的片段列表
            target_ratios: 目标时长比例 [痛点, 解决方案, 买点配方, 促销]
            total_target_duration: 总目标时长（秒）
            selection_mode: 选择模式
            randomness_level: 随机强度参数 ("保守", "适中", "激进")
            random_seed: 随机种子
            manual_selections: 手动选择的片段ID字典
            
        Returns:
            Dict: 选择结果
        """
        # 🎲 设置随机种子（如果指定）
        if random_seed is not None:
            random.seed(random_seed)
            logger.info(f"设置随机种子: {random_seed}")
        
        if target_ratios is None:
            target_ratios = self.default_ratios
            
        # 计算各模块的目标时长
        total_ratio = sum(target_ratios)
        target_durations = [
            (ratio / total_ratio) * total_target_duration 
            for ratio in target_ratios
        ]
        
        selection_result = {
            "selected_segments": {},
            "total_duration": 0,
            "target_duration": total_target_duration,
            "module_details": {}
        }
        
        # 为每个模块选择片段
        for i, module in enumerate(self.four_modules):
            target_duration = target_durations[i]
            
            # 🔧 添加调试信息：统计该模块的片段情况
            module_segments = [s for s in mapped_segments if s.get('category') == module]
            valid_duration_segments = [s for s in module_segments if s.get('duration', 0) > 0]
            zero_duration_segments = [s for s in module_segments if s.get('duration', 0) == 0]
            
            logger.info(f"🔍 模块 {module} 片段统计:")
            logger.info(f"   总片段数: {len(module_segments)}")
            logger.info(f"   有效时长片段: {len(valid_duration_segments)} (duration > 0)")
            logger.info(f"   零时长片段: {len(zero_duration_segments)} (duration = 0)")
            
            if valid_duration_segments:
                total_available_duration = sum(s.get('duration', 0) for s in valid_duration_segments)
                logger.info(f"   可用总时长: {total_available_duration:.2f}s")
                logger.info(f"   目标时长: {target_duration:.2f}s")
                logger.info(f"   理论覆盖率: {min(100, total_available_duration/target_duration*100):.1f}%")
            
            # 🎯 根据选择模式处理
            if selection_mode == SelectionMode.MANUAL:
                # 手动选择模式（限制最大片段数）
                selected = self._select_manual_segments(module_segments, module, manual_selections or {})
                
                # 🔧 从配置文件读取最大片段数限制
                max_segments_limit = self._get_max_segments_per_module()
                
                if len(selected) > max_segments_limit:  # 🔧 使用配置的限制
                    selected = selected[:max_segments_limit]
                    logger.warning(f"⚠️ 手动选择片段数超限，截取前{max_segments_limit}个片段")
                    total_duration = sum(s.get('duration', 0) for s in selected)
                logger.info(f"👆 使用手动选择，模块 {module}: {len(selected)} 个片段（最多{max_segments_limit}个）")
                
            else:
                # 筛选该类别的片段并按质量排序
                candidates = [
                    s for s in mapped_segments 
                    if s.get('category') == module and s.get('duration', 0) > 0
                ]
                
                # 🚫 关键修复：在选择前先进行全局过滤检查
                from streamlit_app.modules.mapper import VideoSegmentMapper
                mapper = VideoSegmentMapper()
                
                # 过滤掉包含排除关键词的片段
                filtered_candidates = []
                for candidate in candidates:
                    all_tags = candidate.get('all_tags', [])
                    if all_tags:
                        tags_text = " ".join(all_tags).lower()
                        if not mapper._is_excluded_by_negative_keywords(tags_text):
                            filtered_candidates.append(candidate)
                        else:
                            logger.warning(f"🚫 片段被全局排除: {candidate.get('file_name', 'unknown')} - 标签: {all_tags}")
                    else:
                        # 如果没有标签信息，保留片段
                        filtered_candidates.append(candidate)
                
                candidates = filtered_candidates
                logger.info(f"🔍 模块 {module} 过滤后剩余候选片段: {len(candidates)} 个")
                
                # 🔧 如果没有有效时长的片段，尝试使用零时长片段（赋予默认时长）
                if not candidates and zero_duration_segments:
                    logger.warning(f"⚠️ 模块 {module} 没有有效时长片段，使用零时长片段并赋予默认时长")
                    candidates = []
                    for segment in zero_duration_segments:
                        # 创建片段副本并赋予默认时长
                        segment_copy = segment.copy()
                        segment_copy['duration'] = 3.0  # 默认3秒
                        segment_copy['is_default_duration'] = True
                        candidates.append(segment_copy)
                        logger.debug(f"   为片段 {segment.get('file_name', 'unknown')} 赋予默认时长3秒")
                
                # 按综合质量分排序（质量分 * 置信度）
                candidates.sort(
                    key=lambda x: x.get('combined_quality', 0), 
                    reverse=True
                )
                
                logger.info(f"🎯 模块 {module} 候选片段: {len(candidates)} 个")
                
                # 🚀 选择算法：根据模式选择不同策略
                selected = []
                total_duration = 0
                
                if not candidates:
                    logger.error(f"❌ 模块 {module} 没有可用片段")
                else:
                    # 策略选择：最优化选择
                    total_available = sum(s.get('duration', 0) for s in candidates)
                    
                    # 🔧 从配置文件读取最大片段数限制
                    max_segments_limit = self._get_max_segments_per_module()
                    
                    if total_available >= target_duration:
                        # 最优化选择：使用背包算法找最优组合
                        selected = self._select_optimal_segments(candidates, target_duration, max_segments=max_segments_limit)
                        total_duration = sum(s.get('duration', 0) for s in selected)
                        logger.info(f"✅ 使用最优选择算法，覆盖率: {total_duration/target_duration*100:.1f}%")
                    else:
                        # 片段不足，限制最多到配置的片段数
                        selected = candidates[:max_segments_limit]  # 使用配置的最大片段数
                        total_duration = sum(s.get('duration', 0) for s in selected)
                        logger.warning(f"⚠️ 片段时长不足，使用前{len(selected)}个片段（最多{max_segments_limit}个），覆盖率: {total_duration/target_duration*100:.1f}%")
            
            # 保存选择结果
            selection_result["selected_segments"][module] = selected
            selection_result["module_details"][module] = {
                "target_duration": target_duration,
                "actual_duration": total_duration,
                "segment_count": len(selected),
                "available_segments": len(valid_duration_segments),  # 🔧 添加可用片段数
                "total_module_segments": len(module_segments),  # 🔧 添加模块总片段数
                "avg_quality": (
                    sum(s.get('combined_quality', 0) for s in selected) / len(selected)
                    if selected else 0
                ),
                "coverage_ratio": total_duration / target_duration if target_duration > 0 else 0
            }
            
            selection_result["total_duration"] += total_duration
            
            logger.info(
                f"✅ 模块 {module}: 目标{target_duration:.1f}s, 实际{total_duration:.1f}s, "
                f"片段数{len(selected)}/{len(valid_duration_segments)}, 覆盖率{total_duration/target_duration*100:.1f}%"
            )
        
        return selection_result
    
    def _select_optimal_segments(self, candidates: List[Dict], target_duration: float, max_segments: int = 3) -> List[Dict]:
        """
        使用改进的背包算法选择最优片段组合
        
        Args:
            candidates: 候选片段列表 (已按质量排序)
            target_duration: 目标时长
            max_segments: 最大片段数限制
            
        Returns:
            List[Dict]: 选择的最优片段组合
        """
        # 策略：优先达到100%覆盖率，在此基础上优化质量
        
        # 方法1：贪心算法 - 按时长/质量比选择
        candidates_with_ratio = []
        for segment in candidates:
            duration = segment.get('duration', 0)
            quality = segment.get('combined_quality', 0)
            if duration > 0:
                # 时长效率 = 质量分 / 时长，优先选择高效片段
                efficiency = quality / duration
                candidates_with_ratio.append((segment, duration, quality, efficiency))
        
        # 按效率排序
        candidates_with_ratio.sort(key=lambda x: x[3], reverse=True)
        
        selected = []
        total_duration = 0
        
        # 第一轮：贪心选择，优先达到目标时长（限制最大片段数）
        for segment, duration, quality, efficiency in candidates_with_ratio:
            if len(selected) >= max_segments:  # 🔧 片段数量限制
                logger.info(f"🔢 达到最大片段数限制: {max_segments}")
                break
            if total_duration < target_duration:
                selected.append(segment)
                total_duration += duration
            elif total_duration >= target_duration * 0.95:  # 已达到95%以上
                break
        
        # 第二轮：如果还未达到100%，继续添加片段（但要检查片段数限制）
        if total_duration < target_duration:
            remaining = [item for item in candidates_with_ratio 
                        if item[0] not in selected]
            
            # 按时长降序排序，优先选择较长的片段快速达标
            remaining.sort(key=lambda x: x[1], reverse=True)
            
            for segment, duration, quality, efficiency in remaining:
                # 🔧 关键修复：检查片段数量限制
                if len(selected) >= max_segments:
                    logger.info(f"🔢 第二轮达到最大片段数限制: {max_segments}")
                    break
                    
                if total_duration < target_duration * 1.2:  # 最多超出20%
                    selected.append(segment)
                    total_duration += duration
                    
                    if total_duration >= target_duration:  # 达到目标即停止
                        break
        
        return selected
    
    def _select_random_segments(self, candidates: List[Dict], target_duration: float, randomness_level: str) -> List[Dict]:
        """
        使用随机算法选择片段组合
        
        Args:
            candidates: 候选片段列表
            target_duration: 目标时长
            randomness_level: 随机强度参数 ("保守", "适中", "激进")
            
        Returns:
            List[Dict]: 选择的随机片段组合
        """
        try:
            # 🎲 根据随机强度调整候选片段
            if randomness_level == "保守":
                # 保守模式：优先考虑高质量片段，但顺序随机
                quality_threshold = 0.6  # 只考虑质量分>0.6的片段
                filtered_candidates = [c for c in candidates if c.get('combined_quality', 0) >= quality_threshold]
                if not filtered_candidates:  # 如果没有高质量片段，降低标准
                    filtered_candidates = candidates
                working_candidates = filtered_candidates.copy()
                random.shuffle(working_candidates)
                logger.debug(f"保守模式：筛选出{len(working_candidates)}/{len(candidates)}个高质量片段")
                
            elif randomness_level == "激进":
                # 激进模式：完全随机，忽略质量分
                working_candidates = candidates.copy()
                random.shuffle(working_candidates)
                # 进一步打乱，包括低质量片段
                logger.debug(f"激进模式：完全随机选择，{len(working_candidates)}个候选片段")
                
            else:  # 适中模式（默认）
                # 适中模式：平衡质量和随机性
                working_candidates = candidates.copy()
                random.shuffle(working_candidates)
                logger.debug(f"适中模式：平衡随机选择，{len(working_candidates)}个候选片段")
            
            # 随机打乱候选片段
            shuffled_candidates = working_candidates
            
            selected = []
            total_duration = 0
            
            # 🎲 根据随机强度调整选择策略
            if randomness_level == "保守":
                # 保守策略：更倾向于达到精确覆盖率
                target_tolerance = 1.1  # 只允许10%超出
                stop_probability = 0.95  # 95%概率在达到目标后停止
            elif randomness_level == "激进":
                # 激进策略：更大的变化性
                target_tolerance = 1.3  # 允许30%超出
                stop_probability = 0.7   # 70%概率在达到目标后停止
            else:  # 适中
                target_tolerance = 1.2   # 允许20%超出
                stop_probability = 0.9   # 90%概率在达到目标后停止
            
            # 🔧 从配置文件读取最大片段数限制
            max_segments_limit = self._get_max_segments_per_module()
            
            # 策略1：随机贪心 - 随机顺序添加片段直到达到目标
            for segment in shuffled_candidates:
                # 🔧 检查片段数量限制
                if len(selected) >= max_segments_limit:
                    logger.info(f"🔢 随机选择达到最大片段数限制: {max_segments_limit}")
                    break
                    
                segment_duration = segment.get('duration', 0)
                
                # 检查添加此片段是否会严重超出目标
                if total_duration + segment_duration <= target_duration * target_tolerance:
                    selected.append(segment)
                    total_duration += segment_duration
                    
                    # 如果已经达到目标的95%以上，根据随机强度决定是否停止
                    if total_duration >= target_duration * 0.95:
                        if random.random() < stop_probability:
                            break
            
            # 策略2：如果还未达到目标，随机从剩余片段中补充
            if total_duration < target_duration:
                remaining = [s for s in shuffled_candidates if s not in selected]
                
                # 随机尝试添加更多片段
                for segment in remaining:
                    # 🔧 检查片段数量限制
                    if len(selected) >= max_segments_limit:
                        logger.info(f"🔢 随机补充达到最大片段数限制: {max_segments_limit}")
                        break
                        
                    segment_duration = segment.get('duration', 0)
                    if total_duration + segment_duration <= target_duration * target_tolerance:
                        selected.append(segment)
                        total_duration += segment_duration
                        
                        if total_duration >= target_duration:
                            break
            
            # 策略3：极端情况下的随机替换优化（仅在保守和适中模式下）
            if randomness_level != "激进" and total_duration < target_duration * 0.8:
                # 如果覆盖率太低，尝试随机替换一些短片段为长片段
                self._random_replace_for_better_coverage(selected, candidates, target_duration)
            
            # 保存选择结果
            logger.debug(f"随机选择完成: 选择了{len(selected)}个片段，总时长{total_duration:.2f}s")
            return selected
            
        except Exception as e:
            logger.error(f"随机选择算法异常: {e}")
            # 异常情况下回退到简单随机选择
            return self._fallback_random_selection(candidates, target_duration)
    
    def _random_replace_for_better_coverage(
        self, 
        selected: List[Dict], 
        all_candidates: List[Dict], 
        target_duration: float
    ) -> None:
        """
        随机替换策略，提高覆盖率
        
        Args:
            selected: 已选择的片段列表（会被修改）
            all_candidates: 所有候选片段
            target_duration: 目标时长
        """
        try:
            current_duration = sum(s.get('duration', 0) for s in selected)
            need_duration = target_duration - current_duration
            
            if need_duration <= 0:
                return
            
            # 找出未选择的较长片段
            unselected = [s for s in all_candidates if s not in selected]
            longer_segments = [s for s in unselected if s.get('duration', 0) >= need_duration * 0.5]
            
            if longer_segments and selected:
                # 随机选择一个较长片段
                new_segment = random.choice(longer_segments)
                # 随机移除一个较短片段
                shorter_selected = [s for s in selected if s.get('duration', 0) <= need_duration * 0.8]
                
                if shorter_selected:
                    old_segment = random.choice(shorter_selected)
                    selected.remove(old_segment)
                    selected.append(new_segment)
                    logger.debug(f"随机替换: {old_segment.get('file_name')} -> {new_segment.get('file_name')}")
        
        except Exception as e:
            logger.error(f"随机替换策略异常: {e}")
    
    def _fallback_random_selection(self, candidates: List[Dict], target_duration: float) -> List[Dict]:
        """
        备用随机选择策略（简单版本）
        
        Args:
            candidates: 候选片段列表
            target_duration: 目标时长
            
        Returns:
            List[Dict]: 选择的片段组合
        """
        try:
            # 🔧 从配置文件读取最大片段数限制
            max_segments_limit = self._get_max_segments_per_module()
            
            # 简单随机选择：随机选择片段直到接近目标时长
            shuffled = candidates.copy()
            random.shuffle(shuffled)
            
            selected = []
            total_duration = 0
            
            for segment in shuffled:
                # 🔧 检查片段数量限制
                if len(selected) >= max_segments_limit:
                    logger.info(f"🔢 备用选择达到最大片段数限制: {max_segments_limit}")
                    break
                    
                duration = segment.get('duration', 0)
                if total_duration + duration <= target_duration * 1.15:  # 允许15%超出
                    selected.append(segment)
                    total_duration += duration
                    
                    if total_duration >= target_duration * 0.9:  # 达到90%即可
                        break
            
            return selected
        
        except Exception as e:
            logger.error(f"备用随机选择异常: {e}")
            # 最后兜底：返回前几个片段，但要遵循配置限制
            max_segments_limit = self._get_max_segments_per_module()
            return candidates[:min(max_segments_limit, len(candidates))]
    
    def create_ffmpeg_concat_file(self, selected_segments: Dict[str, List[Dict]], temp_dir: str) -> str:
        """
        创建FFmpeg concat文件
        
        Args:
            selected_segments: 选择的片段.
                               Can be Dict[module_name, List[segment_dict]] or
                               Dict[\"script_matched\", List[segment_dict]].
            temp_dir: 临时目录
            
        Returns:
            str: concat文件路径
        """
        concat_file_path = os.path.join(temp_dir, "concat_list.txt")
        
        all_segments = []
        # 🔧 FIX: Handle different structures of selected_segments
        if "script_matched" in selected_segments:
            all_segments = selected_segments["script_matched"]
            logger.info(f"使用脚本匹配的 {len(all_segments)} 个片段创建concat文件")
        elif any(module in selected_segments for module in self.four_modules):
            for module in self.four_modules:
                module_segments = selected_segments.get(module, [])
                # 在模块内按质量分排序
                module_segments.sort(key=lambda x: x.get('combined_quality', 0), reverse=True)
                all_segments.extend(module_segments)
            logger.info(f"使用四大模块的 {len(all_segments)} 个片段创建concat文件")
        else:
            logger.warning(f"Unexpected structure for selected_segments or empty in create_ffmpeg_concat_file: {list(selected_segments.keys())}")
            # Attempt to flatten if it's a dict of lists
            for key in selected_segments:
                if isinstance(selected_segments[key], list):
                    all_segments.extend(selected_segments[key])

        valid_segments = 0
        invalid_segments = 0
        
        with open(concat_file_path, 'w', encoding='utf-8') as f:
            for segment in all_segments:
                file_path = segment.get('file_path') or segment.get('video_path') or segment.get('path')
                
                # 🔧 改进：更强的路径构建逻辑
                if not file_path:
                    video_id = segment.get('video_id', '')
                    file_name = segment.get('file_name', '')
                    if video_id and file_name:
                        file_path = f"data/output/google_video/video_pool/{video_id}/{file_name}"
                    elif file_name:
                        # 尝试多个可能的路径
                        possible_paths = [
                            f"data/output/google_video/video_pool/{file_name}",
                            f"data/temp/uploads/{file_name}",
                            f"data/temp/google_cloud/{file_name}",
                            f"data/output/google_video/{file_name}"
                        ]
                        for possible_path in possible_paths:
                            if os.path.exists(possible_path):
                                file_path = possible_path
                                break
                
                # 🔧 调试：检查文件路径
                logger.debug(f"检查片段文件: {segment.get('file_name')} -> {file_path}")
                
                if file_path and os.path.exists(file_path):
                    # 🔧 额外验证：确保文件不是空的
                    try:
                        file_size = os.path.getsize(file_path)
                        if file_size > 0:
                            abs_path = os.path.abspath(file_path)
                            # 🔧 简化路径转义：只需要处理单引号即可
                            escaped_path = abs_path.replace("'", "'\"'\"'")
                            f.write(f"file '{escaped_path}'\n")
                            valid_segments += 1
                            logger.debug(f"✅ 添加有效片段: {abs_path} (大小: {file_size} bytes)")
                        else:
                            invalid_segments += 1
                            logger.warning(f"⚠️ 片段文件为空: {file_path}")
                    except Exception as e:
                        invalid_segments += 1
                        logger.warning(f"❌ 检查文件大小失败: {file_path} - {e}")
                else:
                    invalid_segments += 1
                    logger.warning(f"❌ 片段文件不存在: {file_path}")
                    # 🔧 调试：显示片段的详细信息
                    logger.debug(f"   片段详情: file_name={segment.get('file_name')}, video_id={segment.get('video_id')}")
        
        logger.info(f"创建concat文件: {concat_file_path}, 包含 {valid_segments}/{len(all_segments)} 个有效片段 ({invalid_segments} 个无效)")
        
        # 🔧 检查concat文件是否为空
        if valid_segments == 0:
            logger.error("❌ Concat文件为空！没有找到任何有效的视频片段文件")
            # 显示所有段的详细信息用于调试
            logger.error("🔍 调试信息 - 所有片段详情:")
            for i, segment in enumerate(all_segments[:5]):  # 只显示前5个
                logger.error(f"  片段{i+1}: {segment}")
            
        if logger.isEnabledFor(logging.DEBUG):
            try:
                with open(concat_file_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                    logger.debug(f"Concat文件内容预览: {content[:200]}...")
            except Exception as e:
                logger.debug(f"无法读取concat文件: {e}")
        
        return concat_file_path
    
    def compose_video_with_ffmpeg(
        self, 
        selected_segments: Dict[str, List[Dict]], 
        output_path: str,
        resolution: str = "1080x1920",
        bitrate: str = "2M",
        fps: int = 30
    ) -> Dict[str, Any]:
        """
        使用FFmpeg拼接视频（改进版，防止变速和静止画面）
        
        Args:
            selected_segments: 选择的片段
            output_path: 输出文件路径
            resolution: 输出分辨率
            bitrate: 输出比特率
            fps: 输出帧率
            
        Returns:
            Dict: 合成结果
        """
        result = {
            "success": False,
            "output_path": output_path,
            "error": None,
            "duration": 0,
            "segment_count": 0,
            "compatibility_analysis": None
        }
        
        try:
            # 创建临时目录
            with tempfile.TemporaryDirectory() as temp_dir:
                # 🔧 第1步：兼容性分析
                logger.info("🔍 步骤1: 分析视频片段兼容性...")
                print("🔍 步骤1: 分析视频片段兼容性...")
                compatibility = self.analyze_segments_compatibility(selected_segments)
                result["compatibility_analysis"] = compatibility
                
                if compatibility["segments_analyzed"] == 0:
                    result["error"] = "没有找到有效的视频片段"
                    return result
                
                # 🔧 第2步：创建标准化concat文件
                logger.info("📝 步骤2: 创建标准化concat文件...")
                print("📝 步骤2: 创建标准化concat文件...")
                concat_file = self.create_standardized_ffmpeg_concat_file(
                    selected_segments, temp_dir, fps, resolution
                )
                
                # 检查concat文件是否有内容
                if not os.path.exists(concat_file) or os.path.getsize(concat_file) == 0:
                    result["error"] = "没有有效的视频片段可供拼接"
                    logger.error("Concat文件为空或不存在")
                    return result
                
                # 检查concat文件内容
                with open(concat_file, 'r', encoding='utf-8') as f:
                    lines = f.readlines()
                    valid_lines = [line for line in lines if line.strip().startswith('file')]
                    if not valid_lines:
                        result["error"] = "Concat文件中没有有效的视频文件路径"
                        logger.error("Concat文件中没有有效的file行")
                        return result
                    logger.info(f"Concat文件包含 {len(valid_lines)} 个有效文件路径")
                
                # 确保输出目录存在
                os.makedirs(os.path.dirname(output_path), exist_ok=True)
                
                # 🔧 第3步：构建改进的FFmpeg命令
                logger.info("🎬 步骤3: 开始FFmpeg视频拼接...")
                print("🎬 步骤3: 开始FFmpeg视频拼接...")
                
                # 🔧 优化的FFmpeg参数，专门解决音视频同步问题
                ffmpeg_cmd = [
                    'ffmpeg',
                    '-f', 'concat',
                    '-safe', '0',
                    '-i', concat_file,
                    
                    # 🔧 优化的视频编码参数
                    '-c:v', 'libx264',           # 视频编码器
                    '-preset', 'medium',         # 编码预设
                    '-crf', '23',                # 恒定质量因子
                    '-s', resolution,            # 输出分辨率
                    '-pix_fmt', 'yuv420p',       # 像素格式
                    
                    # 🔧 优化的时间戳和同步处理（移除冲突参数）
                    '-avoid_negative_ts', 'make_zero',  # 避免负时间戳
                    '-fps_mode', 'vfr',          # 🔧 使用新的fps_mode参数替代deprecated的-vsync
                    '-async', '1',               # 音频同步
                    
                    # 🔧 优化的格式和性能参数
                    '-movflags', '+faststart',   # 快速启动
                    '-max_muxing_queue_size', '1024',  # 增大混合队列
                    '-threads', '0',             # 使用所有可用线程
                    
                    '-y',                        # 覆盖输出文件
                    output_path
                ]
                
                # 🔧 音频处理：检查第一个文件是否有音频
                try:
                    first_file = valid_lines[0].split("'")[1] if valid_lines else ""
                    if first_file and os.path.exists(first_file):
                        probe_cmd = ['ffprobe', '-v', 'quiet', '-select_streams', 'a', '-show_streams', first_file]
                        probe_result = subprocess.run(probe_cmd, capture_output=True, text=True, timeout=10)
                        if probe_result.returncode == 0 and probe_result.stdout.strip():
                            # 有音频流，添加音频处理参数
                            audio_params = [
                                '-c:a', 'aac',           # 音频编码器
                                '-b:a', '128k',          # 音频比特率
                                '-ar', '44100',          # 音频采样率
                                '-ac', '2'               # 音频声道数（立体声）
                            ]
                            # 使用列表拼接而不是插入，避免位置错误
                            ffmpeg_cmd = ffmpeg_cmd[:-2] + audio_params + ffmpeg_cmd[-2:]
                            logger.info("✅ 检测到音频流，启用音频编码")
                        else:
                            ffmpeg_cmd.insert(-2, '-an')  # 无音频
                            logger.info("🔇 未检测到音频流，仅编码视频")
                except Exception as e:
                    logger.warning(f"检查音频流失败，使用默认设置: {e}")
                    # 使用默认音频设置
                    default_audio = ['-c:a', 'aac']
                    ffmpeg_cmd = ffmpeg_cmd[:-2] + default_audio + ffmpeg_cmd[-2:]
                
                logger.info(f"FFmpeg命令: {' '.join(ffmpeg_cmd)}")
                print(f"🎬 FFmpeg命令: {' '.join(ffmpeg_cmd)}")
                
                # 🔧 第4步：执行FFmpeg合成
                logger.info("⚙️ 步骤4: 执行视频合成...")
                print("⚙️ 步骤4: 执行视频合成...")
                
                process = subprocess.run(
                    ffmpeg_cmd,
                    capture_output=True,
                    text=True,
                    timeout=600  # 10分钟超时
                )
                
                # 打印FFmpeg输出用于调试
                if process.stdout:
                    logger.debug(f"FFmpeg stdout: {process.stdout}")
                if process.stderr:
                    logger.debug(f"FFmpeg stderr: {process.stderr}")
                    # 只在错误时打印stderr
                    if process.returncode != 0:
                        print(f"📝 FFmpeg stderr: {process.stderr}")
                
                if process.returncode == 0:
                    # 🎉 成功
                    result["success"] = True
                    
                    # 获取输出视频信息
                    if os.path.exists(output_path):
                        video_info = self.get_video_info(output_path)
                        result["duration"] = video_info.get("duration", 0)
                        result["file_size"] = os.path.getsize(output_path)
                        
                        # 统计片段数量
                        result["segment_count"] = sum(
                            len(segments) for segments in selected_segments.values()
                        )
                        
                        # 🔧 质量验证
                        output_info = self.get_detailed_video_info(output_path)
                        result["output_quality"] = {
                            "fps": output_info.get("fps", 0),
                            "resolution": f"{output_info.get('width', 0)}x{output_info.get('height', 0)}",
                            "codec": output_info.get("video_codec", ""),
                            "has_audio": output_info.get("has_audio", False)
                        }
                        
                        logger.info(
                            f"✅ 视频拼接成功: {output_path}, "
                            f"时长: {result['duration']:.2f}s, "
                            f"片段数: {result['segment_count']}, "
                            f"帧率: {output_info.get('fps', 0):.1f}fps"
                        )
                        print(f"✅ 视频拼接成功！时长: {result['duration']:.2f}s, 片段数: {result['segment_count']}")
                    else:
                        result["success"] = False
                        result["error"] = "输出文件未生成"
                        
                else:
                    # ❌ 失败
                    result["error"] = f"FFmpeg执行失败 (返回码: {process.returncode}): {process.stderr}"
                    logger.error(f"FFmpeg错误 (返回码: {process.returncode}): {process.stderr}")
                    print(f"❌ FFmpeg失败: {process.stderr}")
            
        except subprocess.TimeoutExpired:
            result["error"] = "FFmpeg执行超时（可能由于片段过多或技术参数差异过大）"
            logger.error("FFmpeg执行超时")
        except Exception as e:
            result["error"] = f"视频拼接异常: {str(e)}"
            logger.error(f"视频拼接异常: {e}")
        
        return result
    
    def get_video_info(self, video_path: str) -> Dict[str, Any]:
        """
        获取视频信息
        
        Args:
            video_path: 视频文件路径
            
        Returns:
            Dict: 视频信息
        """
        try:
            cmd = [
                'ffprobe', '-v', 'quiet', '-print_format', 'json',
                '-show_format', '-show_streams', video_path
            ]
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
            
            if result.returncode == 0:
                data = json.loads(result.stdout)
                format_info = data.get('format', {})
                
                return {
                    "duration": float(format_info.get('duration', 0)),
                    "size": int(format_info.get('size', 0)),
                    "bit_rate": int(format_info.get('bit_rate', 0)),
                    "format_name": format_info.get('format_name', '')
                }
        except Exception as e:
            logger.error(f"获取视频信息失败: {e}")
        
        return {"duration": 0, "size": 0, "bit_rate": 0, "format_name": ""}
    
    def align_with_srt(
        self, 
        video_path: str, 
        srt_path: str, 
        max_adjustment: float = 0.02
    ) -> Dict[str, Any]:
        """
        将视频与SRT字幕对齐（预留功能）
        
        Args:
            video_path: 视频文件路径
            srt_path: SRT字幕文件路径
            max_adjustment: 最大调整幅度（2%）
            
        Returns:
            Dict: 对齐结果
        """
        # TODO: 实现SRT对齐逻辑
        # 1. 解析SRT文件获取时间戳
        # 2. 计算视频时长与SRT时长差异
        # 3. 在2%范围内调整视频播放速度
        
        logger.info(f"SRT对齐功能待实现: {video_path} + {srt_path}")
        
        return {
            "success": True,
            "adjustment_ratio": 1.0,
            "message": "SRT对齐功能待实现"
        }
    
    def generate_composition_report(
        self, 
        selection_result: Dict[str, Any], 
        composition_result: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        生成合成报告
        
        Args:
            selection_result: 片段选择结果
            composition_result: 视频合成结果
            
        Returns:
            Dict: 合成报告
        """
        report = {
            "timestamp": datetime.datetime.now().isoformat(),
            "success": composition_result.get("success", False),
            "summary": {
                "total_segments": selection_result.get("total_duration", 0),
                "target_duration": selection_result.get("target_duration", 0),
                "actual_duration": composition_result.get("duration", 0),
                "file_size_mb": composition_result.get("file_size", 0) / (1024*1024) if composition_result.get("file_size") else 0
            },
            "module_breakdown": selection_result.get("module_details", {}),
            "technical_details": {
                "output_path": composition_result.get("output_path", ""),
                "error": composition_result.get("error"),
                "segment_count": composition_result.get("segment_count", 0)
            }
        }
        
        return report

    def compose_video_with_benchmark_audio(
        self, 
        selected_segments: Dict[str, List[Dict]], 
        output_path: str,
        benchmark_audio_path: str,
        resolution: str = "1080x1920",
        bitrate: str = "2M",
        fps: int = 30,
        use_segment_audio: bool = True  # 🔧 新增：是否使用片段原音频
    ) -> Dict[str, Any]:
        """
        使用标杆音频合成视频 - 🎯 优化版：解决音画不同步问题
        
        Args:
            selected_segments: 选择的片段
            output_path: 输出文件路径
            benchmark_audio_path: 标杆音频文件路径 (当use_segment_audio=False时使用)
            resolution: 输出分辨率
            bitrate: 输出比特率
            fps: 输出帧率
            use_segment_audio: 是否使用片段原音频(推荐True，避免音画不匹配)
            
        Returns:
            Dict: 合成结果
        """
        result = {
            "success": False,
            "output_path": output_path,
            "error": None,
            "duration": 0,
            "segment_count": 0,
            "audio_strategy": "segment_audio" if use_segment_audio else "benchmark_audio"
        }
        
        try:
            # 🔧 智能音频策略：优先保留片段原音频
            if use_segment_audio:
                logger.info("🎵 使用智能音频策略: 保留片段原音频，避免音画不匹配")
                print("🎵 使用智能音频策略: 保留片段原音频")
                # 直接使用标准合成方法，保留各片段原音频
                return self.compose_video_with_ffmpeg(
                    selected_segments, output_path, resolution, bitrate, fps
                )
            
            # 🎯 标杆音频完全替换策略 - 🔧 新增稳定音画同步方案
            logger.info("🎯 使用优化的标杆音频替换策略，确保音画同步")
            print("🎯 使用优化的标杆音频替换策略，确保音画同步")
            
            # 验证标杆音频文件
            if not os.path.exists(benchmark_audio_path):
                result["error"] = f"标杆音频文件不存在: {benchmark_audio_path}"
                return result
            
            # 🎯 获取标杆音频的时长
            benchmark_audio_info = self.get_video_info(benchmark_audio_path)
            benchmark_duration = benchmark_audio_info.get("duration", 0)
            logger.info(f"🎯 标杆音频时长: {benchmark_duration:.2f}秒")
            print(f"🎯 标杆音频时长: {benchmark_duration:.2f}秒")
            
            # 创建临时目录
            with tempfile.TemporaryDirectory() as temp_dir:
                # 🔧 步骤1: 先拼接视频并计算实际时长
                temp_video_with_audio = os.path.join(temp_dir, "temp_video_with_audio.mp4")
                
                # 先用标准方法创建完整视频（保留原音频）
                logger.info("第1步：创建完整拼接视频...")
                standard_result = self.compose_video_with_ffmpeg(
                    selected_segments, temp_video_with_audio, resolution, bitrate, fps
                )
                
                if not standard_result.get("success", False):
                    result["error"] = f"标准视频拼接失败: {standard_result.get('error', 'Unknown error')}"
                    return result
                
                actual_video_duration = standard_result.get("duration", 0)
                logger.info(f"实际视频时长: {actual_video_duration:.2f}秒，标杆音频时长: {benchmark_duration:.2f}秒")
                
                # 🔧 步骤2: 智能音视频时长对齐策略
                if abs(actual_video_duration - benchmark_duration) <= 1.0:
                    # 时长差异小于1秒，直接替换音频
                    logger.info("⚡ 时长差异 ≤ 1秒，使用直接音频替换策略")
                    
                    ffmpeg_cmd = [
                        'ffmpeg',
                        '-i', temp_video_with_audio,     # 视频输入
                        '-i', benchmark_audio_path,      # 音频输入
                        
                        # 🔧 简单直接的流映射，避免复杂的filter_complex
                        '-map', '0:v:0',                 # 使用第一个输入的视频流
                        '-map', '1:a:0',                 # 使用第二个输入的音频流
                        
                        # 🔧 保持原有视频编码，避免重新编码导致的同步问题
                        '-c:v', 'copy',                  # 复制视频流，不重新编码
                        '-c:a', 'aac',                   # 重新编码音频为AAC
                        '-b:a', '128k',                  # 音频比特率
                        
                        # 🔧 精确时长控制
                        '-t', str(min(actual_video_duration, benchmark_duration)),
                        
                        # 🔧 基本同步参数
                        '-avoid_negative_ts', 'make_zero',
                        '-movflags', '+faststart',
                        
                        '-y',
                        output_path
                    ]
                    
                elif actual_video_duration < benchmark_duration:
                    # 视频短于音频，需要循环视频
                    logger.info("🔄 视频短于音频，使用视频循环策略")
                    
                    ffmpeg_cmd = [
                        'ffmpeg',
                        '-stream_loop', '-1',            # 无限循环视频输入
                        '-i', temp_video_with_audio,     # 视频输入（循环）
                        '-i', benchmark_audio_path,      # 音频输入
                        
                        # 🔧 精简的视频处理（避免复杂filter_complex）
                        '-map', '0:v:0',                 # 循环的视频流
                        '-map', '1:a:0',                 # 标杆音频流
                        
                        # 🔧 保持视频质量，重新编码以确保循环平滑
                        '-c:v', 'libx264',
                        '-crf', '23',
                        '-preset', 'medium',
                        '-c:a', 'aac',
                        '-b:a', '128k',
                        
                        # 🔧 精确时长控制为音频时长
                        '-t', str(benchmark_duration),
                        
                        # 🔧 音画同步优化
                        '-fps_mode', 'cfr',              # 恒定帧率
                        '-r', str(fps),                  # 明确指定帧率
                        '-async', '1',                   # 音频同步
                        '-avoid_negative_ts', 'make_zero',
                        '-movflags', '+faststart',
                        
                        '-y',
                        output_path
                    ]
                    
                else:
                    # 视频长于音频，需要截断视频
                    logger.info("✂️ 视频长于音频，使用视频截断策略")
                    
                    ffmpeg_cmd = [
                        'ffmpeg',
                        '-i', temp_video_with_audio,     # 视频输入
                        '-i', benchmark_audio_path,      # 音频输入
                        
                        # 🔧 简单流映射
                        '-map', '0:v:0',                 # 视频流
                        '-map', '1:a:0',                 # 音频流
                        
                        # 🔧 保持视频编码
                        '-c:v', 'copy',                  # 复制视频流
                        '-c:a', 'aac',                   # 重新编码音频
                        '-b:a', '128k',
                        
                        # 🔧 精确时长控制为音频时长
                        '-t', str(benchmark_duration),
                        
                        # 🔧 基本同步参数
                        '-avoid_negative_ts', 'make_zero',
                        '-movflags', '+faststart',
                        
                        '-y',
                        output_path
                    ]
                
                # 确保输出目录存在
                os.makedirs(os.path.dirname(output_path), exist_ok=True)
                
                # 执行FFmpeg命令
                logger.info(f"执行音视频合并: {' '.join(ffmpeg_cmd[:10])}...")
                process = subprocess.run(
                    ffmpeg_cmd,
                    capture_output=True,
                    text=True,
                    timeout=600
                )
                
                if process.returncode == 0:
                    # 成功
                    result["success"] = True
                    
                    # 获取输出视频信息
                    if os.path.exists(output_path):
                        video_info = self.get_video_info(output_path)
                        result["duration"] = video_info.get("duration", 0)
                        result["file_size"] = os.path.getsize(output_path)
                        
                        # 统计片段数量
                        result["segment_count"] = sum(
                            len(segments) for segments in selected_segments.values()
                        )
                        
                        logger.info(
                            f"🎯 标杆音频视频合成成功: {output_path}, "
                            f"输出时长: {result['duration']:.2f}s, "
                            f"目标时长: {benchmark_duration:.2f}s, "
                            f"片段数: {result['segment_count']}"
                        )
                        print(f"✅ 优化音频合成成功！输出时长: {result['duration']:.2f}s (目标: {benchmark_duration:.2f}s)")
                        
                        # 🎯 验证时长匹配
                        duration_diff = abs(result["duration"] - benchmark_duration)
                        if duration_diff > 1.0:  # 允许1秒误差
                            logger.warning(f"⚠️ 输出时长与目标时长相差 {duration_diff:.2f}s")
                            print(f"⚠️ 时长偏差: {duration_diff:.2f}s")
                        else:
                            logger.info("✅ 输出时长与目标时长匹配良好")
                            print("✅ 时长匹配良好")
                    else:
                        result["success"] = False
                        result["error"] = "输出文件未生成"
                        
                else:
                    # 失败
                    result["error"] = f"音频合并失败: {process.stderr}"
                    logger.error(f"FFmpeg错误: {process.stderr}")

        except Exception as e:
            result["error"] = f"合成过程异常: {str(e)}"
            logger.error(f"compose_video_with_benchmark_audio异常: {e}")

        return result

    def _select_manual_segments(self, module_segments: List[Dict], module: str, manual_selections: Dict[str, List[str]]) -> List[Dict]:
        """
        根据手动选择的片段ID获取实际片段
        
        Args:
            module_segments: 该模块的所有片段
            module: 模块名称
            manual_selections: 手动选择的片段ID字典
            
        Returns:
            List[Dict]: 手动选择的片段列表
        """
        selected_ids = manual_selections.get(module, [])
        selected_segments = []
        
        for segment in module_segments:
            if segment.get('segment_id') in selected_ids:
                selected_segments.append(segment)
        
        logger.info(f"👆 手动选择模块 {module}: 选择了 {len(selected_segments)}/{len(module_segments)} 个片段")
        
        return selected_segments

    def get_detailed_video_info(self, video_path: str) -> Dict[str, Any]:
        """
        获取详细的视频技术信息，包括帧率、分辨率、编码格式等
        
        Args:
            video_path: 视频文件路径
            
        Returns:
            Dict: 详细视频信息
        """
        try:
            cmd = [
                'ffprobe', '-v', 'quiet', '-print_format', 'json',
                '-show_format', '-show_streams', video_path
            ]
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
            
            if result.returncode == 0:
                data = json.loads(result.stdout)
                format_info = data.get('format', {})
                streams = data.get('streams', [])
                
                # 查找视频流
                video_stream = None
                audio_stream = None
                for stream in streams:
                    if stream.get('codec_type') == 'video':
                        video_stream = stream
                    elif stream.get('codec_type') == 'audio':
                        audio_stream = stream
                
                info = {
                    "duration": float(format_info.get('duration', 0)),
                    "size": int(format_info.get('size', 0)),
                    "bit_rate": int(format_info.get('bit_rate', 0)),
                    "format_name": format_info.get('format_name', ''),
                    "has_video": video_stream is not None,
                    "has_audio": audio_stream is not None
                }
                
                if video_stream:
                    # 提取视频流信息
                    info.update({
                        "video_codec": video_stream.get('codec_name', ''),
                        "width": int(video_stream.get('width', 0)),
                        "height": int(video_stream.get('height', 0)),
                        "fps": self._parse_fps(video_stream.get('r_frame_rate', '0/1')),
                        "avg_fps": self._parse_fps(video_stream.get('avg_frame_rate', '0/1')),
                        "pix_fmt": video_stream.get('pix_fmt', ''),
                        "video_bitrate": int(video_stream.get('bit_rate', 0)) if video_stream.get('bit_rate') else 0
                    })
                
                if audio_stream:
                    # 提取音频流信息
                    info.update({
                        "audio_codec": audio_stream.get('codec_name', ''),
                        "sample_rate": int(audio_stream.get('sample_rate', 0)),
                        "channels": int(audio_stream.get('channels', 0)),
                        "audio_bitrate": int(audio_stream.get('bit_rate', 0)) if audio_stream.get('bit_rate') else 0
                    })
                
                return info
                
        except Exception as e:
            logger.error(f"获取详细视频信息失败: {e}")
        
        return {"duration": 0, "has_video": False, "has_audio": False}
    
    def _parse_fps(self, fps_str: str) -> float:
        """解析帧率字符串（如 "30/1"）为浮点数"""
        try:
            if '/' in fps_str:
                num, den = fps_str.split('/')
                return float(num) / float(den) if float(den) != 0 else 0
            else:
                return float(fps_str)
        except:
            return 0
    
    def analyze_segments_compatibility(self, selected_segments: Dict[str, List[Dict]]) -> Dict[str, Any]:
        """
        分析视频片段的兼容性，检查是否存在技术参数不一致的问题
        
        Args:
            selected_segments: 选择的片段
            
        Returns:
            Dict: 兼容性分析结果
        """
        all_segments = []
        for module_segments in selected_segments.values():
            all_segments.extend(module_segments)
        
        if not all_segments:
            return {"compatible": True, "issues": [], "segments_analyzed": 0}
        
        logger.info(f"🔍 开始分析 {len(all_segments)} 个视频片段的兼容性...")
        
        segment_infos = []
        issues = []
        
        for i, segment in enumerate(all_segments):
            file_path = segment.get('file_path') or segment.get('video_path') or segment.get('path')
            
            if not file_path:
                # 尝试构建路径
                video_id = segment.get('video_id', '')
                file_name = segment.get('file_name', '')
                if video_id and file_name:
                    file_path = f"data/output/google_video/video_pool/{video_id}/{file_name}"
                elif file_name:
                    file_path = f"data/output/google_video/video_pool/{file_name}"
            
            if file_path and os.path.exists(file_path):
                info = self.get_detailed_video_info(file_path)
                info['segment_id'] = segment.get('segment_id', f'segment_{i}')
                info['file_path'] = file_path
                segment_infos.append(info)
            else:
                issues.append(f"片段文件不存在: {file_path}")
        
        if not segment_infos:
            return {"compatible": False, "issues": ["没有找到有效的视频文件"], "segments_analyzed": 0}
        
        # 分析技术参数一致性
        fps_values = [info['fps'] for info in segment_infos if info.get('fps', 0) > 0]
        resolutions = [(info.get('width', 0), info.get('height', 0)) for info in segment_infos if info.get('width', 0) > 0]
        codecs = [info.get('video_codec', '') for info in segment_infos if info.get('video_codec')]
        
        # 🔧 初始化兼容性标志
        compatible = True
        needs_standardization = False
        fps_variance = 0
        resolution_consistent = True
        
        # 检查帧率一致性
        if fps_values:
            fps_variance = max(fps_values) - min(fps_values)
            if fps_variance > 1:  # 帧率差异超过1fps
                unique_fps = list(set(fps_values))
                issues.append(f"帧率不一致: 发现 {len(unique_fps)} 种不同帧率 {unique_fps}")
                logger.warning(f"⚠️ 帧率不一致: {unique_fps}")
                compatible = False
                needs_standardization = True
        
        # 检查分辨率一致性
        if resolutions:
            unique_resolutions = list(set(resolutions))
            if len(unique_resolutions) > 1:
                issues.append(f"分辨率不一致: 发现 {len(unique_resolutions)} 种不同分辨率 {unique_resolutions}")
                logger.warning(f"⚠️ 分辨率不一致: {unique_resolutions}")
                compatible = False
                needs_standardization = True
                resolution_consistent = False
        
        # 检查编码格式
        if codecs:
            unique_codecs = list(set(codecs))
            if len(unique_codecs) > 1:
                issues.append(f"视频编码不一致: 发现 {len(unique_codecs)} 种编码格式 {unique_codecs}")
                logger.warning(f"⚠️ 编码格式不一致: {unique_codecs}")
                compatible = False
                needs_standardization = True
        
        # 检查是否有损坏的视频
        invalid_segments = [info for info in segment_infos if not info.get('has_video')]
        if invalid_segments:
            issues.append(f"发现 {len(invalid_segments)} 个无效视频片段")
            compatible = False
            needs_standardization = True
        
        logger.info(f"🔍 兼容性分析完成: {'兼容' if compatible else '存在问题'}")
        if issues:
            for issue in issues:
                logger.warning(f"   - {issue}")
        
        return {
            "compatible": compatible,
            "needs_standardization": needs_standardization,  # 🔧 添加缺少的字段
            "fps_variance": fps_variance,  # 🔧 添加缺少的字段
            "resolution_consistent": resolution_consistent,  # 🔧 添加缺少的字段
            "issues": issues,
            "segments_analyzed": len(segment_infos),
            "segment_details": segment_infos,
            "stats": {
                "fps_range": [min(fps_values), max(fps_values)] if fps_values else [0, 0],
                "resolutions": unique_resolutions if 'unique_resolutions' in locals() else [],
                "codecs": unique_codecs if 'unique_codecs' in locals() else []
            }
        }
    
    def create_standardized_ffmpeg_concat_file(self, selected_segments: Dict[str, List[Dict]], temp_dir: str, target_fps: int = 30, target_resolution: str = "1080x1920") -> str:
        """
        创建标准化的FFmpeg concat文件 - 🚀 性能优化版
        
        Args:
            selected_segments: 选择的片段.
                               Can be Dict[module_name, List[segment_dict]] or
                               Dict[\"script_matched\", List[segment_dict]].
            temp_dir: 临时目录
            target_fps: 目标帧率
            target_resolution: 目标分辨率
            
        Returns:
            str: concat文件路径
        """
        concat_file_path = os.path.join(temp_dir, "concat_list.txt")
        standardized_dir = os.path.join(temp_dir, "standardized_segments")
        os.makedirs(standardized_dir, exist_ok=True)
        
        # 按四大模块顺序排列片段或处理 script_matched 结构
        all_segments = []
        # 🔧 FIX: Handle different structures of selected_segments
        if "script_matched" in selected_segments:
            all_segments = selected_segments["script_matched"]
            logger.info("Using segments from 'script_matched' for standardized concat file.")
        elif any(module in selected_segments for module in self.four_modules):
            for module in self.four_modules:
                module_segments = selected_segments.get(module, [])
                # 在模块内按质量分排序
                module_segments.sort(key=lambda x: x.get('combined_quality', 0), reverse=True)
                all_segments.extend(module_segments)
            logger.info("Using segments categorized by four modules for standardized concat file.")
        else:
            logger.warning(f"Unexpected structure for selected_segments or empty in create_standardized_ffmpeg_concat_file: {list(selected_segments.keys())}")
            # Attempt to flatten if it's a dict of lists
            for key in selected_segments:
                if isinstance(selected_segments[key], list):
                    all_segments.extend(selected_segments[key])
        
        valid_segments = 0
        standardized_count = 0
        skipped_count = 0
        
        # 🚀 分析兼容性，智能决定是否需要标准化
        compatibility = self.analyze_segments_compatibility(selected_segments)
        need_standardization = not compatibility['compatible']
        fps_variance = compatibility.get('fps_variance', 0)
        
        if need_standardization:
            logger.info(f"🔧 检测到技术参数不一致（帧率差异{fps_variance:.1f}fps），开始智能标准化...")
            print(f"🔧 检测到技术参数不一致，开始智能标准化...")
        else:
            logger.info("✅ 所有片段技术参数兼容，无需标准化")
            print("✅ 所有片段技术参数兼容，无需标准化")
        
        # 🚀 智能标准化策略：优先使用高质量片段，跳过问题片段
        with open(concat_file_path, 'w', encoding='utf-8') as f:
            for i, segment in enumerate(all_segments):
                file_path = segment.get('file_path') or segment.get('video_path') or segment.get('path')
                
                if not file_path:
                    video_id = segment.get('video_id', '')
                    file_name = segment.get('file_name', '')
                    if video_id and file_name:
                        file_path = f"data/output/google_video/video_pool/{video_id}/{file_name}"
                    elif file_name:
                        file_path = f"data/output/google_video/video_pool/{file_name}"
                
                if file_path and os.path.exists(file_path):
                    final_path = file_path  # 默认使用原文件
                    
                    if need_standardization:
                        # 🚀 智能判断：只对真正需要的片段进行标准化
                        segment_info = self.get_detailed_video_info(file_path)
                        current_fps = segment_info.get('fps', 30)
                        current_resolution = f"{segment_info.get('width', 0)}x{segment_info.get('height', 0)}"
                        current_duration = segment_info.get('duration', 0)
                        
                        # 🚀 智能跳过条件
                        should_standardize = False
                        skip_reasons = []
                        
                        # 检查是否真的需要标准化
                        if abs(current_fps - target_fps) > target_fps * 0.2:  # 帧率差异超过20%
                            should_standardize = True
                        elif current_resolution != target_resolution:  # 分辨率不匹配
                            should_standardize = True
                        
                        # 跳过条件
                        if current_duration > 20:  # 🚀 跳过超过20秒的片段
                            skip_reasons.append("过长")
                        elif current_duration < 0.5:  # 跳过过短的片段
                            skip_reasons.append("过短")
                        elif segment_info.get('video_codec') not in ['h264', 'libx264'] and current_duration > 10:
                            skip_reasons.append("编码复杂且较长")
                        
                        if should_standardize and not skip_reasons:
                            # 尝试标准化
                            standardized_path = os.path.join(standardized_dir, f"segment_{i:03d}.mp4")
                            logger.info(f"🔧 标准化片段 {i+1}/{len(all_segments)}: {os.path.basename(file_path)}")
                            
                            if self._standardize_video_segment(file_path, standardized_path, target_fps, target_resolution):
                                final_path = standardized_path
                                standardized_count += 1
                                logger.debug(f"✅ 标准化成功: {os.path.basename(file_path)}")
                            else:
                                # 标准化失败，使用原文件
                                logger.warning(f"⚠️ 标准化失败，使用原文件: {os.path.basename(file_path)}")
                                skipped_count += 1
                        elif skip_reasons:
                            logger.info(f"⚠️ 跳过标准化({'/'.join(skip_reasons)}): {os.path.basename(file_path)}")
                            skipped_count += 1
                        else:
                            logger.debug(f"✅ 无需标准化: {os.path.basename(file_path)}")
                    
                    # 添加到concat文件
                    abs_path = os.path.abspath(final_path)
                    # Correctly escape single quotes for FFmpeg concat file format
                    escaped_for_concat = abs_path.replace("'", "'\\''")
                    f.write(f"file '{escaped_for_concat}'\n")
                    valid_segments += 1
                    logger.debug(f"添加片段到concat: {os.path.basename(final_path)}")
                else:
                    logger.warning(f"片段文件不存在，跳过: {file_path}")
        
        # 🚀 性能报告
        logger.info(f"🚀 智能标准化完成: {valid_segments}/{len(all_segments)} 个有效片段")
        if need_standardization:
            logger.info(f"   📊 标准化统计: 成功{standardized_count}个, 跳过{skipped_count}个, 使用原文件{valid_segments-standardized_count}个")
            print(f"🚀 智能标准化: {standardized_count}个重编码, {skipped_count}个智能跳过")
        
        return concat_file_path
    
    def _standardize_video_segment(self, input_path: str, output_path: str, target_fps: int, target_resolution: str) -> bool:
        """
        标准化单个视频片段的技术参数 - 🚀 性能优化版
        
        Args:
            input_path: 输入视频路径
            output_path: 输出视频路径
            target_fps: 目标帧率
            target_resolution: 目标分辨率
            
        Returns:
            bool: 是否成功
        """
        try:
            # 🔧 优化：先获取输入视频信息，智能处理帧率转换
            info = self.get_detailed_video_info(input_path)
            input_fps = info.get('fps', 30)
            input_duration = info.get('duration', 0)
            
            # 🚀 性能优化：跳过过长的片段标准化
            if input_duration > 30:  # 超过30秒的片段跳过标准化
                logger.warning(f"⚠️ 片段过长({input_duration:.1f}s)，跳过标准化: {os.path.basename(input_path)}")
                return False
            
            # 🔧 智能帧率处理：使用更严格的同步策略
            if input_fps > target_fps * 1.5:
                # 输入帧率较高，使用精确降帧率
                logger.info(f"输入帧率较高({input_fps:.1f}fps)，精确降帧到{target_fps}fps")
                video_filter = f"fps={target_fps}:round=down"
            elif input_fps < target_fps * 0.8:
                # 输入帧率较低，使用精确升帧率
                logger.info(f"输入帧率较低({input_fps:.1f}fps)，精确升帧到{target_fps}fps")
                video_filter = f"fps={target_fps}:round=up"
            else:
                # 帧率接近，直接转换
                video_filter = f"fps={target_fps}"
            
            # 🚀 构建高性能FFmpeg命令
            ffmpeg_cmd = [
                'ffmpeg',
                '-i', input_path,
                '-c:v', 'libx264',           # 统一使用H.264编码
                '-preset', 'ultrafast',      # 🚀 关键优化：使用最快预设
                '-crf', '28',                # 🚀 降低质量要求，提升速度
                '-vf', f"scale={target_resolution}:flags=bicubic,{video_filter}",  # 🚀 使用更快的bicubic算法
                '-pix_fmt', 'yuv420p',       # 统一像素格式
                '-avoid_negative_ts', 'make_zero',  # 避免负时间戳
                '-fps_mode', 'cfr',          # 🚀 恒定帧率模式
                '-threads', '0',             # 🚀 使用所有可用线程
                '-y',                        # 覆盖输出文件
                output_path
            ]
            
            # 🚀 简化音频处理，提升性能
            if info.get('has_audio'):
                audio_params = [
                    '-c:a', 'aac',
                    '-b:a', '96k',           # 🚀 降低音频码率
                    '-ar', '44100',          # 标准采样率
                    '-ac', '2'               # 双声道
                ]
                # 在 -y 之前插入所有音频参数
                ffmpeg_cmd = ffmpeg_cmd[:-2] + audio_params + ffmpeg_cmd[-2:]
            else:
                ffmpeg_cmd.insert(-2, '-an')  # 无音频
            
            logger.debug(f"🚀 快速标准化命令: {' '.join(ffmpeg_cmd[:10])}...")
            
            # 🚀 执行标准化，使用更短的超时时间
            process = subprocess.run(
                ffmpeg_cmd,
                capture_output=True,
                text=True,
                timeout=60  # 🚀 减少到60秒超时
            )
            
            if process.returncode == 0:
                logger.debug(f"✅ 片段标准化成功: {os.path.basename(input_path)}")
                return True
            else:
                logger.warning(f"❌ 片段标准化失败: {process.stderr[:200]}...")  # 只显示前200字符
                return False
                
        except subprocess.TimeoutExpired:
            logger.warning(f"⚠️ 片段标准化超时，跳过: {os.path.basename(input_path)}")
            return False
        except Exception as e:
            logger.warning(f"⚠️ 片段标准化异常，跳过: {os.path.basename(input_path)} - {str(e)[:100]}")
            return False
    
    def select_segments_by_script_content(
        self,
        mapped_segments: List[Dict[str, Any]],
        srt_entries: List[Dict[str, Any]],
        target_duration: float = 100.0,
        visual_match_threshold: float = 0.4,  # 降低阈值，提高匹配成功率
        text_match_threshold: float = 0.6,
        benchmark_ratios: List[int] = None  # 🎯 新增：标杆视频的模块比例
    ) -> Dict[str, Any]:
        """
        基于脚本内容选择视频片段 - 🎯 NEW: 使用模块特异性匹配器
        
        Args:
            mapped_segments: 映射后的片段列表
            srt_entries: 解析后的SRT条目列表，格式：[{index, timestamp, text}, ...]
            target_duration: 目标总时长（秒）
            visual_match_threshold: 视觉标签匹配阈值（降低以提高成功率）
            text_match_threshold: 文本转录匹配阈值
            benchmark_ratios: 🎯 标杆视频的模块比例 [痛点%, 解决方案%, 卖点%, 促销%]
            
        Returns:
            Dict: 选择结果，包含matched_segments和matching_details
        """
        # 🎯 使用标杆视频的模块比例，或回退到默认比例
        if benchmark_ratios is None:
            benchmark_ratios = [25, 28, 32, 15]  # 默认比例
        
        logger.info(f"🎯 开始模块特异性脚本匹配")
        logger.info(f"📊 目标时长: {target_duration}s, 标杆模块比例: {benchmark_ratios}")
        
        # 🎯 NEW: 使用模块特异性匹配器进行第一阶段匹配
        try:
            from .module_specific_matcher import match_segments_advanced
            
            logger.info("🧠 使用模块特异性匹配器进行精准匹配...")
            advanced_result = match_segments_advanced(srt_entries, mapped_segments)
            
            matched_segments = advanced_result["matched_segments"]
            matching_details = advanced_result["matching_details"]
            unused_srt_count = advanced_result["unused_srt"]
            
            logger.info(f"✅ 模块特异性匹配完成: {len(matched_segments)} 个片段匹配成功, {unused_srt_count} 个SRT未匹配")
            
            # 显示匹配详情
            for detail in matching_details[:5]:  # 显示前5个匹配详情
                if detail["matched_segment"]:
                    logger.info(f"   ✅ SRT: '{detail['srt_text']}' → 模块: {detail['module']} → 片段: {detail['matched_segment']} (评分: {detail['score']})")
                else:
                    logger.warning(f"   ❌ SRT: '{detail['srt_text']}' → 模块: {detail['module']} → 无匹配片段")
            
        except ImportError as e:
            logger.warning(f"⚠️ 无法导入模块特异性匹配器: {e}，回退到传统匹配")
            # 回退到原有逻辑
            return self._fallback_script_matching(mapped_segments, srt_entries, target_duration, 
                                                visual_match_threshold, text_match_threshold, benchmark_ratios)
        except Exception as e:
            logger.error(f"❌ 模块特异性匹配失败: {e}，回退到传统匹配")
            return self._fallback_script_matching(mapped_segments, srt_entries, target_duration,
                                                visual_match_threshold, text_match_threshold, benchmark_ratios)
        
        # 计算已匹配的总时长
        matched_duration = sum(seg.get('duration', 0) for seg in matched_segments)
        remaining_duration = target_duration - matched_duration
        
        logger.info(f"📊 模块特异性匹配结果: {len(matched_segments)} 个片段, "
                   f"已匹配时长 {matched_duration:.1f}s, 剩余需填充 {remaining_duration:.1f}s")
        
        # 🔄 第二阶段：智能填充到目标时长（如果需要）
        if remaining_duration > 5:  # 如果剩余时长超过5秒，进行填充
            logger.info(f"🔄 开始智能填充剩余时长 {remaining_duration:.1f}s")
            
            # 获取已使用的片段ID
            used_segment_ids = set()
            for seg in matched_segments:
                used_segment_ids.add(seg.get('segment_id', seg.get('file_name', '')))
            
            # 🎯 使用标杆视频的实际模块比例进行填充
            modules = ["痛点", "解决方案导入", "卖点·成分&配方", "促销机制"]
            
            for i, (module, ratio) in enumerate(zip(modules, benchmark_ratios)):
                module_target_duration = (remaining_duration * ratio) / 100
                
                # 获取该模块的可用片段（排除已使用的）
                available_segments = [
                    seg for seg in mapped_segments 
                    if seg.get('category') == module 
                    and seg.get('segment_id', seg.get('file_name', '')) not in used_segment_ids
                ]
                
                if not available_segments:
                    logger.warning(f"⚠️ 模块 {module} 没有可用片段用于填充")
                    continue
                
                # 按质量排序，优先选择高质量片段
                available_segments.sort(key=lambda x: x.get('combined_quality', 0), reverse=True)
                
                # 选择片段填充该模块时长
                module_selected = []
                module_duration = 0
                
                for segment in available_segments:
                    if module_duration >= module_target_duration:
                        break
                    
                    segment_duration = segment.get('duration', 0)
                    if module_duration + segment_duration <= module_target_duration * 1.2:  # 允许超出20%
                        module_selected.append(segment)
                        module_duration += segment_duration
                        used_segment_ids.add(segment.get('segment_id', segment.get('file_name', '')))
                
                # 添加到总结果
                matched_segments.extend(module_selected)
                matched_duration += module_duration
                
                logger.info(f"✅ 模块 {module} 填充: 添加 {len(module_selected)} 个片段, 时长 {module_duration:.1f}s")
        
        # 构建最终结果
        selection_result = {
            "matched_segments": matched_segments,
            "total_duration": matched_duration,
            "target_duration": target_duration,
            "benchmark_ratios": benchmark_ratios,
            "matching_details": matching_details,
            "matching_stats": {
                "total_matched": len(matched_segments),
                "srt_matched": len(matched_segments) - unused_srt_count,
                "unused_srt": unused_srt_count,
                "coverage_rate": (matched_duration / target_duration) * 100 if target_duration > 0 else 0
            }
        }
        
        logger.info(f"🎉 模块特异性脚本匹配完成: {len(matched_segments)} 个片段, "
                   f"总时长 {matched_duration:.1f}s, 覆盖率 {selection_result['matching_stats']['coverage_rate']:.1f}%")
        
        return selection_result
    
    def _fallback_script_matching(
        self,
        mapped_segments: List[Dict[str, Any]],
        srt_entries: List[Dict[str, Any]],
        target_duration: float,
        visual_match_threshold: float,
        text_match_threshold: float,
        benchmark_ratios: List[int]
    ) -> Dict[str, Any]:
        """
        传统脚本匹配的回退逻辑（保持原有功能）
        """
        logger.info("🔄 使用传统脚本匹配逻辑")
        
        selection_result = {
            "matched_segments": [],
            "total_duration": 0,
            "target_duration": target_duration,
            "benchmark_ratios": benchmark_ratios,
            "matching_details": [],
            "matching_stats": {
                "visual_matches": 0,
                "transcript_matches": 0,
                "category_fallbacks": 0,
                "intelligent_fills": 0,
                "unmatched": 0
            }
        }
        
        used_segment_ids = set()
        
        # 原有的SRT内容匹配逻辑
        for srt_entry in srt_entries:
            srt_text = srt_entry['text'].strip()
            srt_timestamp = srt_entry['timestamp']
            
            if not srt_text:
                continue
                
            best_segment = None
            match_type = None
            match_score = 0
            
            # 视觉标签匹配
            best_segment, match_type, match_score = self._find_best_visual_match(
                srt_text, mapped_segments, used_segment_ids, visual_match_threshold
            )
            
            # 文本转录匹配
            if not best_segment:
                segments_with_transcript = [
                    s for s in mapped_segments 
                    if s.get('transcription') and s.get('transcription').strip()
                ]
                
                if segments_with_transcript:
                    best_segment, match_type, match_score = self._find_best_transcript_match(
                        srt_text, segments_with_transcript, used_segment_ids, text_match_threshold
                    )
            
            # 分类兜底匹配
            if not best_segment:
                best_segment, match_type, match_score = self._find_category_fallback_match(
                    srt_text, mapped_segments, used_segment_ids
                )
            
            # 记录匹配结果
            if best_segment:
                used_segment_ids.add(best_segment.get('segment_id', best_segment.get('file_name', '')))
                selection_result["matched_segments"].append(best_segment)
                selection_result["total_duration"] += best_segment.get('duration', 0)
                
                # 更新统计
                if match_type == "visual":
                    selection_result["matching_stats"]["visual_matches"] += 1
                elif match_type == "transcript":
                    selection_result["matching_stats"]["transcript_matches"] += 1
                elif match_type == "category":
                    selection_result["matching_stats"]["category_fallbacks"] += 1
                
                # 记录匹配详情
                match_detail = {
                    "srt_text": srt_text,
                    "srt_timestamp": srt_timestamp,
                    "matched_segment": best_segment.get('file_name', 'unknown'),
                    "match_type": match_type,
                    "match_score": match_score,
                    "segment_duration": best_segment.get('duration', 0),
                    "has_transcription": bool(best_segment.get('transcription'))
                }
                selection_result["matching_details"].append(match_detail)
                
            else:
                selection_result["matching_stats"]["unmatched"] += 1
        
        return selection_result
    
    def _find_best_transcript_match(
        self,
        srt_text: str,
        mapped_segments: List[Dict[str, Any]],
        used_segment_ids: set,
        similarity_threshold: float
    ) -> Tuple[Optional[Dict], str, float]:
        """
        第一优先级：在片段转录文本中寻找最佳匹配
        
        Args:
            srt_text: SRT条目文本
            mapped_segments: 候选片段列表
            used_segment_ids: 已使用片段ID集合
            similarity_threshold: 相似度阈值
            
        Returns:
            Tuple: (最佳片段, 匹配类型, 匹配分数)
        """
        best_segment = None
        best_score = 0
        
        # 提取SRT文本中的关键词（去除停用词）
        srt_keywords = self._extract_keywords(srt_text)
        
        for segment in mapped_segments:
            segment_id = segment.get('segment_id', segment.get('file_name', ''))
            if segment_id in used_segment_ids:
                continue
            
            # 获取片段的转录文本
            transcript = segment.get('transcription', '')
            if not transcript:
                continue
            
            # 计算文本相似度
            similarity = self._calculate_text_similarity(srt_text, transcript)
            
            # 也检查关键词匹配度
            keyword_matches = self._count_keyword_matches(srt_keywords, transcript)
            keyword_score = keyword_matches / len(srt_keywords) if srt_keywords else 0
            
            # 综合评分：文本相似度权重0.7，关键词匹配权重0.3
            combined_score = similarity * 0.7 + keyword_score * 0.3
            
            if combined_score > best_score and combined_score >= similarity_threshold:
                best_score = combined_score
                best_segment = segment
        
        return best_segment, "transcript", best_score
    
    def _find_best_visual_match(
        self,
        srt_text: str,
        mapped_segments: List[Dict[str, Any]],
        used_segment_ids: set,
        visual_match_threshold: float
    ) -> Tuple[Optional[Dict], str, float]:
        """
        第二优先级：在片段视觉标签/OCR中寻找关键词匹配
        
        Args:
            srt_text: SRT条目文本
            mapped_segments: 候选片段列表
            used_segment_ids: 已使用片段ID集合
            visual_match_threshold: 视觉匹配阈值
            
        Returns:
            Tuple: (最佳片段, 匹配类型, 匹配分数)
        """
        best_segment = None
        best_score = 0
        
        # 提取SRT文本中的关键词
        srt_keywords = self._extract_keywords(srt_text)
        
        for segment in mapped_segments:
            segment_id = segment.get('segment_id', segment.get('file_name', ''))
            if segment_id in used_segment_ids:
                continue
            
            # 🎯 NEW: 跳过人脸特写片段
            if segment.get('is_face_close_up', False) or segment.get('unusable', False):
                logger.debug(f"跳过人脸特写片段: {segment_id}")
                continue
            
            # 获取片段的视觉分析数据
            visual_analysis = segment.get('visual_analysis', {})
            all_visual_tags = []
            
            # 收集所有视觉标签
            if 'tags' in visual_analysis:
                all_visual_tags.extend(visual_analysis['tags'])
            if 'ocr_text' in visual_analysis:
                all_visual_tags.append(visual_analysis['ocr_text'])
            if 'detected_objects' in visual_analysis:
                all_visual_tags.extend(visual_analysis['detected_objects'])
            
            if not all_visual_tags:
                continue
            
            # 计算关键词在视觉标签中的匹配度
            visual_text = ' '.join(all_visual_tags).lower()
            keyword_matches = self._count_keyword_matches(srt_keywords, visual_text)
            match_score = keyword_matches / len(srt_keywords) if srt_keywords else 0
            
            if match_score > best_score and match_score >= visual_match_threshold:
                best_score = match_score
                best_segment = segment
        
        return best_segment, "visual", best_score
    
    def _find_category_fallback_match(
        self,
        srt_text: str,
        mapped_segments: List[Dict[str, Any]],
        used_segment_ids: set
    ) -> Tuple[Optional[Dict], str, float]:
        """
        第三优先级：基于传统分类的兜底匹配
        
        Args:
            srt_text: SRT条目文本
            mapped_segments: 候选片段列表
            used_segment_ids: 已使用片段ID集合
            
        Returns:
            Tuple: (最佳片段, 匹配类型, 匹配分数)
        """
        # 🔧 修复：简单的关键词到分类映射（符合母婴vlog特点）
        category_keywords = {
            "痛点": ["哭", "病", "医院", "问题", "困难", "担心", "焦虑"],
            "解决方案导入": ["解决", "方法", "方案", "帮助", "指导", "教程"],
            "卖点·成分&配方": ["A2", "HMO", "DHA", "营养", "成分", "配方", "品质"],
            "促销机制": ["开心", "快乐", "活力", "健康", "成长", "爱笑", "机灵", "聪明", "活泼"]  # 🔧 母婴vlog促销：宝宝积极状态展示
        }
        
        # 确定SRT文本最可能属于的分类
        target_category = None
        max_keyword_matches = 0
        
        for category, keywords in category_keywords.items():
            matches = self._count_keyword_matches(keywords, srt_text.lower())
            if matches > max_keyword_matches:
                max_keyword_matches = matches
                target_category = category
        
        if not target_category:
            return None, "category", 0
        
        # 在对应分类中寻找质量最高且未使用的片段
        best_segment = None
        best_quality = 0
        
        for segment in mapped_segments:
            segment_id = segment.get('segment_id', segment.get('file_name', ''))
            if segment_id in used_segment_ids:
                continue
            
            # 🎯 NEW: 跳过人脸特写片段
            if segment.get('is_face_close_up', False) or segment.get('unusable', False):
                logger.debug(f"跳过人脸特写片段: {segment_id}")
                continue
            
            if segment.get('category') == target_category:
                quality = segment.get('combined_quality', 0)
                if quality > best_quality:
                    best_quality = quality
                    best_segment = segment
        
        return best_segment, "category", best_quality
    
    def _extract_keywords(self, text: str) -> List[str]:
        """
        从文本中提取关键词（去除停用词）
        
        Args:
            text: 输入文本
            
        Returns:
            List[str]: 关键词列表
        """
        # 简单的中文停用词列表
        stop_words = {
            "的", "了", "在", "是", "我", "有", "和", "就", "不", "人", "都", "一", "一个",
            "上", "也", "很", "到", "说", "要", "去", "你", "会", "着", "没有", "看", "好",
            "可以", "这", "那", "什么", "这个", "他", "她", "它", "我们", "你们", "他们"
        }
        
        import re
        # 分词（简单按标点和空格分割）
        words = re.findall(r'[\u4e00-\u9fff]+|[A-Za-z]+\d*', text)
        
        # 过滤停用词和长度小于2的词
        keywords = [word for word in words if word not in stop_words and len(word) >= 2]
        
        return keywords
    
    def _calculate_text_similarity(self, text1: str, text2: str) -> float:
        """
        计算两段文本的相似度
        
        Args:
            text1: 文本1
            text2: 文本2
            
        Returns:
            float: 相似度分数（0-1）
        """
        if not text1 or not text2:
            return 0
        
        # 使用difflib计算序列相似度
        similarity = difflib.SequenceMatcher(None, text1.lower(), text2.lower()).ratio()
        return similarity
    
    def _count_keyword_matches(self, keywords: List[str], text: str) -> int:
        """
        计算关键词在文本中的匹配数量
        
        Args:
            keywords: 关键词列表
            text: 目标文本
            
        Returns:
            int: 匹配的关键词数量
        """
        if not keywords or not text:
            return 0
        
        text_lower = text.lower()
        matches = 0
        
        for keyword in keywords:
            if keyword.lower() in text_lower:
                matches += 1
        
        return matches

    def select_segments_by_fixed_sequence(
        self,
        mapped_segments: List[Dict[str, Any]],
        srt_entries: List[Dict[str, Any]],
        target_ratios: List[int] = None,
        total_target_duration: float = 100.0,
        selection_mode: SelectionMode = SelectionMode.OPTIMAL,
        randomness_level: str = "适中",
        random_seed: Optional[int] = None,
        min_segments_per_module: int = 2,
        max_segments_per_module: int = 3,
        max_single_segment_ratio: float = 0.8
    ) -> Dict[str, Any]:
        """
        🎯 固定序列模式：固定模块顺序+比例，但使用模块特异性脚本匹配
        
        特点：
        1. 严格按照预设的模块顺序：痛点 → 解决方案 → 卖点 → 促销
        2. 按照预设的时长占比分配每个模块
        3. 在每个模块内使用模块特异性匹配找到最合适的片段
        4. 确保SRT文本与视频片段的精准对应
        
        Args:
            mapped_segments: 映射后的片段列表
            srt_entries: 解析后的SRT条目列表
            target_ratios: 目标时长比例 [痛点, 解决方案, 卖点, 促销]，默认[25, 28, 32, 15]
            total_target_duration: 总目标时长（秒）
            selection_mode: 选择模式
            randomness_level: 随机强度参数
            random_seed: 随机种子
            min_segments_per_module: 每个模块最少片段数
            max_segments_per_module: 每个模块最多片段数
            max_single_segment_ratio: 单个片段最大占比
            
        Returns:
            Dict: 选择结果，按固定顺序排列且具备脚本匹配能力
        """
        logger.info(f"🎯 开始固定序列模式：固定顺序+比例+模块特异性脚本匹配")
        logger.info(f"📊 固定模块顺序: {' → '.join(self.four_modules)}")
        
        # 🎲 设置随机种子（如果指定）
        if random_seed is not None:
            random.seed(random_seed)
            logger.info(f"设置随机种子: {random_seed}")
        
        if target_ratios is None:
            target_ratios = self.default_ratios
            
        # 计算各模块的目标时长
        total_ratio = sum(target_ratios)
        target_durations = [
            (ratio / total_ratio) * total_target_duration 
            for ratio in target_ratios
        ]
        
        logger.info(f"📊 固定时长比例: {target_ratios}% = {[f'{d:.1f}s' for d in target_durations]}")
        
        # 第一步：使用模块特异性匹配器获取SRT到片段的匹配
        try:
            from .module_specific_matcher import match_segments_advanced
            
            logger.info("🧠 步骤1: 使用模块特异性匹配器进行SRT脚本匹配...")
            advanced_result = match_segments_advanced(srt_entries, mapped_segments)
            
            matched_segments_raw = advanced_result["matched_segments"]
            matching_details = advanced_result["matching_details"]
            unused_srt_count = advanced_result["unused_srt"]
            
            logger.info(f"✅ 模块特异性匹配完成: {len(matched_segments_raw)} 个片段匹配成功, {unused_srt_count} 个SRT未匹配")
            
        except ImportError as e:
            logger.warning(f"⚠️ 无法导入模块特异性匹配器: {e}，使用内置匹配逻辑")
            matched_segments_raw = []
            matching_details = []
            unused_srt_count = len(srt_entries)
        
        # 第二步：按固定模块顺序重新组织匹配结果
        logger.info("🎯 步骤2: 按固定模块顺序重新组织匹配结果...")
        
        selection_result = {
            "selected_segments": {},
            "total_duration": 0,
            "target_duration": total_target_duration,
            "module_details": {},
            "selection_strategy": "fixed_sequence_with_script_matching",
            "fixed_order": self.four_modules.copy(),
            "matching_details": matching_details,
            "matching_stats": {
                "script_matched": len(matched_segments_raw),
                "unused_srt": unused_srt_count,
                "total_srt": len(srt_entries)
            }
        }
        
        # 按固定顺序处理每个模块
        used_segment_ids = set()
        
        for i, module in enumerate(self.four_modules):
            target_duration = target_durations[i]
            
            logger.info(f"🔍 步骤2.{i+1}: 处理模块 {module} (目标时长: {target_duration:.1f}s)")
            
            # 2.1 获取该模块的脚本匹配片段
            module_script_matched = [
                seg for seg in matched_segments_raw 
                if seg.get('script_matched_module') == module  # 假设匹配器添加了这个字段
                and seg.get('segment_id', seg.get('file_name', '')) not in used_segment_ids
            ]
            
            # 2.2 如果脚本匹配不足，从该模块的所有片段中补充
            if len(module_script_matched) == 0 or sum(seg.get('duration', 0) for seg in module_script_matched) < target_duration * 0.8:
                logger.info(f"   脚本匹配不足，从模块片段池补充...")
                
                # 获取该模块的所有高质量片段
                module_all_segments = [
                    s for s in mapped_segments 
                    if s.get('category') == module 
                    and s.get('duration', 0) > 0
                    and s.get('segment_id', s.get('file_name', '')) not in used_segment_ids
                ]
                
                # 按质量排序
                module_all_segments.sort(key=lambda x: x.get('combined_quality', 0), reverse=True)
                
                # 优先使用脚本匹配的，然后补充高质量的
                module_candidates = module_script_matched + module_all_segments
                
                # 去重（保持顺序）
                seen_ids = set()
                module_candidates_unique = []
                for seg in module_candidates:
                    seg_id = seg.get('segment_id', seg.get('file_name', ''))
                    if seg_id not in seen_ids:
                        seen_ids.add(seg_id)
                        module_candidates_unique.append(seg)
                
                module_candidates = module_candidates_unique
            else:
                module_candidates = module_script_matched
                logger.info(f"   脚本匹配充足，使用 {len(module_candidates)} 个匹配片段")
            
            # 🚫 先过滤过长片段，避免单个片段占用过多时长
            filtered_candidates = [c for c in module_candidates if c.get('duration', 0) <= target_duration * max_single_segment_ratio]
            if not filtered_candidates:  # 如果过滤后没有候选，则回退使用原始列表
                filtered_candidates = module_candidates.copy()

            # 🎲 多样化增强：确保每个模块至少 min_segments_per_module，至多 max_segments_per_module
            # 1) 如果片段不足，随机补充
            if len(filtered_candidates) < min_segments_per_module:
                additional_pool = [seg for seg in module_candidates if seg not in filtered_candidates]
                random.shuffle(additional_pool)
                for seg in additional_pool:
                    if len(filtered_candidates) >= min_segments_per_module:
                        break
                    filtered_candidates.append(seg)

            # 2) 如果片段超出上限，随机裁剪，但保证覆盖率不低于80%
            if len(filtered_candidates) > max_segments_per_module:
                random.shuffle(filtered_candidates)
                filtered_candidates = filtered_candidates[:max_segments_per_module]

            # 如果没有候选片段，直接跳过，并记录
            if not filtered_candidates:
                logger.warning(f"⚠️ 模块 {module} 仍然没有可用片段（候选为空）")
                selected = []
                total_duration = 0
            else:
                # 使用最优或随机选择算法
                if selection_mode == SelectionMode.OPTIMAL:
                    selected = self._select_optimal_segments(filtered_candidates, target_duration)
                else:
                    selected = self._select_random_segments(filtered_candidates, target_duration, randomness_level)

                # 重新计算时长（可能因多样化调整而变化）
                total_duration = sum(s.get('duration', 0) for s in selected)
                
                # 记录已使用的片段
                for seg in selected:
                    used_segment_ids.add(seg.get('segment_id', seg.get('file_name', '')))

            # 保存模块结果
            selection_result["selected_segments"][module] = selected
            selection_result["module_details"][module] = {
                "target_duration": target_duration,
                "actual_duration": total_duration,
                "segment_count": len(selected),
                "script_matched_count": len(module_script_matched),
                "available_segments": len(module_candidates),
                "avg_quality": (
                    sum(s.get('combined_quality', 0) for s in selected) / len(selected)
                    if selected else 0
                ),
                "coverage_ratio": total_duration / target_duration if target_duration > 0 else 0
            }
            
            selection_result["total_duration"] += total_duration
            
            logger.info(
                f"✅ 模块 {module}: 目标{target_duration:.1f}s, 实际{total_duration:.1f}s, "
                f"片段数{len(selected)} (脚本匹配{len(module_script_matched)}), 覆盖率{total_duration/target_duration*100:.1f}%"
            )
        
        # 第三步：转换为兼容格式（供后续处理使用）
        logger.info("🔄 步骤3: 转换为合成器兼容格式...")
        
        # 按固定顺序展平所有片段
        final_matched_segments = []
        for module in self.four_modules:
            module_segments = selection_result["selected_segments"].get(module, [])
            for seg in module_segments:
                # 标记片段所属模块和在固定序列中的位置
                seg_copy = seg.copy()
                seg_copy['fixed_sequence_module'] = module
                seg_copy['fixed_sequence_order'] = len(final_matched_segments)
                final_matched_segments.append(seg_copy)
        
        # 更新匹配统计
        selection_result["matching_stats"].update({
            "total_matched": len(final_matched_segments),
            "coverage_rate": (selection_result["total_duration"] / total_target_duration) * 100 if total_target_duration > 0 else 0,
            "modules_filled": len([m for m in self.four_modules if len(selection_result["selected_segments"].get(m, [])) > 0])
        })
        
        logger.info(f"🎯 固定序列选择完成:")
        logger.info(f"   总片段数: {len(final_matched_segments)}")
        logger.info(f"   总时长: {selection_result['total_duration']:.1f}s / {total_target_duration:.1f}s")
        logger.info(f"   覆盖率: {selection_result['matching_stats']['coverage_rate']:.1f}%")
        logger.info(f"   填充模块数: {selection_result['matching_stats']['modules_filled']}/4")
        
        # 添加最终片段列表到结果中（兼容性）
        selection_result["matched_segments"] = final_matched_segments
        
        return selection_result

    def compose_video_with_quality_preservation(
        self, 
        selected_segments: Dict[str, List[Dict]], 
        output_path: str,
        resolution: str = "1080x1920",
        bitrate: str = "2M",
        target_fps: int = 30,
        quality_mode: str = "preserve"  # "preserve", "balance", "strict"
    ) -> Dict[str, Any]:
        """
        🎯 保持画质的视频拼接（支持帧率不一致）
        
        Args:
            selected_segments: 选择的片段
            output_path: 输出路径
            resolution: 目标分辨率
            bitrate: 目标码率
            target_fps: 参考帧率（用于决策，不强制统一）
            quality_mode: 质量模式
                - "preserve": 最大程度保持原画质，容忍轻微不一致
                - "balance": 平衡画质和一致性
                - "strict": 严格统一，保证完美同步
        
        Returns:
            Dict: 拼接结果
        """
        logger.info(f"🎯 启动画质保持模式拼接: {quality_mode}")
        
        temp_dir = f"temp_{int(time.time())}"
        os.makedirs(temp_dir, exist_ok=True)
        
        try:
            # 🔧 分析片段兼容性
            compatibility = self.analyze_segments_compatibility(selected_segments)
            needs_standardization = compatibility.get('needs_standardization', True)
            fps_variance = compatibility.get('fps_variance', 0)
            resolution_consistent = compatibility.get('resolution_consistent', True)
            
            logger.info(f"📊 兼容性分析: 需要标准化={needs_standardization}, 帧率差异={fps_variance:.1f}fps")
            
            # 🌟 修改preserve模式的条件 - 更宽松的画质保持策略
            if quality_mode == "preserve":
                # 🌟 新策略：除非绝对必要，否则不重编码
                if resolution_consistent:
                    # 分辨率一致时，即使帧率差异很大也优先保持原画质
                    logger.info("🌟 使用超高画质保持模式（分辨率一致，容忍帧率差异）")
                    return self._compose_with_ultra_preserve_mode(selected_segments, output_path, temp_dir)
                elif fps_variance <= 30.0:  # 🔧 将阈值从5fps提升到30fps
                    # 帧率差异不是特别极端时，使用最小化重编码
                    logger.info("🌟 使用高画质保持模式（最小化重编码）")
                    return self._compose_with_minimal_reencoding(selected_segments, output_path, temp_dir)
                else:
                    # 帧率差异极端时，使用智能重编码
                    logger.warning(f"⚠️ 帧率差异过大({fps_variance:.1f}fps)，回退到智能重编码")
                    return self._compose_with_smart_reencoding(selected_segments, output_path, temp_dir, target_fps, resolution)
                
            elif quality_mode == "balance":
                # ⚖️ 平衡模式：智能选择性重编码
                logger.info("⚖️ 使用平衡模式（智能重编码）")
                return self._compose_with_smart_reencoding(selected_segments, output_path, temp_dir, target_fps, resolution)
                
            else:
                # 🔒 严格模式：使用现有的完全标准化
                logger.info("🔒 使用严格模式（完全标准化）")
                return self.compose_video_with_ffmpeg(selected_segments, output_path, resolution, bitrate, target_fps)
                
        except Exception as e:
            logger.error(f"❌ 画质保持拼接失败: {e}")
            # 回退到标准模式
            logger.info("🔄 回退到标准拼接模式")
            return self.compose_video_with_ffmpeg(selected_segments, output_path, resolution, bitrate, target_fps)
        finally:
            # 清理临时文件
            if os.path.exists(temp_dir):
                import shutil
                shutil.rmtree(temp_dir, ignore_errors=True)
    
    def _compose_with_ultra_preserve_mode(self, selected_segments: Dict[str, List[Dict]], output_path: str, temp_dir: str) -> Dict[str, Any]:
        """🌟 超高画质保持模式 - 绝对最小化重编码"""
        start_time = time.time()
        
        logger.info("🌟 启动超高画质保持模式：分辨率一致，容忍帧率差异")
        print("🌟 超高画质模式：完全避免重编码，保持原始画质")
        
        # 创建片段文件列表
        concat_file_path = os.path.join(temp_dir, "ultra_preserve_concat_list.txt")
        all_segments = []
        for module, segments in selected_segments.items():
            all_segments.extend(segments)
        
        valid_segments = 0
        
        # 🔧 构建concat文件，直接使用原始文件路径
        with open(concat_file_path, 'w', encoding='utf-8') as f:
            for segment in all_segments:
                video_path = segment.get('file_path') or segment.get('video_path') or segment.get('path')
                
                # 构建路径逻辑
                if not video_path:
                    video_id = segment.get('video_id', '')
                    file_name = segment.get('file_name', '')
                    if video_id and file_name:
                        video_path = f"data/output/google_video/video_pool/{video_id}/{file_name}"
                    elif file_name:
                        video_path = f"data/output/google_video/video_pool/{file_name}"
                
                if video_path and os.path.exists(video_path):
                    # 🌟 直接使用原始路径，不进行任何预处理
                    abs_path = os.path.abspath(video_path)
                    escaped_path = abs_path.replace("'", "'\"'\"'")
                    f.write(f"file '{escaped_path}'\n")
                    valid_segments += 1
                    logger.debug(f"✅ 直接添加原始片段: {os.path.basename(video_path)}")
                else:
                    logger.warning(f"❌ 片段文件不存在: {video_path}")
        
        if valid_segments == 0:
            logger.error("❌ 没有找到有效的视频片段文件")
            raise Exception("没有找到有效的视频片段文件")
        
        logger.info(f"🌟 超高画质模式: 直接拼接 {valid_segments} 个原始片段")
        
        # 🌟 使用stream copy进行完全无损拼接
        ffmpeg_cmd = [
            'ffmpeg',
            '-f', 'concat',
            '-safe', '0',
            '-i', concat_file_path,
            
            # 🌟 关键：完全流复制，避免任何重编码
            '-c', 'copy',                    # 所有流都使用copy
            '-avoid_negative_ts', 'make_zero',  # 避免负时间戳
            '-fflags', '+genpts',            # 生成新的时间戳
            '-movflags', '+faststart',       # 优化播放
            
            '-y',
            output_path
        ]
        
        logger.info(f"🌟 执行超高画质拼接: {' '.join(ffmpeg_cmd)}")
        print(f"🌟 FFmpeg超高画质拼接命令")
        
        try:
            result = subprocess.run(ffmpeg_cmd, capture_output=True, text=True, timeout=300)
            
            if result.returncode == 0:
                composition_time = time.time() - start_time
                output_info = self.get_detailed_video_info(output_path)
                
                logger.info(f"✅ 超高画质拼接成功，耗时 {composition_time:.2f}s")
                print(f"✅ 超高画质拼接完成！耗时 {composition_time:.2f}s，完全保持原画质")
                
                return {
                    "success": True,
                    "output_path": output_path,
                    "composition_time": composition_time,
                    "output_info": output_info,
                    "quality_mode": "ultra_preserve",
                    "reencoding": "none",
                    "preserved_segments": valid_segments,
                    "message": "✅ 超高画质拼接完成，100%保持原始画质"
                }
            else:
                logger.warning(f"⚠️ 超高画质拼接失败，FFmpeg错误: {result.stderr}")
                print(f"⚠️ 超高画质拼接失败，回退到最小化重编码模式")
                # 回退到最小化重编码
                return self._compose_with_minimal_reencoding(selected_segments, output_path, temp_dir)
                
        except subprocess.TimeoutExpired:
            logger.error("❌ 超高画质拼接超时")
            raise Exception("超高画质拼接超时")
        except Exception as e:
            logger.error(f"❌ 超高画质拼接异常: {e}")
            # 回退到最小化重编码
            return self._compose_with_minimal_reencoding(selected_segments, output_path, temp_dir)
    
    def _compose_with_minimal_reencoding(self, selected_segments: Dict[str, List[Dict]], output_path: str, temp_dir: str) -> Dict[str, Any]:
        """🌟 最小化重编码的高画质拼接"""
        start_time = time.time()
        
        # 创建片段文件列表
        concat_file_path = os.path.join(temp_dir, "concat_list.txt")
        all_segments = []
        for module, segments in selected_segments.items():
            all_segments.extend(segments)
        
        # 🔧 构建concat文件（使用stream copy）
        with open(concat_file_path, 'w', encoding='utf-8') as f:
            for segment in all_segments:
                video_path = segment.get('segment_path') or segment.get('file_path')
                if video_path and os.path.exists(video_path):
                    f.write(f"file '{os.path.abspath(video_path)}'\n")
        
        # 🌟 使用stream copy进行无损拼接
        ffmpeg_cmd = [
            'ffmpeg',
            '-f', 'concat',
            '-safe', '0',
            '-i', concat_file_path,
            '-c', 'copy',  # 🌟 关键：流复制，避免重编码
            '-avoid_negative_ts', 'make_zero',
            '-fflags', '+genpts',  # 生成新的时间戳
            '-y',
            output_path
        ]
        
        logger.info(f"🌟 执行高画质拼接: {' '.join(ffmpeg_cmd)}")
        
        try:
            result = subprocess.run(ffmpeg_cmd, capture_output=True, text=True, timeout=300)
            
            if result.returncode == 0:
                composition_time = time.time() - start_time
                output_info = self.get_detailed_video_info(output_path)
                
                return {
                    "success": True,
                    "output_path": output_path,
                    "composition_time": composition_time,
                    "output_info": output_info,
                    "quality_mode": "preserve",
                    "reencoding": "minimal",
                    "message": "✅ 高画质拼接完成，最大程度保持原始画质"
                }
            else:
                logger.warning(f"⚠️ 高画质拼接失败，回退到智能重编码: {result.stderr}")
                return self._compose_with_smart_reencoding(selected_segments, output_path, temp_dir, 30, "1080x1920")
                
        except subprocess.TimeoutExpired:
            logger.error("❌ 高画质拼接超时")
            raise
        except Exception as e:
            logger.error(f"❌ 高画质拼接异常: {e}")
            raise
    
    def _compose_with_smart_reencoding(self, selected_segments: Dict[str, List[Dict]], output_path: str, temp_dir: str, target_fps: int, resolution: str) -> Dict[str, Any]:
        """⚖️ 智能重编码的平衡模式拼接"""
        start_time = time.time()
        
        # 🔧 分析需要重编码的片段
        reencoding_plan = self._analyze_reencoding_needs(selected_segments, target_fps, resolution)
        
        # 预处理需要重编码的片段
        processed_segments = []
        for segment in reencoding_plan["segments"]:
            if segment["needs_reencoding"]:
                # 使用高质量设置重编码
                processed_path = self._reencode_segment_high_quality(
                    segment["original_path"], 
                    temp_dir, 
                    target_fps, 
                    resolution
                )
                processed_segments.append(processed_path)
            else:
                # 直接使用原始文件
                processed_segments.append(segment["original_path"])
        
        # 🔧 使用stream copy拼接处理后的片段
        concat_file_path = os.path.join(temp_dir, "smart_concat_list.txt")
        with open(concat_file_path, 'w', encoding='utf-8') as f:
            for seg_path in processed_segments:
                f.write(f"file '{os.path.abspath(seg_path)}'\n")
        
        ffmpeg_cmd = [
            'ffmpeg',
            '-f', 'concat',
            '-safe', '0',
            '-i', concat_file_path,
            '-c', 'copy',  # 处理后的片段使用stream copy
            '-avoid_negative_ts', 'make_zero',
            '-y',
            output_path
        ]
        
        logger.info(f"⚖️ 执行智能重编码拼接")
        
        result = subprocess.run(ffmpeg_cmd, capture_output=True, text=True, timeout=300)
        
        if result.returncode == 0:
            composition_time = time.time() - start_time
            output_info = self.get_detailed_video_info(output_path)
            
            return {
                "success": True,
                "output_path": output_path,
                "composition_time": composition_time,
                "output_info": output_info,
                "quality_mode": "balance",
                "reencoding": "selective",
                "reencoded_count": len([s for s in reencoding_plan["segments"] if s["needs_reencoding"]]),
                "message": "✅ 智能重编码拼接完成，平衡画质与一致性"
            }
        else:
            logger.error(f"❌ 智能重编码拼接失败: {result.stderr}")
            raise Exception(f"智能重编码拼接失败: {result.stderr}")
    
    def _analyze_reencoding_needs(self, selected_segments: Dict[str, List[Dict]], target_fps: int, target_resolution: str) -> Dict[str, Any]:
        """分析哪些片段需要重编码"""
        all_segments = []
        for module, segments in selected_segments.items():
            all_segments.extend(segments)
        
        analysis = {
            "segments": [],
            "total_count": len(all_segments),
            "reencoding_count": 0
        }
        
        for segment in all_segments:
            video_path = segment.get('segment_path') or segment.get('file_path')
            info = self.get_detailed_video_info(video_path)
            
            needs_reencoding = False
            reasons = []
            
            # 检查帧率差异
            current_fps = info.get('fps', 30)
            if abs(current_fps - target_fps) > target_fps * 0.15:  # 允许15%的差异
                needs_reencoding = True
                reasons.append(f"帧率差异过大: {current_fps:.1f}fps vs {target_fps}fps")
            
            # 检查分辨率差异
            current_resolution = f"{info.get('width', 0)}x{info.get('height', 0)}"
            if current_resolution != target_resolution:
                needs_reencoding = True
                reasons.append(f"分辨率不匹配: {current_resolution} vs {target_resolution}")
            
            # 检查编码格式
            if info.get('video_codec') not in ['h264', 'libx264']:
                needs_reencoding = True
                reasons.append(f"编码格式需要转换: {info.get('video_codec')}")
            
            analysis["segments"].append({
                "original_path": video_path,
                "needs_reencoding": needs_reencoding,
                "reasons": reasons,
                "current_info": info
            })
            
            if needs_reencoding:
                analysis["reencoding_count"] += 1
        
        logger.info(f"📊 重编码分析: {analysis['reencoding_count']}/{analysis['total_count']} 个片段需要重编码")
        return analysis
    
    def _reencode_segment_high_quality(self, input_path: str, temp_dir: str, target_fps: int, target_resolution: str) -> str:
        """使用高质量设置重编码单个片段"""
        output_path = os.path.join(temp_dir, f"hq_{os.path.basename(input_path)}")
        
        # 🌟 使用更高质量的编码设置
        ffmpeg_cmd = [
            'ffmpeg',
            '-i', input_path,
            '-c:v', 'libx264',
            '-preset', 'slow',        # 🌟 更慢但更高质量的预设
            '-crf', '18',             # 🌟 更低的CRF值 = 更高质量
            '-profile:v', 'high',     # 🌟 使用高级编码档次
            '-level:v', '4.1',        # 🌟 指定编码级别
            '-vf', f"scale={target_resolution}:flags=lanczos,fps={target_fps}:round=near",
            '-pix_fmt', 'yuv420p',
            '-movflags', '+faststart', # 🌟 优化流媒体播放
            '-y',
            output_path
        ]
        
        # 处理音频（如果有）
        info = self.get_detailed_video_info(input_path)
        if info.get('has_audio'):
            audio_params = [
                '-c:a', 'aac',
                '-b:a', '192k',    # 🌟 更高的音频码率
                '-ar', '48000',    # 🌟 更高的采样率
                '-ac', '2'
            ]
            ffmpeg_cmd = ffmpeg_cmd[:-2] + audio_params + ffmpeg_cmd[-2:]
        else:
            ffmpeg_cmd.insert(-2, '-an')
        
        logger.debug(f"🌟 高质量重编码: {os.path.basename(input_path)}")
        
        result = subprocess.run(ffmpeg_cmd, capture_output=True, text=True, timeout=120)
        
        if result.returncode == 0:
            return output_path
        else:
            logger.error(f"❌ 高质量重编码失败: {result.stderr}")
            raise Exception(f"高质量重编码失败: {result.stderr}")

# 工具函数
def create_output_filename(prefix: str = "composed_video") -> str:
    """
    创建输出文件名
    
    Args:
        prefix: 文件名前缀
        
    Returns:
        str: 完整的输出文件路径
    """
    import datetime
    
    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"{prefix}_{timestamp}.mp4"
    
    # 🔧 智能检测输出目录位置
    current_work_dir = os.getcwd()
    if current_work_dir.endswith("streamlit_app"):
        # 如果在streamlit_app目录中运行
        output_dir = "../data/output/composed_video"
    else:
        # 如果在项目根目录中运行
        output_dir = "data/output/composed_video"
    
    os.makedirs(output_dir, exist_ok=True)
    
    return os.path.join(output_dir, filename) 