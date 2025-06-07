# 🚫 人脸特写检测功能

## 📋 功能概述

人脸特写检测功能是根据最佳实践原则新增的视觉分析规则，用于自动识别和过滤人脸特写片段，确保混剪视频只包含有场景的片段内容。

## 🎯 功能特点

### 1. 多层检测机制
- **标签内容检测**：基于AI分析生成的标签识别人脸特写关键词
- **场景缺失检测**：人脸特写通常缺乏场景信息
- **物体比例检测**：检查是否主要包含人物相关标签而缺少环境信息
- **视频帧检测**：可选的基于OpenCV的人脸区域面积检测

### 2. 智能过滤机制
- 在视觉分析阶段自动标记人脸特写片段
- 在片段映射时自动忽略不可用片段
- 在脚本匹配时跳过人脸特写片段
- 确保最终混剪只包含有意义的场景片段

## 🔧 技术实现

### 配置参数
```python
# streamlit_app/config/factory_config.py
VISUAL_ANALYSIS_CONFIG = {
    "face_close_up_detection": {
        "enabled": True,                    # 是否启用检测
        "face_area_threshold": 0.3,         # 人脸占画面30%以上认为是特写
        "frame_sampling_count": 3,          # 采样帧数
        "detection_confidence": 0.5,        # 检测阈值
        "keywords": [                       # 人脸特写关键词
            "人脸", "面部", "头像", "特写", "肖像", "脸部",
            "眼睛", "嘴唇", "鼻子", "面孔", "头部特写"
        ]
    }
}
```

### 检测逻辑

#### 1. 基于标签的检测
```python
def _detect_face_close_up(self, analysis_result, video_path):
    # 检查标签中是否包含人脸特写关键词
    face_indicators_count = 0
    for indicator in face_close_up_indicators:
        if indicator in all_text:
            face_indicators_count += 1
    
    # 检查是否缺少场景信息
    scene_missing = not scene_tags or scene_tags in ['', '无', '不确定']
    
    # 人脸指标 >= 2 且场景缺失 = 人脸特写
    return face_indicators_count >= 2 and scene_missing
```

#### 2. 物体比例检测
```python
# 如果物体标签很少且主要是人相关，而场景为空
if len(objects) <= 2 and scene_missing:
    person_objects = [obj for obj in objects if any(pr in obj for pr in person_related)]
    if len(person_objects) >= len(objects) * 0.8:  # 80%以上是人相关
        return True
```

#### 3. 视频帧检测（可选）
```python
# 使用OpenCV检测人脸区域
faces = face_cascade.detectMultiScale(gray, 1.1, 4)
for (x, y, w, h) in faces:
    face_ratio = (w * h) / (width * height)
    if face_ratio > face_area_threshold:  # 人脸占比超过阈值
        return True
```

### 过滤集成

#### 1. 视觉分析阶段标记
```python
# 在 QwenVideoAnalyzer._analyze_with_retry 中
face_close_up_detected = self._detect_face_close_up(analysis_result, video_path)
if face_close_up_detected:
    analysis_result["is_face_close_up"] = True
    analysis_result["unusable"] = True
    analysis_result["unusable_reason"] = "人脸特写片段"
    analysis_result["quality_score"] = 0.1  # 降低质量分
```

#### 2. 片段映射阶段过滤
```python
# 在 VideoSegmentMapper.scan_video_pool 中
is_face_close_up = segment.get('is_face_close_up', False)
is_unusable = segment.get('unusable', False)

if is_face_close_up or is_unusable:
    logger.info(f"🚫 跳过人脸特写/不可用片段: {file_name}")
    continue
```

#### 3. 脚本匹配阶段过滤
```python
# 在 VideoComposer 的匹配方法中
if segment.get('is_face_close_up', False) or segment.get('unusable', False):
    logger.debug(f"跳过人脸特写片段: {segment_id}")
    continue
```

## 📊 检测效果

### 会被识别为人脸特写的情况：
- ✅ 标签：`['人脸', '特写', '面部']` + 场景为空
- ✅ 标签：`['眼睛', '嘴唇']` + 场景为空  
- ✅ 物体：`['妈妈']` + 场景为空 + 人物比例高
- ✅ 视频帧中人脸占比 > 30%

### 不会被误判的情况：
- ❌ 标签：`['妈妈', '宝宝', '厨房']` + 有场景信息
- ❌ 标签：`['人脸']` + 场景：`['客厅']` + 有环境信息
- ❌ 物体丰富且包含环境元素

## 🎉 功能优势

### 1. 提升混剪质量
- 确保混剪视频包含有意义的场景内容
- 避免过多的人脸特写干扰叙事流畅性
- 提高观众观看体验

### 2. 智能化程度高
- 多维度检测，减少误判
- 配置化参数，灵活调整
- 与现有workflow无缝集成

### 3. 性能友好
- 主要基于已有标签数据
- 视频帧检测可选，不影响性能
- 过滤在早期阶段完成，节省后续计算

## 🔧 使用方法

### 1. 启用/禁用检测
```python
# 在 factory_config.py 中修改
"face_close_up_detection": {
    "enabled": False,  # 设为 False 禁用检测
}
```

### 2. 调整检测阈值
```python
"face_close_up_detection": {
    "face_area_threshold": 0.4,  # 提高到40%，更严格
}
```

### 3. 自定义关键词
```python
"keywords": [
    "人脸", "面部", "特写",  # 添加更多关键词
    "头像", "肖像", "脸部"
]
```

## 🧪 测试验证

运行测试脚本验证功能：
```bash
python test_face_close_up_detection.py
```

测试覆盖：
- ✅ 基础标签检测逻辑
- ✅ 配置参数加载
- ✅ 过滤集成功能
- ✅ 边界情况处理

## 📈 后续优化

### 可能的改进方向：
1. **机器学习模型**：训练专门的人脸特写分类模型
2. **更精确的帧分析**：结合人脸关键点检测
3. **动态阈值**：根据视频内容自动调整检测参数
4. **用户反馈**：允许用户手动标记和训练

### 性能优化：
1. **缓存检测结果**：避免重复计算
2. **并行处理**：多线程处理视频帧检测
3. **快速预筛**：基于文件名或元数据预过滤

---

## 🎯 总结

人脸特写检测功能按照Streamlit最佳实践原则实现，采用模块化设计、配置化管理、日志记录等标准做法。功能实现了：

1. **🎯 精准检测**：多维度识别人脸特写片段
2. **🚫 自动过滤**：在多个阶段自动忽略不可用片段  
3. **⚙️ 配置灵活**：支持参数调整和功能开关
4. **🔧 集成无缝**：与现有workflow完美配合

此功能确保了混剪视频的高质量输出，避免了人脸特写对叙事连贯性的干扰。 