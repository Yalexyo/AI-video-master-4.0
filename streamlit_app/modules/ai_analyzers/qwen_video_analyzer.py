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

# 导入音频分析器
from .dashscope_audio_analyzer import DashScopeAudioAnalyzer
from .deepseek_analyzer import DeepSeekAnalyzer

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
            'model': 'qwen-vl-plus-latest',  # 使用最新模型
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
        
        try:
            # 🎯 第一步：尝试视觉分析（带重试机制）
            logger.info("🎯 开始视觉分析...")
            visual_result = self._analyze_with_retry(video_path, frame_rate, tag_language)
            
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
    
    def _analyze_with_retry(self, video_path: str, frame_rate: float, tag_language: str) -> Dict[str, Any]:
        """
        🔧 带重试机制的视觉分析
        """
        max_retry = self.quality_config['max_retry_count']
        
        for attempt in range(max_retry + 1):
            try:
                # 选择提示词（重试时使用增强版）
                if attempt == 0:
                    prompt = self._build_professional_prompt(tag_language)
                else:
                    prompt = self._build_enhanced_retry_prompt(tag_language)
                    logger.info(f"🔄 第{attempt}次重试，使用增强提示词")
                
                # 执行分析
                visual_result = self._analyze_video_file(video_path, frame_rate, prompt)
                
                if visual_result and 'analysis' in visual_result:
                    # 解析结果
                    analysis_result = self._parse_analysis_result(
                        visual_result['analysis'], tag_language
                    )
                    analysis_result["success"] = True
                    analysis_result["quality_score"] = visual_result.get('quality_score', 0.8)
                    analysis_result["analysis_method"] = "visual"
                    analysis_result["retry_count"] = attempt
                    
                    # 🎯 NEW: 检测人脸特写
                    face_close_up_detected = self._detect_face_close_up(analysis_result, video_path)
                    if face_close_up_detected:
                        logger.warning(f"🚫 检测到人脸特写片段，标记为不可用: {video_path}")
                        analysis_result["is_face_close_up"] = True
                        analysis_result["unusable"] = True
                        analysis_result["unusable_reason"] = "人脸特写片段"
                        # 降低质量分，确保在匹配时被过滤
                        analysis_result["quality_score"] = 0.1
                    else:
                        analysis_result["is_face_close_up"] = False
                        analysis_result["unusable"] = False
                    
                    # 检查质量
                    if analysis_result["quality_score"] >= self.quality_config['min_quality_threshold']:
                        logger.info(f"✅ 分析成功，质量分: {analysis_result['quality_score']:.2f}")
                        return analysis_result
                    elif attempt < max_retry:
                        logger.warning(f"⚠️ 质量分过低 ({analysis_result['quality_score']:.2f})，准备重试...")
                        continue
                    else:
                        # 最后一次重试，进行后处理优化
                        analysis_result = self._enhance_poor_result(analysis_result, video_path)
                        logger.info(f"🔧 应用后处理优化，最终质量分: {analysis_result['quality_score']:.2f}")
                        return analysis_result
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
        🔧 构建基于配置文件的视觉分析提示词
        """
        try:
            from streamlit_app.utils.keyword_config import sync_prompt_templates
            templates = sync_prompt_templates()
            return templates.get("qwen_visual", "")
        except Exception as e:
            logger.warning(f"无法导入统一prompt模板，使用兜底配置: {e}")
            return self._get_fallback_visual_prompt()
    
    def _build_enhanced_retry_prompt(self, tag_language: str) -> str:
        """
        🔧 构建基于配置文件的重试提示词
        """
        try:
            from streamlit_app.utils.keyword_config import sync_prompt_templates
            templates = sync_prompt_templates()
            return templates.get("qwen_retry", "")
        except Exception as e:
            logger.warning(f"无法导入统一重试prompt模板，使用兜底配置: {e}")
            return self._get_fallback_retry_prompt()
    
    def _get_fallback_visual_prompt(self) -> str:
        """兜底视觉分析prompt"""
        return """你是母婴产品**视觉识别专家**，请**只看画面**提取关键信息。

—— **强制识别字段** ——
object:        奶粉罐、奶瓶、宝宝、妈妈、婴儿用品、营养表
sence:         厨房、客厅、医院、病房、户外、公园、游乐场
emotion:       [快乐 / 兴奋 / 温馨 / 焦虑 / 痛苦]  ← 只能选这 5 个
brand_elements:启赋、Wyeth、illuma、A2、ATWO、HMO、DHA
confidence:    0.0-1.0

