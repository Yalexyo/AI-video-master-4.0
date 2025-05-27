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
        format_result: bool = True
    ) -> Dict[str, Any]:
        """
        音频转录
        
        Args:
            audio_path: 音频文件路径
            hotwords: 热词列表，用于提高识别准确度
            professional_terms: 专业词汇列表
            language: 语言代码 (zh, en)
            format_result: 是否格式化结果
            
        Returns:
            转录结果字典
        """
        if not self.is_available():
            return {
                "success": False,
                "error": "DashScope API不可用",
                "transcript": "",
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
            from dashscope.audio.asr import Recognition
            
            # 准备参数
            recognition_params = {
                "model": "paraformer-realtime-v1",
                "format": "pcm",
                "sample_rate": 16000,
                "callback": None
            }
            
            # 添加热词
            if hotwords:
                recognition_params["vocabulary_id"] = self._create_vocabulary(hotwords)
            
            # 执行转录
            with open(audio_path, 'rb') as f:
                audio_data = f.read()
            
            try:
                result = Recognition.call(
                    audio_data,
                    **recognition_params
                )
                
                if result.status_code == 200:
                    # 处理转录结果
                    transcript_data = result.output
                    
                    # 应用专业词汇矫正
                    if professional_terms and transcript_data.get('text'):
                        transcript_data['text'] = self._apply_professional_correction(
                            transcript_data['text'], professional_terms
                        )
                    
                    # 格式化结果
                    if format_result:
                        formatted_result = self._format_transcript_result(transcript_data)
                        formatted_result["success"] = True
                        return formatted_result
                    else:
                        return {
                            "success": True,
                            "raw_result": transcript_data,
                            "transcript": transcript_data.get('text', ''),
                            "segments": []
                        }
                else:
                    return {
                        "success": False,
                        "error": f"转录失败: {result.message}",
                        "transcript": "",
                        "segments": []
                    }
                
            except Exception as api_error:
                # 处理网络连接、代理等错误
                error_msg = str(api_error)
                if "ProxyError" in error_msg or "Max retries exceeded" in error_msg:
                    return {
                        "success": False,
                        "error": f"网络连接失败，请检查网络设置和代理配置: {error_msg}",
                        "transcript": "",
                        "segments": []
                    }
                elif "HTTPSConnectionPool" in error_msg:
                    return {
                        "success": False,
                        "error": f"HTTPS连接失败，请检查网络连接: {error_msg}",
                        "transcript": "",
                        "segments": []
                    }
                else:
                    return {
                        "success": False,
                        "error": f"API调用异常: {error_msg}",
                        "transcript": "",
                        "segments": []
                    }
                
        except ImportError as e:
            logger.error(f"缺少必要的依赖库: {e}")
            return {
                "success": False,
                "error": f"缺少依赖库: {e}",
                "transcript": "",
                "segments": []
            }
        except Exception as e:
            logger.error(f"DashScope音频转录失败: {str(e)}")
            return {
                "success": False,
                "error": str(e),
                "transcript": "",
                "segments": []
            }
    
    def transcribe_video(
        self,
        video_path: str,
        hotwords: Optional[List[str]] = None,
        professional_terms: Optional[List[str]] = None,
        extract_audio_first: bool = True
    ) -> Dict[str, Any]:
        """
        视频转录（先提取音频再转录）
        
        Args:
            video_path: 视频文件路径
            hotwords: 热词列表
            professional_terms: 专业词汇列表
            extract_audio_first: 是否先提取音频
            
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
                audio_path, hotwords, professional_terms
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
            from dashscope.audio.asr import Vocabulary
            
            result = Vocabulary.create(
                name=vocab_name,
                domain=domain,
                words=terms
            )
            
            if result.status_code == 200:
                vocab_id = result.output.get('vocabulary_id')
                logger.info(f"自定义词汇表创建成功: {vocab_id}")
                return vocab_id
            else:
                logger.error(f"词汇表创建失败: {result.message}")
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