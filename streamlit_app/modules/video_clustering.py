"""
视频镜头聚类模块

基于视觉特征的镜头聚类，将相似的细碎镜头合并成有意义的场景
"""

import os
import cv2
import numpy as np
import logging
from typing import List, Dict, Any, Tuple, Optional
from pathlib import Path
import tempfile
from sklearn.cluster import AgglomerativeClustering
from sklearn.metrics.pairwise import cosine_similarity
from sklearn.preprocessing import StandardScaler

logger = logging.getLogger(__name__)


class ShotClusterer:
    """镜头聚类器 - 基于视觉特征聚类相似镜头"""
    
    def __init__(self, similarity_threshold: float = 0.8, min_cluster_duration: float = 3.0):
        """
        初始化镜头聚类器
        
        Args:
            similarity_threshold: 相似度阈值 (0-1)
            min_cluster_duration: 最小聚类持续时间（秒）
        """
        self.similarity_threshold = similarity_threshold
        self.min_cluster_duration = min_cluster_duration
        
    def cluster_shots(
        self, 
        shots: List[Dict[str, Any]], 
        video_path: str,
        max_clusters: Optional[int] = None
    ) -> List[Dict[str, Any]]:
        """
        对镜头进行聚类，合并相似的镜头
        
        Args:
            shots: 镜头列表
            video_path: 原始视频路径
            max_clusters: 最大聚类数量（None表示自动确定）
            
        Returns:
            聚类后的场景列表
        """
        if len(shots) <= 2:
            logger.info("镜头数量太少，无需聚类")
            return self._convert_shots_to_scenes(shots)
        
        logger.info(f"开始对 {len(shots)} 个镜头进行视觉特征聚类...")
        
        try:
            # 1. 提取每个镜头的视觉特征
            features = self._extract_shot_features(shots, video_path)
            if features is None or len(features) == 0:
                logger.warning("无法提取视觉特征，返回原始镜头")
                return self._convert_shots_to_scenes(shots)
            
            # 2. 计算镜头相似度矩阵
            similarity_matrix = self._compute_similarity_matrix(features)
            
            # 3. 执行聚类
            clusters = self._perform_clustering(similarity_matrix, max_clusters)
            
            # 4. 合并聚类结果
            clustered_scenes = self._merge_shots_by_clusters(shots, clusters)
            
            # 5. 后处理：合并过短的场景
            final_scenes = self._post_process_scenes(clustered_scenes)
            
            logger.info(f"聚类完成：{len(shots)} 个镜头 → {len(final_scenes)} 个场景")
            
            # 6. 记录聚类统计
            self._log_clustering_statistics(shots, final_scenes)
            
            return final_scenes
            
        except Exception as e:
            logger.error(f"镜头聚类失败: {str(e)}")
            return self._convert_shots_to_scenes(shots)
    
    def _extract_shot_features(
        self, 
        shots: List[Dict[str, Any]], 
        video_path: str
    ) -> Optional[np.ndarray]:
        """提取每个镜头的视觉特征"""
        if not os.path.exists(video_path):
            logger.error(f"视频文件不存在: {video_path}")
            return None
        
        features = []
        cap = cv2.VideoCapture(video_path)
        
        if not cap.isOpened():
            logger.error(f"无法打开视频文件: {video_path}")
            return None
        
        fps = cap.get(cv2.CAP_PROP_FPS)
        
        for i, shot in enumerate(shots):
            try:
                # 计算镜头中间时间点
                mid_time = (shot['start_time'] + shot['end_time']) / 2
                frame_number = int(mid_time * fps)
                
                # 定位到该帧
                cap.set(cv2.CAP_PROP_POS_FRAMES, frame_number)
                ret, frame = cap.read()
                
                if ret:
                    # 提取多种视觉特征
                    feature_vector = self._extract_frame_features(frame)
                    features.append(feature_vector)
                else:
                    logger.warning(f"无法读取镜头 {i+1} 的关键帧")
                    # 使用零向量作为默认特征
                    features.append(np.zeros(self._get_feature_dimension()))
                    
            except Exception as e:
                logger.warning(f"提取镜头 {i+1} 特征失败: {str(e)}")
                features.append(np.zeros(self._get_feature_dimension()))
        
        cap.release()
        
        if not features:
            return None
        
        # 标准化特征
        features_array = np.array(features)
        scaler = StandardScaler()
        normalized_features = scaler.fit_transform(features_array)
        
        logger.info(f"成功提取 {len(features)} 个镜头的视觉特征，特征维度: {normalized_features.shape[1]}")
        return normalized_features
    
    def _extract_frame_features(self, frame: np.ndarray) -> np.ndarray:
        """从单帧图像中提取视觉特征"""
        features = []
        
        # 1. 颜色直方图特征
        color_features = self._extract_color_histogram(frame)
        features.extend(color_features)
        
        # 2. 纹理特征（LBP）
        texture_features = self._extract_texture_features(frame)
        features.extend(texture_features)
        
        # 3. 边缘特征
        edge_features = self._extract_edge_features(frame)
        features.extend(edge_features)
        
        # 4. 亮度和对比度特征
        brightness_features = self._extract_brightness_features(frame)
        features.extend(brightness_features)
        
        return np.array(features)
    
    def _extract_color_histogram(self, frame: np.ndarray, bins: int = 32) -> List[float]:
        """提取颜色直方图特征"""
        # 转换到HSV色彩空间
        hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)
        
        # 分别计算H、S、V通道的直方图
        h_hist = cv2.calcHist([hsv], [0], None, [bins], [0, 180])
        s_hist = cv2.calcHist([hsv], [1], None, [bins], [0, 256])
        v_hist = cv2.calcHist([hsv], [2], None, [bins], [0, 256])
        
        # 归一化
        h_hist = h_hist.flatten() / h_hist.sum()
        s_hist = s_hist.flatten() / s_hist.sum()
        v_hist = v_hist.flatten() / v_hist.sum()
        
        return np.concatenate([h_hist, s_hist, v_hist]).tolist()
    
    def _extract_texture_features(self, frame: np.ndarray) -> List[float]:
        """提取纹理特征（简化版LBP）"""
        # 转换为灰度图
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        
        # 缩小图像以减少计算量
        small_gray = cv2.resize(gray, (64, 64))
        
        # 计算简单的纹理统计
        # 1. 标准差（衡量纹理复杂度）
        texture_std = np.std(small_gray)
        
        # 2. 梯度幅值的平均值
        grad_x = cv2.Sobel(small_gray, cv2.CV_64F, 1, 0, ksize=3)
        grad_y = cv2.Sobel(small_gray, cv2.CV_64F, 0, 1, ksize=3)
        grad_magnitude = np.sqrt(grad_x**2 + grad_y**2)
        avg_gradient = np.mean(grad_magnitude)
        
        # 3. 局部二值模式（简化版）
        lbp_hist = self._simple_lbp_histogram(small_gray)
        
        return [texture_std, avg_gradient] + lbp_hist
    
    def _simple_lbp_histogram(self, gray_image: np.ndarray, bins: int = 16) -> List[float]:
        """计算简化的局部二值模式直方图"""
        h, w = gray_image.shape
        lbp_codes = []
        
        # 对每个像素计算简单的LBP码
        for i in range(1, h-1):
            for j in range(1, w-1):
                center = gray_image[i, j]
                code = 0
                
                # 检查8个邻居
                neighbors = [
                    gray_image[i-1, j-1], gray_image[i-1, j], gray_image[i-1, j+1],
                    gray_image[i, j+1], gray_image[i+1, j+1], gray_image[i+1, j],
                    gray_image[i+1, j-1], gray_image[i, j-1]
                ]
                
                for k, neighbor in enumerate(neighbors):
                    if neighbor >= center:
                        code |= (1 << k)
                
                lbp_codes.append(code % bins)
        
        # 计算直方图
        hist, _ = np.histogram(lbp_codes, bins=bins, range=(0, bins))
        hist = hist.astype(float)
        hist = hist / hist.sum() if hist.sum() > 0 else hist
        
        return hist.tolist()
    
    def _extract_edge_features(self, frame: np.ndarray) -> List[float]:
        """提取边缘特征"""
        # 转换为灰度图
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        
        # Canny边缘检测
        edges = cv2.Canny(gray, 50, 150)
        
        # 统计边缘像素比例
        edge_ratio = np.sum(edges > 0) / edges.size
        
        # 边缘密度分布（将图像分成4x4网格）
        h, w = edges.shape
        grid_h, grid_w = h // 4, w // 4
        edge_densities = []
        
        for i in range(4):
            for j in range(4):
                y1, y2 = i * grid_h, min((i + 1) * grid_h, h)
                x1, x2 = j * grid_w, min((j + 1) * grid_w, w)
                grid_edges = edges[y1:y2, x1:x2]
                density = np.sum(grid_edges > 0) / grid_edges.size
                edge_densities.append(density)
        
        return [edge_ratio] + edge_densities
    
    def _extract_brightness_features(self, frame: np.ndarray) -> List[float]:
        """提取亮度和对比度特征"""
        # 转换为灰度图
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        
        # 亮度统计
        mean_brightness = np.mean(gray)
        std_brightness = np.std(gray)
        
        # 对比度（标准差）
        contrast = std_brightness
        
        # 动态范围
        dynamic_range = np.max(gray) - np.min(gray)
        
        return [mean_brightness, std_brightness, contrast, dynamic_range]
    
    def _get_feature_dimension(self) -> int:
        """获取特征向量的维度"""
        # 颜色直方图: 32*3 = 96
        # 纹理特征: 2 + 16 = 18
        # 边缘特征: 1 + 16 = 17
        # 亮度特征: 4
        return 96 + 18 + 17 + 4  # 总计135维
    
    def _compute_similarity_matrix(self, features: np.ndarray) -> np.ndarray:
        """计算镜头间的相似度矩阵"""
        # 使用余弦相似度
        similarity_matrix = cosine_similarity(features)
        logger.info(f"计算相似度矩阵完成，形状: {similarity_matrix.shape}")
        return similarity_matrix
    
    def _perform_clustering(
        self, 
        similarity_matrix: np.ndarray, 
        max_clusters: Optional[int] = None
    ) -> np.ndarray:
        """执行层次聚类"""
        n_shots = similarity_matrix.shape[0]
        
        # 转换相似度为距离
        distance_matrix = 1 - similarity_matrix
        
        # 确定聚类数量
        if max_clusters is None:
            # 自动确定聚类数：基于相似度阈值
            n_clusters = self._estimate_optimal_clusters(similarity_matrix)
        else:
            n_clusters = min(max_clusters, n_shots)
        
        logger.info(f"使用层次聚类，目标聚类数: {n_clusters}")
        
        # 执行聚类
        clustering = AgglomerativeClustering(
            n_clusters=n_clusters,
            metric='precomputed',
            linkage='average'
        )
        
        cluster_labels = clustering.fit_predict(distance_matrix)
        
        logger.info(f"聚类完成，生成 {len(set(cluster_labels))} 个聚类")
        return cluster_labels
    
    def _estimate_optimal_clusters(self, similarity_matrix: np.ndarray) -> int:
        """基于相似度阈值估计最优聚类数"""
        n_shots = similarity_matrix.shape[0]
        
        # 计算每对镜头的相似度，统计高相似度的对数
        high_similarity_pairs = 0
        total_pairs = 0
        
        for i in range(n_shots):
            for j in range(i + 1, n_shots):
                similarity = similarity_matrix[i, j]
                if similarity > self.similarity_threshold:
                    high_similarity_pairs += 1
                total_pairs += 1
        
        # 基于高相似度比例估计聚类数
        if total_pairs == 0:
            return n_shots
        
        similarity_ratio = high_similarity_pairs / total_pairs
        
        if similarity_ratio > 0.5:
            # 高相似度，较少聚类
            estimated_clusters = max(2, n_shots // 3)
        elif similarity_ratio > 0.3:
            # 中等相似度
            estimated_clusters = max(2, n_shots // 2)
        else:
            # 低相似度，保持较多聚类
            estimated_clusters = max(2, int(n_shots * 0.8))
        
        logger.info(f"相似度比例: {similarity_ratio:.2f}, 估计聚类数: {estimated_clusters}")
        return min(estimated_clusters, n_shots)
    
    def _merge_shots_by_clusters(
        self, 
        shots: List[Dict[str, Any]], 
        cluster_labels: np.ndarray
    ) -> List[Dict[str, Any]]:
        """根据聚类结果合并镜头"""
        clustered_scenes = []
        
        # 按聚类标签分组
        clusters = {}
        for shot_idx, cluster_id in enumerate(cluster_labels):
            if cluster_id not in clusters:
                clusters[cluster_id] = []
            clusters[cluster_id].append(shots[shot_idx])
        
        # 合并每个聚类中的镜头
        for cluster_id, cluster_shots in clusters.items():
            # 按时间排序
            cluster_shots.sort(key=lambda x: x['start_time'])
            
            # 创建场景
            scene = {
                'cluster_id': cluster_id,
                'start_time': cluster_shots[0]['start_time'],
                'end_time': cluster_shots[-1]['end_time'],
                'duration': cluster_shots[-1]['end_time'] - cluster_shots[0]['start_time'],
                'shot_count': len(cluster_shots),
                'type': f"场景{cluster_id + 1}",
                'confidence': 0.95,
                'shots': cluster_shots
            }
            
            clustered_scenes.append(scene)
        
        # 按开始时间排序
        clustered_scenes.sort(key=lambda x: x['start_time'])
        
        # 重新编号
        for i, scene in enumerate(clustered_scenes):
            scene['index'] = i + 1
            scene['type'] = f"场景{i + 1}"
        
        return clustered_scenes
    
    def _post_process_scenes(
        self, 
        scenes: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """后处理：合并过短的场景"""
        if not scenes:
            return scenes
        
        processed_scenes = []
        current_scene = scenes[0].copy()
        
        for i in range(1, len(scenes)):
            next_scene = scenes[i]
            
            # 如果当前场景太短，尝试与下一个场景合并
            if current_scene['duration'] < self.min_cluster_duration:
                # 检查时间是否连续
                gap = next_scene['start_time'] - current_scene['end_time']
                
                if gap <= 1.0:  # 允许1秒的间隙
                    # 合并场景
                    merged_scene = {
                        'cluster_id': f"{current_scene['cluster_id']}-{next_scene['cluster_id']}",
                        'start_time': current_scene['start_time'],
                        'end_time': next_scene['end_time'],
                        'duration': next_scene['end_time'] - current_scene['start_time'],
                        'shot_count': current_scene['shot_count'] + next_scene['shot_count'],
                        'type': f"合并场景",
                        'confidence': min(current_scene['confidence'], next_scene['confidence']),
                        'shots': current_scene['shots'] + next_scene['shots']
                    }
                    current_scene = merged_scene
                    continue
            
            # 无法合并，保存当前场景
            processed_scenes.append(current_scene)
            current_scene = next_scene.copy()
        
        # 添加最后一个场景
        processed_scenes.append(current_scene)
        
        # 重新编号
        for i, scene in enumerate(processed_scenes):
            scene['index'] = i + 1
            scene['type'] = f"场景{i + 1}"
        
        return processed_scenes
    
    def _convert_shots_to_scenes(self, shots: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """将镜头直接转换为场景（无聚类）"""
        scenes = []
        for i, shot in enumerate(shots):
            scene = shot.copy()
            scene['cluster_id'] = i
            scene['shot_count'] = 1
            scene['type'] = f"场景{i + 1}"
            scene['shots'] = [shot]
            scenes.append(scene)
        return scenes
    
    def _log_clustering_statistics(
        self, 
        original_shots: List[Dict[str, Any]], 
        clustered_scenes: List[Dict[str, Any]]
    ):
        """记录聚类统计信息"""
        original_count = len(original_shots)
        clustered_count = len(clustered_scenes)
        reduction_ratio = (original_count - clustered_count) / original_count * 100
        
        avg_original_duration = np.mean([s['duration'] for s in original_shots])
        avg_clustered_duration = np.mean([s['duration'] for s in clustered_scenes])
        
        logger.info("=" * 50)
        logger.info("镜头聚类统计信息:")
        logger.info(f"原始镜头数: {original_count}")
        logger.info(f"聚类后场景数: {clustered_count}")
        logger.info(f"减少比例: {reduction_ratio:.1f}%")
        logger.info(f"原始平均时长: {avg_original_duration:.2f}秒")
        logger.info(f"聚类后平均时长: {avg_clustered_duration:.2f}秒")
        
        # 详细的场景信息
        for scene in clustered_scenes:
            shot_indices = [shot['index'] for shot in scene['shots']]
            logger.info(f"场景{scene['index']}: {scene['duration']:.2f}秒, "
                       f"包含镜头 {shot_indices}, "
                       f"({scene['start_time']:.2f}s - {scene['end_time']:.2f}s)")
        
        logger.info("=" * 50)

    def _extract_segment_features(
        self, 
        segment_files: List[Path], 
        progress_callback=None
    ) -> Optional[np.ndarray]:
        """从视频片段文件中提取视觉特征"""
        features = []
        total_files = len(segment_files)
        
        for i, segment_file in enumerate(segment_files):
            try:
                if progress_callback:
                    progress = 20 + (i / total_files) * 40  # 20%-60%的进度范围
                    progress_callback(int(progress), f"分析片段 {i+1}/{total_files}: {segment_file.name}")
                
                # 打开视频片段
                cap = cv2.VideoCapture(str(segment_file))
                if not cap.isOpened():
                    logger.warning(f"无法打开片段文件: {segment_file}")
                    features.append(np.zeros(self._get_feature_dimension()))
                    continue
                
                # 读取中间帧作为代表帧
                total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
                middle_frame = total_frames // 2
                
                cap.set(cv2.CAP_PROP_POS_FRAMES, middle_frame)
                ret, frame = cap.read()
                
                if ret:
                    feature_vector = self._extract_frame_features(frame)
                    features.append(feature_vector)
                else:
                    logger.warning(f"无法读取片段 {segment_file.name} 的关键帧")
                    features.append(np.zeros(self._get_feature_dimension()))
                
                cap.release()
                
            except Exception as e:
                logger.warning(f"提取片段 {segment_file.name} 特征失败: {str(e)}")
                features.append(np.zeros(self._get_feature_dimension()))
        
        if not features:
            return None
        
        # 标准化特征
        features_array = np.array(features)
        scaler = StandardScaler()
        normalized_features = scaler.fit_transform(features_array)
        
        logger.info(f"成功提取 {len(features)} 个片段的视觉特征，特征维度: {normalized_features.shape[1]}")
        return normalized_features
    
    def _convert_segments_to_scenes(self, shots: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """将片段转换为场景格式（不聚类）"""
        scenes = []
        for i, shot in enumerate(shots):
            scene = {
                'index': i + 1,
                'start_time': shot['start_time'],
                'end_time': shot['end_time'],
                'duration': shot['duration'],
                'type': f"scene_{i+1}",
                'confidence': shot['confidence'],
                'segment_count': 1,
                'segments': [shot],
                'file_paths': [shot['file_path']]
            }
            scenes.append(scene)
        return scenes
    
    def _merge_segments_by_clusters(
        self, 
        shots: List[Dict[str, Any]], 
        cluster_labels: np.ndarray
    ) -> List[Dict[str, Any]]:
        """根据聚类标签合并片段"""
        scenes = {}
        
        # 按聚类标签分组
        for shot, cluster_id in zip(shots, cluster_labels):
            if cluster_id not in scenes:
                scenes[cluster_id] = {
                    'segments': [],
                    'file_paths': []
                }
            scenes[cluster_id]['segments'].append(shot)
            scenes[cluster_id]['file_paths'].append(shot['file_path'])
        
        # 创建场景对象
        clustered_scenes = []
        for cluster_id, scene_data in scenes.items():
            segments = scene_data['segments']
            
            # 按开始时间排序
            segments.sort(key=lambda x: x['start_time'])
            
            # 计算场景统计信息
            start_time = min(seg['start_time'] for seg in segments)
            end_time = max(seg['end_time'] for seg in segments)
            total_duration = sum(seg['duration'] for seg in segments)
            avg_confidence = sum(seg['confidence'] for seg in segments) / len(segments)
            
            scene = {
                'index': len(clustered_scenes) + 1,
                'start_time': start_time,
                'end_time': end_time,
                'duration': total_duration,
                'type': f"clustered_scene_{cluster_id}",
                'confidence': avg_confidence,
                'segment_count': len(segments),
                'segments': segments,
                'file_paths': scene_data['file_paths'],
                'cluster_id': cluster_id
            }
            clustered_scenes.append(scene)
        
        # 按开始时间排序
        clustered_scenes.sort(key=lambda x: x['start_time'])
        
        # 重新分配索引
        for i, scene in enumerate(clustered_scenes):
            scene['index'] = i + 1
            scene['type'] = f"scene_{i+1}"
        
        return clustered_scenes
    
    def _post_process_segment_scenes(
        self, 
        scenes: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """后处理片段场景：合并过短的场景"""
        if len(scenes) <= 1:
            return scenes
        
        # 按时长排序，优先合并最短的场景
        processed_scenes = scenes.copy()
        
        # 多轮合并，直到没有过短的场景
        max_iterations = 5
        for iteration in range(max_iterations):
            short_scenes = [s for s in processed_scenes if s['duration'] < self.min_cluster_duration]
            
            if not short_scenes:
                break  # 没有过短场景，结束
            
            # 找到最短的场景
            shortest_scene = min(short_scenes, key=lambda x: x['duration'])
            shortest_idx = processed_scenes.index(shortest_scene)
            
            # 寻找最相似的邻近场景进行合并
            best_merge_idx = None
            best_similarity = -1
            
            # 检查前后邻居
            candidates = []
            if shortest_idx > 0:
                candidates.append(shortest_idx - 1)
            if shortest_idx < len(processed_scenes) - 1:
                candidates.append(shortest_idx + 1)
            
            for candidate_idx in candidates:
                # 简单的相似度计算（基于持续时间和片段数量）
                candidate = processed_scenes[candidate_idx]
                duration_similarity = 1.0 / (1.0 + abs(candidate['duration'] - shortest_scene['duration']))
                count_similarity = 1.0 / (1.0 + abs(candidate['segment_count'] - shortest_scene['segment_count']))
                similarity = (duration_similarity + count_similarity) / 2
                
                if similarity > best_similarity:
                    best_similarity = similarity
                    best_merge_idx = candidate_idx
            
            # 执行合并
            if best_merge_idx is not None:
                target_scene = processed_scenes[best_merge_idx]
                
                # 合并场景数据
                merged_scene = {
                    'index': min(shortest_scene['index'], target_scene['index']),
                    'start_time': min(shortest_scene['start_time'], target_scene['start_time']),
                    'end_time': max(shortest_scene['end_time'], target_scene['end_time']),
                    'duration': shortest_scene['duration'] + target_scene['duration'],
                    'type': f"merged_scene_{min(shortest_scene['index'], target_scene['index'])}",
                    'confidence': (shortest_scene['confidence'] + target_scene['confidence']) / 2,
                    'segment_count': shortest_scene['segment_count'] + target_scene['segment_count'],
                    'segments': shortest_scene['segments'] + target_scene['segments'],
                    'file_paths': shortest_scene['file_paths'] + target_scene['file_paths']
                }
                
                # 移除原场景，添加合并后的场景
                processed_scenes.remove(shortest_scene)
                processed_scenes.remove(target_scene)
                processed_scenes.append(merged_scene)
                
                # 重新排序
                processed_scenes.sort(key=lambda x: x['start_time'])
            else:
                # 无法合并，保留原场景
                break
        
        # 重新分配索引和类型
        for i, scene in enumerate(processed_scenes):
            scene['index'] = i + 1
            scene['type'] = f"scene_{i+1}"
        
        logger.info(f"后处理完成：{len(scenes)} → {len(processed_scenes)} 个场景")
        return processed_scenes


def cluster_video_shots(
    shots: List[Dict[str, Any]], 
    video_path: str,
    similarity_threshold: float = 0.75,
    min_cluster_duration: float = 3.0,
    max_clusters: Optional[int] = None
) -> List[Dict[str, Any]]:
    """
    便捷函数：对视频镜头进行聚类
    
    Args:
        shots: 镜头列表
        video_path: 视频文件路径
        similarity_threshold: 相似度阈值
        min_cluster_duration: 最小聚类持续时间
        max_clusters: 最大聚类数量
        
    Returns:
        聚类后的场景列表
    """
    clusterer = ShotClusterer(
        similarity_threshold=similarity_threshold,
        min_cluster_duration=min_cluster_duration
    )
    
    return clusterer.cluster_shots(shots, video_path, max_clusters)

def split_clustered_scene_to_time_continuous_segments(clustered_scene, max_gap=0.1):
    """
    将聚类场景内的镜头按时间连续性分割成多个片段
    
    Args:
        clustered_scene: 聚类场景，包含'shots'列表
        max_gap: 最大允许的时间间隔（秒），默认0.1秒
        
    Returns:
        时间连续的片段列表
    """
    if 'shots' not in clustered_scene:
        logger.warning("聚类场景没有shots字段")
        return [{
            'start_time': clustered_scene['start_time'],
            'end_time': clustered_scene['end_time'],
            'type': clustered_scene['type'],
            'confidence': clustered_scene.get('confidence', 0.95)
        }]
    
    shots = sorted(clustered_scene['shots'], key=lambda s: s['start_time'])
    segments = []
    
    if not shots:
        return segments
    
    current_start = shots[0]['start_time']
    current_end = shots[0]['end_time']
    current_shots = [shots[0]]
    
    for i in range(1, len(shots)):
        gap = shots[i]['start_time'] - current_end
        
        if gap > max_gap:
            # 时间断裂，保存前一个片段
            segments.append({
                'start_time': current_start,
                'end_time': current_end,
                'type': clustered_scene['type'],
                'confidence': clustered_scene.get('confidence', 0.95),
                'shot_count': len(current_shots),
                'source_shots': current_shots
            })
            # 开始新片段
            current_start = shots[i]['start_time']
            current_shots = [shots[i]]
        else:
            # 时间连续，扩展当前片段
            current_shots.append(shots[i])
        
        current_end = shots[i]['end_time']
    
    # 保存最后一个片段
    segments.append({
        'start_time': current_start,
        'end_time': current_end,
        'type': clustered_scene['type'],
        'confidence': clustered_scene.get('confidence', 0.95),
        'shot_count': len(current_shots),
        'source_shots': current_shots
    })
    
    # 记录分割情况
    if len(segments) > 1:
        logger.info(f"场景 {clustered_scene.get('index', '?')} 被分割成 {len(segments)} 个时间连续片段")
        for idx, seg in enumerate(segments):
            logger.info(f"  片段{idx+1}: {seg['start_time']:.2f}s - {seg['end_time']:.2f}s ({seg['shot_count']}个镜头)")

def cluster_video_segments(
    segment_files: List[Path],
    video_id: str,
    similarity_threshold: float = 0.75,
    min_scene_duration: float = 3.0,
    max_scenes: Optional[int] = None,
    progress_callback=None
) -> List[Dict[str, Any]]:
    """
    对已切分的视频片段进行聚类，生成场景
    
    Args:
        segment_files: 视频片段文件路径列表
        video_id: 视频ID
        similarity_threshold: 相似度阈值
        min_scene_duration: 最小场景时长
        max_scenes: 最大场景数量
        progress_callback: 进度回调函数
        
    Returns:
        聚类后的场景列表
    """
    if progress_callback:
        progress_callback(5, "准备分析视频片段...")
    
    logger.info(f"开始对 {len(segment_files)} 个视频片段进行聚类分析...")
    
    try:
        # 1. 将片段文件转换为shots格式
        if progress_callback:
            progress_callback(10, "解析视频片段信息...")
        
        shots = []
        for i, segment_file in enumerate(segment_files):
            # 从文件名解析时间信息（假设文件名包含时间信息）
            segment_name = segment_file.stem
            
            # 估算时长（基于文件大小）
            file_size_mb = segment_file.stat().st_size / (1024*1024)
            estimated_duration = max(1.0, file_size_mb / 2)  # 简单估算
            
            shot_info = {
                'index': i + 1,
                'start_time': i * estimated_duration,  # 虚拟时间，用于排序
                'end_time': (i + 1) * estimated_duration,
                'duration': estimated_duration,
                'type': f'segment_{i+1}',
                'confidence': 0.9,
                'file_path': str(segment_file),
                'file_name': segment_file.name
            }
            shots.append(shot_info)
        
        if progress_callback:
            progress_callback(20, "提取视觉特征...")
        
        # 2. 创建聚类器
        clusterer = ShotClusterer(
            similarity_threshold=similarity_threshold,
            min_cluster_duration=min_scene_duration
        )
        
        # 3. 提取每个片段的视觉特征
        features = clusterer._extract_segment_features(segment_files, progress_callback)
        if features is None:
            logger.warning("无法提取视觉特征，返回原始片段")
            return clusterer._convert_segments_to_scenes(shots)
        
        if progress_callback:
            progress_callback(60, "计算相似度矩阵...")
        
        # 4. 计算相似度矩阵
        similarity_matrix = clusterer._compute_similarity_matrix(features)
        
        if progress_callback:
            progress_callback(70, "执行聚类算法...")
        
        # 5. 执行聚类
        clusters = clusterer._perform_clustering(similarity_matrix, max_scenes)
        
        if progress_callback:
            progress_callback(80, "合并聚类结果...")
        
        # 6. 合并聚类结果
        clustered_scenes = clusterer._merge_segments_by_clusters(shots, clusters)
        
        if progress_callback:
            progress_callback(90, "后处理优化...")
        
        # 7. 后处理
        final_scenes = clusterer._post_process_segment_scenes(clustered_scenes)
        
        if progress_callback:
            progress_callback(100, "聚类完成！")
        
        logger.info(f"片段聚类完成：{len(segment_files)} 个片段 → {len(final_scenes)} 个场景")
        
        return final_scenes
        
    except Exception as e:
        logger.error(f"视频片段聚类失败: {str(e)}")
        if progress_callback:
            progress_callback(100, f"聚类失败: {str(e)}")
        return [] 