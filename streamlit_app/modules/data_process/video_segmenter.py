import os
import time
import json
import logging
import tempfile
import subprocess
from pathlib import Path
import streamlit as st
from moviepy.editor import VideoFileClip
from datetime import datetime

from config.config import get_config, get_paths_config
from modules.data_loader.video_loader import find_target_video
from src.core.utils.video_processor import VideoProcessor
from modules.analysis.intent_analyzer import SemanticAnalyzer

# 设置日志
logger = logging.getLogger(__name__)

class VideoSegmenter:
    """视频分段处理类"""
    
    def __init__(self, video_path=None, output_dir=None, verbose=True):
        """
        初始化视频分段处理器
        
        Args:
            video_path: 视频文件路径
            output_dir: 输出目录
            verbose: 是否输出详细日志
        """
        config = get_config()
        paths = get_paths_config()
        
        self.video_path = video_path or find_target_video()
        if not self.video_path or not os.path.exists(self.video_path):
            raise FileNotFoundError(f"视频文件不存在: {self.video_path}")
            
        self.verbose = verbose
        self.timestamp = int(time.time())
        self.video_id = os.path.splitext(os.path.basename(self.video_path))[0]
        
        # 输出目录设置
        if output_dir:
            self.output_dir = output_dir
        else:
            test_folder = f"test_{self.timestamp}"
            self.output_dir = os.path.join(paths["segments_dir"], test_folder)
        
        os.makedirs(self.output_dir, exist_ok=True)
        
        # 临时目录设置
        self.temp_dir = os.path.join(config["temp_dir"], f"segmenter_test_{self.timestamp}")
        os.makedirs(self.temp_dir, exist_ok=True)
        
        # 音频提取临时目录
        self.audio_dir = os.path.join(config["temp_dir"], f"audio_test_{self.timestamp}")
        os.makedirs(self.audio_dir, exist_ok=True)
        
        # 时间戳提取临时目录
        self.timestamp_dir = os.path.join(config["temp_dir"], f"timestamp_test_{self.timestamp}")
        os.makedirs(self.timestamp_dir, exist_ok=True)
        
        # 输出文件路径
        self.segments_json = os.path.join(self.output_dir, f"{self.video_id}_segments.json")
        self.audio_path = os.path.join(self.audio_dir, f"{self.video_id}.wav")
        
        logger.info(f"初始化视频分段处理器，视频ID: {self.video_id}")
    
    def extract_audio(self):
        """
        从视频中提取音频
        
        Returns:
            音频文件路径
        """
        if not os.path.exists(self.video_path):
            raise FileNotFoundError(f"找不到视频文件: {self.video_path}")
        
        # 使用ffmpeg提取音频
        cmd = [
            "ffmpeg", "-i", self.video_path, 
            "-vn", "-acodec", "pcm_s16le", 
            "-ar", "16000", "-ac", "1", 
            self.audio_path, "-y"
        ]
        
        try:
            subprocess.run(cmd, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            logger.info(f"音频提取成功: {self.audio_path}")
            return self.audio_path
        except subprocess.CalledProcessError as e:
            logger.error(f"音频提取失败: {e}")
            raise
    
    def analyze_audio(self, audio_path=None, use_new_analyzer=True):
        """
        分析音频，获取语音时间戳
        
        Args:
            audio_path: 音频文件路径，如果为None则使用提取的音频
            use_new_analyzer: 是否使用新的DashScope分析器
            
        Returns:
            语音时间戳列表
        """
        audio_path = audio_path or self.audio_path
        if not os.path.exists(audio_path):
            logger.error(f"音频文件不存在: {audio_path}")
            raise FileNotFoundError(f"音频文件不存在: {audio_path}")
        
        timestamp_str = time.strftime("%Y%m%d_%H%M%S")
        output_json = os.path.join(
            self.timestamp_dir, 
            f"{self.video_id}_api_{timestamp_str}.json"
        )
        
        try:
            if use_new_analyzer:
                # 使用新的DashScope语音分析器
                from modules.ai_analyzers import DashScopeAudioAnalyzer
                
                analyzer = DashScopeAudioAnalyzer()
                if not analyzer.is_available():
                    logger.warning("DashScope分析器不可用，回退到原有方法")
                    use_new_analyzer = False
                else:
                    # 使用正则表达式规则进行专业词汇矫正
                    result = analyzer.transcribe_audio(
                        audio_path, 
                        format_result=True,
                        professional_terms=None  # 使用内置的正则规则
                    )
                    
                    if result["success"]:
                        # 转换格式以兼容现有代码
                        transcript_data = {
                            "transcripts": [{
                                "text": result["transcript"],
                                "sentences": result["segments"]
                            }]
                        }
                        
                        # 应用JSON校正 (使用正则表达式规则)
                        corrected_data, was_corrected = analyzer.apply_corrections_to_json(
                            transcript_data, use_regex_rules=True
                        )
                        
                        # 保存结果
                        with open(output_json, 'w', encoding='utf-8') as f:
                            json.dump(corrected_data, f, ensure_ascii=False, indent=2)
                        
                        if was_corrected:
                            logger.info(f"已应用专业词汇矫正到转录结果")
                        
                        logger.info(f"语音时间戳分析成功，结果保存至: {output_json}")
                        return corrected_data
                    else:
                        logger.error(f"DashScope转录失败: {result['error']}")
                        use_new_analyzer = False
            
            if not use_new_analyzer:
                # 回退到原有的转录方法
                from src.core.transcribe_core import transcribe_audio_with_timestamp
                
            transcript_data = transcribe_audio_with_timestamp(
                audio_path, 
                output_json=output_json
            )
            
            logger.info(f"语音时间戳分析成功，结果保存至: {output_json}")
            return transcript_data
                
        except Exception as e:
            logger.error(f"语音时间戳分析失败: {str(e)}")
            raise
    
    def segment_video(self, transcript_data=None):
        """
        根据语音时间戳分段视频
        
        Args:
            transcript_data: 语音时间戳数据，如果为None则调用analyze_audio获取
            
        Returns:
            分段数据
        """
        if transcript_data is None:
            if not os.path.exists(self.audio_path):
                self.extract_audio()
            transcript_data = self.analyze_audio()
        
        # 从语音时间戳中提取分段信息
        segments = []
        
        # 提取句子级别的时间戳
        # 确保处理 transcripts 列表中的第一个元素的 sentences
        transcript_sentences = []
        if "transcripts" in transcript_data and transcript_data["transcripts"]:
            if "sentences" in transcript_data["transcripts"][0]:
                transcript_sentences = transcript_data["transcripts"][0]["sentences"]
        elif "sentences" in transcript_data: # 兼容直接在顶层有sentences的情况
             transcript_sentences = transcript_data["sentences"]
        else:
            logger.warning(f"在转录数据中未找到'sentences'字段: {self.video_id}")

        for i, sentence in enumerate(transcript_sentences):
            segment = {
                "id": i,
                "video_id": self.video_id,
                "start_time": sentence.get("begin_time", 0) / 1000.0,  # 修正: 使用 get 并转换为秒
                "end_time": sentence.get("end_time", 0) / 1000.0,    # 修正: 使用 get 并转换为秒
                "text": sentence.get("text", ""),
                "segment_path": os.path.join(self.output_dir, f"{self.video_id}_segment_{i}.mp4")
            }
            segments.append(segment)
        
        # 保存分段信息到JSON文件
        with open(self.segments_json, 'w', encoding='utf-8') as f:
            json.dump(segments, f, ensure_ascii=False, indent=2)
        
        logger.info(f"视频分段完成，共 {len(segments)} 个分段，保存至 {self.segments_json}")
        return segments
    
    def extract_segment_videos(self, segments=None):
        """
        提取分段视频片段
        
        Args:
            segments: 分段数据，如果为None则从self.segments_json加载
            
        Returns:
            成功提取的分段列表
        """
        if segments is None:
            with open(self.segments_json, 'r', encoding='utf-8') as f:
                segments = json.load(f)
        
        extracted_segments = []
        
        for segment in segments:
            segment_id = segment["id"]
            start_time = segment["start_time"]
            end_time = segment["end_time"]
            output_path = segment["segment_path"]
            
            # 使用ffmpeg提取视频片段
            cmd = [
                "ffmpeg", "-i", self.video_path,
                "-ss", str(start_time),
                "-to", str(end_time),
                "-c:v", "libx264", "-c:a", "aac",
                "-strict", "experimental",
                output_path, "-y"
            ]
            
            try:
                subprocess.run(cmd, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
                logger.info(f"成功提取分段 {segment_id}: {output_path}")
                extracted_segments.append(segment)
            except subprocess.CalledProcessError as e:
                logger.error(f"提取分段 {segment_id} 失败: {e}")
        
        logger.info(f"视频分段提取完成，成功: {len(extracted_segments)}/{len(segments)}")
        return extracted_segments
    
    def process(self):
        """
        处理完整的视频分段流程
        
        Returns:
            Tuple: (分段数据列表, 完整的转录数据字典)
        """
        logger.info(f"开始处理视频: {self.video_path}")
        
        try:
            # 1. 提取音频
            self.extract_audio()
            
            # 2. 分析音频
            transcript_data = self.analyze_audio() # 这个 transcript_data 包含完整文本
            if not transcript_data:
                logger.error(f"音频分析失败，无法获取转录数据: {self.video_path}")
                return [], None # 返回空列表和None
            
            # 3. 分段视频 (基于transcript_data中的句子)
            segments = self.segment_video(transcript_data)
            
            # 4. 提取分段视频片段 (物理文件)
            extracted_segments = self.extract_segment_videos(segments)
            
            logger.info(f"视频处理完成: {self.video_path}")
            return extracted_segments, transcript_data # 返回分段和原始转录数据
        except Exception as e:
            logger.error(f"视频处理失败: {str(e)}")
            # raise # 避免在这里 raise，让调用方处理None或空列表
            return [], None # 出错时也返回空列表和None

# Cached core processing function
@st.cache_data(ttl=86400) # Cache for 1 day
def _cached_video_processing_and_segmentation(video_path, file_mtime, file_size, cache_buster=None):
    logger.info(f"CACHE MISS for video segmentation: {video_path} (mtime: {file_mtime}, size: {file_size}, cache_buster: {cache_buster}). Processing...")
    video_id = os.path.splitext(os.path.basename(video_path))[0]
    config = get_config()
    output_base_dir = os.path.join(config["processed_dir"], "segments")
    # 为每个视频创建一个独特的子目录，例如使用时间戳或视频ID
    timestamp_str = datetime.now().strftime("%Y%m%d_%H%M%S")
    # 使用 video_id 创建更可预测的路径，如果缓存希望跨会话且基于视频名
    # output_dir = os.path.join(output_base_dir, f"{video_id}_{timestamp_str}") 
    # 改为使用更固定的路径，便于缓存和查找，但要注意潜在的并发写入问题（如果适用）
    # 考虑在 main_analysis_pipeline 中为每次运行生成唯一 run_id 并传递下来
    # 这里暂时使用 video_id 和一个固定的 run_id 占位符或动态时间戳
    # 为了支持缓存和多次运行，我们使用 video_id 和一个基于当前时间的 run_id，或者可以从调用栈上传递一个统一的 run_id
    current_run_id = f"run_{timestamp_str}" # 简单起见，每次调用生成一个新的run_id
    # output_dir = os.path.join(output_base_dir, video_id, current_run_id)
    # 修正：segments 保存路径应该更稳定，以 video_id 为基础
    # segments_json_dir = os.path.join(config["processed_dir"], "segments", f"test_{current_run_id}") 
    # 确保路径是基于 video_id 的，以便后续查找
    # 之前的路径是 test_<timestamp>，现在改成 video_id
    # output_dir = os.path.join(config["processed_dir"], "segments", video_id) # 存放视频片段
    # segments_json_path = os.path.join(output_dir, f"{video_id}_segments.json") # 存放片段信息的json
    
    # 统一存放处理后的segments数据，以video_id为子目录
    processed_segments_base_dir = os.path.join(config["processed_dir"], "segments")
    video_segments_dir = os.path.join(processed_segments_base_dir, video_id) # e.g., data/processed/segments/video1/
    os.makedirs(video_segments_dir, exist_ok=True)
    segments_json_path = os.path.join(video_segments_dir, f"{video_id}_segments_info.json") # e.g., data/processed/segments/video1/video1_segments_info.json

    segments_data = []
    
    # 1. 使用VideoProcessor获取转录数据（包括原始ASR句子和校正后文本）
    processor = VideoProcessor(temp_dir=config.get("temp_dir"))
    
    # 先让VideoProcessor优化视频（如果需要）
    video_info = processor.process_video(video_path, output_dir=config.get("processed_dir"))
    
    # 准备转录
    asr_temp_dir = os.path.join(config.get("temp_dir"), "asr_intermediate_files", f"{video_id}_{timestamp_str}")
    os.makedirs(asr_temp_dir, exist_ok=True)
    
    # 尝试使用新的DashScope分析器
    transcript_json_path = None
    try:
        from modules.ai_analyzers import DashScopeAudioAnalyzer
        
        analyzer = DashScopeAudioAnalyzer()
        if analyzer.is_available():
            logger.info("使用DashScope语音分析器进行转录")
            result = analyzer.transcribe_video(video_path, extract_audio_first=True)
            
            if result["success"]:
                # 转换格式以兼容现有代码
                transcript_data_new = {
                    "text": result["transcript"],
                    "transcripts": [{
                        "text": result["transcript"],
                        "sentences": result["segments"]
                    }],
                    "result": {
                        "Sentences": result["segments"]
                    }
                }
                
                # 保存到临时目录
                transcript_json_path = os.path.join(asr_temp_dir, f"{video_id}_transcript.json")
                with open(transcript_json_path, 'w', encoding='utf-8') as f:
                    json.dump(transcript_data_new, f, ensure_ascii=False, indent=2)
                
                logger.info(f"DashScope转录完成，结果保存至: {transcript_json_path}")
            else:
                logger.warning(f"DashScope转录失败: {result['error']}，回退到原有方法")
                analyzer = None
        else:
            logger.warning("DashScope分析器不可用，回退到原有方法")
            analyzer = None
            
    except Exception as e:
        logger.warning(f"DashScope分析器初始化失败: {str(e)}，回退到原有方法")
        analyzer = None
    
    # 如果DashScope失败，使用原有的转录方法
    if not transcript_json_path:
        from src.core.transcribe_core import process_video as transcribe_process_video
    transcript_json_path = transcribe_process_video(video_path, output_dir=asr_temp_dir)
    
    # 加载转录结果
    transcript_data_corrected = None
    if transcript_json_path and os.path.exists(transcript_json_path):
        try:
            with open(transcript_json_path, 'r', encoding='utf-8') as f:
                transcript_data_corrected = json.load(f)
                logger.info(f"成功加载转录数据: {transcript_json_path}")
                
                # 添加调试日志，输出JSON结构的顶级键
                logger.debug(f"转录JSON顶级键: {list(transcript_data_corrected.keys())}")
                
                # 检查是否有transcripts字段并包含数据
                if "transcripts" in transcript_data_corrected and transcript_data_corrected["transcripts"]:
                    # 打印第一个transcript的键
                    first_transcript = transcript_data_corrected["transcripts"][0]
                    logger.debug(f"第一个transcript的键: {list(first_transcript.keys())}")
                    
                    # 适配阿里云API格式: 准备text和sentences
                    if "text" not in transcript_data_corrected and "text" in first_transcript:
                        # 将transcripts[0]中的text复制到顶层
                        transcript_data_corrected["text"] = first_transcript["text"]
                        logger.debug(f"从transcript[0]复制text到顶层")
                    
                    # 确保result.Sentences存在(为了兼容性)
                    if "result" not in transcript_data_corrected:
                        transcript_data_corrected["result"] = {}
                    
                    if "Sentences" not in transcript_data_corrected.get("result", {}):
                        # 检查transcript中是否有sentences
                        if "sentences" in first_transcript:
                            # 复制sentences到result.Sentences
                            transcript_data_corrected["result"]["Sentences"] = first_transcript["sentences"]
                            logger.debug(f"从transcript[0].sentences复制到result.Sentences，句子数量: {len(first_transcript['sentences'])}")
        except Exception as e:
            logger.error(f"加载转录数据失败: {e}")

    # 检查数据是否有效
    has_sentences = False
    if transcript_data_corrected:
        # 检查多个可能的句子位置
        if transcript_data_corrected.get("result", {}).get("Sentences"):
            has_sentences = True
        elif "transcripts" in transcript_data_corrected and transcript_data_corrected["transcripts"]:
            first_transcript = transcript_data_corrected["transcripts"][0]
            if "sentences" in first_transcript and first_transcript["sentences"]:
                has_sentences = True
    
    if not transcript_data_corrected or not has_sentences or not transcript_data_corrected.get("text"):
        logger.error(f"未能获取有效的转录数据或ASR句子列表 for {video_path}")
        # 清理临时的ASR文件
        if os.path.exists(asr_temp_dir):
            try:
                import shutil
                shutil.rmtree(asr_temp_dir)
                logger.info(f"已清理临时ASR目录: {asr_temp_dir}")
            except Exception as e_clean:
                logger.error(f"清理临时ASR目录失败: {asr_temp_dir}, error: {e_clean}")
        return [], transcript_data_corrected # 返回空分段和已获取的转录数据

    # 提取文本和句子数据
    full_corrected_text = transcript_data_corrected.get("text", "")
    
    # 尝试多个可能的句子位置
    original_asr_sentences = []
    if transcript_data_corrected.get("result", {}).get("Sentences"):
        original_asr_sentences = transcript_data_corrected["result"]["Sentences"]
    elif "transcripts" in transcript_data_corrected and transcript_data_corrected["transcripts"]:
        first_transcript = transcript_data_corrected["transcripts"][0]
        if "sentences" in first_transcript:
            original_asr_sentences = first_transcript["sentences"]
    
    logger.info(f"找到 {len(original_asr_sentences)} 个ASR句子")

    # 生成SRT文件并保存到指定目录
    if original_asr_sentences:
        # 创建用于SRT文件的目录
        srt_output_dir = os.path.join(config["data_dir"], "output", "test_videos")
        os.makedirs(srt_output_dir, exist_ok=True)
        
        # 视频ID (去除扩展名)
        video_id = os.path.splitext(os.path.basename(video_path))[0]
        srt_file_path = os.path.join(srt_output_dir, f"{video_id}.srt")
        
        # 为SRT生成格式化时间
        def format_time_srt(seconds: float) -> str:
            """将秒转换为SRT时间戳格式 (HH:MM:SS,mmm)"""
            from datetime import timedelta
            delta = timedelta(seconds=seconds)
            hours, remainder = divmod(delta.seconds, 3600)
            minutes, seconds_val = divmod(remainder, 60)
            milliseconds = delta.microseconds // 1000
            return f"{hours:02}:{minutes:02}:{seconds_val:02},{milliseconds:03}"
        
        # 生成SRT内容
        try:
            srt_blocks = []
            for i, sentence in enumerate(original_asr_sentences):
                # 检查必要的字段是否存在
                if 'begin_time' not in sentence or 'end_time' not in sentence or 'text' not in sentence:
                    logger.warning(f"跳过缺少必要字段的ASR句子: {sentence}")
                    continue
                
                # 获取开始和结束时间 (确保转换为毫秒)
                start_ms = int(sentence['begin_time'])
                end_ms = int(sentence['end_time'])
                
                # 跳过无效的时间戳
                if end_ms <= start_ms:
                    logger.warning(f"跳过无效时间戳的ASR句子: {sentence}")
                    continue
                
                # 转换为SRT格式的时间戳
                start_time_srt = format_time_srt(start_ms / 1000.0)
                end_time_srt = format_time_srt(end_ms / 1000.0)
                
                # 添加SRT块
                srt_blocks.append(f"{i + 1}")
                srt_blocks.append(f"{start_time_srt} --> {end_time_srt}")
                srt_blocks.append(sentence['text'])
                srt_blocks.append("") # 空行分隔
            
            # 将SRT内容写入文件
            with open(srt_file_path, "w", encoding="utf-8") as f:
                f.write("\n".join(srt_blocks))
            
            logger.info(f"SRT文件已保存到: {srt_file_path}")
            # 将SRT文件路径添加到返回的转录数据中
            if transcript_data_corrected is not None: # 确保 transcript_data_corrected 不是 None
                transcript_data_corrected['srt_file_path'] = srt_file_path
            else: # 如果是None, 初始化它（尽管这不太可能发生在这里，因为前面有赋值）
                transcript_data_corrected = {'srt_file_path': srt_file_path}

        except Exception as e:
            logger.error(f"生成SRT文件时出错: {str(e)}")
            # 即使生成SRT失败，也确保 srt_file_path 键存在，但值为 None
            if transcript_data_corrected is not None:
                transcript_data_corrected['srt_file_path'] = None
            else:
                transcript_data_corrected = {'srt_file_path': None}

    # 2. 使用SemanticAnalyzer进行语义分段和时间戳对齐
    sa = SemanticAnalyzer() # 初始化语义分析器
    # semantic_segments_with_time = sa.segment_transcript_by_intent(full_corrected_text, original_asr_sentences)

    # 新的调用方式：直接传递SRT文件路径
    # 首先确保 srt_file_path 在 transcript_data_corrected 中是可用的 (我们之前修改过以确保这一点)
    srt_file_path_for_segmentation = transcript_data_corrected.get('srt_file_path')

    if not srt_file_path_for_segmentation or not os.path.exists(srt_file_path_for_segmentation):
        logger.error(f"SRT文件路径在转录数据中不可用或文件不存在: {srt_file_path_for_segmentation}，无法进行基于SRT的语义分段。")
        # 清理临时的ASR文件
        if os.path.exists(asr_temp_dir):
            try:
                import shutil
                shutil.rmtree(asr_temp_dir)
                logger.info(f"已清理临时ASR目录: {asr_temp_dir}")
            except Exception as e_clean:
                logger.error(f"清理临时ASR目录失败: {asr_temp_dir}, error: {e_clean}")
        return [], transcript_data_corrected # 返回空分段列表和原始转录数据

    semantic_segments_with_time = sa.segment_transcript_by_intent(srt_file_path_for_segmentation)

    if not semantic_segments_with_time:
        logger.warning(f"语义分段失败或未返回任何区块 for {video_path}. 视频将不会被切割成片段。")
        # 清理临时的ASR文件
        if os.path.exists(asr_temp_dir):
            try:
                import shutil
                shutil.rmtree(asr_temp_dir)
                logger.info(f"已清理临时ASR目录: {asr_temp_dir}")
            except Exception as e_clean:
                logger.error(f"清理临时ASR目录失败: {asr_temp_dir}, error: {e_clean}")
        return [], transcript_data_corrected

    logger.info(f"语义分段完成，获得 {len(semantic_segments_with_time)} 个区块 for {video_path}")

    # 3. 根据语义区块的时间戳切割视频 和 准备返回给UI的segments_data
    segments_data_for_ui = [] # 用于存储传递给UI的片段信息
    try:
        total_segments_to_cut = len(semantic_segments_with_time)
        success_count = 0

        for i, seg_info in enumerate(semantic_segments_with_time):
            semantic_type = seg_info["semantic_type"]
            segment_text = seg_info["text"] # LLM输出的该区块文本
            asr_matched_text = seg_info.get("asr_matched_text", segment_text) # 实际用于切割的ASR文本
            start_time = seg_info["start_time"]
            end_time = seg_info["end_time"]
            
            if start_time >= end_time: # 确保时间戳有效
                logger.warning(f"无效的时间戳 (start >= end) for semantic segment {i} ('{semantic_type}'): {start_time}s - {end_time}s. 跳过此片段.")
                continue

            segment_filename = f"{video_id}_semantic_seg_{i}_{semantic_type.replace(' ', '_')}.mp4"
            segment_output_path = os.path.join(video_segments_dir, segment_filename)

            # 使用改进的 VideoProcessor.extract_segment 方法
            actual_segment_output_path = processor.extract_segment(
                video_path=video_path, # 显式传递 video_path
                start_time=start_time,
                end_time=end_time,
                segment_index=i, # 使用循环变量i作为segment_index
                semantic_type=semantic_type, # 使用已获取的semantic_type
                video_id=video_id, # 使用已获取的video_id
                output_dir=video_segments_dir # 将 segment_output_path 改为 video_segments_dir 并使用正确的参数名 output_dir
            )
            
            if actual_segment_output_path and os.path.exists(actual_segment_output_path):
                logger.info(f"成功提取语义片段 {i}/{total_segments_to_cut} ('{semantic_type}'): {actual_segment_output_path} [{start_time:.2f}s - {end_time:.2f}s]")
                success_count += 1
                
                # 为UI准备数据，添加 time_period
                formatted_start_time = seconds_to_hms(start_time)
                formatted_end_time = seconds_to_hms(end_time)
                time_period_str = f"{formatted_start_time} - {formatted_end_time}"
                
                segments_data_for_ui.append({
                    "video_id": video_id,
                    "segment_id": i, 
                    "semantic_type": semantic_type,
                    "text": segment_text, # 可以考虑是否用asr_matched_text，取决于UI希望显示哪个
                    "asr_matched_text": asr_matched_text,
                    "start_time": start_time,
                    "end_time": end_time,
                    "time_period": time_period_str, # 添加格式化的时间段
                    "segment_path": actual_segment_output_path, # 实际保存的片段路径
                    "srt_lines": seg_info.get("srt_lines", "") # 从原始seg_info中获取
                })
            else:
                logger.error(f"提取语义片段失败: {segment_filename}")
        
        logger.info(f"视频语义分段切割完成，成功提取: {success_count}/{total_segments_to_cut} for {video_path}")

    except Exception as e_cut:
        logger.error(f"切割视频片段时发生错误: {str(e_cut)}")
        # 即使切割失败，也尝试返回已有的转录数据和可能已处理的少量片段
    
    # 保存语义片段的详细信息到JSON文件 (segments_data_for_ui)
    try:
        with open(segments_json_path, 'w', encoding='utf-8') as f:
            json.dump(segments_data_for_ui, f, ensure_ascii=False, indent=4)
        logger.info(f"语义片段信息已保存到: {segments_json_path}")
    except Exception as e_json_save:
        logger.error(f"保存语义片段信息到JSON文件失败: {e_json_save}")
        
    # 清理临时的ASR文件
    if os.path.exists(asr_temp_dir):
        try:
            import shutil
            shutil.rmtree(asr_temp_dir)
            logger.info(f"已清理临时ASR目录: {asr_temp_dir}")
        except Exception as e_clean:
            logger.error(f"清理临时ASR目录失败: {asr_temp_dir}, error: {e_clean}")
            
    return segments_data_for_ui, transcript_data_corrected

def seconds_to_hms(seconds_float):
    """将浮点数秒转换为 HH:MM:SS.ms 格式或 HH:MM:SS 格式 (如果毫秒为0)"""
    hours = int(seconds_float // 3600)
    minutes = int((seconds_float % 3600) // 60)
    secs = int(seconds_float % 60)
    ms = int((seconds_float - int(seconds_float)) * 1000)
    if ms > 0:
        return f"{hours:02d}:{minutes:02d}:{secs:02d}.{ms:03d}"
    else:
        return f"{hours:02d}:{minutes:02d}:{secs:02d}"

# Original segment_video function, now acts as a wrapper for caching
def segment_video(video_path: str) -> tuple[list, dict | None]:
    """
    Segments the video, performs transcription, and returns segment data and full transcript.
    Uses caching based on video file path, modification time, and size.
    """
    if not os.path.exists(video_path):
        logger.error(f"Video file not found: {video_path}")
        return [], None
    if not os.path.isfile(video_path):
        logger.error(f"Path is not a file: {video_path}")
        return [], None

    try:
        stat = os.stat(video_path)
        file_mtime = stat.st_mtime
        file_size = stat.st_size
    except OSError as e:
        logger.error(f"Error accessing file metadata for {video_path} for caching: {e}. \
                       Processing without cache for this call.")
        # Fallback: call the core logic directly, bypassing cache for this specific error case.
        # This means it will re-process if metadata can't be read.
        # For fallback, we don't pass cache_buster as it's not part of the original direct call logic
        # However, to ensure consistency if vs.process() itself might be cached or call cached functions,
        # it's safer to align. But `VideoSegmenter.process` is not cached.
        # We'll assume the direct call doesn't need the cache_buster for now.
        # If direct processing is desired, one might call a non-cached version of the core logic.
        # vs = VideoSegmenter(video_path)
        # return vs.process() # Assuming vs.process() is the original core logic
        # Forcing re-evaluation even in fallback by calling the core function with a cache buster.
        # This ensures that if the error is intermittent, a subsequent successful call benefits from caching.
        import time # Ensure time is imported
        return _cached_video_processing_and_segmentation(video_path, 0, 0, cache_buster=time.time())


    logger.info(f"CACHE CHECK for video segmentation: {video_path} (mtime: {file_mtime}, size: {file_size})")
    import time # Ensure time is imported for the main call
    return _cached_video_processing_and_segmentation(video_path, file_mtime, file_size, cache_buster=time.time()) 