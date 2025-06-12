#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
视频分段器模块（严格版）

基于意图分析对视频进行分段处理，支持：
1. 视频转文字转录
2. 基于意图分析的视频分段
3. 分段视频的物理切分
4. 分段视频的内容分析

注意：此版本在服务失败时会直接报错，不使用模拟数据
"""

import os
import json
import logging
import subprocess
import tempfile
import time
import re
import sys
from pathlib import Path
from typing import List, Dict, Any, Optional, Tuple, Union
import pandas as pd
import numpy as np
from dotenv import load_dotenv
import difflib  # 添加difflib用于计算字符串相似度

# 设置日志
logging.basicConfig(level=logging.INFO,
                   format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# 尝试导入千问2.5视觉分析器
try:
    from src.core.models.qwen25_visual_analyzer import Qwen25VisualAnalyzer
    HAVE_QWEN25 = True
    logger.info("成功导入千问2.5视觉分析器")
except ImportError:
    HAVE_QWEN25 = False
    logger.warning("未能导入千问2.5视觉分析器，视觉分析功能将不可用")


class VideoSegmenter:
    """
    视频分段器类

    基于音频转录和意图分析对视频进行分段处理
    """

    def __init__(
    self,
    temp_dir: Optional[str] = None,
     hotword_id: Optional[str] = None):
        """
        初始化视频分段器

        Args:
            temp_dir: 临时文件目录，如果为None则使用系统临时目录
            hotword_id: 热词ID，用于音频转录
        """
        self.temp_dir = temp_dir or tempfile.mkdtemp(prefix="video_segmenter_")
        self.hotword_id = hotword_id

        # 创建临时目录
        if not os.path.exists(self.temp_dir):
            os.makedirs(self.temp_dir)

        # 如果有千问2.5分析器，初始化它
        if HAVE_QWEN25:
            self.visual_analyzer = Qwen25VisualAnalyzer()
        else:
            self.visual_analyzer = None

        logger.info(f"初始化视频分段器，临时目录: {self.temp_dir}")

    def process_video(self, video_path: str, output_dir: Optional[str] = None, skip_visual_analysis: bool = False) -> List[Dict[str, Any]]:
        """
        处理视频：提取音频、转录、分段

        Args:
            video_path: 视频文件路径
            output_dir: 输出目录
            skip_visual_analysis: 是否跳过视觉分析，默认为False
            
        Returns:
            分段信息列表
        """
        logger.info(f"开始处理视频: {video_path}")

        # 设置输出目录
        if output_dir is None:
            video_name = Path(video_path).stem
            output_dir = os.path.join("output", video_name)

        os.makedirs(output_dir, exist_ok=True)

        # 1. 提取音频
        audio_path = self._extract_audio(video_path)

        # 2. 转录音频
        transcript = self._transcribe_audio(audio_path)

        # 3. 基于意图分段
        segments = self._segment_by_intents(transcript, video_path)

        # 4. 提取视频片段
        segments = self.extract_video_segments(
            video_path, segments, output_dir)

        # 5. 分析视频片段（仅当未跳过视觉分析时执行）
        if not skip_visual_analysis and HAVE_QWEN25:
            logger.info("开始视觉内容分析...")
            segments = self.analyze_video_segments(segments)
        else:
            if skip_visual_analysis:
                logger.info("已跳过视觉内容分析")
            elif not HAVE_QWEN25:
                logger.warning("千问2.5视觉分析器不可用，跳过视频内容分析")

        # 6. 保存分段信息
        output_path = os.path.join(output_dir,
     f"{Path(video_path).stem}_segments.json")
        self.save_segments_to_json(segments, output_path)

        logger.info(f"视频处理完成，分段信息已保存至: {output_path}")
        return segments

    def _extract_audio(self, video_path: str) -> str:
        """
        从视频中提取音频

        Args:
            video_path: 视频文件路径

        Returns:
            提取的音频文件路径
        """
        if not os.path.exists(video_path):
            raise FileNotFoundError(f"视频文件不存在: {video_path}")

        # 准备输出路径
        video_name = Path(video_path).stem
        audio_path = os.path.join(self.temp_dir, f"{video_name}.wav")

        # 使用ffmpeg提取音频
        cmd = [
            "ffmpeg", "-y",
            "-i", video_path,
            "-vn",  # 不处理视频
            "-acodec", "pcm_s16le",  # 使用PCM 16bit编码
            "-ar", "16000",  # 采样率16kHz
            "-ac", "1",  # 单声道
            audio_path
        ]

        logger.info(f"提取音频: {video_path} -> {audio_path}")

        try:
            result = subprocess.run(cmd, capture_output=True, text=True)
            if result.returncode != 0:
                logger.error(f"音频提取失败: {result.stderr}")
                raise RuntimeError(f"音频提取失败: {result.stderr}")

            # 验证音频文件是否生成
            if not os.path.exists(
                audio_path) or os.path.getsize(audio_path) == 0:
                logger.error("音频提取失败，输出文件不存在或为空")
                raise RuntimeError("音频提取失败，输出文件不存在或为空")

            logger.info(f"音频提取成功: {audio_path}")
            return audio_path

        except Exception as e:
            logger.error(f"执行音频提取命令失败: {str(e)}")
            raise

    def _transcribe_audio(self, audio_path: str, use_new_analyzer: bool = True) -> Dict[str, Any]:
        """
        转录音频文件

        Args:
            audio_path: 音频文件路径
            use_new_analyzer: 是否使用新的DashScope分析器

        Returns:
            转录结果字典
        """
        if not os.path.exists(audio_path):
            raise FileNotFoundError(f"音频文件不存在: {audio_path}")

        logger.info(f"开始转录音频: {audio_path}")

        try:
            if use_new_analyzer:
                # 尝试使用新的DashScope分析器
                try:
                    from streamlit_app.modules.ai_analyzers import DashScopeAudioAnalyzer
                    
                    analyzer = DashScopeAudioAnalyzer()
                    if analyzer.is_available():
                        logger.info("使用DashScope语音分析器进行转录")
                        # 使用正则表达式规则进行专业词汇矫正
                        result = analyzer.transcribe_audio(
                            audio_path, 
                            format_result=True,
                            professional_terms=None  # 使用内置的正则规则
                        )
                        
                        if result["success"]:
                            # 转换格式以兼容现有代码
                            transcript_data = {
                                "text": result["transcript"],
                                "transcripts": [{
                                    "text": result["transcript"],
                                    "sentences": []
                                }],
                                "sentences": []
                            }
                            
                            # 转换时间段格式
                            for segment in result["segments"]:
                                sentence_data = {
                                    "text": segment["text"],
                                    "begin_time": int(segment["start_time"] * 1000),  # 转换为毫秒
                                    "end_time": int(segment["end_time"] * 1000),
                                    "confidence": segment.get("confidence", 1.0)
                                }
                                transcript_data["sentences"].append(sentence_data)
                                transcript_data["transcripts"][0]["sentences"].append(sentence_data)
                            
                            # 应用JSON校正 (使用正则表达式规则)
                            corrected_data, was_corrected = analyzer.apply_corrections_to_json(
                                transcript_data, use_regex_rules=True
                            )
                            
                            if was_corrected:
                                transcript_data = corrected_data
                                logger.info(f"已应用专业词汇矫正到转录结果")
                            
                            logger.info(f"DashScope转录成功，识别到 {len(result['segments'])} 个语音段")
                            
                        else:
                            logger.warning(f"DashScope转录失败: {result['error']}，回退到原有方法")
                            analyzer = None
                    else:
                        logger.warning("DashScope分析器不可用，回退到原有方法")
                        analyzer = None
                        
                except Exception as e:
                    logger.warning(f"DashScope分析器使用失败: {str(e)}，回退到原有方法")
                    analyzer = None
                
                # 如果DashScope成功，直接使用结果
                if analyzer and 'transcript_data' in locals():
                    pass  # 继续使用transcript_data
                else:
                    use_new_analyzer = False
            
            if not use_new_analyzer:
                # 使用原有的转录方法
            from src.core.transcribe_core import transcribe_audio

            # 如果有热词ID，使用它
            hotword_id = self.hotword_id if self.hotword_id else None

            # 使用临时目录
            output_dir = self.temp_dir

            # 使用transcribe_core进行转录
            transcript_json = transcribe_audio(
    audio_path, hotword_id=hotword_id, output_dir=output_dir)

            if not transcript_json or not os.path.exists(transcript_json):
                logger.error("音频转录失败，无法获取有效转录结果")
                raise RuntimeError("音频转录失败，无法获取有效转录结果")

            # 读取转录结果
            with open(transcript_json, 'r', encoding='utf-8') as f:
                transcript_data = json.load(f)

            logger.debug(f"转录结果格式: {json.dumps(list(transcript_data.keys()))}")

            # 处理不同格式的转录结果
            full_text = transcript_data.get("text", "")
            sentences = []

            # 检查是否有transcripts数组（新格式）
            if "transcripts" in transcript_data and isinstance(
                transcript_data["transcripts"], list):
                logger.info("检测到新格式转录结果，包含transcripts数组")

                for transcript_item in transcript_data["transcripts"]:
                    # 提取全文（如果还没有的话）
                    if not full_text and "text" in transcript_item:
                        full_text = transcript_item.get("text", "")

                    # 检查是否有sentences
                    if "sentences" in transcript_item and isinstance(
                        transcript_item["sentences"], list):
                        logger.info(
                            f"从转录频道中找到 {len(transcript_item['sentences'])} 个句子")

                        # 处理每个句子
                        for sentence in transcript_item["sentences"]:
                            # 获取开始和结束时间（以毫秒为单位）
                            begin_time_ms = sentence.get("begin_time", 0)
                            end_time_ms = sentence.get(
                                "end_time", begin_time_ms)

                            # 转换为时间戳字符串
                            start_time_str = self._format_seconds_to_timestamp(
                                begin_time_ms / 1000)
                            end_time_str = self._format_seconds_to_timestamp(
                                end_time_ms / 1000)

                            # 添加到句子列表
                            sentences.append({
                                "text": sentence.get("text", ""),
                                "start_time": start_time_str,
                                "end_time": end_time_str,
                                "start_ms": begin_time_ms,
                                "end_ms": end_time_ms
                            })

            # 如果没有在transcripts中找到，使用传统方式查找sentences
            if not sentences and "sentences" in transcript_data:
                logger.info("使用传统方式查找句子信息")
                for sentence in transcript_data["sentences"]:
                    # 处理开始时间
                    start_time = sentence.get("start_time", 0)
                    if isinstance(start_time, str):
                        start_time_str = start_time
                        # 尝试转换为毫秒
                        start_ms = self._time_to_ms(start_time)
                    else:
                        start_ms = start_time
                        start_time_str = self._format_seconds_to_timestamp(
                            start_time / 1000)

                    # 处理结束时间
                    end_time = sentence.get("end_time", start_time)  # 默认使用开始时间
                    if isinstance(end_time, str):
                        end_time_str = end_time
                        # 尝试转换为毫秒
                        end_ms = self._time_to_ms(end_time)
                    else:
                        end_ms = end_time
                        end_time_str = self._format_seconds_to_timestamp(
                            end_time / 1000)

                    # 添加句子信息
                    sentences.append({
                        "text": sentence.get("text", ""),
                        "start_time": start_time_str,
                        "end_time": end_time_str,
                        "start_ms": start_ms,
                        "end_ms": end_ms
                    })

            # 检查是否有足够的句子进行分段
            if not sentences:
                logger.error("转录结果不包含句子信息，无法进行分段")
                logger.error(
                    f"转录结果格式: {json.dumps(list(transcript_data.keys()))}")
                raise RuntimeError("转录结果不包含句子信息，无法进行分段")

            # 如果没有全文但有句子，从句子生成全文
            if not full_text and sentences:
                full_text = " ".join([s["text"] for s in sentences])
                logger.info("从句子生成了完整转录文本")

            # 验证和校准时间戳
            sentences = self._validate_and_calibrate_timestamps(
                sentences, audio_path)

            # 构建结果
            result = {
                "text": full_text,
                "sentences": sentences,
                "audio_path": audio_path,
                "timestamp": True
            }

            logger.info(f"音频转录成功，识别到 {len(sentences)} 个句子")
            return result

        except ImportError:
            logger.error("无法导入转录核心模块 src.core.transcribe_core")
            raise
        except Exception as e:
            logger.error(f"音频转录过程中出错: {str(e)}")
            raise

    def _validate_and_calibrate_timestamps(
        self, sentences: List[Dict[str, Any]], audio_path: str) -> List[Dict[str, Any]]:
        """
        验证和校准时间戳

        Args:
            sentences: 句子列表
            audio_path: 音频文件路径

        Returns:
            校准后的句子列表
        """
        logger.info("开始验证和校准时间戳")

        # 获取音频总时长
        audio_duration = self._get_audio_duration(audio_path)
        if audio_duration <= 0:
            logger.error(f"获取音频时长失败，无法校准时间戳")
            raise RuntimeError("获取音频时长失败，无法校准时间戳")

        logger.info(f"音频总时长: {audio_duration:.2f}秒")

        # 验证和校准后的句子列表
        validated_sentences = []

        # 上一句结束时间（毫秒）
        last_end_ms = 0

        for i, sentence in enumerate(sentences):
            # 提取时间戳
            start_time_str = sentence.get("start_time", "00:00:00,000")
            end_time_str = sentence.get("end_time", "00:00:00,000")
            text = sentence.get("text", "").strip()

            # 如果文本为空，跳过该句子
            if not text:
                logger.warning(f"句子 {i+1} 文本为空，已跳过")
                continue

            try:
                # 优先使用已提供的毫秒值
                start_ms = sentence.get("start_ms")
                end_ms = sentence.get("end_ms")

                # 如果毫秒值不存在，从时间字符串转换
                if start_ms is None:
                    start_ms = self._time_to_ms(start_time_str)
                if end_ms is None:
                    end_ms = self._time_to_ms(end_time_str)

                # 时间校验与校准
                if start_ms < 0:
                    logger.warning(f"句子 {i+1} 起始时间为负值，已修正为0")
                    start_ms = 0

                # 起始时间不能超过音频总时长
                audio_duration_ms = audio_duration * 1000
                if start_ms > audio_duration_ms:
                    logger.error(
                        f"句子 {i+1} 起始时间 ({start_ms/1000:.2f}秒) 超过音频总时长，已修正为0")
                    start_ms = 0

                # 结束时间不能超过音频总时长
                if end_ms > audio_duration_ms:
                    logger.warning(
                        f"句子 {i+1} 结束时间 ({end_ms/1000:.2f}秒) 超过音频总时长，已修正为音频时长")
                    end_ms = int(audio_duration_ms)

                # 结束时间必须大于起始时间
                if end_ms <= start_ms:
                    # 基于文本长度估算合理的持续时间（按语速每字符约180-220ms）
                    text_length = len(text)
                    # 计算基于文本长度的估计时长
                    estimated_duration = max(1000, text_length * 200)  # 至少1秒

                    # 对非常长的文本做特殊处理，避免过长估计
                    if text_length > 100:
                        # 长文本的语速通常会加快
                        estimated_duration = 10000 + (text_length - 100) * 150

                    # 确保时长不超过合理范围
                    estimated_duration = min(
    estimated_duration, 15000)  # 最长15秒

                    end_ms = start_ms + estimated_duration

                    # 确保不超过音频总时长
                    if end_ms > audio_duration_ms:
                        end_ms = int(audio_duration_ms)

                    logger.warning(
                        f"句子 {i+1} 时间范围无效，已基于文本长度({text_length}字符)估算修正: {start_ms/1000:.2f}s - {end_ms/1000:.2f}s")

                # 检查与前一句的时间关系（避免时间重叠）
                if start_ms < last_end_ms:
                    overlap = last_end_ms - start_ms
                    # 如果重叠超过500ms，进行修正
                    if overlap > 500:
                        logger.warning(
                            f"句子 {i+1} 与前一句时间重叠 {overlap/1000:.2f}秒，已修正")
                        start_ms = last_end_ms

                        # 重新估算结束时间，确保句子有足够的时长
                        text_length = len(text)
                        min_duration = max(
    1000, text_length * 150)  # 最少150ms每字符

                        # 计算新的结束时间
                        new_end_ms = start_ms + min_duration

                        # 如果原来的结束时间更晚，保留原来的；否则使用新计算的
                        end_ms = max(end_ms, new_end_ms)

                        # 确保不超过音频总时长
                        if end_ms > audio_duration_ms:
                            end_ms = int(audio_duration_ms)

                # 转回字符串格式
                start_time_calibrated = self._format_seconds_to_timestamp(
                    start_ms / 1000)
                end_time_calibrated = self._format_seconds_to_timestamp(
                    end_ms / 1000)

                # 将校准后的句子添加到列表
                validated_sentences.append({
                    "text": text,
                    "start_time": start_time_calibrated,
                    "end_time": end_time_calibrated,
                    "start_ms": start_ms,  # 添加毫秒数，便于后续处理
                    "end_ms": end_ms
                })

                # 更新上一句结束时间
                last_end_ms = end_ms

            except Exception as e:
                logger.error(f"校准句子 {i+1} 时间戳失败: {str(e)}")
                raise RuntimeError(f"校准时间戳失败: {str(e)}")

        # 检查校准后是否还有句子
        if not validated_sentences:
            logger.error("校准后没有有效句子，无法继续处理")
            raise RuntimeError("校准后没有有效句子，无法继续处理")

        logger.info(f"时间戳校准完成，校准后有 {len(validated_sentences)} 个有效句子")
        return validated_sentences

    def _format_seconds_to_timestamp(self, seconds: float) -> str:
        """
        将秒数转换为HH:MM:SS.mmm格式（使用小数点作为毫秒分隔符）

        Args:
            seconds: 秒数

        Returns:
            时间戳字符串
        """
        hours = int(seconds // 3600)
        minutes = int((seconds % 3600) // 60)
        secs = seconds % 60
        return f"{hours:02d}:{minutes:02d}:{secs:06.3f}"  # 使用小数点作为毫秒分隔符

    def _get_audio_duration(self, audio_path: str) -> float:
        """
        获取音频文件的时长

        Args:
            audio_path: 音频文件路径

        Returns:
            音频时长（秒）
        """
        try:
            # 使用ffprobe获取音频时长
            cmd = [
                "ffprobe", "-v", "error",
                "-show_entries", "format=duration",
                "-of", "default=noprint_wrappers=1:nokey=1",
                audio_path
            ]

            result = subprocess.run(cmd, capture_output=True, text=True)
            if result.returncode != 0:
                logger.error(f"获取音频时长失败: {result.stderr}")
                raise RuntimeError(f"获取音频时长失败: {result.stderr}")

            duration = float(result.stdout.strip())
            logger.info(f"音频时长: {duration:.2f} 秒")
            return duration

        except Exception as e:
            logger.error(f"获取音频时长时出错: {str(e)}")
            raise

    def extract_video_segments(self,
    video_path: str,
    segments: List[Dict[str,
    Any]],
    output_dir: str) -> List[Dict[str,
     Any]]:
        """
        提取视频片段

        Args:
            video_path: 源视频路径
            segments: 分段信息列表
            output_dir: 输出目录

        Returns:
            更新后的分段信息列表
        """
        logger.info(f"开始提取视频片段，共 {len(segments)} 个片段")

        # 确保输出目录存在
        os.makedirs(output_dir, exist_ok=True)

        # 更新的分段信息
        updated_segments = []

        # 视频名称
        video_name = Path(video_path).stem

        for i, segment in enumerate(segments):
            # 获取起止时间
            start_time = segment.get("start_time", "00:00:00")
            end_time = segment.get("end_time", "00:00:00")

            # 确保时间格式正确
            if ":" not in start_time:
                start_time = self._format_seconds_to_hhmmss(
                    float(start_time), include_ms=True)
            if ":" not in end_time:
                end_time = self._format_seconds_to_hhmmss(
                    float(end_time), include_ms=True)

            # 获取片段名称
            segment_name = segment.get("name", f"segment_{i+1}")
            safe_segment_name = re.sub(
    r'[^\w\-_]', '_', segment_name)  # 创建文件安全的名称

            # 输出视频路径
            output_path = os.path.join(
    output_dir, f"{video_name}_{i+1:02d}_{safe_segment_name}.mp4")

            try:
                # 提取视频片段
                self._extract_segment(
    video_path, output_path, start_time, end_time)

                # 更新分段信息
                segment_info = segment.copy()
                segment_info["video_path"] = output_path
                updated_segments.append(segment_info)

            except Exception as e:
                logger.error(f"提取视频片段 {i+1} 失败: {str(e)}")
                # 仍然添加到列表，但标记为错误
                segment_info = segment.copy()
                segment_info["error"] = str(e)
                updated_segments.append(segment_info)

        if not updated_segments:
            logger.error("所有视频片段提取均失败")
            raise RuntimeError("视频片段提取失败")

        logger.info(f"视频片段提取完成，成功提取 {len(updated_segments)} 个片段")
        return updated_segments

    def analyze_video_segments(
        self, segments: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        分析视频片段内容

        Args:
            segments: 分段信息列表

        Returns:
            更新后的分段信息列表
        """
        logger.info(f"开始分析视频片段内容，共 {len(segments)} 个片段")

        # 如果没有千问2.5分析器，直接返回
        if not HAVE_QWEN25 or self.visual_analyzer is None:
            logger.warning("千问2.5视觉分析器不可用，跳过视频内容分析")
            return segments

        # 更新的分段信息
        updated_segments = []

        # 根据片段数量和视频总时长调整分析参数
        total_duration = 0
        for segment in segments:
            # 从时间字符串计算视频片段时长
            start_time = segment.get("start_time", "00:00:00")
            end_time = segment.get("end_time", "00:00:00")

            try:
                start_ms = self._time_to_ms(start_time)
                end_ms = self._time_to_ms(end_time)
                duration = (end_ms - start_ms) / 1000  # 转换为秒
                total_duration += duration
            except Exception:
                # 如果计算失败，使用默认值
                total_duration += 10  # 假设每个片段平均10秒

        # 根据视频总时长和片段数量动态调整帧率
        if total_duration < 30 or len(segments) <= 3:
            # 短视频或少量片段，使用较高帧率捕获更多细节
            default_frame_rate = 4.0  # 4帧/秒
            logger.info(
                f"视频较短({total_duration:.2f}秒)或片段较少({len(segments)}个)，使用高帧率: {default_frame_rate} 帧/秒")
        else:
            # 长视频或较多片段，使用较低帧率以节省分析时间
            default_frame_rate = 2.0  # 2帧/秒
            logger.info(
                f"视频较长({total_duration:.2f}秒)或片段较多({len(segments)}个)，使用标准帧率: {default_frame_rate} 帧/秒")

        # 创建分析提示词模板 - 优化结构化提示词
        prompt_template = """你是一位专业的母婴奶粉广告视觉分析专家。
请对这段母婴奶粉广告视频片段进行结构化视觉内容分析，返回严格的 JSON 对象，包括以下部分：

{
  "config": {
    "allowed_categories": [
      "产品展示","母婴形象","功效可视化","品牌元素",
      "情感场景","科学背书","促销元素"
    ],
    "allowed_intents": [
      "广告开场","宝宝问题","产品介绍","促销信息","行动号召"
    ]
  },
  "scenes": [
    {
      "description": "场景描述（例如：明亮厨房中母亲抱婴儿）",
      "intent": "广告开场 | 宝宝问题 | 产品介绍 | 促销信息 | 行动号召"
    }
    // 可继续添加更多场景
  ],
  "elements": [
    {
      "type": "物体类型（例如：奶粉罐）",
      "color": "颜色（例如：蓝白）",
      "category": "产品展示 | 母婴形象 | 功效可视化 | 品牌元素 | 情感场景 | 科学背书 | 促销元素",
      "intent": "广告开场 | 宝宝问题 | 产品介绍 | 促销信息 | 行动号召",
      "confidence": 0.95
    }
    // 可继续添加更多元素
  ]
}

说明：
1. `config` 部分限定可选标签和意图；
2. `scenes` 标明每个场景的描述及对应意图；
3. `elements` 中的每项均含类别、意图和置信度；
4. 严格返回上述 JSON，不要包含其他注释或说明。
"""

        for i, segment in enumerate(segments):
            # 获取视频路径
            video_path = segment.get("video_path")
            if not video_path or not os.path.exists(video_path):
                logger.warning(f"片段 {i+1} 没有有效的视频路径，跳过分析")
                updated_segments.append(segment)
                continue

            try:
                # 分析视频内容
                logger.info(f"分析视频片段 {i+1}: {video_path}")

                # 根据视频长度设置合适的帧率
                try:
                    video_duration = self._get_video_duration(video_path)

                    # 🎯 NEW: 获取文件大小进行额外优化
                    try:
                        file_size_mb = os.path.getsize(video_path) / (1024 * 1024)
                    except:
                        file_size_mb = 0
                    
                    # 🎯 过滤过小文件
                    if file_size_mb < 0.5:
                        logger.info(f"🚫 跳过过小视频文件: {file_size_mb:.2f}MB")
                        continue
                    
                    # 🎯 优化的短视频帧率策略
                    if file_size_mb < 1.0 or video_duration < 5:  # 短视频优化
                        current_frame_rate = 5.0  # 使用高帧率捕获更多细节
                        logger.info(f"⚡ 短视频优化: {file_size_mb:.2f}MB，{video_duration:.1f}秒，使用高帧率")
                    elif video_duration < 10:  # 中等片段
                        current_frame_rate = 3.0
                        logger.info(f"📊 中等片段: {video_duration:.1f}秒，使用标准帧率")
                    else:  # 长片段
                        current_frame_rate = 2.0
                        logger.info(f"🎬 长片段: {video_duration:.1f}秒，使用保守帧率")
                        
                except Exception as e:
                    logger.warning(f"无法获取视频时长，使用默认帧率: {e}")
                    current_frame_rate = 2.0

                # 使用自定义帧率分析视频
                analysis = self.visual_analyzer.analyze_video_file(
                    video_path,
                    frame_rate=current_frame_rate,
                    prompt=prompt_template
                )

                # 更新分段信息
                segment_info = segment.copy()

                # 类型检查并添加原始分析结果
                if isinstance(analysis, dict):
                    segment_info["raw_visual_analysis"] = analysis

                    # 尝试提取结构化数据，并确保错误不会导致整个流程失败
                    try:
                        structured_analysis = self.visual_analyzer.extract_structured_analysis(
                            analysis)
                        if isinstance(structured_analysis, dict):
                            segment_info["visual_analysis"] = structured_analysis
                    except Exception as e:
                        logger.error(f"提取结构化分析失败: {str(e)}")
                        segment_info["visual_analysis"] = {"error": str(e)}
                else:
                    logger.error(f"视频分析结果不是字典类型: {type(analysis)}")
                    segment_info["visual_analysis"] = {"error": "视频分析结果类型错误"}

                updated_segments.append(segment_info)

            except Exception as e:
                logger.error(f"分析视频片段 {i+1} 失败: {str(e)}")
                # 添加错误信息但不中断流程
                segment_info = segment.copy()
                segment_info["visual_analysis"] = {"error": str(e)}
                updated_segments.append(segment_info)

        logger.info(f"视频片段内容分析完成，共分析 {len(updated_segments)} 个片段")
        return updated_segments

    def batch_analyze_video_segments(
        self, segments: List[Dict[str, Any]], batch_size: int = 10) -> List[Dict[str, Any]]:
        """
        批量分析视频片段内容

        Args:
            segments: 分段信息列表
            batch_size: 每批处理的最大片段数量

        Returns:
            更新后的分段信息列表
        """
        logger.info(f"开始批量分析视频片段内容，共 {len(segments)} 个片段")

        # 如果没有千问2.5分析器，直接返回
        if not HAVE_QWEN25 or self.visual_analyzer is None:
            logger.warning("千问2.5视觉分析器不可用，跳过视频内容分析")
            return segments

        # 根据片段数量和视频总时长调整分析参数
        total_duration = 0
        for segment in segments:
            # 从时间字符串计算视频片段时长
            start_time = segment.get("start_time", "00:00:00")
            end_time = segment.get("end_time", "00:00:00")

            try:
                start_ms = self._time_to_ms(start_time)
                end_ms = self._time_to_ms(end_time)
                duration = (end_ms - start_ms) / 1000  # 转换为秒
                total_duration += duration
            except Exception:
                # 如果计算失败，使用默认值
                total_duration += 10  # 假设每个片段平均10秒

        # 根据视频总时长和片段数量动态调整帧率
        if total_duration < 30 or len(segments) <= 3:
            # 短视频或少量片段，使用较高帧率捕获更多细节
            default_frame_rate = 4.0  # 4帧/秒
            logger.info(
                f"视频较短({total_duration:.2f}秒)或片段较少({len(segments)}个)，使用高帧率: {default_frame_rate} 帧/秒")
        else:
            # 长视频或较多片段，使用较低帧率以节省分析时间
            default_frame_rate = 2.0  # 2帧/秒
            logger.info(
                f"视频较长({total_duration:.2f}秒)或片段较多({len(segments)}个)，使用标准帧率: {default_frame_rate} 帧/秒")

        # 创建分析提示词模板 - 优化结构化提示词
        prompt_template = """你是一位专业的母婴奶粉广告视觉分析专家。
请对这段母婴奶粉广告视频片段进行结构化视觉内容分析，返回严格的 JSON 对象，包括以下部分：

{
  "config": {
    "allowed_categories": [
      "产品展示","母婴形象","功效可视化","品牌元素",
      "情感场景","科学背书","促销元素"
    ],
    "allowed_intents": [
      "广告开场","宝宝问题","产品介绍","促销信息","行动号召"
    ]
  },
  "scenes": [
    {
      "description": "场景描述（例如：明亮厨房中母亲抱婴儿）",
      "intent": "广告开场 | 宝宝问题 | 产品介绍 | 促销信息 | 行动号召"
    }
    // 可继续添加更多场景
  ],
  "elements": [
    {
      "type": "物体类型（例如：奶粉罐）",
      "color": "颜色（例如：蓝白）",
      "category": "产品展示 | 母婴形象 | 功效可视化 | 品牌元素 | 情感场景 | 科学背书 | 促销元素",
      "intent": "广告开场 | 宝宝问题 | 产品介绍 | 促销信息 | 行动号召",
      "confidence": 0.95
    }
    // 可继续添加更多元素
  ]
}

说明：
1. `config` 部分限定可选标签和意图；
2. `scenes` 标明每个场景的描述及对应意图；
3. `elements` 中的每项均含类别、意图和置信度；
4. 严格返回上述 JSON，不要包含其他注释或说明。
"""

        # 过滤有效的视频片段
        valid_segments = []
        for i, segment in enumerate(segments):
            video_path = segment.get("video_path")
            if video_path and os.path.exists(video_path):
                valid_segments.append((i, segment))
            else:
                logger.warning(f"片段 {i+1} 没有有效的视频路径，跳过分析")
                # 保持该片段未修改
                segment_info = segment.copy()
                segment_info["visual_analysis"] = {"error": "无效的视频路径"}
                segments[i] = segment_info

        # 如果没有有效片段，直接返回
        if not valid_segments:
            logger.warning("没有找到有效的视频片段，跳过分析")
            return segments

        logger.info(f"找到 {len(valid_segments)} 个有效视频片段，使用批量处理")

        # 分批处理
        total_batches = (len(valid_segments) + batch_size - 1) // batch_size
        for batch_idx in range(total_batches):
            start_idx = batch_idx * batch_size
            end_idx = min(start_idx + batch_size, len(valid_segments))
            batch_segments = valid_segments[start_idx:end_idx]

            logger.info(
                f"处理批次 {batch_idx+1}/{total_batches}，包含 {len(batch_segments)} 个片段")

            # 收集批次中的视频路径和帧率
            video_paths = []
            frame_rates = []
            original_indices = []

            for original_idx, segment in batch_segments:
                video_path = segment.get("video_path")
                original_indices.append(original_idx)
                video_paths.append(video_path)

                # 根据视频长度设置合适的帧率
                try:
                    video_duration = self._get_video_duration(video_path)

                    # 🎯 NEW: 获取文件大小进行额外优化
                    try:
                        file_size_mb = os.path.getsize(video_path) / (1024 * 1024)
                    except:
                        file_size_mb = 0
                    
                    # 🎯 过滤过小文件
                    if file_size_mb < 0.5:
                        logger.info(f"🚫 跳过过小视频文件: {file_size_mb:.2f}MB")
                        continue
                    
                    # 🎯 优化的短视频帧率策略
                    if file_size_mb < 1.0 or video_duration < 5:  # 短视频优化
                        current_frame_rate = 5.0  # 使用高帧率捕获更多细节
                        logger.info(f"⚡ 短视频优化: {file_size_mb:.2f}MB，{video_duration:.1f}秒，使用高帧率")
                    elif video_duration < 10:  # 中等片段
                        current_frame_rate = 3.0
                        logger.info(f"📊 中等片段: {video_duration:.1f}秒，使用标准帧率")
                    else:  # 长片段
                        current_frame_rate = 2.0
                        logger.info(f"🎬 长片段: {video_duration:.1f}秒，使用保守帧率")
                        
                except Exception as e:
                    logger.warning(f"无法获取视频时长，使用默认帧率: {e}")
                    current_frame_rate = 2.0

                    logger.info(
                        f"片段 {original_idx+1} 长度: {video_duration:.2f}秒，文件: {file_size_mb:.2f}MB，帧率: {current_frame_rate:.1f}fps")
                    frame_rates.append(current_frame_rate)
                except Exception as e:
                    logger.error(f"获取视频时长失败: {str(e)}")
                    frame_rates.append(default_frame_rate)
                    logger.info(
                        f"片段 {original_idx+1} 使用默认帧率: {default_frame_rate} 帧/秒")

            try:
                # 批量分析视频
                batch_results = self.visual_analyzer.batch_analyze_video_files(
                    video_paths,
                    frame_rates=frame_rates,
                    prompt=prompt_template
                )

                # 处理批量分析结果
                for i, (original_idx, result) in enumerate(
                    zip(original_indices, batch_results)):
                    segment_info = segments[original_idx].copy()

                    # 类型检查并添加原始分析结果
                    if isinstance(result, dict):
                        segment_info["raw_visual_analysis"] = result

                        # 尝试提取结构化数据
                        try:
                            if "error" not in result:
                                structured_analysis = self.visual_analyzer.extract_structured_analysis(
                                    result)
                                if isinstance(structured_analysis, dict):
                                    segment_info["visual_analysis"] = structured_analysis
                            else:
                                segment_info["visual_analysis"] = {
                                    "error": result.get("error", "未知错误")}
                        except Exception as e:
                            logger.error(f"提取结构化分析失败: {str(e)}")
                            segment_info["visual_analysis"] = {
                                "error": f"提取结构化分析失败: {str(e)}"}
                    else:
                        logger.error(f"视频分析结果不是字典类型: {type(result)}")
                        segment_info["visual_analysis"] = {
                            "error": "视频分析结果类型错误"}

                    # 更新原始segments列表
                    segments[original_idx] = segment_info

            except Exception as e:
                logger.error(f"批量分析视频片段失败: {str(e)}")
                # 处理错误，将错误信息添加到每个片段
                for original_idx, _ in batch_segments:
                    segment_info = segments[original_idx].copy()
                    segment_info["visual_analysis"] = {
                        "error": f"批量分析失败: {str(e)}"}
                    segments[original_idx] = segment_info

        logger.info(f"视频片段批量分析完成，共分析 {len(valid_segments)} 个片段")
        return segments

    def save_segments_to_json(
        self, segments: List[Dict[str, Any]], output_path: str) -> None:
        """
        保存分段信息到JSON文件

        Args:
            segments: 分段信息列表
            output_path: 输出JSON文件路径
        """
        # 处理NumPy类型
        def convert_int64(obj):
            if isinstance(obj, np.integer):
                return int(obj)
            elif isinstance(obj, np.floating):
                return float(obj)
            elif isinstance(obj, np.ndarray):
                return obj.tolist()
            return obj

        # 确保输出目录存在
        os.makedirs(os.path.dirname(output_path), exist_ok=True)

        # 保存JSON
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(
    segments,
    f,
    ensure_ascii=False,
    indent=2,
     default=convert_int64)

        logger.info(f"分段信息已保存至: {output_path}")

    def _format_seconds_to_hhmmss(
    self,
    seconds: float,
     include_ms: bool = True) -> str:
        """
        将秒数转换为HH:MM:SS[.mmm]格式

        Args:
            seconds: 秒数
            include_ms: 是否包含毫秒部分，默认为True

        Returns:
            HH:MM:SS[.mmm]格式的时间字符串
        """
        hours = int(seconds // 3600)
        minutes = int((seconds % 3600) // 60)

        if include_ms:
            secs = seconds % 60  # 保留小数部分
            return f"{hours:02d}:{minutes:02d}:{secs:06.3f}"  # 例如：00:01:23.456
        else:
            seconds = int(seconds % 60)  # 不保留小数部分
            return f"{hours:02d}:{minutes:02d}:{seconds:02d}"  # 例如：00:01:23

    def _segment_by_intents(
        self, transcript: Dict[str, Any], video_path: str) -> List[Dict[str, Any]]:
        """
        基于意图分段

        Args:
            transcript: 转录结果字典
            video_path: 视频文件路径

        Returns:
            分段信息列表
        """
        logger.info("开始基于意图进行分段")

        # 从转录中获取完整文本和带时间戳的句子
        full_text = transcript.get("text", "")
        sentences = transcript.get("sentences", [])

        # 获取视频时长（毫秒）
        duration_seconds = self._get_video_duration(video_path)
        duration_ms = duration_seconds * 1000 if duration_seconds > 0 else 0

        # 分析意图
        intent_segments = self._analyze_intents(
            full_text, duration_ms, sentences)

        if not intent_segments:
            logger.error("未找到有效的意图分段")
            raise RuntimeError("意图分析失败，未找到有效的分段")

        # 转换意图分段为分段信息
        segments = []
        for i, segment in enumerate(intent_segments):
            # 获取时间范围
            time_range = segment.get("time_range", "00:00:00-00:00:00")
            start_time, end_time = time_range.split("-")

            segment_info = {
                "id": segment.get("intent_id", f"segment_{i+1:02d}"),
                "name": segment.get("intent_label", f"分段{i+1}"),
                "start_time": start_time,
                "end_time": end_time,
                "keywords": segment.get("intent_keywords", []),
                "transcript": segment.get("transcript", ""),
                "intent_label": segment.get("intent_label", "未分类")
            }

            segments.append(segment_info)

        logger.info(f"完成基于意图的分段，生成了 {len(segments)} 个分段")
        return segments

    def _analyze_intents(self,
    transcript: str,
    video_duration_ms: float,
    sentences_with_time: List[Dict[str,
    Any]] = None) -> List[Dict[str,
     Any]]:
        """
        分析转录文本以确定意图分段

        Args:
            transcript: 完整的转录文本
            video_duration_ms: 视频时长（毫秒）
            sentences_with_time: 带时间戳的句子列表（可选）

        Returns:
            意图分段列表
        """
        if not transcript:
            logger.error("转录文本为空，无法进行意图分析")
            raise ValueError("转录文本为空，无法进行意图分析")

        try:
            # 尝试导入standalone意图分析器
            from srt_intent_analyzer_standalone import analyze_srt_intents

            logger.info("使用standalone意图分析器分析视频内容")

            # 检查句子列表
            if not sentences_with_time:
                logger.error("无带时间戳的句子，无法创建SRT格式片段进行意图分析")
                raise ValueError("无带时间戳的句子，无法创建SRT格式片段进行意图分析")

            srt_segments = []
            for i, sentence in enumerate(sentences_with_time):
                try:
                    # 安全地获取时间值和文本
                    text = sentence.get('text', '').strip()

                    # 如果文本为空，跳过此句子
                    if not text:
                        logger.warning(f"跳过空文本句子 {i+1}")
                        continue

                    # 直接使用校准后的毫秒值
                    start_ms = sentence.get('start_ms')
                    end_ms = sentence.get('end_ms')

                    # 如果没有毫秒值，尝试转换时间字符串
                    if start_ms is None or end_ms is None:
                        start_time = sentence.get('start_time', '00:00:00.000')
                        end_time = sentence.get('end_time', '00:00:00.000')

                        start_ms = self._time_to_ms(start_time)
                        end_ms = self._time_to_ms(end_time)

                    # 验证时间有效性
                    if start_ms >= end_ms:
                        logger.error(
                            f"句子 {i+1} 时间范围无效 ({start_ms/1000:.2f}s >= {end_ms/1000:.2f}s)")
                        raise ValueError(f"句子时间范围无效")

                    # 创建SRT片段
                    srt_segments.append({
                        "index": i + 1,
                        "text": text,
                        "start": start_ms / 1000,  # 转为秒
                        "end": end_ms / 1000,      # 转为秒
                        "start_time": sentence.get('start_time', '00:00:00,000'),
                        "end_time": sentence.get('end_time', '00:00:00,000')
                    })

                except Exception as e:
                    logger.error(f"处理句子 {i+1} 时出错: {str(e)}")
                    raise RuntimeError(f"处理句子失败: {str(e)}")

            # 检查是否有有效的SRT片段
            if not srt_segments:
                logger.error("无法创建有效的SRT片段，意图分析失败")
                raise ValueError("无法创建有效的SRT片段，意图分析失败")

            # 使用意图分析器，根据片段数量调整最大持续时间
            max_duration = 20 if len(srt_segments) <= 3 else 15
            logger.info(f"使用最大分段持续时间: {max_duration}秒")

            # 调用意图分析
            intent_segments = analyze_srt_intents(
                srt_segments, max_duration=max_duration)

            # 检查意图分析结果
            if not intent_segments:
                logger.error("意图分析返回空结果，分析失败")
                raise RuntimeError("意图分析返回空结果，分析失败")

            # 校准意图分段与视频帧
            intent_segments = self._calibrate_intent_segments_with_video(
                intent_segments, video_duration_ms)

            logger.info(f"意图分析成功，找到 {len(intent_segments)} 个意图分段")
            return intent_segments

        except ImportError as e:
            logger.error(f"无法导入意图分析器: {str(e)}")
            raise
        except Exception as e:
            logger.error(f"意图分析过程中出错: {str(e)}")
            raise

    def _calibrate_intent_segments_with_video(
        self, intent_segments: List[Dict[str, Any]], video_duration_ms: float) -> List[Dict[str, Any]]:
        """
        将意图分段与视频帧进行校准，确保分段边界与视频关键帧对齐

        Args:
            intent_segments: 意图分段列表
            video_duration_ms: 视频总时长(毫秒)

        Returns:
            校准后的意图分段列表
        """
        logger.info("开始将意图分段与视频帧进行校准")

        # 检查视频时长
        if video_duration_ms <= 0:
            logger.error("视频时长无效，无法校准分段")
            raise ValueError("视频时长无效")

        calibrated_segments = []
        last_end_ms = 0  # 记录上一个分段的结束时间

        for i, segment in enumerate(intent_segments):
            try:
                # 获取时间范围
                time_range = segment.get("time_range", "00:00:00-00:00:00")
                times = time_range.split("-")

                if len(times) != 2:
                    logger.error(f"分段 {i+1} 时间范围格式错误: {time_range}")
                    raise ValueError(f"分段时间范围格式错误")

                start_time, end_time = times

                # 转换为毫秒
                start_ms = self._time_to_ms(start_time)
                end_ms = self._time_to_ms(end_time)

                # 验证时间范围
                if start_ms < 0:
                    logger.warning(f"分段 {i+1} 起始时间为负值，已修正为0")
                    start_ms = 0

                if end_ms > video_duration_ms:
                    logger.warning(f"分段 {i+1} 结束时间超过视频时长，已修正为视频结束时间")
                    end_ms = video_duration_ms

                if start_ms >= end_ms:
                    logger.error(
                        f"分段 {i+1} 时间范围无效 ({start_ms/1000:.2f}s >= {end_ms/1000:.2f}s)")
                    # 如果是第一个分段，从0开始
                    if i == 0:
                        start_ms = 0
                        # 使用合理的分段长度，例如10秒或视频时长的1/5
                        end_ms = min(10000, video_duration_ms / 5)
                    else:
                        # 否则，从上一个分段结束时间开始，持续一段合理时间
                        start_ms = last_end_ms
                        end_ms = min(start_ms + 10000, video_duration_ms)

                    logger.warning(f"已修正分段 {i+1} 时间范围: {start_ms/1000:.2f}s - {end_ms/1000:.2f}s")
                
                # 校准到关键帧
                start_ms_aligned = self._align_to_keyframe(start_ms, is_start=True)
                end_ms_aligned = self._align_to_keyframe(end_ms, is_start=False)
                
                # 确保起始时间不会早于0
                start_ms_aligned = max(0, start_ms_aligned)
                
                # 确保结束时间不会超过视频时长
                end_ms_aligned = min(end_ms_aligned, video_duration_ms)
                
                # 处理与前一个分段的关系
                if i > 0 and calibrated_segments:
                    prev_end_ms = calibrated_segments[-1].get("end_ms", last_end_ms)
                    
                    # 如果与前一个分段有重叠，调整起始时间
                    if start_ms_aligned < prev_end_ms:
                        logger.warning(f"分段 {i+1} 与前一分段时间重叠，已调整起始时间")
                        start_ms_aligned = prev_end_ms
                    
                    # 如果与前一个分段有较大间隙(超过2秒)，考虑调整
                    gap_ms = start_ms_aligned - prev_end_ms
                    if gap_ms > 2000:
                        logger.info(f"分段 {i+1} 与前一分段有 {gap_ms/1000:.2f}秒 间隙")
                        
                        # 判断是否需要调整间隙
                        # 如果间隙很大(>5秒)且不是故意的分段，可以考虑减小间隙
                        if gap_ms > 5000:
                            # 调整前一分段的结束时间或当前分段的起始时间
                            # 这里选择向前调整当前分段的起始时间
                            new_start_ms = max(prev_end_ms, start_ms_aligned - 3000)
                            logger.warning(f"调整分段 {i+1} 起始时间，从 {start_ms_aligned/1000:.2f}秒 到 {new_start_ms/1000:.2f}秒")
                            start_ms_aligned = new_start_ms
                
                # 确保校准后时间范围仍然有效
                if start_ms_aligned >= end_ms_aligned:
                    logger.error(f"校准后分段 {i+1} 时间范围无效 ({start_ms_aligned/1000:.2f}s >= {end_ms_aligned/1000:.2f}s)")
                    # 强制修正，确保至少有1秒的持续时间
                    end_ms_aligned = start_ms_aligned + 1000
                    logger.warning(f"已强制修正分段 {i+1} 时间范围: {start_ms_aligned/1000:.2f}s - {end_ms_aligned/1000:.2f}s")
                
                # 确保分段长度至少为3秒，千问视觉分析API要求视频不能太短
                min_segment_duration_ms = 3000  # 3秒
                if end_ms_aligned - start_ms_aligned < min_segment_duration_ms:
                    logger.warning(f"分段 {i+1} 长度不足3秒，调整为最小长度")
                    # 尝试延长结束时间
                    new_end_ms = start_ms_aligned + min_segment_duration_ms
                    # 但不要超过视频总长度
                    if new_end_ms <= video_duration_ms:
                        end_ms_aligned = new_end_ms
                    else:
                        # 如果无法延长结束时间，尝试提前开始时间
                        new_start_ms = max(0, end_ms_aligned - min_segment_duration_ms)
                        start_ms_aligned = new_start_ms
                    logger.info(f"调整后分段 {i+1} 时间范围: {start_ms_aligned/1000:.2f}s - {end_ms_aligned/1000:.2f}s")
                
                # 更新分段时间范围
                start_time_aligned = self._format_seconds_to_timestamp(start_ms_aligned / 1000)
                end_time_aligned = self._format_seconds_to_timestamp(end_ms_aligned / 1000)
                
                updated_segment = segment.copy()
                updated_segment["time_range"] = f"{start_time_aligned}-{end_time_aligned}"
                updated_segment["start_ms"] = start_ms_aligned  # 添加毫秒时间戳便于后续处理
                updated_segment["end_ms"] = end_ms_aligned
                updated_segment["aligned"] = True
                
                calibrated_segments.append(updated_segment)
                
                # 更新上一个分段结束时间
                last_end_ms = end_ms_aligned
                
            except Exception as e:
                logger.error(f"校准分段 {i+1} 失败: {str(e)}")
                raise RuntimeError(f"校准分段失败: {str(e)}")
        
        if not calibrated_segments:
            logger.error("校准后没有有效的分段")
            raise RuntimeError("校准后没有有效的分段")
        
        logger.info(f"分段校准完成，共 {len(calibrated_segments)} 个校准后的分段")
        return calibrated_segments
    
    def _align_to_keyframe(self, time_ms: float, is_start: bool) -> float:
        """
        将时间点对齐到视频关键帧
        
        Args:
            time_ms: 时间点(毫秒)
            is_start: 是否为分段起始点
            
        Returns:
            对齐到关键帧的时间点(毫秒)
        """
        # 注意：理想情况下，应该使用ffprobe查找真实的关键帧时间点
        # 但为了效率和实用性，这里使用简化的对齐方法
        
        # 模拟关键帧间隔为500ms
        keyframe_interval_ms = 500
        
        # 计算对齐位置
        if is_start:
            # 起始点向前对齐到最近的关键帧
            # 对于起始点，通常希望它不要提前太多，以避免包含不相关内容
            aligned_ms = int(time_ms / keyframe_interval_ms) * keyframe_interval_ms
            
            # 如果对齐后的时间点提前超过1秒，则限制最大前移时间
            if time_ms - aligned_ms > 1000:
                aligned_ms = time_ms - (time_ms % keyframe_interval_ms)
                logger.debug(f"限制起始点前移，从 {time_ms} 调整到 {aligned_ms}")
        else:
            # 结束点向后对齐到最近的关键帧
            # 结束点通常希望不要延后太多，以避免包含下一个内容
            aligned_ms = int((time_ms + keyframe_interval_ms - 1) / keyframe_interval_ms) * keyframe_interval_ms
            
            # 如果对齐后的时间点延后超过1秒，则限制最大后移时间
            if aligned_ms - time_ms > 1000:
                aligned_ms = time_ms + (keyframe_interval_ms - (time_ms % keyframe_interval_ms))
                if time_ms % keyframe_interval_ms == 0:  # 如果已经在关键帧上，不需要后移
                    aligned_ms = time_ms
                logger.debug(f"限制结束点后移，从 {time_ms} 调整到 {aligned_ms}")
        
        logger.debug(f"{'起始' if is_start else '结束'}点 {time_ms/1000:.3f}s 对齐到 {aligned_ms/1000:.3f}s")
        return aligned_ms
    
    def _extract_segment(self, video_path: str, output_path: str, start_time: str, end_time: str) -> None:
        """
        提取视频片段
        
        Args:
            video_path: 源视频路径
            output_path: 输出视频路径
            start_time: 开始时间 (HH:MM:SS格式)
            end_time: 结束时间 (HH:MM:SS格式)
        """
        if not os.path.exists(video_path):
            raise FileNotFoundError(f"源视频文件不存在: {video_path}")
                    
        # 确保输出目录存在
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        
        # 标准化时间格式，确保使用小数点而不是逗号作为毫秒分隔符
        start_time = start_time.replace(',', '.')
        end_time = end_time.replace(',', '.')
        
        # 使用ffmpeg提取片段
        cmd = [
            "ffmpeg", "-y",
            "-i", video_path,
            "-ss", start_time,
            "-to", end_time,
            "-c:v", "libx264", 
            "-c:a", "aac",
            "-preset", "fast",
            "-crf", "23",
            "-ac", "2",
            output_path
        ]
        
        try:
            result = subprocess.run(cmd, capture_output=True, text=True)
            if result.returncode != 0:
                logger.error(f"视频片段提取失败: {result.stderr}")
                raise RuntimeError(f"视频片段提取失败: {result.stderr}")
                    
            # 验证输出文件是否生成
            if not os.path.exists(output_path) or os.path.getsize(output_path) == 0:
                logger.error("视频片段提取失败，输出文件不存在或为空")
                raise RuntimeError("视频片段提取失败，输出文件不存在或为空")
            
            logger.info(f"视频片段提取成功: {output_path}")
        except Exception as e:
            logger.error(f"执行视频片段提取命令失败: {str(e)}")
            raise
    
    def _get_video_duration(self, video_path: str) -> float:
        """
        获取视频文件的时长
        
        Args:
            video_path: 视频文件路径
            
        Returns:
            视频时长（秒）
        """
        try:
            # 使用ffprobe获取视频时长
            cmd = [
                "ffprobe", "-v", "error",
                "-show_entries", "format=duration",
                "-of", "default=noprint_wrappers=1:nokey=1",
                video_path
            ]
            
            result = subprocess.run(cmd, capture_output=True, text=True)
            if result.returncode != 0:
                logger.error(f"获取视频时长失败: {result.stderr}")
                raise RuntimeError(f"获取视频时长失败: {result.stderr}")
            
            duration = float(result.stdout.strip())
            logger.info(f"视频时长: {duration:.2f} 秒")
            return duration
            
        except Exception as e:
            logger.error(f"获取视频时长时出错: {str(e)}")
            raise
    
    def _time_to_ms(self, time_str: str) -> int:
        """
        将时间字符串转换为毫秒
        
        Args:
            time_str: 时间字符串，支持多种格式：
                      - HH:MM:SS.mmm
                      - HH:MM:SS,mmm
                      - mmm (纯毫秒)
            
        Returns:
            毫秒数
        """
        if not time_str:
            raise ValueError("时间字符串为空")
        
        # 如果已经是数字，则直接返回
        if isinstance(time_str, (int, float)):
            return int(time_str)
        
        try:
            # 检查是否为纯毫秒数
            if time_str.isdigit():
                return int(time_str)
            
            # 处理HH:MM:SS.mmm或HH:MM:SS,mmm格式
            if ':' in time_str:
                # 标准化分隔符
                time_str = time_str.replace(',', '.')
                
                # 解析时间部分
                parts = time_str.split(':')
                ms = 0
                
                if len(parts) == 3:  # HH:MM:SS 格式
                    hours, minutes, rest = parts
                    if '.' in rest:
                        seconds, milliseconds = rest.split('.')
                        ms = int(hours) * 3600000 + int(minutes) * 60000 + int(seconds) * 1000
                        # 确保毫秒部分处理正确
                        ms += int(milliseconds.ljust(3, '0')[:3])  # 补齐到3位并截取前3位
                    else:
                        ms = int(hours) * 3600000 + int(minutes) * 60000 + int(rest) * 1000
                
                elif len(parts) == 2:  # MM:SS 格式
                    minutes, rest = parts
                    if '.' in rest:
                        seconds, milliseconds = rest.split('.')
                        ms = int(minutes) * 60000 + int(seconds) * 1000
                        ms += int(milliseconds.ljust(3, '0')[:3])
                    else:
                        ms = int(minutes) * 60000 + int(rest) * 1000
                
            return ms
            
            # 如果不符合上述格式，尝试作为秒数处理
            if '.' in time_str:  # 带小数点的秒数
                seconds, milliseconds = time_str.split('.')
                ms = int(seconds) * 1000
                ms += int(milliseconds.ljust(3, '0')[:3])
                return ms
            
            logger.error(f"无法解析时间格式: {time_str}")
            raise ValueError(f"无法解析时间格式: {time_str}")
            
        except Exception as e:
            logger.error(f"时间字符串转换为毫秒时出错: {str(e)}, 时间字符串: {time_str}")
            raise 