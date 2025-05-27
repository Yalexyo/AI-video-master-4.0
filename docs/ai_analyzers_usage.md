# AI分析器模块使用手册

## 📋 概述

根据Streamlit最佳实践，我们将AI模型分析功能抽象成独立的模块，以便在不同页面和功能中重复使用。

## 🏗️ 模块结构

```
streamlit_app/modules/ai_analyzers/
├── __init__.py              # 模块初始化
├── google_video_analyzer.py # Google Cloud Video Intelligence API分析器
├── qwen_video_analyzer.py   # 千问2.5视觉分析器
└── deepseek_analyzer.py     # DeepSeek分析器
```

## 📦 分析器详解

### 1. Google Cloud Video Intelligence 分析器

**功能**: Google Cloud视频智能分析

```python
from streamlit_app.modules.ai_analyzers import GoogleVideoAnalyzer

# 初始化
analyzer = GoogleVideoAnalyzer(credentials_path="path/to/credentials.json")

# 检查凭据
has_creds, path = analyzer.check_credentials()

# 分析视频
result = analyzer.analyze_video(
    video_path="video.mp4",
    features=["shot_detection", "label_detection", "face_detection"],
    progress_callback=lambda p, m: print(f"{p}%: {m}")
)

# 提取分析结果
if result["success"]:
    shots = analyzer.extract_shots(result)
    labels = analyzer.extract_labels(result)
    faces = analyzer.extract_faces(result)
    continuity = analyzer.validate_shot_continuity(shots)
```

**支持的功能**:
- `shot_detection`: 镜头切分检测
- `label_detection`: 标签检测
- `text_detection`: 文本检测
- `face_detection`: 人脸检测
- `object_tracking`: 物体跟踪

### 2. 千问2.5视觉分析器

**功能**: 千问2.5多模态视频内容分析

```python
from streamlit_app.modules.ai_analyzers import QwenVideoAnalyzer

# 初始化（需要DASHSCOPE_API_KEY环境变量）
analyzer = QwenVideoAnalyzer()

# 检查可用性
if analyzer.is_available():
    # 分析单个视频片段
    result = analyzer.analyze_video_segment(
        video_path="segment.mp4",
        tag_language="中文",
        frame_rate=2.0
    )
    
    if result["success"]:
        objects = result["objects"]     # 物体标签
        scenes = result["scenes"]       # 场景标签
        people = result["people"]       # 人物标签
        emotions = result["emotions"]   # 情绪标签
        all_tags = result["all_tags"]   # 所有标签

# 批量分析
results = analyzer.batch_analyze_videos(
    video_paths=["video1.mp4", "video2.mp4"],
    tag_language="中文"
)

# 获取高频标签统计
top_tags = analyzer.get_top_tags_by_category(results, top_n=5)
```

**输出格式**:
- **物体**: 桌子|椅子|杯子
- **场景**: 室内|客厅|办公室
- **人物**: 女性|成人|微笑
- **情绪**: 开心|平静|专注

### 3. DeepSeek分析器

**功能**: DeepSeek模型文本分析和翻译

```python
from streamlit_app.modules.ai_analyzers import DeepSeekAnalyzer

# 初始化（需要DEEPSEEK_API_KEY环境变量）
analyzer = DeepSeekAnalyzer()

# 检查可用性
if analyzer.is_available():
    # 翻译英文标签
    chinese_label = analyzer.translate_text("cat", "中文")  # 返回: "猫"
    
    # 分析视频摘要
    summary = analyzer.analyze_video_summary(transcript_text)
    target_audience = summary.get("target_audience", "")
    
    # 分析语义片段
    enhanced_segments = analyzer.analyze_semantic_segments(segments)
```

## 🔧 集成到页面

### 在Streamlit页面中使用

```python
import streamlit as st
from streamlit_app.modules.ai_analyzers import GoogleVideoAnalyzer, QwenVideoAnalyzer

def main():
    st.title("视频分析")
    
    # Google Cloud分析
    google_analyzer = GoogleVideoAnalyzer()
    if google_analyzer.check_credentials()[0]:
        st.success("Google Cloud分析器可用")
        
        # 执行分析...
        
    # 千问分析
    qwen_analyzer = QwenVideoAnalyzer()
    if qwen_analyzer.is_available():
        st.success("千问2.5分析器可用")
        
        # 执行分析...
```

### 错误处理

```python
try:
    result = analyzer.analyze_video(video_path="video.mp4")
    if result["success"]:
        # 处理成功结果
        pass
    else:
        st.error(f"分析失败: {result['error']}")
except Exception as e:
    st.error(f"分析器错误: {str(e)}")
```

## 🌍 环境变量配置

分析器需要以下环境变量：

```bash
# Google Cloud Video Intelligence
export GOOGLE_APPLICATION_CREDENTIALS="/path/to/credentials.json"

# 千问2.5视觉分析
export DASHSCOPE_API_KEY="your_dashscope_api_key"

# DeepSeek
export DEEPSEEK_API_KEY="your_deepseek_api_key"
```

## 📊 性能优化建议

### 1. 批量处理
```python
# 好的做法：批量分析
results = qwen_analyzer.batch_analyze_videos(video_paths)

# 避免：逐个分析
for path in video_paths:
    result = qwen_analyzer.analyze_video_segment(path)
```

### 2. 帧率调整
```python
# 长视频使用低帧率
result = qwen_analyzer.analyze_video_segment(
    video_path, frame_rate=1.0  # 1fps
)

# 短视频使用高帧率
result = qwen_analyzer.analyze_video_segment(
    video_path, frame_rate=3.0  # 3fps
)
```

### 3. 进度回调
```python
def progress_callback(progress, message):
    progress_bar.progress(progress)
    status_text.text(message)

analyzer.analyze_video(
    video_path="large_video.mp4",
    progress_callback=progress_callback
)
```

## 🔍 调试与日志

分析器使用Python标准logging模块：

```python
import logging
logging.basicConfig(level=logging.INFO)

# 查看分析器日志
logger = logging.getLogger("streamlit_app.modules.ai_analyzers")
```

## 📚 最佳实践

1. **模块化设计**: 每个分析器专注单一职责
2. **错误处理**: 优雅处理API失败和网络问题
3. **配置检查**: 在使用前检查环境变量和凭据
4. **进度反馈**: 长时间操作提供进度显示
5. **资源管理**: 及时释放大型文件句柄
6. **缓存策略**: 避免重复分析相同内容

## 🔄 扩展新分析器

要添加新的AI分析器：

1. 在`ai_analyzers`目录创建新文件
2. 实现标准接口（`is_available()`, `analyze_xxx()`）
3. 在`__init__.py`中导出
4. 添加环境变量检查
5. 更新文档

示例：
```python
class NewAnalyzer:
    def __init__(self, api_key=None):
        self.api_key = api_key or os.environ.get("NEW_API_KEY")
    
    def is_available(self) -> bool:
        return self.api_key is not None
    
    def analyze_content(self, content_path: str) -> Dict[str, Any]:
        # 实现分析逻辑
        pass
``` 