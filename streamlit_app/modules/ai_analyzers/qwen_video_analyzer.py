"""
千问2.5视觉分析器

专门处理千问2.5多模态视频分析功能的模块
"""

import os
import logging
from typing import Dict, Any, List, Optional
from pathlib import Path
from collections import Counter

logger = logging.getLogger(__name__)


class QwenVideoAnalyzer:
    """千问2.5视觉分析器"""
    
    def __init__(self, api_key: Optional[str] = None):
        """
        初始化千问2.5分析器
        
        Args:
            api_key: DashScope API密钥
        """
        self.api_key = api_key or os.environ.get("DASHSCOPE_API_KEY")
        self.analyzer = None
        
        if not self.api_key:
            logger.warning("未设置DASHSCOPE_API_KEY，千问2.5分析器不可用")
        else:
            self._initialize_analyzer()
    
    def _initialize_analyzer(self):
        """初始化千问2.5分析器"""
        try:
            # 直接内置千问分析功能，不依赖外部模块
            import dashscope
            dashscope.api_key = self.api_key
            self.analyzer = True  # 标记为可用
            logger.info("千问2.5视觉分析器初始化成功")
        except ImportError as e:
            logger.error(f"无法导入DashScope: {str(e)}")
            self.analyzer = None
        except Exception as e:
            logger.error(f"千问2.5分析器初始化失败: {str(e)}")
            self.analyzer = None
    
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
        分析单个视频片段
        
        Args:
            video_path: 视频文件路径
            tag_language: 标签语言（"中文" 或 "英文"）
            frame_rate: 帧率（每秒几帧）
            
        Returns:
            分析结果字典
        """
        if not self.is_available():
            return {
                "success": False,
                "error": "千问2.5分析器不可用",
                "objects": [],
                "scenes": [],
                "people": [],
                "emotions": [],
                "brands": [],
                "all_tags": []
            }
        
        if not os.path.exists(video_path):
            return {
                "success": False,
                "error": f"视频文件不存在: {video_path}",
                "objects": [],
                "scenes": [],
                "people": [],
                "emotions": [],
                "brands": [],
                "all_tags": []
            }
        
        try:
            # 构建分析提示词
            prompt = self._build_analysis_prompt(tag_language)
            
            # 调用千问2.5分析
            result = self._analyze_video_file(
                video_path,
                frame_rate=frame_rate,
                prompt=prompt
            )
            
            if result and 'analysis' in result:
                # 解析分析结果
                analysis_result = self._parse_analysis_result(
                    result['analysis'], tag_language
                )
                analysis_result["success"] = True
                return analysis_result
            else:
                return {
                    "success": False,
                    "error": "千问2.5分析返回空结果",
                    "objects": [],
                    "scenes": [],
                    "people": [],
                    "emotions": [],
                    "brands": [],
                    "all_tags": []
                }
                
        except Exception as e:
            logger.error(f"千问2.5视频分析失败: {str(e)}")
            return {
                "success": False,
                "error": str(e),
                "objects": [],
                "scenes": [],
                "people": [],
                "emotions": [],
                "brands": [],
                "all_tags": []
            }
    
    def _build_analysis_prompt(self, tag_language: str) -> str:
        """构建分析提示词，以符合新的CSV格式要求"""
        # 提示词要求模型输出与 demo.csv 格式一致的字段
        # object, sence, emotion, brand_elements 为逗号分隔的标签列表
        # confidence 为单个浮点数值
        return """请分析视频内容，并按以下格式输出结果：
object: [物体标签列表，以英文逗号分隔]
sence: [场景标签列表，以英文逗号分隔]
emotion: [情绪标签列表，以英文逗号分隔]
brand_elements: [品牌元素列表，例如：奶粉罐,奶瓶,小瓶水奶,成分表,配料表,奶粉罐成分表。以英文逗号分隔]
confidence: [单一置信度评分，0.0到1.0之间]

