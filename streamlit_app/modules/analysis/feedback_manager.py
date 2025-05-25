"""
用户反馈管理器
用于收集、分析和应用用户对视频片段分割的反馈
"""

import json
import os
import logging
from typing import Dict, List, Any, Optional
from datetime import datetime, timedelta
from collections import defaultdict, Counter

logger = logging.getLogger(__name__)


class FeedbackManager:
    """用户反馈管理器类"""
    
    def __init__(self, feedback_dir: str = "data/user_feedback"):
        """
        初始化反馈管理器
        
        Args:
            feedback_dir: 反馈数据存储目录
        """
        self.feedback_dir = feedback_dir
        self.corrections_file = os.path.join(feedback_dir, "segment_corrections.json")
        self.training_data_file = os.path.join(feedback_dir, "training_data.json")
        self.patterns_file = os.path.join(feedback_dir, "learned_patterns.json")
        
        # 确保目录存在
        os.makedirs(feedback_dir, exist_ok=True)
    
    def load_feedback_data(self) -> List[Dict[str, Any]]:
        """
        加载所有用户反馈数据
        
        Returns:
            反馈数据列表
        """
        if not os.path.exists(self.corrections_file):
            return []
        
        try:
            with open(self.corrections_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        except (json.JSONDecodeError, FileNotFoundError) as e:
            logger.error(f"加载反馈数据失败: {e}")
            return []
    
    def analyze_feedback_patterns(self) -> Dict[str, Any]:
        """
        分析用户反馈模式，提取改进建议
        
        Returns:
            分析结果字典
        """
        feedback_data = self.load_feedback_data()
        
        if not feedback_data:
            return {"message": "暂无反馈数据"}
        
        analysis = {
            "total_corrections": len(feedback_data),
            "semantic_type_corrections": defaultdict(int),
            "time_adjustments": [],
            "common_patterns": {},
            "improvement_suggestions": []
        }
        
        # 分析语义类型修正
        for feedback in feedback_data:
            for modification in feedback.get('modifications', []):
                original_type = modification.get('original_semantic_type')
                new_type = modification.get('new_semantic_type')
                
                if original_type != new_type:
                    correction_key = f"{original_type} → {new_type}"
                    analysis["semantic_type_corrections"][correction_key] += 1
                
                # 分析时间调整
                original_start = modification.get('original_start_time', 0)
                new_start = modification.get('new_start_time', 0)
                original_end = modification.get('original_end_time', 0)
                new_end = modification.get('new_end_time', 0)
                
                if abs(original_start - new_start) > 1 or abs(original_end - new_end) > 1:
                    analysis["time_adjustments"].append({
                        "start_diff": new_start - original_start,
                        "end_diff": new_end - original_end,
                        "semantic_type": new_type
                    })
        
        # 生成改进建议
        analysis["improvement_suggestions"] = self._generate_improvement_suggestions(analysis)
        
        # 保存分析结果
        self._save_patterns(analysis)
        
        return analysis
    
    def _generate_improvement_suggestions(self, analysis: Dict[str, Any]) -> List[str]:
        """
        基于分析结果生成改进建议
        
        Args:
            analysis: 分析结果
            
        Returns:
            改进建议列表
        """
        suggestions = []
        
        # 分析最常见的语义类型修正
        corrections = analysis["semantic_type_corrections"]
        if corrections:
            most_common = max(corrections.items(), key=lambda x: x[1])
            suggestions.append(f"最常见的修正: {most_common[0]} (出现 {most_common[1]} 次)")
            
            # 如果某个修正出现频率很高，建议调整模型
            if most_common[1] >= 3:
                suggestions.append(f"建议: 调整 '{most_common[0].split(' → ')[0]}' 类型的识别规则")
        
        # 分析时间调整模式
        time_adjustments = analysis["time_adjustments"]
        if time_adjustments:
            avg_start_diff = sum(adj["start_diff"] for adj in time_adjustments) / len(time_adjustments)
            avg_end_diff = sum(adj["end_diff"] for adj in time_adjustments) / len(time_adjustments)
            
            if abs(avg_start_diff) > 2:
                suggestions.append(f"建议: 片段开始时间平均需要调整 {avg_start_diff:.1f} 秒")
            
            if abs(avg_end_diff) > 2:
                suggestions.append(f"建议: 片段结束时间平均需要调整 {avg_end_diff:.1f} 秒")
        
        return suggestions
    
    def _save_patterns(self, patterns: Dict[str, Any]):
        """
        保存学习到的模式
        
        Args:
            patterns: 模式数据
        """
        try:
            with open(self.patterns_file, 'w', encoding='utf-8') as f:
                json.dump(patterns, f, ensure_ascii=False, indent=2, default=str)
        except Exception as e:
            logger.error(f"保存模式数据失败: {e}")
    
    def generate_training_prompts(self) -> List[Dict[str, str]]:
        """
        基于用户反馈生成训练提示词
        
        Returns:
            训练提示词列表
        """
        feedback_data = self.load_feedback_data()
        training_prompts = []
        
        for feedback in feedback_data:
            for modification in feedback.get('modifications', []):
                text = modification.get('text', '')
                original_type = modification.get('original_semantic_type')
                correct_type = modification.get('new_semantic_type')
                
                if text and original_type != correct_type:
                    prompt = {
                        "text": text,
                        "incorrect_classification": original_type,
                        "correct_classification": correct_type,
                        "training_prompt": f"文本: '{text}' 应该被分类为 '{correct_type}' 而不是 '{original_type}'"
                    }
                    training_prompts.append(prompt)
        
        # 保存训练数据
        try:
            with open(self.training_data_file, 'w', encoding='utf-8') as f:
                json.dump(training_prompts, f, ensure_ascii=False, indent=2)
        except Exception as e:
            logger.error(f"保存训练数据失败: {e}")
        
        return training_prompts
    
    def get_feedback_statistics(self) -> Dict[str, Any]:
        """
        获取反馈统计信息
        
        Returns:
            统计信息字典
        """
        feedback_data = self.load_feedback_data()
        
        if not feedback_data:
            return {"total_feedback": 0}
        
        stats = {
            "total_feedback": len(feedback_data),
            "total_modifications": sum(len(f.get('modifications', [])) for f in feedback_data),
            "recent_feedback": 0,
            "videos_with_feedback": len(set(f.get('video_id') for f in feedback_data)),
            "most_corrected_types": {},
            "feedback_timeline": []
        }
        
        # 计算最近7天的反馈
        recent_date = datetime.now() - timedelta(days=7)
        for feedback in feedback_data:
            try:
                feedback_date = datetime.fromisoformat(feedback.get('timestamp', ''))
                if feedback_date > recent_date:
                    stats["recent_feedback"] += 1
                
                # 添加到时间线
                stats["feedback_timeline"].append({
                    "date": feedback_date.strftime("%Y-%m-%d"),
                    "modifications": len(feedback.get('modifications', []))
                })
            except (ValueError, TypeError):
                continue
        
        # 统计最常修正的类型
        type_corrections = Counter()
        for feedback in feedback_data:
            for modification in feedback.get('modifications', []):
                original_type = modification.get('original_semantic_type')
                if original_type:
                    type_corrections[original_type] += 1
        
        stats["most_corrected_types"] = dict(type_corrections.most_common(5))
        
        return stats
    
    def apply_feedback_to_prompt(self, base_prompt: str) -> str:
        """
        将用户反馈应用到基础提示词中
        
        Args:
            base_prompt: 基础提示词
            
        Returns:
            增强后的提示词
        """
        patterns = self._load_patterns()
        
        if not patterns or not patterns.get("improvement_suggestions"):
            return base_prompt
        
        # 添加用户反馈学习到的规则
        feedback_rules = "\n\n基于用户反馈的改进规则:\n"
        
        # 添加常见修正规则
        corrections = patterns.get("semantic_type_corrections", {})
        if corrections:
            feedback_rules += "常见分类修正:\n"
            for correction, count in corrections.items():
                if count >= 2:  # 只包含出现2次以上的修正
                    feedback_rules += f"- {correction} (用户修正 {count} 次)\n"
        
        # 添加改进建议
        suggestions = patterns.get("improvement_suggestions", [])
        if suggestions:
            feedback_rules += "\n重要注意事项:\n"
            for suggestion in suggestions[:3]:  # 只包含前3个建议
                feedback_rules += f"- {suggestion}\n"
        
        return base_prompt + feedback_rules
    
    def _load_patterns(self) -> Dict[str, Any]:
        """
        加载学习到的模式
        
        Returns:
            模式数据
        """
        if not os.path.exists(self.patterns_file):
            return {}
        
        try:
            with open(self.patterns_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        except (json.JSONDecodeError, FileNotFoundError) as e:
            logger.error(f"加载模式数据失败: {e}")
            return {}
    
    def save_segment_correction(self, feedback_data: Dict[str, Any]) -> bool:
        """
        保存用户片段修正数据
        
        Args:
            feedback_data: 包含原始片段和更新片段的反馈数据
            
        Returns:
            是否保存成功
        """
        try:
            # 转换为标准的修正格式
            video_id = feedback_data.get('video_id', 'unknown')
            original_segments = feedback_data.get('original_segments', [])
            updated_segments = feedback_data.get('updated_segments', [])
            timestamp = feedback_data.get('timestamp', datetime.now().isoformat())
            
            # 构建修正数据
            correction_data = {
                'video_id': video_id,
                'timestamp': timestamp,
                'modifications': []
            }
            
            # 比较原始片段和更新片段，找出修改
            for i, (original, updated) in enumerate(zip(original_segments, updated_segments)):
                modifications = {}
                
                # 检查语义类型修改
                if original.get('semantic_type') != updated.get('semantic_type'):
                    modifications['original_semantic_type'] = original.get('semantic_type', '其他')
                    modifications['new_semantic_type'] = updated.get('semantic_type', '其他')
                
                # 检查时间修改
                if original.get('start_time') != updated.get('start_time'):
                    modifications['original_start_time'] = original.get('start_time', 0.0)
                    modifications['new_start_time'] = updated.get('start_time', 0.0)
                
                if original.get('end_time') != updated.get('end_time'):
                    modifications['original_end_time'] = original.get('end_time', 0.0)
                    modifications['new_end_time'] = updated.get('end_time', 0.0)
                
                # 检查产品类型修改
                if original.get('product_type') != updated.get('product_type'):
                    modifications['original_product_type'] = original.get('product_type', '未识别')
                    modifications['new_product_type'] = updated.get('product_type', '未识别')
                
                # 检查目标人群修改
                if original.get('target_audience') != updated.get('target_audience'):
                    modifications['original_target_audience'] = original.get('target_audience', '新手爸妈')
                    modifications['new_target_audience'] = updated.get('target_audience', '新手爸妈')
                
                # 如果有修改，添加到修正列表
                if modifications:
                    modifications['segment_index'] = i
                    modifications['text'] = original.get('text', '')
                    correction_data['modifications'].append(modifications)
            
            # 如果没有修改，不保存
            if not correction_data['modifications']:
                logger.info(f"视频 {video_id} 没有检测到修改，跳过保存")
                return True
            
            # 读取现有反馈数据
            existing_data = self.load_feedback_data()
            
            # 🆕 查找并移除同一视频的旧修正记录（覆盖逻辑）
            existing_data = [item for item in existing_data if item.get('video_id') != video_id]
            
            # 添加新的修正数据
            existing_data.append(correction_data)
            
            # 保存到文件
            with open(self.corrections_file, 'w', encoding='utf-8') as f:
                json.dump(existing_data, f, ensure_ascii=False, indent=2)
            
            logger.info(f"成功保存视频 {video_id} 的 {len(correction_data['modifications'])} 个修正（已覆盖旧记录）")
            return True
            
        except Exception as e:
            logger.error(f"保存片段修正数据失败: {e}")
            return False


def get_feedback_manager() -> FeedbackManager:
    """
    获取反馈管理器实例
    
    Returns:
        FeedbackManager实例
    """
    return FeedbackManager() 