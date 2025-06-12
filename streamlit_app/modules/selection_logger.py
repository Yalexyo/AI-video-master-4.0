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
from threading import Lock
import streamlit as st

# ---------------------------------------------------------------------------- #
#                              单例模式实现 (Singleton Pattern)                              #
# ---------------------------------------------------------------------------- #
# 全局变量，用于存储唯一的日志记录器实例
# _logger_instance = None  # 移除类型注解，避免向前引用问题
# 线程锁，确保在多线程环境下创建实例也是安全的
# _lock = Lock()

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
        self.summary = {
            "session_id": self.session_id,
            "log_file": str(self.log_file),
            "segments_analyzed": 0,
            "start_time": timestamp,
            "current_time": timestamp,
        }
    
    def _update_summary(self):
        """更新会话摘要信息"""
        self.summary["segments_analyzed"] = self.segment_count
        self.summary["current_time"] = datetime.now().strftime("%Y%m%d_%H%M%S")
    
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
        # 🔧 NEW: 添加类型检查，防止AttributeError
        if not isinstance(segment_info, dict):
            self.logger.error(f"片段信息类型错误: 期望dict，实际收到 {type(segment_info).__name__}: {segment_info}")
            # 创建默认的片段信息字典
            segment_info = {
                "file_name": "unknown_segment",
                "duration": 0,
                "all_tags": [],
                "combined_quality": 0,
                "is_face_close_up": False
            }
        
        self.segment_count += 1
        
        try:
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
            file_name = segment_info.get('file_name', 'unknown')
            self.logger.info(f"🎯 片段分析完成: {file_name} -> {final_result}")
            self.logger.info(f"   决策原因: {decision_reason}")
            self.logger.info(f"   分析步骤: {len(analysis_steps)} 步")
            
        except Exception as e:
            self.logger.error(f"记录片段分析时出错: {e}")
            # 仍然记录基本信息
            self.logger.info(f"🎯 片段分析完成: unknown -> {final_result} (记录失败)")
    
    def log_exclusion_check(self, 
                          segment_info: Optional[Dict[str, Any]],
                          tags: List[str],
                          exclusion_results: Dict[str, Any]) -> Dict[str, Any]:
        """
        记录排除关键词检查过程
        
        Args:
            segment_info: 片段信息字典
            tags: 片段标签
            exclusion_results: 排除检查结果
            
        Returns:
            格式化的排除检查步骤
        """
        # 🔧 增强稳健性: 即使传入None也能处理
        if not segment_info:
            segment_name = "unknown_segment"
            self.logger.warning("log_exclusion_check 收到空的 segment_info")
        else:
            segment_name = segment_info.get("file_name", "unknown_segment")

        # 🔧 NEW: 添加类型检查，防止AttributeError
        if not isinstance(exclusion_results, dict):
            self.logger.error(f"排除检查结果类型错误: 期望dict，实际收到 {type(exclusion_results).__name__}: {exclusion_results}")
            # 创建默认的排除结果字典
            exclusion_results = {
                "is_excluded": False,
                "exclusion_reasons": [],
                "matched_keywords": {}
            }

        step = {
            "step_type": "exclusion_check",
            "timestamp": datetime.now().isoformat(),
            "input_tags": tags,
            "exclusion_results": exclusion_results
        }
        
        # 详细记录排除情况
        try:
            is_excluded = exclusion_results.get("is_excluded", False)
            if is_excluded:
                self.logger.warning(f"🚫 片段被排除: {segment_name}")
                exclusion_reasons = exclusion_results.get("exclusion_reasons", [])
                for reason in exclusion_reasons:
                    # 🕒 特殊处理时长过滤的日志
                    if "时长" in reason and "超过限制" in reason:
                        self.logger.info(f"   🕒 时长过滤: {reason}")
                    else:
                        self.logger.warning(f"   排除原因: {reason}")
            else:
                self.logger.info(f"✅ 片段通过排除检查: {segment_name}")
        except Exception as e:
            self.logger.error(f"处理排除检查结果时出错: {e}")
            self.logger.info(f"✅ 片段通过排除检查: {segment_name} (默认通过)")
        
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
        # 🔧 增强稳健性
        if not segment_name:
            segment_name = "unknown_segment"
            self.logger.warning("log_keyword_classification 收到空的 segment_name")
            
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
                    self.logger.debug(f"   {module}: {matches}")
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
        # 🔧 增强稳健性
        if not segment_name:
            segment_name = "unknown_segment"
            self.logger.warning("log_ai_classification 收到空的 segment_name")
            
        step = {
            "step_type": "ai_classification",
            "timestamp": datetime.now().isoformat(),
            "input_tags": tags,
            "ai_result": ai_result,
            "confidence": confidence,
            "api_call_info": api_call_info
        }
        
        self.logger.info(f"🤖 AI分类结果: {segment_name} -> {ai_result} (置信度: {confidence:.2f})")
        
        # 🔧 NEW: 添加api_call_info类型检查
        if isinstance(api_call_info, dict):
            if api_call_info.get("error"):
                self.logger.error(f"   API错误: {api_call_info['error']}")
            else:
                self.logger.debug(f"   API调用耗时: {api_call_info.get('duration', 0):.2f}秒")
        else:
            self.logger.warning(f"   API调用信息类型错误: {type(api_call_info).__name__}")
        
        return step
    
    def log_quality_evaluation(self,
                             segment_info: Optional[Dict[str, Any]],
                             quality_metrics: Dict[str, float],
                             quality_threshold: float,
                             passes_quality: bool) -> Dict[str, Any]:
        """
        记录质量评估过程
        
        Args:
            segment_info: 片段信息字典
            quality_metrics: 质量指标
            quality_threshold: 质量阈值
            passes_quality: 是否通过质量检查
            
        Returns:
            格式化的质量评估步骤
        """
        # 🔧 增强稳健性
        if not segment_info:
            segment_name = "unknown_segment"
            self.logger.warning("log_quality_evaluation 收到空的 segment_info")
        elif not isinstance(segment_info, dict):
            segment_name = "unknown_segment"
            self.logger.error(f"log_quality_evaluation 收到错误类型的 segment_info: {type(segment_info).__name__}")
        else:
            segment_name = segment_info.get("file_name", "unknown_segment")

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
                self.logger.debug(f"   {metric}: {value:.2f}")
        
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
        
        self.logger.info(f"✅ 模块 {module_name}: {len(selected_segments)}/{len(candidates)} 个片段被选中")
        for segment in selected_segments:
            self.logger.info(f"   ✅ {segment.get('file_name', 'unknown')} (分数: {segment.get('combined_quality', 0):.2f})")
    
    def log_module_selection_start(self, module_name: str, target_duration: float, candidates_count: int):
        """记录模块选片开始"""
        try:
            message = f"🎬 开始为模块 {module_name} 选片: 目标时长{target_duration:.1f}s, 候选片段{candidates_count}个"
            self.logger.info(message)
            
            # 添加到JSONL
            entry = {
                "timestamp": datetime.now().isoformat(),
                "event_type": "module_selection_start",
                "module": module_name,
                "target_duration": target_duration,
                "candidates_count": candidates_count
            }
            self._write_jsonl_entry(entry)
        except Exception as e:
            self.logger.warning(f"记录模块选片开始失败: {e}")
    
    def log_deduplication_action(self, module_name: str, before_count: int, after_count: int, filtered_segments: List[str]):
        """记录去重操作"""
        try:
            if before_count > after_count:
                message = f"🔧 模块 {module_name} 去重过滤: {before_count} -> {after_count} 个候选片段"
                self.logger.info(message)
                
                if filtered_segments:
                    self.logger.info(f"   🚫 被过滤片段: {', '.join(filtered_segments)}")
                
                # 添加到JSONL
                entry = {
                    "timestamp": datetime.now().isoformat(),
                    "event_type": "deduplication",
                    "module": module_name,
                    "before_count": before_count,
                    "after_count": after_count,
                    "filtered_segments": filtered_segments
                }
                self._write_jsonl_entry(entry)
        except Exception as e:
            self.logger.warning(f"记录去重操作失败: {e}")
    
    def log_segment_selection_detail(self, module_name: str, segment_info: Dict[str, Any], is_selected: bool, reason: str = ""):
        """记录具体片段的选择详情"""
        try:
            if not isinstance(segment_info, dict):
                segment_info = {"file_name": str(segment_info), "segment_id": str(segment_info)}
            
            segment_name = segment_info.get('file_name', segment_info.get('filename', 'unknown'))
            segment_id = segment_info.get('segment_id', segment_info.get('file_name', 'unknown'))
            duration = segment_info.get('duration', 0)
            quality = segment_info.get('combined_quality', 0)
            
            status = "✅ 选中" if is_selected else "🚫 排除"
            message = f"   {status}: {segment_name} (ID: {segment_id}, 时长: {duration:.1f}s, 质量: {quality:.2f})"
            if reason:
                message += f" - {reason}"
            
            self.logger.info(message)
            
            # 添加到JSONL
            entry = {
                "timestamp": datetime.now().isoformat(),
                "event_type": "segment_selection_detail",
                "module": module_name,
                "segment_name": segment_name,
                "segment_id": segment_id,
                "duration": duration,
                "quality": quality,
                "is_selected": is_selected,
                "reason": reason
            }
            self._write_jsonl_entry(entry)
        except Exception as e:
            self.logger.warning(f"记录片段选择详情失败: {e}")
    
    def log_final_verification(self, total_segments: int, unique_segments: int, duplicate_info: List[Dict]):
        """记录最终验证结果"""
        try:
            if duplicate_info:
                message = f"❌ 去重验证失败: 总共选择{total_segments}个片段，但只有{unique_segments}个唯一片段"
                self.logger.error(message)
                
                for dup in duplicate_info:
                    self.logger.error(f"   重复片段: {dup.get('segment_name', 'unknown')} 在模块 {dup.get('modules', [])} 中重复出现")
            else:
                message = f"✅ 去重验证通过: 共选择{total_segments}个片段，全部唯一"
                self.logger.info(message)
            
            # 添加到JSONL
            entry = {
                "timestamp": datetime.now().isoformat(),
                "event_type": "final_verification",
                "total_segments": total_segments,
                "unique_segments": unique_segments,
                "has_duplicates": len(duplicate_info) > 0,
                "duplicate_info": duplicate_info
            }
            self._write_jsonl_entry(entry)
        except Exception as e:
            self.logger.warning(f"记录最终验证失败: {e}")
    
    def _write_jsonl_entry(self, entry: Dict[str, Any]):
        """写入JSONL条目的辅助方法"""
        try:
            with open(self.log_file, 'a', encoding='utf-8') as f:
                f.write(json.dumps(entry, ensure_ascii=False) + '\n')
        except Exception as e:
            self.logger.warning(f"写入JSONL条目失败: {e}")
    
    def get_session_summary(self) -> Dict[str, Any]:
        """获取当前会话的摘要信息"""
        self._update_summary()
        return self.summary
    
    def log_step(self, step_type: str, input_tags: List[str], result: str, **kwargs):
        """
        记录分类过程中的单个步骤
        
        Args:
            step_type: 步骤类型（如 'keyword_classification', 'ai_classification'）
            input_tags: 输入标签
            result: 步骤结果
            **kwargs: 其他相关信息
        """
        step_entry = {
            "session_id": self.session_id,
            "timestamp": datetime.now().isoformat(),
            "log_type": "classification_step",
            "step_type": step_type,
            "input_tags": input_tags,
            "result": result,
            **kwargs
        }
        
        self._write_jsonl_entry(step_entry)
        self.logger.info(f"🔄 分类步骤: {step_type} -> {result}")
    
    def log_final_result(self, final_category: str, reason: str, segment_info: Optional[Dict[str, Any]] = None):
        """
        记录最终分类结果
        
        Args:
            final_category: 最终分类类别
            reason: 分类原因
            segment_info: 片段信息（可选）
        """
        result_entry = {
            "session_id": self.session_id,
            "timestamp": datetime.now().isoformat(),
            "log_type": "final_classification",
            "final_category": final_category,
            "reason": reason,
            "segment_info": segment_info or {}
        }
        
        self._write_jsonl_entry(result_entry)
        
        segment_name = "unknown"
        if segment_info and isinstance(segment_info, dict):
            segment_name = segment_info.get("file_name", "unknown")
        
        self.logger.info(f"🎯 最终分类: {segment_name} -> {final_category} ({reason})")
    
    def close(self):
        """关闭日志会话，释放处理器"""
        self.logger.info(f"🏁 选片日志会话结束: {self.session_id}, 共分析 {self.segment_count} 个片段")
        handlers = self.logger.handlers[:]
        for handler in handlers:
            handler.close()
            self.logger.removeHandler(handler)

def get_selection_logger():
    """
    获取当前会话的日志记录器实例.
    使用st.session_state确保在整个用户会话中是唯一的.
    """
    if 'selection_logger_instance' not in st.session_state:
        # 如果实例不存在，创建一个新的并存储在session_state中
        st.session_state.selection_logger_instance = SelectionLogger()
    return st.session_state.selection_logger_instance

def start_new_session():
    """
    开始一个新的日志会话.
    如果已有实例，会先关闭，然后创建新的实例.
    """
    if 'selection_logger_instance' in st.session_state and st.session_state.selection_logger_instance:
        try:
            st.session_state.selection_logger_instance.close()
        except Exception as e:
            # st.logger is not available here, so we print
            print(f"[Warning] Failed to close existing logger: {e}")
            
    # 创建新实例并存储
    st.session_state.selection_logger_instance = SelectionLogger()
    return st.session_state.selection_logger_instance

def close_current_session():
    """关闭当前的日志会话"""
    if 'selection_logger_instance' in st.session_state and st.session_state.selection_logger_instance:
        st.session_state.selection_logger_instance.close()
        del st.session_state.selection_logger_instance 