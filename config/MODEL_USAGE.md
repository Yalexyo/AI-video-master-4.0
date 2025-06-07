# 🎯 AI模型配置与管理指南 - 统一配置时代

## 📋 配置架构概述

### 🔧 **统一配置中心** ✅ 已实现
系统现已采用**统一配置管理**，所有AI模型相关配置统一在 `config/keywords.yml` 中管理。

```
配置层次架构：
config/keywords.yml          # 🎯 统一关键词与prompt配置
├── modules                  # 业务模块关键词
├── emotions                 # 标准情绪枚举
├── brands                   # 品牌关键词  
├── visual_objects           # 视觉识别对象
├── scenes                   # 场景类别
└── audio_objects            # 音频识别对象

streamlit_app/config/        # 🏠 应用专用配置
├── config.py               # 目标人群、产品类型等
├── factory_config.py       # 工厂模块配置
└── mixing_config.py        # 混剪模块配置
```

## 🤖 模型分工与职责

### 1. Qwen-VL-Chat (视觉分析)
**专职**: 🖼️ 画面内容识别

**触发时机**:
- 视频帧采样分析
- 实时视觉内容识别
- 多模态场景理解

**Prompt配置**: 
- 📍 位置: `keywords.yml` → `qwen_visual` template  
- 🔧 管理: `streamlit_app/utils/keyword_config.py`
- 🎯 用途: 提取 object、scene、emotion、brand_elements

```python
# 🔧 统一调用方式
from streamlit_app.utils.keyword_config import sync_prompt_templates
templates = sync_prompt_templates()
qwen_prompt = templates["qwen_visual"]
```

### 2. DeepSeek-Chat (语义分析)
**专职**: 🎧 音频转录分析 + 👥 目标人群识别

**使用场景**:
- 音频转录内容分析
- 目标人群自动识别  
- 语义片段分类
- 英中翻译服务

**Prompt配置**:
- 📍 音频分析: `deepseek_audio` template
- 📍 人群识别: `target_audience` template  
- 📍 语义分析: `semantic_analysis` template

### 3. SentenceTransformer (文本嵌入)
**专职**: 📊 离线文本相似度计算

**主模型**: `all-MiniLM-L6-v2` (87MB)
**备用模型**: `paraphrase-multilingual-MiniLM-L12-v2` (471MB)

**自动切换机制** ✅ 已实现:
```
1. 尝试主模型 → 成功则返回结果
2. 主模型失败 → 自动切换备用模型
3. 备用模型失败 → 返回"其他"兜底
```

## 🎯 人群划分系统详解

### **为什么需要人群划分？**

母婴营销具有**强烈的人群特征**，不同人群关注点完全不同：

| 人群类型 | 关注重点 | 典型场景 | 关键词信号 |
|---------|----------|----------|------------|
| **孕期妈妈** | 营养安全、胎儿发育 | 孕检、营养补充 | "孕期"、"胎儿"、"叶酸" |
| **新手爸妈** | 喂养指导、育儿知识 | 新生儿护理、喂奶技巧 | "新生儿"、"第一次"、"怎么办" |
| **二胎妈妈** | 实用性、性价比 | 二胎经验、时间管理 | "二胎"、"忙碌"、"省心" |
| **混养妈妈** | 母乳+奶粉平衡 | 混合喂养、营养搭配 | "混喂"、"母乳不够"、"营养" |
| **贵妇妈妈** | 品质、高端配方 | 高端产品、进口品牌 | "有机"、"进口"、"高端" |

### **人群识别流程**:
```
完整转录文本 → DeepSeek分析 → 内容特征提取 → 人群匹配 → 业务决策
                    ↓
            "提到二胎、忙碌、省心" → 二胎妈妈
            "提到孕期、胎儿发育" → 孕期妈妈  
            "提到新手、第一次" → 新手爸妈
```

## 🔄 配置管理最佳实践

### ✅ **已实现的优化**

#### 1. 统一Prompt管理
```python
# ❌ 旧方式 - 分散在各文件中
def _build_prompt(self):
    return f"你是专家..." # 硬编码

# ✅ 新方式 - 统一配置
from streamlit_app.utils.keyword_config import sync_prompt_templates
templates = sync_prompt_templates()
prompt = templates["qwen_visual"]
```

