"""
视频片段映射模块
用于将video_pool中的视频片段自动映射到四大模块：痛点、解决方案导入、卖点·成分&配方、促销机制
"""

import os
import json
import glob
import subprocess
import logging
from typing import List, Dict, Any, Optional
import streamlit as st
from pathlib import Path
import threading
import time

logger = logging.getLogger(__name__)

class VideoSegmentMapper:
    """视频片段映射器"""
    
    def __init__(self):
        """初始化映射器"""
        self.four_modules = ["痛点", "解决方案导入", "卖点·成分&配方", "促销机制"]
        
        # 🔧 初始化DeepSeek分析器
        try:
            from streamlit_app.modules.ai_analyzers import DeepSeekAnalyzer
            self.deepseek_analyzer = DeepSeekAnalyzer()
            logger.info("DeepSeek分析器初始化完成")
        except ImportError as e:
            logger.warning(f"无法导入DeepSeek分析器: {e}")
            self.deepseek_analyzer = None
        except Exception as e:
            logger.error(f"DeepSeek分析器初始化失败: {e}")
            self.deepseek_analyzer = None
        
        # 🔧 使用统一配置文件加载关键词规则
        try:
            from streamlit_app.utils.keyword_config import get_mapper_keywords, get_pain_point_rules
            
            # 从配置文件加载关键词映射
            self.keyword_rules = get_mapper_keywords()
            
            # 从配置文件加载痛点专用规则
            self.pain_point_rules = get_pain_point_rules()
            
            logger.info("🎯 映射器配置加载成功，使用统一关键词配置文件")
            logger.info(f"   模块数量: {len(self.keyword_rules)}")
            logger.info(f"   痛点规则: {len(self.pain_point_rules)}")
            
        except ImportError:
            logger.warning("无法导入关键词配置，使用默认映射规则")
            # 兜底配置
            self.keyword_rules = {
                "痛点": ["医院", "哭闹", "发烧"],
                "解决方案导入": ["冲奶", "奶粉罐", "奶瓶"],
                "卖点·成分&配方": ["A2", "HMO", "DHA", "启赋"],
                "促销机制": ["优惠", "限时", "促销"]
            }
            self.pain_point_rules = {
                "baby_presence": ["宝宝", "婴儿"],
                "negative_emotions": ["哭", "痛苦", "焦虑"],
                "visual_signals": ["宝宝哭", "医院"]
            }
        
        # 🔧 特殊处理：品牌优先级关键词（从配置文件获取）
        try:
            from streamlit_app.utils.keyword_config import get_brands
            self.brand_priority_keywords = get_brands()
        except ImportError:
            self.brand_priority_keywords = ["启赋", "illuma", "Wyeth", "A2", "ATWO", "HMO", "DHA"]
        
        # 🔧 Intentionally disable embedding models
        logger.info("EMBEDDING MODELS ARE DISABLED. Classification will rely on keywords and DeepSeek API.")
        self.embedding_model = None
        self.fallback_model = None # Though fallback_model was part of embedding, set to None for clarity
        self.embedding_util = None
    
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
        基于简化5情绪+关键词的高精度分类
        
        Args:
            all_tags: 片段的所有标签列表
            
        Returns:
            str: 分类结果，如果无法分类返回None
        """
        if not all_tags:
            logger.debug("classify_segment_by_tags: 标签列表为空，返回None")
            return None
            
        tags_text = " ".join(all_tags).lower()
        logger.debug(f"classify_segment_by_tags: 待分类标签文本: '{tags_text}'")
        
        # 🚫 第零优先级：检查全局排除关键词和负面关键词过滤
        if self._is_excluded_by_negative_keywords(tags_text):
            logger.warning(f"🚫 片段被排除关键词过滤: '{tags_text}'")
            return None
        
        # 🎯 第一优先级：基于5个固定情绪进行分类
        if "痛苦" in tags_text or "焦虑" in tags_text:
            logger.info(f"🎯 痛苦/焦虑情绪匹配 -> 痛点")
            return "痛点"
        
        if "快乐" in tags_text or "兴奋" in tags_text:
            logger.info(f"🎯 快乐/兴奋情绪匹配 -> 促销机制")
            return "促销机制"
        
        # 🎯 第二优先级：痛点场景直接识别
        try:
            from streamlit_app.utils.keyword_config import get_pain_point_rules
            pain_rules = get_pain_point_rules()
            pain_signals = pain_rules.get("visual_signals", [])
        except ImportError:
            pain_signals = [
                "宝宝哭", "输液管", "医院", "病床", "发烧", "夜醒", "父母焦虑",
                "哭闹", "拉肚子", "生病", "医院场景"
            ]
        
        for signal in pain_signals:
            if signal in tags_text:
                logger.info(f"🎯 痛点场景信号匹配: '{signal}' -> 痛点")
                return "痛点"
        
        # 🎯 第三优先级：活力促销场景识别（🔧 新策略：只认欢乐活力镜头）
        try:
            from streamlit_app.utils.keyword_config import get_promotion_vitality_keywords
            vitality_keywords = get_promotion_vitality_keywords()  # 🔧 使用新的活力关键词
        except ImportError:
            vitality_keywords = [
                "宝宝喝奶粉开心", "喝奶粉开心", "宝宝玩耍开心", "宝宝奔跑", "宝宝跳跃",
                "户外玩耍", "公园", "游乐场", "滑梯", "蹦床", "大笑", "欢乐", "活力"
            ]
        
        # 🎯 新纲领：只认欢乐活力镜头，不需文字CTA
        for keyword in vitality_keywords:
            if keyword in tags_text:
                logger.info(f"🎯 活力欢乐信号匹配: '{keyword}' -> 促销机制")
                return "促销机制"
        
        # 🎯 第四优先级：品牌卖点识别
        try:
            from streamlit_app.utils.keyword_config import get_brands
            brands = get_brands()
            brand_signals = [brand.lower() for brand in brands] + [
                "营养表", "营养成分", "分子结构", "品牌logo"
            ]
        except ImportError:
            brand_signals = [
                "启赋", "wyeth", "illuma", "a2", "atwo", "hmo", "dha",
                "营养表", "营养成分", "分子结构", "品牌logo"
            ]
        
        for signal in brand_signals:
            if signal in tags_text:
                logger.info(f"🎯 品牌卖点信号匹配: '{signal}' -> 卖点·成分&配方")
                return "卖点·成分&配方"
        
        # 🎯 第五优先级：解决方案场景识别（扩展关键词）
        solution_signals = [
            # 🔧 核心特征：妈妈说教场景
            "妈妈", "母亲", "长辈", "奶奶", "婆婆", "专家", "医生",
            "说话", "讲解", "指导", "教导", "传授", "分享", "告诉",
            "经验", "建议", "提醒", "叮嘱", "关怀", "呵护",
            
            # 🔧 教学场景特征
            "教学", "教程", "演示", "示范", "指导视频", "经验分享",
            "知识", "方法", "技巧", "窍门", "注意事项", "小贴士",
            "正确方法", "使用方法", "如何", "怎么", "步骤",
            
            # 🔧 产品使用场景（保留重要的）
            "冲奶", "冲调", "调配", "配制", "奶粉罐", "奶瓶", "勺子",
            "准备奶粉", "操作演示", "产品演示", "台面操作",
            
            # 🔧 关爱互动场景
            "耐心", "细心", "温柔", "关爱", "母爱", "亲情",
            "对话", "交流", "沟通", "解答", "回应",
            
            # 🔧 场景环境（妈妈说教常见场景）
            "客厅", "沙发", "餐桌", "厨房", "家庭", "居家",
            "面对面", "坐着", "聊天", "谈话"
        ]
        
        for signal in solution_signals:
            if signal in tags_text:
                logger.info(f"🎯 解决方案信号匹配: '{signal}' -> 解决方案导入")
                return "解决方案导入"
        
        # 🔧 增强兜底规则：温馨 + 产品相关 = 解决方案
        if "温馨" in tags_text:
            # 检查是否有产品相关元素
            product_related = ["奶粉", "奶瓶", "喂养", "冲调", "产品", "包装"]
            has_product = any(prod in tags_text for prod in product_related)
            if has_product:
                logger.info("🎯 温馨+产品场景匹配 -> 解决方案导入")
                return "解决方案导入"
            else:
                logger.info("🎯 纯温馨情绪，无产品元素 -> 跳过")
        
        # 🔧 保留原有的痛点组合判断作为兜底
        if self._is_pain_point_by_combination(all_tags):
            logger.info(f"🎯 痛点组合规则匹配 -> 痛点")
            return "痛点"
        
        # 🔧 保留原有的关键词规则作为最后兜底
        for module, keywords in self.keyword_rules.items():
            if module == "痛点":  # 痛点已经通过上面的逻辑处理
                continue
                
            for keyword in keywords:
                if keyword.lower() in tags_text:
                    logger.info(f"🎯 传统关键词匹配: '{keyword}' -> {module}")
                    return module
        
        logger.info(f"🎯 所有规则均未匹配: '{tags_text}'")
        return None
    
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
            
        tags_text = " ".join(all_tags).lower()
        
        # 检查是否有宝宝在场
        has_baby = False
        for baby_keyword in self.pain_point_rules["baby_presence"]:
            if baby_keyword.lower() in tags_text:
                has_baby = True
                logger.debug(f"痛点检测: 发现宝宝关键词 '{baby_keyword.lower()}'")
                break
        
        # 检查是否有负面情绪
        has_negative_emotion = False
        matched_emotion = None
        for emotion_keyword in self.pain_point_rules["negative_emotions"]:
            if emotion_keyword.lower() in tags_text:
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
            # 检查映射规则配置文件
            config_file = "../config/matching_rules.json"
            if not os.path.exists(config_file):
                config_file = "config/matching_rules.json"
            
            if os.path.exists(config_file):
                with open(config_file, 'r', encoding='utf-8') as f:
                    matching_rules = json.load(f)
                
                # 检查模块级别的排除关键词
                for module, rules in matching_rules.items():
                    if module == "GLOBAL_SETTINGS":
                        continue
                    
                    negative_keywords = rules.get("negative_keywords", [])
                    module_matches = []
                    
                    for neg_kw in negative_keywords:
                        if neg_kw.lower() in tags_text.lower():
                            module_matches.append(neg_kw)
                    
                    if module_matches:
                        result["is_excluded"] = True
                        result["exclusion_reasons"].append(f"{module}模块排除: {module_matches}")
                        result["matched_keywords"][module] = module_matches
                
                # 检查全局排除设置
                if "GLOBAL_SETTINGS" in matching_rules:
                    global_settings = matching_rules["GLOBAL_SETTINGS"]
                    irrelevant_categories = global_settings.get("irrelevant_scene_categories", {})
                    
                    for category, keywords in irrelevant_categories.items():
                        global_matches = []
                        for kw in keywords:
                            if kw.lower() in tags_text.lower():
                                global_matches.append(kw)
                        
                        if global_matches:
                            result["is_excluded"] = True
                            result["exclusion_reasons"].append(f"全局排除-{category}: {global_matches}")
                            result["matched_keywords"][f"global_{category}"] = global_matches
            
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
        tags_text = " ".join(all_tags).lower()
        
        for module in self.four_modules:
            module_matches = []
            
            # 检查每种类型的关键词
            if module in self.keyword_rules:
                keywords = self.keyword_rules[module]
                for kw in keywords:
                    if kw.lower() in tags_text:
                        module_matches.append(kw)
            
            matches[module] = module_matches
        
        return matches
    
    def _is_excluded_by_negative_keywords(self, tags_text: str) -> bool:
        """
        检查片段是否被负面关键词排除
        
        Args:
            tags_text: 标签文本（已转换为小写）
            
        Returns:
            bool: 是否应该被排除
        """
        try:
            # 加载matching_rules.json中的排除配置
            import json
            config_file = "../config/matching_rules.json"
            # 如果相对路径不存在，尝试绝对路径
            if not os.path.exists(config_file):
                config_file = "config/matching_rules.json"
            if os.path.exists(config_file):
                with open(config_file, 'r', encoding='utf-8') as f:
                    matching_rules = json.load(f)
            else:
                logger.warning("matching_rules.json不存在，跳过排除检查")
                return False
            
            # 🚫 检查全局排除关键词（优先级最高）
            if "GLOBAL_SETTINGS" in matching_rules:
                global_exclusion = matching_rules["GLOBAL_SETTINGS"].get("global_exclusion_keywords", [])
                for global_kw in global_exclusion:
                    if global_kw.lower() in tags_text:
                        logger.warning(f"🚫 全局排除关键词过滤: '{global_kw}' 在 '{tags_text}' 中")
                        return True
            
            # 1. 检查全局排除关键词
            if "GLOBAL_SETTINGS" in matching_rules:
                global_settings = matching_rules["GLOBAL_SETTINGS"]
                irrelevant_categories = global_settings.get("irrelevant_scene_categories", {})
                
                for category, keywords in irrelevant_categories.items():
                    for keyword in keywords:
                        if keyword.lower() in tags_text:
                            logger.warning(f"🚨 全局排除命中 - {category}: '{keyword}' 在 '{tags_text}' 中")
                            return True
            
            # 2. 检查各模块的负面关键词
            modules = ["痛点", "解决方案导入", "卖点·成分&配方", "促销机制"]
            
            for module in modules:
                if module in matching_rules:
                    negative_keywords = matching_rules[module].get("negative_keywords", [])
                    
                    for neg_kw in negative_keywords:
                        if neg_kw.lower() in tags_text:
                            logger.warning(f"🚫 模块排除命中 - {module}: '{neg_kw}' 在 '{tags_text}' 中")
                            return True
            
            # 3. 检查solution_intro和pain_point的特殊排除规则
            for special_module in ["solution_intro", "pain_point"]:
                if special_module in matching_rules:
                    negative_keywords = matching_rules[special_module].get("negative_keywords", [])
                    
                    for neg_kw in negative_keywords:
                        if neg_kw.lower() in tags_text:
                            logger.warning(f"🚫 特殊排除命中 - {special_module}: '{neg_kw}' 在 '{tags_text}' 中")
                            return True
            
            return False
            
        except Exception as e:
            logger.error(f"排除关键词检查失败: {e}")
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
            
            # 🔧 使用统一的prompt配置
            try:
                from streamlit_app.utils.keyword_config import get_mapper_keywords
                keywords = get_mapper_keywords()
                
                # 构建分类系统prompt
                system_content = """你是一个专业的母婴视频内容分析师。请根据视频标签，将内容分类为以下四种机制之一：