—— **痛点信号**（若出现请一定写到 object 或 sence） ——
宝宝哭、输液管、医院、病床、发烧、夜醒、父母焦虑

—— **活力信号**（判促销结尾用） ——
宝宝奔跑、跳跃、滑梯、蹦床、户外玩耍、公园嬉戏

—— **输出要求** ——
必须严格按以下格式输出，每行一个字段：
object: [识别到的物体，逗号分隔]
sence: [识别到的场景，逗号分隔]
emotion: [识别到的情绪，只能从5个选项中选]
brand_elements: [识别到的品牌，逗号分隔]
confidence: [置信度0.0-1.0]

注意：
1. 不要添加任何解释或说明文字
2. 看不清的字段留空，但保留字段名
3. 每个字段都必须存在

请开始分析画面："""
    
    def _get_fallback_retry_prompt(self) -> str:
        """兜底重试prompt"""
        return """你是母婴视觉专家，重新**深度放大**画面，补抓遗漏信息。

—— **关键补抓** ——
• pain_signals: 宝宝哭、输液管、医院、发烧、夜醒  
• vitality_signals: 跑、跳、滑梯、蹦床、户外、公园  
• brand logo / 营养成分表 / 分子结构

—— **输出要求** ——
必须严格按以下格式输出，每行一个字段：
object: [识别到的物体，逗号分隔]
sence: [识别到的场景，逗号分隔]
emotion: [快乐/兴奋/温馨/焦虑/痛苦中选一个]
brand_elements: [识别到的品牌，逗号分隔]
confidence: [置信度0.0-1.0]

注意：看不清的字段留空，但保留字段名。

请再次精准识别："""
    
    def _get_fallback_audio_prompt(self, transcription: str) -> str:
        """兜底音频分析prompt"""
        return f"""分析母婴短片语音转录，提取产品与场景关键词。
语音内容:
{transcription}

必抓信息:
object:        奶粉、奶瓶、宝宝、妈妈、医院、游乐场
sence:         冲奶、指导、护理、户外玩耍、医院场景
emotion:       [快乐 / 兴奋 / 温馨 / 焦虑 / 痛苦]  (限选5个)
brand_elements:启赋、Wyeth、illuma、A2、ATWO、HMO、DHA
confidence:    0.0-1.0

重点关注:
- 痛点词: 哭闹、发烧、拉肚子、夜醒、生病、焦虑
- 促销信号: 宝宝开心、快乐成长、活力满满、健康成长、爱笑、精神饱满、机灵可爱、聪明活泼

输出要求:
1. 全中文小写 (品牌名保留大小写)
2. 逗号分隔单词/短语 (无括号/引号)
3. confidence < 0.6 不输出
4. 仅基于语音，不臆测画面