#### 2. 配置健康检查
```python
from streamlit_app.utils.keyword_config import health_check

# 系统自检
health = health_check()
print(f"配置状态: {health['overall_status']}")
print(f"错误数量: {len(health['errors'])}")
```

#### 3. 兼容性验证
```python
from streamlit_app.utils.keyword_config import check_compatibility

# 模块兼容性检查
compatibility = check_compatibility()
print(f"Qwen兼容: {compatibility['qwen_analyzer']}")
print(f"DeepSeek兼容: {compatibility['deepseek_analyzer']}")
```

### 🎯 **使用指南**

#### 开发者日常操作
```bash
# 1. 检查配置状态
python -c "from streamlit_app.utils.keyword_config import health_check; print(health_check())"

# 2. 导出配置摘要  
python -c "from streamlit_app.utils.keyword_config import export_config_summary; print(export_config_summary())"

# 3. 重新加载配置
python -c "from streamlit_app.utils.keyword_config import reload_config; reload_config()"
```

#### 生产环境监控
```python
# 在应用启动时自动检查
from streamlit_app.utils.keyword_config import health_check, check_compatibility

def startup_check():
    health = health_check()
    compatibility = check_compatibility()
    
    if health["overall_status"] == "error":
        raise RuntimeError(f"配置错误: {health['errors']}")
    
    incompatible_modules = [k for k, v in compatibility.items() if not v]
    if incompatible_modules:
        logger.warning(f"模块兼容性问题: {incompatible_modules}")
```

## 📊 模型性能对比 & 使用建议

### SentenceTransformer 双模型策略

| 特性 | 主模型 (all-MiniLM-L6-v2) | 备用模型 (paraphrase-multilingual) |
|------|---------------------------|-----------------------------------|
| **大小** | 87MB | 471MB |
| **速度** | ⚡ 快 (0.01-0.05s) | 🐌 较慢 (0.02-0.08s) |
| **精度** | 🎯 标准 | 🎯🎯 更高 |
| **多语言** | ✅ 支持 | ✅✅ 更强 |
| **使用场景** | 日常批量处理 | 复杂文本/失败重试 |

### AI模型调用策略

```
视频分析优先级 (已优化):

1. 🔧 关键词规则分类 (最快)
   ├── 痛点信号检测
   ├── 活力促销检测  
   └── 品牌卖点检测

2. 🤖 DeepSeek AI分类 (第二优先级)
   ├── 超时设置: 10秒
   ├── 失败自动降级
   └── 成本控制

3. 📊 Embedding相似度 (第三优先级)
   ├── 主模型优先
   ├── 失败自动切换备用模型
   └── 离线计算

4. 🛡️ 兜底机制
   └── 返回"其他"分类
```

## 🚀 新功能与改进

### ✅ **已完成优化** (2025-01-02 更新)

1. **🎯 统一配置中心**
   - 删除重复的 `matching_rules_default.json`
   - 删除弃用的 `fallback_ai.json`  
   - 统一使用 `keywords.yml` 管理所有prompt

2. **🔧 配置管理增强**
   - 添加健康检查功能
   - 添加兼容性验证
   - 添加配置导出功能
   - 改进错误处理机制

3. **🤖 AI模型优化**
   - DeepSeek prompt重构，去除重复定义
   - Qwen prompt统一配置化
   - Embedding模型fallback机制完善

4. **👥 人群识别改进**
   - 统一人群划分prompt
   - 改进目标人群识别准确性
   - 业务逻辑与AI分析分离

### 🎯 **使用建议**

#### 新项目接入
1. 确保环境变量配置：`DEEPSEEK_API_KEY`、`DASHSCOPE_API_KEY`
2. 检查配置健康状态：`health_check()`
3. 验证模块兼容性：`check_compatibility()`
4. 根据需要调整 `config/keywords.yml`

#### 配置更新流程
1. 修改 `config/keywords.yml`
2. 调用 `reload_config()` 重新加载
3. 运行 `health_check()` 验证
4. 测试相关功能模块

#### 生产环境监控
- 每日检查配置健康状态
- 监控模型调用成功率
- 定期导出配置摘要备份
