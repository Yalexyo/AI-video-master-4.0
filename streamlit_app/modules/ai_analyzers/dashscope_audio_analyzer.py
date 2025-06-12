"""
DashScope语音转录分析器

专门处理阿里云DashScope语音转录、热词分析、专业词汇矫正功能的模块
"""

import os
import json
import logging
import time
from typing import Dict, Any, List, Optional, Union, Tuple
from pathlib import Path

logger = logging.getLogger(__name__)


class DashScopeAudioAnalyzer:
    """DashScope语音转录分析器"""
    
    def __init__(self, api_key: Optional[str] = None):
        """
        初始化DashScope语音分析器
        
        Args:
            api_key: DashScope API密钥
        """
        self.api_key = api_key or os.environ.get("DASHSCOPE_API_KEY")
        self.base_url = "https://dashscope.aliyuncs.com"
        
        if not self.api_key:
            logger.warning("未设置DASHSCOPE_API_KEY，DashScope语音分析器不可用")
        else:
            self._initialize_client()
    
    def _initialize_client(self):
        """初始化DashScope客户端"""
        try:
            import dashscope
            dashscope.api_key = self.api_key
            logger.info("DashScope语音分析器初始化成功")
        except ImportError as e:
            logger.error(f"无法导入DashScope: {str(e)}")
            self.api_key = None
        except Exception as e:
            logger.error(f"DashScope语音分析器初始化失败: {str(e)}")
            self.api_key = None
    
    def is_available(self) -> bool:
        """检查分析器是否可用"""
        return self.api_key is not None
    
    def transcribe_audio(
        self,
        audio_path: str,
        hotwords: Optional[List[str]] = None,
        professional_terms: Optional[List[str]] = None,
        language: str = "zh",
        format_result: bool = True,
        preset_vocabulary_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        转录音频文件
        
        Args:
            audio_path: 音频文件路径
            hotwords: 热词列表
            professional_terms: 专业词汇列表
            language: 语言代码
            format_result: 是否格式化结果
            preset_vocabulary_id: 预设词汇表ID
            
        Returns:
            转录结果字典
        """
        if not self.is_available():
            logger.warning("DashScope API不可用，使用模拟结果")
            return {
                "success": False,
                "error": "DashScope API不可用",
                "transcript": "模拟转录结果：这是一个测试音频文件的转录内容。",
                "segments": []
            }
        
        if not os.path.exists(audio_path):
            return {
                "success": False,
                "error": f"音频文件不存在: {audio_path}",
                "transcript": "",
                "segments": []
            }
        
        try:
            # 1. 上传音频到OSS
            oss_url = self._upload_audio_to_oss(audio_path)
            if not oss_url:
                return {
                    "success": False,
                    "error": "音频文件上传失败",
                    "transcript": "",
                    "segments": []
                }
            
            # 2. 调用DashScope ASR API
            result = self._call_dashscope_asr(
                oss_url=oss_url,
                hotwords=hotwords,
                professional_terms=professional_terms,
                language=language,
                preset_vocabulary_id=preset_vocabulary_id
            )
            
            # 3. 后处理结果
            if result.get("success") and professional_terms and result.get("transcript"):
                # 应用专业词汇修正
                corrected_transcript = self.correct_professional_terms(
                    result["transcript"], 
                    professional_terms
                    )
                result["transcript"] = corrected_transcript
                result["corrected"] = True
            
            # 🔧 修复：确保总是返回result，而不是仅在专业词汇修正时返回
            return result
                
        except Exception as e:
            logger.error(f"音频转录失败: {str(e)}")
            return {
                "success": False,
                "error": str(e),
                "transcript": "",
                "segments": []
            }
    
    def _upload_audio_to_oss(self, audio_path: str) -> Optional[str]:
        """
        上传音频文件到OSS，供DashScope API调用
        
        Args:
            audio_path: 本地音频文件路径
            
        Returns:
            OSS文件URL，失败时返回None
        """
        try:
            # 🔧 直接使用 oss2 库上传
            import oss2
            import uuid
            import os
            
            # 从环境变量获取OSS配置
            access_key_id = os.environ.get("OSS_ACCESS_KEY_ID")
            access_key_secret = os.environ.get("OSS_ACCESS_KEY_SECRET")
            bucket_name = os.environ.get("OSS_BUCKET_NAME", "ai-video-master")
            endpoint = os.environ.get("OSS_ENDPOINT", "oss-cn-shanghai.aliyuncs.com")
            
            if not (access_key_id and access_key_secret):
                logger.error("📤 OSS配置不完整，缺少访问密钥")
                return None
            
            # 创建OSS客户端
            auth = oss2.Auth(access_key_id, access_key_secret)
            bucket = oss2.Bucket(auth, endpoint, bucket_name)
            
            # 生成OSS对象名
            file_extension = os.path.splitext(audio_path)[1]
            oss_filename = f"audio_transcription/{uuid.uuid4().hex}{file_extension}"
            
            logger.info(f"📤 正在上传 {audio_path} 到 OSS: {oss_filename}")
            
            # 🔧 修复：使用正确的OSS上传方法
            with open(audio_path, 'rb') as f:
                bucket.put_object(oss_filename, f)
            
            # 生成公网访问URL（临时URL，1小时有效）
            oss_url = bucket.sign_url('GET', oss_filename, 3600)
            
            logger.info(f"📤 OSS上传成功: {oss_url}")
            return oss_url
                
        except ImportError as e:
            logger.warning(f"📤 oss2库不可用，尝试替代方案: {e}")
            return self._fallback_upload_to_oss(audio_path)
        except Exception as e:
            error_details = {
                'error_type': type(e).__name__,
                'error_message': str(e),
                'traceback': getattr(e, '__traceback__', None)
            }
            
            # 如果是OSS特定错误，提取更多信息
            if hasattr(e, 'status'):
                error_details['status'] = e.status
            if hasattr(e, 'code'):
                error_details['code'] = e.code
            if hasattr(e, 'request_id'):
                error_details['request_id'] = e.request_id
                
            logger.error(f"📤 OSS上传失败: {error_details}")
            return self._fallback_upload_to_oss(audio_path)
    
    def _fallback_upload_to_oss(self, audio_path: str) -> Optional[str]:
        """
        OSS上传的替代方案
        
        Args:
            audio_path: 本地音频文件路径
            
        Returns:
            OSS文件URL，失败时返回None
        """
        try:
            # 🔧 方法2：尝试直接使用 oss2 库
            import oss2
            import uuid
            import os
            
            # 从环境变量获取OSS配置
            access_key_id = os.environ.get("OSS_ACCESS_KEY_ID")
            access_key_secret = os.environ.get("OSS_ACCESS_KEY_SECRET")
            bucket_name = os.environ.get("OSS_BUCKET_NAME", "ai-video-master")
            endpoint = os.environ.get("OSS_ENDPOINT", "oss-cn-shanghai.aliyuncs.com")
            
            if not (access_key_id and access_key_secret):
                logger.error("📤 OSS配置不完整，缺少访问密钥")
                return None
            
            # 创建OSS客户端
            auth = oss2.Auth(access_key_id, access_key_secret)
            bucket = oss2.Bucket(auth, endpoint, bucket_name)
            
            # 生成OSS对象名
            file_extension = os.path.splitext(audio_path)[1]
            object_name = f"dashscope-audio/{uuid.uuid4().hex}{file_extension}"
            
            logger.info(f"📤 使用oss2库上传文件: {object_name}")
            
            # 上传文件
            with open(audio_path, 'rb') as f:
                bucket.put_object(object_name, f)
            
            # 生成公网访问URL（临时URL，1小时有效）
            oss_url = bucket.sign_url('GET', object_name, 3600)
            
            logger.info(f"📤 oss2上传成功: {oss_url}")
            return oss_url
            
        except ImportError:
            logger.error("📤 oss2库不可用，无法上传到OSS")
            return None
        except Exception as e:
            error_details = {
                'error_type': type(e).__name__,
                'error_message': str(e)
            }
            
            # 如果是OSS特定错误，提取更多信息
            if hasattr(e, 'status'):
                error_details['status'] = e.status
            if hasattr(e, 'code'):
                error_details['code'] = e.code
            if hasattr(e, 'request_id'):
                error_details['request_id'] = e.request_id
                
            logger.error(f"📤 oss2上传失败: {error_details}")
            return None
    
    def _call_dashscope_asr(
        self, 
        oss_url: str, 
        hotwords: Optional[List[str]] = None,
        professional_terms: Optional[List[str]] = None,
        language: str = "zh",
        preset_vocabulary_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        调用DashScope ASR API进行语音识别（基于官方文档的paraformer-v2录音文件识别）
        
        官方文档：https://help.aliyun.com/zh/model-studio/paraformer-recorded-speech-recognition-python-sdk
        
        Args:
            oss_url: OSS文件URL（必须是公网可访问的URL）
            hotwords: 热词列表
            professional_terms: 专业词汇列表
            language: 语言代码（zh/en/ja/ko等）
            preset_vocabulary_id: 预设词汇表ID
            
        Returns:
            转录结果字典
        """
        try:
            import dashscope
            from dashscope.audio.asr import Transcription
            from http import HTTPStatus
            
            logger.info(f"🎤 开始DashScope录音文件识别")
            logger.info(f"📁 音频URL: {oss_url}")
            logger.info(f"🌐 目标语言: {language}")
            
            # 🔧 根据官方文档配置paraformer-v2参数
            params = {
                'model': 'paraformer-v2',              # 官方推荐：最新多语种模型
                'file_urls': [oss_url],                # 文件URL列表（公网可访问）
                'language_hints': [language],          # 语言提示（提升识别效果）
                
                # 🎯 核心功能参数（时间戳相关）
                'enable_words': True,                  # ✅ 关键：启用词级别时间戳
                'enable_punctuation_prediction': True, # ✅ 官方推荐：标点符号预测
                'enable_inverse_text_normalization': True,  # ✅ 官方推荐：ITN
                
                # 🔧 优化参数
                'enable_disfluency': False,            # 不过滤语气词（保持原始内容）
                'enable_sample_rate_adaptive': True,   # 自动降采样（适配任意采样率）
            }
            
            # 🎯 热词处理（官方支持定制热词功能）
            if preset_vocabulary_id:
                params["vocabulary_id"] = preset_vocabulary_id
                logger.info(f"📋 使用预设热词词汇表: {preset_vocabulary_id}")
            elif hotwords and len(hotwords) > 0:
                # 创建自定义词汇表
                vocabulary_id = self._create_vocabulary(hotwords)
                if vocabulary_id:
                    params["vocabulary_id"] = vocabulary_id
                    logger.info(f"✏️ 使用自定义热词词汇表: {vocabulary_id} (共{len(hotwords)}个热词)")
                else:
                    logger.warning("⚠️ 自定义热词词汇表创建失败，继续使用基础识别")
            else:
                logger.info("🚫 未使用热词优化")
            
            logger.info(f"🔧 API调用参数: {params}")
            
            # 🔧 使用官方推荐的异步调用方式
            logger.info("📤 提交录音文件识别任务...")
            task_response = Transcription.async_call(**params)
            
            # 验证任务提交结果
            if not task_response or not hasattr(task_response, 'output') or not task_response.output:
                logger.error("❌ 录音文件识别任务提交失败：未获得有效响应")
                return {
                    "success": False,
                    "error": "录音文件识别任务提交失败：API未返回有效的任务ID",
                    "transcript": "",
                    "segments": []
                }
            
            task_id = task_response.output.task_id
            logger.info(f"✅ 任务提交成功，TaskId: {task_id}")
            
            # 🔧 等待任务完成（官方推荐的轮询方式）
            logger.info("⏳ 等待识别任务完成...")
            transcribe_response = Transcription.wait(task=task_id)
            
            # 检查响应状态
            if transcribe_response.status_code == HTTPStatus.OK:
                logger.info("🎉 录音文件识别成功！开始解析结果...")
                
                # 解析识别结果
                result = self._parse_dashscope_result(transcribe_response.output)
                
                # 记录成功统计
                if result.get("success"):
                    segments_count = len(result.get("segments", []))
                    text_length = len(result.get("transcript", ""))
                    logger.info(f"📊 识别统计: 文本长度={text_length}字符, 时间戳片段={segments_count}个")
                
                return result
                
            else:
                # 处理识别失败
                error_msg = f"DashScope录音文件识别失败: {getattr(transcribe_response, 'message', '未知错误')}"
                status_code = getattr(transcribe_response, 'status_code', 'unknown')
                
                logger.error(f"❌ {error_msg} (状态码: {status_code})")
                
                return {
                    "success": False,
                    "error": f"{error_msg} (状态码: {status_code})",
                    "transcript": "",
                    "segments": [],
                    "error_type": "api_error",
                    "status_code": status_code
                }
                
        except ImportError as e:
            error_msg = f"DashScope SDK导入失败: {str(e)}"
            logger.error(f"❌ {error_msg}")
            return {
                "success": False,
                "error": f"{error_msg}。请安装最新版DashScope SDK: pip install dashscope --upgrade",
                "transcript": "",
                "segments": [],
                "error_type": "import_error"
            }
        except Exception as e:
            error_msg = f"DashScope录音文件识别调用异常: {str(e)}"
            logger.error(f"❌ {error_msg}")
            import traceback
            logger.error(f"详细错误堆栈:\n{traceback.format_exc()}")
            
            # 根据错误类型提供具体建议
            suggestions = []
            error_str = str(e).lower()
            
            if "network" in error_str or "connection" in error_str:
                suggestions.append("检查网络连接是否正常")
                suggestions.append("确认可以访问dashscope.aliyuncs.com")
            elif "api key" in error_str or "authentication" in error_str:
                suggestions.append("检查DASHSCOPE_API_KEY环境变量是否正确设置")
                suggestions.append("确认API Key有效且有录音文件识别权限")
            elif "url" in error_str or "download" in error_str:
                suggestions.append("确认音频文件URL可以通过公网访问")
                suggestions.append("检查OSS文件权限设置是否为公共读")
            elif "format" in error_str or "codec" in error_str:
                suggestions.append("确认音频格式被支持（mp3/wav/mp4/aac等）")
                suggestions.append("尝试转换为标准格式后重试")
            
            return {
                "success": False,
                "error": error_msg,
                "transcript": "",
                "segments": [],
                "error_type": "exception",
                "suggestions": suggestions
            }
    
    def _parse_dashscope_result(self, result) -> Dict[str, Any]:
        """
        解析DashScope ASR结果，支持多种响应格式
        
        Args:
            result: DashScope API响应结果 (可能是字典或TranscriptionOutput对象)
            
        Returns:
            标准化的转录结果字典
        """
        try:
            # 记录原始结果用于调试
            logger.debug(f"正在解析DashScope结果类型: {type(result)}")
            
            full_text = ""
            srt_content = ""
            segments = []
            
            # 处理 TranscriptionOutput 对象
            if hasattr(result, '__dict__'):
                # 转换为字典以便统一处理
                try:
                    # 安全地检查 results 属性
                    results = getattr(result, 'results', None)
                    if results is not None:
                        result_dict = {'results': results}
                        
                        # 安全地添加其他可能的属性
                        for attr in ['task_id', 'task_status', 'submit_time', 'scheduled_time', 'end_time', 'task_metrics', 'code', 'message']:
                            try:
                                value = getattr(result, attr, None)
                                if value is not None:
                                    result_dict[attr] = value
                            except (KeyError, AttributeError) as e:
                                # 忽略不存在的属性，避免 KeyError
                                logger.debug(f"属性 {attr} 不存在或无法访问: {e}")
                                continue
                        
                        logger.debug(f"转换TranscriptionOutput为字典: {list(result_dict.keys())}")
                        result = result_dict
                    else:
                        # 如果没有 results 属性，尝试直接转换整个对象
                        try:
                            result = vars(result) if hasattr(result, '__dict__') else result
                            logger.debug(f"直接转换对象属性: {list(result.keys()) if isinstance(result, dict) else type(result)}")
                        except Exception as e:
                            logger.warning(f"无法直接转换对象: {e}")
                except Exception as e:
                    logger.error(f"处理TranscriptionOutput对象时发生错误: {e}")
                    # 继续处理，可能是其他类型的对象
            
            # 现在统一按字典格式处理
            logger.debug(f"准备解析结果，类型: {type(result)}")
            if isinstance(result, dict):
                logger.debug(f"结果字段: {list(result.keys())}")
                if 'results' in result:
                    logger.debug(f"results字段存在，值: {result['results']}")
                    logger.debug(f"results是否为真值: {bool(result['results'])}")
            
            # 格式1: DashScope录音文件识别 - 标准格式
            if isinstance(result, dict) and 'results' in result and result['results']:
                logger.debug(f"检测到DashScope results字段，task_status: {result.get('task_status', 'unknown')}")
                
                # 检查任务状态
                task_status = result.get('task_status', '')
                if task_status != 'SUCCEEDED':
                    logger.warning(f"DashScope任务未成功完成，状态: {task_status}")
                    return {
                        "success": False,
                        "error": f"DashScope任务状态: {task_status}",
                        "transcript": "",
                        "segments": [],
                        "task_status": task_status
                    }
                
                # 查找成功的子任务
                results_list = result['results'] if isinstance(result['results'], list) else [result['results']]
                for result_item in results_list:
                    if not isinstance(result_item, dict):
                        continue
                        
                    subtask_status = result_item.get('subtask_status', '')
                    if subtask_status != 'SUCCEEDED':
                        logger.debug(f"跳过失败的子任务，状态: {subtask_status}")
                        continue
                    
                    transcription_url = result_item.get('transcription_url', '')
                    if not transcription_url:
                        logger.debug("子任务缺少transcription_url")
                        continue
                    
                    logger.info(f"找到成功的转录结果URL: {transcription_url[:50]}...")
                    
                    # 下载并解析转录结果
                    transcription_result = self._download_transcription_result(transcription_url)
                    if transcription_result:
                        return transcription_result
                    else:
                        logger.warning("转录结果下载失败，返回基本信息")
                        return {
                            "success": True,
                            "transcript": "转录结果下载失败",
                            "srt_content": "",
                            "segments": [],
                            "has_timestamps": False,
                            "transcription_url": transcription_url,
                            "note": "转录结果文件下载失败"
                        }
                
                # 如果没有找到成功的子任务
                logger.error("所有DashScope子任务都失败了")
                return {
                    "success": False,
                    "error": "所有子任务都失败",
                    "transcript": "",
                    "segments": []
                }
            
            # 格式3: 直接在顶级的text字段 (老版本)
            if isinstance(result, dict) and 'text' in result:
                full_text = result['text']
                if full_text and full_text.strip():
                    logger.warning("DashScope结果为旧版格式，缺少时间戳，只返回纯文本")
                    return {
                        "success": True,
                        "transcript": full_text.strip(),
                        "srt_content": "",
                        "segments": [],
                        "has_timestamps": False
                    }
            
            # 格式4: 检查是否是空音频导致的空结果
            if not result or (isinstance(result, dict) and not any(result.values())):
                logger.warning("DashScope返回空结果，可能是音频无语音内容")
                return {
                    "success": True,
                    "transcript": "",
                    "srt_content": "",
                    "segments": [],
                    "has_timestamps": False,
                    "note": "音频无语音内容或静音"
                }
            
            # 格式5: 其他可能的格式尝试
            if isinstance(result, dict):
                # 尝试查找任何可能包含文本的字段
                possible_text_fields = ['transcript', 'text', 'content', 'result']
                for field in possible_text_fields:
                    if field in result and result[field]:
                        text_value = result[field]
                        if isinstance(text_value, str) and text_value.strip():
                            logger.warning(f"DashScope使用备用字段'{field}'解析文本")
                            return {
                                "success": True,
                                "transcript": text_value.strip(),
                                "srt_content": "",
                                "segments": [],
                                "has_timestamps": False
                            }
            
            # 所有格式都无法识别
            if isinstance(result, dict):
                keys_info = list(result.keys())
            else:
                keys_info = [attr for attr in dir(result) if not attr.startswith('_')] if hasattr(result, '__dict__') else str(type(result))
            
            logger.error(f"无法识别的DashScope结果格式，原始结果结构: {keys_info}")
            return {
                "success": False,
                "error": f"无法识别的DashScope结果格式: {type(result)}",
                "transcript": "",
                "segments": [],
                "raw_result_type": str(type(result)),
                "raw_result_keys": keys_info
            }
            
        except Exception as e:
            logger.error(f"解析DashScope结果时发生未知错误: {e}")
            import traceback
            logger.error(f"详细错误堆栈:\n{traceback.format_exc()}")
            
            return {
                "success": False,
                "error": f"解析DashScope转录结果失败: {str(e)}",
                "transcript": "",
                "segments": [],
                "exception_details": str(e)
            }

    def _download_transcription_result(self, transcription_url: str) -> Optional[Dict[str, Any]]:
        """
        下载并解析DashScope转录结果文件
        
        Args:
            transcription_url: 转录结果JSON文件的URL
            
        Returns:
            解析后的转录结果或None
        """
        try:
            import requests
            
            logger.info(f"📥 开始下载转录结果: {transcription_url[:50]}...")
            
            # 下载JSON文件
            response = requests.get(transcription_url, timeout=30)
            response.raise_for_status()
            
            # 解析JSON内容
            transcription_data = response.json()
            logger.info(f"转录结果JSON结构: {list(transcription_data.keys())}")
            
            # 输出完整的JSON数据以便调试
            logger.info(f"完整转录结果: {transcription_data}")
            
            # 按照官方文档格式解析
            if 'transcripts' not in transcription_data:
                logger.error("转录结果格式错误：缺少transcripts字段")
                return None
            
            full_text = ""
            srt_content = ""
            segments = []
            
            for transcript in transcription_data['transcripts']:
                if 'sentences' in transcript and transcript['sentences']:
                    logger.info(f"处理转录包含 {len(transcript['sentences'])} 个句子")
                    for i, sentence in enumerate(transcript['sentences'], 1):
                        start_ms = sentence.get('begin_time', 0)
                        end_ms = sentence.get('end_time', 0)
                        text = sentence.get('text', '')
                        
                        logger.info(f"句子 {i}: 原始时间戳 start={start_ms} ({type(start_ms)}), end={end_ms} ({type(end_ms)})")
                        logger.info(f"句子 {i}: 文本={text[:50]}...")
                        
                        # 确保时间戳是整数类型
                        start_ms = int(float(start_ms)) if start_ms else 0
                        end_ms = int(float(end_ms)) if end_ms else 0
                        
                        logger.info(f"句子 {i}: 转换后时间戳 start={start_ms}ms, end={end_ms}ms")
                        
                        if text and text.strip():
                            full_text += text + " "
                            start_time = self._format_timestamp(start_ms)
                            end_time = self._format_timestamp(end_ms)
                            logger.info(f"句子 {i}: 格式化时间戳 {start_time} --> {end_time}")
                            srt_content += f"{i}\n{start_time} --> {end_time}\n{text}\n\n"
                            
                            segments.append({
                                "start": start_ms / 1000.0,
                                "end": end_ms / 1000.0,
                                "text": text.strip()
                            })
                
                # 如果没有sentences，尝试使用text字段
                elif 'text' in transcript:
                    full_text = transcript['text']
            
            if segments:
                logger.info(f"✅ 成功解析转录结果: {len(segments)}个片段, {len(full_text.strip())}字符")
                return {
                    "success": True,
                    "transcript": full_text.strip(),
                    "srt_content": srt_content.strip(),
                    "segments": segments,
                    "has_timestamps": True
                }
            elif full_text.strip():
                logger.warning("⚠️ 转录结果无时间戳，仅返回文本")
                return {
                    "success": True,
                    "transcript": full_text.strip(),
                    "srt_content": "",
                    "segments": [],
                    "has_timestamps": False
                }
            else:
                logger.warning("⚠️ 转录结果为空")
                return {
                    "success": True,
                    "transcript": "",
                    "srt_content": "",
                    "segments": [],
                    "has_timestamps": False,
                    "note": "音频无语音内容"
                }
                
        except requests.exceptions.RequestException as e:
            logger.error(f"❌ 下载转录结果失败: {e}")
            return None
        except Exception as e:
            logger.error(f"❌ 解析转录结果失败: {e}")
            import traceback
            logger.error(f"详细错误: {traceback.format_exc()}")
            return None

    def _format_timestamp(self, milliseconds) -> str:
        """
        将毫秒转换为格式化的时间戳
        
        Args:
            milliseconds: 毫秒数（int或float）
            
        Returns:
            格式化的时间戳
        """
        # 确保输入是数字类型并转换为整数
        ms = int(float(milliseconds)) if milliseconds else 0
        
        seconds = ms // 1000
        minutes = seconds // 60
        hours = minutes // 60
        seconds = seconds % 60
        ms_remainder = ms % 1000
        
        return f"{hours:02d}:{minutes:02d}:{seconds:02d},{ms_remainder:03d}"
    
    def transcribe_video(
        self,
        video_path: str,
        hotwords: Optional[List[str]] = None,
        professional_terms: Optional[List[str]] = None,
        extract_audio_first: bool = True,
        preset_vocabulary_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        视频转录（先提取音频再转录）
        
        Args:
            video_path: 视频文件路径
            hotwords: 热词列表
            professional_terms: 专业词汇列表
            extract_audio_first: 是否先提取音频
            preset_vocabulary_id: 预设词汇表ID
            
        Returns:
            转录结果字典
        """
        if not os.path.exists(video_path):
            return {
                "success": False,
                "error": f"视频文件不存在: {video_path}",
                "transcript": "",
                "segments": []
            }
        
        try:
            if extract_audio_first:
                # 提取音频
                audio_path = self._extract_audio_from_video(video_path)
                if not audio_path:
                    return {
                        "success": False,
                        "error": "音频提取失败",
                        "transcript": "",
                        "segments": []
                    }
            else:
                audio_path = video_path
            
            # 转录音频
            result = self.transcribe_audio(
                audio_path, 
                hotwords, 
                professional_terms,
                preset_vocabulary_id=preset_vocabulary_id
            )
            
            # 清理临时音频文件
            if extract_audio_first and audio_path != video_path:
                try:
                    os.unlink(audio_path)
                except:
                    pass
            
            return result
            
        except Exception as e:
            logger.error(f"视频转录失败: {str(e)}")
            return {
                "success": False,
                "error": str(e),
                "transcript": "",
                "segments": []
            }
    
    def analyze_hotwords(
        self,
        transcript_text: str,
        domain: str = "general"
    ) -> Dict[str, Any]:
        """
        分析转录文本中的热词
        
        Args:
            transcript_text: 转录文本
            domain: 领域 (general, medical, legal, finance, etc.)
            
        Returns:
            热词分析结果
        """
        if not self.is_available():
            return {
                "success": False,
                "error": "DashScope API不可用",
                "hotwords": [],
                "keywords": []
            }
        
        try:
            # 使用文本分析API提取关键词
            from dashscope import TextAnalysis
            
            result = TextAnalysis.call(
                model="text-analysis-v1",
                input=transcript_text,
                task="keyword_extraction",
                domain=domain
            )
            
            if result.status_code == 200:
                keywords = result.output.get('keywords', [])
                
                # 转换为热词格式
                hotwords = [kw.get('word', '') for kw in keywords if kw.get('score', 0) > 0.5]
                
                return {
                    "success": True,
                    "hotwords": hotwords,
                    "keywords": keywords,
                    "domain": domain
                }
            else:
                return {
                    "success": False,
                    "error": f"热词分析失败: {result.message}",
                    "hotwords": [],
                    "keywords": []
                }
                
        except Exception as e:
            logger.error(f"热词分析失败: {str(e)}")
            return {
                "success": False,
                "error": str(e),
                "hotwords": [],
                "keywords": []
            }
    
    def create_custom_vocabulary(
        self,
        terms: List[str],
        vocab_name: str = "custom_vocab",
        domain: str = "general"
    ) -> Optional[str]:
        """
        创建自定义词汇表
        
        Args:
            terms: 词汇列表
            vocab_name: 词汇表名称
            domain: 领域
            
        Returns:
            词汇表ID
        """
        if not self.is_available():
            logger.warning("DashScope API不可用")
            return None
        
        try:
            from dashscope.audio.asr import VocabularyService
            
            vocab_service = VocabularyService()
            result = vocab_service.create_vocabulary(
                vocabulary_name=vocab_name,
                domain=domain,
                words=terms
            )
            
            # 适配不同的返回格式
            if isinstance(result, dict):
                # 如果直接返回字典
                if result.get("success", True):  # 假设成功
                    vocab_id = result.get('vocabulary_id') or result.get("output", {}).get('vocabulary_id')
                    if vocab_id:
                        logger.info(f"自定义词汇表创建成功: {vocab_id}")
                        return vocab_id
                logger.error(f"词汇表创建失败: {result.get('error', '未知错误')}")
                return None
            elif hasattr(result, 'status_code'):
                # 如果有status_code属性（老格式）
                if result.status_code == 200:
                    vocab_id = result.output.get('vocabulary_id')
                    logger.info(f"自定义词汇表创建成功: {vocab_id}")
                    return vocab_id
                else:
                    logger.error(f"词汇表创建失败: {result.message}")
                    return None
            else:
                logger.error(f"未知的响应格式: {type(result)}")
                return None
                
        except Exception as e:
            logger.error(f"创建词汇表失败: {str(e)}")
            return None
    
    def correct_professional_terms(
        self,
        text: str,
        professional_terms: Optional[List[str]] = None,
        similarity_threshold: float = 0.8,
        use_regex_rules: bool = True
    ) -> str:
        """
        专业词汇矫正 - 支持正则表达式规则和相似度匹配两种方式
        
        Args:
            text: 待矫正文本
            professional_terms: 专业词汇列表 (用于相似度匹配)
            similarity_threshold: 相似度阈值
            use_regex_rules: 是否使用预定义的正则表达式规则
            
        Returns:
            矫正后的文本
        """
        if not text:
            return text
        
        corrected_text = text
        
        # 1. 首先应用正则表达式规则 (从 transcribe_core.py 移植)
        if use_regex_rules:
            corrected_text = self._apply_regex_corrections(corrected_text)
        
        # 2. 然后应用相似度匹配 (如果提供了专业词汇列表)
        if professional_terms:
            corrected_text = self._apply_similarity_corrections(
                corrected_text, professional_terms, similarity_threshold
            )
        
        return corrected_text
    
    def _apply_regex_corrections(self, text: str) -> str:
        """
        应用正则表达式校正规则 (从 transcribe_core.py 移植的精确规则)
        """
        import re
        
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
            try:
                before_count = len(re.findall(pattern, corrected_text))
                corrected_text = re.sub(pattern, replacement, corrected_text)
                after_count = len(re.findall(replacement, corrected_text))
                
                if before_count > 0:
                    logger.debug(f"正则矫正: {pattern} -> {replacement} (匹配 {before_count} 次)")
            except Exception as e:
                logger.warning(f"正则表达式 {pattern} 执行失败: {str(e)}")
        
        return corrected_text
    
    def _apply_similarity_corrections(
        self, 
        text: str, 
        professional_terms: List[str], 
        similarity_threshold: float
    ) -> str:
        """
        应用相似度匹配校正
        """
        try:
            import difflib
            
            corrected_text = text
            words = text.split()
            
            for i, word in enumerate(words):
                # 找到最相似的专业词汇
                matches = difflib.get_close_matches(
                    word, professional_terms, 
                    n=1, cutoff=similarity_threshold
                )
                
                if matches and matches[0] != word:
                    # 替换为专业词汇
                    corrected_word = matches[0]
                    corrected_text = corrected_text.replace(word, corrected_word, 1)
                    logger.debug(f"相似度矫正: {word} -> {corrected_word}")
            
            return corrected_text
            
        except Exception as e:
            logger.error(f"相似度匹配失败: {str(e)}")
            return text
    
    def batch_transcribe(
        self,
        file_paths: List[str],
        hotwords: Optional[List[str]] = None,
        professional_terms: Optional[List[str]] = None,
        progress_callback: Optional[callable] = None
    ) -> List[Dict[str, Any]]:
        """
        批量转录
        
        Args:
            file_paths: 文件路径列表
            hotwords: 热词列表
            professional_terms: 专业词汇列表
            progress_callback: 进度回调函数
            
        Returns:
            转录结果列表
        """
        results = []
        total = len(file_paths)
        
        for i, file_path in enumerate(file_paths):
            if progress_callback:
                progress = int((i / total) * 100)
                progress_callback(progress, f"正在转录 {i+1}/{total}: {Path(file_path).name}")
            
            # 判断文件类型
            file_ext = Path(file_path).suffix.lower()
            if file_ext in ['.mp4', '.avi', '.mov', '.mkv', '.webm']:
                result = self.transcribe_video(file_path, hotwords, professional_terms)
            elif file_ext in ['.wav', '.mp3', '.m4a', '.aac', '.flac']:
                result = self.transcribe_audio(file_path, hotwords, professional_terms)
            else:
                result = {
                    "success": False,
                    "error": f"不支持的文件格式: {file_ext}",
                    "transcript": "",
                    "segments": []
                }
            
            result["file_path"] = file_path
            result["file_name"] = Path(file_path).name
            results.append(result)
        
        if progress_callback:
            progress_callback(100, f"批量转录完成，共处理 {total} 个文件")
        
        return results
    
    def _extract_audio_from_video(self, video_path: str) -> Optional[str]:
        """从视频中提取音频"""
        try:
            import subprocess
            import tempfile
            
            # 创建临时音频文件
            with tempfile.NamedTemporaryFile(suffix='.wav', delete=False) as tmp:
                audio_path = tmp.name
            
            # 使用ffmpeg提取音频
            cmd = [
                'ffmpeg', '-i', video_path,
                '-vn',  # 不要视频
                '-acodec', 'pcm_s16le',  # 16位PCM编码
                '-ar', '16000',  # 16kHz采样率
                '-ac', '1',  # 单声道
                '-y',  # 覆盖输出文件
                audio_path
            ]
            
            result = subprocess.run(cmd, capture_output=True, text=True)
            
            if result.returncode == 0:
                logger.info(f"音频提取成功: {audio_path}")
                return audio_path
            else:
                logger.error(f"音频提取失败: {result.stderr}")
                return None
                
        except Exception as e:
            logger.error(f"音频提取异常: {str(e)}")
            return None
    
    def _create_vocabulary(self, words: List[str]) -> Optional[str]:
        """创建临时词汇表"""
        try:
            import uuid
            vocab_name = f"temp_vocab_{uuid.uuid4().hex[:8]}"
            return self.create_custom_vocabulary(words, vocab_name)
        except Exception as e:
            logger.error(f"创建临时词汇表失败: {str(e)}")
            return None
    
    def _apply_professional_correction(
        self, 
        text: str, 
        professional_terms: List[str]
    ) -> str:
        """应用专业词汇矫正"""
        return self.correct_professional_terms(text, professional_terms)
    
    def apply_corrections_to_json(
        self, 
        json_data: Union[Dict[str, Any], str], 
        output_file: Optional[str] = None,
        professional_terms: Optional[List[str]] = None,
        use_regex_rules: bool = True
    ) -> Tuple[Dict[str, Any], bool]:
        """
        应用专业词汇校正到JSON数据 (从 transcribe_core.py 移植)
        
        Args:
            json_data: JSON数据（可以是字典或文件路径）
            output_file: 输出JSON文件路径，如果为None则只返回结果不写入文件
            professional_terms: 专业词汇列表
            use_regex_rules: 是否使用正则表达式规则
            
        Returns:
            (修正后的JSON数据, 是否有修改)
        """
        import json
        
        # 如果json_data是字符串，则尝试将其解释为文件路径
        if isinstance(json_data, str):
            try:
                with open(json_data, 'r', encoding='utf-8') as f:
                    data = json.load(f)
            except Exception as e:
                logger.error(f"无法加载JSON文件: {json_data}, 错误: {str(e)}")
                return {}, False
        else:
            data = json_data.copy() if isinstance(json_data, dict) else {}
        
        # 应用专业词汇校正
        corrected = False
        
        # 处理 transcripts 字段
        if "transcripts" in data:
            for transcript in data["transcripts"]:
                # 校正整体文本
                if "text" in transcript:
                    original_text = transcript["text"]
                    transcript["text"] = self.correct_professional_terms(
                        original_text, professional_terms, use_regex_rules=use_regex_rules
                    )
                    if original_text != transcript["text"]:
                        corrected = True
                
                # 校正每个句子
                if "sentences" in transcript:
                    for sentence in transcript["sentences"]:
                        if "text" in sentence:
                            original_text = sentence["text"]
                            sentence["text"] = self.correct_professional_terms(
                                original_text, professional_terms, use_regex_rules=use_regex_rules
                            )
                            if original_text != sentence["text"]:
                                corrected = True
        
        # 检查是否有单独的sentences字段（适配不同API返回格式）
        if "sentences" in data:
            for sentence in data["sentences"]:
                if "text" in sentence:
                    original_text = sentence["text"]
                    sentence["text"] = self.correct_professional_terms(
                        original_text, professional_terms, use_regex_rules=use_regex_rules
                    )
                    if original_text != sentence["text"]:
                        corrected = True
        
        # 处理单独的 text 字段
        if "text" in data:
            original_text = data["text"]
            data["text"] = self.correct_professional_terms(
                original_text, professional_terms, use_regex_rules=use_regex_rules
            )
            if original_text != data["text"]:
                corrected = True
        
        # 如果需要输出到文件
        if output_file:
            try:
                with open(output_file, 'w', encoding='utf-8') as f:
                    json.dump(data, f, ensure_ascii=False, indent=2)
                logger.info(f"校正后的JSON已保存到: {output_file}")
            except Exception as e:
                logger.error(f"保存JSON文件失败: {str(e)}")
        
        return data, corrected
    
    def _format_transcript_result(self, raw_result: Dict[str, Any]) -> Dict[str, Any]:
        """格式化转录结果"""
        try:
            # 基础转录文本
            transcript = raw_result.get('text', '')
            
            # 时间段信息
            segments = []
            if 'sentences' in raw_result:
                for sentence in raw_result['sentences']:
                    segments.append({
                        'text': sentence.get('text', ''),
                        'start_time': sentence.get('begin_time', 0) / 1000,  # 转换为秒
                        'end_time': sentence.get('end_time', 0) / 1000,
                        'confidence': sentence.get('confidence', 1.0)
                    })
            
            # 说话人分离信息
            speakers = []
            if 'speaker_map' in raw_result:
                speakers = raw_result['speaker_map']
            
            return {
                "transcript": transcript,
                "segments": segments,
                "speakers": speakers,
                "language": raw_result.get('language', 'zh'),
                "duration": raw_result.get('duration', 0),
                "word_count": len(transcript.split()) if transcript else 0,
                "raw_result": raw_result
            }
            
        except Exception as e:
            logger.error(f"格式化转录结果失败: {str(e)}")
            return {
                "transcript": raw_result.get('text', ''),
                "segments": [],
                "speakers": [],
                "language": "zh",
                "duration": 0,
                "word_count": 0,
                "raw_result": raw_result
            }
    
    def get_supported_formats(self) -> Dict[str, List[str]]:
        """获取支持的文件格式"""
        return {
            "audio": [".wav", ".mp3", ".m4a", ".aac", ".flac"],
            "video": [".mp4", ".avi", ".mov", ".mkv", ".webm"],
            "sample_rates": ["8000", "16000", "22050", "44100", "48000"],
            "channels": ["1", "2"]
        }
    
    def estimate_cost(self, duration_seconds: float) -> Dict[str, Any]:
        """估算转录成本"""
        # 基于阿里云DashScope定价（示例价格，实际以官网为准）
        price_per_minute = 0.01  # 每分钟0.01元
        duration_minutes = duration_seconds / 60
        estimated_cost = duration_minutes * price_per_minute
        
        return {
            "duration_seconds": duration_seconds,
            "duration_minutes": round(duration_minutes, 2),
            "estimated_cost_cny": round(estimated_cost, 4),
            "currency": "CNY",
            "note": "价格仅供参考，实际以阿里云官网为准"
        }

    def get_vocabulary_content(self, vocabulary_id: str) -> Dict[str, Any]:
        """
        获取词汇表内容
        
        Args:
            vocabulary_id: 词汇表ID
            
        Returns:
            词汇表内容信息
        """
        if not self.is_available():
            return {
                "success": False,
                "error": "DashScope API不可用",
                "content": []
            }
        
        try:
            import dashscope
            from dashscope.audio.asr import VocabularyService
            
            logger.info(f"🔍 获取词汇表内容: {vocabulary_id}")
            
            # 根据官方文档，VocabularyService方法可能直接返回结果
            vocab_service = VocabularyService()
            result = vocab_service.query_vocabulary(vocabulary_id=vocabulary_id)
            
            # 检查result的类型和结构
            logger.debug(f"🔍 VocabularyService响应类型: {type(result)}")
            logger.debug(f"🔍 VocabularyService响应内容: {result}")
            
            # 如果result是字典，直接使用
            if isinstance(result, dict):
                # 假设返回格式类似官方文档中的output字段
                vocabulary_info = result.get("output", result)
                
                # 提取词汇表信息
                response_data = {
                    "success": True,
                    "vocabulary_id": vocabulary_id,
                    "name": vocabulary_info.get("target_model", ""),
                    "description": f"预设词汇表 {vocabulary_id}",
                    "status": vocabulary_info.get("status", "OK"),
                    "word_count": len(vocabulary_info.get("vocabulary", [])),
                    "content": vocabulary_info.get("vocabulary", []),
                    "created_time": vocabulary_info.get("gmt_create", ""),
                    "domain": vocabulary_info.get("domain", "")
                }
                
                logger.info(f"📋 词汇表信息获取成功: 词汇数量: {response_data['word_count']}")
                return response_data
                
            # 如果result有status_code属性（老格式）
            elif hasattr(result, 'status_code'):
                from http import HTTPStatus
                if result.status_code == HTTPStatus.OK:
                    vocabulary_info = result.output
                    response_data = {
                        "success": True,
                        "vocabulary_id": vocabulary_id,
                        "name": vocabulary_info.get("name", ""),
                        "description": vocabulary_info.get("description", ""),
                        "status": vocabulary_info.get("status", ""),
                        "word_count": vocabulary_info.get("word_count", 0),
                        "content": vocabulary_info.get("words", []),
                        "created_time": vocabulary_info.get("created_time", ""),
                        "domain": vocabulary_info.get("domain", "")
                    }
                    
                    logger.info(f"📋 词汇表信息获取成功: {response_data['name']}, 词汇数量: {response_data['word_count']}")
                    return response_data
                else:
                    error_msg = f"获取词汇表失败: {getattr(result, 'message', '未知错误')}"
                    logger.error(error_msg)
                    return {
                        "success": False,
                        "error": error_msg,
                        "content": []
                    }
            else:
                # 未知格式
                error_msg = f"未知的响应格式: {type(result)}"
                logger.error(error_msg)
                return {
                    "success": False,
                    "error": error_msg,
                    "content": []
                }
                
        except Exception as e:
            error_msg = f"查询词汇表异常: {str(e)}"
            logger.error(error_msg)
            return {
                "success": False,
                "error": error_msg,
                "content": []
            }

    def list_vocabularies(self) -> Dict[str, Any]:
        """
        列出所有可用的词汇表
        
        Returns:
            词汇表列表
        """
        if not self.is_available():
            return {
                "success": False,
                "error": "DashScope API不可用",
                "vocabularies": []
            }
        
        try:
            import dashscope
            from dashscope.audio.asr import VocabularyService
            from http import HTTPStatus
            
            logger.info("📋 获取词汇表列表...")
            
            # 获取词汇表列表
            vocab_service = VocabularyService()
            result = vocab_service.list_vocabularies()
            
            # 适配不同的返回格式
            if isinstance(result, dict):
                # 如果直接返回字典
                vocabularies = result.get("vocabularies", []) or result.get("output", {}).get("vocabularies", [])
                
                logger.info(f"📋 找到 {len(vocabularies)} 个词汇表")
                return {
                    "success": True,
                    "vocabularies": vocabularies,
                    "count": len(vocabularies)
                }
            elif hasattr(result, 'status_code'):
                # 如果有status_code属性（老格式）
                if result.status_code == HTTPStatus.OK:
                    vocabularies = result.output.get("vocabularies", [])
                    
                    logger.info(f"📋 找到 {len(vocabularies)} 个词汇表")
                    return {
                        "success": True,
                        "vocabularies": vocabularies,
                        "count": len(vocabularies)
                    }
                else:
                    error_msg = f"获取词汇表列表失败: {getattr(result, 'message', '未知错误')}"
                    logger.error(error_msg)
                    return {
                        "success": False,
                        "error": error_msg,
                        "vocabularies": []
                    }
            else:
                error_msg = f"未知的响应格式: {type(result)}"
                logger.error(error_msg)
                return {
                    "success": False,
                    "error": error_msg,
                    "vocabularies": []
                }
                
        except Exception as e:
            error_msg = f"查询词汇表列表异常: {str(e)}"
            logger.error(error_msg)
            return {
                "success": False,
                "error": error_msg,
                "vocabularies": []
            } 