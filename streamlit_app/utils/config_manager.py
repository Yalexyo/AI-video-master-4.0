import streamlit as st
import yaml
import os
from typing import Dict, Any, List, Set
import logging

# 设置日志
logger = logging.getLogger(__name__)

CONFIG_PATH = os.path.join(os.path.dirname(__file__), "..", "..", "config", "keywords.yml")

@st.cache_data(ttl=3600)
def load_yaml_config(path: str) -> Dict[str, Any]:
    """从指定路径加载YAML配置文件并缓存。"""
    try:
        with open(path, 'r', encoding='utf-8') as f:
            return yaml.safe_load(f)
    except FileNotFoundError:
        st.error(f"配置文件未找到: {path}")
        logger.error(f"配置文件未找到: {path}")
        return {}
    except Exception as e:
        st.error(f"加载或解析YAML配置文件失败: {e}")
        logger.error(f"加载或解析YAML配置文件失败: {e}")
        return {}

class ConfigManager:
    """
    统一配置中心。
    负责从 keywords.yml 加载业务蓝图，并动态生成AI和分类器所需的配置。
    支持批量定义（简洁写法）和传统配置格式。
    """
    def __init__(self, config_path: str = CONFIG_PATH):
        self._config = load_yaml_config(config_path)
        self._matching_rules = self._generate_matching_rules()
        self._ai_vocabulary = self._generate_ai_vocabulary()

    def _generate_matching_rules(self) -> Dict[str, Any]:
        """根据业务蓝图动态生成分类匹配规则。"""
        if not self._config:
            return {}
        
        rules = {}
        module_mapping = {
            "pain_points": "痛点",
            "solutions": "解决方案导入",
            "features_formula": "卖点·成分&配方",
            "promotions": "促销机制"
        }
        
        overrides = self._config.get("global_settings", {}).get("overrides", {})

        for key, module_name in module_mapping.items():
            module_data = self._config.get(key, {})
            if not module_data:
                continue

            # 🔧 统一提取核心身份词汇 (emotions, actions, features, brands)
            core_identity = []
            core_identity.extend(module_data.get("emotions", []))
            core_identity.extend(module_data.get("actions", []))
            core_identity.extend(module_data.get("features", []))
            core_identity.extend(module_data.get("brands", []))
            
            # 🆕 支持批量定义
            core_identity.extend(self._extract_batch_keywords(module_data))

            # 🆕 合并模块级和全局级 negative_keywords
            module_negatives = module_data.get("negative_keywords", [])
            global_negatives = overrides.get(f"{key}_negatives", [])
            combined_negatives = list(set(module_negatives + global_negatives))
            
            rules[module_name] = {
                "core_identity": core_identity,
                "extended_keywords": module_data.get("extended_keywords", {}),
                "negative_keywords": combined_negatives
            }
        
        return rules

    def _extract_batch_keywords(self, module_data: Dict[str, Any]) -> List[str]:
        """从批量定义中提取关键词。"""
        batch_keywords = []
        
        # 检查是否有ai_batch字段
        ai_batch = module_data.get("ai_batch", {})
        if ai_batch:
            for category, words in ai_batch.items():
                if isinstance(words, list):
                    for item in words:
                        if isinstance(item, dict):
                            # 提取word字段
                            word = item.get("word", "")
                            if word:
                                batch_keywords.append(word)
                        else:
                            # 兼容简单字符串格式
                            batch_keywords.append(str(item))
        
        return batch_keywords

    def _generate_ai_vocabulary(self) -> Dict[str, Set[str]]:
        """从整个配置中提取并去重，生成供AI使用的统一词汇表。支持批量定义。"""
        if not self._config:
            return {"object": set(), "scene": set(), "emotion": set(), "brand": set()}

        all_objects: Set[str] = set()
        all_scenes: Set[str] = set()
        all_emotions: Set[str] = set()
        all_brands: Set[str] = set()

        # 提取所有品牌（从features_formula.brands，这个是合理的）
        features_data = self._config.get("features_formula", {})
        all_brands.update(features_data.get("brands", []))
        
        # 遍历所有模块，优先使用批量定义
        all_modules_data = self._config.copy()
        global_settings = all_modules_data.pop("global_settings", None) # 移除全局配置
        
        # 统计使用传统映射的模块
        modules_without_batch = []
        modules_with_batch = []
        
        for module_key, module_data in all_modules_data.items():
            if not isinstance(module_data, dict):
                continue

            # 🆕 优先处理批量定义（精确控制）
            ai_batch = module_data.get("ai_batch", {})
            if ai_batch:
                # 处理每个类别，提取word字段
                for category in ["object", "scene", "emotion", "brand"]:
                    words = ai_batch.get(category, [])
                    target_set = {"object": all_objects, "scene": all_scenes, "emotion": all_emotions, "brand": all_brands}[category]
                    
                    for item in words:
                        if isinstance(item, dict):
                            word = item.get("word", "")
                            if word:
                                target_set.add(word)
                        else:
                            target_set.add(str(item))
                modules_with_batch.append(module_key)
                logger.info(f"✅ 模块 {module_key} 使用批量定义，分布: object={len(ai_batch.get('object', []))}, scene={len(ai_batch.get('scene', []))}, emotion={len(ai_batch.get('emotion', []))}, brand={len(ai_batch.get('brand', []))}")
            else:
                # ⚠️ 检测到没有批量定义的模块
                modules_without_batch.append(module_key)
                
                # 🔥 重要：不再使用错误的传统映射做兜底！
                # 原来的错误逻辑：
                # all_emotions.update(module_data.get("emotions", []))  # 这个还算合理
                # all_objects.update(module_data.get("actions", []))    # 这个部分合理  
                # all_emotions.update(module_data.get("features", []))  # ❌ 这个是错误的！
                
                # 🆕 新逻辑：仅处理明确合理的传统映射
                # emotions → emotion （这个映射是合理的）
                traditional_emotions = module_data.get("emotions", [])
                if traditional_emotions:
                    all_emotions.update(traditional_emotions)
                    logger.warning(f"⚠️ 模块 {module_key} 的emotions字段使用传统映射到emotion类别")
                
                # 🚫 不再自动处理 actions 和 features 字段
                # 因为它们的映射规则存在问题，需要用户明确使用批量定义
                traditional_actions = module_data.get("actions", [])
                traditional_features = module_data.get("features", [])
                
                if traditional_actions:
                    logger.warning(f"⚠️ 模块 {module_key} 的actions字段被忽略，请使用ai_batch明确指定AI类别")
                if traditional_features:
                    logger.warning(f"⚠️ 模块 {module_key} 的features字段被忽略，请使用ai_batch明确指定AI类别")
            
        # 📊 生成配置质量报告
        total_modules = len([k for k in all_modules_data.keys() if isinstance(all_modules_data[k], dict)])
        batch_coverage = len(modules_with_batch) / total_modules * 100 if total_modules > 0 else 0
        
        if modules_without_batch:
            logger.warning(f"⚠️ 配置质量警告：{len(modules_without_batch)}/{total_modules} 个模块未使用批量定义: {modules_without_batch}")
            logger.warning(f"⚠️ 批量定义覆盖率: {batch_coverage:.1f}%，建议100%覆盖以获得最佳AI识别效果")
        else:
            logger.info(f"✅ 配置质量优秀：所有模块都使用批量定义，AI词汇分类精确可控")

        logger.info(f"最终AI词汇分布: object={len(all_objects)}, scene={len(all_scenes)}, emotion={len(all_emotions)}, brand={len(all_brands)}")

        return {
            "object": all_objects,
            "scene": all_scenes,
            "emotion": all_emotions,
            "brand": all_brands
        }

    def get_matching_rules(self) -> Dict[str, Any]:
        """获取生成的分类匹配规则。"""
        return self._matching_rules

    def get_ai_vocabulary(self) -> Dict[str, Set[str]]:
        """获取生成的AI词汇表。"""
        return self._ai_vocabulary
        
    def get_raw_config(self) -> Dict[str, Any]:
        """获取原始的、未经处理的配置文件内容。"""
        return self._config

    def get_ai_statistics(self) -> Dict[str, int]:
        """获取AI词汇分布统计。"""
        vocab = self.get_ai_vocabulary()
        return {
            "object": len(vocab["object"]),
            "scene": len(vocab["scene"]),
            "emotion": len(vocab["emotion"]),
            "brand": len(vocab["brand"])
        }

    def supports_batch_definition(self) -> bool:
        """检查配置是否使用了批量定义。"""
        if not self._config:
            return False
        
        for module_key, module_data in self._config.items():
            if isinstance(module_data, dict) and "ai_batch" in module_data:
                return True
        return False

    def get_promotions_config(self) -> Dict[str, Any]:
        """获取促销机制模块的完整配置。"""
        return self._config.get("promotions", {})

    def get_global_exclusion_keywords(self) -> List[str]:
        """获取全局排除关键词列表。"""
        # 假设全局排除关键词存储在 global_settings 下
        global_settings = self._config.get("global_settings", {})
        return global_settings.get("global_exclusion_keywords", [])

    def get_negative_keywords_for_module(self, module_key: str) -> List[str]:
        """
        获取指定模块的最终排除关键词列表，合并了模块自身和全局的配置。
        """
        # 实现逻辑：从配置中提取指定模块的 negative_keywords
        # 这里需要根据实际的配置结构来实现
        # 目前只是一个占位，实际实现需要根据配置结构来提取
        return []

    def get_keywords_config(self) -> Dict[str, Any]:
        """
        获取关键词配置，主要用于AI分析器的负面关键词过滤。
        返回原始配置文件内容。
        """
        return self._config

# 创建一个全局实例，以便在应用中方便地调用
# 使用@st.cache_resource确保在整个会话中只有一个实例
@st.cache_resource
def get_config_manager():
    logger.info("正在创建或获取ConfigManager实例...")
    return ConfigManager() 