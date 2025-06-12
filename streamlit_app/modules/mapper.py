"""
视频片段映射模块
用于将video_pool中的视频片段自动映射到四大模块：痛点、解决方案导入、卖点·成分&配方、促销机制
"""

import logging
import json
import os
import re
import glob
import subprocess
from typing import Dict, List, Optional, Any, Tuple
from pathlib import Path
import threading
import time
import streamlit as st

from modules.selection_logger import get_selection_logger
# from .quality_analyzer import QualityAnalyzer  # 暂时注释掉，文件不存在
# from .ai_analyzers.analyzer_factory import AnalyzerFactory  # 暂时注释掉，文件不存在
# from .data_models import Segment, MappedSegment, VideoAnalysisResult, SceneInfo  # 暂时注释掉，文件不存在
from utils.config_manager import get_config_manager
from utils.path_utils import get_project_root
from modules.ai_analyzers import DeepSeekAnalyzer

logger = logging.getLogger(__name__)

def resolve_video_pool_path(relative_path: str = "data/output/google_video/video_pool") -> str:
    """
    🔧 跨平台兼容的video_pool路径解析
    
    解决streamlit_app工作目录下相对路径找不到../data的问题
    
    Args:
        relative_path: 相对路径，默认为data/output/google_video/video_pool
        
    Returns:
        str: 解析后的绝对路径
    """
    # 方案1：尝试当前工作目录下的相对路径
    if os.path.exists(relative_path):
        abs_path = os.path.abspath(relative_path)
        logger.debug(f"✅ 路径解析成功(当前目录): {relative_path} -> {abs_path}")
        return abs_path
    
    # 方案2：尝试上级目录下的相对路径（适用于streamlit_app工作目录）
    parent_relative_path = os.path.join("..", relative_path)
    if os.path.exists(parent_relative_path):
        abs_path = os.path.abspath(parent_relative_path)
        logger.debug(f"✅ 路径解析成功(上级目录): {parent_relative_path} -> {abs_path}")
        return abs_path
    
    # 方案3：使用项目根目录拼接
    try:
        project_root = get_project_root()
        project_based_path = os.path.join(project_root, relative_path)
        if os.path.exists(project_based_path):
            logger.debug(f"✅ 路径解析成功(项目根目录): {project_based_path}")
            return project_based_path
    except Exception as e:
        logger.debug(f"项目根目录方法失败: {e}")
    
    # 方案4：基于当前文件位置推断
    current_file_dir = os.path.dirname(os.path.abspath(__file__))
    # 当前文件在 streamlit_app/modules/mapper.py
    # 需要跳到项目根目录: ../../data/output/google_video/video_pool
    inferred_path = os.path.join(current_file_dir, "..", "..", relative_path)
    if os.path.exists(inferred_path):
        abs_path = os.path.abspath(inferred_path)
        logger.debug(f"✅ 路径解析成功(推断路径): {inferred_path} -> {abs_path}")
        return abs_path
    
    # 所有方案都失败，返回原始路径并记录警告
    logger.warning(f"⚠️ 无法解析video_pool路径，所有尝试的路径都不存在:")
    logger.warning(f"   1. {os.path.abspath(relative_path)}")
    logger.warning(f"   2. {os.path.abspath(parent_relative_path)}")
    if 'project_based_path' in locals():
        logger.warning(f"   3. {project_based_path}")
    logger.warning(f"   4. {os.path.abspath(inferred_path)}")
    logger.warning(f"   当前工作目录: {os.getcwd()}")
    
    return os.path.abspath(relative_path)  # 返回绝对路径，即使不存在

