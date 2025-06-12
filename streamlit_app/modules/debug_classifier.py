import os
import json
import shutil
from typing import List, Dict, Any
from pathlib import Path
import logging

logger = logging.getLogger(__name__)

class DebugClassifier:
    """调试分类器：按模块分类片段并保存到对应文件夹"""
    
    def __init__(self, output_base_dir: str = "../data/output/composed_video"):
        self.output_base_dir = Path(output_base_dir)
        self.module_folders = {
            "痛点": "痛点",
            "解决方案导入": "解决方案", 
            "卖点·成分&配方": "卖点",
            "促销机制": "促销"
        }
        
    def create_module_folders(self):
        """创建模块文件夹"""
        for module_name, folder_name in self.module_folders.items():
            folder_path = self.output_base_dir / folder_name
            folder_path.mkdir(parents=True, exist_ok=True)
            logger.info(f"✅ 创建模块文件夹: {folder_path}")
    
    def classify_and_save_segments_by_srt_timing(
        self, 
        mapped_segments: List[Dict[str, Any]], 
        srt_entries: List[Dict[str, Any]],
        target_ratios: List[int] = None
    ) -> Dict[str, Any]:
        """
        根据SRT时间比例和映射机制分类片段并保存到对应文件夹
        
        Args:
            mapped_segments: 已映射的片段列表
            srt_entries: SRT条目列表
            target_ratios: 目标比例 [痛点, 解决方案, 卖点, 促销]
            
        Returns:
            分类结果统计
        """
        if target_ratios is None:
            target_ratios = [25, 21, 49, 4]  # 默认比例
            
        # 创建文件夹
        self.create_module_folders()
        
        # 清空现有文件夹内容
        self._clean_module_folders()
        
        # 计算SRT时间段分配
        total_srt_duration = sum(entry.get('duration', 0) for entry in srt_entries)
        module_time_ranges = self._calculate_srt_time_ranges(srt_entries, target_ratios)
        
        logger.info(f"📊 SRT时间分配:")
        for module, time_range in module_time_ranges.items():
            logger.info(f"   {module}: {time_range['start']:.1f}s - {time_range['end']:.1f}s ({time_range['duration']:.1f}s)")
        
        # 按模块分类片段
        classification_result = {
            "total_segments": len(mapped_segments),
            "classified_segments": 0,
            "module_stats": {},
            "srt_time_ranges": module_time_ranges
        }
        
        for module_name, folder_name in self.module_folders.items():
            # 获取该模块的片段
            module_segments = [s for s in mapped_segments if s.get('category') == module_name]
            
            # 根据SRT时间范围进一步筛选（如果需要）
            # 这里可以添加时间范围匹配逻辑
            
            # 保存片段到文件夹
            saved_count = self._save_segments_to_folder(module_segments, folder_name)
            
            classification_result["module_stats"][module_name] = {
                "total_segments": len(module_segments),
                "saved_segments": saved_count,
                "target_time": module_time_ranges.get(module_name, {}).get('duration', 0),
                "actual_time": sum(s.get('duration', 0) for s in module_segments),
                "folder_path": str(self.output_base_dir / folder_name)
            }
            
            classification_result["classified_segments"] += saved_count
            
            logger.info(f"📁 {module_name}: {saved_count} 个片段保存到 {folder_name} 文件夹")
        
        # 保存分类报告
        self._save_classification_report(classification_result)
        
        return classification_result
    
    def _calculate_srt_time_ranges(self, srt_entries: List[Dict], target_ratios: List[int]) -> Dict[str, Dict]:
        """计算各模块在SRT中的时间范围"""
        total_duration = sum(entry.get('duration', 0) for entry in srt_entries)
        
        # 按比例分配时间
        module_names = ["痛点", "解决方案导入", "卖点·成分&配方", "促销机制"]
        time_ranges = {}
        current_time = 0
        
        for i, (module, ratio) in enumerate(zip(module_names, target_ratios)):
            duration = total_duration * (ratio / 100)
            time_ranges[module] = {
                "start": current_time,
                "end": current_time + duration,
                "duration": duration,
                "ratio": ratio
            }
            current_time += duration
            
        return time_ranges
    
    def _clean_module_folders(self):
        """清空模块文件夹内容"""
        for folder_name in self.module_folders.values():
            folder_path = self.output_base_dir / folder_name
            if folder_path.exists():
                for item in folder_path.iterdir():
                    if item.is_file():
                        item.unlink()
                    elif item.is_dir():
                        shutil.rmtree(item)
                logger.debug(f"🧹 清空文件夹: {folder_path}")
    
    def _save_segments_to_folder(self, segments: List[Dict], folder_name: str) -> int:
        """将片段保存到指定文件夹"""
        folder_path = self.output_base_dir / folder_name
        saved_count = 0
        
        for i, segment in enumerate(segments):
            try:
                # 复制视频文件
                source_path = Path(segment.get('file_path', ''))
                if source_path.exists():
                    # 生成目标文件名
                    target_filename = f"{i+1:03d}_{source_path.name}"
                    target_path = folder_path / target_filename
                    
                    # 复制文件
                    shutil.copy2(source_path, target_path)
                    saved_count += 1
                    
                    logger.debug(f"📄 复制: {source_path.name} -> {target_path}")
                else:
                    logger.warning(f"⚠️ 源文件不存在: {source_path}")
                    
                # 保存片段信息JSON
                info_filename = f"{i+1:03d}_{source_path.stem}_info.json"
                info_path = folder_path / info_filename
                
                segment_info = {
                    "file_name": segment.get('file_name'),
                    "file_path": str(source_path),
                    "duration": segment.get('duration'),
                    "category": segment.get('category'),
                    "all_tags": segment.get('all_tags', []),
                    "quality_score": segment.get('combined_quality', 0),
                    "classification_reason": segment.get('classification_reason', ''),
                    "video_id": segment.get('video_id', '')
                }
                
                with open(info_path, 'w', encoding='utf-8') as f:
                    json.dump(segment_info, f, ensure_ascii=False, indent=2)
                    
            except Exception as e:
                logger.error(f"❌ 保存片段失败: {segment.get('file_name', 'unknown')}, 错误: {e}")
                
        return saved_count
    
    def _save_classification_report(self, result: Dict[str, Any]):
        """保存分类报告"""
        report_path = self.output_base_dir / "classification_report.json"
        
        try:
            with open(report_path, 'w', encoding='utf-8') as f:
                json.dump(result, f, ensure_ascii=False, indent=2)
            
            logger.info(f"📊 分类报告已保存: {report_path}")
            
        except Exception as e:
            logger.error(f"❌ 保存分类报告失败: {e}")
    
    def get_folder_stats(self) -> Dict[str, Dict]:
        """获取各文件夹的统计信息"""
        stats = {}
        
        for module_name, folder_name in self.module_folders.items():
            folder_path = self.output_base_dir / folder_name
            
            if folder_path.exists():
                # 统计视频文件
                video_files = list(folder_path.glob("*.mp4"))
                json_files = list(folder_path.glob("*_info.json"))
                
                total_duration = 0
                for json_file in json_files:
                    try:
                        with open(json_file, 'r', encoding='utf-8') as f:
                            data = json.load(f)
                            total_duration += data.get('duration', 0)
                    except Exception:
                        pass
                
                stats[module_name] = {
                    "folder_path": str(folder_path),
                    "video_count": len(video_files),
                    "total_duration": total_duration,
                    "avg_duration": total_duration / len(video_files) if video_files else 0
                }
            else:
                stats[module_name] = {
                    "folder_path": str(folder_path),
                    "video_count": 0,
                    "total_duration": 0,
                    "avg_duration": 0
                }
        
        return stats 