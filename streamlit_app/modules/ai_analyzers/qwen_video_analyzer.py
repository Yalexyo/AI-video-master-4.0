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
        """构建分析提示词"""
        return """视频内容分析，提取以下四类标签：

物体：人物、婴幼儿用品、日常物品
场景：室内外环境
情绪：人物表情状态
品牌：奶粉罐、奶瓶、奶粉成分标签等婴幼儿品牌产品

输出格式（用"|"分隔）：
物体：标签1|标签2|标签3
场景：标签1|标签2
情绪：标签1|标签2
品牌：标签1|标签2

无法确定时输出"无"。"""
    
    def _parse_analysis_result(
        self, 
        analysis_text, 
        tag_language: str
    ) -> Dict[str, Any]:
        """解析分析结果"""
        analysis_result = {
            'objects': [],
            'scenes': [],
            'people': [],
            'emotions': [],
            'brands': [],  # 新增品牌标签
            'all_tags': []
        }
        
        try:
            # 确保analysis_text是字符串类型
            if isinstance(analysis_text, list):
                # 如果是列表，尝试连接为字符串
                analysis_text = '\n'.join(str(item) for item in analysis_text)
                logger.warning("分析结果是列表类型，已转换为字符串")
            elif not isinstance(analysis_text, str):
                # 如果不是字符串也不是列表，转换为字符串
                analysis_text = str(analysis_text)
                logger.warning(f"分析结果类型异常({type(analysis_text)})，已转换为字符串")
            
            lines = analysis_text.split('\n')
            for line in lines:
                line = line.strip()
                if ':' in line or '：' in line:
                    # 支持中英文冒号
                    separator = '：' if '：' in line else ':'
                    parts = line.split(separator, 1)
                    if len(parts) == 2:
                        category = parts[0].strip().lower()
                        tags_str = parts[1].strip()
                        
                        if tags_str and tags_str != '-' and tags_str != 'none':
                            # 用|分隔标签
                            tags = [tag.strip() for tag in tags_str.split('|') if tag.strip()]
                            
                            # 分类存储标签
                            if 'object' in category or '物体' in category:
                                analysis_result['objects'].extend(tags)
                            elif 'scene' in category or '场景' in category:
                                analysis_result['scenes'].extend(tags)
                            elif 'people' in category or '人物' in category:
                                analysis_result['people'].extend(tags)
                            elif 'emotion' in category or '情绪' in category or 'expression' in category or '表情' in category:
                                analysis_result['emotions'].extend(tags)
                            elif 'brand' in category or '品牌' in category:
                                analysis_result['brands'].extend(tags)
                            else:
                                # 如果无法归类，根据内容推测分类
                                for tag in tags:
                                    if any(keyword in tag for keyword in ['宝宝', '婴儿', '妈妈', '爸爸', '儿童', '成人', '老人', '男性', '女性']):
                                        analysis_result['people'].append(tag)
                                    elif any(keyword in tag for keyword in ['开心', '微笑', '哭泣', '难过', '生气', '惊讶', '平静', '专注']):
                                        analysis_result['emotions'].append(tag)
                                    elif any(keyword in tag for keyword in ['客厅', '厨房', '卧室', '公园', '室内', '室外']):
                                        analysis_result['scenes'].append(tag)
                                    elif any(keyword in tag for keyword in ['奶粉罐', '奶瓶', '奶粉', '成分标签', '营养标签', '配料表', '品牌标识', '商标']):
                                        analysis_result['brands'].append(tag)
                                    else:
                                        analysis_result['objects'].append(tag)
            
            # 合并所有标签
            all_tags = (analysis_result['objects'] + 
                      analysis_result['scenes'] + 
                      analysis_result['people'] + 
                      analysis_result['emotions'] + 
                      analysis_result['brands'])
            analysis_result['all_tags'] = list(set(all_tags))  # 去重
            
        except Exception as e:
            logger.error(f"解析千问2.5分析结果失败: {str(e)}")
            
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
                all_objects.extend(result.get('objects', []))
                all_scenes.extend(result.get('scenes', []))
                all_people.extend(result.get('people', []))
                all_emotions.extend(result.get('emotions', []))
                all_brands.extend(result.get('brands', []))
        
        return {
            'objects': Counter(all_objects).most_common(top_n),
            'scenes': Counter(all_scenes).most_common(top_n),
            'people': Counter(all_people).most_common(top_n),
            'emotions': Counter(all_emotions).most_common(top_n),
            'brands': Counter(all_brands).most_common(top_n)
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