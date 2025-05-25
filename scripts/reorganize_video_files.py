#!/usr/bin/env python3
"""
视频文件重组脚本
将原始视频和SRT文件移动到segments目录，删除重复的切割片段
"""

import os
import shutil
import json
from pathlib import Path

def reorganize_video_files():
    """重组视频文件结构"""
    
    # 定义路径
    uploads_dir = "data/temp/uploads"
    segments_dir = "data/processed/segments"
    output_dir = "data/output"
    srt_dir = "data/output/test_videos"
    
    print("🔄 开始重组视频文件结构...")
    
    # 1. 移动原始视频文件到segments目录
    if os.path.exists(uploads_dir):
        for file in os.listdir(uploads_dir):
            if file.endswith('.mp4'):
                video_id = file.replace('.mp4', '')
                source_path = os.path.join(uploads_dir, file)
                target_dir = os.path.join(segments_dir, video_id)
                target_path = os.path.join(target_dir, f"original_{video_id}.mp4")
                
                # 确保目标目录存在
                os.makedirs(target_dir, exist_ok=True)
                
                # 移动文件
                if os.path.exists(source_path) and not os.path.exists(target_path):
                    shutil.move(source_path, target_path)
                    print(f"✅ 移动原始视频: {file} -> {target_path}")
    
    # 2. 移动SRT文件到对应的segments目录
    if os.path.exists(srt_dir):
        for file in os.listdir(srt_dir):
            if file.endswith('.srt'):
                video_id = file.replace('.srt', '')
                source_path = os.path.join(srt_dir, file)
                target_dir = os.path.join(segments_dir, video_id)
                target_path = os.path.join(target_dir, f"corrected_{video_id}.srt")
                
                # 确保目标目录存在
                os.makedirs(target_dir, exist_ok=True)
                
                # 复制文件（保留原文件）
                if os.path.exists(source_path) and not os.path.exists(target_path):
                    shutil.copy2(source_path, target_path)
                    print(f"✅ 复制SRT文件: {file} -> {target_path}")
    
    # 3. 删除segments目录中的重复切割片段（保留info.json文件）
    for video_id in os.listdir(segments_dir):
        video_dir = os.path.join(segments_dir, video_id)
        if os.path.isdir(video_dir):
            for file in os.listdir(video_dir):
                file_path = os.path.join(video_dir, file)
                # 删除切割片段文件，但保留原始视频、SRT文件和info.json
                if (file.endswith('.mp4') and 
                    'semantic_seg_' in file and 
                    not file.startswith('original_')):
                    os.remove(file_path)
                    print(f"🗑️ 删除重复片段: {file_path}")
    
    # 4. 更新segments_info.json文件，添加原始视频路径信息
    for video_id in os.listdir(segments_dir):
        video_dir = os.path.join(segments_dir, video_id)
        info_file = os.path.join(video_dir, f"{video_id}_segments_info.json")
        
        if os.path.exists(info_file):
            try:
                with open(info_file, 'r', encoding='utf-8') as f:
                    info_data = json.load(f)
                
                # 添加原始视频路径
                original_video_path = os.path.join(video_dir, f"original_{video_id}.mp4")
                srt_path = os.path.join(video_dir, f"corrected_{video_id}.srt")
                
                info_data['original_video_path'] = original_video_path
                info_data['corrected_srt_path'] = srt_path
                
                # 保存更新后的信息
                with open(info_file, 'w', encoding='utf-8') as f:
                    json.dump(info_data, f, ensure_ascii=False, indent=2)
                
                print(f"📝 更新info文件: {info_file}")
                
            except Exception as e:
                print(f"❌ 更新info文件失败 {info_file}: {e}")
    
    print("✅ 视频文件重组完成！")
    print("\n📁 新的文件结构:")
    print("├── data/processed/segments/{video_id}/")
    print("│   ├── original_{video_id}.mp4     # 原始完整视频")
    print("│   ├── corrected_{video_id}.srt    # 校正后的SRT字幕")
    print("│   └── {video_id}_segments_info.json  # 片段信息")
    print("└── data/output/{semantic_type}/")
    print("    └── {video_id}_semantic_seg_*.mp4  # 按语义类型组织的片段")

if __name__ == "__main__":
    reorganize_video_files() 