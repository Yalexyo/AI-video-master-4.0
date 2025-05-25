"""
用户反馈数据处理模块
用于处理、验证和应用用户对视频片段的反馈数据
"""

import json
import os
import logging
from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime
from pathlib import Path

logger = logging.getLogger(__name__)


class UserFeedbackProcessor:
    """用户反馈数据处理器"""
    
    def __init__(self, feedback_dir: str = "data/user_feedback"):
        """
        初始化反馈数据处理器
        
        Args:
            feedback_dir: 反馈数据存储目录
        """
        self.feedback_dir = Path(feedback_dir)
        self.feedback_dir.mkdir(parents=True, exist_ok=True)
        
        self.corrections_file = self.feedback_dir / "segment_corrections.json"
        self.training_data_file = self.feedback_dir / "training_data.json"
        self.validation_log_file = self.feedback_dir / "validation_log.json"
    
    def validate_segment_correction(self, correction: Dict[str, Any]) -> Tuple[bool, List[str]]:
        """
        验证片段修正数据的有效性
        
        Args:
            correction: 修正数据
            
        Returns:
            (是否有效, 错误信息列表)
        """
        errors = []
        
        # 检查必需字段
        required_fields = ['video_id', 'timestamp', 'modifications']
        for field in required_fields:
            if field not in correction:
                errors.append(f"缺少必需字段: {field}")
        
        # 验证modifications
        if 'modifications' in correction:
            modifications = correction['modifications']
            if not isinstance(modifications, list):
                errors.append("modifications必须是列表")
            else:
                for i, mod in enumerate(modifications):
                    if not isinstance(mod, dict):
                        errors.append(f"modification[{i}]必须是字典")
                        continue
                    
                    # 检查modification的必需字段
                    mod_required = ['segment_index', 'original_semantic_type', 'new_semantic_type']
                    for field in mod_required:
                        if field not in mod:
                            errors.append(f"modification[{i}]缺少字段: {field}")
                    
                    # 验证时间字段
                    time_fields = ['new_start_time', 'new_end_time']
                    for field in time_fields:
                        if field in mod:
                            try:
                                float(mod[field])
                            except (ValueError, TypeError):
                                errors.append(f"modification[{i}].{field}必须是数字")
        
        return len(errors) == 0, errors
    
    def save_correction(self, correction: Dict[str, Any]) -> bool:
        """
        保存用户修正数据
        
        Args:
            correction: 修正数据
            
        Returns:
            是否保存成功
        """
        try:
            # 验证数据
            is_valid, errors = self.validate_segment_correction(correction)
            if not is_valid:
                logger.error(f"修正数据验证失败: {errors}")
                self._log_validation_error(correction, errors)
                return False
            
            # 读取现有数据
            existing_corrections = self._load_corrections()
            
            # 添加新修正
            existing_corrections.append(correction)
            
            # 保存数据
            with open(self.corrections_file, 'w', encoding='utf-8') as f:
                json.dump(existing_corrections, f, ensure_ascii=False, indent=2)
            
            logger.info(f"成功保存用户修正数据: video_id={correction.get('video_id')}")
            return True
            
        except Exception as e:
            logger.error(f"保存用户修正数据失败: {e}")
            return False
    
    def _load_corrections(self) -> List[Dict[str, Any]]:
        """加载现有的修正数据"""
        if not self.corrections_file.exists():
            return []
        
        try:
            with open(self.corrections_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        except (json.JSONDecodeError, FileNotFoundError):
            logger.warning("无法加载现有修正数据，返回空列表")
            return []
    
    def _log_validation_error(self, correction: Dict[str, Any], errors: List[str]):
        """记录验证错误"""
        error_log = {
            'timestamp': datetime.now().isoformat(),
            'correction': correction,
            'errors': errors
        }
        
        try:
            # 读取现有错误日志
            existing_logs = []
            if self.validation_log_file.exists():
                with open(self.validation_log_file, 'r', encoding='utf-8') as f:
                    existing_logs = json.load(f)
            
            # 添加新错误
            existing_logs.append(error_log)
            
            # 保存错误日志
            with open(self.validation_log_file, 'w', encoding='utf-8') as f:
                json.dump(existing_logs, f, ensure_ascii=False, indent=2)
                
        except Exception as e:
            logger.error(f"记录验证错误失败: {e}")
    
    def generate_training_examples(self) -> List[Dict[str, Any]]:
        """
        从用户反馈生成训练样例
        
        Returns:
            训练样例列表
        """
        corrections = self._load_corrections()
        training_examples = []
        
        for correction in corrections:
            video_id = correction.get('video_id', '')
            
            for modification in correction.get('modifications', []):
                text = modification.get('text', '')
                original_type = modification.get('original_semantic_type', '')
                correct_type = modification.get('new_semantic_type', '')
                
                if text and original_type != correct_type:
                    example = {
                        'video_id': video_id,
                        'text': text,
                        'incorrect_classification': original_type,
                        'correct_classification': correct_type,
                        'correction_timestamp': correction.get('timestamp', ''),
                        'training_weight': self._calculate_training_weight(modification)
                    }
                    training_examples.append(example)
        
        # 保存训练样例
        try:
            with open(self.training_data_file, 'w', encoding='utf-8') as f:
                json.dump(training_examples, f, ensure_ascii=False, indent=2)
            logger.info(f"生成了 {len(training_examples)} 个训练样例")
        except Exception as e:
            logger.error(f"保存训练样例失败: {e}")
        
        return training_examples
    
    def _calculate_training_weight(self, modification: Dict[str, Any]) -> float:
        """
        计算训练样例的权重
        
        Args:
            modification: 修正数据
            
        Returns:
            训练权重 (0.1-1.0)
        """
        weight = 1.0
        
        # 根据时间调整幅度调整权重
        original_start = modification.get('original_start_time', 0)
        new_start = modification.get('new_start_time', 0)
        original_end = modification.get('original_end_time', 0)
        new_end = modification.get('new_end_time', 0)
        
        time_change = abs(new_start - original_start) + abs(new_end - original_end)
        
        # 时间调整越大，权重越高（表示原始分割问题越严重）
        if time_change > 10:  # 超过10秒的调整
            weight = 1.0
        elif time_change > 5:  # 5-10秒的调整
            weight = 0.8
        elif time_change > 2:  # 2-5秒的调整
            weight = 0.6
        else:  # 小幅调整
            weight = 0.4
        
        return max(0.1, min(1.0, weight))
    
    def get_correction_statistics(self) -> Dict[str, Any]:
        """
        获取修正统计信息
        
        Returns:
            统计信息字典
        """
        corrections = self._load_corrections()
        
        stats = {
            'total_corrections': len(corrections),
            'total_modifications': 0,
            'semantic_type_changes': {},
            'time_adjustments': {
                'major': 0,  # >10秒
                'moderate': 0,  # 5-10秒
                'minor': 0,  # 2-5秒
                'minimal': 0  # <2秒
            },
            'videos_corrected': set(),
            'recent_corrections': 0
        }
        
        recent_threshold = datetime.now().timestamp() - (7 * 24 * 3600)  # 7天前
        
        for correction in corrections:
            video_id = correction.get('video_id', '')
            if video_id:
                stats['videos_corrected'].add(video_id)
            
            # 检查是否为最近的修正
            try:
                correction_time = datetime.fromisoformat(correction.get('timestamp', '')).timestamp()
                if correction_time > recent_threshold:
                    stats['recent_corrections'] += 1
            except (ValueError, TypeError):
                pass
            
            for modification in correction.get('modifications', []):
                stats['total_modifications'] += 1
                
                # 统计语义类型变化
                original_type = modification.get('original_semantic_type', '')
                new_type = modification.get('new_semantic_type', '')
                
                if original_type != new_type:
                    change_key = f"{original_type} → {new_type}"
                    stats['semantic_type_changes'][change_key] = stats['semantic_type_changes'].get(change_key, 0) + 1
                
                # 统计时间调整
                original_start = modification.get('original_start_time', 0)
                new_start = modification.get('new_start_time', 0)
                original_end = modification.get('original_end_time', 0)
                new_end = modification.get('new_end_time', 0)
                
                time_change = abs(new_start - original_start) + abs(new_end - original_end)
                
                if time_change > 10:
                    stats['time_adjustments']['major'] += 1
                elif time_change > 5:
                    stats['time_adjustments']['moderate'] += 1
                elif time_change > 2:
                    stats['time_adjustments']['minor'] += 1
                else:
                    stats['time_adjustments']['minimal'] += 1
        
        stats['videos_corrected'] = len(stats['videos_corrected'])
        
        return stats
    
    def export_feedback_data(self, output_file: str) -> bool:
        """
        导出反馈数据
        
        Args:
            output_file: 输出文件路径
            
        Returns:
            是否导出成功
        """
        try:
            corrections = self._load_corrections()
            training_examples = self.generate_training_examples()
            stats = self.get_correction_statistics()
            
            export_data = {
                'export_timestamp': datetime.now().isoformat(),
                'statistics': stats,
                'corrections': corrections,
                'training_examples': training_examples
            }
            
            with open(output_file, 'w', encoding='utf-8') as f:
                json.dump(export_data, f, ensure_ascii=False, indent=2)
            
            logger.info(f"反馈数据已导出到: {output_file}")
            return True
            
        except Exception as e:
            logger.error(f"导出反馈数据失败: {e}")
            return False


def get_user_feedback_processor() -> UserFeedbackProcessor:
    """
    获取用户反馈处理器实例
    
    Returns:
        UserFeedbackProcessor实例
    """
    return UserFeedbackProcessor() 