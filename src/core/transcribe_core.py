#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
转录核心模块 - 提供统一的转录和校正功能

⚠️ 注意：本模块正在逐步迁移到 streamlit_app/modules/ai_analyzers/dashscope_audio_analyzer.py
- 专业词汇校正功能已迁移到新模块
- 本模块仅保留必要的转录功能作为回退方案
- 建议新代码使用 DashScopeAudioAnalyzer

该模块封装了从视频/音频文件中提取、转录并校正文本的全流程功能，
包括专业词汇校正、热词表支持等，作为项目中转录功能的统一入口。
"""

import os
import sys
import json
import shutil
import logging
import tempfile
import subprocess
import time
import re
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Union, Tuple
from pathlib import Path

# 设置日志
logging.basicConfig(level=logging.INFO,
                   format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# ==================== 已弃用函数 ====================
# 以下函数已迁移到 DashScopeAudioAnalyzer，此处保留仅为向后兼容

def correct_professional_terms(text):
    """
    ⚠️ 已弃用：此函数已迁移到 DashScopeAudioAnalyzer._apply_regex_corrections()
    建议使用：DashScopeAudioAnalyzer.correct_professional_terms(text, use_regex_rules=True)
    
    校正文本中的专业术语，使用正则表达式替换
    """
    logger.warning("correct_professional_terms() 已弃用，建议使用 DashScopeAudioAnalyzer.correct_professional_terms()")
    
    # 为了向后兼容，尝试使用新分析器
    try:
        from streamlit_app.modules.ai_analyzers import DashScopeAudioAnalyzer
        analyzer = DashScopeAudioAnalyzer()
        return analyzer.correct_professional_terms(text, use_regex_rules=True)
    except Exception as e:
        logger.warning(f"无法使用新分析器，回退到原有实现: {str(e)}")
        # 回退到原有实现...
        corrections = [
            # 启赋蕴淳A2专用规则
            (r"启赋蕴淳\s*[Aa]2", "启赋蕴淳A2"),
            (r"(起肤|启赋|其赋|启步|寄附|企付|气付)蕴(醇|春|淳|纯|存|纯新)\s*[Aa]2", "启赋蕴淳A2"),
            (r"启赋\s+蕴(醇|春|淳|纯|存)\s*[Aa]2", "启赋蕴淳A2"),
            
            # 启赋蕴淳系列纠正
            (r"(其|起|启|寄|企|气|七)(妇|赋|肤|步|腹|肚|服|赴|附|父|复|伏|夫|扶)(孕|蕴|运|韵|氲|芸|允|孕)(唇|春|淳|纯|醇|淙|椿|纯)(准|尊|遵)?", "启赋蕴淳"),
            (r"(盲选)?(起|启|其|寄|企|气|七)?(腹|肚|服|赴|附|父|复|伏|夫|扶|妇|赋|肤|步)(孕|运|韵|氲|芸|允|孕|蕴)(唇|春|淳|纯|醇|淙|椿|纯)(准|尊|遵)?", "启赋蕴淳"),
            (r"(起肤|启赋|其赋|启步|寄附|企付|气付)蕴(醇|春|淳|纯|存|纯新)", "启赋蕴淳"),
            (r"启赋\s+蕴(醇|春|淳|纯|存)", "启赋蕴淳"),
            (r"(起肤|启赋|其赋|启步|寄附|企付|气付)\s+蕴(醇|春|淳|纯|存)", "启赋蕴淳"),
            (r"(起肤|启赋|其赋|启步|寄附|企付|气付)(韵|运|孕)(醇|春|淳|纯|存)", "启赋蕴淳"),
            (r"(起|启|其).*(孕|蕴).*(准|淳|唇)", "启赋蕴淳"),
            
            # 低聚糖HMO系列纠正
            (r"低聚糖\s*[Hh][Mm]?[Oo]?", "低聚糖HMO"),
            (r"低聚糖\s*[Hh](\s|是|，|,|。|\.)", "低聚糖HMO$1"),
            (r"低聚(塘|唐|煻)\s*[Hh][Mm]?[Oo]?", "低聚糖HMO"),
            (r"低(祖|组|族)糖\s*[Hh][Mm]?[Oo]?", "低聚糖HMO"),
            
            # A2奶源系列纠正
            (r"([Aa]|二|黑二|埃|爱|挨)奶源", "A2奶源"),
            (r"[Aa]\s*2奶源", "A2奶源"),
            (r"[Aa]二奶源", "A2奶源"),
            (r"([Aa]|二|黑二|埃|爱|挨)(\s+)奶源", "A2奶源"),
            
            # OPN/OPG系列纠正
            (r"欧盾", "OPN"),
            (r"O-P-N", "OPN"),
            (r"O\.P\.N", "OPN"),
            (r"(欧|偶|鸥)(\s+)?(盾|顿|敦)", "OPN"),
            (r"蛋白\s*[Oo]\s*[Pp]\s*[Nn]", "蛋白OPN"),
            (r"蛋白\s*([Oo]|欧|偶)\s*([Pp]|盾|顿)\s*([Nn]|恩)", "蛋白OPN"),
            (r"op[n]?王", "OPN"),
            (r"op[g]?王", "OPN"),
            
            # 自御力/自愈力系列
            (r"自(御|愈|育|渔|余|予|玉|预)力", "自愈力"),
            (r"自(御|愈|育|渔|余|予|玉|预)(\s+)力", "自愈力"),
        ]
        
        # 应用所有校正规则
        corrected_text = text
        for pattern, replacement in corrections:
            corrected_text = re.sub(pattern, replacement, corrected_text)
        
        return corrected_text

def apply_corrections_to_json(json_data, output_file=None):
    """
    ⚠️ 已弃用：此函数已迁移到 DashScopeAudioAnalyzer.apply_corrections_to_json()
    建议使用：DashScopeAudioAnalyzer.apply_corrections_to_json(json_data, use_regex_rules=True)
    
    应用专业词汇校正到JSON数据
    """
    logger.warning("apply_corrections_to_json() 已弃用，建议使用 DashScopeAudioAnalyzer.apply_corrections_to_json()")
    
    # 为了向后兼容，尝试使用新分析器
    try:
        from streamlit_app.modules.ai_analyzers import DashScopeAudioAnalyzer
        analyzer = DashScopeAudioAnalyzer()
        return analyzer.apply_corrections_to_json(json_data, output_file, use_regex_rules=True)
    except Exception as e:
        logger.warning(f"无法使用新分析器，回退到原有实现: {str(e)}")
        
        # 回退到原有实现
        if isinstance(json_data, str):
            try:
                with open(json_data, 'r', encoding='utf-8') as f:
                    data = json.load(f)
            except:
                logger.error(f"无法加载JSON文件: {json_data}")
                return None, False
        else:
            data = json_data
        
        # 应用专业词汇校正
        corrected = False
        if "transcripts" in data:
            for transcript in data["transcripts"]:
                # 校正整体文本
                if "text" in transcript:
                    original_text = transcript["text"]
                    transcript["text"] = correct_professional_terms(original_text)
                    if original_text != transcript["text"]:
                        corrected = True
                
                # 校正每个句子
                if "sentences" in transcript:
                    for sentence in transcript["sentences"]:
                        if "text" in sentence:
                            original_text = sentence["text"]
                            sentence["text"] = correct_professional_terms(original_text)
                            if original_text != sentence["text"]:
                                corrected = True
        
        # 检查是否有单独的sentences字段
        if "sentences" in data:
            for sentence in data["sentences"]:
                if "text" in sentence:
                    original_text = sentence["text"]
                    sentence["text"] = correct_professional_terms(original_text)
                    if original_text != sentence["text"]:
                        corrected = True
        
        # 如果需要输出到文件
        if output_file:
            with open(output_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
        
        return data, corrected

# ==================== 仍在使用的核心函数 ====================

def millisec_to_srt_time(ms):
    """将毫秒转换为SRT格式的时间戳 (HH:MM:SS,mmm)"""
    td = timedelta(milliseconds=ms)
    # 计算小时、分钟、秒和毫秒
    hours, remainder = divmod(td.seconds, 3600)
    minutes, seconds = divmod(remainder, 60)
    # 格式化为SRT时间格式
    return f"{hours:02}:{minutes:02}:{seconds:02},{ms % 1000:03}"

def extract_audio(video_path, output_path=None, temp_dir=None):
    """
    从视频中提取音频
    
    Args:
        video_path: 视频文件路径
        output_path: 输出音频文件路径，默认为None（使用临时文件）
        temp_dir: 临时目录，默认为None（使用系统临时目录）
        
    Returns:
        提取的音频文件路径
    """
    # 确保输入视频存在
    if not os.path.exists(video_path):
        logger.error(f"视频文件不存在: {video_path}")
        return None
    
    # 创建临时目录（如果需要）
    if temp_dir:
        os.makedirs(temp_dir, exist_ok=True)
    else:
        temp_dir = tempfile.mkdtemp(prefix="aliyun_transcribe_")
    
    # 如果未指定输出路径，则使用临时文件
    if not output_path:
        output_path = os.path.join(temp_dir, f"{int(time.time())}_processed_audio.wav")
    
    # 使用ffmpeg提取和预处理音频
    cmd = [
        "ffmpeg", "-y", "-i", video_path,
        "-vn", "-acodec", "pcm_s16le", 
        "-ar", "16000", "-ac", "1",
        "-af", "highpass=f=50,lowpass=f=8000,dynaudnorm,volume=1.5",
        output_path
    ]
    
    try:
        result = subprocess.run(cmd, capture_output=True, text=True)
        if result.returncode != 0:
            logger.error(f"音频提取失败: {result.stderr}")
            return None
        
        logger.info(f"音频预处理完成: {output_path}")
        return output_path
    except Exception as e:
        logger.error(f"执行音频提取命令失败: {str(e)}")
        return None

def transcribe_audio(audio_path, hotword_id=None, output_dir=None):
    """
    使用阿里云服务转录音频
    
    Args:
        audio_path: 音频文件路径
        hotword_id: 热词表ID，为None使用默认值
        output_dir: 输出目录，为None使用默认目录
        
    Returns:
        转录结果JSON文件路径或None（如果失败）
    """
    # 设置默认热词ID
    if hotword_id is None:
        hotword_id = "vocab-aivideo-4d73bdb1b5ef496d94f5104a957c012b"
    
    # 设置默认输出目录
    if output_dir is None:
        output_dir = os.path.join("data", "processed", "transcripts")
    
    # 确保输出目录存在
    os.makedirs(output_dir, exist_ok=True)
    
    # 获取API密钥
    try:
        from src.core.utils.video_processor import VideoProcessor
        import dashscope
        from dashscope.audio.asr.transcription import Transcription
        
        # 获取API密钥
        api_key = os.environ.get("DASHSCOPE_API_KEY")
        if not api_key:
            logger.error("未设置DASHSCOPE_API_KEY环境变量，无法继续")
            return None
            
        # 设置API密钥
        dashscope.api_key = api_key
        
        vp = VideoProcessor()
        
        # 上传到OSS获取URL，如果失败则重试
        audio_url = None
        max_retries = 3
        
        for attempt in range(max_retries):
            try:
                audio_url = vp._upload_to_accessible_url(audio_path, expiration=7200)  # 2小时过期时间
                if audio_url:
                    logger.info(f"OSS上传成功 (尝试 {attempt + 1}/{max_retries}): {audio_url[:50]}...")
                    break
                else:
                    logger.warning(f"OSS上传失败 (尝试 {attempt + 1}/{max_retries})")
            except Exception as e:
                logger.error(f"OSS上传异常 (尝试 {attempt + 1}/{max_retries}): {e}")
            
            if attempt < max_retries - 1:
                time.sleep(2)  # 等待2秒后重试
        
        if not audio_url:
            logger.error("OSS上传多次失败，无法继续转录。请检查OSS配置和网络连接。")
            return None
        
        # 使用SDK直接调用
        logger.info(f"使用DashScope SDK转录音频，热词ID: {hotword_id}")
        
        # 配置参数
        params = {
            "sample_rate": 16000,
            "punctuation": True,
            "vocabulary_id": hotword_id
        }
        
        # 提交异步转写任务
        api_response = Transcription.async_call(
            model="paraformer-v2",
            file_urls=[audio_url],  # 使用列表形式
            **params
        )
        
        # 从响应中获取任务ID
        task_id = None
        if hasattr(api_response, 'output') and isinstance(api_response.output, dict) and 'task_id' in api_response.output:
            task_id = api_response.output.get('task_id')
            logger.info(f"转录任务已提交，任务ID: {task_id}")
        else:
            logger.error("未获取到有效的任务ID")
            return None
        
        # 等待任务完成
        logger.info("等待转录任务完成...")
        sdk_result = Transcription.wait(task_id)
        
        # 保存基本信息
        base_name = os.path.splitext(os.path.basename(audio_path))[0]
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        # 提取转录URL
        transcription_url = None
        
        # 检查结果对象
        if hasattr(sdk_result, 'output') and isinstance(sdk_result.output, dict):
            output = sdk_result.output
            
            # 保存output到JSON文件
            api_json_output = os.path.join(output_dir, f"{base_name}_api_{timestamp}.json")
            with open(api_json_output, 'w', encoding='utf-8') as f:
                json.dump(output, f, ensure_ascii=False, indent=2)
            
            logger.info(f"API返回的JSON已保存: {api_json_output}")
            
            # 查找转录URL (路径: output.results[0].transcription_url)
            if 'results' in output and isinstance(output['results'], list) and len(output['results']) > 0:
                results = output['results']
                first_result = results[0]
                
                if isinstance(first_result, dict) and 'transcription_url' in first_result:
                    transcription_url = first_result['transcription_url']
                    logger.info(f"找到阿里云转录URL: {transcription_url}")
                    
                    # 将URL保存到文件
                    url_file = os.path.join(output_dir, f"{base_name}_url_{timestamp}.txt")
                    with open(url_file, 'w', encoding='utf-8') as f:
                        f.write(transcription_url)
                    
                    logger.info(f"转录URL已保存到: {url_file}")
                    
                    # 下载并保存原始转录JSON
                    raw_json_output = os.path.join(output_dir, f"{base_name}_raw_{timestamp}.json")
                    logger.info(f"正在下载中间JSON文件到: {raw_json_output}")
                    
                    curl_cmd = [
                        "curl", "-s", "-o", raw_json_output, transcription_url
                    ]
                    
                    curl_result = subprocess.run(curl_cmd)
                    if curl_result.returncode != 0:
                        logger.error(f"下载失败，curl返回码: {curl_result.returncode}")
                        return None
                        
                    # 检查文件大小
                    if os.path.exists(raw_json_output) and os.path.getsize(raw_json_output) > 0:
                        logger.info(f"成功下载中间JSON文件: {raw_json_output}")
                        
                        # 应用专业词汇校正
                        corrected_json_output = os.path.join(output_dir, f"{base_name}_corrected_{timestamp}.json")
                        result_json, has_corrections = apply_corrections_to_json(raw_json_output, corrected_json_output)
                        
                        if has_corrections:
                            logger.info(f"已进行专业词汇校正，结果保存到: {corrected_json_output}")
                        else:
                            logger.info(f"无需专业词汇校正，结果保存到: {corrected_json_output}")
                        
                        return corrected_json_output
                    else:
                        logger.error("下载失败或文件为空")
        
        logger.error("处理过程中出错，未能获取或下载转录JSON")
        return None
    except Exception as e:
        logger.exception(f"转录处理过程中出错: {str(e)}")
        return None

def json_to_srt(json_file, output_file):
    """将转录JSON转换为SRT格式字幕文件"""
    # 读取JSON文件
    with open(json_file, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    # 打开输出文件
    with open(output_file, 'w', encoding='utf-8') as f:
        # 获取所有句子
        sentences = None
        
        # 查找sentences的位置
        if "transcripts" in data and len(data["transcripts"]) > 0:
            if "sentences" in data["transcripts"][0]:
                sentences = data["transcripts"][0]["sentences"]
        elif "sentences" in data:
            sentences = data["sentences"]
        
        if not sentences:
            logger.error(f"在JSON中未找到句子数据: {json_file}")
            return False
            
        # 遍历每个句子生成SRT条目
        for idx, sentence in enumerate(sentences):
            # SRT序号
            f.write(f"{idx+1}\n")
            
            # 时间戳 (开始 --> 结束)
            start_time = millisec_to_srt_time(sentence['begin_time'])
            end_time = millisec_to_srt_time(sentence['end_time'])
            f.write(f"{start_time} --> {end_time}\n")
            
            # 句子文本
            f.write(f"{sentence['text']}\n\n")
    
    logger.info(f"已将JSON转换为SRT并保存至: {output_file}")
    return True

def process_video(video_path, output_dir=None, hotword_id=None, temp_dir=None):
    """
    完整处理视频：提取音频、转录、校正
    
    Args:
        video_path: 视频文件路径
        output_dir: 输出目录，为None使用默认目录
        hotword_id: 热词表ID，为None使用默认值
        temp_dir: 临时目录，为None使用系统临时目录
        
    Returns:
        转录结果JSON文件路径或None（如果失败）
    """
    try:
        # 提取并预处理音频
        logger.info(f"从视频提取音频: {video_path}")
        audio_path = extract_audio(video_path, temp_dir=temp_dir)
        if not audio_path:
            return None
        
        # 转录音频
        logger.info(f"开始转录音频: {audio_path}")
        transcript_json = transcribe_audio(audio_path, hotword_id, output_dir)
        if not transcript_json:
            return None
        
        # 返回转录结果的JSON文件路径
        return transcript_json
    except Exception as e:
        logger.exception(f"处理视频过程中出错: {str(e)}")
        return None

def create_srt_from_video(video_path, output_dir=None, hotword_id=None, temp_dir=None, output_srt=None):
    """
    从视频创建SRT字幕文件
    
    Args:
        video_path: 视频文件路径
        output_dir: 输出目录，为None使用默认目录
        hotword_id: 热词表ID，为None使用默认值
        temp_dir: 临时目录，为None使用系统临时目录
        output_srt: 输出SRT文件路径，为None自动生成
        
    Returns:
        SRT文件路径或None（如果失败）
    """
    # 设置默认输出目录
    if output_dir is None:
        output_dir = os.path.join("data", "processed", "transcripts")
    
    # 确保输出目录存在
    os.makedirs(output_dir, exist_ok=True)
    
    # 处理视频获取转录结果
    transcript_json = process_video(video_path, output_dir, hotword_id, temp_dir)
    if not transcript_json:
        logger.error("无法获取转录结果，SRT生成失败")
        return None
    
    # 设置默认SRT输出路径
    if output_srt is None:
        base_name = os.path.splitext(os.path.basename(video_path))[0]
        output_srt = os.path.join(output_dir, f"{base_name}_sentences.srt")
    
    # 转换为SRT
    if json_to_srt(transcript_json, output_srt):
        logger.info(f"SRT字幕生成成功: {output_srt}")
        return output_srt
    else:
        logger.error("SRT字幕生成失败")
        return None

def transcribe_audio_with_timestamp(audio_path, output_json=None, hotword_id=None, output_dir=None):
    """
    转录音频并返回带时间戳的转录结果
    
    Args:
        audio_path: 音频文件路径
        output_json: 输出JSON文件路径，为None使用默认命名
        hotword_id: 热词表ID，为None使用默认值
        output_dir: 输出目录，为None使用默认目录
        
    Returns:
        带时间戳的转录结果字典
    """
    # 如果未指定输出路径，创建一个
    if output_json is None:
        if output_dir is None:
            output_dir = os.path.join("data", "processed", "transcripts")
        os.makedirs(output_dir, exist_ok=True)
        
        # 从音频文件名创建JSON文件名
        basename = os.path.splitext(os.path.basename(audio_path))[0]
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_json = os.path.join(output_dir, f"{basename}_transcript_{timestamp}.json")
    
    # 调用转录功能
    result_path = transcribe_audio(audio_path, hotword_id, os.path.dirname(output_json))
    
    if result_path and os.path.exists(result_path):
        # 读取转录结果
        try:
            with open(result_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            # 应用专业词汇校正
            corrected_data, _ = apply_corrections_to_json(data)
            
            # 如果output_json与result_path不同，保存校正后的结果
            if output_json != result_path:
                with open(output_json, 'w', encoding='utf-8') as f:
                    json.dump(corrected_data, f, ensure_ascii=False, indent=2)
            
            return corrected_data
        except Exception as e:
            logger.error(f"处理转录结果时出错: {str(e)}")
            return None
    else:
        logger.error("转录失败，无法获取结果")
        return None 