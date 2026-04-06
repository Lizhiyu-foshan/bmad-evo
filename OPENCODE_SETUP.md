# BMAD-EVO v3.1 OpenCode 集成配置指南

## 快速开始

### 方法1: 使用环境变量（推荐）

在 OpenCode 中运行 BMAD-EVO 时，设置以下环境变量：

```bash
# 启用 OpenCode 直接模式（跳过 openclaw CLI）
export BMAD_EVO_MODE=opencode

# 设置项目路径
export BMAD_EVO_PROJECT=./my_analysis
```

### 方法2: 修改现有代码

如果你要使用现有的 BMAD-EVO 代码，需要修改以下几个文件来替换 `openclaw` CLI 调用：

#### 1. 修改 `lib/v3/task_analyzer.py`

找到 `_call_model` 方法（约第166行），替换为：

```python
def _call_model(self, model: str, prompt: str) -> str:
    """调用模型 - OpenCode 版本"""
    import os
    
    # 检查是否在 OpenCode 模式
    if os.environ.get('BMAD_EVO_MODE') == 'opencode':
        return prompt
    
    # 原有的 openclaw 调用代码保持不变
    ...
```

#### 2. 修改 `lib/v3/role_generator.py`

同样修改 `_call_model` 方法。

#### 3. 修改 `lib/v3/model_router.py`

修改 `_call_model` 方法。

#### 4. 修改 `lib/agent_executor.py`

修改 `_execute_openclaw` 方法，添加 OpenCode 分支：

```python
def _execute_openclaw(self, config: AgentConfig, prompt: str) -> AgentResult:
    """执行 Agent - OpenCode 兼容版本"""
    import os
    import time
    
    start_time = time.time()
    
    # OpenCode 模式
    if os.environ.get('BMAD_EVO_MODE') == 'opencode':
        return AgentResult(
            success=True,
            output=f"[OpenCode Mode] Task for {config.name}:\n\n{prompt[:500]}...",
            model_used=config.model,
            execution_time=time.time() - start_time
        )
    
    # 原有的 openclaw 代码
    ...
```

## 完整集成方案

### 创建自定义执行器

```python
# opencode_runner.py
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent / "lib"))
sys.path.insert(0, str(Path(__file__).parent / "lib" / "v3"))

from lib.v3 import BMADEVO3

class OpenCodeRunner:
    """OpenCode 专用运行器"""
    
    def __init__(self):
        self.system = BMADEVO3(project_path="./analysis_output")
    
    def run(self, task_description: str):
        """运行任务"""
        return self.system.execute(task_description)

# 使用
runner = OpenCodeRunner()
result = runner.run("分析美以打击伊朗的影响...")
```

## 模型映射 (v3.1)

BMAD-EVO v3.1 使用的 GLM Coding Plan 模型与 OpenCode 的对应关系：

| BMAD-EVO 模型 | 定位 | 用途 |
|--------------|------|------|
| `glm-5.1` | 旗舰 (推理级) | 复杂推理、系统架构、深度规划 |
| `glm-4.7` | 全能主力 | 通用编码、多轮对话、需求分析 |
| `glm-4.7-flash` | 轻量开源 | 低延迟、快速实验、QA测试 |
| `glm-4.7-flashx` | 云端极速 | 高并发、批量任务 |
| `glm-4.6` | 上一代主力 | 稳定编码、通用编程 |
| `glm-4.6v` | 多模态编码 | 设计图转代码、视觉调试 |
| `glm-4.5-air` | 超轻量 | 极简场景、快速补全 |
| `kimi-coding/k2p5` | 绝对回退 | 所有 GLM 模型失败时的终极回退 |

### 模型回退链

```
主模型 (GLM) → 备选1 (GLM) → 备选2 (GLM) → kimi-coding/k2p5 (绝对回退)
```

## 关键修改点总结

1. **模型体系更新**：所有角色使用 GLM Coding Plan 模型，kimi-coding/k2p5 仅作绝对回退
2. **移除 openclaw 依赖**：替换所有 `subprocess.run(["openclaw", ...])` 调用
3. **上下文预算管理**：预留 20% 余量防止幻觉
4. **多轮迭代支持**：每个阶段最多迭代 5 次，用户反馈作为新约束
5. **输出格式**：确保返回 JSON 格式的结果

## 测试命令

```bash
# 运行 OpenCode 版本
python run_opencode_analysis.py

# 或者使用现有的 v3 系统（需要设置环境变量）
export BMAD_EVO_MODE=opencode
python -c "from lib.v3 import BMADEVO3; BMADEVO3().execute('测试任务')"
```

## 注意事项

1. **模型选择**：优先使用 GLM 模型，kimi-coding/k2p5 仅在所有 GLM 模型不可用时使用
2. **上下文预算**：GLM-4.6v 和 GLM-4.5-Air 上下文窗口为 128K，其他为 200K
3. **超时设置**：OpenCode 有自己的超时机制，可以适当调整
4. **并发执行**：OpenCode 支持并行执行多个角色任务
5. **迭代模式**：v3.1 支持多轮迭代执行，最大迭代次数可配置
