# 从 transcribe_core.py 迁移到 DashScope 分析器指南

## 🎯 迁移目标

将 `src/core/transcribe_core.py` 中的专业词汇校正机制整合到 `streamlit_app/modules/ai_analyzers/dashscope_audio_analyzer.py` 中，实现模块化管理。

## 📋 迁移内容

### 1. **专业词汇校正规则**

**原位置**: `src/core/transcribe_core.py` - `correct_professional_terms()` 函数
**新位置**: `streamlit_app/modules/ai_analyzers/dashscope_audio_analyzer.py` - `_apply_regex_corrections()` 方法

```python
# 旧用法 (transcribe_core.py)
from src.core.transcribe_core import correct_professional_terms
corrected_text = correct_professional_terms(text)

# 新用法 (DashScope分析器)
from streamlit_app.modules.ai_analyzers import DashScopeAudioAnalyzer
analyzer = DashScopeAudioAnalyzer()
corrected_text = analyzer.correct_professional_terms(text, use_regex_rules=True)
```

### 2. **JSON校正功能**

**原位置**: `src/core/transcribe_core.py` - `apply_corrections_to_json()` 函数
**新位置**: `streamlit_app/modules/ai_analyzers/dashscope_audio_analyzer.py` - `apply_corrections_to_json()` 方法

```python
# 旧用法
from src.core.transcribe_core import apply_corrections_to_json
corrected_data, was_corrected = apply_corrections_to_json(json_data)

# 新用法
analyzer = DashScopeAudioAnalyzer()
corrected_data, was_corrected = analyzer.apply_corrections_to_json(
    json_data, use_regex_rules=True
)
```

### 3. **热词ID配置**

**配置位置**: `streamlit_app/config/config.py`
**默认值**: `vocab-aivideo-4d73bdb1b5ef496d94f5104a957c012b`

```python
# 可通过环境变量或配置文件设置
HOTWORD_ID = "vocab-aivideo-4d73bdb1b5ef496d94f5104a957c012b"
```

## 🔧 新功能特性

### 1. **双重校正机制**

```python
analyzer = DashScopeAudioAnalyzer()

# 方式1：仅使用正则表达式规则 (推荐)
corrected_text = analyzer.correct_professional_terms(
    text, 
    use_regex_rules=True,
    professional_terms=None
)

# 方式2：正则 + 相似度匹配
corrected_text = analyzer.correct_professional_terms(
    text,
    use_regex_rules=True,
    professional_terms=["启赋蕴淳A2", "低聚糖HMO", "A2奶源"],
    similarity_threshold=0.8
)
```

### 2. **集成语音转录与校正**

```python
# 一步完成转录和校正
result = analyzer.transcribe_audio(
    audio_path,
    hotwords=["启赋", "蕴淳", "HMO"],
    professional_terms=None  # 使用内置正则规则
)

# 结果已经过校正
if result["success"]:
    corrected_transcript = result["transcript"]
    corrected_segments = result["segments"]
```

## 📝 校正规则详细说明

### 1. **启赋蕴淳系列**
- `启赋蕴淳` ← `起肤蕴醇`, `其赋蕴春`, `启步蕴纯` 等
- `启赋蕴淳A2` ← `启赋蕴醇A2`, `起肤蕴春a2` 等

### 2. **低聚糖HMO系列**
- `低聚糖HMO` ← `低聚塘HMO`, `低组糖H`, `低聚糖hmo` 等

### 3. **A2奶源系列**
- `A2奶源` ← `二奶源`, `黑二奶源`, `埃奶源`, `爱奶源` 等

### 4. **OPN系列**
- `OPN` ← `欧盾`, `O-P-N`, `偶顿` 等
- `蛋白OPN` ← `蛋白欧盾`, `蛋白O P N` 等

### 5. **自愈力系列**
- `自愈力` ← `自御力`, `自育力`, `自渔力`, `自予力` 等

## 🚀 迁移状态

### ✅ **已完成的迁移**

1. **专业词汇校正机制已迁移**：
   - `correct_professional_terms()` → `DashScopeAudioAnalyzer._apply_regex_corrections()`
   - `apply_corrections_to_json()` → `DashScopeAudioAnalyzer.apply_corrections_to_json()`

2. **向后兼容性保障**：
   - `transcribe_core.py` 中的函数已标记为弃用
   - 自动尝试使用新分析器，失败时回退到原有实现
   - 显示弃用警告，引导用户使用新接口

3. **回退机制完整**：
   - 当 DashScope API 不可用时，系统自动回退到原有转录方法
   - 保证系统在任何情况下都能正常工作

### 🔄 **当前状态**

- **`transcribe_core.py`**: 保留作为回退方案，专业词汇校正函数已弃用但仍可用
- **新代码**: 建议使用 `DashScopeAudioAnalyzer`
- **现有代码**: 自动兼容，会显示弃用警告

### 📋 **使用建议**

1. **新项目**：直接使用 `DashScopeAudioAnalyzer`
2. **现有项目**：逐步迁移，观察弃用警告并更新代码
3. **生产环境**：保留回退机制确保稳定性

### 🛠️ **手动迁移步骤 (推荐)**

1. **更新函数调用**:
```python
# 旧方式 (仍可用，但会显示警告)
from src.core.transcribe_core import correct_professional_terms
corrected_text = correct_professional_terms(text)

# 新方式 (推荐)
from streamlit_app.modules.ai_analyzers import DashScopeAudioAnalyzer
analyzer = DashScopeAudioAnalyzer()
corrected_text = analyzer.correct_professional_terms(text, use_regex_rules=True)
```

2. **验证功能**:
```bash
python test_dashscope_audio_analyzer.py
```

### 🗂️ **未来清理计划**

当确认新系统稳定运行后，可考虑：
1. 完全删除 `transcribe_core.py` 中的弃用函数
2. 移除回退机制
3. 清理相关引用

## ⚠️ 注意事项

1. **向后兼容性**: 新的DashScope分析器完全兼容原有的校正规则
2. **性能**: 正则表达式校正比相似度匹配性能更好
3. **准确性**: 预定义规则比自动匹配更准确
4. **热词ID**: 确保环境变量 `DASHSCOPE_API_KEY` 和 `HOTWORD_ID` 正确设置

## 🔍 验证清单

- [ ] DashScope分析器初始化成功
- [ ] 专业词汇校正规则正常工作
- [ ] JSON校正功能正常
- [ ] 语音转录集成校正功能
- [ ] 所有测试通过
- [ ] 现有代码功能未受影响 