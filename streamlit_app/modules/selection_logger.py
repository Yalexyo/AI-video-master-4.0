"""
选片决策日志模块
记录视频片段选择的详细决策过程，便于调试和分析
"""

import os
import json
import logging
from datetime import datetime
from typing import List, Dict, Any, Optional
from pathlib import Path

class SelectionLogger:
    """选片决策日志记录器"""
    
    def __init__(self, log_dir: str = "logs/selection"):
        """
        初始化选片日志记录器
        
        Args:
            log_dir: 日志目录路径
        """
        self.log_dir = Path(log_dir)
        self.log_dir.mkdir(parents=True, exist_ok=True)
        
        # 创建当前会话的日志文件
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        self.log_file = self.log_dir / f"selection_log_{timestamp}.jsonl"
        
        # 创建详细日志记录器
        self.logger = logging.getLogger(f"selection_logger_{timestamp}")
        self.logger.setLevel(logging.INFO)
        
        # 添加文件处理器
        handler = logging.FileHandler(str(self.log_file.with_suffix('.log')), encoding='utf-8')
        formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
        handler.setFormatter(formatter)
        self.logger.addHandler(handler)
        
        # 初始化计数器
        self.segment_count = 0
        self.session_id = timestamp
        
        self.logger.info(f"🎬 选片日志会话开始: {self.session_id}")
    
    def log_segment_analysis(self, 
                           segment_info: Dict[str, Any], 
                           analysis_steps: List[Dict[str, Any]],
                           final_result: str,
                           decision_reason: str) -> None:
        """
        记录单个片段的完整分析过程
        
        Args:
            segment_info: 片段基本信息
            analysis_steps: 分析步骤列表
            final_result: 最终分类结果
            decision_reason: 决策原因
        """
        self.segment_count += 1
        
        log_entry = {
            "session_id": self.session_id,
            "segment_id": self.segment_count,
            "timestamp": datetime.now().isoformat(),
            "segment_info": {
                "file_name": segment_info.get("file_name", "unknown"),
                "duration": segment_info.get("duration", 0),
                "all_tags": segment_info.get("all_tags", []),
                "quality_score": segment_info.get("combined_quality", 0),
                "is_face_close_up": segment_info.get("is_face_close_up", False)
            },
            "analysis_steps": analysis_steps,
            "final_result": final_result,
            "decision_reason": decision_reason
        }
        
        # 写入JSONL文件
        with open(self.log_file, 'a', encoding='utf-8') as f:
            f.write(json.dumps(log_entry, ensure_ascii=False) + '\n')
        
        # 记录到标准日志
        self.logger.info(f"🎯 片段分析完成: {segment_info.get('file_name', 'unknown')} -> {final_result}")
        self.logger.info(f"   决策原因: {decision_reason}")
        self.logger.info(f"   分析步骤: {len(analysis_steps)} 步")
    
    def log_exclusion_check(self, 
                          segment_name: str,
                          tags: List[str],
                          exclusion_results: Dict[str, Any]) -> Dict[str, Any]:
        """
        记录排除关键词检查过程
        
        Args:
            segment_name: 片段名称
            tags: 片段标签
            exclusion_results: 排除检查结果
            
        Returns:
            格式化的排除检查步骤
        """
        step = {
            "step_type": "exclusion_check",
            "timestamp": datetime.now().isoformat(),
            "input_tags": tags,
            "exclusion_results": exclusion_results
        }
        
        # 详细记录排除情况
        if exclusion_results.get("is_excluded", False):
            self.logger.warning(f"🚫 片段被排除: {segment_name}")
            for reason in exclusion_results.get("exclusion_reasons", []):
                self.logger.warning(f"   排除原因: {reason}")
        else:
            self.logger.info(f"✅ 片段通过排除检查: {segment_name}")
        
        return step
    
    def log_keyword_classification(self,
                                 segment_name: str,
                                 tags: List[str],
                                 keyword_matches: Dict[str, List[str]],
                                 classification_result: Optional[str]) -> Dict[str, Any]:
        """
        记录关键词分类过程
        
        Args:
            segment_name: 片段名称
            tags: 片段标签
            keyword_matches: 关键词匹配结果
            classification_result: 分类结果
            
        Returns:
            格式化的关键词分类步骤
        """
        step = {
            "step_type": "keyword_classification",
            "timestamp": datetime.now().isoformat(),
            "input_tags": tags,
            "keyword_matches": keyword_matches,
            "classification_result": classification_result
        }
        
        if classification_result:
            self.logger.info(f"🎯 关键词分类成功: {segment_name} -> {classification_result}")
            for module, matches in keyword_matches.items():
                if matches:
                    self.logger.info(f"   {module}: {matches}")
        else:
            self.logger.info(f"⚠️ 关键词分类无结果: {segment_name}")
        
        return step
    
    def log_ai_classification(self,
                            segment_name: str,
                            tags: List[str],
                            ai_result: str,
                            confidence: float,
                            api_call_info: Dict[str, Any]) -> Dict[str, Any]:
        """
        记录AI分类过程
        
        Args:
            segment_name: 片段名称
            tags: 片段标签
            ai_result: AI分类结果
            confidence: 置信度
            api_call_info: API调用信息
            
        Returns:
            格式化的AI分类步骤
        """
        step = {
            "step_type": "ai_classification",
            "timestamp": datetime.now().isoformat(),
            "input_tags": tags,
            "ai_result": ai_result,
            "confidence": confidence,
            "api_call_info": api_call_info
        }
        
        self.logger.info(f"🤖 AI分类结果: {segment_name} -> {ai_result} (置信度: {confidence:.2f})")
        if api_call_info.get("error"):
            self.logger.error(f"   API错误: {api_call_info['error']}")
        else:
            self.logger.info(f"   API调用耗时: {api_call_info.get('duration', 0):.2f}秒")
        
        return step
    
    def log_quality_evaluation(self,
                             segment_name: str,
                             quality_metrics: Dict[str, float],
                             quality_threshold: float,
                             passes_quality: bool) -> Dict[str, Any]:
        """
        记录质量评估过程
        
        Args:
            segment_name: 片段名称
            quality_metrics: 质量指标
            quality_threshold: 质量阈值
            passes_quality: 是否通过质量检查
            
        Returns:
            格式化的质量评估步骤
        """
        step = {
            "step_type": "quality_evaluation",
            "timestamp": datetime.now().isoformat(),
            "quality_metrics": quality_metrics,
            "quality_threshold": quality_threshold,
            "passes_quality": passes_quality
        }
        
        total_score = quality_metrics.get("combined_quality", 0)
        if passes_quality:
            self.logger.info(f"✅ 质量检查通过: {segment_name} (分数: {total_score:.2f} >= {quality_threshold})")
        else:
            self.logger.warning(f"❌ 质量检查失败: {segment_name} (分数: {total_score:.2f} < {quality_threshold})")
        
        for metric, value in quality_metrics.items():
            if metric != "combined_quality":
                self.logger.info(f"   {metric}: {value:.2f}")
        
        return step
    
    def log_module_selection(self,
                           module_name: str,
                           candidates: List[Dict[str, Any]],
                           selected_segments: List[Dict[str, Any]],
                           selection_criteria: Dict[str, Any]) -> None:
        """
        记录模块选片过程
        
        Args:
            module_name: 模块名称
            candidates: 候选片段列表
            selected_segments: 最终选中的片段
            selection_criteria: 选择标准
        """
        log_entry = {
            "session_id": self.session_id,
            "log_type": "module_selection",
            "timestamp": datetime.now().isoformat(),
            "module_name": module_name,
            "candidates_count": len(candidates),
            "selected_count": len(selected_segments),
            "selection_criteria": selection_criteria,
            "selected_segments": [
                {
                    "file_name": seg.get("file_name"),
                    "quality_score": seg.get("combined_quality"),
                    "duration": seg.get("duration")
                } for seg in selected_segments
            ]
        }
        
        # 写入JSONL文件
        with open(self.log_file, 'a', encoding='utf-8') as f:
            f.write(json.dumps(log_entry, ensure_ascii=False) + '\n')
        
        self.logger.info(f"🎬 {module_name} 选片完成: {len(selected_segments)}/{len(candidates)} 片段被选中")
        for seg in selected_segments:
            self.logger.info(f"   ✅ {seg.get('file_name')} (分数: {seg.get('combined_quality', 0):.2f})")
    
    def get_session_summary(self) -> Dict[str, Any]:
        """
        获取当前会话的摘要信息
        
        Returns:
            会话摘要
        """
        return {
            "session_id": self.session_id,
            "log_file": str(self.log_file),
            "segments_analyzed": self.segment_count,
            "start_time": self.session_id,
            "current_time": datetime.now().strftime("%Y%m%d_%H%M%S")
        }
    
    def close(self):
        """关闭日志记录器"""
        self.logger.info(f"🏁 选片日志会话结束: {self.session_id}, 共分析 {self.segment_count} 个片段")
        
        # 关闭处理器
        for handler in self.logger.handlers[:]:
            handler.close()
            self.logger.removeHandler(handler)

# 全局选片日志记录器实例
_global_logger: Optional[SelectionLogger] = None

def get_selection_logger() -> SelectionLogger:
    """获取全局选片日志记录器"""
    global _global_logger
    if _global_logger is None:
        _global_logger = SelectionLogger()
    return _global_logger

def start_new_session() -> SelectionLogger:
    """开始新的选片日志会话"""
    global _global_logger
    if _global_logger:
        _global_logger.close()
    _global_logger = SelectionLogger()
    return _global_logger 