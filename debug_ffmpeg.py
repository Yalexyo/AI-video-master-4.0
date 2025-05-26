#!/usr/bin/env python3
"""
调试FFmpeg场景检测解析逻辑
"""

import subprocess
import sys

def test_ffmpeg_parsing():
    """测试FFmpeg解析逻辑"""
    
    video_path = "data/temp/uploads/1.mp4"
    threshold = 0.01
    
    cmd = [
        "ffmpeg", 
        "-i", video_path,
        "-filter:v", f"select='gt(scene,{threshold})',metadata=print:file=-",
        "-f", "null", 
        "-",
        "-v", "info"
    ]
    
    print(f"执行命令: {' '.join(cmd)}")
    
    try:
        result = subprocess.run(
            cmd, 
            capture_output=True, 
            text=True, 
            check=False,
            timeout=60
        )
        
        print(f"返回码: {result.returncode}")
        print(f"stderr长度: {len(result.stderr)}")
        print(f"stdout长度: {len(result.stdout)}")
        
        lines = result.stderr.split('\n')
        print(f"总行数: {len(lines)}")
        
        # 查找包含frame和scene信息的行
        frame_lines = [line for line in lines if 'frame:' in line and 'pts_time:' in line]
        scene_lines = [line for line in lines if 'lavfi.scene_score=' in line]
        
        print(f"\n找到 {len(frame_lines)} 行frame信息")
        print(f"找到 {len(scene_lines)} 行scene分数信息")
        
        # 显示前10行frame信息
        print("\n前10行frame信息:")
        for i, line in enumerate(frame_lines[:10]):
            print(f"{i:2d}: {line.strip()}")
        
        # 显示前10行scene分数
        print("\n前10行scene分数:")
        for i, line in enumerate(scene_lines[:10]):
            print(f"{i:2d}: {line.strip()}")
        
        # 解析场景变化
        scene_times = []
        current_time = None
        
        for i, line in enumerate(lines):
            line = line.strip()
            
            if line.startswith('frame:') and 'pts_time:' in line:
                try:
                    pts_time_part = line.split('pts_time:')[1]
                    current_time = float(pts_time_part.strip())
                    print(f"解析时间: {current_time:.3f}s")
                except Exception as e:
                    print(f"时间解析失败: {line} -> {e}")
                    continue
            
            elif line.startswith('lavfi.scene_score=') and current_time is not None:
                try:
                    scene_score = float(line.split('=')[1])
                    print(f"解析分数: {scene_score:.3f} (时间: {current_time:.3f}s)")
                    
                    if scene_score > threshold:
                        scene_times.append((current_time, scene_score))
                        print(f"✓ 检测到场景变化: {current_time:.3f}s, 分数: {scene_score:.3f}")
                    
                    current_time = None
                    
                except Exception as e:
                    print(f"分数解析失败: {line} -> {e}")
                    continue
        
        print(f"\n总共检测到 {len(scene_times)} 个场景变化:")
        for time, score in scene_times[:10]:
            print(f"  {time:.3f}s: {score:.3f}")
        
    except Exception as e:
        print(f"执行失败: {e}")

if __name__ == "__main__":
    test_ffmpeg_parsing() 