# BMAD-EVO v3.1 任务目录管理系统

## 概述

BMAD-EVO v3.1 提供完整的任务目录管理系统，为每个新任务自动生成标准化的目录结构，便于管理需求、设计、代码、报告等所有相关文件。

## 目录结构

每个任务都会生成以下目录结构：

```
project_name/
├── .bmad/                      # BMAD-EVO 配置目录
│   ├── versions/                # 版本索引
│   │   └── version-index.json   # 版本信息
│   ├── decisions/               # 用户决策记录
│   ├── checkpoints/             # 执行检查点
│   ├── reports/                 # 审计报告
│   └── constraints/            # 约束配置
│       └── global.json
├── tasks/                       # 任务文档目录
│   ├── requirement.md           # 需求描述
│   ├── design.md                # 设计文档
│   ├── assignment.md            # 任务分解和模型指派
│   └── config/
│       └── task-config.json     # 任务配置
├── outputs/                     # 输出目录
│   ├── reports/                 # 分析报告
│   │   └── v1.0/
│   │       ├── report.md        # Markdown 报告
│   │       └── meta.json       # 版本元数据
│   ├── code/                    # 代码输出
│   │   └── v1.0/
│   │       ├── src/             # 源代码
│   │       ├── docs/            # 代码文档
│   │       └── meta.json
│   └── docs/                    # 文档输出
│       └── v1.0/
│           ├── content.md       # Markdown 文档
│           └── meta.json
└── logs/                        # 日志目录
    ├── execution.log            # 执行日志
    └── audit.log                # 审计日志
```

## 核心文档说明

### 1. requirement.md - 需求描述

存储任务的需求信息，包括：

- 基本信息（项目名称、任务类型、创建时间）
- 任务描述
- 详细需求（功能需求、非功能需求）
- 约束条件
- 验收标准

### 2. design.md - 设计文档

存储系统设计信息，包括：

- 架构概览
- 技术栈
- 模块设计
- 数据流
- 接口设计
- 安全设计
- 部署方案

### 3. assignment.md - 任务分解和模型指派

存储任务分解和模型分配信息，包括：

- 任务分解（角色流程、角色详情）
- 模型指派（GLM Coding Plan 模型分配表）
- 回退链配置
- 执行计划（阶段划分、时间估算、依赖关系）
- 上下文预算报告

## 版本管理

### 版本号规则

- 格式: `v{major}.{minor}`
- 示例: `v1.0`, `v1.1`, `v2.0`
- 主版本号 (major): 重大变更
- 次版本号 (minor): 迭代改进

### 版本索引 (version-index.json)

每个版本记录以下信息：

```json
{
  "version": "v1.0",
  "created_at": "2026-04-06T10:30:00",
  "status": "completed",
  "output_type": "code",
  "changes": [
    "初始版本",
    "基本功能实现"
  ],
  "output_files": [
    "auth.py",
    "utils.py"
  ],
  "audit_score": 95,
  "iterations": 2,
  "user_feedback": [
    "需要添加错误处理",
    "密码验证不完整"
  ]
}
```

## 使用方法

### 1. 自动创建任务目录

使用 `WorkflowOrchestratorV3Final` 自动创建完整的任务目录结构：

```python
from agents.workflow_orchestrator_v3_final import WorkflowOrchestratorV3Final

orchestrator = WorkflowOrchestratorV3Final(
    project_path="./my_project",
    interactive=True
)

result = orchestrator.execute_full_workflow("开发用户认证系统")
```

这将自动创建所有目录和文档，并在工作流完成后生成报告或代码。

### 2. 手动使用任务目录管理器

```python
from lib.v3.task_directory_manager import TaskDirectoryManager, OutputType, TaskStatus

manager = TaskDirectoryManager(
    project_path="./my_project",
    task_description="开发用户认证系统"
)

# 创建目录结构
manager.create_task_structure(
    output_type=OutputType.CODE,
    task_type="软件开发"
)

# 创建新版本
version = manager.create_new_version(
    output_type=OutputType.CODE,
    changes=["初始版本", "基本功能实现"],
    status=TaskStatus.IN_PROGRESS
)

# 保存代码
code_content = {
    "auth.py": "def login():\n    ...",
    "utils.py": "def hash_password():\n    ..."
}

manager.save_code(
    version,
    code_content,
    meta={
        "author": "AI开发助手",
        "files": len(code_content)
    }
)

# 更新版本状态
manager.update_version_status(
    version,
    status=TaskStatus.COMPLETED,
    audit_score=95,
    iterations=2
)

# 查看版本摘要
print(manager.get_version_summary())
```

### 3. 保存报告

```python
# 保存分析报告
report_content = "# 执行报告\n\n..."

manager.save_report(
    version="v1.0",
    report_content=report_content,
    meta={
        "total_phases": 5,
        "completed_phases": 5,
        "all_passed": True
    }
)
```

### 4. 更新任务文档

```python
# 更新需求文档
manager.update_requirement_document(
    "# 需求更新\n\n添加新功能...",
    "产品经理"
)

# 更新设计文档
manager.update_design_document(
    "# 设计更新\n\n优化架构...",
    "架构师"
)

# 更新任务分解和模型指派
manager.update_assignment_document(
    role_flow=role_flow,
    model_routing=model_routing,
    context_budget_report=budget_report
)
```

## 输出类型

| 输出类型 | 说明 | 存储位置 |
|---------|------|----------|
| `OutputType.REPORT` | 分析报告 | `outputs/reports/v{version}/report.md` |
| `OutputType.CODE` | 代码输出 | `outputs/code/v{version}/src/` |
| `OutputType.DOCUMENT` | 文档内容 | `outputs/docs/v{version}/content.md` |
| `OutputType.MIXED` | 混合输出 | 根据具体内容存储 |

## 任务状态

| 状态 | 说明 |
|------|------|
| `TaskStatus.PENDING` | 待处理 |
| `TaskStatus.PLANNING` | 规划中 |
| `TaskStatus.IN_PROGRESS` | 执行中 |
| `TaskStatus.REVIEWING` | 审查中 |
| `TaskStatus.COMPLETED` | 已完成 |
| `TaskStatus.FAILED` | 失败 |
| `TaskStatus.CANCELLED` | 已取消 |

## 示例：查看目录结构

运行以下命令查看已创建的任务目录结构：

```bash
python test_task_directory.py
```

这将创建一个测试项目并演示目录管理器的所有功能。

## 集成到工作流

任务目录管理器已集成到 `WorkflowOrchestratorV3Final` 中，在工作流执行时：

1. **步骤 1** (`_generate_project`): 创建完整的任务目录结构
2. **步骤 5.5** (`_check_context_budget`): 更新 `assignment.md`（任务分解和模型指派）
3. **最终** (`_generate_final_report`): 创建新版本并保存输出报告或代码

所有这些操作都是自动完成的，无需手动干预。

## 优势

1. **标准化**: 所有任务使用统一的目录结构和文档格式
2. **版本管理**: 清晰的版本索引，便于追踪变更
3. **完整记录**: 需求、设计、实现、报告全部集中管理
4. **自动集成**: 与工作流编排器无缝集成
5. **易于扩展**: 支持添加自定义文档和输出类型

---

*BMAD-EVO v3.1 任务目录管理系统*
