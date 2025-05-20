#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
视频处理工具模块 - 提供视频文件处理和上传功能
"""

import os
import time
import uuid
import logging
import tempfile
import subprocess
from pathlib import Path
from typing import Optional, Dict, Any

import oss2
from dotenv import load_dotenv
from moviepy.editor import VideoFileClip # 确保导入

# 设置日志
logger = logging.getLogger(__name__)

# 加载环境变量
load_dotenv()

class VideoProcessor:
    """视频处理工具类，提供视频文件处理和上传功能"""
    
    def __init__(self, temp_dir: Optional[str] = None):
        """
        初始化视频处理器
        
        Args:
            temp_dir: 临时文件目录，默认为系统临时目录
        """
        # 阿里云OSS配置
        self.access_key_id = os.environ.get("OSS_ACCESS_KEY_ID")
        self.access_key_secret = os.environ.get("OSS_ACCESS_KEY_SECRET")
        self.oss_bucket_name = os.environ.get("OSS_BUCKET_NAME", "ai-video-master")
        self.oss_endpoint = os.environ.get("OSS_ENDPOINT", "oss-cn-shanghai.aliyuncs.com")
        
        # 检查必要的环境变量
        if not (self.access_key_id and self.access_key_secret):
            logger.warning("未设置阿里云OSS访问密钥，上传功能将不可用")
        
        # 临时目录设置
        self.temp_dir = temp_dir or tempfile.mkdtemp(prefix="video_processor_")
        os.makedirs(self.temp_dir, exist_ok=True)
        
        # 项目根目录，用于定位 @segments 文件夹
        self.root_dir = Path(__file__).parent.parent.parent.parent
        self.segments_output_dir = self.root_dir / "data" / "processed" / "segments"
        self.temp_audio_dir = self.root_dir / "data" / "temp" # 定义临时音频文件目录
        os.makedirs(self.segments_output_dir, exist_ok=True)
        logger.info(f"Segments will be saved to: {self.segments_output_dir}")

        logger.info("初始化视频处理器")
    
    def _get_oss_bucket(self) -> Optional[oss2.Bucket]:
        """
        获取OSS存储桶实例
        
        Returns:
            OSS存储桶实例或None（如果配置无效）
        """
        if not (self.access_key_id and self.access_key_secret):
            logger.error("未设置阿里云OSS访问密钥，无法获取存储桶")
            return None
        
        try:
            # 创建认证对象
            auth = oss2.Auth(self.access_key_id, self.access_key_secret)
            # 创建存储桶实例
            bucket = oss2.Bucket(auth, self.oss_endpoint, self.oss_bucket_name)
            return bucket
        except Exception as e:
            logger.error(f"获取OSS存储桶失败: {str(e)}")
            return None
    
    def _upload_to_accessible_url(self, file_path: str, 
                                 expiration: int = 3600) -> Optional[str]:
        """
        上传文件到OSS并返回可访问的URL
        
        Args:
            file_path: 本地文件路径
            expiration: URL过期时间（秒），默认1小时
            
        Returns:
            可访问的URL或None（如果上传失败）
        """
        if not os.path.exists(file_path):
            logger.error(f"文件不存在: {file_path}")
            return None
        
        bucket = self._get_oss_bucket()
        if not bucket:
            logger.error("无法获取OSS存储桶，上传失败")
            return None
        
        try:
            # 生成OSS对象名称（使用UUID和原始文件名）
            file_name = os.path.basename(file_path)
            object_name = f"uploads/{uuid.uuid4()}_{file_name}"
            
            # 上传文件
            logger.info(f"开始上传文件到OSS: {file_path} -> {object_name}")
            bucket.put_object_from_file(object_name, file_path)
            
            # 生成可访问的URL（带过期时间）
            url = bucket.sign_url('GET', object_name, expiration)
            logger.info(f"文件上传成功，URL: {url}")
            
            return url
        except Exception as e:
            logger.error(f"上传文件到OSS失败: {str(e)}")
            return None
    
    def process_video(self, video_path: str, output_dir: Optional[str] = None, 
                     optimize: bool = False) -> Dict[str, Any]:
        """
        处理视频文件（可选优化）
        
        Args:
            video_path: 视频文件路径
            output_dir: 输出目录，默认为临时目录
            optimize: 是否优化视频，默认为False
            
        Returns:
            处理结果信息
        """
        if not os.path.exists(video_path):
            logger.error(f"视频文件不存在: {video_path}")
            return {"success": False, "error": "视频文件不存在"}
        
        # 设置输出目录
        if not output_dir:
            output_dir = self.temp_dir
        os.makedirs(output_dir, exist_ok=True)
        
        result = {
            "input_path": video_path,
            "success": True,
            "output_path": video_path,  # 默认输出与输入相同
            "duration": None,
            "resolution": None,
            "metadata": {}
        }
        
        try:
            # 获取视频信息
            info = self._get_video_info(video_path)
            if info:
                result["duration"] = info.get("duration")
                result["resolution"] = info.get("resolution")
                result["metadata"] = info
            
            # 如果需要优化视频
            if optimize:
                output_path = os.path.join(
                    output_dir, 
                    f"optimized_{int(time.time())}_{os.path.basename(video_path)}"
                )
                optimize_success = self._optimize_video(video_path, output_path)
                if optimize_success:
                    result["output_path"] = output_path
                    # 获取优化后视频的信息
                    optimized_info = self._get_video_info(output_path)
                    if optimized_info:
                        result["optimized_duration"] = optimized_info.get("duration")
                        result["optimized_resolution"] = optimized_info.get("resolution")
                        result["optimized_metadata"] = optimized_info
            
            return result
        except Exception as e:
            logger.error(f"处理视频时发生错误: {str(e)}")
            return {"success": False, "error": str(e), "input_path": video_path}
    
    def _get_video_info(self, video_path: str) -> Optional[Dict[str, Any]]:
        """
        获取视频文件信息
        
        Args:
            video_path: 视频文件路径
            
        Returns:
            视频信息字典或None（如果获取失败）
        """
        if not os.path.exists(video_path):
            logger.error(f"视频文件不存在: {video_path}")
            return None
        
        try:
            # 使用ffprobe获取视频信息
            cmd = [
                "ffprobe", 
                "-v", "quiet", 
                "-print_format", "json", 
                "-show_format", 
                "-show_streams", 
                video_path
            ]
            
            logger.debug(f"Running ffprobe command: {' '.join(cmd)}")
            result = subprocess.run(cmd, capture_output=True, text=True, check=False) # check=False to inspect stderr
            
            if result.returncode != 0:
                logger.error(f"获取视频信息失败 (ffprobe). stderr: {result.stderr}")
                return None
            
            import json
            info = json.loads(result.stdout)
            
            # 提取关键信息
            video_stream = next((s for s in info.get("streams", []) if s.get("codec_type") == "video"), None)
            
            if not video_stream:
                logger.warning(f"无法找到视频流: {video_path}")
                # Fallback: try to get duration from format if video stream is missing
                duration_fallback = float(info.get("format", {}).get("duration", 0))
                if duration_fallback > 0:
                    return {
                        "duration": duration_fallback,
                        "resolution": "N/A",
                        "width": 0,
                        "height": 0,
                        "format": info.get("format", {}),
                        "video_codec": "N/A",
                        "raw": info
                    }
                return info # return raw info if absolutely no video stream
            
            # 计算视频时长（秒）
            duration = float(info.get("format", {}).get("duration", 0))
            if duration == 0 and video_stream.get("duration"): # Fallback for duration
                 duration = float(video_stream.get("duration"))

            # 获取分辨率
            width = int(video_stream.get("width", 0))
            height = int(video_stream.get("height", 0))
            
            # 构建结果
            result_info = {
                "duration": duration,
                "resolution": f"{width}x{height}",
                "width": width,
                "height": height,
                "format": info.get("format", {}),
                "video_codec": video_stream.get("codec_name"),
                "raw": info
            }
            
            return result_info
        except json.JSONDecodeError as json_err:
            logger.error(f"解析ffprobe输出时JSON解码错误: {json_err}. Output: {result.stdout}")
            return None
        except Exception as e:
            logger.error(f"获取视频信息时发生一般错误: {str(e)}")
            return None
    
    def _optimize_video(self, input_path: str, output_path: str) -> bool:
        """
        优化视频（减小文件大小，保持质量）
        
        Args:
            input_path: 输入视频路径
            output_path: 输出视频路径
            
        Returns:
            成功返回True，否则返回False
        """
        try:
            # 使用ffmpeg优化视频
            cmd = [
                "ffmpeg", "-y",
                "-i", input_path,
                "-c:v", "libx264",
                "-crf", "23",  # 质量控制
                "-preset", "medium",  # 编码速度与压缩率平衡
                "-c:a", "aac",
                "-b:a", "128k",
                output_path
            ]
            logger.debug(f"Running ffmpeg optimize command: {' '.join(cmd)}")
            result = subprocess.run(cmd, capture_output=True, text=True, check=False) # check=False to inspect stderr

            if result.returncode != 0:
                logger.error(f"优化视频失败 (ffmpeg). stderr: {result.stderr}")
                return False
            
            logger.info(f"视频优化成功: {output_path}")
            return True
        except Exception as e:
            logger.error(f"优化视频时发生一般错误: {str(e)}")
            return False

    def extract_segment(self, video_path: str, start_time: float, end_time: float, \
                        segment_index: int, semantic_type: str, video_id: str, output_dir: str = None) -> Optional[str]:
        """
        从视频中提取一个片段。

        Args:
            video_path: 原始视频文件路径。
            start_time: 片段开始时间 (秒)。
            end_time: 片段结束时间 (秒)。
            segment_index: 片段的索引号。
            semantic_type: 片段的语义类型。
            video_id: 原始视频的ID (通常是文件名，不含扩展名)。
            output_dir: 可选的输出目录。如果提供，将片段保存到此目录而非默认的@segments目录。

        Returns:
            提取的片段文件路径，如果失败则返回None。
        """
        if not os.path.exists(video_path):
            logger.error(f"原始视频文件不存在: {video_path}")
            return None

        # 确定输出路径
        segment_filename = f"{video_id}_semantic_seg_{segment_index}_{semantic_type.replace(' ', '_')}.mp4"
        
        if output_dir:
            # 如果提供了输出目录，使用它
            os.makedirs(output_dir, exist_ok=True)
            output_path = Path(output_dir) / segment_filename
        else:
            # 否则使用默认的 @segments 目录
            output_path = self.segments_output_dir / segment_filename
        
        logger.info(f"准备提取片段: {output_path} 从 {video_path} [{start_time}s - {end_time}s]")

        try:
            with VideoFileClip(video_path) as video_clip:
                # 确保结束时间不超过视频总时长
                if end_time > video_clip.duration:
                    logger.warning(f"片段结束时间 ({end_time}s) 超出视频总时长 ({video_clip.duration}s). 将使用视频总时长作为结束时间。")
                    end_time = video_clip.duration
                
                # 确保开始时间小于结束时间
                if start_time >= end_time:
                    logger.error(f"片段开始时间 ({start_time}s) 大于或等于结束时间 ({end_time}s). 无法提取片段。")
                    return None

                segment = video_clip.subclip(start_time, end_time)
                
                # 尝试写入文件，并记录详细日志
                logger.info(f"开始写入视频片段: {output_path}")
                
                # 使用 MoviePy 的 logger 来捕获 FFmpeg 命令和输出
                # 创建一个自定义的 MoviePy logger
                moviepy_logger = logging.getLogger("moviepy")
                # 可以设置 moviepy_logger 的级别和处理器，以便将日志输出到文件或控制台
                # 例如: moviepy_logger.setLevel(logging.DEBUG)
                # moviepy_logger.addHandler(logging.StreamHandler()) # 输出到控制台

                segment.write_videofile(
                    str(output_path), 
                    codec="libx264", 
                    audio_codec="aac",
                    temp_audiofile=f"{self.temp_dir}/temp_audio_{segment_index}.m4a", # 确保临时音频文件路径有效
                    remove_temp=True,
                    # logger='bar' # 使用进度条，也可以传入自定义 logger
                    # ffmpeg_params=["-loglevel", "debug"] # 尝试获取ffmpeg的debug日志，但可能干扰MoviePy的stdout/stderr捕获
                )
            logger.info(f"成功提取视频片段: {output_path}")
            return str(output_path)
        except subprocess.CalledProcessError as e: # 更具体的ffmpeg错误
            logger.error(f"MoviePy/FFmpeg 在提取片段 {output_path} 时发生 CalledProcessError:")
            logger.error(f"  Command: {e.cmd}")
            logger.error(f"  Return code: {e.returncode}")
            logger.error(f"  Stdout: {e.stdout.decode(errors='ignore') if e.stdout else 'N/A'}")
            logger.error(f"  Stderr: {e.stderr.decode(errors='ignore') if e.stderr else 'N/A'}")
            return None
        except Exception as e:
            # 捕获 'NoneType' object has no attribute 'stdout' 这类错误
            logger.error(f"提取视频片段 {output_path} 时发生未知错误: {type(e).__name__} - {str(e)}")
            import traceback
            logger.error(f"Traceback: {traceback.format_exc()}")
            # 尝试清理可能的临时文件
            if os.path.exists(output_path):
                try:
                    os.remove(output_path)
                except Exception as e_remove:
                    logger.warning(f"清理失败的片段文件 {output_path} 时出错: {e_remove}")
            return None 