1. 痛点机制：宝宝哭闹、不适、喂养困难等负面情况
2. 促销机制：宝宝开心、活力、玩耍等正面场景  
3. 科普机制：营养知识、育儿方法、专业指导
4. 情感机制：母爱、亲情、温馨、陪伴

请只回答机制名称，不要其他解释。如果无法确定，回答"其他"。"""
                
            except Exception as e:
                logger.warning(f"无法导入统一关键词配置: {e}")
                system_content = """你是一个专业的母婴视频内容分析师。请根据视频标签，将内容分类为以下四种机制之一：

1. 痛点机制：宝宝哭闹、不适、喂养困难等负面情况
2. 促销机制：宝宝开心、活力、玩耍等正面场景  
3. 科普机制：营养知识、育儿方法、专业指导
4. 情感机制：母爱、亲情、温馨、陪伴

请只回答机制名称，不要其他解释。如果无法确定，回答"其他"。"""
            
            messages = [
                {
                    "role": "system",
                    "content": system_content
                },
                {
                    "role": "user", 
                    "content": f"请分析这些视频标签：{tags_text}"
                }
            ]
            
            # 使用线程和超时机制
            result_container = {"result": None, "error": None}
            
            def call_deepseek():
                try:
                    response = analyzer._chat_completion(messages)
                    if response and "choices" in response and len(response["choices"]) > 0:
                        content = response["choices"][0]["message"]["content"].strip()
                        result_container["result"] = content
                    else:
                        result_container["error"] = "API响应格式无效"
                except Exception as e:
                    result_container["error"] = str(e)
            
            # 启动线程
            thread = threading.Thread(target=call_deepseek)
            thread.daemon = True
            thread.start()
            
            # 等待结果，设置超时
            timeout = 10  # 10秒超时
            thread.join(timeout)
            
            if thread.is_alive():
                # 超时，使用embedding fallback
                logger.warning(f"DeepSeek API调用超时，回退到关键词分类: {tags_text}")
                keyword_result = self.classify_segment_by_tags(all_tags)
                return keyword_result if keyword_result else "其他"
            
            if result_container["error"]:
                logger.error(f"DeepSeek API调用失败: {result_container['error']}")
                logger.info("回退到关键词分类")
                keyword_result = self.classify_segment_by_tags(all_tags)
                return keyword_result if keyword_result else "其他"
            
            result = result_container["result"]
            if result:
                # 验证返回的分类是否有效
                valid_categories = ["痛点机制", "促销机制", "科普机制", "情感机制", "其他"]
                if any(cat in result for cat in valid_categories):
                    for cat in valid_categories:
                        if cat in result:
                            logger.info(f"DeepSeek分类成功: {tags_text} -> {cat}")
                            return cat
                else:
                    logger.warning(f"DeepSeek返回无效分类: {result}, 回退到关键词分类")
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
        
        Args:
            all_tags: 片段的所有标签列表
            segment_info: 片段详细信息（用于日志记录）
            
        Returns:
            str: 分类结果
        """
        # 🔧 添加调试信息
        logger.debug(f"开始分类片段，标签: {all_tags}")
        
        # 初始化选片日志
        try:
            from streamlit_app.modules.selection_logger import get_selection_logger
            selection_logger = get_selection_logger()
        except ImportError:
            selection_logger = None
        
        analysis_steps = []
        segment_name = segment_info.get("file_name", "unknown") if segment_info else "unknown"
        
        # 🚫 第一步：检查排除关键词
        tags_text = " ".join(all_tags).lower()
        exclusion_result = self._detailed_exclusion_check(tags_text)
        
        if selection_logger:
            exclusion_step = selection_logger.log_exclusion_check(
                segment_name, all_tags, exclusion_result
            )
            analysis_steps.append(exclusion_step)
        
        if exclusion_result.get("is_excluded", False):
            logger.info(f"🚫 片段被排除关键词过滤: '{' '.join(all_tags)}'")
            
            if selection_logger and segment_info:
                selection_logger.log_segment_analysis(
                    segment_info, analysis_steps, "其他", 
                    f"被排除关键词过滤: {exclusion_result.get('exclusion_reasons', [])}"
                )
            
            return "其他"
        
        # 🎯 第二步：基于关键词的快速分类
        keyword_matches = self._get_keyword_matches(all_tags)
        keyword_result = self.classify_segment_by_tags(all_tags)
        
        if selection_logger:
            keyword_step = selection_logger.log_keyword_classification(
                segment_name, all_tags, keyword_matches, keyword_result
            )
            analysis_steps.append(keyword_step)
        
        if keyword_result:
            logger.debug(f"关键词分类成功: {all_tags} -> {keyword_result}")
            
            if selection_logger and segment_info:
                selection_logger.log_segment_analysis(
                    segment_info, analysis_steps, keyword_result,
                    f"关键词匹配成功: {keyword_matches.get(keyword_result, [])}"
                )
            
            return keyword_result
        
        # 🤖 第三步：如果关键词分类失败，使用AI分类
        logger.info(f"关键词规则无法分类标签 {all_tags}，使用DeepSeek模型")
        
        ai_start_time = time.time()
        deepseek_result = self.classify_segment_by_deepseek(all_tags)
        ai_duration = time.time() - ai_start_time
        
        if selection_logger:
            ai_step = selection_logger.log_ai_classification(
                segment_name, all_tags, deepseek_result, 0.8,  # 默认置信度
                {"duration": ai_duration, "error": None}
            )
            analysis_steps.append(ai_step)
        
        logger.debug(f"DeepSeek分类结果: {all_tags} -> {deepseek_result}")
        
        if selection_logger and segment_info:
            if deepseek_result and deepseek_result != "其他":
                selection_logger.log_segment_analysis(
                    segment_info, analysis_steps, deepseek_result,
                    "AI分类成功，关键词分类失败"
                )
            else:
                selection_logger.log_segment_analysis(
                    segment_info, analysis_steps, "其他",
                    "关键词和AI分类都无法确定类别"
                )
        
        return deepseek_result
    
    def scan_video_pool(self, video_pool_path: str = "data/output/google_video/video_pool") -> List[Dict[str, Any]]:
        """
        扫描video_pool目录中的所有JSON文件
        
        Args:
            video_pool_path: video_pool目录路径
            
        Returns:
            List[Dict]: 映射后的片段列表
        """
        mapped_segments = []
        
        # 确保路径存在
        if not os.path.exists(video_pool_path):
            logger.error(f"video_pool目录不存在: {video_pool_path}")
            return mapped_segments
        
        # 查找所有JSON文件
        json_files = glob.glob(os.path.join(video_pool_path, "*.json"))
        logger.info(f"在 {video_pool_path} 中找到 {len(json_files)} 个JSON文件")
        
        if not json_files:
            logger.warning(f"在 {video_pool_path} 中未找到任何JSON文件")
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
                            logger.debug(f"处理片段进度: {seg_idx + 1}/{len(segments)}")
                        
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
                                segment.get('sence', ''),
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
                            category = self.classify_segment(all_tags, segment_info_for_logging)
                        except Exception as e:
                            logger.error(f"片段分类失败: {all_tags}, 错误: {e}")
                            category = "其他"
                        
                        # 计算综合质量分
                        combined_quality = quality_score * confidence
                        
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
                        
                        mapped_segments.append(mapped_segment)
                        logger.debug(f"成功映射片段: {file_name} -> {category} (时长: {duration:.2f}s)")
                        
                    except Exception as e:
                        logger.error(f"处理片段失败: {segment.get('file_name', segment.get('filename', 'unknown'))}, 错误: {e}")
                        continue
                
                logger.info(f"文件 {os.path.basename(json_file)} 处理完成，成功处理 {len([s for s in mapped_segments if s['video_id'] == video_id])} 个片段")
                        
            except Exception as e:
                logger.error(f"处理JSON文件失败: {json_file}, 错误: {e}")
                continue
        
        logger.info(f"映射完成，共处理 {len(mapped_segments)} 个有效片段")
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