如果某个类别没有识别到内容，请在该类别后留空或填写 "无"。
例如：
object: 婴儿,玩具,小汽车
sence: 卧室,室内
emotion: 开心
brand_elements: 奶粉罐,品牌Logo
confidence: 0.85
"""
    
    def _parse_analysis_result(
        self, 
        analysis_text, 
        tag_language: str
    ) -> Dict[str, Any]:
        """解析分析结果，以提取 object, sence, emotion, brand_elements 和 confidence"""
        analysis_result = {
            'object': '',      # 存储逗号分隔的字符串
            'sence': '',       # 存储逗号分隔的字符串
            'emotion': '',     # 存储逗号分隔的字符串
            'brand_elements': '', # 存储逗号分隔的字符串
            'confidence': 0.8, # 默认置信度，如果解析失败
            'all_tags': []      # 保留字段，但主要数据结构改变
        }
        
        try:
            # 🔍 添加调试日志：记录原始API响应
            logger.info(f"🔍 千问API原始响应内容:\n{analysis_text}")
            logger.info(f"🔍 响应类型: {type(analysis_text)}")
            
            # 🛠️ 修复：正确处理列表响应格式
            if isinstance(analysis_text, list):
                # 如果是列表，提取第一个元素的'text'字段
                if len(analysis_text) > 0 and isinstance(analysis_text[0], dict):
                    analysis_text = analysis_text[0].get('text', '')
                    logger.info(f"🔍 从列表中提取的text内容:\n{analysis_text}")
                else:
                    # 如果列表中不是字典，将列表元素连接
                    analysis_text = '\n'.join(str(item) for item in analysis_text)
            elif not isinstance(analysis_text, str):
                analysis_text = str(analysis_text)
            
            logger.info(f"🔍 最终处理后的文本内容:\n{analysis_text}")

            lines = analysis_text.strip().split('\n')
            parsed_data = {}
            logger.info(f"🔍 分割后的行数: {len(lines)}")
            
            for i, line in enumerate(lines):
                line = line.strip()
                logger.info(f"🔍 第{i+1}行: '{line}'")
                if ':' in line:
                    key, value = line.split(':', 1)
                    parsed_key = key.strip().lower()
                    parsed_value = value.strip()
                    parsed_data[parsed_key] = parsed_value
                    logger.info(f"🔍 解析键值对: '{parsed_key}' = '{parsed_value}'")
            
            logger.info(f"🔍 最终解析数据: {parsed_data}")
            
            analysis_result['object'] = parsed_data.get('object', '无')
            analysis_result['sence'] = parsed_data.get('sence', parsed_data.get('scene', '无')) # 支持两种拼写
            analysis_result['emotion'] = parsed_data.get('emotion', '无')
            analysis_result['brand_elements'] = parsed_data.get('brand_elements', '无')
            
            logger.info(f"🔍 赋值后的结果:")
            logger.info(f"   object: '{analysis_result['object']}'")
            logger.info(f"   sence: '{analysis_result['sence']}'")
            logger.info(f"   emotion: '{analysis_result['emotion']}'")
            logger.info(f"   brand_elements: '{analysis_result['brand_elements']}'")
            
            try:
                confidence_str = parsed_data.get('confidence', '0.8')
                analysis_result['confidence'] = float(confidence_str if confidence_str and confidence_str.lower() != '无' else '0.8')
            except ValueError:
                analysis_result['confidence'] = 0.8 # 如果转换失败，使用默认值

            # 更新 all_tags (可选，根据新格式调整)
            temp_tags = []
            for key in ['object', 'sence', 'emotion', 'brand_elements']:
                tags_str = analysis_result[key]
                if tags_str and tags_str.lower() != '无':
                    temp_tags.extend([tag.strip() for tag in tags_str.split(',')])
            analysis_result['all_tags'] = list(set(filter(None, temp_tags))) # 去重并移除空字符串
            
        except Exception as e:
            logger.error(f"解析千问2.5新格式分析结果失败: {str(e)}\n原始文本:\n{analysis_text}")
            # 保留默认值或空值
            analysis_result['object'] = '解析失败'
            analysis_result['sence'] = '解析失败'
            analysis_result['emotion'] = '解析失败'
            analysis_result['brand_elements'] = '解析失败'
            analysis_result['confidence'] = 0.0
            
        return analysis_result
    
    def batch_analyze_videos(
        self,
        video_paths: List[str],
        tag_language: str = "中文",
        frame_rate: float = 2.0,
        progress_callback: Optional[callable] = None
    ) -> List[Dict[str, Any]]:
        """
        批量分析视频
        
        Args:
            video_paths: 视频文件路径列表
            tag_language: 标签语言
            frame_rate: 帧率
            progress_callback: 进度回调函数，接受(current, total, message)参数
            
        Returns:
            分析结果列表
        """
        results = []
        total_videos = len(video_paths)
        
        logger.info(f"开始批量分析 {total_videos} 个视频片段")
        
        for i, video_path in enumerate(video_paths):
            try:
                # 更新进度
                if progress_callback:
                    progress_callback(i + 1, total_videos, f"正在分析视频 {i+1}/{total_videos}: {os.path.basename(video_path)}")
                
                # 分析单个视频
                result = self.analyze_video_segment(
                    video_path, tag_language, frame_rate
                )
                
                # 添加视频路径信息到结果中
                result["video_path"] = video_path
                result["video_name"] = os.path.basename(video_path)
                
                results.append(result)
                
                # 记录成功/失败状态
                if result.get("success"):
                    logger.info(f"视频 {i+1}/{total_videos} 分析成功: {os.path.basename(video_path)}")
                else:
                    logger.warning(f"视频 {i+1}/{total_videos} 分析失败: {result.get('error', '未知错误')}")
                    
            except Exception as e:
                error_msg = f"视频 {i+1}/{total_videos} 分析异常: {str(e)}"
                logger.error(error_msg)
                
                # 创建错误结果
                error_result = {
                    "success": False,
                    "error": str(e),
                    "objects": [],
                    "scenes": [],
                    "people": [],
                    "emotions": [],
                    "brands": [],
                    "all_tags": [],
                    "video_path": video_path,
                    "video_name": os.path.basename(video_path)
                }
                results.append(error_result)
        
        # 最终进度更新
        if progress_callback:
            successful_count = sum(1 for r in results if r.get("success"))
            progress_callback(total_videos, total_videos, 
                            f"批量分析完成！成功: {successful_count}/{total_videos}")
        
        logger.info(f"批量分析完成，成功分析 {sum(1 for r in results if r.get('success'))}/{total_videos} 个视频")
        return results
    
    def get_top_tags_by_category(
        self, 
        analysis_results: List[Dict[str, Any]],
        top_n: int = 5
    ) -> Dict[str, List[tuple]]:
        """
        获取各类别的高频标签
        
        Args:
            analysis_results: 分析结果列表
            top_n: 返回前N个高频标签
            
        Returns:
            各类别的高频标签字典
        """
        all_objects = []
        all_scenes = []
        all_people = []
        all_emotions = []
        all_brands = []
        
        for result in analysis_results:
            if result.get("success"):
                # 根据新的数据结构调整这里的标签提取逻辑
                # 例如，如果 'object' 是逗号分隔的字符串:
                object_tags = result.get('object', '')
                if object_tags and object_tags.lower() != '无':
                    all_objects.extend([tag.strip() for tag in object_tags.split(',')])
                
                scene_tags = result.get('sence', '') # 注意拼写 'sence'
                if scene_tags and scene_tags.lower() != '无':
                    all_scenes.extend([tag.strip() for tag in scene_tags.split(',')])

                emotion_tags = result.get('emotion', '')
                if emotion_tags and emotion_tags.lower() != '无':
                    all_emotions.extend([tag.strip() for tag in emotion_tags.split(',')])

                brand_tags = result.get('brand_elements', '')
                if brand_tags and brand_tags.lower() != '无':
                    all_brands.extend([tag.strip() for tag in brand_tags.split(',')])
        
        return {
            'object': Counter(all_objects).most_common(top_n),
            'sence': Counter(all_scenes).most_common(top_n), # 确保键名一致
            'emotion': Counter(all_emotions).most_common(top_n),
            'brand_elements': Counter(all_brands).most_common(top_n)
        }
    
    def _analyze_video_file(
        self,
        video_path: str,
        frame_rate: float = 2.0,
        prompt: str = ""
    ) -> Dict[str, Any]:
        """
        内置的视频文件分析方法
        
        Args:
            video_path: 视频文件路径
            frame_rate: 帧率
            prompt: 分析提示词
            
        Returns:
            分析结果字典
        """
        try:
            import cv2
            import base64
            import tempfile
            import os
            from dashscope import MultiModalConversation
            
            # 提取关键帧
            frames = self._extract_frames(video_path, frame_rate)
            if not frames:
                return {"error": "无法提取视频帧"}
            
            # 编码帧为base64
            encoded_frames = []
            for frame in frames:
                # 将帧保存为临时图像文件
                with tempfile.NamedTemporaryFile(suffix='.jpg', delete=False) as tmp:
                    cv2.imwrite(tmp.name, frame)
                    
                    # 读取并编码为base64
                    with open(tmp.name, 'rb') as f:
                        img_data = f.read()
                        encoded = base64.b64encode(img_data).decode()
                        encoded_frames.append(f"data:image/jpeg;base64,{encoded}")
                    
                    # 清理临时文件
                    os.unlink(tmp.name)
            
            # 构建消息
            content = [{"text": prompt}]
            
            # 添加图像（限制数量以避免token超限）
            max_frames = min(len(encoded_frames), 6)  # 最多6帧
            for i in range(0, max_frames):
                content.append({"image": encoded_frames[i]})
            
            messages = [{"role": "user", "content": content}]
            
            # 调用千问2.5视觉分析
            try:
                response = MultiModalConversation.call(
                    model='qwen-vl-plus',
                    messages=messages
                )
                
                if response.status_code == 200:
                    # 安全地提取分析内容
                    try:
                        content = response.output.choices[0].message.content
                        return {
                            "analysis": content,
                            "frames_analyzed": max_frames
                        }
                    except (AttributeError, IndexError, TypeError) as e:
                        logger.error(f"API响应结构异常: {e}")
                        return {"error": f"API响应格式错误: {e}"}
                else:
                    return {"error": f"API调用失败: 状态码 {response.status_code}"}
                    
            except Exception as api_error:
                # 处理网络连接、代理等错误
                error_msg = str(api_error)
                if "ProxyError" in error_msg or "Max retries exceeded" in error_msg:
                    return {"error": f"网络连接失败，请检查网络设置和代理配置: {error_msg}"}
                elif "HTTPSConnectionPool" in error_msg:
                    return {"error": f"HTTPS连接失败，请检查网络连接: {error_msg}"}
                else:
                    return {"error": f"API调用异常: {error_msg}"}
                
        except ImportError as e:
            logger.error(f"缺少必要的依赖库: {e}")
            return {"error": f"缺少依赖库: {e}"}
        except Exception as e:
            logger.error(f"视频分析失败: {str(e)}")
            return {"error": str(e)}
    
    def _extract_frames(self, video_path: str, frame_rate: float) -> List:
        """
        从视频中提取关键帧
        
        Args:
            video_path: 视频文件路径
            frame_rate: 帧率（每秒几帧）
            
        Returns:
            帧列表
        """
        try:
            import cv2
            
            cap = cv2.VideoCapture(video_path)
            if not cap.isOpened():
                logger.error(f"无法打开视频文件: {video_path}")
                return []
            
            # 获取视频信息
            fps = cap.get(cv2.CAP_PROP_FPS)
            total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
            
            if fps <= 0:
                logger.error("无法获取视频帧率")
                cap.release()
                return []
            
            # 计算采样间隔
            interval = max(1, int(fps / frame_rate))
            
            frames = []
            frame_count = 0
            
            while True:
                ret, frame = cap.read()
                if not ret:
                    break
                
                # 按间隔采样帧
                if frame_count % interval == 0:
                    frames.append(frame)
                
                frame_count += 1
                
                # 限制最大帧数
                if len(frames) >= 8:  # 最多8帧
                    break
            
            cap.release()
            logger.info(f"从视频 {video_path} 提取了 {len(frames)} 帧")
            return frames
            
        except Exception as e:
            logger.error(f"提取视频帧失败: {str(e)}")
            return [] 