class VideoSegmentMapper:
    """
    视频片段映射器，负责将AI分析的标签映射到业务模块。
    """
    
    def __init__(self):
        """初始化映射器"""
        self.four_modules = ["痛点", "解决方案导入", "卖点·成分&配方", "促销机制"]
        
        # 🔧 初始化DeepSeek分析器
        try:
            self.deepseek_analyzer = DeepSeekAnalyzer()
            logger.info("DeepSeek分析器初始化完成")
        except ImportError as e:
            logger.warning(f"无法导入DeepSeek分析器: {e}")
            self.deepseek_analyzer = None
        except Exception as e:
            logger.error(f"DeepSeek分析器初始化失败: {e}")
            self.deepseek_analyzer = None
        
        # 🔧 使用统一配置中心加载规则
        try:
            config_manager = get_config_manager()
            self.keyword_rules = config_manager.get_matching_rules()
            
            # 从原始配置中提取痛点规则和品牌关键词用于特殊处理（如果需要的话）
            # 注意：大部分逻辑应直接使用 get_matching_rules() 的结果
            raw_config = config_manager.get_raw_config()
            self.pain_point_rules = raw_config.get("pain_points", {}) # 示例，可能不再需要
            self.brand_priority_keywords = raw_config.get("features_formula", {}).get("brands", [])

            logger.info("🎯 映射器配置加载成功，使用统一配置中心")
            logger.info(f"   模块数量: {len(self.keyword_rules)}")
            
        except Exception as e:
            logger.error(f"无法从配置中心加载规则，将使用默认兜底配置: {e}")
            # 兜底配置
            self.keyword_rules = {
                "痛点": {"core_identity": ["医院", "哭闹", "发烧"]},
                "解决方案导入": {"core_identity": ["冲奶", "奶粉罐", "奶瓶"]},
                "卖点·成分&配方": {"core_identity": ["A2", "HMO", "DHA", "启赋"]},
                "促销机制": {"core_identity": ["优惠", "限时", "促销"]}
            }
            self.pain_point_rules = {}
            self.brand_priority_keywords = ["启赋", "illuma", "Wyeth", "A2", "ATWO", "HMO", "DHA"]
        
        # 🔧 Intentionally disable embedding models
        logger.info("EMBEDDING MODELS ARE DISABLED. Classification will rely on keywords and DeepSeek API.")
        self.embedding_model = None
        self.embedding_util = None
    
        # 🔧 【已彻底移除】不再需要手动加载matching_rules.json，完全依赖ConfigManager
        # 确保rules属性存在，用于向后兼容性
        if not hasattr(self, 'keyword_rules') or not self.keyword_rules:
            logger.error("ConfigManager未能提供任何规则，将使用一个空的默认配置。")
            self.keyword_rules = self._create_default_rules()
        
        # 为向后兼容，同时设置rules属性
        self.rules = self.keyword_rules
                
    def _load_matching_rules(self):
        """
        【已废弃】此方法不再使用。所有规则均由ConfigManager统一提供。
        """
        logger.warning("调用了已废弃的_load_matching_rules方法，此方法不应再被使用。")
        self.rules = self._create_default_rules()
    
    def _create_default_rules(self) -> dict:
        """
        创建默认的规则配置（作为fallback）
        
        Returns:
            默认配置字典
        """
        return {
            "痛点": {
                "object_keywords": ["宝宝", "婴儿", "新生儿"],
                "scene_keywords": ["哭闹", "不安", "难受"],
                "emotion_keywords": ["焦虑", "担心", "困扰"],
                "negative_keywords": ["开心", "快乐", "满意"],
                "required_keywords": [],
                "min_score_threshold": 0.3
            },
            "卖点·成分&配方": {
                "object_keywords": ["奶粉", "配方", "营养"],
                "scene_keywords": ["产品", "展示", "介绍"],
                "emotion_keywords": ["专业", "科学", "安全"],
                "negative_keywords": ["哭闹", "问题", "难受"],
                "required_keywords": [],
                "min_score_threshold": 0.3
            },
            "解决方案导入": {
                "object_keywords": ["建议", "方法", "解决"],
                "scene_keywords": ["指导", "教学", "演示"],
                "emotion_keywords": ["专业", "信任", "安心"],
                "negative_keywords": ["产品", "推销", "广告"],
                "required_keywords": [],
                "min_score_threshold": 0.3
            },
            "促销机制": {
                "object_keywords": ["宝宝", "婴儿", "孩子"],
                "scene_keywords": ["开心", "活力", "健康"],
                "emotion_keywords": ["快乐", "满意", "成长"],
                "negative_keywords": ["哭闹", "问题", "担心"],
                "required_keywords": [],
                "min_score_threshold": 0.3
            },
            "GLOBAL_SETTINGS": {
                "global_exclusion_keywords": ["疑似", "模糊", "不清楚"],
                "irrelevant_scene_categories": {
                    "无关场景": ["广告", "logo", "文字"]
                }
            }
        }
    
    def _init_embedding_model_offline(self):
        """离线模式下初始化embedding模型（增强版）"""
        try:
            import os
            import torch
            from pathlib import Path
            
            # 检查离线配置文件
            offline_config_path = Path("config/offline_config.py")
            if not offline_config_path.exists():
                logger.debug("离线配置文件不存在，跳过离线模式")
                return False
            
            # 检查主模型路径
            primary_model_path = Path("models/sentence_transformers/all-MiniLM-L6-v2")
            fallback_model_path = Path("models/sentence_transformers/paraphrase-multilingual-MiniLM-L12-v2")
            
            if not primary_model_path.exists():
                logger.debug(f"主模型不存在: {primary_model_path}")
                return False
            
            # 🔧 增强：多层次模型加载策略
            from sentence_transformers import SentenceTransformer, util
            
            # 策略1：尝试无设备指定加载
            try:
                logger.debug("尝试策略1：无设备指定加载")
                self.embedding_model = SentenceTransformer(str(primary_model_path))
                self.embedding_util = util
                logger.info(f"✅ 策略1成功：无设备指定加载: {primary_model_path}")
                return True
                
            except Exception as e1:
                logger.debug(f"策略1失败: {e1}")
                
                # 策略2：显式指定CPU设备
                try:
                    logger.debug("尝试策略2：显式CPU设备加载")
                    self.embedding_model = SentenceTransformer(str(primary_model_path), device='cpu')
                    self.embedding_util = util
                    logger.info(f"✅ 策略2成功：CPU设备加载: {primary_model_path}")
                    return True
                    
                except Exception as e2:
                    logger.debug(f"策略2失败: {e2}")
                    
                    # 策略3：尝试手动配置torch
                    try:
                        logger.debug("尝试策略3：手动配置torch设备")
                        
                        # 临时禁用MPS
                        original_mps_available = None
                        if hasattr(torch.backends, 'mps'):
                            original_mps_available = torch.backends.mps.is_available
                            torch.backends.mps.is_available = lambda: False
                        
                        self.embedding_model = SentenceTransformer(str(primary_model_path))
                        self.embedding_util = util
                        
                        # 恢复MPS设置
                        if original_mps_available is not None:
                            torch.backends.mps.is_available = original_mps_available
                        
                        logger.info(f"✅ 策略3成功：手动配置torch: {primary_model_path}")
                        return True
                        
                    except Exception as e3:
                        logger.debug(f"策略3失败: {e3}")
                        
                        # 策略4：尝试从不同路径加载
                        try:
                            logger.debug("尝试策略4：绝对路径加载")
                            abs_path = primary_model_path.resolve()
                            self.embedding_model = SentenceTransformer(str(abs_path), device='cpu')
                            self.embedding_util = util
                            logger.info(f"✅ 策略4成功：绝对路径加载: {abs_path}")
                            return True
                            
                        except Exception as e4:
                            logger.debug(f"策略4失败: {e4}")
                            e5 = None  # Initialize e5 here
                            
                            # 策略5：尝试fallback模型
                            if fallback_model_path.exists():
                                try:
                                    logger.debug("尝试策略5：fallback模型")
                                    self.embedding_model = SentenceTransformer(str(fallback_model_path), device='cpu')
                                    self.embedding_util = util
                                    logger.info(f"✅ 策略5成功：fallback模型: {fallback_model_path}")
                                    return True
                                    
                                except Exception as err_fallback: # Changed variable name for clarity in assignment
                                    logger.debug(f"策略5失败: {err_fallback}")
                                    e5 = err_fallback # Assign the actual error to e5
                                    
                            # 所有策略都失败
                            logger.error(f"❌ 所有离线加载策略都失败:")
                            logger.error(f"  策略1 (无设备): {e1}")
                            logger.error(f"  策略2 (CPU): {e2}")
                            logger.error(f"  策略3 (禁用MPS): {e3}")
                            logger.error(f"  策略4 (绝对路径): {e4}")
                            if fallback_model_path.exists():
                                logger.error(f"  策略5 (fallback): {e5}") # Now e5 will be defined (or None)
                            
                            return False
            
        except ImportError as e:
            logger.warning(f"离线模式：sentence_transformers未安装: {e}")
            return False
        except Exception as e:
            logger.error(f"❌ 离线模式初始化失败: {e}")
            return False
    
    def get_video_duration_ffprobe(self, file_path: str) -> float:
        """
        使用ffprobe获取视频时长
        
        Args:
            file_path: 视频文件路径
            
        Returns:
            float: 视频时长（秒），失败返回0
        """
        try:
            cmd = [
                'ffprobe', '-v', 'quiet', '-print_format', 'json',
                '-show_format', file_path
            ]
            # 🔧 减少超时时间，避免长时间阻塞
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=10)
            
            if result.returncode == 0:
                data = json.loads(result.stdout)
                duration = float(data['format']['duration'])
                logger.debug(f"成功获取视频时长: {file_path} -> {duration}秒")
                return duration
            else:
                logger.warning(f"ffprobe命令执行失败: {file_path}, 错误: {result.stderr}")
                return 0
                
        except subprocess.TimeoutExpired:
            logger.error(f"ffprobe超时(10秒): {file_path}")
            return 0
        except json.JSONDecodeError as e:
            logger.error(f"ffprobe输出JSON解析失败: {file_path}, 错误: {e}")
            return 0
        except Exception as e:
            logger.error(f"ffprobe读取失败: {file_path}, 错误: {e}")
            return 0
    
    def classify_segment_by_tags(self, all_tags: List[str]) -> str:
        """
        使用权重累加机制，根据ai_batch配置对片段进行分类，归属得分最高的模块（严格排除负向关键词）。
        增加全局排除逻辑。
        """
        # 🔧 过滤None值，确保类型安全
        all_tags = [tag for tag in all_tags if tag is not None and isinstance(tag, str)]
        
        # 0. 全局排除检查 (最高优先级)
        config_manager = get_config_manager()
        global_exclusion_keywords = config_manager.get_global_exclusion_keywords()
        if global_exclusion_keywords:
            # 将所有标签和关键词转为小写以进行不区分大小写的比较
            lower_all_tags = {tag.lower() for tag in all_tags if tag}  # 额外过滤空字符串
            lower_global_exclusion_keywords = {kw.lower() for kw in global_exclusion_keywords if kw}
            
            # 查找交集
            intersection = lower_all_tags.intersection(lower_global_exclusion_keywords)
            if intersection:
                logger.info(f"🚫 片段因包含全局排除关键词被过滤: {intersection}")
                return None # 直接返回None，不进行任何分类

        # 1. 加载原始配置，获取各模块ai_batch权重词表
        try:
            raw_config = config_manager.get_raw_config()
        except Exception as e:
            logger.error(f"无法加载配置，使用原有逻辑: {e}")
            return None
            
        modules = [
            ("pain_points", "痛点"),
            ("solutions", "解决方案导入"),
            ("features_formula", "卖点·成分&配方"),
            ("promotions", "促销机制")
        ]
        tag_text = " ".join(all_tags).lower()
        module_scores = {}
        excluded_modules = set()

        # 2. 先执行全局排除（负向关键词）- 支持模块级和全局级排除
        global_overrides = raw_config.get("global_settings", {}).get("overrides", {})
        for key, module_name in modules:
            # 检查全局overrides排除
            negatives_key = f"{key}_negatives"
            negatives = global_overrides.get(negatives_key, [])
            for neg in negatives:
                if neg and isinstance(neg, str) and neg.lower() in tag_text:
                    excluded_modules.add(module_name)
                    logger.debug(f"模块 {module_name} 被全局排除词 '{neg}' 排除")
                    break
            
            # 🆕 检查模块级 negative_keywords
            if module_name not in excluded_modules:
                module_data = raw_config.get(key, {})
                module_negatives = module_data.get("negative_keywords", [])
                for neg in module_negatives:
                    if isinstance(neg, str) and neg.lower() in tag_text:
                        excluded_modules.add(module_name)
                        logger.debug(f"模块 {module_name} 被模块级排除词 '{neg}' 排除")
                        break

        # 3. 遍历每个模块，累加权重分
        for key, module_name in modules:
            if module_name in excluded_modules:
                continue
            module_data = raw_config.get(key, {})
            ai_batch = module_data.get("ai_batch", {})
            score = 0
            for cat in ["object", "scene", "emotion", "brand"]:
                words = ai_batch.get(cat, [])
                for item in words:
                    if isinstance(item, dict):
                        word = item.get("word", "")
                        weight = item.get("weight", 1)
                    else:
                        word = str(item)
                        weight = 1
                    if word and word.lower() in tag_text:
                        score += weight
            if score > 0:
                module_scores[module_name] = score

        if not module_scores:
            return None
        # 4. 得分最高的模块归属
        best_module = max(module_scores, key=module_scores.get)
        logger.info(f"权重打分归属: {' '.join(all_tags)} -> {best_module} (分数: {module_scores[best_module]})")
        
        # 🆕 输出排除日志以便调试
        if excluded_modules:
            logger.debug(f"被排除的模块: {list(excluded_modules)}")
        
        return best_module
    
    def _is_pain_point_by_combination(self, all_tags: List[str]) -> bool:
        """
        通过组合判断是否为痛点场景
        必须同时满足：宝宝/婴儿在场 + 负面情绪/哭闹
        
        Args:
            all_tags: 片段的所有标签列表
            
        Returns:
            bool: 是否为痛点场景
        """
        if not all_tags:
            return False
        
        # 🔧 过滤None值，确保类型安全
        all_tags = [tag for tag in all_tags if tag is not None and isinstance(tag, str)]
        
        tags_text = " ".join(all_tags).lower()
        
        # 检查是否有宝宝在场
        has_baby = False
        for baby_keyword in self.pain_point_rules.get("baby_prescene", []):
            if baby_keyword and isinstance(baby_keyword, str) and baby_keyword.lower() in tags_text:
                has_baby = True
                logger.debug(f"痛点检测: 发现宝宝关键词 '{baby_keyword.lower()}'")
                break
        
        # 检查是否有负面情绪
        has_negative_emotion = False
        matched_emotion = None
        for emotion_keyword in self.pain_point_rules.get("negative_emotions", []):
            if emotion_keyword and isinstance(emotion_keyword, str) and emotion_keyword.lower() in tags_text:
                has_negative_emotion = True
                matched_emotion = emotion_keyword.lower()
                logger.debug(f"痛点检测: 发现负面情绪关键词 '{emotion_keyword.lower()}'")
                break
        
        # 只有同时满足两个条件才判定为痛点
        is_pain_point = has_baby and has_negative_emotion
        
        if is_pain_point:
            logger.info(f"痛点检测: ✅ 同时满足宝宝在场和负面情绪，判定为痛点场景")
            logger.info(f"    宝宝在场: {has_baby}")
            logger.info(f"    负面情绪: {has_negative_emotion} (匹配词: {matched_emotion})")
        else:
            logger.debug(f"痛点检测: ❌ 不满足痛点条件")
            logger.debug(f"    宝宝在场: {has_baby}")
            logger.debug(f"    负面情绪: {has_negative_emotion}")
        
        return is_pain_point
    
    def _check_duration_limit(self, segment_info: Optional[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
        """
        检查片段时长是否超过限制
        
        Args:
            segment_info: 片段信息字典
            
        Returns:
            Dict: 如果超过限制则返回排除信息，否则返回None
        """
        try:
            if not segment_info or not isinstance(segment_info, dict):
                return None
            
            # 获取片段时长
            duration = segment_info.get('duration', 0)
            if not duration:
                return None
            
            # 获取配置中的最大时长限制
            max_duration = 10  # 默认10秒
            
            if hasattr(self, 'rules') and self.rules:
                global_settings = self.rules.get("GLOBAL_SETTINGS", {})
                if isinstance(global_settings, dict):
                    max_duration = global_settings.get("max_duration_seconds", 10)
            
            # 检查是否超过限制
            if duration > max_duration:
                segment_name = segment_info.get("file_name", "unknown")
                reason = f"时长{duration:.1f}s超过限制{max_duration}s"
                
                logger.info(f"🕒 时长过滤: {segment_name} ({reason})")
                
                return {
                    "is_excluded": True,
                    "reason": reason,
                    "duration": duration,
                    "max_duration": max_duration
                }
            
            return None
            
        except Exception as e:
            logger.warning(f"时长检查失败: {e}")
            return None
    
    def _detailed_exclusion_check(self, tags_text: str) -> Dict[str, Any]:
        """
        详细的排除关键词检查，返回完整的检查结果
        
        Args:
            tags_text: 标签文本
            
        Returns:
            Dict: 包含是否排除和具体原因的详细结果
        """
        result = {
            "is_excluded": False,
            "exclusion_reasons": [],
            "matched_keywords": {}
        }
        
        try:
            # 🔧 使用ConfigManager替代直接读取matching_rules.json
            from utils.config_manager import get_config_manager
            config_manager = get_config_manager()
            matching_rules = config_manager.get_matching_rules()
            
            if not isinstance(matching_rules, dict):
                logger.warning(f"配置规则类型错误: {type(matching_rules).__name__}")
                return result
            
            # 检查模块级别的排除关键词
            for module, rules in matching_rules.items():
                if not isinstance(rules, dict):
                    logger.debug(f"跳过模块 {module}，数据类型错误: {type(rules).__name__}")
                    continue
                
                negative_keywords = rules.get("negative_keywords", [])
                
                if not isinstance(negative_keywords, list):
                    logger.warning(f"模块 {module} negative_keywords类型错误: {type(negative_keywords).__name__}")
                    continue
                    
                module_matches = []
                
                for neg_kw in negative_keywords:
                    if isinstance(neg_kw, str) and neg_kw.lower() in tags_text.lower():
                        module_matches.append(neg_kw)
                
                if module_matches:
                    result["is_excluded"] = True
                    result["exclusion_reasons"].append(f"{module}模块排除: {module_matches}")
                    result["matched_keywords"][module] = module_matches
        
        except Exception as e:
            logger.error(f"排除关键词检查失败: {e}")
        
        return result
    
    def _get_keyword_matches(self, all_tags: List[str]) -> Dict[str, List[str]]:
        """
        获取所有模块的关键词匹配情况
        
        Args:
            all_tags: 片段标签
            
        Returns:
            Dict: 每个模块匹配的关键词列表
        """
        matches = {}
        
        # 🔧 过滤None值，确保类型安全
        all_tags = [tag for tag in all_tags if tag is not None and isinstance(tag, str)]
        
        tags_text = " ".join(all_tags).lower()
        
        for module in self.four_modules:
            module_matches = []
            
            # 检查每种类型的关键词
            if module in self.keyword_rules:
                keywords = self.keyword_rules[module]
                for kw in keywords:
                    if kw and isinstance(kw, str) and kw.lower() in tags_text:
                        module_matches.append(kw)
            
            matches[module] = module_matches
        
        return matches
    
    def _is_excluded_by_negative_keywords(self, tags_text: str) -> bool:
        """
        🔧 简化版：检查片段是否被全局排除关键词排除
        
        Args:
            tags_text: 标签文本（已转换为小写）
            
        Returns:
            bool: 是否应该被排除
        """
        try:
            # 🔧 简化：使用已加载的配置
            if not hasattr(self, 'rules') or not self.rules:
                # 如果没有加载配置，尝试加载
                self._load_matching_rules()
                
            # 🔧 NEW: 强化类型检查
            if not self.rules or not isinstance(self.rules, dict):
                logger.warning(f"配置规则类型错误或为空: {type(self.rules).__name__ if self.rules else 'None'}")
                return False
            
            # 🚫 只检查全局排除关键词（简化逻辑）
            if "GLOBAL_SETTINGS" in self.rules:
                global_settings = self.rules["GLOBAL_SETTINGS"]
                
                # 🔧 NEW: 确保GLOBAL_SETTINGS也是字典
                if not isinstance(global_settings, dict):
                    logger.warning(f"GLOBAL_SETTINGS类型错误: {type(global_settings).__name__}")
                    return False
                
                # 检查全局排除关键词
                global_exclusion = global_settings.get("global_exclusion_keywords", [])
                if isinstance(global_exclusion, list):
                    for global_kw in global_exclusion:
                        if isinstance(global_kw, str) and global_kw.lower() in tags_text:
                            logger.info(f"🚫 全局排除关键词过滤: '{global_kw}' 在 '{tags_text}' 中")
                            return True
            
                # 检查无关场景类别
                irrelevant_categories = global_settings.get("irrelevant_scene_categories", {})
                if isinstance(irrelevant_categories, dict):
                    for category, keywords in irrelevant_categories.items():
                        if isinstance(keywords, list):
                            for keyword in keywords:
                                if isinstance(keyword, str) and keyword.lower() in tags_text:
                                    logger.info(f"🚫 无关场景过滤 - {category}: '{keyword}' 在 '{tags_text}' 中")
                                    return True
            
            return False
            
        except Exception as e:
            logger.warning(f"排除关键词检查失败: {e}")
            return False
    
    def _classify_by_embedding_similarity(self, all_tags: List[str]) -> str:
        """
        使用embedding相似度进行分类（DeepSeek超时时的fallback）
        如果embedding模型不可用，则使用关键词分类
        
        Args:
            all_tags: 标签列表
            
        Returns:
            分类结果
        """
        # 🔧 Embedding models are disabled. This method now directly falls back to keyword classification.
        logger.info("Embedding models are disabled. _classify_by_embedding_similarity falling back to keywords.")
        
        # Original logic when embedding_model is None:
        # if not self.embedding_model or not self.embedding_util:
        #     logger.info("Embedding模型不可用，使用关键词分类作为fallback")
        #     keyword_result = self.classify_segment_by_tags(all_tags)
        #     return keyword_result if keyword_result else "其他"
        
        # Simplified fallback:
        keyword_result = self.classify_segment_by_tags(all_tags)
        return keyword_result if keyword_result else "其他"
            
        # The rest of the original method (embedding logic) is now unreachable 
        # because self.embedding_model will always be None.
        # Consider removing the unreachable code below in a future cleanup if this change is permanent.
        
        # if not all_tags:
        #     return "其他"
            
        # tags_text = " ".join(all_tags)
        # logger.info(f"使用embedding相似度分类: {tags_text}")
        
        # # 🔧 尝试主模型分类
        # result = self._classify_with_model(all_tags, self.embedding_model, "主模型")
        # if result != "模型失败":
        #     return result
        
        # # 🔧 主模型失败，尝试fallback模型
        # if hasattr(self, 'fallback_model') and self.fallback_model:
        #     logger.warning("主模型分类失败，尝试使用fallback模型")
        #     result = self._classify_with_model(all_tags, self.fallback_model, "fallback模型")
        #     if result != "模型失败":
        #         return result
        
        # # 🔧 所有embedding模型都失败，回退到关键词分类
        # logger.error("所有embedding模型都不可用，回退到关键词分类")
        # keyword_result = self.classify_segment_by_tags(all_tags)
        # return keyword_result if keyword_result else "其他"
    
    def _classify_with_model(self, all_tags: List[str], model, model_name: str) -> str:
        """
        使用指定模型进行分类
        
        Args:
            all_tags: 标签列表
            model: SentenceTransformer模型实例
            model_name: 模型名称（用于日志）
            
        Returns:
            分类结果，失败时返回"模型失败"
        """
        if not model or not self.embedding_util:
            logger.debug(f"{model_name}不可用")
            return "模型失败"
            
        if not all_tags:
            return "其他"
            
        tags_text = " ".join(all_tags)
        
        try:
            # 定义各类别的代表性文本
            category_texts = {
                "痛点机制": "宝宝哭闹 婴儿不适 喂养困难 睡眠问题 健康担忧",
                "促销机制": "宝宝喝奶粉开心 宝宝玩耍开心 宝宝奔跑 户外玩耍 游乐场 大笑 欢乐 活力",
                "科普机制": "营养知识 育儿方法 健康指导 专业建议 科学喂养",
                "情感机制": "母爱 亲情 温馨 陪伴 成长 关爱"
            }
            
            # 计算相似度
            embeddings = model.encode([tags_text] + list(category_texts.values()))
            similarities = self.embedding_util.pytorch_cos_sim(embeddings[0], embeddings[1:])
            
            # 找到最相似的类别
            max_similarity = float(similarities.max())
            max_index = int(similarities.argmax())
            
            categories = list(category_texts.keys())
            best_category = categories[max_index]
            
            # 设置阈值，相似度太低则返回"其他"
            threshold = 0.4
            if max_similarity < threshold:
                logger.info(f"{model_name} 相似度 {max_similarity:.3f} 低于阈值 {threshold}，返回其他")
                return "其他"
            
            logger.info(f"{model_name} 分类成功: {tags_text} -> {best_category} (相似度: {max_similarity:.3f})")
            return best_category
            
        except Exception as e:
            logger.error(f"{model_name} 分类失败: {e}")
            return "模型失败"
    
    def classify_segment_by_deepseek(self, all_tags: List[str]) -> str:
        """
        🔧 使用DeepSeek模型进行分类（统一prompt配置）
        """
        if not self.deepseek_analyzer or not self.deepseek_analyzer.is_available():
            logger.warning("DeepSeek分析器不可用，使用embedding fallback")
            return self._classify_by_embedding_similarity(all_tags)
        
        if not all_tags:
            logger.info("标签为空，DeepSeek跳过分类，返回其他")
            return "其他"
        
        tags_text = " ".join(all_tags)
        logger.info(f"使用DeepSeek分类: {tags_text}")
        
        try:
            analyzer = self.deepseek_analyzer
            
            # 🔧 使用简化的分类prompt，避免冗余
            try:
                # 动态构建分类指令
                config_manager = get_config_manager()
                rules = config_manager.get_matching_rules()
                
                system_prompt_parts = ["你是一个专业的母婴视频内容分析师。请根据视频标签，将内容分类为以下四个模块之一："]
                for module, config in rules.items():
                    # 拼接核心词作为模块描述
                    core_terms = ", ".join(config.get('core_identity', []))
                    system_prompt_parts.append(f"- **{module}**: 核心信号包括 {core_terms}")
                
                system_prompt_parts.append("\n请只回答模块名称，不要其他解释。如果无法确定，回答\"其他\"。")
                system_content = "\n".join(system_prompt_parts)
                
            except Exception as e:
                logger.warning(f"无法从配置中心构建DeepSeek prompt: {e}，使用兜底prompt")
                system_content = """你是一个专业的母婴视频内容分析师。请根据视频标签，将内容分类为以下四个模块之一：

1. 痛点：宝宝哭闹、不适、喂养困难、生病、焦虑等负面情况
2. 解决方案导入：冲奶粉、使用奶瓶、喂养过程、产品使用等行动场景
3. 卖点·成分&配方：A2蛋白、HMO、DHA、营养成分、产品特色等专业内容
4. 促销机制：宝宝开心、活力满满、健康成长、优惠活动等正面推广

请只回答模块名称，不要其他解释。如果无法确定，回答"其他"。"""

            user_content = f"视频标签: {', '.join(all_tags)}。请分类。"
            
            response = analyzer.analyze_text(system_content, user_content)
            
            if response and "choices" in response and len(response["choices"]) > 0:
                content = response["choices"][0]["message"]["content"].strip()
                if content in self.four_modules:
                    logger.info(f"DeepSeek分类成功: {tags_text} -> {content}")
                    return content
                else:
                    logger.warning(f"DeepSeek返回无效分类: {content}, 回退到关键词分类")
                    keyword_result = self.classify_segment_by_tags(all_tags)
                    return keyword_result if keyword_result else "其他"
            else:
                logger.warning("DeepSeek API响应无效，回退到关键词分类")
                keyword_result = self.classify_segment_by_tags(all_tags)
                return keyword_result if keyword_result else "其他"
                
        except Exception as e:
            logger.error(f"DeepSeek分类失败: {e}")
            logger.info("回退到关键词分类")
            keyword_result = self.classify_segment_by_tags(all_tags)
            return keyword_result if keyword_result else "其他"
    
    def classify_segment(self, all_tags: List[str], segment_info: Optional[Dict[str, Any]] = None) -> str:
        """
        对片段进行分类（关键词优先，DeepSeek兜底），并记录详细决策过程
        """
        selection_logger = get_selection_logger()
        logger.debug(f"开始分类片段，标签: {all_tags}")
        
        # 第一步：关键词规则分类
        category = self.classify_segment_by_tags(all_tags)
        
        if category:
            log_reason = "关键词分类成功"
            selection_logger.log_step(
                step_type="keyword_classification",
                input_tags=all_tags,
                result=category
            )
        
        # 第二步：如果关键词分类失败，使用DeepSeek模型
        else:
            logger.info(f"关键词规则无法分类标签 {all_tags}，使用DeepSeek模型")
            category = self.classify_segment_by_deepseek(all_tags)
            log_reason = "AI分类成功，关键词分类失败" if category != "其他" else "关键词和AI分类都无法确定类别"

        # 第三步：应用负面关键词过滤
        if category and category != "其他":
            filtered_category, filter_reason = self._apply_module_negative_filter(category, all_tags)
            if filtered_category != category:
                logger.info(f"🚫 分类已由负面关键词过滤: {category} -> {filtered_category} ({filter_reason})")
                category = filtered_category
                log_reason = f"负面关键词过滤: {filter_reason}"

        # 记录最终结果
        selection_logger.log_final_result(
            final_category=category,
            reason=log_reason,
            segment_info=segment_info
        )
        
        return category
    
    def scan_video_pool(self, video_pool_path: str = "data/output/google_video/video_pool") -> List[Dict[str, Any]]:
        """
        扫描video_pool目录中的所有JSON文件
        
        Args:
            video_pool_path: video_pool目录路径
            
        Returns:
            List[Dict]: 映射后的片段列表
        """
        mapped_segments = []
        
        # 🔧 核心修复：添加映射阶段去重机制
        seen_segment_ids = set()  # 用于跟踪已经映射的片段ID
        
        # 🔧 使用跨平台兼容的路径解析
        resolved_path = resolve_video_pool_path(video_pool_path)
        logger.info(f"🔍 解析video_pool路径: {video_pool_path} -> {resolved_path}")
        
        # 确保路径存在
        if not os.path.exists(resolved_path):
            logger.error(f"video_pool目录不存在: {resolved_path}")
            logger.error(f"当前工作目录: {os.getcwd()}")
            return mapped_segments
        
        # 查找所有JSON文件
        json_files = glob.glob(os.path.join(resolved_path, "*.json"))
        logger.info(f"在 {resolved_path} 中找到 {len(json_files)} 个JSON文件")
        
        if not json_files:
            logger.warning(f"在 {resolved_path} 中未找到任何JSON文件")
            return mapped_segments
        
        # 处理每个JSON文件，添加进度跟踪
        for file_idx, json_file in enumerate(json_files):
            try:
                logger.info(f"正在处理文件 {file_idx + 1}/{len(json_files)}: {os.path.basename(json_file)}")
                
                # 🔧 添加文件大小检查，避免处理过大的文件
                file_size = os.path.getsize(json_file)
                if file_size > 50 * 1024 * 1024:  # 50MB限制
                    logger.warning(f"跳过过大的文件: {json_file} ({file_size/1024/1024:.1f}MB)")
                    continue
                
                with open(json_file, 'r', encoding='utf-8') as f:
                    video_data = json.load(f)
                
                video_id = video_data.get('video_id', 'unknown')
                segments = video_data.get('segments', [])
                
                logger.info(f"处理视频 {video_id}，包含 {len(segments)} 个片段")
                
                # 🔧 限制每个文件处理的片段数量，避免过度处理
                max_segments_per_file = 100
                if len(segments) > max_segments_per_file:
                    logger.warning(f"文件 {json_file} 包含 {len(segments)} 个片段，只处理前 {max_segments_per_file} 个")
                    segments = segments[:max_segments_per_file]
                
                # 处理每个片段
                for seg_idx, segment in enumerate(segments):
                    try:
                        # 🔧 添加片段处理进度日志
                        if seg_idx % 10 == 0:  # 每10个片段记录一次
                            logger.info(f"🔄 处理片段进度: {seg_idx + 1}/{len(segments)}")
                        
                        # 基本信息提取
                        file_path = segment.get('file_path', '')
                        all_tags = segment.get('all_tags', [])
                        quality_score = segment.get('quality_score', 0.9)
                        confidence = segment.get('confidence', 0.8)
                        file_name = segment.get('file_name', '')
                        
                        # 🔧 添加analysis_method字段处理，为旧JSON文件提供默认值
                        analysis_method = segment.get('analysis_method', 'visual')  # 默认为visual
                        transcription = segment.get('transcription', None)  # 语音转录内容
                        
                        # 🔧 NEW: 兼容旧格式JSON文件，从其他字段构建all_tags
                        if not all_tags:
                            # 从旧格式字段构建标签 - 支持字符串和逗号分隔格式
                            raw_fields = [
                                segment.get('object', ''),
                                segment.get('scene', ''),
                                segment.get('emotion', ''),
                                segment.get('brand_elements', '')
                            ]
                            
                            all_tags = []
                            for raw_field in raw_fields:
                                if not raw_field:
                                    continue
                                    
                                # 处理逗号分隔的情况
                                if ',' in raw_field:
                                    tags = raw_field.split(',')
                                else:
                                    tags = [raw_field]
                                
                                # 清理和添加标签
                                for tag in tags:
                                    clean_tag = tag.strip()
                                    if clean_tag and clean_tag not in all_tags:
                                        all_tags.append(clean_tag)
                            
                            logger.debug(f"从旧格式构建标签: {file_name} -> {all_tags}")
                        
                        # 跳过空标签片段
                        if not all_tags:
                            logger.debug(f"跳过空标签片段: {file_name}")
                            continue
                        
                        # 🎯 NEW: 跳过人脸特写片段
                        is_face_close_up = segment.get('is_face_close_up', False)
                        is_unusable = segment.get('unusable', False)
                        unusable_reason = segment.get('unusable_reason', '')
                        
                        if is_face_close_up or is_unusable:
                            logger.info(f"🚫 跳过人脸特写/不可用片段: {file_name} (原因: {unusable_reason})")
                            continue
                        
                        # 🔧 添加超时控制的视频时长提取
                        duration = 0
                        if file_path and os.path.exists(file_path):
                            try:
                                duration = self.get_video_duration_ffprobe(file_path)
                            except Exception as e:
                                logger.warning(f"获取视频时长失败: {file_path}, 错误: {e}")
                                duration = 0
                        else:
                            logger.warning(f"视频文件不存在: {file_path}")
                        
                        # 🕒 NEW: 检查时长限制，直接在扫描阶段过滤长视频
                        max_duration = 10  # 默认10秒
                        if hasattr(self, 'rules') and self.rules:
                            global_settings = self.rules.get("GLOBAL_SETTINGS", {})
                            if isinstance(global_settings, dict):
                                max_duration = global_settings.get("max_duration_seconds", 10)
                        
                        if duration > max_duration:
                            logger.info(f"🕒 时长过滤: {file_name} (时长{duration:.1f}s > 限制{max_duration}s)")
                            continue
                        
                        # 🔧 构建片段信息用于日志记录
                        segment_info_for_logging = {
                            "file_name": file_name,
                            "duration": duration,
                            "all_tags": all_tags,
                            "combined_quality": quality_score * confidence,
                            "is_face_close_up": is_face_close_up
                        }
                        
                        # 🔧 添加超时控制的分类处理
                        try:
                            logger.debug(f"🔍 开始分类片段: {file_name} 标签: {all_tags}")
                            category = self.classify_segment(all_tags, segment_info_for_logging)
                            logger.info(f"🎯 分类完成: {file_name} -> {category}")
                        except Exception as e:
                            logger.error(f"❌ 片段分类失败: {file_name} {all_tags}, 错误: {e}")
                            category = "其他"
                        
                        # 计算综合质量分
                        combined_quality = quality_score * confidence
                        
                        # 🔧 生成片段的唯一标识符进行去重检查（增强版）
                        # 使用文件路径+文件名+标签的组合来确保唯一性
                        tags_signature = "_".join(sorted(all_tags[:5]))  # 前5个标签排序组合
                        unique_id = f"{video_id}::{file_name}::{file_path}::{tags_signature}"
                        
                        # 🔧 核心去重检查：避免重复映射
                        if unique_id in seen_segment_ids:
                            logger.info(f"🚫 跳过重复片段: {file_name} (ID: {unique_id[:100]}...)")
                            continue
                        
                        # 构建映射结果
                        mapped_segment = {
                            "segment_id": f"{video_id}_{file_name}",
                            "file_path": file_path,
                            "file_name": file_name,  # 🔧 确保使用file_name字段名
                            "filename": file_name,   # 🔧 添加filename字段以保持兼容性
                            "all_tags": all_tags,
                            "category": category,    # 🔧 确保使用category字段名
                            "classification": category,  # 🔧 添加classification字段以保持兼容性
                            "quality_score": quality_score,
                            "confidence": confidence,
                            "combined_quality": combined_quality,
                            "duration": duration,
                            "video_id": video_id,
                            "analysis_method": analysis_method,  # 🔧 添加analysis_method字段
                            "transcription": transcription,      # 🔧 添加transcription字段
                            "success": True
                        }
                        
                        # 🔧 添加到已见集合和结果列表
                        seen_segment_ids.add(unique_id)
                        mapped_segments.append(mapped_segment)
                        logger.info(f"✅ 映射片段: {file_name} -> {category} (时长: {duration:.2f}s, 标签: {all_tags[:3]})")
                        
                    except Exception as e:
                        logger.error(f"处理片段失败: {segment.get('file_name', segment.get('filename', 'unknown'))}, 错误: {e}")
                        continue
                
                logger.info(f"文件 {os.path.basename(json_file)} 处理完成，成功处理 {len([s for s in mapped_segments if s['video_id'] == video_id])} 个片段")
                        
            except Exception as e:
                logger.error(f"处理JSON文件失败: {json_file}, 错误: {e}")
                continue
        
        logger.info(f"🎯 映射完成统计:")
        logger.info(f"   - 最终有效片段: {len(mapped_segments)} 个")
        logger.info(f"   - 已处理唯一ID: {len(seen_segment_ids)} 个")
        logger.info(f"   - 去重效果: {len(seen_segment_ids) - len(mapped_segments)} 个重复被过滤")
        
        return mapped_segments
    
    def get_mapping_statistics(self, mapped_segments: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        获取映射统计信息
        
        Args:
            mapped_segments: 映射后的片段列表
            
        Returns:
            Dict: 统计信息
        """
        stats = {
            "total_segments": len(mapped_segments),
            "by_category": {},
            "by_video": {},
            "quality_stats": {
                "avg_quality": 0,
                "avg_confidence": 0,
                "avg_duration": 0,
                "total_duration": 0
            }
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
            stats["quality_stats"]["avg_quality"] = sum(s["quality_score"] for s in mapped_segments) / len(mapped_segments)
            stats["quality_stats"]["avg_confidence"] = sum(s["confidence"] for s in mapped_segments) / len(mapped_segments)
            stats["quality_stats"]["avg_duration"] = sum(s["duration"] for s in mapped_segments) / len(mapped_segments)
            stats["quality_stats"]["total_duration"] = sum(s["duration"] for s in mapped_segments)
        
        return stats

    def _init_embedding_model_online(self):
        """在线模式下初始化embedding模型（增强版）"""
        import time
        
        # 在线模式的多个fallback选项
        online_models = [
            'all-MiniLM-L6-v2',          # 主选择
            'all-mpnet-base-v2',         # 备选1
            'paraphrase-MiniLM-L6-v2'    # 备选2
        ]
        
        for attempt, model_name in enumerate(online_models, 1):
            logger.info(f"尝试在线模型 {attempt}/{len(online_models)}: {model_name}")
            
            # 每个模型尝试3次
            for retry in range(3):
                try:
                    from sentence_transformers import SentenceTransformer, util
                    
                    if retry > 0:
                        wait_time = retry * 2  # 递增等待时间
                        logger.info(f"第{retry + 1}次重试，等待{wait_time}秒...")
                        time.sleep(wait_time)
                    
                    # 设置较短的超时时间
                    self.embedding_model = SentenceTransformer(model_name, device='cpu')
                    self.embedding_util = util
                    logger.info(f"✅ 在线模式成功: {model_name} (重试{retry}次)")
                    return True
                    
                except ImportError as e:
                    logger.error(f"❌ 无法导入sentence_transformers: {e}")
                    return False
                    
                except Exception as e:
                    logger.warning(f"在线模型 {model_name} 第{retry + 1}次尝试失败: {e}")
                    if "Connection" in str(e) or "timeout" in str(e).lower():
                        logger.debug("检测到网络问题，继续重试...")
                        continue
                    else:
                        logger.debug("非网络问题，跳过重试")
                        break
        
        # 所有在线选项都失败，使用纯关键词模式
        logger.error("❌ 所有在线模型都无法加载")
        logger.info("🔄 切换到纯关键词分类模式（无需embedding）")
        self.embedding_model = None
        self.embedding_util = None
        return False

    def _apply_module_negative_filter(self, predicted_module: str, all_tags: List[str]) -> Tuple[str, str]:
        """
        应用模块特定的负面关键词过滤
        
        Args:
            predicted_module: 预测的模块名
            all_tags: 片段标签列表
            
        Returns:
            Tuple[str, str]: (最终模块, 过滤原因)
        """
        # 🔧 过滤None值，确保类型安全
        all_tags = [tag for tag in all_tags if tag is not None and isinstance(tag, str)]
        
        tags_text = ' '.join(all_tags).lower()
        
        # 获取关键词配置
        try:
            from utils.config_manager import get_config_manager
            config_manager = get_config_manager()
            raw_config = config_manager.get_raw_config()
            keywords_config = raw_config
        except Exception as e:
            logger.error(f"无法加载关键词配置: {e}")
            return predicted_module, ""
        
        # 特殊处理：卖点·成分&配方模块的负面过滤
        if predicted_module == "卖点·成分&配方":
            try:
                # 检查features_formula的负面关键词
                negatives = keywords_config.get('features_formula', {}).get('negative_keywords', [])
                detected_negatives = [neg for neg in negatives if neg and isinstance(neg, str) and neg in tags_text]
                
                if detected_negatives:
                    # 特别检查玩耍、商场等场景
                    play_scene_negatives = ['玩具', '滑梯', '商场', '游乐场', '户外', '公园', '玩耍', '游戏']
                    if any(neg in detected_negatives for neg in play_scene_negatives):
                        logger.info(f"🚫 移除卖点·成分&配方分类: 检测到玩耍/商场场景 {detected_negatives}")
                        return "其他", f"检测到非奶粉相关场景: {detected_negatives}"
                    
                    # 检查医疗场景
                    medical_negatives = ['医院', '诊所', '医生', '急诊', '儿科', '治疗']
                    if any(neg in detected_negatives for neg in medical_negatives):
                        logger.info(f"🚫 移除卖点·成分&配方分类: 检测到医疗场景 {detected_negatives}")
                        return "痛点", f"重新分类为痛点: {detected_negatives}"
                    
                    # 其他负面关键词
                    logger.info(f"🚫 移除卖点·成分&配方分类: 检测到负面关键词 {detected_negatives}")
                    return "其他", f"检测到负面关键词: {detected_negatives}"
                    
            except Exception as e:
                logger.error(f"卖点模块负面过滤失败: {e}")
        
        return predicted_module, ""

# 缓存的映射函数
@st.cache_data(ttl=3600, show_spinner=False)
def get_cached_mapping_results(video_pool_path: str) -> tuple:
    """
    缓存的映射结果获取函数
    
    Args:
        video_pool_path: video_pool目录路径
        
    Returns:
        tuple: (mapped_segments, statistics)
    """
    mapper = VideoSegmentMapper()
    mapped_segments = mapper.scan_video_pool(video_pool_path)
    statistics = mapper.get_mapping_statistics(mapped_segments)
    return mapped_segments, statistics 