按此格式生成: object, sence, emotion, brand_elements, confidence."""
    
    def _get_default_result(self, error_msg: str) -> Dict[str, Any]:
        """获取默认错误结果"""
        return {
            "success": False,
            "error": error_msg,
            "object": "",
            "sence": "",
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
        required_fields = ['object:', 'sence:', 'emotion:', 'brand_elements:', 'confidence:']
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
        video_info = self._extract_video_info(video_path)
        
        # 基于视频特征推断
        if enhanced_result.get('object') in ['无', '画面不清晰', '']:
            if video_info.get('duration', 0) < 5:
                enhanced_result['object'] = '疑似产品展示'
            else:
                enhanced_result['object'] = '疑似人物活动'
        
        if enhanced_result.get('sence') in ['无', '画面不清晰', '']:
            enhanced_result['sence'] = '疑似室内环境'
        
        if enhanced_result.get('emotion') in ['无', '画面不清晰', '']:
            enhanced_result['emotion'] = '疑似温馨氛围'
        
        if enhanced_result.get('brand_elements') in ['无', '画面不清晰', '']:
            enhanced_result['brand_elements'] = '疑似品牌要素'
        
        # 重建all_tags
        enhanced_result['all_tags'] = self._rebuild_tags(enhanced_result)
        
        # 提升质量分
        enhanced_result['quality_score'] = min(enhanced_result.get('quality_score', 0.0) + 0.1, 0.7)
        
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
        """重建all_tags字段"""
        all_tags = []
        for field in ['object', 'sence', 'emotion', 'brand_elements']:
            value = result.get(field, '')
            if value and value not in ['无', '画面不清晰', '疑似品牌要素', '疑似室内环境', '疑似温馨氛围', '疑似产品展示', '疑似人物活动']:
                tags = [tag.strip() for tag in value.split(',') if tag.strip()]
                all_tags.extend(tags)
        
        # 去重并过滤
        unique_tags = []
        for tag in all_tags:
            tag_clean = tag.replace('疑似', '').strip()
            if tag_clean and tag_clean not in unique_tags:
                unique_tags.append(tag_clean)
        
        return unique_tags
    
    def _parse_analysis_result(self, analysis_text, tag_language: str) -> Dict[str, Any]:
        """解析分析结果，使用简化的5字段格式"""
        
        # 🔧 重用的格式清理函数
        def clean_field_value(value: str) -> str:
            """清理字段值，确保输出简洁的单词短语"""
            if not value:
                return ''
            
            # 基础清理
            cleaned = value.strip()
            
            # 🔧 重要修复：移除字段标识符干扰
            field_markers = ['object:', 'sence:', 'emotion:', 'brand_elements:', 'confidence:']
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
                'object': '',
                'sence': '', 
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
                    
                    # 检查每一行是否包含字段标识符
                    if line.lower().startswith('object:'):
                        raw_value = line[7:].strip()
                        result['object'] = clean_field_value(raw_value)
                        logger.debug(f"提取object: '{raw_value}' -> '{result['object']}'")
                        
                    elif line.lower().startswith('sence:'):
                        raw_value = line[6:].strip()
                        result['sence'] = clean_field_value(raw_value)
                        logger.debug(f"提取sence: '{raw_value}' -> '{result['sence']}'")
                        
                    elif line.lower().startswith('emotion:'):
                        raw_value = line[8:].strip()
                        result['emotion'] = clean_field_value(raw_value)
                        logger.debug(f"提取emotion: '{raw_value}' -> '{result['emotion']}'")
                        
                    elif line.lower().startswith('brand_elements:'):
                        raw_value = line[15:].strip()
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
                        try:
                            confidence_match = re.search(r'([0-9.]+)', confidence_text)
                            if confidence_match:
                                result['confidence'] = float(confidence_match.group(1))
                                logger.debug(f"提取confidence: '{confidence_text}' -> {result['confidence']}")
                        except:
                            result['confidence'] = 0.8
            else:
                # 格式2：简单文本格式 - 智能解析逗号分隔的内容
                logger.info("🔧 检测到简单文本格式，启用智能解析")
                full_text = analysis_text.replace('\n', ' ').strip()
                
                # 分割为tokens
                tokens = [token.strip() for token in full_text.split('、') if token.strip()]
                if not tokens:
                    tokens = [token.strip() for token in full_text.split(',') if token.strip()]
                
                # 智能分类配置
                from streamlit_app.utils.keyword_config import get_keyword_config
                try:
                    keywords_config = get_keyword_config()
                    
                    # 获取配置词汇 - 使用正确的配置结构
                    from streamlit_app.utils.keyword_config import get_visual_objects, get_scenes, get_emotions, get_brands
                    
                    visual_objects = get_visual_objects()
                    visual_scenes = get_scenes() 
                    emotions = get_emotions()
                    brands = get_brands()
                    
                    # 智能分类
                    detected_objects = []
                    detected_scenes = []
                    detected_emotions = []
                    detected_brands = []
                    
                    for token in tokens:
                        cleaned_token = clean_field_value(token)
                        if not cleaned_token:
                            continue
                            
                        # 品牌优先级最高
                        if any(brand.lower() in cleaned_token.lower() for brand in brands):
                            detected_brands.append(cleaned_token)
                        # 情绪匹配
                        elif any(emotion in cleaned_token for emotion in emotions):
                            detected_emotions.append(cleaned_token)
                        # 场景匹配
                        elif any(scene in cleaned_token for scene in visual_scenes):
                            detected_scenes.append(cleaned_token)
                        # 物体匹配
                        elif any(obj in cleaned_token for obj in visual_objects):
                            detected_objects.append(cleaned_token)
                        else:
                            # 兜底：根据关键词特征判断
                            if any(keyword in cleaned_token for keyword in ['奶粉', '奶瓶', '宝宝', '妈妈', '婴儿', '用品']):
                                detected_objects.append(cleaned_token)
                            elif any(keyword in cleaned_token for keyword in ['厨房', '客厅', '户外', '公园', '医院', '游乐场']):
                                detected_scenes.append(cleaned_token)
                    
                    # 填充结果 - 🔧 增强数字污染清理
                    result['object'] = ','.join(detected_objects) if detected_objects else ''
                    result['sence'] = ','.join(detected_scenes) if detected_scenes else ''
                    result['emotion'] = ','.join(detected_emotions) if detected_emotions else ''
                    # 🔧 特殊处理品牌：过滤数字污染
                    clean_brands = [brand for brand in detected_brands if brand and not re.match(r'^[0-9]+\.?[0-9]*$', brand)]
                    result['brand_elements'] = ','.join(clean_brands) if clean_brands else ''
                    
                    logger.info(f"🔧 智能解析结果:")
                    logger.info(f"   原始tokens: {tokens}")
                    logger.info(f"   物体: {detected_objects}")
                    logger.info(f"   场景: {detected_scenes}")
                    logger.info(f"   情绪: {detected_emotions}")
                    logger.info(f"   品牌: {detected_brands}")
                    
                except Exception as e:
                    logger.warning(f"智能解析失败，使用兜底策略: {e}")
                    # 兜底：直接将所有内容放入object字段
                    result['object'] = clean_field_value(full_text)
            
            # 🔧 创建all_tags - 包含所有有意义的内容（强化数字过滤）
            all_tags = []
            for field_name, value in result.items():
                if field_name == 'confidence':
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
            
            logger.info(f"🎯 简化解析最终结果:")
            logger.info(f"   物体: '{result['object']}'")
            logger.info(f"   场景: '{result['sence']}'")
            logger.info(f"   情绪: '{result['emotion']}'")
            logger.info(f"   品牌: '{result['brand_elements']}'")
            logger.info(f"   置信度: {result['confidence']}")
            logger.info(f"   全部标签: {result['all_tags']}")
            
            return result
            
        except Exception as e:
            logger.error(f"解析分析结果失败: {str(e)}")
            return {
                'object': '',
                'sence': '',
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
        object_empty = not visual_result.get('object') or visual_result.get('object') == ''
        brand_empty = not visual_result.get('brand_elements') or visual_result.get('brand_elements') == ''
        scene_empty = not visual_result.get('sence') or visual_result.get('sence') == ''
        
        # 如果物体和品牌都为空，启用音频兜底
        if object_empty and brand_empty:
            logger.info("🎤 检测到关键字段为空(物体+品牌)，启用音频兜底分析")
            return True
        
        # 如果物体、场景、品牌三者中有两个为空，也启用音频分析
        empty_count = sum([object_empty, brand_empty, scene_empty])
        if empty_count >= 2:
            logger.info(f"🎤 检测到{empty_count}个关键字段为空，启用音频兜底分析")
            return True
        
        return False
    
    def _get_targeted_analysis_prompt(self, transcription: str, visual_result: Dict[str, Any]) -> str:
        """
        🎯 生成针对性分析prompt - 只分析visual缺失的字段
        """
        # 分析visual结果中的空字段
        missing_fields = []
        field_analysis = {}
        
        object_empty = not visual_result.get('object') or visual_result.get('object') == ''
        scene_empty = not visual_result.get('sence') or visual_result.get('sence') == ''
        emotion_empty = not visual_result.get('emotion') or visual_result.get('emotion') == ''
        brand_empty = not visual_result.get('brand_elements') or visual_result.get('brand_elements') == ''
        
        if object_empty:
            missing_fields.append("object")
            field_analysis["object"] = "奶粉、奶瓶、宝宝、妈妈、医院、游乐场"
        
        if scene_empty:
            missing_fields.append("sence")
            field_analysis["sence"] = "冲奶、指导、护理、户外玩耍、医院场景"
        
        if emotion_empty:
            missing_fields.append("emotion")
            field_analysis["emotion"] = "[快乐 / 兴奋 / 温馨 / 焦虑 / 痛苦]"
        
        if brand_empty:
            missing_fields.append("brand_elements")
            field_analysis["brand_elements"] = "启赋、Wyeth、illuma、A2、ATWO、HMO、DHA"
        
        # 构建针对性prompt
        prompt_parts = [
            f"🎯 针对性分析母婴vlog语音转录，只补充visual分析缺失的{len(missing_fields)}个字段。",
            f"",
            f"语音内容:",
            f"{transcription}",
            f"",
            f"📋 Visual分析已有结果:",
        ]
        
        # 显示已有结果
        if not object_empty:
            prompt_parts.append(f"object: {visual_result.get('object', '')} ✅")
        if not scene_empty:
            prompt_parts.append(f"sence: {visual_result.get('sence', '')} ✅")
        if not emotion_empty:
            prompt_parts.append(f"emotion: {visual_result.get('emotion', '')} ✅")
        if not brand_empty:
            prompt_parts.append(f"brand_elements: {visual_result.get('brand_elements', '')} ✅")
        
        prompt_parts.extend([
            f"",
            f"🎯 仅需分析以下{len(missing_fields)}个缺失字段:",
        ])
        
        # 只列出需要分析的字段
        for field in missing_fields:
            prompt_parts.append(f"{field}: {field_analysis[field]}")
        
        prompt_parts.extend([
            f"",
            f"📝 输出要求:",
            f"1. 仅输出缺失字段，不要重复已有结果",
            f"2. 全中文小写(品牌名保留大小写)",
            f"3. 逗号分隔单词/短语",
            f"4. confidence < 0.6 的字段输出为空",
            f"5. 基于语音内容，不臆测画面",
            f"",
            f"输出格式 - 只包含缺失字段:",
        ])
        
        # 动态生成输出格式
        for field in missing_fields:
            prompt_parts.append(f"{field}: <分析结果>")
        
        return "\n".join(prompt_parts)
    
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
                'sence': visual_result.get('sence', ''),
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
                
                # 只处理DeepSeek新分析的字段，保留visual的非空字段
                if line.lower().startswith('object:') and not visual_result.get('object'):
                    raw_value = line[7:].strip()
                    new_value = clean_field_value(raw_value)
                    if new_value:  # 只有非空时才更新
                        result['object'] = new_value
                        logger.info(f"🎯 补充object: '{new_value}'")
                    
                elif line.lower().startswith('sence:') and not visual_result.get('sence'):
                    raw_value = line[6:].strip()
                    new_value = clean_field_value(raw_value)
                    if new_value:
                        result['sence'] = new_value
                        logger.info(f"🎯 补充sence: '{new_value}'")
                    
                elif line.lower().startswith('emotion:') and not visual_result.get('emotion'):
                    raw_value = line[8:].strip()
                    new_value = clean_field_value(raw_value)
                    if new_value:
                        result['emotion'] = new_value
                        logger.info(f"🎯 补充emotion: '{new_value}'")
                    
                elif line.lower().startswith('brand_elements:') and not visual_result.get('brand_elements'):
                    raw_value = line[15:].strip()
                    new_value = clean_field_value(raw_value)
                    if new_value:
                        result['brand_elements'] = new_value
                        logger.info(f"🎯 补充brand_elements: '{new_value}'")
                        
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
            for value in [result['object'], result['sence'], result['emotion'], result['brand_elements']]:
                if value:
                    tags = [tag.strip() for tag in value.split(',') if tag.strip()]
                    for tag in tags:
                        cleaned_tag = clean_field_value(tag)
                        if cleaned_tag and cleaned_tag not in all_tags:
                            all_tags.append(cleaned_tag)
            
            result['all_tags'] = all_tags
            
            logger.info(f"🎯 针对性分析完成:")
            logger.info(f"   物体: '{result['object']}'")
            logger.info(f"   场景: '{result['sence']}'")
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
            for field in ['object', 'sence', 'emotion', 'brand_elements']:
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
            supplemented_count = sum(1 for field in ['object', 'sence', 'emotion', 'brand_elements'] 
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
        """使用DeepSeekAnalyzer分析转录文本"""
        try:
            if not self.deepseek_analyzer.is_available():
                logger.warning("🤖 DeepSeek分析器不可用，使用简单文本分析")
                return self._simple_text_analysis(transcription)
            
            logger.info("🤖 开始DeepSeek音频转录文本分析...")
                
            # 构建音频转录分析提示词
            try:
                from streamlit_app.utils.keyword_config import sync_prompt_templates
                templates = sync_prompt_templates()
                analysis_prompt = templates.get("deepseek_audio", "").replace("[音频转录文本]", transcription)
                
                if not analysis_prompt:
                    # 使用兜底prompt
                    analysis_prompt = self._get_fallback_audio_prompt(transcription)
                    
            except Exception as e:
                logger.warning(f"无法导入统一音频prompt模板，使用兜底配置: {e}")
                analysis_prompt = self._get_fallback_audio_prompt(transcription)

            # 使用DeepSeek分析器
            messages = [
                {"role": "system", "content": "你是专业的母婴产品语音内容分析师，专门分析语音转录文本中的产品和营销信息。"},
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
        """解析DeepSeek分析结果"""
        
        # 🔧 重用Qwen的格式清理函数
        def clean_field_value(value: str) -> str:
            """清理字段值，确保输出简洁的单词短语"""
            if not value:
                return ''
            
            # 基础清理
            cleaned = value.strip()
            
            # 🔧 重要修复：移除字段标识符干扰
            field_markers = ['object:', 'sence:', 'emotion:', 'brand_elements:', 'confidence:']
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
                'sence': '', 
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
                
                # 检查每一行是否包含字段标识符
                if line.lower().startswith('object:'):
                    raw_value = line[7:].strip()  # 移除 "object:" 
                    result['object'] = clean_field_value(raw_value)
                    logger.info(f"提取object: '{raw_value}' -> '{result['object']}'")
                    
                elif line.lower().startswith('sence:'):
                    raw_value = line[6:].strip()  # 移除 "sence:"
                    result['sence'] = clean_field_value(raw_value)
                    logger.info(f"提取sence: '{raw_value}' -> '{result['sence']}'")
                    
                elif line.lower().startswith('emotion:'):
                    raw_value = line[8:].strip()  # 移除 "emotion:"
                    result['emotion'] = clean_field_value(raw_value)
                    logger.info(f"提取emotion: '{raw_value}' -> '{result['emotion']}'")
                    
                elif line.lower().startswith('brand_elements:'):
                    raw_value = line[15:].strip()  # 移除 "brand_elements:"
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
            for value in [result['object'], result['sence'], result['emotion'], result['brand_elements']]:
                if value:  # 只要不为空就处理
                    # 分割逗号分隔的标签
                    tags = [tag.strip() for tag in value.split(',') if tag.strip()]
                    for tag in tags:
                        cleaned_tag = clean_field_value(tag)
                        if cleaned_tag:  # 清理后不为空就添加
                            all_tags.append(cleaned_tag)
            
            # 去重并过滤
            result['all_tags'] = list(set(filter(None, all_tags)))
            
            logger.info(f"🎯 DeepSeek最终解析结果:")
            logger.info(f"   物体: '{result['object']}'")
            logger.info(f"   场景: '{result['sence']}'")
            logger.info(f"   情绪: '{result['emotion']}'")
            logger.info(f"   品牌: '{result['brand_elements']}'")
            logger.info(f"   置信度: {result['confidence']}")
            logger.info(f"   标签: {result['all_tags']}")
            
            return result if any(v for v in result.values() if v not in ['', 0.7, []]) else None
            
        except Exception as e:
            logger.error(f"解析DeepSeek结果失败: {str(e)}")
            return None
    
    def _simple_text_analysis(self, text: str) -> Dict[str, Any]:
        """简单文本分析（关键词匹配）"""
        object_keywords = ['奶粉', '奶瓶', '婴儿', '宝宝', '妈妈', '孩子', '产品']
        scene_keywords = ['家庭', '厨房', '卧室', '客厅', '育儿']
        emotion_keywords = ['温馨', '关爱', '专业', '舒适', '安全']
        brand_keywords = ['营养', '品牌', '质量', '健康', '成长']
        
        found_objects = [kw for kw in object_keywords if kw in text]
        found_scenes = [kw for kw in scene_keywords if kw in text]
        found_emotions = [kw for kw in emotion_keywords if kw in text]
        found_brands = [kw for kw in brand_keywords if kw in text]
        
        result = {
            'object': ', '.join(found_objects) if found_objects else '不确定',
            'sence': ', '.join(found_scenes) if found_scenes else '不确定',
            'emotion': ', '.join(found_emotions) if found_emotions else '不确定',
            'brand_elements': ', '.join(found_brands) if found_brands else '不确定',
            'confidence': 0.6 if any([found_objects, found_scenes, found_emotions, found_brands]) else 0.3,
            'all_tags': found_objects + found_scenes + found_emotions + found_brands,
            'success': True
        }
        
        return result
    
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
            
            for field in ['object', 'sence', 'emotion', 'brand_elements']:
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
            logger.info(f"   场景: {merged_result['sence']}")
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
                from streamlit_app.config.factory_config import VISUAL_ANALYSIS_CONFIG
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
            scene_tags = analysis_result.get('sence', '')
            
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