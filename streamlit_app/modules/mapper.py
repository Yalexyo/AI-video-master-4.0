"""
视频片段映射模块 - 纯AI分类版本
使用DeepSeek AI进行智能分类，移除所有关键词匹配机制
"""

import logging
import json
import os
import glob
import subprocess
from typing import Dict, List, Optional, Any
from pathlib import Path
import streamlit as st

from modules.selection_logger import get_selection_logger
from utils.path_utils import get_project_root
from modules.ai_analyzers import DeepSeekAnalyzer

logger = logging.getLogger(__name__)

def resolve_video_pool_path(relative_path: str = "data/output/google_video/video_pool") -> str:
    """解析video_pool的绝对路径"""
    try:
        project_root = get_project_root()
        resolved_path = os.path.join(project_root, relative_path)
        return resolved_path
    except Exception as e:
        logger.warning(f"解析路径失败，使用原路径: {e}")
        return relative_path

class VideoSegmentMapper:
    """🎯 视频片段映射器，使用DeepSeek AI进行智能分类"""
    
    def __init__(self):
        """初始化映射器"""
        self.four_modules = ["痛点", "解决方案导入", "卖点·成分&配方", "促销机制"]
        
        # 初始化DeepSeek分析器
        try:
            self.deepseek_analyzer = DeepSeekAnalyzer()
            logger.info("DeepSeek分析器初始化完成")
        except Exception as e:
            logger.error(f"DeepSeek分析器初始化失败: {e}")
            self.deepseek_analyzer = None
    
    def get_video_duration_ffprobe(self, file_path: str) -> float:
        """🎯 使用ffprobe获取视频时长"""
        try:
            cmd = ['ffprobe', '-v', 'quiet', '-print_format', 'json', '-show_format', file_path]
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=10, check=True)
            data = json.loads(result.stdout)
            return float(data['format']['duration'])
        except Exception as e:
            logger.error(f"获取视频时长失败: {str(e)}")
            return 0.0
    
    def classify_segment_by_deepseek_ai(self, all_tags: List[str], segment_info: Optional[Dict[str, Any]] = None) -> str:
        """🎯 使用DeepSeek AI进行视频片段智能分类"""
        if not self.deepseek_analyzer or not self.deepseek_analyzer.is_available():
            logger.warning("DeepSeek分析器不可用")
            return "其他"
        
        if not all_tags:
            return "其他"
        
        tags_text = " ".join(all_tags)
        logger.info(f"🎯 使用DeepSeek AI智能分类: {tags_text}")
        
        try:
            system_prompt = self._build_ai_classification_prompt()
            
            # 准备用户输入内容
            user_content_parts = [f"视频片段标签: {', '.join(all_tags)}"]
            
            if segment_info:
                transcription = segment_info.get('transcription')
                if transcription and transcription.strip():
                    user_content_parts.append(f"语音转录内容: {transcription.strip()}")
                
                duration = segment_info.get('duration')
                if duration:
                    user_content_parts.append(f"片段时长: {duration:.1f}秒")
            
            user_content = "\n".join(user_content_parts)
            user_content += "\n\n请根据以上信息进行模块分类，只回答模块名称。"
            
            response = self.deepseek_analyzer._chat_completion([
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_content}
            ])
            
            if response and "choices" in response and len(response["choices"]) > 0:
                content = response["choices"][0]["message"]["content"].strip()
                cleaned_result = self._extract_module_from_ai_response(content)
                
                if cleaned_result in self.four_modules:
                    logger.info(f"✅ DeepSeek AI分类成功: {tags_text} -> {cleaned_result}")
                    return cleaned_result
                else:
                    logger.warning(f"⚠️ DeepSeek返回无效分类: {content}")
                    return "其他"
            else:
                logger.warning("⚠️ DeepSeek API响应无效")
                return "其他"
                
        except Exception as e:
            logger.error(f"❌ DeepSeek AI分类失败: {e}")
            return "其他"
    
    def _build_ai_classification_prompt(self) -> str:
        """构建AI分类提示词"""
        return """🎯 你是专业的母婴视频内容分析专家，请根据视频标签将内容分类到以下四个业务模块之一：

## 🎯 痛点
- **核心特征**: 识别宝宝或妈妈遇到的问题、困扰、不适状况
- **典型标签**: 哭闹、生病、不适、焦虑、便秘、腹泻、过敏、吐奶、拒食、睡眠困难
- **情绪特征**: 负面情绪占主导，如悲伤、生气、焦虑
- **场景特征**: 医院、诊所、问题处理场景
- **识别重点**: 强调问题存在，体现需求痛点

## 🎯 解决方案导入
- **核心特征**: 展示具体的解决方案、操作过程、使用方法
- **典型标签**: 冲奶、喂养、奶瓶、准备、操作、使用、手机、学习
- **情绪特征**: 中性或轻微正面，专注于过程
- **场景特征**: 厨房、操作台、学习环境、实操场景
- **识别重点**: 强调行动和解决过程，展示如何解决问题

## 🎯 卖点·成分&配方
- **核心特征**: 突出产品特点、营养成分、科学配方、专业优势
- **典型标签**: A2奶源、DHA、HMO、成分、配方、营养、科技、专利、专业、权威
- **情绪特征**: 专业、科学、信赖感
- **场景特征**: 实验室、专业背景、产品展示、科研环境
- **识别重点**: 强调产品优势和科学价值，体现专业性

## 🎯 促销机制
- **核心特征**: 展示产品效果、宝宝健康成长、推广激励
- **典型标签**: 开心、健康、活力、快乐成长、推荐、优惠、活动、笑容、茁壮成长
- **情绪特征**: 积极正面，充满活力
- **场景特征**: 户外、游乐场、阳光、温馨家庭、快乐时光
- **识别重点**: 强调使用效果和推广价值，激发购买欲望

⚠️ **重要说明**:
- 只回答四个模块名称之一：痛点、解决方案导入、卖点·成分&配方、促销机制
- 如果无法确定，回答'其他'
- 不要提供解释，只要模块名称
- 优先考虑标签的主要倾向和整体语义"""
    
    def _extract_module_from_ai_response(self, ai_response: str) -> str:
        """从AI响应中提取模块名称"""
        if not ai_response:
            return "其他"
        
        cleaned = ai_response.strip()
        
        # 直接匹配模块名称
        for module in self.four_modules:
            if module in cleaned:
                return module
        
        # 匹配简写
        mapping = {
            "痛点": "痛点",
            "解决方案": "解决方案导入",
            "卖点": "卖点·成分&配方", 
            "促销": "促销机制"
        }
        
        for key, value in mapping.items():
            if key in cleaned:
                return value
        
        return "其他"
    
    def classify_segment(self, all_tags: List[str], segment_info: Optional[Dict[str, Any]] = None) -> str:
        """🎯 对片段进行AI分类"""
        selection_logger = get_selection_logger()
        
        # 使用DeepSeek AI进行分类
        category = self.classify_segment_by_deepseek_ai(all_tags, segment_info)
        
        log_reason = "AI分类成功" if category != "其他" else "AI分类无法确定类别"
        
        selection_logger.log_step(
            step_type="ai_classification",
            input_tags=all_tags,
            result=category
        )
        
        selection_logger.log_final_result(
            final_category=category,
            reason=log_reason,
            segment_info=segment_info
        )
        
        return category
    
    def scan_video_pool(self, video_pool_path: str = "data/output/google_video/video_pool") -> List[Dict[str, Any]]:
        """🎯 使用AI分类扫描video_pool目录中的所有JSON文件"""
        mapped_segments = []
        seen_segment_ids = set()
        
        resolved_path = resolve_video_pool_path(video_pool_path)
        logger.info(f"🎯 使用AI智能分类扫描: {resolved_path}")
        
        if not os.path.exists(resolved_path):
            logger.error(f"video_pool目录不存在: {resolved_path}")
            return mapped_segments
        
        json_files = glob.glob(os.path.join(resolved_path, "*.json"))
        logger.info(f"找到 {len(json_files)} 个JSON文件")
        
        for file_idx, json_file in enumerate(json_files):
            try:
                logger.info(f"处理文件 {file_idx + 1}/{len(json_files)}: {os.path.basename(json_file)}")
                
                with open(json_file, 'r', encoding='utf-8') as f:
                    video_data = json.load(f)
                
                video_id = video_data.get('video_id', 'unknown')
                segments = video_data.get('segments', [])
                
                for seg_idx, segment in enumerate(segments):
                    try:
                        # 提取基本信息
                        file_path = segment.get('file_path', '')
                        all_tags = segment.get('all_tags', [])
                        quality_score = segment.get('quality_score', 0.9)
                        confidence = segment.get('confidence', 0.8)
                        file_name = segment.get('file_name', '')
                        analysis_method = segment.get('analysis_method', 'visual')
                        transcription = segment.get('transcription', None)
                        
                        # 兼容旧格式
                        if not all_tags:
                            raw_fields = [
                                segment.get('object', ''),
                                segment.get('scene', ''),
                                segment.get('emotion', ''),
                                segment.get('brand_elements', '')
                            ]
                            
                            all_tags = []
                            for raw_field in raw_fields:
                                if raw_field:
                                    if ',' in raw_field:
                                        tags = raw_field.split(',')
                                    else:
                                        tags = [raw_field]
                                
                                    for tag in tags:
                                        clean_tag = tag.strip()
                                        if clean_tag and clean_tag not in all_tags:
                                            all_tags.append(clean_tag)
                            
                        if not all_tags:
                            continue
                        
                        # 跳过人脸特写和不可用片段
                        if segment.get('is_face_close_up', False) or segment.get('unusable', False):
                            continue
                        
                        # 获取视频时长
                        duration = 0
                        if file_path and os.path.exists(file_path):
                                duration = self.get_video_duration_ffprobe(file_path)
                        
                        # 时长过滤
                        if duration > 10:
                            continue
                        
                        # 构建片段信息
                        segment_info_for_classification = {
                            "file_name": file_name,
                            "duration": duration,
                            "all_tags": all_tags,
                            "transcription": transcription,
                            "analysis_method": analysis_method
                        }
                        
                        # AI分类
                        category = self.classify_segment(all_tags, segment_info_for_classification)
                        
                        # 去重检查
                        unique_id = f"{video_id}::{file_name}"
                        if unique_id in seen_segment_ids:
                            continue
                        
                        # 构建映射结果
                        mapped_segment = {
                            "segment_id": f"{video_id}_{file_name}",
                            "file_path": file_path,
                            "category": category,
                            "all_tags": all_tags,
                            "quality_score": quality_score,
                            "confidence": confidence,
                            "duration": duration,
                            "transcription": transcription,
                            "analysis_method": analysis_method
                        }
                        
                        mapped_segments.append(mapped_segment)
                        seen_segment_ids.add(unique_id)
                        
                    except Exception as e:
                        logger.error(f"处理片段失败: {str(e)}")
                        continue
                        
            except Exception as e:
                logger.error(f"处理文件失败: {str(e)}")
                continue
        
        return mapped_segments
    
    def get_mapping_statistics(self, mapped_segments: List[Dict[str, Any]]) -> Dict[str, Any]:
        """获取映射统计信息"""
        stats = {
            "total_segments": len(mapped_segments),
            "by_category": {},
            "by_video": {},
            "quality_stats": {"avg_quality": 0, "avg_confidence": 0, "avg_duration": 0, "total_duration": 0}
        }
        
        if not mapped_segments:
            return stats
        
        # 按类别统计
        for module in self.four_modules + ["其他"]:
            module_segments = [s for s in mapped_segments if s["category"] == module]
            stats["by_category"][module] = {
                "count": len(module_segments),
                "total_duration": sum(s["duration"] for s in module_segments),
                "avg_quality": sum(s["combined_quality"] for s in module_segments) / len(module_segments) if module_segments else 0
            }
        
        # 按视频统计
        video_counts = {}
        for segment in mapped_segments:
            video_id = segment["video_id"]
            if video_id not in video_counts:
                video_counts[video_id] = 0
            video_counts[video_id] += 1
        stats["by_video"] = video_counts
        
        # 质量统计
        if mapped_segments:
            stats["quality_stats"] = {
                "avg_quality": sum(s["combined_quality"] for s in mapped_segments) / len(mapped_segments),
                "avg_confidence": sum(s["confidence"] for s in mapped_segments) / len(mapped_segments),
                "avg_duration": sum(s["duration"] for s in mapped_segments) / len(mapped_segments),
                "total_duration": sum(s["duration"] for s in mapped_segments)
            }
        
        return stats

# 缓存的映射函数
@st.cache_data(ttl=3600, show_spinner=False)
def get_cached_mapping_results(video_pool_path: str) -> tuple:
    """缓存的映射结果获取函数"""
    mapper = VideoSegmentMapper()
    mapped_segments = mapper.scan_video_pool(video_pool_path)
    statistics = mapper.get_mapping_statistics(mapped_segments)
    return mapped_segments, statistics 