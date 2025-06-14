"""
千问2.5视觉分析器

专门处理千问2.5多模态视频分析功能的模块，包含语音转录保底机制
应用了qwen_optimization_guide.md中的全部优化策略
"""

import os
import logging
from typing import Dict, Any, List, Optional
from pathlib import Path
from collections import Counter
from http import HTTPStatus
import re
import json

# 导入音频分析器
from .dashscope_audio_analyzer import DashScopeAudioAnalyzer
from .deepseek_analyzer import DeepSeekAnalyzer

from utils.config_manager import get_config_manager

logger = logging.getLogger(__name__)


class QwenVideoAnalyzer:
    """千问2.5视觉分析器（包含语音转录保底机制 + 全面优化策略）"""
    
    def __init__(self, api_key: Optional[str] = None):
        """
        初始化千问2.5分析器
        
        Args:
            api_key: DashScope API密钥
        """
        self.api_key = api_key or os.environ.get("DASHSCOPE_API_KEY")
        self.analyzer = None
        
        # 初始化音频分析器 - 语音转录保底机制
        self.audio_analyzer = DashScopeAudioAnalyzer(api_key=self.api_key)
        
        # 初始化DeepSeek分析器 - 文本分析
        self.deepseek_analyzer = DeepSeekAnalyzer()
        
        if not self.api_key:
            logger.warning("未设置DASHSCOPE_API_KEY，千问2.5分析器不可用")
        else:
            self._initialize_analyzer()
    
    def _initialize_analyzer(self):
        """初始化千问2.5分析器"""
        try:
            import dashscope
            dashscope.api_key = self.api_key
            self.analyzer = True
            logger.info("千问2.5视觉分析器初始化成功")
        except ImportError as e:
            logger.error(f"无法导入DashScope: {str(e)}")
            self.analyzer = None
        except Exception as e:
            logger.error(f"千问2.5分析器初始化失败: {str(e)}")
            self.analyzer = None
            
        # 🔧 优化的模型参数配置
        self.model_config = {
            'model': 'qwen-vl-max-latest',   # 使用最新最强模型
            'temperature': 0.1,              # 降低随机性
            'top_p': 0.8,                   # 控制生成质量
            'max_tokens': 1500,             # 增加输出长度
            'seed': 1234                    # 确保可重复性
        }
        
        # 🔧 质量控制参数
        self.quality_config = {
            'min_quality_threshold': 0.6,   # 质量分阈值
            'max_retry_count': 1,            # 最大重试次数 (从2改为0以提高速度)
            'confidence_threshold': 0.6      # 置信度阈值
        }
        
        # 🎯 NEW: 短视频优化配置
        self.short_video_config = {
            'file_size_threshold_mb': 1.0,    # 小于1MB视为短视频
            'duration_threshold_sec': 5.0,    # 小于5秒视为短视频
            'quality_threshold_reduction': 0.15, # 短视频质量阈值降低0.15
            'frame_rate_boost': 2.0,           # 短视频帧率提升倍数
            'max_frame_rate': 8.0,             # 短视频最大帧率限制
            'min_file_size_mb': 0.5            # 小于此大小的文件将被过滤
        }
        
        logger.info(f"千问2.5分析器初始化完成，模型: {self.model_config['model']}")
    
    def is_available(self) -> bool:
        """检查分析器是否可用"""
        return self.analyzer is not None and self.api_key is not None
    
    def analyze_video_segment(
        self,
        video_path: str,
        tag_language: str = "中文",
        frame_rate: float = 2.0
    ) -> Dict[str, Any]:
        """
        视频片段分析（包含语音转录保底机制 + 全面优化策略）
        
        Args:
            video_path: 视频文件路径
            tag_language: 标签语言
            frame_rate: 帧率
            
        Returns:
            分析结果字典
        """
        logger.info(f"🎯 开始分析视频: {video_path}")

        if not self.is_available():
            return self._get_default_result("千问2.5分析器不可用")
        
        if not os.path.exists(video_path):
            return self._get_default_result(f"视频文件不存在: {video_path}")
        
        # 🎯 NEW: 短视频智能优化
        optimized_params = self._optimize_for_short_video(video_path, frame_rate)
        
        # 检查是否应该跳过处理
        if optimized_params.get("should_skip", False):
            return self._get_default_result(f"文件过小，已跳过: {optimized_params.get('reason', '未知')}")
        
        optimized_frame_rate = optimized_params['frame_rate']
        optimized_quality_threshold = optimized_params['quality_threshold']
        
        try:
            # 🎯 第一步：尝试视觉分析（带重试机制）
            logger.info("🎯 开始视觉分析...")
            visual_result = self._analyze_with_retry(video_path, optimized_frame_rate, tag_language, optimized_quality_threshold)
            
            if visual_result and visual_result.get('success'):
                # 🔍 检查是否需要启用语音转录保底机制
                if self._needs_audio_fallback(visual_result):
                    logger.warning("🎤 视觉分析存在未识别内容，启用DeepSeek音频转录兜底分析...")
                    
                    # 🎯 使用针对性分析而不是完整重新分析
                    enhanced_result = self._targeted_audio_fallback_analysis(video_path, visual_result, tag_language)
                    
                    if enhanced_result.get("success"):
                        logger.info("🎯 针对性DeepSeek语音兜底分析完成")
                        return enhanced_result
                    else:
                        logger.warning("🎯 针对性分析失败，返回原始visual结果")
                        return visual_result
                
                return visual_result
            else:
                # 🎤 视觉分析失败，直接启用语音转录保底
                logger.warning("🎤 Qwen视觉分析失败，启用DeepSeek音频转录兜底分析...")
                return self._audio_fallback_analysis(video_path, tag_language)
                
        except Exception as e:
            logger.error(f"视频分析失败: {str(e)}")
            # 🎤 异常情况下尝试语音转录保底
            try:
                return self._audio_fallback_analysis(video_path, tag_language)
            except Exception as fallback_error:
                logger.error(f"语音转录保底也失败: {str(fallback_error)}")
                return self._get_default_result(f"分析失败: {str(e)}")
    
    def _analyze_with_retry(self, video_path: str, frame_rate: float, tag_language: str, quality_threshold: float) -> Dict[str, Any]:
        """
        🔧 带重试机制的视觉分析（新增双模型分工机制）
        """
        max_retry = self.quality_config['max_retry_count']
        
        for attempt in range(max_retry + 1):
            try:
                # 🎯 第一阶段：通用物体识别（AI-B）
                general_prompt = self._build_general_detection_prompt(tag_language)
                general_result = self._analyze_video_file(video_path, frame_rate, general_prompt)
                
                if general_result and 'analysis' in general_result:
                    # 解析通用识别结果
                    general_analysis = self._parse_analysis_result(
                        general_result['analysis'], tag_language
                    )
                    
                    # 🕵️‍♂️ [侦查日志] 打印通用识别结果
                    logger.info("🕵️‍♂️ [侦查日志] ====== 通用识别阶段 (AI-B) ======")
                    logger.info(f"   - 原始返回: {general_result['analysis']}")
                    logger.info(f"   - 解析后: {general_analysis}")
                    logger.info("🕵️‍♂️ =======================================")
                    
                    # 🎯 第二阶段：品牌检测触发器
                    if self._should_trigger_brand_detection(general_analysis):
                        logger.info("🔍 检测到产品相关物体，启动核心品牌检测...")
                        brand_result = self._detect_core_brands(video_path, frame_rate)
                        if brand_result:
                            general_analysis['brand_elements'] = brand_result
                        logger.info(f"🎯 品牌检测完成，结果: {brand_result or '未检测到核心品牌'}")
                    else:
                        # 非产品相关场景，确保brand_elements为空
                        general_analysis['brand_elements'] = ""
                    
                    # 应用负面关键词过滤
                    general_analysis = self._apply_negative_keywords_filter(general_analysis)
                    
                    general_analysis["success"] = True
                    general_analysis["quality_score"] = general_result.get('quality_score', 0.8)
                    general_analysis["analysis_method"] = "dual_model_workflow"
                    general_analysis["retry_count"] = attempt
                    
                    # 检测人脸特写
                    face_close_up_detected = self._detect_face_close_up(general_analysis, video_path)
                    if face_close_up_detected:
                        logger.warning(f"🚫 检测到人脸特写片段，标记为不可用: {video_path}")
                        general_analysis["is_face_close_up"] = True
                        general_analysis["unusable"] = True
                        general_analysis["unusable_reason"] = "人脸特写片段"
                        # 降低质量分，确保在匹配时被过滤
                        general_analysis["quality_score"] = 0.1
                    else:
                        general_analysis["is_face_close_up"] = False
                        general_analysis["unusable"] = False
                    
                    # 检查质量
                    if general_analysis["quality_score"] >= quality_threshold:
                        logger.info(f"✅ 分析成功，质量分: {general_analysis['quality_score']:.2f}")
                        return general_analysis
                    elif attempt < max_retry:
                        logger.warning(f"⚠️ 质量分过低 ({general_analysis['quality_score']:.2f})，准备重试...")
                        continue
                    else:
                        # 最后一次重试，进行后处理优化
                        general_analysis = self._enhance_poor_result(general_analysis, video_path)
                        logger.info(f"🔧 应用后处理优化，最终质量分: {general_analysis['quality_score']:.2f}")
                        return general_analysis
                else:
                    if attempt < max_retry:
                        logger.warning(f"⚠️ 分析返回空结果，准备重试...")
                        continue
                    else:
                        return self._get_default_result("重试后仍无法获取分析结果")
                        
            except Exception as e:
                if attempt < max_retry:
                    logger.warning(f"⚠️ 分析异常: {str(e)}，准备重试...")
                    continue
                else:
                    logger.error(f"❌ 重试{max_retry}次后仍失败: {str(e)}")
                    return self._get_default_result(f"重试失败: {str(e)}")
        
        return self._get_default_result("重试机制异常")
    
    def _build_professional_prompt(self, tag_language: str) -> str:
        """
        🔧 构建Qwen视觉分析专用提示词（强调视频帧视觉元素识别）
        """
        try:
            from utils.keyword_config import get_qwen_visual_prompt
            prompt = get_qwen_visual_prompt()
            return prompt if prompt else self._get_fallback_visual_prompt()
        except Exception as e:
            logger.warning(f"无法导入Qwen视觉prompt生成逻辑，使用兜底配置: {e}")
            return self._get_fallback_visual_prompt()

    def _build_enhanced_retry_prompt(self, tag_language: str) -> str:
        """
        🔧 构建Qwen视觉分析重试提示词（同样专注于视觉识别）
        """
        try:
            from utils.keyword_config import get_qwen_visual_prompt
            prompt = get_qwen_visual_prompt()
            return prompt if prompt else self._get_fallback_retry_prompt()
        except Exception as e:
            logger.warning(f"无法导入Qwen视觉prompt生成逻辑，使用兜底配置: {e}")
            return self._get_fallback_retry_prompt()
    
    def _get_fallback_visual_prompt(self) -> str:
        """
        获取一个基于配置的、健壮的可视化分析兜底Prompt。
        不再硬编码关键词，而是从统一配置中心动态生成。
        """
        try:
            config_manager = get_config_manager()
            vocab = config_manager.get_ai_vocabulary()
            
            objects = list(vocab.get("object", []))
            scenes = list(vocab.get("scene", []))
            emotions = list(vocab.get("emotion", []))
            brands = list(vocab.get("brand", []))

            # 为空时提供默认值，避免Prompt格式错误
            if not objects: objects = ["奶粉罐", "宝宝"]
            if not scenes: scenes = ["室内", "户外"]
            if not emotions: emotions = ["开心", "温馨"]
            if not brands: brands = ["启赋", "A2"]

            prompt = f"""
请你作为一位专业的母婴行业视频内容分析师，严格、详细、客观地分析给你的视频帧。

**分析维度**:
1.  **`object` (物体识别)**: 识别视频中与母婴、喂养、生活相关的物体。
    -   参考词汇: {str(objects)}
2.  **`scene` (场景识别)**: 描述视频发生的场景。
    -   参考词汇: {str(scenes)}
3.  **`emotion` (情绪识别)**: 分析视频传达的核心情绪氛围。
    -   参考词汇: {str(emotions)}
4.  **`brand_elements` (品牌元素)**: **如果能明确识别**出以下品牌相关的logo、包装或文字，请列出。否则留空。
    -   核心品牌列表: {str(brands)}

**输出要求**:
-   必须严格按照以下JSON格式输出，不要添加任何额外说明或markdown标记。
-   所有字段都必须存在，即使没有识别到内容，也要返回一个空字符串 `""`。
-   识别的内容请用中文输出。

```json
{{
  "object": "识别出的物体，用逗号分隔",
  "scene": "识别出的场景，用逗号分隔",
  "emotion": "识别出的情绪，用逗号分隔",
  "brand_elements": "明确识别出的品牌，用逗号分隔"
}}
```
"""
            logger.info("成功从ConfigManager动态生成Qwen视觉Prompt。")
            return prompt

        except Exception as e:
            logger.error(f"从ConfigManager生成Qwen Prompt失败: {e}，使用硬编码的旧版Prompt。")
            # 在此保留一个硬编码的、功能性的兜底Prompt
            return """
请你作为一位专业的母婴行业视频内容分析师，严格、详细、客观地分析给你的视频帧。

**分析维度**:
1.  **`object` (物体识别)**: 识别视频中与母婴、喂养、生活相关的物体。
    -   参考词汇: ['奶粉罐', '奶瓶', '宝宝', '妈妈', '成分表', '包装']
2.  **`scene` (场景识别)**: 描述视频发生的场景。
    -   参考词汇: ['厨房', '客厅', '医院', '户外', '评测']
3.  **`emotion` (情绪识别)**: 分析视频传达的核心情绪氛围。
    -   参考词汇: ['开心', '温馨', '焦虑', '专业']
4.  **`brand_elements` (品牌元素)**: **如果能明确识别**出以下品牌相关的logo、包装或文字，请列出。否则留空。
    -   核心品牌列表: ['启赋', 'illuma', '惠氏', 'A2', 'HMO']

**输出要求**:
-   必须严格按照以下JSON格式输出，不要添加任何额外说明或markdown标记。
-   所有字段都必须存在，即使没有识别到内容，也要返回一个空字符串 `""`。
-   识别的内容请用中文输出。

```json
{{
  "object": "识别出的物体，用逗号分隔",
  "scene": "识别出的场景，用逗号分隔",
  "emotion": "识别出的情绪，用逗号分隔",
  "brand_elements": "明确识别出的品牌，用逗号分隔"
}}
```
"""
    
    def _get_fallback_retry_prompt(self) -> str:
        """获取重试视觉分析的兜底Prompt，风格更激进（使用动态配置）"""
        try:
            # 动态加载核心品牌列表
            core_brands_text = "核心品牌列表：['illuma', '启赋', '惠氏', '蕴淳', 'Wyeth', 'A2', 'ATWO', 'HMO']"
            try:
                from utils.keyword_config import get_brands
                brands = get_brands()
                if brands:
                    core_brands_text = f"核心品牌列表：{brands}"
            except Exception as e:
                logger.warning(f"无法加载核心品牌列表，将使用默认列表: {e}")

            # 关键优化：在重试Prompt中同样明确品牌范围
            return f"""
# **身份**
你是一位顶级的视觉分析专家，拥有火眼金睛，能够从视频帧中精准识别营销要素。

# **任务**
分析给定的视频帧，**只**从提供的"关键词词库"中选择最相关的词汇来描述内容。

# **核心指令**
1.  **关键词匹配**: 你的唯一任务是在图像中寻找与"关键词词库"匹配的元素。
2.  **品牌识别铁律**: `brand_elements`字段**只能**从下方"核心品牌列表"中选择。如果画面中没有明确出现这些核心品牌，该字段必须为"无"。**绝对禁止**识别任何其他品牌。
3.  **品牌识别重点**: 重点寻找包装上的品牌logo、产品名称、品牌标识文字，特别关注奶粉罐、包装盒上的品牌信息。
4.  **关键物体**: 对 "奶粉罐"、"奶瓶" 这类关键物体要进行最优先识别。
5.  **拒绝模糊**: 不要使用"疑似"、"可能"等任何不确定的描述。如果无法确定，请将该字段留空或标记为"无"。
6.  **结构化**: 严格按照下面的"输出格式"返回结果，不要有任何多余的解释。

# **关键词词库**
- **核心品牌列表（仅限识别以下品牌）**: {brand_vocab}
⚠️ **品牌识别铁律**: brand_elements字段只能从上述核心品牌列表选择，不得识别任何其他品牌！
- **物体词库**: {product_vocab}
- **场景词库**: {scene_vocab}
- **情绪词库**: {emotion_vocab}

# **输出格式** (严格遵守，使用'{tag_language}'语言)
object: [从"物体词库"中选择的词，用逗号分隔]
scene: [从"场景词库"中选择的词，用逗号分隔]
emotion: [从"情绪词库"中选择的词，用逗号分隔]  
brand_elements: [从"品牌词库"中选择的词，用逗号分隔]
confidence: [0.0-1.0]

# **示例**
- **输入**: 一张包含启赋奶粉罐和微笑宝宝的图片
- **输出**:
object: 奶粉罐,宝宝
scene: 产品特写,温馨
emotion: 开心,幸福
brand_elements: 启赋
confidence: 0.9

# **开始分析**
"""
        except Exception as e:
            logger.error(f"构建重试视觉Prompt失败: {e}")
            return "请严格重新分析画面，并按Object, Sence, Emotion, Brand_Elements, Confidence的格式输出。"
    
    def _get_fallback_audio_prompt(self) -> str:
        """
        获取一个基于配置的、健壮的音频转录分析兜底Prompt。
        动态从统一配置中心生成。
        """
        try:
            config_manager = get_config_manager()
            vocab = config_manager.get_ai_vocabulary()
            
            objects = list(vocab.get("object", []))
            scenes = list(vocab.get("scene", []))
            emotions = list(vocab.get("emotion", []))
            brands = list(vocab.get("brand", []))

            # 为空时提供默认值
            if not objects: objects = ["奶粉罐", "宝宝"]
            if not scenes: scenes = ["室内", "户外"]
            if not emotions: emotions = ["开心", "温馨"]
            if not brands: brands = ["启赋", "A2"]

            prompt = f"""
你是一个专业的内容分析师。请根据以下录音文本，提取内容标签。

**分析维度**:
1.  **`object` (提及物体)**: 文本中提到的具体事物。
    -   参考词汇: {str(objects)}
2.  **`scene` (提及场景)**: 文本中描述的场景。
    -   参考词汇: {str(scenes)}
3.  **`emotion` (表达情绪)**: 文本中传达的情感。
    -   参考词汇: {str(emotions)}
4.  **`brand_elements` (提及品牌)**: 文本中明确提到的品牌名称。
    -   核心品牌列表: {str(brands)}

**品牌识别铁律**:
⚠️ **严格限制**: brand_elements字段只能从上述核心品牌列表选择，不得识别任何其他品牌！
🎯 **识别重点**: 重点识别语音中直接说出的品牌名称，注意品牌的准确性和完整性。

**输出要求**:
-   严格按照以下JSON格式输出，不要有额外说明。
-   所有字段必须存在，没有则返回空字符串。

```json
{{
  "object": "提及的物体，用逗号分隔",
  "scene": "提及的场景，用逗号分隔",
  "emotion": "表达的情绪，用逗号分隔",
  "brand_elements": "明确提及的品牌，用逗号分隔"
}}
```
"""
            logger.info("成功从ConfigManager动态生成DeepSeek音频Prompt。")
            return prompt

        except Exception as e:
            logger.error(f"从ConfigManager生成DeepSeek Prompt失败: {e}，使用硬编码的旧版Prompt。")
            return """
你是一个专业的内容分析师。请根据以下录音文本，提取内容标签。

**分析维度**:
1.  **`object` (提及物体)**: 文本中提到的具体事物。
    -   参考词汇: ['奶粉', '奶瓶', '宝宝', '妈妈']
2.  **`scene` (提及场景)**: 文本中描述的场景。
    -   参考词汇: ['喂养', '睡觉', '玩耍']
3.  **`emotion` (表达情绪)**: 文本中传达的情感。
    -   参考词汇: ['开心', '哭闹', '健康']
4.  **`brand_elements` (提及品牌)**: 文本中明确提到的品牌名称。
    -   核心品牌列表: ['启赋', 'A2', 'illuma']

**品牌识别铁律**:
⚠️ **严格限制**: brand_elements字段只能从上述核心品牌列表选择，不得识别任何其他品牌！
🎯 **识别重点**: 重点识别语音中直接说出的品牌名称，注意品牌的准确性和完整性。

**输出要求**:
-   严格按照以下JSON格式输出，不要有额外说明。
-   所有字段必须存在，没有则返回空字符串。

```json
{{
  "object": "提及的物体，用逗号分隔",
  "scene": "提及的场景，用逗号分隔",
  "emotion": "表达的情绪，用逗号分隔",
  "brand_elements": "明确提及的品牌，用逗号分隔"
}}
```
"""
    
    def _get_default_result(self, error_msg: str) -> Dict[str, Any]:
        """获取默认错误结果"""
        return {
            "success": False,
            "error": error_msg,
            "object": "",
            "scene": "",
            "emotion": "",
            "brand_elements": "",
            "confidence": 0.0,
            "all_tags": []
        }
        
    def _analyze_video_file(self, video_path: str, frame_rate: float, prompt: str) -> Dict[str, Any]:
        """分析视频文件"""
        try:
            import cv2
            import dashscope
            
            # 提取帧
            cap = cv2.VideoCapture(video_path)
            if not cap.isOpened():
                return None
            
            # 获取视频时长
            fps = cap.get(cv2.CAP_PROP_FPS)
            frame_count = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
            duration = frame_count / fps if fps > 0 else 0
            
            # 🔧 极保守的帧采样策略
            frames = self._ultra_conservative_frame_sampling(cap, duration)
            cap.release()
            
            if not frames:
                return None
            
            # 调用千问API
            messages = [
                {
                    'role': 'user',
                    'content': [
                        {'text': prompt},
                        *[{'image': frame_data} for frame_data in frames]
                    ]
                }
            ]
            
            response = dashscope.MultiModalConversation.call(
                model=self.model_config['model'],
                messages=messages,
                temperature=self.model_config['temperature'],
                top_p=self.model_config['top_p'],
                max_tokens=self.model_config['max_tokens']
            )
            
            if response.status_code == HTTPStatus.OK:
                # 🔧 修复：处理content可能是list的情况
                content = response.output.choices[0].message.content
                if isinstance(content, list):
                    # 如果content是列表，提取text部分
                    result_text = ""
                    for item in content:
                        if isinstance(item, dict) and 'text' in item:
                            result_text += item['text']
                        elif isinstance(item, str):
                            result_text += item
                else:
                    result_text = str(content) if content else ""
                
                logger.info(f"🔍 千问API返回内容: {result_text[:200]}...")
                quality_score = self._assess_result_quality(result_text)
                return {'analysis': result_text, 'quality_score': quality_score}
            else:
                logger.error(f"千问API调用失败: {response.message}")
                return None
                
        except Exception as e:
            logger.error(f"视频文件分析失败: {str(e)}")
            return None
    
    def _ultra_conservative_frame_sampling(self, cap, duration: float) -> List[str]:
        """
        🔧 极保守的帧采样策略 - 符合API最严格要求
        """
        import cv2
        import base64
        from io import BytesIO
        from PIL import Image
        
        frames = []
        
        # 🔧 极保守策略 - 只采样1帧，避免内容长度超限
        cap.set(cv2.CAP_PROP_POS_MSEC, duration * 0.5 * 1000)
        ret, frame = cap.read()
        
        if ret:
            try:
                # 转换为PIL图像
                frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                pil_image = Image.fromarray(frame_rgb)
                
                # 🔧 极度压缩图像
                processed_image = self._ultra_compress_image(pil_image)
                
                # 转换为base64
                buffered = BytesIO()
                processed_image.save(buffered, format='JPEG', quality=60)
                img_base64 = base64.b64encode(buffered.getvalue()).decode('utf-8')
                frames.append(f"data:image/jpeg;base64,{img_base64}")
                
                logger.info(f"🔧 极保守帧采样完成，图像尺寸: {processed_image.size}")
                
            except Exception as e:
                logger.warning(f"处理帧时出错: {str(e)}")
        
        return frames
    
    def _ultra_compress_image(self, pil_image):
        """
        🔧 极度压缩图像 - 符合API最严格要求
        """
        from PIL import Image
        
        # 🔧 极保守的尺寸策略 - 224x224 (8x28 = 224)
        target_width = 224   # 28的倍数
        target_height = 224  # 28的倍数
        
        # 强制调整到目标尺寸
        compressed_image = pil_image.resize((target_width, target_height), Image.Resampling.LANCZOS)
        return compressed_image
    
    def _assess_result_quality(self, result_text: str) -> float:
        """
        🔧 优化的结果质量评估
        """
        if not result_text or len(result_text.strip()) < 10:
            return 0.0
        
        quality_score = 0.5  # 基础分
        
        # 必要字段完整性 (30%)
        required_fields = ['object:', 'scene:', 'emotion:', 'brand_elements:', 'confidence:']
        field_count = sum(1 for field in required_fields if field in result_text)
        quality_score += (field_count / len(required_fields)) * 0.3
        
        # 避免"无"回答 (15%)
        if '无' not in result_text or result_text.count('无') <= 1:
            quality_score += 0.15
        
        # 内容丰富度 (5%)
        if len(result_text) > 100:
            quality_score += 0.05
        
        return min(quality_score, 1.0)
    
    def _enhance_poor_result(self, result: Dict[str, Any], video_path: str) -> Dict[str, Any]:
        """
        🔧 智能后处理优化 - 增强低质量结果
        """
        logger.info("🔧 开始后处理优化...")
        
        enhanced_result = result.copy()
        
        # 🚨 严格遵循新策略：不再填充任何"疑似..."占位符
        # 所有无效内容一律保持为空，让AI模型和用户明确知道这些内容未被识别
        
        # 清理无效占位符
        invalid_values = ['无', '画面不清晰', '不确定', '']
        
        for field in ['object', 'scene', 'emotion']:
            if enhanced_result.get(field) in invalid_values:
                enhanced_result[field] = ''  # 保持为空，不填充占位符
        
        # 🚨 品牌字段严格过滤：绝不填充任何内容，保持为空
        if enhanced_result.get('brand_elements') in invalid_values:
            enhanced_result['brand_elements'] = ''  # 保持为空，严格遵守品牌过滤规则
        
        # 重建all_tags（不包含无效占位符）
        enhanced_result['all_tags'] = self._rebuild_tags(enhanced_result)
        
        # 轻微提升质量分，但不过度优化
        enhanced_result['quality_score'] = min(enhanced_result.get('quality_score', 0.0) + 0.05, 0.6)
        
        logger.info(f"🔧 后处理优化完成，质量分: {enhanced_result['quality_score']:.2f}")
        return enhanced_result
    
    def _extract_video_info(self, video_path: str) -> Dict[str, Any]:
        """提取视频基本信息"""
        try:
            import cv2
            cap = cv2.VideoCapture(video_path)
            if cap.isOpened():
                fps = cap.get(cv2.CAP_PROP_FPS)
                frame_count = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
                duration = frame_count / fps if fps > 0 else 0
                cap.release()
                return {'duration': duration, 'fps': fps, 'frame_count': frame_count}
        except:
            pass
        return {'duration': 0, 'fps': 0, 'frame_count': 0}
    
    def _rebuild_tags(self, result: Dict[str, Any]) -> List[str]:
        """重建all_tags字段，严格过滤无效和占位符标签"""
        all_tags = []
        
        # 定义无效标签列表
        invalid_tags = [
            '无', '画面不清晰', '不确定', '',
            '疑似室内环境', '疑似温馨氛围', '疑似产品展示', '疑似人物活动',
            '疑似品牌要素', '疑似'
        ]
        
        for field in ['object', 'scene', 'emotion', 'brand_elements']:
            value = result.get(field, '')
            if value and value not in invalid_tags:
                tags = [tag.strip() for tag in value.split(',') if tag.strip()]
                all_tags.extend(tags)
        
        # 去重并严格过滤
        unique_tags = []
        for tag in all_tags:
            # 移除任何"疑似"前缀
            tag_clean = tag.replace('疑似', '').strip()
            
            # 跳过无效标签
            if (tag_clean and 
                tag_clean not in invalid_tags and 
                tag_clean not in unique_tags and
                len(tag_clean) > 1):  # 至少2个字符的有效标签
                unique_tags.append(tag_clean)
        
        return unique_tags
    
    def _parse_analysis_result(self, analysis_text, tag_language: str) -> Dict[str, Any]:
        """
        解析AI模型返回的文本结果，并进行严格的后处理过滤。
        """
        # 🔧 重用的格式清理函数
        def clean_field_value(value: str) -> str:
            """清理字段值，确保输出简洁的单词短语"""
            if not value:
                return ''
            
            # 基础清理
            cleaned = value.strip()
            
            # 🔧 重要修复：移除字段标识符干扰
            field_markers = ['object:', 'scene:', 'emotion:', 'brand_elements:', 'confidence:']
            for marker in field_markers:
                if marker in cleaned:
                    # 如果在开头，移除它
                    if cleaned.startswith(marker):
                        cleaned = cleaned[len(marker):].strip()
                    else:
                        # 如果在中间，只取前面部分
                        cleaned = cleaned.split(marker)[0].strip()
            
            # 去除Markdown和特殊符号
            cleaned = cleaned.replace('**', '').replace('*', '')
            cleaned = cleaned.replace('- ', '').replace('+ ', '')
            cleaned = cleaned.replace('# ', '').replace('[', '').replace(']', '')
            cleaned = cleaned.replace('(', '').replace(')', '')
            cleaned = cleaned.replace('"', '').replace("'", '')
            cleaned = cleaned.replace('：', ':').replace('。', '').replace('；', '')
            
            # 去除多余空格和标点
            cleaned = re.sub(r'\s+', ' ', cleaned).strip()
            cleaned = re.sub(r'[,，]+', ',', cleaned)
            cleaned = cleaned.strip(',')
            
            # 过滤无意义内容
            meaningless = ['无', '不确定', '画面不清晰', '解析失败', 
                          '', 'none', 'n/a', '不明确', '相关']
            if cleaned.lower() in meaningless:
                return ''
            
            # 🔧 新增：过滤纯数字内容（confidence值误入其他字段）
            if re.match(r'^[0-9.]+$', cleaned):
                return ''
            
            # 🔧 强化：过滤包含纯数字的片段（如"0.5"误入品牌字段）
            if re.match(r'^[0-9]+\.?[0-9]*$', cleaned):
                return ''
            
            # 🔧 新增：过滤过短的无意义内容（1-2字符）
            if len(cleaned) <= 2 and cleaned.lower() in ['0', '1', '2', '3', '4', '5', '6', '7', '8', '9', '.']:
                return ''
            
            return cleaned
        
        try:
            result = {
                'interaction': '', # 新增
                'object': '',      # 保留
                'scene': '', 
                'emotion': '',
                'brand_elements': '',
                'confidence': 0.8
            }
            
            logger.info(f"🎯 开始解析简化分析文本:")
            logger.info(f"原始文本: {analysis_text}")
            
            # 🔧 支持两种格式：标准字段格式 和 简单文本格式
            lines = analysis_text.strip().split('\n')
            has_field_markers = any(':' in line for line in lines)
            
            if has_field_markers:
                # 格式1：标准字段格式（object: xxx）
                for line in lines:
                    line = line.strip()
                    if not line:
                        continue
                        
                    logger.debug(f"处理行: '{line}'")
                    
                    # 🔧 修复：处理竖线分隔符格式和行内格式
                    # 检查是否是竖线分隔的单行格式：object: ... | scene: ... | emotion: ... | brand: ...
                    if '|' in line and any(marker in line.lower() for marker in ['object:', 'scene:', 'emotion:', 'brand']):
                        # 处理竖线分隔格式
                        segments = line.split('|')
                        for segment in segments:
                            segment = segment.strip()
                            if segment.lower().startswith('object:'):
                                raw_value = segment[7:].strip()
                                result['object'] = clean_field_value(raw_value)
                                logger.debug(f"[竖线格式] 提取object: '{raw_value}' -> '{result['object']}'")
                            elif segment.lower().startswith('scene:'):
                                raw_value = segment[6:].strip()
                                result['scene'] = clean_field_value(raw_value)
                                logger.debug(f"[竖线格式] 提取scene: '{raw_value}' -> '{result['scene']}'")
                            elif segment.lower().startswith('emotion:'):
                                raw_value = segment[8:].strip()
                                result['emotion'] = clean_field_value(raw_value)
                                logger.debug(f"[竖线格式] 提取emotion: '{raw_value}' -> '{result['emotion']}'")
                            elif segment.lower().startswith('brand:') or segment.lower().startswith('brand_elements:'):
                                if segment.lower().startswith('brand:'):
                                    raw_value = segment[6:].strip()
                                else:
                                    raw_value = segment[15:].strip()
                                cleaned_brand = clean_field_value(raw_value)
                                if cleaned_brand:
                                    brand_parts = [part.strip() for part in cleaned_brand.split(',')]
                                    clean_parts = [part for part in brand_parts if part and not re.match(r'^[0-9]+\.?[0-9]*$', part)]
                                    result['brand_elements'] = ','.join(clean_parts) if clean_parts else ''
                                else:
                                    result['brand_elements'] = ''
                                logger.debug(f"[竖线格式] 提取brand: '{raw_value}' -> '{result['brand_elements']}'")
                    
                    # 标准单行格式处理
                    elif line.lower().startswith('object:'):
                        raw_value = line[7:].strip()
                        # 移除可能的竖线后缀
                        if '|' in raw_value:
                            raw_value = raw_value.split('|')[0].strip()
                        result['object'] = clean_field_value(raw_value)
                        logger.debug(f"提取object: '{raw_value}' -> '{result['object']}'")
                        
                    elif line.lower().startswith('scene:'):
                        raw_value = line[6:].strip()
                        if '|' in raw_value:
                            raw_value = raw_value.split('|')[0].strip()
                        result['scene'] = clean_field_value(raw_value)
                        logger.debug(f"提取scene: '{raw_value}' -> '{result['scene']}'")
                        
                    elif line.lower().startswith('emotion:'):
                        raw_value = line[8:].strip()
                        if '|' in raw_value:
                            raw_value = raw_value.split('|')[0].strip()
                        result['emotion'] = clean_field_value(raw_value)
                        logger.debug(f"提取emotion: '{raw_value}' -> '{result['emotion']}'")
                        
                    elif line.lower().startswith('brand_elements:') or line.lower().startswith('brand:'):
                        if line.lower().startswith('brand:'):
                            raw_value = line[6:].strip()
                        else:
                            raw_value = line[15:].strip()
                        # 移除可能的竖线后缀
                        if '|' in raw_value:
                            raw_value = raw_value.split('|')[0].strip()
                        # 🔧 特殊处理brand_elements：过滤数字污染
                        cleaned_brand = clean_field_value(raw_value)
                        if cleaned_brand:
                            # 进一步清理：移除纯数字片段
                            brand_parts = [part.strip() for part in cleaned_brand.split(',')]
                            clean_parts = [part for part in brand_parts if part and not re.match(r'^[0-9]+\.?[0-9]*$', part)]
                            result['brand_elements'] = ','.join(clean_parts) if clean_parts else ''
                        else:
                            result['brand_elements'] = ''
                        logger.debug(f"提取brand_elements: '{raw_value}' -> '{result['brand_elements']}'")
                        
                    elif line.lower().startswith('confidence:'):
                        confidence_text = line[11:].strip()
                        if '|' in confidence_text:
                            confidence_text = confidence_text.split('|')[0].strip()
                        try:
                            confidence_match = re.search(r'([0-9.]+)', confidence_text)
                            if confidence_match:
                                result['confidence'] = float(confidence_match.group(1))
                                logger.debug(f"提取confidence: '{confidence_text}' -> {result['confidence']}")
                        except:
                            result['confidence'] = 0.8
                    
                    elif line.lower().startswith('interaction:'):
                        raw_value = line[12:].strip()
                        result['interaction'] = clean_field_value(raw_value)
                        logger.debug(f"提取interaction: '{raw_value}' -> '{result['interaction']}'")
            
            # 为了兼容性，将interaction内容同步到object
            if result.get('interaction'):
                result['object'] = result['interaction']
            
            # 🔧 创建all_tags - 包含所有有意义的内容（强化数字过滤）
            all_tags = []
            for field_name, value in result.items():
                if field_name == 'confidence':
                    continue
                # 兼容性：不将interaction重复添加到all_tags
                if field_name == 'interaction':
                    continue
                if value:  # 只要不为空就处理
                    # 分割逗号分隔的标签
                    tags = [tag.strip() for tag in value.split(',') if tag.strip()]
                    for tag in tags:
                        cleaned_tag = clean_field_value(tag)
                        # 🔧 强化数字过滤：再次检查是否为纯数字
                        if cleaned_tag and not re.match(r'^[0-9]+\.?[0-9]*$', cleaned_tag):
                            all_tags.append(cleaned_tag)
            
            # 去重并过滤
            result['all_tags'] = list(set(filter(None, all_tags)))
            
            # 🚨 最后一步：严格过滤品牌元素，只保留配置中的品牌
            try:
                from utils.keyword_config import get_brands
                allowed_brands = [b.lower() for b in get_brands()]
            except Exception as e:
                logger.error(f"无法加载品牌配置，使用默认列表: {e}")
                allowed_brands = ['illuma', '启赋', '惠氏', '蕴淳', 'wyeth', 'a2', 'atwo', 'hmo']
            
            if result['brand_elements']:
                detected_brands_raw = result['brand_elements']
                detected_brands_list = [b.strip() for b in detected_brands_raw.split(',') if b.strip()]
                
                final_brands = []
                for brand in detected_brands_list:
                    # 必须是配置列表中的品牌（忽略大小写）
                    if brand.lower() in allowed_brands:
                        final_brands.append(brand)
                    else:
                        logger.debug(f"🚫 [品牌过滤] 已移除不在配置中的品牌: '{brand}'")
                
                # 去重并更新
                if final_brands:
                    result['brand_elements'] = ','.join(list(dict.fromkeys(final_brands)))
                else:
                    result['brand_elements'] = ''
            
            logger.info(f"🎯 简化解析最终结果:")
            logger.info(f"   交互行为: '{result.get('interaction', '')}'") # 新增日志
            logger.info(f"   物体: '{result['object']}'")
            logger.info(f"   场景: '{result['scene']}'")
            logger.info(f"   情绪: '{result['emotion']}'")
            logger.info(f"   品牌: '{result['brand_elements']}'")
            logger.info(f"   置信度: {result['confidence']}")
            logger.info(f"   全部标签: {result['all_tags']}")
            
            return result
            
        except Exception as e:
            logger.error(f"解析分析结果失败: {str(e)}")
            return {
                'interaction': '', # 新增
                'object': '',
                'scene': '',
                'emotion': '',
                'brand_elements': '',
                'confidence': 0.1,
                'all_tags': []
            }
    
    def _needs_audio_fallback(self, visual_result: Dict[str, Any]) -> bool:
        """判断是否需要启用语音转录保底机制"""
        all_tags = visual_result.get('all_tags', [])
        
        # 情况1：all_tags完全为空
        if not all_tags:
            return True
        
        # 情况2：all_tags只包含无意义内容
        meaningless_tags = {'不确定', '无', '画面不清晰', '解析失败', ''}
        if all(tag in meaningless_tags for tag in all_tags):
            return True
        
        # 情况3：质量分过低
        quality_score = visual_result.get('quality_score', 1.0)
        if quality_score < 0.5:
            return True
        
        # 情况4：关键字段为空时启用音频兜底
        def is_field_empty(field_value):
            """判断字段是否为空或无意义"""
            if not field_value:
                return True
            cleaned = str(field_value).strip()
            return cleaned in ['', '无', '不确定', '解析失败', '疑似品牌要素', '疑似人物活动', '疑似室内环境', '疑似温馨氛围']
        
        object_empty = is_field_empty(visual_result.get('object'))
        brand_empty = is_field_empty(visual_result.get('brand_elements'))
        scene_empty = is_field_empty(visual_result.get('scene'))
        emotion_empty = is_field_empty(visual_result.get('emotion'))
        
        # 如果物体和品牌都为空，启用音频兜底
        if object_empty and brand_empty:
            logger.info("🎤 检测到关键字段为空(物体+品牌)，启用音频兜底分析")
            return True
        
        # 如果物体、场景、品牌三者中有两个为空，也启用音频分析
        empty_count = sum([object_empty, brand_empty, scene_empty])
        if empty_count >= 2:
            logger.info(f"🎤 检测到{empty_count}个关键字段为空，启用音频兜底分析")
            return True
        
        # 如果四个主要字段中有3个为空，强制启用音频分析
        total_empty = sum([object_empty, brand_empty, scene_empty, emotion_empty])
        if total_empty >= 3:
            logger.info(f"🎤 检测到{total_empty}个字段为空(共4个)，强制启用音频兜底分析")
            return True
        
        return False
    
    def _get_targeted_analysis_prompt(self, transcription: str, visual_result: Dict[str, Any]) -> str:
        """为目标性音频分析生成Prompt，结合视觉和音频信息，按新优先级排序"""
        try:
            # 动态加载核心品牌列表
            core_brands_text = "核心品牌列表：['illuma', '启赋', '惠氏', '蕴淳', 'Wyeth', 'A2', 'ATWO', 'HMO']"
            try:
                from utils.keyword_config import get_brands
                brands = get_brands()
                if brands:
                    core_brands_text = f"核心品牌列表：{brands}"
            except Exception as e:
                logger.warning(f"无法加载核心品牌列表，将使用默认列表: {e}")

            visual_summary = (
                f"- **画面物体**: {visual_result.get('object', '未知')}\n"
                f"- **画面场景**: {visual_result.get('scene', '未知')}\n"
                f"- **画面情绪**: {visual_result.get('emotion', '未知')}"
            )

            # 按新优先级重新构建提示词
            return f"""
# **身份**
你是一位结合多模态信息（视觉+语音）的高级分析专家。

# **任务**
你的任务是结合"初步视觉分析摘要"和"语音转录文本"，对内容进行一次全面、精确的补充分析。语音信息是主要判断依据，视觉信息为辅助。

# **🎯 识别优先级顺序（按重要性排序）**
1️⃣ **最高优先级 - 品牌识别和品牌相关内容**
2️⃣ **第二优先级 - 情绪表达定位**
3️⃣ **第三优先级 - 其他物体和场景**

# **🏷️ 第一优先级：品牌识别和品牌相关内容识别**
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
- **品牌识别铁律**: 品牌(brand_elements)的识别必须遵守铁律：**只能**从"{core_brands_text}"中选择。如果在语音或视觉中没有明确提到这些核心品牌，该字段必须为"无"。**绝对禁止**识别任何其他品牌。
- **品牌识别重点**: 特别关注语音中直接提及的品牌名称，以及视觉中的品牌logo、包装标识。

🥛 **品牌相关内容（优先识别）**:
- **产品物体**: 奶粉、奶粉罐、奶瓶、产品包装、奶粉特写等
- **营养成分**: A2奶源、DHA、HMO、sn-2、成分、配方、自御力、保护力等
- **品牌标识**: 品牌logo、Logo特写、品牌标识、官方标识等
- **使用场景**: 冲奶、喂养、产品展示、专家推荐等
- **功效描述**: 免疫力、吸收、消化、健康成长、营养成分等

⚠️ **严格限制**: Brand_Elements字段只能从核心品牌列表选择，不得识别任何其他品牌！
🎯 **识别重点**: 
- 语音中直接说出的品牌名称
- 视觉中的品牌logo、产品包装标识
- 与核心品牌相关的产品特征描述

# **😊 第二优先级：情绪表达定位**
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
🎨 **情绪识别指引**:
- **语音情绪**: 重点识别语音中直接表达的情感词汇和语气变化
- **视觉情绪**: 结合画面氛围、人物表情传达的情感
- **整体情绪**: 综合语音和视觉信息判断整体情感氛围
- **隐含情绪**: 从描述的情境和内容中推断隐含的情感状态

# **🔍 第三优先级：其他物体和场景**
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
- **其他物体**: 在完成品牌相关物体识别后，补充识别其他相关物体
- **场景环境**: 理解和描述语音中提及或视觉中展现的场景环境

# **核心指令**
- **语音优先**: 主要依赖"语音转录文本"进行判断。
- **品牌识别优先级最高**: 发现核心品牌提及时必须准确识别
- **品牌相关内容重点关注**: 营养成分、产品功效等要特别留意
- **情绪定位很重要**: 准确判断语音和视觉传达的情感状态
- **补充分析**: 你的目标是补充或修正初步的视觉分析，特别是那些在语音中才明确体现的信息（如具体功效、用户反馈等）。

# **已知信息**
## 初步视觉分析摘要
{visual_summary}

## 语音转录文本
"{transcription}"

# **输出格式** (严格遵守，只需输出补充信息)
- **Object_Supplement**: [语音中提到的、可补充的物体信息，优先识别品牌相关物体]
- **Sence_Supplement**: [语音中提到的、可补充的场景信息]
- **Emotion_Supplement**: [语音中提到的、可补充的情绪信息]
- **Brand_Elements**: [只能来自上述品牌铁律中提到的列表]
- **Confidence**: [0.0-1.0]

# **开始分析**
请根据上述所有信息和优先级顺序，开始你的补充分析。
"""
        except Exception as e:
            logger.error(f"构建目标性分析Prompt失败: {e}")
            return f"请基于以下文本进行补充分析：{transcription}"
    
    def _audio_fallback_analysis(self, video_path: str, tag_language: str = "中文") -> Dict[str, Any]:
        """语音转录保底分析机制"""
        try:
            logger.info("🎤 开始语音转录分析...")
            
            # 步骤1：提取音频并转录
            transcription = self._extract_and_transcribe_audio(video_path)
            
            if not transcription or transcription.strip() == "":
                logger.warning("🎤 语音转录结果为空")
                return self._get_default_result("语音转录结果为空")
            
            logger.info(f"🎤 转录成功，文本长度: {len(transcription)} 字符")
            
            # 步骤2：使用DeepSeek分析转录文本
            audio_analysis = self._analyze_transcription_with_deepseek(transcription, tag_language)
            
            if audio_analysis.get("success"):
                audio_analysis["analysis_method"] = "audio_only"
                audio_analysis["transcription"] = transcription
                logger.info("🎤 语音转录分析成功")
                return audio_analysis
            else:
                logger.warning("🎤 DeepSeek文本分析失败")
                return self._get_default_result("DeepSeek文本分析失败")
                
        except Exception as e:
            logger.error(f"语音转录保底分析失败: {str(e)}")
            return self._get_default_result(f"语音转录分析失败: {str(e)}")
    
    def _targeted_audio_fallback_analysis(self, video_path: str, visual_result: Dict[str, Any], tag_language: str = "中文") -> Dict[str, Any]:
        """
        🎯 针对性语音转录保底分析 - 只补强visual缺失字段
        """
        try:
            logger.info("🎯 开始针对性语音转录分析...")
            
            # 步骤1：提取音频并转录
            transcription = self._extract_and_transcribe_audio(video_path)
            
            if not transcription or transcription.strip() == "":
                logger.warning("🎤 语音转录结果为空")
                return visual_result  # 返回原始visual结果
            
            logger.info(f"🎤 转录成功，文本长度: {len(transcription)} 字符")
            
            # 步骤2：使用针对性DeepSeek分析
            audio_supplement = self._targeted_deepseek_analysis(transcription, visual_result, tag_language)
            
            if audio_supplement.get("success"):
                # 步骤3：智能合并结果
                merged_result = self._merge_targeted_results(visual_result, audio_supplement)
                merged_result["analysis_method"] = "visual_targeted_audio_fusion"
                merged_result["transcription"] = transcription
                logger.info("🎯 针对性视觉+语音融合完成")
                return merged_result
            else:
                logger.warning("🎤 针对性DeepSeek分析失败，返回visual结果")
                return visual_result
                
        except Exception as e:
            logger.error(f"针对性语音转录分析失败: {str(e)}")
            return visual_result
    
    def _targeted_deepseek_analysis(self, transcription: str, visual_result: Dict[str, Any], tag_language: str) -> Dict[str, Any]:
        """
        🎯 针对性DeepSeek分析 - 只分析缺失字段
        """
        try:
            if not self.deepseek_analyzer.is_available():
                logger.warning("🤖 DeepSeek分析器不可用")
                return {"success": False}
            
            logger.info("🎯 开始针对性DeepSeek音频分析...")
            
            # 生成针对性prompt
            targeted_prompt = self._get_targeted_analysis_prompt(transcription, visual_result)
            
            # 使用DeepSeek分析器
            messages = [
                {"role": "system", "content": "你是专业的母婴产品语音内容分析师，专门补充visual分析的缺失字段。只分析指定的缺失字段，不要重复已有结果。"},
                {"role": "user", "content": targeted_prompt}
            ]
            
            response = self.deepseek_analyzer._chat_completion(messages)
            
            if response and "choices" in response and response["choices"]:
                result_text = response["choices"][0].get("message", {}).get("content", "")
                logger.info(f"🎯 针对性DeepSeek分析结果: {result_text}")
                
                # 解析针对性分析结果
                parsed_result = self._parse_targeted_deepseek_analysis(result_text, visual_result)
                
                if parsed_result:
                    parsed_result["success"] = True
                    return parsed_result
                else:
                    return {"success": False}
            else:
                logger.warning("🤖 针对性DeepSeek API调用失败")
                return {"success": False}
                
        except Exception as e:
            logger.error(f"针对性DeepSeek分析失败: {str(e)}")
            return {"success": False}
    
    def _parse_targeted_deepseek_analysis(self, analysis_text: str, visual_result: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        🎯 解析针对性DeepSeek分析结果 - 只处理缺失字段
        """
        try:
            result = {
                'object': visual_result.get('object', ''),  # 保留visual结果
                'scene': visual_result.get('scene', ''),
                'emotion': visual_result.get('emotion', ''),
                'brand_elements': visual_result.get('brand_elements', ''),
                'confidence': visual_result.get('confidence', 0.7)
            }
            
            logger.info(f"🎯 开始解析针对性分析结果:")
            logger.info(f"原始文本: {analysis_text}")
            
            # 清理函数
            def clean_field_value(value):
                if not value:
                    return ''
                cleaned = str(value).strip()
                # 移除常见的无意义值
                if cleaned in ['无', '不确定', '解析失败', 'N/A', 'null', 'None', '']:
                    return ''
                # 移除方括号等
                cleaned = cleaned.replace('[', '').replace(']', '').replace('**', '')
                return cleaned.strip()
            
            # 逐行处理，只更新有内容的字段
            lines = analysis_text.strip().split('\n')
            
            for line in lines:
                line = line.strip()
                if not line:
                    continue
                    
                logger.info(f"处理行: '{line}'")
                
                # 解析各种格式的字段
                if line.lower().startswith('object_supplement:') or line.lower().startswith('- **object_supplement**:'):
                    # 针对性分析补充格式
                    raw_value = line.split(':', 1)[1].strip() if ':' in line else ''
                    new_value = clean_field_value(raw_value)
                    if new_value and not visual_result.get('object'):
                        result['object'] = new_value
                        logger.info(f"🎯 补充object: '{new_value}'")
                        
                elif line.lower().startswith('object:') and not visual_result.get('object'):
                    raw_value = line[7:].strip()
                    new_value = clean_field_value(raw_value)
                    if new_value:  # 只有非空时才更新
                        result['object'] = new_value
                        logger.info(f"🎯 补充object: '{new_value}'")
                
                elif line.lower().startswith('scene_supplement:') or line.lower().startswith('- **scene_supplement**:'):
                    raw_value = line.split(':', 1)[1].strip() if ':' in line else ''
                    new_value = clean_field_value(raw_value)
                    if new_value and not visual_result.get('scene'):
                        result['scene'] = new_value
                        logger.info(f"🎯 补充scene: '{new_value}'")
                    
                elif line.lower().startswith('scene:') and not visual_result.get('scene'):
                    raw_value = line[6:].strip()
                    new_value = clean_field_value(raw_value)
                    if new_value:
                        result['scene'] = new_value
                        logger.info(f"🎯 补充scene: '{new_value}'")
                
                elif line.lower().startswith('emotion_supplement:') or line.lower().startswith('- **emotion_supplement**:'):
                    raw_value = line.split(':', 1)[1].strip() if ':' in line else ''
                    new_value = clean_field_value(raw_value)
                    if new_value and not visual_result.get('emotion'):
                        result['emotion'] = new_value
                        logger.info(f"🎯 补充emotion: '{new_value}'")
                    
                elif line.lower().startswith('emotion:') and not visual_result.get('emotion'):
                    raw_value = line[8:].strip()
                    new_value = clean_field_value(raw_value)
                    if new_value:
                        result['emotion'] = new_value
                        logger.info(f"🎯 补充emotion: '{new_value}'")
                    
                elif line.lower().startswith('brand_elements:') or line.lower().startswith('- **brand_elements**:'):
                    # 🔧 修复：安全地提取brand_elements的值
                    if '- **brand_elements**:' in line.lower():
                        raw_value = line.split(':', 1)[1].strip() if ':' in line else ''
                    else:
                        raw_value = line[15:].strip()
                    
                    new_value = clean_field_value(raw_value)
                    # 🔧 重要修复：如果visual是"疑似品牌要素"或空，且DeepSeek有正确识别，则覆盖
                    visual_brand = visual_result.get('brand_elements', '')
                    if new_value and (not visual_brand or visual_brand in ['疑似品牌要素', '无', '']):
                        # 🚨 严格品牌过滤：只接受配置列表中的品牌
                        try:
                            from utils.keyword_config import get_brands
                            allowed_brands = [b.lower() for b in get_brands()]
                        except Exception as e:
                            logger.error(f"无法加载品牌配置: {e}")
                            allowed_brands = ['illuma', '启赋', '惠氏', '蕴淳', 'wyeth', 'a2', 'atwo', 'hmo']
                        
                        # 过滤并验证品牌
                        detected_brands = [b.strip() for b in new_value.split(',') if b.strip()]
                        valid_brands = []
                        for brand in detected_brands:
                            if brand.lower() in allowed_brands:
                                valid_brands.append(brand)
                            else:
                                logger.debug(f"🚫 [品牌过滤] 已移除不在配置中的品牌: '{brand}'")
                        
                        if valid_brands:
                            result['brand_elements'] = ','.join(valid_brands)
                            logger.info(f"🎯 覆盖brand_elements: '{result['brand_elements']}' (替换了: '{visual_brand}')")
                        else:
                            result['brand_elements'] = ''
                            logger.info(f"🎯 品牌过滤后为空，清除brand_elements")
                        
                elif line.lower().startswith('confidence:'):
                    confidence_text = line[11:].strip()
                    try:
                        import re
                        confidence_match = re.search(r'([0-9.]+)', confidence_text)
                        if confidence_match:
                            result['confidence'] = float(confidence_match.group(1))
                    except:
                        pass  # 保持原有confidence
            
            # 更新all_tags
            all_tags = []
            for value in [result['object'], result['scene'], result['emotion'], result['brand_elements']]:
                if value:
                    tags = [tag.strip() for tag in value.split(',') if tag.strip()]
                    for tag in tags:
                        cleaned_tag = clean_field_value(tag)
                        if cleaned_tag and cleaned_tag not in all_tags:
                            all_tags.append(cleaned_tag)
            
            result['all_tags'] = all_tags
            
            logger.info(f"🎯 针对性分析完成:")
            logger.info(f"   物体: '{result['object']}'")
            logger.info(f"   场景: '{result['scene']}'")
            logger.info(f"   情绪: '{result['emotion']}'")
            logger.info(f"   品牌: '{result['brand_elements']}'")
            
            return result
            
        except Exception as e:
            logger.error(f"解析针对性DeepSeek结果失败: {str(e)}")
            return None
    
    def _merge_targeted_results(self, visual_result: Dict[str, Any], audio_supplement: Dict[str, Any]) -> Dict[str, Any]:
        """
        🎯 合并针对性结果 - 高效融合
        """
        try:
            logger.info("🎯 开始合并针对性分析结果...")
            
            # 以visual为基础，用audio补充
            merged_result = visual_result.copy()
            
            # 只覆盖visual中的空字段
            for field in ['object', 'scene', 'emotion', 'brand_elements']:
                visual_value = visual_result.get(field, '')
                audio_value = audio_supplement.get(field, '')
                
                # 如果visual为空且audio有值，则使用audio的值
                if not visual_value and audio_value:
                    merged_result[field] = audio_value
                    logger.info(f"🎯 字段补充: {field} = '{audio_value}'")
            
            # 合并all_tags
            visual_tags = visual_result.get('all_tags', [])
            audio_tags = audio_supplement.get('all_tags', [])
            merged_tags = list(set(visual_tags + audio_tags))  # 去重
            merged_result['all_tags'] = merged_tags
            
            # 更新质量分 - 如果有补充，质量分提升
            supplemented_count = sum(1 for field in ['object', 'scene', 'emotion', 'brand_elements'] 
                                   if not visual_result.get(field) and audio_supplement.get(field))
            
            if supplemented_count > 0:
                original_quality = visual_result.get('quality_score', 0.5)
                boost = supplemented_count * 0.1  # 每补充一个字段提升0.1
                merged_result['quality_score'] = min(1.0, original_quality + boost)
                logger.info(f"🎯 质量分提升: {original_quality:.2f} → {merged_result['quality_score']:.2f} (补充了{supplemented_count}个字段)")
            
            merged_result['success'] = True
            merged_result['targeted_supplement_count'] = supplemented_count
            
            return merged_result
            
        except Exception as e:
            logger.error(f"针对性结果合并失败: {str(e)}")
            return visual_result  # 失败时返回original visual结果
    
    def _extract_and_transcribe_audio(self, video_path: str) -> str:
        """使用DashScopeAudioAnalyzer提取音频并转录"""
        try:
            if not self.audio_analyzer.is_available():
                logger.warning("🎤 DashScope音频分析器不可用")
                return ""
            
            logger.info(f"🎤 开始转录视频音频: {video_path}")
            
            # 使用音频分析器进行转录 - 🔧 启用默认热词优化
            result = self.audio_analyzer.transcribe_video(
                video_path=video_path,
                extract_audio_first=True,
                preset_vocabulary_id="default"  # 🔧 使用默认热词ID
            )
            
            if result.get("success") and result.get("transcript"):
                transcription = result["transcript"]
                logger.info(f"🎤 转录成功，文本长度: {len(transcription)} 字符")
                return transcription
            else:
                error_msg = result.get("error", "未知错误")
                logger.warning(f"🎤 转录失败: {error_msg}")
                return ""
                
        except Exception as e:
            logger.error(f"音频转录失败: {str(e)}")
            return ""
    
    def _analyze_transcription_with_deepseek(self, transcription: str, tag_language: str) -> Dict[str, Any]:
        """使用DeepSeekAnalyzer分析转录文本（专为语音内容定制）"""
        try:
            if not self.deepseek_analyzer.is_available():
                logger.warning("🤖 DeepSeek分析器不可用，使用简单文本分析")
                return self._simple_text_analysis(transcription)
            
            logger.info("🤖 开始DeepSeek音频转录文本分析...")
                
            # 构建音频转录分析提示词（使用专门的语音分析Prompt）
            try:
                from utils.keyword_config import get_deepseek_audio_prompt
                analysis_prompt = get_deepseek_audio_prompt()
                
                # 在Prompt中添加实际转录文本
                analysis_prompt += f"\n\n📝 需要分析的转录文本：\n{transcription}"
                
            except Exception as e:
                logger.warning(f"无法导入DeepSeek语音prompt生成逻辑，使用兜底配置: {e}")
                analysis_prompt = self._get_fallback_audio_prompt() + f"\n\n转录文本：{transcription}"

            # 使用DeepSeek分析器
            messages = [
                {"role": "system", "content": "你是专业的母婴产品语音内容分析师，专门从语音转录文本中提取语义信息。请基于转录内容的语义理解进行分析，严格从业务词表中选择匹配的标签。"},
                {"role": "user", "content": analysis_prompt}
            ]
            
            response = self.deepseek_analyzer._chat_completion(messages)
            
            if response and "choices" in response and response["choices"]:
                result_text = response["choices"][0].get("message", {}).get("content", "")
                logger.info(f"🤖 DeepSeek音频分析结果: {result_text}")
                
                # 解析DeepSeek的分析结果
                parsed_result = self._parse_deepseek_analysis(result_text)
                
                if parsed_result:
                    parsed_result["success"] = True
                    return parsed_result
                else:
                    return self._simple_text_analysis(transcription)
            else:
                logger.warning("🤖 DeepSeek API调用失败")
                return self._simple_text_analysis(transcription)
                    
        except Exception as e:
            logger.error(f"DeepSeek文本分析失败: {str(e)}")
            return self._simple_text_analysis(transcription)
    
    def _parse_deepseek_analysis(self, analysis_text: str) -> Optional[Dict[str, Any]]:
        """
        解析DeepSeek返回的文本结果，并进行严格的后处理过滤。
        """
        # 🔧 重用Qwen的格式清理函数
        def clean_field_value(value: str) -> str:
            """清理字段值，确保输出简洁的单词短语"""
            if not value:
                return ''
            
            # 基础清理
            cleaned = value.strip()
            
            # 🔧 重要修复：移除字段标识符干扰
            field_markers = ['object:', 'scene:', 'emotion:', 'brand_elements:', 'confidence:']
            for marker in field_markers:
                if marker in cleaned:
                    # 如果在开头，移除它
                    if cleaned.startswith(marker):
                        cleaned = cleaned[len(marker):].strip()
                    else:
                        # 如果在中间，只取前面部分
                        cleaned = cleaned.split(marker)[0].strip()
            
            # 去除Markdown和特殊符号
            cleaned = cleaned.replace('**', '').replace('*', '')
            cleaned = cleaned.replace('- ', '').replace('+ ', '')
            cleaned = cleaned.replace('# ', '').replace('[', '').replace(']', '')
            cleaned = cleaned.replace('(', '').replace(')', '')
            cleaned = cleaned.replace('"', '').replace("'", '')
            cleaned = cleaned.replace('：', ':').replace('。', '').replace('；', '')
            
            # 去除"疑似"等词汇
            cleaned = cleaned.replace('疑似', '').replace('可能', '')
            cleaned = cleaned.replace('应该', '').replace('似乎', '')
            
            # 去除长句描述（超过20字的内容截取关键词）
            if len(cleaned) > 20:
                # 提取关键词（简单处理）
                keywords = []
                key_terms = ['奶粉', '奶瓶', '启赋', 'Wyeth', 'A2', 'HMO', 'DHA', 
                           '厨房', '客厅', '温馨', '专业', '关爱', '品牌']
                for term in key_terms:
                    if term in cleaned:
                        keywords.append(term)
                cleaned = ','.join(keywords[:3]) if keywords else cleaned[:10]
            
            # 去除多余空格和标点
            cleaned = re.sub(r'\s+', ' ', cleaned).strip()
            cleaned = re.sub(r'[,，]+', ',', cleaned)
            cleaned = cleaned.strip(',')
            
            # 过滤无意义内容
            meaningless = ['无', '不确定', '画面不清晰', '解析失败', '语音信息不足', 
                          '', 'none', 'n/a', '不明确', '转录误差', '相关']
            if cleaned.lower() in meaningless:
                return ''
            
            # 🔧 新增：过滤纯数字内容（confidence值误入其他字段）
            if re.match(r'^[0-9.]+$', cleaned):
                return ''
            
            # 🔧 新增：过滤过短的无意义内容（1-2字符）
            if len(cleaned) <= 2 and cleaned.lower() in ['0', '1', '2', '3', '4', '5', '6', '7', '8', '9', '.']:
                return ''
            
            return cleaned
        
        try:
            result = {
                'object': '',
                'scene': '', 
                'emotion': '',
                'brand_elements': '',
                'confidence': 0.7
            }
            
            logger.info(f"🎯 开始解析DeepSeek分析文本:")
            logger.info(f"原始文本: {analysis_text}")
            
            # 🔧 全新的解析策略：逐行处理，避免跨行匹配问题
            lines = analysis_text.strip().split('\n')
            
            for line in lines:
                line = line.strip()
                if not line:
                    continue
                    
                logger.info(f"处理行: '{line}'")
                
                # 🔧 修复：处理竖线分隔符格式和行内格式
                # 检查是否是竖线分隔的单行格式：object: ... | scene: ... | emotion: ... | brand: ...
                if '|' in line and any(marker in line.lower() for marker in ['object:', 'scene:', 'emotion:', 'brand']):
                    # 处理竖线分隔格式
                    segments = line.split('|')
                    for segment in segments:
                        segment = segment.strip()
                        if segment.lower().startswith('object:'):
                            raw_value = segment[7:].strip()
                            result['object'] = clean_field_value(raw_value)
                            logger.info(f"[竖线格式] 提取object: '{raw_value}' -> '{result['object']}'")
                        elif segment.lower().startswith('scene:'):
                            raw_value = segment[6:].strip()
                            result['scene'] = clean_field_value(raw_value)
                            logger.info(f"[竖线格式] 提取scene: '{raw_value}' -> '{result['scene']}'")
                        elif segment.lower().startswith('emotion:'):
                            raw_value = segment[8:].strip()
                            result['emotion'] = clean_field_value(raw_value)
                            logger.info(f"[竖线格式] 提取emotion: '{raw_value}' -> '{result['emotion']}'")
                        elif segment.lower().startswith('brand:') or segment.lower().startswith('brand_elements:'):
                            if segment.lower().startswith('brand:'):
                                raw_value = segment[6:].strip()
                            else:
                                raw_value = segment[15:].strip()
                            cleaned_brand = clean_field_value(raw_value)
                            if cleaned_brand:
                                brand_parts = [part.strip() for part in cleaned_brand.split(',')]
                                clean_parts = [part for part in brand_parts if part and not re.match(r'^[0-9]+\.?[0-9]*$', part)]
                                result['brand_elements'] = ','.join(clean_parts) if clean_parts else ''
                            else:
                                result['brand_elements'] = ''
                            logger.info(f"[竖线格式] 提取brand: '{raw_value}' -> '{result['brand_elements']}'")
                
                # 标准单行格式处理
                elif line.lower().startswith('object:'):
                    raw_value = line[7:].strip()  # 移除 "object:" 
                    # 移除可能的竖线后缀
                    if '|' in raw_value:
                        raw_value = raw_value.split('|')[0].strip()
                    result['object'] = clean_field_value(raw_value)
                    logger.info(f"提取object: '{raw_value}' -> '{result['object']}'")
                    
                elif line.lower().startswith('scene:'):
                    raw_value = line[6:].strip()  # 移除 "scene:"
                    if '|' in raw_value:
                        raw_value = raw_value.split('|')[0].strip()
                    result['scene'] = clean_field_value(raw_value)
                    logger.info(f"提取scene: '{raw_value}' -> '{result['scene']}'")
                    
                elif line.lower().startswith('emotion:'):
                    raw_value = line[8:].strip()  # 移除 "emotion:"
                    if '|' in raw_value:
                        raw_value = raw_value.split('|')[0].strip()
                    result['emotion'] = clean_field_value(raw_value)
                    logger.info(f"提取emotion: '{raw_value}' -> '{result['emotion']}'")
                    
                elif line.lower().startswith('brand_elements:') or line.lower().startswith('brand:'):
                    if line.lower().startswith('brand:'):
                        raw_value = line[6:].strip()
                    else:
                        raw_value = line[15:].strip()  # 移除 "brand_elements:"
                    # 移除可能的竖线后缀
                    if '|' in raw_value:
                        raw_value = raw_value.split('|')[0].strip()
                    # 🔧 特殊处理brand_elements：过滤数字污染
                    cleaned_brand = clean_field_value(raw_value)
                    if cleaned_brand:
                        # 进一步清理：移除纯数字片段
                        brand_parts = [part.strip() for part in cleaned_brand.split(',')]
                        clean_parts = [part for part in brand_parts if part and not re.match(r'^[0-9]+\.?[0-9]*$', part)]
                        result['brand_elements'] = ','.join(clean_parts) if clean_parts else ''
                    else:
                        result['brand_elements'] = ''
                    logger.info(f"提取brand_elements: '{raw_value}' -> '{result['brand_elements']}'")
                    
                elif line.lower().startswith('confidence:'):
                    confidence_text = line[11:].strip()  # 移除 "confidence:"
                    if '|' in confidence_text:
                        confidence_text = confidence_text.split('|')[0].strip()
                    try:
                        # 提取数字部分
                        confidence_match = re.search(r'([0-9.]+)', confidence_text)
                        if confidence_match:
                            result['confidence'] = float(confidence_match.group(1))
                            logger.info(f"提取confidence: '{confidence_text}' -> {result['confidence']}")
                    except:
                        result['confidence'] = 0.7
            
            # 🔧 创建all_tags - 只包含有意义的内容
            all_tags = []
            for value in [result['object'], result['scene'], result['emotion'], result['brand_elements']]:
                if value:  # 只要不为空就处理
                    # 分割逗号分隔的标签
                    tags = [tag.strip() for tag in value.split(',') if tag.strip()]
                    for tag in tags:
                        cleaned_tag = clean_field_value(tag)
                        if cleaned_tag:  # 清理后不为空就添加
                            all_tags.append(cleaned_tag)
            
            # 去重并过滤
            result['all_tags'] = list(set(filter(None, all_tags)))
            
            # 🚨 最后一步：严格过滤品牌元素，只保留配置中的品牌
            try:
                from utils.keyword_config import get_brands
                allowed_brands = [b.lower() for b in get_brands()]
            except Exception as e:
                logger.error(f"无法加载品牌配置，使用默认列表: {e}")
                allowed_brands = ['illuma', '启赋', '惠氏', '蕴淳', 'wyeth', 'a2', 'atwo', 'hmo']
            
            if result['brand_elements']:
                detected_brands_raw = result['brand_elements']
                detected_brands_list = [b.strip() for b in detected_brands_raw.split(',') if b.strip()]
                
                final_brands = []
                for brand in detected_brands_list:
                    # 必须是配置列表中的品牌（忽略大小写）
                    if brand.lower() in allowed_brands:
                        final_brands.append(brand)
                    else:
                        logger.debug(f"🚫 [品牌过滤] 已移除不在配置中的品牌: '{brand}'")
                
                # 去重并更新
                if final_brands:
                    result['brand_elements'] = ','.join(list(dict.fromkeys(final_brands)))
                else:
                    result['brand_elements'] = ''
            
            logger.info(f"🎯 DeepSeek最终解析结果:")
            logger.info(f"   物体: '{result['object']}'")
            logger.info(f"   场景: '{result['scene']}'")
            logger.info(f"   情绪: '{result['emotion']}'")
            logger.info(f"   品牌: '{result['brand_elements']}'")
            logger.info(f"   置信度: {result['confidence']}")
            logger.info(f"   标签: {result['all_tags']}")
            
            return result if any(v for v in result.values() if v not in ['', 0.7, []]) else None
            
        except Exception as e:
            logger.error(f"解析DeepSeek结果失败: {str(e)}")
            return None
    
    def _simple_text_analysis(self, text: str) -> Dict[str, Any]:
        """简单文本分析（关键词匹配）- 统一从matching_rules.json提取词汇"""
        try:
            # 🎯 核心改进：直接从matching_rules.json提取所有词汇
            all_objects = []
            all_scenes = []
            all_emotions = []
            
            # 品牌关键词从配置获取
            try:
                from utils.keyword_config import get_brands
                brands = get_brands()
                brand_keywords = brands if brands else ["启赋", "Wyeth", "illuma", "A2", "ATWO", "HMO", "DHA"]
            except Exception as e:
                logger.warning(f"无法获取品牌列表: {e}")
                brand_keywords = ["启赋", "Wyeth", "illuma", "A2", "ATWO", "HMO", "DHA"]
            
            found_objects = [kw for kw in all_objects if kw in text]
            found_scenes = [kw for kw in all_scenes if kw in text]
            found_emotions = [kw for kw in all_emotions if kw in text]
            found_brands = [kw for kw in brand_keywords if kw in text]
            
            result = {
                'object': ', '.join(found_objects) if found_objects else '',
                'scene': ', '.join(found_scenes) if found_scenes else '',
                'emotion': ', '.join(found_emotions) if found_emotions else '',
                'brand_elements': ', '.join(found_brands) if found_brands else '',
                'confidence': 0.6 if any([found_objects, found_scenes, found_emotions, found_brands]) else 0.3,
                'all_tags': found_objects + found_scenes + found_emotions + found_brands,
                'success': True
            }
            
            return result
            
        except Exception as e:
            logger.error(f"简单文本分析失败: {e}")
            return {
                'object': '',
                'scene': '',
                'emotion': '',
                'brand_elements': '',
                'confidence': 0.3,
                'all_tags': [],
                'success': False
            }
    
    def _merge_visual_audio_results(self, visual_result: Dict[str, Any], audio_result: Dict[str, Any]) -> Dict[str, Any]:
        """融合视觉和语音分析结果"""
        try:
            logger.info("🎯🎤 开始融合视觉和语音分析结果...")
            
            # 基于质量分的融合策略
            visual_weight = visual_result.get('quality_score', 0.3)
            audio_weight = 0.7  # 语音转录通常更可靠
            
            # 🔧 修复：标准化字段值处理函数
            def clean_and_split_value(value):
                """清理并分割字段值"""
                if not value or value in ['无', '不确定', '解析失败', '']:
                    return []
                
                # 清理多余符号 
                cleaned = str(value).strip()
                # 移除方括号和特殊符号
                cleaned = cleaned.replace('[', '').replace(']', '').replace('**', '')
                # 分割并清理
                parts = []
                for part in cleaned.split(','):
                    part = part.strip()
                    if part and part not in ['无', '不确定', '解析失败']:
                        parts.append(part)
                return parts
            
            # 🔧 修复：融合各字段
            merged_result = {}
            
            for field in ['object', 'scene', 'emotion', 'brand_elements']:
                visual_value = visual_result.get(field, '')
                audio_value = audio_result.get(field, '')
                
                # 清理并合并非空值
                visual_parts = clean_and_split_value(visual_value)
                audio_parts = clean_and_split_value(audio_value)
                
                # 合并并去重
                all_parts = visual_parts + audio_parts
                unique_parts = []
                for part in all_parts:
                    if part not in unique_parts:
                        unique_parts.append(part)
                
                # 🔧 格式化输出：确保与视觉分析格式一致
                if unique_parts:
                    merged_result[field] = unique_parts[0] if len(unique_parts) == 1 else ', '.join(unique_parts)
                else:
                    merged_result[field] = ''  # 保持空值而不是"不确定"
            
            # 🔧 修复：融合质量分和置信度
            visual_conf = visual_result.get('confidence', 0.3)
            audio_conf = audio_result.get('confidence', 0.7)
            merged_confidence = visual_weight * visual_conf + audio_weight * audio_conf
            
            merged_result['confidence'] = round(merged_confidence, 2)
            merged_result['quality_score'] = round(merged_confidence, 2)
            
            # 🔧 修复：融合all_tags - 确保格式一致
            visual_tags = visual_result.get('all_tags', [])
            audio_tags = audio_result.get('all_tags', [])
            
            # 清理和合并标签
            all_tags_raw = visual_tags + audio_tags
            clean_tags = []
            for tag in all_tags_raw:
                if isinstance(tag, str):
                    # 清理标签
                    clean_tag = tag.strip().replace('[', '').replace(']', '').replace('**', '')
                    if clean_tag and clean_tag not in ['无', '不确定', '解析失败'] and clean_tag not in clean_tags:
                        clean_tags.append(clean_tag)
            
            merged_result['all_tags'] = clean_tags
            
            # 🔧 其他必需字段
            merged_result['success'] = True
            merged_result['analysis_method'] = 'visual_audio_fusion'
            merged_result['transcription'] = audio_result.get('transcription', '')
            
            logger.info(f"🎯🎤 视觉+语音融合完成")
            logger.info(f"   物体: {merged_result['object']}")
            logger.info(f"   场景: {merged_result['scene']}")
            logger.info(f"   情绪: {merged_result['emotion']}")
            logger.info(f"   品牌: {merged_result['brand_elements']}")
            logger.info(f"   质量分: {merged_result['quality_score']}")
            logger.info(f"   标签数: {len(merged_result['all_tags'])}")
            
            return merged_result
            
        except Exception as e:
            logger.error(f"结果融合失败: {str(e)}")
            # 如果融合失败，返回音频结果（通常更可靠）
            fallback_result = audio_result if audio_result.get('success') else visual_result
            fallback_result['analysis_method'] = 'fallback_audio' if audio_result.get('success') else 'fallback_visual'
            return fallback_result 
    
    def _detect_face_close_up(self, analysis_result: Dict[str, Any], video_path: str) -> bool:
        """
        🎯 检测人脸特写片段
        
        Args:
            analysis_result: 视觉分析结果
            video_path: 视频文件路径
            
        Returns:
            bool: 是否为人脸特写片段
        """
        try:
            # 加载配置
            try:
                from config.factory_config import VISUAL_ANALYSIS_CONFIG
                detection_config = VISUAL_ANALYSIS_CONFIG.get("face_close_up_detection", {})
                
                # 检查是否启用人脸特写检测
                if not detection_config.get("enabled", True):
                    return False
                
                face_close_up_indicators = detection_config.get("keywords", [
                    '人脸', '面部', '头像', '特写', '肖像', '脸部',
                    '眼睛', '嘴唇', '鼻子', '面孔', '头部特写'
                ])
                face_area_threshold = detection_config.get("face_area_threshold", 0.3)
                
            except ImportError:
                # 配置不可用时使用默认值
                face_close_up_indicators = [
                    '人脸', '面部', '头像', '特写', '肖像', '脸部',
                    '眼睛', '嘴唇', '鼻子', '面孔', '头部特写'
                ]
                face_area_threshold = 0.3
            
            # 方法1: 基于标签内容检测
            all_tags = analysis_result.get('all_tags', [])
            object_tags = analysis_result.get('object', '')
            scene_tags = analysis_result.get('scene', '')
            
            # 检查标签是否主要包含人脸特写相关内容
            all_text = f"{' '.join(all_tags)} {object_tags} {scene_tags}".lower()
            
            face_indicators_count = 0
            for indicator in face_close_up_indicators:
                if indicator in all_text:
                    face_indicators_count += 1
            
            # 检查场景缺失情况（人脸特写通常缺乏场景信息）
            scene_missing = not scene_tags or scene_tags in ['', '无', '不确定']
            
            # 检查物体标签是否主要是人脸相关
            face_dominant = face_indicators_count >= 2 and scene_missing
            
            if face_dominant:
                logger.info(f"🚫 基于标签检测到人脸特写: 人脸指标{face_indicators_count}个，场景缺失: {scene_missing}")
                return True
            
            # 方法2: 基于画面分析检测（启发式规则）
            # 如果物体标签很少且主要是人相关，而场景为空，可能是特写
            objects = object_tags.split(',') if object_tags else []
            person_related = ['人', '妈妈', '宝宝', '婴儿', '母亲', '父亲', '家长']
            
            if len(objects) <= 2 and scene_missing:
                person_objects = [obj for obj in objects if any(pr in obj for pr in person_related)]
                if len(person_objects) >= len(objects) * 0.8:  # 80%以上是人相关
                    logger.info(f"🚫 基于物体-场景比例检测到人脸特写: 人物对象{len(person_objects)}/{len(objects)}")
                    return True
            
            # 方法3: 基于视频帧检测（可选，需要OpenCV）
            frame_based_detection = self._detect_face_close_up_by_frames(video_path, face_area_threshold)
            if frame_based_detection:
                logger.info(f"🚫 基于视频帧检测到人脸特写")
                return True
            
            return False
            
        except Exception as e:
            logger.warning(f"人脸特写检测失败: {str(e)}")
            return False
    
    def _detect_face_close_up_by_frames(self, video_path: str, face_area_threshold: float = 0.3) -> bool:
        """
        🎯 基于视频帧的人脸特写检测
        
        Args:
            video_path: 视频文件路径
            
        Returns:
            bool: 是否检测到人脸特写
        """
        try:
            import cv2
            
            # 打开视频
            cap = cv2.VideoCapture(video_path)
            if not cap.isOpened():
                return False
            
            # 获取视频基本信息
            frame_count = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
            fps = cap.get(cv2.CAP_PROP_FPS)
            duration = frame_count / fps if fps > 0 else 0
            
            # 如果视频太短或太长，跳过帧级检测
            if duration < 1 or duration > 30:
                cap.release()
                return False
            
            # 采样几帧进行检测
            sample_frames = min(3, frame_count // 10)  # 最多采样3帧
            frame_indices = [i * frame_count // (sample_frames + 1) for i in range(1, sample_frames + 1)]
            
            face_frames = 0
            total_frames_checked = 0
            
            for frame_idx in frame_indices:
                cap.set(cv2.CAP_PROP_POS_FRAMES, frame_idx)
                ret, frame = cap.read()
                
                if not ret:
                    continue
                
                total_frames_checked += 1
                
                # 简单的人脸检测（基于面积占比）
                gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
                height, width = gray.shape
                
                try:
                    # 使用OpenCV的人脸检测器（如果可用）
                    face_cascade = cv2.CascadeClassifier(cv2.data.haarcascades + 'haarcascade_frontalface_default.xml')
                    faces = face_cascade.detectMultiScale(gray, 1.1, 4)
                    
                    # 如果检测到人脸且占比较大，可能是特写
                    for (x, y, w, h) in faces:
                        face_area = w * h
                        frame_area = width * height
                        face_ratio = face_area / frame_area
                        
                        # 如果人脸占画面达到配置阈值以上，认为是特写
                        if face_ratio > face_area_threshold:
                            face_frames += 1
                            break
                            
                except Exception:
                    # 如果人脸检测失败，使用简单的启发式方法
                    # 检查画面中央区域的变化
                    center_region = gray[height//4:3*height//4, width//4:3*width//4]
                    if center_region.std() > 50:  # 中央区域变化较大，可能有人脸
                        face_frames += 1
            
            cap.release()
            
            # 如果一半以上的帧都检测到疑似人脸特写
            if total_frames_checked > 0 and face_frames / total_frames_checked >= 0.5:
                return True
            
            return False
            
        except Exception as e:
            logger.warning(f"基于帧的人脸检测失败: {str(e)}")
            return False
    
    def _optimize_for_short_video(self, video_path: str, original_frame_rate: float) -> Dict[str, Any]:
        """
        🎯 短视频智能优化：根据文件大小和时长动态调整分析参数
        
        Args:
            video_path: 视频文件路径
            original_frame_rate: 原始帧率
            
        Returns:
            优化后的分析参数
        """
        try:
            # 获取文件大小（MB）
            file_size_mb = os.path.getsize(video_path) / (1024 * 1024)
            
            # 🎯 过滤过小文件
            if file_size_mb < self.short_video_config['min_file_size_mb']:
                logger.info(f"🚫 文件过小，跳过处理: {file_size_mb:.2f}MB < {self.short_video_config['min_file_size_mb']}MB")
                return {
                    "frame_rate": 0,
                    "quality_threshold": 0,
                    "should_skip": True,
                    "reason": "文件过小"
                }
            
            # 获取视频时长
            video_info = self._extract_video_info(video_path)
            duration_sec = video_info.get('duration', 0)
            
            # 初始化优化参数
            optimized_frame_rate = original_frame_rate
            optimized_quality_threshold = self.quality_config['min_quality_threshold']
            
            # 判断是否需要优化
            is_small_file = file_size_mb < self.short_video_config['file_size_threshold_mb']
            is_short_duration = duration_sec < self.short_video_config['duration_threshold_sec']
            
            if is_small_file or is_short_duration:
                # 短视频优化策略
                optimized_frame_rate = min(
                    original_frame_rate * self.short_video_config['frame_rate_boost'],
                    self.short_video_config['max_frame_rate']
                )
                optimized_quality_threshold = max(
                    self.quality_config['min_quality_threshold'] - self.short_video_config['quality_threshold_reduction'],
                    0.3
                )
                
                logger.info(f"⚡ 短视频优化: {file_size_mb:.2f}MB, {duration_sec:.1f}s -> 帧率{optimized_frame_rate:.1f}, 质量阈值{optimized_quality_threshold:.2f}")
            
            return {
                "frame_rate": optimized_frame_rate,
                "quality_threshold": optimized_quality_threshold,
                "should_skip": False,
                "optimization_applied": is_small_file or is_short_duration,
                "file_size_mb": file_size_mb,
                "duration_sec": duration_sec
            }
            
        except Exception as e:
            logger.error(f"短视频优化失败: {e}")
            return {
                "frame_rate": original_frame_rate,
                "quality_threshold": self.quality_config['min_quality_threshold'],
                "should_skip": False,
                "optimization_applied": False
            }
    
    def _apply_negative_keywords_filter(self, result: Dict[str, Any]) -> Dict[str, Any]:
        """
        🛡️ 升级版反幻觉机制：品牌感知的智能过滤
        
        核心策略：
        1. 有品牌标识 + 奶粉相关 = 真实产品，保留但降低置信度
        2. 无品牌标识 + 奶粉相关 + 负面场景 = 可能误识别，移除
        3. 玩具/游乐场景 + 无品牌 = 完全移除奶粉标签
        
        Args:
            result: 视觉分析结果
            
        Returns:
            智能过滤后的结果
        """
        try:
            # 获取负面关键词配置
            config_manager = get_config_manager()
            keywords_config = config_manager.get_keywords_config()
            
            # 提取核心信息
            brand_elements = str(result.get('brand_elements', '')).strip()
            object_content = str(result.get('object', '')).strip()
            scene_content = str(result.get('scene', '')).strip()
            
            # 🔍 判断是否有明确品牌标识
            has_brand = bool(brand_elements)
            known_brands = ['启赋', 'illuma', 'A2', 'Wyeth', '惠氏', 'HMO', 'DHA']
            has_known_brand = any(brand in brand_elements for brand in known_brands) if has_brand else False
            
            # 🔍 收集所有分析文本用于负面关键词检测
            all_analysis_text = f"{object_content} {scene_content}".lower()
            
            # 🔍 检测负面场景关键词
            features_negatives = keywords_config.get('features_formula', {}).get('negative_keywords', [])
            detected_negatives = []
            for negative_word in features_negatives:
                if negative_word in all_analysis_text:
                    detected_negatives.append(negative_word)
            
            # 🔍 识别奶粉相关标签
            milk_related_keywords = ['奶粉', '奶瓶', '奶粉罐', '配方奶', '配方', '奶粉勺']
            has_milk_objects = any(milk_keyword in object_content for milk_keyword in milk_related_keywords)
            
            # 🔍 识别高风险负面场景（绝对不应该有奶粉的场景）
            high_risk_negatives = ['玩具', '滑梯', '游乐场', '商场', '娱乐', '公园', '户外']
            has_high_risk_scene = any(neg in detected_negatives for neg in high_risk_negatives)
            
            # 🔍 识别中等风险负面场景（可能有奶粉但需要谨慎的场景）
            medium_risk_negatives = ['购物', '运动', '跑步', '散步', '爬行', '跳跃']
            has_medium_risk_scene = any(neg in detected_negatives for neg in medium_risk_negatives)
            
            # 🧠 智能决策逻辑
            if detected_negatives and has_milk_objects:
                filter_action = self._decide_filter_action(
                    has_brand=has_brand,
                    has_known_brand=has_known_brand,
                    has_high_risk_scene=has_high_risk_scene,
                    has_medium_risk_scene=has_medium_risk_scene,
                    detected_negatives=detected_negatives
                )
                
                logger.info(f"🧠 智能过滤决策: {filter_action['action']} (原因: {filter_action['reason']})")
                
                # 执行过滤动作
                result = self._execute_filter_action(result, filter_action, detected_negatives)
            
            return result
            
        except Exception as e:
            logger.error(f"应用智能反幻觉过滤失败: {e}")
            return result
    
    def _decide_filter_action(self, has_brand: bool, has_known_brand: bool, 
                            has_high_risk_scene: bool, has_medium_risk_scene: bool,
                            detected_negatives: List[str]) -> Dict[str, str]:
        """
        🧠 智能决策：根据品牌和场景信息决定过滤策略
        
        Returns:
            Dict with 'action' and 'reason' keys
        """
        
        # 🚨 高风险场景：玩具、游乐场等，无论是否有品牌都要过滤
        if has_high_risk_scene:
            if has_known_brand:
                return {
                    'action': 'reduce_confidence',
                    'reason': f'高风险场景但有知名品牌({detected_negatives})'
                }
            else:
                return {
                    'action': 'remove_objects',
                    'reason': f'高风险场景且无品牌标识({detected_negatives})'
                }
        
        # ⚠️ 中等风险场景：根据品牌信息决策
        elif has_medium_risk_scene:
            if has_known_brand:
                return {
                    'action': 'keep_with_note',
                    'reason': f'中等风险场景但有知名品牌({detected_negatives})'
                }
            else:
                return {
                    'action': 'reduce_confidence',
                    'reason': f'中等风险场景且无明确品牌({detected_negatives})'
                }
        
        # 🔍 低风险场景：有负面关键词但风险较低
        else:
            if has_brand:
                return {
                    'action': 'keep_with_note',
                    'reason': f'低风险场景且有品牌标识({detected_negatives})'
                }
            else:
                return {
                    'action': 'reduce_confidence',
                    'reason': f'低风险场景但无品牌确认({detected_negatives})'
                }
    
    def _execute_filter_action(self, result: Dict[str, Any], filter_action: Dict[str, str], 
                             detected_negatives: List[str]) -> Dict[str, Any]:
        """
        🎯 执行过滤动作
        """
        action = filter_action['action']
        reason = filter_action['reason']
        
        if action == 'remove_objects':
            # 完全移除奶粉相关标签
            result = self._remove_milk_related_objects(result)
            result['anti_hallucination'] = {
                'action': 'objects_removed',
                'reason': reason,
                'detected_negatives': detected_negatives
            }
            logger.info(f"🚫 已移除奶粉相关标签: {reason}")
            
        elif action == 'reduce_confidence':
            # 降低置信度但保留标签
            original_confidence = result.get('confidence', 0.8)
            result['confidence'] = max(0.4, original_confidence - 0.3)
            result['anti_hallucination'] = {
                'action': 'confidence_reduced',
                'reason': reason,
                'detected_negatives': detected_negatives,
                'original_confidence': original_confidence
            }
            logger.info(f"⚠️ 已降低置信度: {original_confidence:.2f} → {result['confidence']:.2f}")
            
        elif action == 'keep_with_note':
            # 保留但添加备注
            result['anti_hallucination'] = {
                'action': 'kept_with_note',
                'reason': reason,
                'detected_negatives': detected_negatives,
                'note': '有品牌标识支持，保留但需人工确认'
            }
            logger.info(f"✅ 保留标签但添加备注: {reason}")
        
        return result
    
    def _remove_milk_related_objects(self, result: Dict[str, Any]) -> Dict[str, Any]:
        """
        从object字段中移除奶制品相关的关键词
        """
        try:
            object_value = result.get('object', '')
            if not object_value:
                return result
            
            # 奶制品相关关键词
            milk_keywords = ['奶粉罐', '奶瓶', '奶粉', '奶制品', '配方奶', '母乳', '牛奶', '奶粉包装']
            
            # 分割并过滤
            object_list = [obj.strip() for obj in str(object_value).split(',') if obj.strip()]
            filtered_objects = [obj for obj in object_list if not any(keyword in obj for keyword in milk_keywords)]
            
            result['object'] = ','.join(filtered_objects) if filtered_objects else ''
            
            if filtered_objects != object_list:
                logger.info(f"已移除奶制品相关物体: {[obj for obj in object_list if obj not in filtered_objects]}")
            
            return result
            
        except Exception as e:
            logger.error(f"移除奶制品相关物体时出错: {e}")
            return result

    # ===============================
    # 双模型分工机制 - 新增方法
    # ===============================

    def _build_general_detection_prompt(self, tag_language: str) -> str:
        """
        构建AI-B通用检测prompt，专注"行为/交互"识别
        """
        try:
            from utils.keyword_config import get_visual_objects, get_scenes, get_emotions
            
            objects = get_visual_objects()[:15]  # 取前15个常见物体
            scenes = get_scenes()[:10]   # 取前10个常见场景
            emotions = get_emotions()[:6]  # 取前6个情绪
            
            # 确保有默认值
            if not objects: objects = ["宝宝", "玩具", "餐具", "衣服"]
            if not scenes: scenes = ["室内", "家中卧室", "客厅"]
            if not emotions: emotions = ["开心", "温馨", "平静"]
            
            return f"""🎯 你是专业的视频内容分析师，请将画面内容描述为"行为/交互"短句。

**重要：本次分析不涉及任何品牌识别，请专注于以下三个维度：**

1. **interaction（行为/交互）**: **核心任务**，用"主语+动词+宾语"的格式描述画面中的核心事件。
   - **优秀示例**: "宝宝开心喝奶", "妈妈冲泡奶粉", "宝宝拒绝奶瓶", "医生推荐产品", "宝宝皮肤泛红"
   - **避免**: "宝宝, 奶瓶" (过于孤立)

2. **scene（场景识别）**: 客观描述画面发生的场景环境
   - 参考词汇：{', '.join(scenes)}

3. **emotion（情绪识别）**: 分析并提炼出画面中最核心、最关键的一个情绪词。
   - 参考词汇：{', '.join(emotions)}

**输出格式（严格遵循）：**
interaction: 行为/交互短句
scene: 场景描述(可含逗号)
emotion: 单个关键词"""

        except Exception as e:
            logger.warning(f"构建通用检测prompt失败，使用兜底版本: {e}")
            return """请将画面内容描述为"行为/交互"短句。
输出格式：
interaction: 行为/交互短句
scene: 场景1,场景2
emotion: 情绪1,情绪2"""

    def _should_trigger_brand_detection(self, general_analysis: Dict[str, Any]) -> bool:
        """
        判断是否需要触发品牌检测（AI-A），基于interaction字段
        """
        # 🔧 从配置文件读取触发关键词
        try:
            config_manager = get_config_manager()
            keywords_config = config_manager.get_keywords_config()
            product_keywords = keywords_config.get('ai_brand_detection', {}).get('trigger_keywords', [])
            
            # 如果配置为空，使用默认关键词作为兜底
            if not product_keywords:
                logger.warning("未找到ai_brand_detection.trigger_keywords配置，使用默认关键词")
                product_keywords = [
                    # 行为/互动相关
                    '罐', '产品', '喂养', '喝', '冲泡', '搅拌',
                    # 传统物体相关
                    '奶粉罐', '奶瓶', '奶粉', '配方奶', '婴儿奶粉',
                    '奶粉包装', '奶粉罐特写', '成分表', '配料表',
                    '营养成分', '产品包装', '包装盒'
                ]
            else:
                logger.info(f"从配置文件加载品牌检测触发关键词: {product_keywords}")
                
        except Exception as e:
            logger.error(f"读取品牌检测配置失败: {e}，使用默认关键词")
            product_keywords = [
                '罐', '产品', '喂养', '喝', '冲泡', '搅拌',
                '奶粉罐', '奶瓶', '奶粉', '配方奶', '婴儿奶粉',
                '奶粉包装', '奶粉罐特写', '成分表', '配料表',
                '营养成分', '产品包装', '包装盒'
            ]

        # 检查interaction和scene字段
        interaction_text = str(general_analysis.get('interaction', '')).lower()
        object_text = str(general_analysis.get('object', '')).lower() # 兼容旧版object字段
        scene_text = str(general_analysis.get('scene', '')).lower()

        # 组合所有可能的文本来源
        combined_text = f"{interaction_text} {object_text} {scene_text}"

        for keyword in product_keywords:
            if keyword in combined_text:
                logger.info(f"触发品牌检测：检测到关键词 '{keyword}' (来源: 配置文件)")
                return True

        return False

    def _detect_core_brands(self, video_path: str, frame_rate: float) -> str:
        """
        AI-A专用核心品牌检测（新增音频兜底机制）
        """
        # 1. 优先尝试视觉检测
        try:
            brand_prompt = self._build_brand_detection_prompt()
            logger.info("🕵️‍♂️ [侦查日志] ====== 品牌检测阶段 (AI-A) - 视觉 ======")
            logger.info(f"   - 使用的Prompt: {brand_prompt}")
            
            result = self._analyze_video_file(video_path, frame_rate, brand_prompt)

            if result and 'analysis' in result:
                analysis_text = result['analysis']
                logger.info(f"   - 品牌检测AI原始返回: '{analysis_text}'")

                # 如果AI明确返回"无"，则认为视觉检测已确认无品牌，无需音频兜底
                if any(neg in analysis_text for neg in ["无", "未检测到", "不包含", "没有"]):
                    logger.info("   - [结论] 视觉品牌检测模型明确返回未检测到品牌。")
                    logger.info("🕵️‍♂️ =======================================")
                    return ""

                config_manager = get_config_manager()
                keywords_config = config_manager.get_keywords_config()
                core_brands = keywords_config.get('ai_brand_detection', {}).get('core_brands', [])
                if not core_brands: core_brands = ['启赋', 'illuma', '惠氏', 'Wyeth', '蕴淳', 'A2', 'ATWO', 'HMO']
                logger.info(f"   - 核心品牌列表: {core_brands}")
                
                found_brands = []
                for brand in core_brands:
                    if re.search(r'\b' + re.escape(brand) + r'\b', analysis_text, re.IGNORECASE):
                        found_brands.append(brand)
                
                if found_brands:
                    detected_brands_str = ','.join(list(dict.fromkeys(found_brands)))
                    logger.info(f"   - [结论] ✅ 视觉核心品牌检测成功: {detected_brands_str}")
                    logger.info("🕵️‍♂️ =======================================")
                    return detected_brands_str
                else:
                    logger.info("   - [结论] 视觉品牌检测未返回核心品牌，准备尝试音频兜底。")

        except Exception as e:
            logger.warning(f"视觉品牌检测失败: {e}, 尝试音频兜底")

        # 2. 如果视觉检测失败或未找到，尝试音频兜底
        logger.info("🎤 [侦查日志] ====== 品牌检测阶段 (AI-A) - 音频兜底 ======")
        try:
            transcription = self._extract_and_transcribe_audio(video_path)
            if not transcription:
                logger.info("   - 音频转录结果为空，无法进行品牌检测。")
                logger.info("🎤 =======================================")
                return ""

            logger.info(f"   - 音频转录内容(片段): '{transcription[:100]}...'")

            config_manager = get_config_manager()
            keywords_config = config_manager.get_keywords_config()
            core_brands = keywords_config.get('ai_brand_detection', {}).get('core_brands', [])
            if not core_brands: core_brands = ['启赋', 'illuma', '惠氏', 'Wyeth', '蕴淳', 'A2', 'ATWO', 'HMO']
            
            found_brands = []
            for brand in core_brands:
                if re.search(r'\b' + re.escape(brand) + r'\b', transcription, re.IGNORECASE):
                    found_brands.append(brand)
            
            if found_brands:
                detected_brands_str = ','.join(list(dict.fromkeys(found_brands)))
                logger.info(f"   - [结论] ✅ 音频兜底核心品牌检测成功: {detected_brands_str}")
                logger.info("🎤 =======================================")
                return detected_brands_str
            else:
                logger.info("   - [结论] 🔍 音频转录中未发现核心品牌。")
                logger.info("🎤 =======================================")
                return ""

        except Exception as e:
            logger.error(f"品牌检测的音频兜底失败: {e}")
            logger.info("🎤 =======================================")
            return ""

    def _build_brand_detection_prompt(self) -> str:
        """
        构建AI-A专用的核心品牌检测prompt
        """
        try:
            config_manager = get_config_manager()
            keywords_config = config_manager.get_keywords_config()
            core_brands = keywords_config.get('ai_brand_detection', {}).get('core_brands', [])

            if not core_brands:
                logger.error("核心品牌列表(core_brands)未配置，使用默认列表进行品牌检测。")
                core_brands = ['启赋', 'illuma', '惠氏', 'Wyeth', '蕴淳', 'A2', 'ATWO', 'HMO']

            brand_list_str = ", ".join(core_brands)
            return f"""🔍 你是品牌识别专家，请严格按照提供的品牌列表检查画面。

# **核心任务**
你的唯一任务是识别画面中是否清晰出现了以下 **核心品牌列表** 中的任何一个品牌标识。

# **核心品牌列表**
`{brand_list_str}`

# **检查重点**
1. 奶粉罐包装上的品牌Logo或文字。
2. 产品包装正面的品牌名称。
3. 任何与核心品牌列表相关的清晰可见的标识。

# **严格要求**
- **只识别列表中的品牌**。如果画面中出现了其他品牌，忽略它们。
- 如果画面模糊、角度不佳或无法100%确认，请不要输出任何品牌。
- 如果没有在画面中找到任何核心品牌，请直接输出 "无"。

# **输出格式**
- 如果检测到一个或多个品牌，请用逗号分隔返回，例如: "启赋, illuma"
- 如果未检测到任何核心品牌，请输出: "无"
"""
        except Exception as e:
            logger.error(f"构建品牌检测prompt失败: {e}")
            # Return a non-functional prompt
            return "请识别视频中的品牌"