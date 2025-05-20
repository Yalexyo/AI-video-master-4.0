#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
文本处理工具模块 - 提供文本处理和专业术语校正功能
"""

import re
import json
import logging
from typing import Dict, List, Optional, Tuple, Any, Union

# 设置日志
logger = logging.getLogger(__name__)

class TextProcessor:
    """文本处理工具类，提供文本处理和专业术语校正功能"""
    
    def __init__(self, custom_corrections: Optional[Dict[str, str]] = None):
        """
        初始化文本处理器
        
        Args:
            custom_corrections: 自定义的校正规则，默认为None
        """
        # 默认校正规则
        self.default_corrections = [
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
        
        # 添加自定义校正规则
        self.custom_corrections = custom_corrections or {}
        
        logger.info("初始化文本处理器")
    
    def correct_professional_terms(self, text: str) -> str:
        """
        校正文本中的专业术语
        
        Args:
            text: 需要校正的文本
            
        Returns:
            校正后的文本
        """
        # 空文本直接返回
        if not text:
            return text
        
        # 应用所有默认校正规则
        corrected_text = text
        for pattern, replacement in self.default_corrections:
            corrected_text = re.sub(pattern, replacement, corrected_text)
        
        # 应用自定义校正规则
        for pattern, replacement in self.custom_corrections.items():
            corrected_text = re.sub(pattern, replacement, corrected_text)
        
        return corrected_text
    
    def apply_corrections_to_json(self, json_data: Union[str, Dict], 
                                 output_file: Optional[str] = None) -> Tuple[Optional[Dict], bool]:
        """
        应用专业词汇校正到JSON数据
        
        Args:
            json_data: JSON数据（可以是字典或文件路径）
            output_file: 输出JSON文件路径，如果为None则只返回结果不写入文件
            
        Returns:
            修正后的JSON数据，及是否有修改
        """
        # 如果json_data是字符串，则尝试将其解释为文件路径
        if isinstance(json_data, str):
            try:
                with open(json_data, 'r', encoding='utf-8') as f:
                    data = json.load(f)
            except Exception as e:
                logger.error(f"无法加载JSON文件: {json_data}, 错误: {str(e)}")
                return None, False
        else:
            data = json_data
        
        # 应用专业词汇校正
        corrected = False
        
        # 检查transcripts字段
        if "transcripts" in data:
            for transcript in data["transcripts"]:
                # 校正整体文本
                if "text" in transcript:
                    original_text = transcript["text"]
                    transcript["text"] = self.correct_professional_terms(original_text)
                    if original_text != transcript["text"]:
                        corrected = True
                
                # 校正每个句子
                if "sentences" in transcript:
                    for sentence in transcript["sentences"]:
                        if "text" in sentence:
                            original_text = sentence["text"]
                            sentence["text"] = self.correct_professional_terms(original_text)
                            if original_text != sentence["text"]:
                                corrected = True
        
        # 检查是否有单独的sentences字段（适配不同API返回格式）
        if "sentences" in data:
            for sentence in data["sentences"]:
                if "text" in sentence:
                    original_text = sentence["text"]
                    sentence["text"] = self.correct_professional_terms(original_text)
                    if original_text != sentence["text"]:
                        corrected = True
        
        # 如果需要输出到文件
        if output_file and data:
            try:
                with open(output_file, 'w', encoding='utf-8') as f:
                    json.dump(data, f, ensure_ascii=False, indent=2)
                logger.info(f"已将校正后的数据保存到: {output_file}")
            except Exception as e:
                logger.error(f"保存JSON文件失败: {output_file}, 错误: {str(e)}")
        
        return data, corrected
    
    def extract_keywords(self, text: str, min_length: int = 2, 
                        max_keywords: int = 10) -> List[str]:
        """
        从文本中提取关键词
        
        Args:
            text: 输入文本
            min_length: 关键词最小长度，默认为2
            max_keywords: 返回的最大关键词数量，默认为10
            
        Returns:
            关键词列表
        """
        try:
            # 加载jieba分词模块（如果可用）
            import jieba
            import jieba.analyse
            
            # 使用jieba提取关键词（基于TF-IDF算法）
            keywords = jieba.analyse.extract_tags(text, topK=max_keywords)
            
            # 过滤掉太短的关键词
            keywords = [k for k in keywords if len(k) >= min_length]
            
            return keywords[:max_keywords]
            
        except ImportError:
            logger.warning("jieba模块未安装，无法使用关键词提取功能")
            
            # 简单的分词和频率统计（备选方案）
            words = re.findall(r'[\w\u4e00-\u9fa5]+', text)
            word_freq = {}
            
            for word in words:
                if len(word) >= min_length:
                    word_freq[word] = word_freq.get(word, 0) + 1
            
            # 按频率排序
            sorted_words = sorted(word_freq.items(), key=lambda x: x[1], reverse=True)
            return [word for word, _ in sorted_words[:max_keywords]]
    
    def format_transcript_to_srt(self, transcript_data: Dict[str, Any]) -> str:
        """
        将转录数据格式化为SRT字幕格式
        
        Args:
            transcript_data: 转录数据字典
            
        Returns:
            SRT格式的字幕文本
        """
        srt_content = []
        
        # 尝试从不同的数据结构中提取句子
        sentences = []
        
        if "sentences" in transcript_data:
            sentences = transcript_data["sentences"]
        elif "transcripts" in transcript_data and transcript_data["transcripts"]:
            # 如果有多个转录结果，使用第一个
            transcript = transcript_data["transcripts"][0]
            if "sentences" in transcript:
                sentences = transcript["sentences"]
        
        if not sentences:
            logger.warning("转录数据中未找到句子信息，无法生成SRT字幕")
            return ""
        
        # 遍历句子生成SRT条目
        for i, sentence in enumerate(sentences):
            # 检查是否有必要的时间信息
            if "start_time" not in sentence or "end_time" not in sentence:
                logger.warning(f"第{i+1}个句子缺少时间信息，跳过")
                continue
            
            # 序号
            srt_content.append(str(i + 1))
            
            # 时间戳
            start_time = self._format_time_to_srt(sentence["start_time"])
            end_time = self._format_time_to_srt(sentence["end_time"])
            srt_content.append(f"{start_time} --> {end_time}")
            
            # 文本内容
            text = sentence.get("text", "")
            srt_content.append(text)
            
            # 空行分隔
            srt_content.append("")
        
        return "\n".join(srt_content)
    
    def _format_time_to_srt(self, seconds: float) -> str:
        """
        将秒数格式化为SRT时间戳格式 (HH:MM:SS,mmm)
        
        Args:
            seconds: 秒数
            
        Returns:
            SRT格式的时间戳
        """
        hours = int(seconds // 3600)
        minutes = int((seconds % 3600) // 60)
        seconds_part = int(seconds % 60)
        milliseconds = int((seconds - int(seconds)) * 1000)
        
        return f"{hours:02d}:{minutes:02d}:{seconds_part:02d},{milliseconds:03d}" 