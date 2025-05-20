#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
音频处理工具模块 - 提供音频文件处理功能
"""

import os
import time
import logging
import tempfile
import subprocess
from typing import Optional, Dict, Any, List, Tuple

# 设置日志
logger = logging.getLogger(__name__)

class AudioProcessor:
    """音频处理工具类，提供音频文件处理功能"""
    
    def __init__(self, temp_dir: Optional[str] = None):
        """
        初始化音频处理器
        
        Args:
            temp_dir: 临时文件目录，默认为系统临时目录
        """
        # 临时目录设置
        self.temp_dir = temp_dir or tempfile.mkdtemp(prefix="audio_processor_")
        os.makedirs(self.temp_dir, exist_ok=True)
        
        logger.info("初始化音频处理器")
    
    def extract_audio(self, video_path: str, output_path: Optional[str] = None, 
                     sample_rate: int = 16000, channels: int = 1) -> Optional[str]:
        """
        从视频中提取音频
        
        Args:
            video_path: 视频文件路径
            output_path: 输出音频文件路径，默认为None（使用临时文件）
            sample_rate: 采样率，默认16000Hz
            channels: 声道数，默认1（单声道）
            
        Returns:
            提取的音频文件路径或None（如果提取失败）
        """
        if not os.path.exists(video_path):
            logger.error(f"视频文件不存在: {video_path}")
            return None
        
        # 如果未指定输出路径，则使用临时文件
        if not output_path:
            output_path = os.path.join(
                self.temp_dir, 
                f"{int(time.time())}_{os.path.splitext(os.path.basename(video_path))[0]}.wav"
            )
        
        try:
            # 使用ffmpeg提取和预处理音频
            cmd = [
                "ffmpeg", "-y", "-i", video_path,
                "-vn", "-acodec", "pcm_s16le", 
                "-ar", str(sample_rate), "-ac", str(channels),
                "-af", "highpass=f=50,lowpass=f=8000,dynaudnorm",
                output_path
            ]
            
            result = subprocess.run(cmd, capture_output=True, text=True)
            if result.returncode != 0:
                logger.error(f"音频提取失败: {result.stderr}")
                return None
            
            if os.path.exists(output_path):
                logger.info(f"音频提取成功: {output_path}")
                return output_path
            else:
                logger.error(f"音频提取后文件不存在: {output_path}")
                return None
        except Exception as e:
            logger.error(f"提取音频时发生错误: {str(e)}")
            return None
    
    def optimize_audio(self, input_path: str, output_path: Optional[str] = None, 
                       normalize: bool = True, noise_reduction: bool = True,
                       sample_rate: int = 16000) -> Optional[str]:
        """
        优化音频质量
        
        Args:
            input_path: 输入音频文件路径
            output_path: 输出音频文件路径，默认为None（使用临时文件）
            normalize: 是否进行音量归一化处理，默认为True
            noise_reduction: 是否进行降噪处理，默认为True
            sample_rate: 采样率，默认16000Hz
            
        Returns:
            优化后的音频文件路径或None（如果优化失败）
        """
        if not os.path.exists(input_path):
            logger.error(f"音频文件不存在: {input_path}")
            return None
        
        # 如果未指定输出路径，则使用临时文件
        if not output_path:
            output_path = os.path.join(
                self.temp_dir, 
                f"optimized_{int(time.time())}_{os.path.basename(input_path)}"
            )
        
        try:
            # 构建音频滤镜
            filters = []
            
            if noise_reduction:
                filters.append("highpass=f=50,lowpass=f=8000")
            
            if normalize:
                filters.append("dynaudnorm")
            
            filter_chain = ",".join(filters) if filters else "copy"
            
            # 使用ffmpeg优化音频
            cmd = [
                "ffmpeg", "-y", "-i", input_path,
                "-ar", str(sample_rate),
                "-af", filter_chain,
                output_path
            ]
            
            result = subprocess.run(cmd, capture_output=True, text=True)
            if result.returncode != 0:
                logger.error(f"音频优化失败: {result.stderr}")
                return None
            
            if os.path.exists(output_path):
                logger.info(f"音频优化成功: {output_path}")
                return output_path
            else:
                logger.error(f"音频优化后文件不存在: {output_path}")
                return None
        except Exception as e:
            logger.error(f"优化音频时发生错误: {str(e)}")
            return None
    
    def get_audio_info(self, audio_path: str) -> Optional[Dict[str, Any]]:
        """
        获取音频文件信息
        
        Args:
            audio_path: 音频文件路径
            
        Returns:
            音频信息字典或None（如果获取失败）
        """
        if not os.path.exists(audio_path):
            logger.error(f"音频文件不存在: {audio_path}")
            return None
        
        try:
            # 使用ffprobe获取音频信息
            cmd = [
                "ffprobe", 
                "-v", "quiet", 
                "-print_format", "json", 
                "-show_format", 
                "-show_streams", 
                audio_path
            ]
            
            result = subprocess.run(cmd, capture_output=True, text=True)
            if result.returncode != 0:
                logger.error(f"获取音频信息失败: {result.stderr}")
                return None
            
            import json
            info = json.loads(result.stdout)
            
            # 提取关键信息
            audio_stream = next((s for s in info.get("streams", []) if s.get("codec_type") == "audio"), None)
            
            if not audio_stream:
                logger.warning(f"无法找到音频流: {audio_path}")
                return info
            
            # 计算音频时长（秒）
            duration = float(info.get("format", {}).get("duration", 0))
            
            # 构建结果
            result = {
                "duration": duration,
                "sample_rate": int(audio_stream.get("sample_rate", 0)),
                "channels": int(audio_stream.get("channels", 0)),
                "codec": audio_stream.get("codec_name"),
                "format": info.get("format", {}).get("format_name"),
                "bit_rate": int(info.get("format", {}).get("bit_rate", 0)),
                "raw": info
            }
            
            return result
        except Exception as e:
            logger.error(f"获取音频信息时发生错误: {str(e)}")
            return None 