import os
import glob
import logging
import pandas as pd
import streamlit as st
from pathlib import Path

from streamlit_app.config.config import get_config, get_paths_config

# 设置日志
logger = logging.getLogger(__name__)

@st.cache_data(ttl=3600)
def find_videos(input_dir=None):
    """
    从指定目录查找视频文件
    
    Args:
        input_dir: 要搜索的目录，如果为None则使用默认目录
        
    Returns:
        找到的视频文件路径列表
    """
    config = get_config()
    
    # 如果input_dir为None，使用默认目录
    if input_dir is None:
        input_dir = config["target_video_dir"]
    
    # 确保目录存在
    os.makedirs(input_dir, exist_ok=True)
    
    # 支持的视频文件扩展名
    video_extensions = ['.mp4', '.avi', '.mov', '.mkv', '.flv', '.wmv']
    
    videos = []
    # 遍历目录及其子目录查找视频文件
    for root, _, files in os.walk(input_dir):
        logger.debug(f"Scanning directory: {root}")
        for file in files:
            file_path = os.path.join(root, file)
            file_ext = os.path.splitext(file)[1].lower()
            logger.debug(f"Checking file: {file_path}, extension: {file_ext}")
            if file_ext in video_extensions:
                videos.append(file_path)
            else:
                logger.debug(f"Skipping file (extension not matched): {file_path}")
    
    # 按名称排序
    videos.sort()
    
    if videos:
        logger.info(f"在 {input_dir} 中找到 {len(videos)} 个视频文件")
    else:
        logger.warning(f"在 {input_dir} 中未找到视频文件")
    
    return videos

@st.cache_data(ttl=3600)
def find_target_video(input_dir=None):
    """
    从指定目录查找第一个视频文件
    
    Args:
        input_dir: 要搜索的目录，如果为None则使用默认目录
        
    Returns:
        找到的第一个视频文件路径，如果没有找到则返回None
    """
    videos = find_videos(input_dir)
    return videos[0] if videos else None

@st.cache_data(ttl=3600)
def load_video_urls_from_csv(csv_file):
    """
    从CSV文件中加载视频URL
    
    Args:
        csv_file: CSV文件路径
        
    Returns:
        包含视频URL的DataFrame
    """
    try:
        df = pd.read_csv(csv_file)
        logger.info(f"从 {csv_file} 加载了 {len(df)} 条视频URL记录")
        return df
    except Exception as e:
        logger.error(f"加载CSV文件失败: {str(e)}")
        return pd.DataFrame()

def get_video_path(video_id, base_dir=None):
    """
    根据视频ID查找视频文件
    
    Args:
        video_id: 视频ID
        base_dir: 基础目录，默认使用配置中的参考视频目录
        
    Returns:
        视频文件路径，如果没找到则返回None
    """
    config = get_config()
    base_dir = base_dir or config["ref_video_dir"]
    
    # 检查直接匹配的文件是否存在
    exact_path = os.path.join(base_dir, f"{video_id}.mp4")
    if os.path.exists(exact_path):
        return exact_path
    
    # 检查带有ID_作为前缀的文件
    prefix_path = os.path.join(base_dir, f"{video_id}_*.mp4")
    matches = glob.glob(prefix_path)
    if matches:
        return matches[0]
    
    # 尝试在文件名中查找ID
    all_videos = glob.glob(os.path.join(base_dir, "*.mp4"))
    for video_path in all_videos:
        filename = os.path.basename(video_path)
        if f"_{video_id}_" in filename or f"_{video_id}." in filename:
            return video_path
    
    logger.warning(f"无法找到视频ID为 {video_id} 的视频文件")
    return None

@st.cache_data(ttl=3600)
def load_segments_json(segments_file):
    """
    加载视频分段JSON文件
    
    Args:
        segments_file: 分段JSON文件路径
        
    Returns:
        分段数据列表
    """
    import json
    try:
        with open(segments_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
        logger.info(f"从 {segments_file} 加载了分段数据")
        return data
    except Exception as e:
        logger.error(f"加载JSON文件失败: {str(e)}")
        return []

@st.cache_data(ttl=3600)
def find_segment_files():
    """
    查找所有分段JSON文件
    
    Returns:
        找到的所有分段JSON文件路径列表
    """
    paths = get_paths_config()
    base_dir = paths["segments_dir"]
    
    if not os.path.exists(base_dir):
        logger.warning(f"默认分段目录不存在: {base_dir}")
        return []
    
    segment_files = []
    
    # 遍历所有子目录
    for subdir in os.listdir(base_dir):
        subdir_path = os.path.join(base_dir, subdir)
        
        # 确保是目录而不是文件
        if not os.path.isdir(subdir_path):
            continue
        
        # 查找子目录中的*_segments.json文件
        for item in os.listdir(subdir_path):
            item_path = os.path.join(subdir_path, item)
            if item.endswith("_segments.json") and os.path.isfile(item_path):
                segment_files.append(item_path)
                logger.debug(f"找到分段文件: {item_path}")
    
    return segment_files 