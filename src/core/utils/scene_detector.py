#!/usr/bin/env python3
"""
视频场景检测模块
用于检测视频中的镜头边界、场景变化和关键帧
"""

import cv2
import numpy as np
import os
import subprocess
import json
import logging
from typing import List, Dict, Tuple, Optional
from pathlib import Path

logger = logging.getLogger(__name__)

class SceneDetector:
    """视频场景检测器"""
    
    def __init__(self, threshold: float = 0.3, min_scene_length: float = 1.0, detection_interval: float = 0.1):
        """
        初始化场景检测器
        
        Args:
            threshold: 场景变化检测阈值 (0.0-1.0)
            min_scene_length: 最小场景长度（秒）
            detection_interval: 检测间隔（秒），控制检测精度
        """
        self.threshold = threshold
        self.min_scene_length = min_scene_length
        self.detection_interval = detection_interval
        
    def detect_scenes(self, video_path: str, method: str = "content") -> List[Dict]:
        """
        检测视频中的场景边界
        
        Args:
            video_path: 视频文件路径
            method: 检测方法 ("content", "histogram", "ffmpeg")
            
        Returns:
            场景列表，每个场景包含start_time, end_time, confidence等信息
        """
        if not os.path.exists(video_path):
            raise FileNotFoundError(f"视频文件不存在: {video_path}")
            
        logger.info(f"开始检测视频场景: {video_path}, 方法: {method}")
        
        if method == "ffmpeg":
            return self._detect_scenes_ffmpeg(video_path)
        elif method == "histogram":
            return self._detect_scenes_histogram(video_path)
        else:
            return self._detect_scenes_content(video_path)
    
    def _detect_scenes_ffmpeg(self, video_path: str) -> List[Dict]:
        """
        使用FFmpeg的场景检测滤镜 - 专业级检测方法
        """
        logger.info("使用FFmpeg专业场景检测")
        
        # 首先检查FFmpeg是否可用
        try:
            subprocess.run(["ffmpeg", "-version"], capture_output=True, check=True)
        except (subprocess.CalledProcessError, FileNotFoundError):
            logger.error("FFmpeg未安装或不可用，回退到内容检测方法")
            return self._detect_scenes_content(video_path)
        
        # 获取视频时长
        video_duration = self._get_video_duration(video_path)
        if video_duration <= 0:
            logger.error("无法获取视频时长")
            return []
        
        # FFmpeg的scene滤镜阈值需要调整
        # 根据实际测试，scene分数范围从0.001到0.6+
        # 调整映射使其更敏感，能检测到更多场景变化
        if self.threshold <= 0.2:
            ffmpeg_threshold = 0.005  # 极高敏感度
        elif self.threshold <= 0.4:
            ffmpeg_threshold = 0.015  # 高敏感度  
        elif self.threshold <= 0.6:
            ffmpeg_threshold = 0.025  # 中等敏感度
        else:
            ffmpeg_threshold = 0.035  # 低敏感度
        
        logger.info(f"FFmpeg场景检测阈值: {ffmpeg_threshold:.3f} (原始: {self.threshold})")
        
        # 使用metadata输出来获取scene分数和时间信息
        cmd = [
            "ffmpeg", 
            "-i", video_path,
            "-filter:v", f"select='gt(scene,{ffmpeg_threshold})',metadata=print:file=-",
            "-f", "null", 
            "-",
            "-v", "quiet"  # 减少输出噪音
        ]
        
        try:
            logger.debug(f"执行FFmpeg命令: {' '.join(cmd)}")
            result = subprocess.run(
                cmd, 
                capture_output=True, 
                text=True, 
                check=False,
                timeout=300
            )
            
            # 解析metadata输出中的场景变化信息
            scene_times = []
            confidence_scores = []
            
            lines = result.stderr.split('\n')
            current_time = None
            
            for line in lines:
                line = line.strip()
                
                # 解析时间信息 - 格式: frame:0    pts:13      pts_time:0.433333
                if line.startswith('frame:') and 'pts_time:' in line:
                    try:
                        pts_time_part = line.split('pts_time:')[1]
                        current_time = float(pts_time_part.strip())
                    except (ValueError, IndexError):
                        continue
                
                # 解析scene分数 - 格式: lavfi.scene_score=0.656445
                elif line.startswith('lavfi.scene_score=') and current_time is not None:
                    try:
                        scene_score = float(line.split('=')[1])
                        
                        # 如果分数超过阈值，记录场景变化
                        if scene_score > ffmpeg_threshold:
                            confidence = min(1.0, scene_score / ffmpeg_threshold)
                            scene_times.append(current_time)
                            confidence_scores.append(confidence)
                            logger.debug(f"检测到场景变化: {current_time:.3f}s, 分数: {scene_score:.3f}, 置信度: {confidence:.3f}")
                        
                        # 重置当前时间
                        current_time = None
                        
                    except (ValueError, IndexError):
                        continue
            
            # 如果没有检测到场景变化，尝试更低的阈值
            if not scene_times and ffmpeg_threshold > 0.005:
                logger.warning(f"未检测到场景变化，尝试更低阈值: {ffmpeg_threshold/2:.4f}")
                lower_threshold = ffmpeg_threshold / 2
                
                cmd_retry = [
                    "ffmpeg", 
                    "-i", video_path,
                    "-filter:v", f"select='gt(scene,{lower_threshold})',metadata=print:file=-",
                    "-f", "null", 
                    "-",
                    "-v", "quiet"
                ]
                
                result_retry = subprocess.run(
                    cmd_retry, 
                    capture_output=True, 
                    text=True, 
                    check=False,
                    timeout=300
                )
                
                # 重新解析输出
                lines_retry = result_retry.stderr.split('\n')
                current_time = None
                
                for line in lines_retry:
                    line = line.strip()
                    
                    if line.startswith('frame:') and 'pts_time:' in line:
                        try:
                            pts_time_part = line.split('pts_time:')[1]
                            current_time = float(pts_time_part.strip())
                        except (ValueError, IndexError):
                            continue
                    
                    elif line.startswith('lavfi.scene_score=') and current_time is not None:
                        try:
                            scene_score = float(line.split('=')[1])
                            
                            if scene_score > lower_threshold:
                                confidence = min(1.0, scene_score / lower_threshold)
                                scene_times.append(current_time)
                                confidence_scores.append(confidence)
                                logger.debug(f"低阈值检测到场景变化: {current_time:.3f}s, 分数: {scene_score:.3f}")
                            
                            current_time = None
                            
                        except (ValueError, IndexError):
                            continue
            
            # 过滤太近的场景变化点
            filtered_times = []
            filtered_confidences = []
            
            for i, (time, conf) in enumerate(zip(scene_times, confidence_scores)):
                if not filtered_times or time - filtered_times[-1] >= self.min_scene_length:
                    filtered_times.append(time)
                    filtered_confidences.append(conf)
                else:
                    logger.debug(f"过滤掉太近的场景变化: {time:.3f}s (距离上一个: {time - filtered_times[-1]:.3f}s)")
            
            # 构建场景列表
            scenes = []
            
            if filtered_times:
                # 第一个场景 (从0开始)
                scenes.append({
                    "start_time": 0.0,
                    "end_time": filtered_times[0],
                    "confidence": 1.0,
                    "method": "ffmpeg",
                    "scene_score": 0.0
                })
                
                # 中间场景
                for i in range(len(filtered_times) - 1):
                    scenes.append({
                        "start_time": filtered_times[i],
                        "end_time": filtered_times[i + 1],
                        "confidence": filtered_confidences[i],
                        "method": "ffmpeg",
                        "scene_score": filtered_confidences[i] * ffmpeg_threshold
                    })
                
                # 最后场景 (到视频结束)
                scenes.append({
                    "start_time": filtered_times[-1],
                    "end_time": video_duration,
                    "confidence": filtered_confidences[-1],
                    "method": "ffmpeg",
                    "scene_score": filtered_confidences[-1] * ffmpeg_threshold
                })
                
            else:
                # 如果仍然没有检测到场景变化，回退到content方法
                logger.warning("FFmpeg未检测到场景变化，回退到content方法")
                return self._detect_scenes_content(video_path)
            
            # 验证场景时间的合理性
            valid_scenes = []
            for scene in scenes:
                if scene["end_time"] > scene["start_time"]:
                    valid_scenes.append(scene)
                else:
                    logger.warning(f"跳过无效场景: {scene['start_time']:.3f}s - {scene['end_time']:.3f}s")
            
            logger.info(f"FFmpeg检测到 {len(valid_scenes)} 个有效场景 (原始: {len(scene_times)}, 过滤后: {len(filtered_times)})")
            return valid_scenes
            
        except subprocess.TimeoutExpired:
            logger.error("FFmpeg场景检测超时，回退到内容检测方法")
            return self._detect_scenes_content(video_path)
        except Exception as e:
            logger.error(f"FFmpeg场景检测失败: {e}")
            logger.info("回退到内容检测方法")
            return self._detect_scenes_content(video_path)
    
    def _detect_scenes_content(self, video_path: str) -> List[Dict]:
        """
        基于内容的场景检测（使用OpenCV）
        """
        logger.info("使用OpenCV内容分析进行场景检测")
        
        cap = cv2.VideoCapture(video_path)
        if not cap.isOpened():
            raise RuntimeError(f"无法打开视频文件: {video_path}")
        
        fps = cap.get(cv2.CAP_PROP_FPS)
        frame_count = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        duration = frame_count / fps
        
        logger.info(f"视频信息: {frame_count} 帧, {fps:.2f} FPS, {duration:.2f} 秒")
        
        scenes = []
        scene_changes = []
        prev_frame = None
        frame_idx = 0
        
        # 每隔一定帧数检测一次（使用动态精度设置）
        check_interval = max(1, int(fps * self.detection_interval))
        logger.info(f"检测间隔: {self.detection_interval}秒 ({check_interval}帧)")
        
        while True:
            ret, frame = cap.read()
            if not ret:
                break
            
            if frame_idx % check_interval == 0:
                # 转换为灰度图
                gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
                
                if prev_frame is not None:
                    # 计算帧间差异
                    diff = cv2.absdiff(prev_frame, gray)
                    diff_score = np.mean(diff) / 255.0
                    
                    # 如果差异超过阈值，认为是场景变化
                    if diff_score > self.threshold:
                        timestamp = frame_idx / fps
                        scene_changes.append({
                            "time": timestamp,
                            "confidence": min(1.0, diff_score / self.threshold)
                        })
                        logger.debug(f"检测到场景变化: {timestamp:.2f}s, 置信度: {diff_score:.3f}")
                
                prev_frame = gray.copy()
            
            frame_idx += 1
        
        cap.release()
        
        # 过滤太近的场景变化点
        filtered_changes = []
        for change in scene_changes:
            if not filtered_changes or change["time"] - filtered_changes[-1]["time"] >= self.min_scene_length:
                filtered_changes.append(change)
        
        # 构建场景列表
        if filtered_changes:
            # 第一个场景
            scenes.append({
                "start_time": 0.0,
                "end_time": filtered_changes[0]["time"],
                "confidence": 1.0,
                "method": "content"
            })
            
            # 中间场景
            for i in range(len(filtered_changes) - 1):
                scenes.append({
                    "start_time": filtered_changes[i]["time"],
                    "end_time": filtered_changes[i + 1]["time"],
                    "confidence": filtered_changes[i]["confidence"],
                    "method": "content"
                })
            
            # 最后场景
            scenes.append({
                "start_time": filtered_changes[-1]["time"],
                "end_time": duration,
                "confidence": filtered_changes[-1]["confidence"],
                "method": "content"
            })
        else:
            # 没有检测到场景变化
            scenes.append({
                "start_time": 0.0,
                "end_time": duration,
                "confidence": 1.0,
                "method": "content"
            })
        
        logger.info(f"内容分析检测到 {len(scenes)} 个场景")
        return scenes
    
    def _detect_scenes_histogram(self, video_path: str) -> List[Dict]:
        """
        基于直方图的场景检测
        """
        logger.info("使用直方图分析进行场景检测")
        
        cap = cv2.VideoCapture(video_path)
        if not cap.isOpened():
            raise RuntimeError(f"无法打开视频文件: {video_path}")
        
        fps = cap.get(cv2.CAP_PROP_FPS)
        frame_count = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        duration = frame_count / fps
        
        scenes = []
        scene_changes = []
        prev_hist = None
        frame_idx = 0
        
        # 每隔一定帧数检测一次（使用动态精度设置）
        check_interval = max(1, int(fps * self.detection_interval))
        logger.info(f"检测间隔: {self.detection_interval}秒 ({check_interval}帧)")
        
        while True:
            ret, frame = cap.read()
            if not ret:
                break
            
            if frame_idx % check_interval == 0:
                # 计算颜色直方图
                hist = cv2.calcHist([frame], [0, 1, 2], None, [50, 50, 50], [0, 256, 0, 256, 0, 256])
                hist = cv2.normalize(hist, hist).flatten()
                
                if prev_hist is not None:
                    # 计算直方图相关性
                    correlation = cv2.compareHist(prev_hist, hist, cv2.HISTCMP_CORREL)
                    
                    # 相关性低表示场景变化大
                    if correlation < (1.0 - self.threshold):
                        timestamp = frame_idx / fps
                        confidence = 1.0 - correlation
                        scene_changes.append({
                            "time": timestamp,
                            "confidence": confidence
                        })
                        logger.debug(f"检测到场景变化: {timestamp:.2f}s, 相关性: {correlation:.3f}")
                
                prev_hist = hist.copy()
            
            frame_idx += 1
        
        cap.release()
        
        # 过滤和构建场景列表（与content方法相同）
        filtered_changes = []
        for change in scene_changes:
            if not filtered_changes or change["time"] - filtered_changes[-1]["time"] >= self.min_scene_length:
                filtered_changes.append(change)
        
        if filtered_changes:
            scenes.append({
                "start_time": 0.0,
                "end_time": filtered_changes[0]["time"],
                "confidence": 1.0,
                "method": "histogram"
            })
            
            for i in range(len(filtered_changes) - 1):
                scenes.append({
                    "start_time": filtered_changes[i]["time"],
                    "end_time": filtered_changes[i + 1]["time"],
                    "confidence": filtered_changes[i]["confidence"],
                    "method": "histogram"
                })
            
            scenes.append({
                "start_time": filtered_changes[-1]["time"],
                "end_time": duration,
                "confidence": filtered_changes[-1]["confidence"],
                "method": "histogram"
            })
        else:
            scenes.append({
                "start_time": 0.0,
                "end_time": duration,
                "confidence": 1.0,
                "method": "histogram"
            })
        
        logger.info(f"直方图分析检测到 {len(scenes)} 个场景")
        return scenes
    
    def _get_video_duration(self, video_path: str) -> float:
        """获取视频时长"""
        try:
            cmd = [
                "ffprobe", "-v", "error",
                "-show_entries", "format=duration",
                "-of", "default=noprint_wrappers=1:nokey=1",
                video_path
            ]
            
            result = subprocess.run(cmd, capture_output=True, text=True, check=False)
            if result.returncode == 0:
                return float(result.stdout.strip())
            else:
                # 备用方法：使用OpenCV
                cap = cv2.VideoCapture(video_path)
                fps = cap.get(cv2.CAP_PROP_FPS)
                frame_count = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
                cap.release()
                return frame_count / fps if fps > 0 else 0.0
                
        except Exception as e:
            logger.error(f"获取视频时长失败: {e}")
            return 0.0
    
    def merge_scenes_with_semantic_segments(self, scenes: List[Dict], semantic_segments: List[Dict]) -> List[Dict]:
        """
        将场景边界与语义分段合并，确保切分点在场景边界上
        
        Args:
            scenes: 场景列表
            semantic_segments: 语义分段列表
            
        Returns:
            合并后的分段列表
        """
        logger.info("合并场景边界与语义分段")
        
        # 提取所有场景边界时间点
        scene_boundaries = set()
        for scene in scenes:
            scene_boundaries.add(scene["start_time"])
            scene_boundaries.add(scene["end_time"])
        
        scene_boundaries = sorted(list(scene_boundaries))
        
        merged_segments = []
        
        for segment in semantic_segments:
            start_time = segment.get("start_time", 0.0)
            end_time = segment.get("end_time", 0.0)
            
            # 找到最接近的场景边界
            adjusted_start = self._find_nearest_boundary(start_time, scene_boundaries)
            adjusted_end = self._find_nearest_boundary(end_time, scene_boundaries)
            
            # 确保调整后的时间仍然有效
            if adjusted_start >= adjusted_end:
                # 如果调整后时间无效，使用原始时间
                adjusted_start = start_time
                adjusted_end = end_time
                logger.warning(f"场景边界调整失败，使用原始时间: {start_time:.2f}s - {end_time:.2f}s")
            else:
                logger.info(f"分段边界已调整到场景边界: {start_time:.2f}s - {end_time:.2f}s → {adjusted_start:.2f}s - {adjusted_end:.2f}s")
            
            # 创建调整后的分段
            adjusted_segment = segment.copy()
            adjusted_segment["start_time"] = adjusted_start
            adjusted_segment["end_time"] = adjusted_end
            adjusted_segment["scene_aligned"] = True
            
            merged_segments.append(adjusted_segment)
        
        return merged_segments
    
    def _find_nearest_boundary(self, time: float, boundaries: List[float], max_distance: float = 2.0) -> float:
        """
        找到最接近的场景边界
        
        Args:
            time: 目标时间
            boundaries: 边界时间列表
            max_distance: 最大调整距离（秒）
            
        Returns:
            调整后的时间
        """
        if not boundaries:
            return time
        
        # 找到最接近的边界
        distances = [abs(time - boundary) for boundary in boundaries]
        min_distance_idx = distances.index(min(distances))
        nearest_boundary = boundaries[min_distance_idx]
        
        # 如果距离在允许范围内，使用边界时间
        if distances[min_distance_idx] <= max_distance:
            return nearest_boundary
        else:
            return time 