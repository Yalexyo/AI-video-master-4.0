"""
Google Cloud Video Intelligence API 分析器

专门处理Google Cloud视频分析功能的模块
"""

import os
import time
import logging
from typing import Dict, Any, List, Tuple, Optional
from pathlib import Path

logger = logging.getLogger(__name__)


class GoogleVideoAnalyzer:
    """Google Cloud Video Intelligence API 分析器"""
    
    def __init__(self, credentials_path: Optional[str] = None):
        """
        初始化Google Cloud分析器
        
        Args:
            credentials_path: Google Cloud凭据文件路径
        """
        # 默认凭据路径，用户可以通过参数覆盖
        default_cred_path = "data/temp/google_cloud/video-ai-461014-d0c437ff635f.json"
        
        self.credentials_path = (
            credentials_path or 
            os.environ.get("GOOGLE_APPLICATION_CREDENTIALS") or
            default_cred_path
        )
        self.client = None
        
        # 设置环境变量
        if self.credentials_path and os.path.exists(self.credentials_path):
            os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = self.credentials_path
            logger.info(f"使用Google Cloud凭据: {self.credentials_path}")
        else:
            logger.warning(f"Google Cloud凭据文件不存在: {self.credentials_path}")
            
        self._initialize_client()
    
    def _initialize_client(self):
        """初始化Google Cloud客户端"""
        try:
            from google.cloud import videointelligence_v1 as vi
            self.client = vi.VideoIntelligenceServiceClient()
            logger.info("Google Cloud Video Intelligence客户端初始化成功")
        except Exception as e:
            logger.error(f"Google Cloud客户端初始化失败: {str(e)}")
            self.client = None
    
    def check_credentials(self) -> Tuple[bool, Optional[str]]:
        """检查Google Cloud凭据是否有效"""
        if self.credentials_path and os.path.exists(self.credentials_path):
            try:
                # 验证JSON文件格式
                import json
                with open(self.credentials_path, 'r', encoding='utf-8') as f:
                    cred_data = json.load(f)
                    
                # 检查必要字段
                required_fields = ['type', 'project_id', 'private_key', 'client_email']
                if all(field in cred_data for field in required_fields):
                    logger.info(f"Google Cloud凭据有效，项目ID: {cred_data.get('project_id', 'Unknown')}")
                    return True, self.credentials_path
                else:
                    logger.error("Google Cloud凭据文件缺少必要字段")
                    return False, None
            except Exception as e:
                logger.error(f"Google Cloud凭据文件验证失败: {str(e)}")
                return False, None
        else:
            logger.warning(f"Google Cloud凭据文件不存在: {self.credentials_path}")
            return False, None
    
    def analyze_video(
        self,
        video_path: Optional[str] = None,
        video_uri: Optional[str] = None,
        features: List[str] = None,
        progress_callback: Optional[callable] = None
    ) -> Dict[str, Any]:
        """
        分析视频内容
        
        Args:
            video_path: 本地视频文件路径
            video_uri: 云端视频URI（如gs://bucket/video.mp4）
            features: 要分析的功能列表
            progress_callback: 进度回调函数
            
        Returns:
            分析结果字典
        """
        if not self.client:
            raise Exception("Google Cloud客户端未初始化")
        
        # 检查网络连接
        if progress_callback:
            progress_callback(5, "检查网络连接和服务可用性...")
        
        try:
            import requests
            # 快速检查Google Cloud服务可用性
            response = requests.get("https://videointelligence.googleapis.com", timeout=10)
            logger.info("Google Cloud Video Intelligence服务连接正常")
        except Exception as e:
            error_msg = f"无法连接到Google Cloud服务，请检查网络连接: {str(e)}"
            logger.error(error_msg)
            return {"success": False, "error": error_msg}
            
        try:
            from google.cloud import videointelligence_v1 as vi
            
            # 默认功能
            if not features:
                features = ["shot_detection", "label_detection"]
            
            # 转换功能名称为API枚举
            feature_map = {
                "shot_detection": vi.Feature.SHOT_CHANGE_DETECTION,
                "label_detection": vi.Feature.LABEL_DETECTION, 
                "text_detection": vi.Feature.TEXT_DETECTION,
                "face_detection": vi.Feature.FACE_DETECTION,
                "object_tracking": vi.Feature.OBJECT_TRACKING
            }
            
            api_features = [feature_map[f] for f in features if f in feature_map]
            
            # 构建请求
            if video_path and os.path.exists(video_path):
                # 检查文件大小
                file_size = os.path.getsize(video_path)
                file_size_mb = file_size / (1024 * 1024)
                
                if progress_callback:
                    progress_callback(15, f"准备上传视频文件 ({file_size_mb:.1f}MB)...")
                
                # 大文件警告
                if file_size_mb > 200:
                    logger.warning(f"视频文件较大 ({file_size_mb:.1f}MB)，分析可能需要较长时间")
                    if progress_callback:
                        progress_callback(20, f"视频文件较大 ({file_size_mb:.1f}MB)，预计需要5-15分钟...")
                elif file_size_mb > 50:
                    if progress_callback:
                        progress_callback(20, f"视频文件大小适中 ({file_size_mb:.1f}MB)，预计需要2-5分钟...")
                else:
                    if progress_callback:
                        progress_callback(20, f"视频文件较小 ({file_size_mb:.1f}MB)，预计1-2分钟完成...")
                
                # 本地文件
                with open(video_path, "rb") as f:
                    input_content = f.read()
                request = {"features": api_features, "input_content": input_content}
            elif video_uri:
                # 云端文件
                request = {"features": api_features, "input_uri": video_uri}
            else:
                raise ValueError("必须提供video_path或video_uri")
            
            # 执行分析
            if progress_callback:
                progress_callback(30, f"分析请求已提交，操作ID: {operation.operation.name}")
            
            # 等待完成
            start_time = time.time()
            timeout = 1200  # 增加到20分钟超时
            check_interval = 10  # 每10秒检查一次
            
            if progress_callback:
                progress_callback(35, "分析任务已提交到Google Cloud，正在处理...")
            
            while not operation.done():
                elapsed = time.time() - start_time
                if elapsed > timeout:
                    error_msg = f"分析超时（{timeout}秒），视频可能太大或网络较慢"
                    logger.error(error_msg)
                    raise TimeoutError(error_msg)
                
                if progress_callback:
                    # 非线性进度计算，前期慢后期快
                    progress_ratio = min(elapsed / timeout, 0.8)
                    progress = 35 + int(progress_ratio * 55)  # 35-90%
                    
                    # 估算剩余时间
                    if elapsed > 30:  # 30秒后开始估算
                        estimated_total = elapsed / progress_ratio if progress_ratio > 0 else timeout
                        remaining = max(0, estimated_total - elapsed)
                        progress_callback(
                            progress, 
                            f"分析进行中... 已用时 {elapsed:.0f}秒，预计还需 {remaining:.0f}秒"
                        )
                    else:
                        progress_callback(progress, f"分析进行中... 已用时 {elapsed:.0f}秒")
                
                time.sleep(check_interval)
            
            result = operation.result()
            
            if progress_callback:
                progress_callback(100, "分析完成！")
            
            return {
                "success": True,
                "result": result,
                "features": features,
                "video_path": video_path,
                "video_uri": video_uri
            }
            
        except Exception as e:
            logger.error(f"Google Cloud视频分析失败: {str(e)}")
            return {
                "success": False,
                "error": str(e),
                "features": features
            }
    
    def extract_shots(self, analysis_result: Dict[str, Any]) -> List[Dict[str, Any]]:
        """从分析结果中提取镜头信息"""
        shots = []
        
        if not analysis_result.get("success") or not analysis_result.get("result"):
            return shots
            
        result = analysis_result["result"]
        if not result.annotation_results:
            return shots
            
        annotation = result.annotation_results[0]
        
        if hasattr(annotation, 'shot_annotations') and annotation.shot_annotations:
            for i, shot in enumerate(annotation.shot_annotations):
                try:
                    start_time = self._get_time_seconds(shot.start_time_offset)
                    end_time = self._get_time_seconds(shot.end_time_offset)
                    
                    shots.append({
                        'index': i + 1,
                        'start_time': start_time,
                        'end_time': end_time,
                        'duration': end_time - start_time,
                        'type': f"镜头{i+1}",
                        'confidence': 1.0
                    })
                except Exception as e:
                    logger.warning(f"处理镜头 {i+1} 时出错: {e}")
                    
        return shots
    
    def extract_labels(self, analysis_result: Dict[str, Any]) -> List[Dict[str, Any]]:
        """从分析结果中提取标签信息"""
        labels = []
        
        if not analysis_result.get("success") or not analysis_result.get("result"):
            return labels
            
        result = analysis_result["result"]
        if not result.annotation_results:
            return labels
            
        annotation = result.annotation_results[0]
        
        if hasattr(annotation, 'segment_label_annotations') and annotation.segment_label_annotations:
            for label in annotation.segment_label_annotations:
                label_name = label.entity.description
                
                for segment in label.segments:
                    try:
                        start_time = self._get_time_seconds(segment.segment.start_time_offset)
                        end_time = self._get_time_seconds(segment.segment.end_time_offset)
                        confidence = segment.confidence
                        
                        labels.append({
                            'label': label_name,
                            'start_time': start_time,
                            'end_time': end_time,
                            'duration': end_time - start_time,
                            'confidence': confidence,
                            'type': f"标签_{label_name}"
                        })
                    except Exception as e:
                        logger.warning(f"处理标签 {label_name} 时出错: {e}")
                        
        return labels
    
    def extract_faces(self, analysis_result: Dict[str, Any]) -> List[Dict[str, Any]]:
        """从分析结果中提取人脸信息"""
        faces = []
        
        if not analysis_result.get("success") or not analysis_result.get("result"):
            return faces
            
        result = analysis_result["result"]
        if not result.annotation_results:
            return faces
            
        annotation = result.annotation_results[0]
        
        if hasattr(annotation, 'face_annotations') and annotation.face_annotations:
            for i, face in enumerate(annotation.face_annotations):
                for j, segment in enumerate(face.segments):
                    try:
                        start_time = self._get_time_seconds(segment.segment.start_time_offset)
                        end_time = self._get_time_seconds(segment.segment.end_time_offset)
                        
                        faces.append({
                            'face_id': i + 1,
                            'segment_id': j + 1,
                            'start_time': start_time,
                            'end_time': end_time,
                            'duration': end_time - start_time,
                            'type': f"人脸{i+1}_片段{j+1}",
                            'confidence': 1.0
                        })
                    except Exception as e:
                        logger.warning(f"处理人脸 {i+1} 片段 {j+1} 时出错: {e}")
                        
        return faces
    
    def _get_time_seconds(self, time_offset) -> float:
        """安全地获取时间偏移的秒数"""
        try:
            if hasattr(time_offset, 'total_seconds'):
                return time_offset.total_seconds()
            elif hasattr(time_offset, 'seconds'):
                # 处理 protobuf Duration 对象
                return time_offset.seconds + time_offset.nanos / 1e9
            else:
                # 如果是数字，直接返回
                return float(time_offset)
        except Exception as e:
            logger.warning(f"时间解析错误: {e}")
            return 0.0
    
    def validate_shot_continuity(self, shots: List[Dict[str, Any]]) -> Dict[str, Any]:
        """验证镜头的时间连贯性"""
        if not shots:
            return {"valid": True, "gaps": [], "overlaps": []}
        
        gaps = []
        overlaps = []
        
        # 检查是否从0开始
        first_start = shots[0]['start_time']
        if first_start > 0.1:  # 允许0.1秒的误差
            gaps.append(f"视频开头有空隙: 0.00s - {first_start:.2f}s")
        
        # 检查相邻镜头之间的连贯性
        for i in range(len(shots) - 1):
            current_end = shots[i]['end_time']
            next_start = shots[i+1]['start_time']
            
            gap = next_start - current_end
            if abs(gap) > 0.1:  # 允许0.1秒的误差
                if gap > 0:
                    gaps.append(f"镜头{i+1}和{i+2}之间有空隙: {gap:.2f}s")
                else:
                    overlaps.append(f"镜头{i+1}和{i+2}有重叠: {abs(gap):.2f}s")
        
        return {
            "valid": len(gaps) == 0 and len(overlaps) == 0,
            "gaps": gaps,
            "overlaps": overlaps,
            "total_shots": len(shots),
            "total_duration": shots[-1]['end_time'] - shots[0]['start_time'] if shots else 0
        } 