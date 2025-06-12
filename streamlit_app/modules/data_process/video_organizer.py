"""
视频组织器模块
此模块负责将视频片段按照语义类型进行组织分类
"""

import os
import shutil
import logging
import traceback
from pathlib import Path

from config.config import get_config, get_paths_config, get_semantic_segment_types

# 设置日志
logger = logging.getLogger(__name__)

def create_semantic_type_directories():
    """在data/output目录下为每种语义类型创建子目录"""
    try:
        paths_config = get_paths_config()
        output_dir = Path(paths_config.get("output_dir"))
        
        # 确保主输出目录存在
        output_dir.mkdir(parents=True, exist_ok=True)
        
        # 使用动态获取的语义类型
        semantic_segment_types = get_semantic_segment_types()
        for segment_type in semantic_segment_types:
            segment_dir = output_dir / segment_type
            segment_dir.mkdir(exist_ok=True)
            logger.debug(f"已确保目录存在: {segment_dir}")
        
        logger.info(f"已为以下语义类型创建目录: {semantic_segment_types}")
        return True
    except Exception as e:
        logger.error(f"创建语义类型目录时出错: {str(e)}")
        return False

def organize_segments_by_type():
    """
    将视频片段按语义类型组织到data/output下对应的文件夹中
    
    此函数扫描data/processed/segments目录下按视频ID组织的语义片段，
    并将它们按语义类型复制到data/output目录下的对应子目录中。
    
    Returns:
        bool: 操作是否成功
    """
    try:
        # 获取配置和路径
        config = get_config()
        paths = get_paths_config()
        
        # 定义源目录和目标目录
        root_dir = Path(__file__).parent.parent.parent.parent
        output_dir = os.path.join(root_dir, "data", "output")
        segments_dir = paths.get("segments_dir", os.path.join(root_dir, "data", "processed", "segments"))
        
        logger.info(f"开始组织视频片段 - 源目录: {segments_dir}, 目标目录: {output_dir}")
        
        # 确保源目录存在
        if not os.path.exists(segments_dir):
            logger.error(f"源目录不存在: {segments_dir}")
            return False
            
        # 检查源目录下是否有视频ID目录
        segment_dirs = [d for d in os.listdir(segments_dir) if os.path.isdir(os.path.join(segments_dir, d))]
        if not segment_dirs:
            logger.warning(f"未在源目录中找到任何视频ID目录: {segments_dir}")
            return False
        
        # 确保output目录存在
        if not os.path.exists(output_dir):
            os.makedirs(output_dir)
            logger.info(f"创建输出根目录: {output_dir}")
        
        # 为每种语义类型创建目录
        type_dirs = []
        for segment_type in get_semantic_segment_types():
            type_dir = os.path.join(output_dir, segment_type)
            type_dirs.append(type_dir)
            if not os.path.exists(type_dir):
                os.makedirs(type_dir)
                logger.info(f"创建语义类型目录: {type_dir}")
        
        logger.info(f"已为以下语义类型创建目录: {get_semantic_segment_types()}")
        
        # 遍历所有视频ID目录
        video_count = 0
        segment_count = 0
        
        for video_id_dir in segment_dirs:
            video_dir_path = os.path.join(segments_dir, video_id_dir)
            
            # 确保是目录
            if not os.path.isdir(video_dir_path):
                continue
            
            video_count += 1
            logger.info(f"处理视频目录: {video_dir_path}")
            
            # 检查此视频ID下的所有片段
            video_segments = [f for f in os.listdir(video_dir_path) if f.endswith(('.mp4', '.avi', '.mov', '.mkv'))]
            if not video_segments:
                logger.warning(f"未在视频目录中找到任何视频片段: {video_dir_path}")
                continue
                
            logger.info(f"找到 {len(video_segments)} 个视频片段文件")
            
            # 遍历此视频ID下的所有片段
            for segment_file in video_segments:
                # 分析文件名，提取语义类型
                # 文件名格式: <video_id>_semantic_seg_<segment_index>_<segment_type>.mp4
                try:
                    parts = segment_file.split('_')
                    if len(parts) >= 5 and 'semantic' in segment_file:
                        # 从文件名提取语义类型
                        segment_type = parts[-1].split('.')[0]  # 移除文件扩展名
                        
                        # 处理某些情况下语义类型可能包含多个部分
                        if len(parts) > 5:
                            segment_type = '_'.join(parts[4:]).split('.')[0]
                        
                        logger.info(f"从文件名 {segment_file} 提取到语义类型: {segment_type}")
                        
                        # 检查语义类型是否有效
                        semantic_segment_types = get_semantic_segment_types()
                        if segment_type in semantic_segment_types:
                            source_path = os.path.join(video_dir_path, segment_file)
                            # 在目标目录中使用原始文件名，保留视频ID信息
                            target_path = os.path.join(output_dir, segment_type, segment_file)
                            
                            # 复制文件
                            shutil.copy2(source_path, target_path)
                            logger.info(f"已复制: {source_path} -> {target_path}")
                            segment_count += 1
                        else:
                            logger.warning(f"提取的语义类型 '{segment_type}' 不在预定义列表中: {semantic_segment_types}")
                            continue
                    else:
                        logger.warning(f"文件名 {segment_file} 不符合预期格式，跳过")
                except Exception as e:
                    logger.error(f"处理文件 {segment_file} 时出错: {str(e)}")
        
        if video_count == 0:
            logger.warning("未处理任何视频目录")
            return False
            
        if segment_count == 0:
            logger.warning("未复制任何视频片段")
            return False
            
        logger.info(f"按语义类型组织完成! 共处理 {video_count} 个视频目录, 复制了 {segment_count} 个片段")
        return True
    except Exception as e:
        logger.error(f"organize_segments_by_type 函数执行失败: {str(e)}")
        logger.error(traceback.format_exc())
        return False 