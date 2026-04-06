"""
BMAD-EVO Task Directory Manager
任务目录管理器

为每个新任务生成完整的目录结构来存储：
- 需求描述 (requirement.md)
- 设计文档 (design.md)
- 任务分解和模型指派 (assignment.md)
- 输出报告或代码（按版本管理）
- 版本索引文件
"""

import json
import logging
import time
from dataclasses import dataclass, asdict, field
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, Optional, List
from enum import Enum

logger = logging.getLogger(__name__)


class OutputType(Enum):
    """输出类型"""

    REPORT = "report"
    CODE = "code"
    DOCUMENT = "document"
    MIXED = "mixed"


class TaskStatus(Enum):
    """任务状态"""

    PENDING = "pending"
    PLANNING = "planning"
    IN_PROGRESS = "in_progress"
    REVIEWING = "reviewing"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


@dataclass
class VersionInfo:
    """版本信息"""

    version: str
    created_at: str
    status: TaskStatus
    output_type: OutputType
    changes: List[str]
    output_files: List[str] = field(default_factory=list)
    audit_score: Optional[int] = None
    iterations: int = 1
    user_feedback: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        d = asdict(self)
        d["status"] = self.status.value
        d["output_type"] = self.output_type.value
        return d


@dataclass
class VersionIndex:
    """版本索引"""

    project_name: str
    created_at: str
    task_description: str
    current_version: str
    versions: Dict[str, VersionInfo] = field(default_factory=dict)

    def add_version(self, version_info: VersionInfo) -> None:
        """添加版本"""
        self.versions[version_info.version] = version_info
        self.current_version = version_info.version

    def get_latest_version(self) -> Optional[VersionInfo]:
        """获取最新版本"""
        if not self.current_version:
            return None
        return self.versions.get(self.current_version)

    def get_version(self, version: str) -> Optional[VersionInfo]:
        """获取指定版本"""
        return self.versions.get(version)

    def to_dict(self) -> Dict[str, Any]:
        versions_dict = {k: v.to_dict() for k, v in self.versions.items()}
        return {
            "project_name": self.project_name,
            "created_at": self.created_at,
            "task_description": self.task_description,
            "current_version": self.current_version,
            "versions": versions_dict,
        }


class TaskDirectoryManager:
    """
    任务目录管理器

    负责创建和管理任务目录结构，包括：
    - 配置文件
    - 执行脚本
    - 输出文件（报告/代码）
    - 需求/设计/分配文档
    - 版本索引
    """

    def __init__(self, project_path: str, task_description: str):
        self.project_path = Path(project_path)
        self.task_description = task_description
        self.project_name = self.project_path.name

        self.tasks_dir = self.project_path / "tasks"
        self.outputs_dir = self.project_path / "outputs"
        self.reports_dir = self.outputs_dir / "reports"
        self.code_dir = self.outputs_dir / "code"
        self.docs_dir = self.outputs_dir / "docs"
        self.logs_dir = self.project_path / "logs"

        self.version_index_path = (
            self.project_path / ".bmad" / "versions" / "version-index.json"
        )

        self.version_index = self._load_or_create_version_index()

    def create_task_structure(
        self, output_type: OutputType = OutputType.MIXED, task_type: str = "general"
    ) -> Dict[str, Any]:
        """
        创建完整的任务目录结构

        目录结构:
        project/
        ├── .bmad/
        │   └── versions/
        │       └── version-index.json
        ├── tasks/
        │   ├── requirement.md          # 需求描述
        │   ├── design.md               # 设计文档
        │   ├── assignment.md           # 任务分解和模型指派
        │   └── config/
        │       └── task-config.json    # 任务配置
        ├── outputs/
        │   ├── reports/               # 分析报告
        │   │   └── v{version}/
        │   │       ├── report.md
        │   │       └── meta.json
        │   ├── code/                  # 代码输出
        │   │   └── v{version}/
        │   │       ├── src/
        │   │       ├── docs/
        │   │       └── meta.json
        │   └── docs/                  # 文档输出
        │       └── v{version}/
        │           ├── content.md
        │           └── meta.json
        └── logs/
            ├── execution.log
            └── audit.log
        """
        directories = [
            self.project_path,
            self.project_path / ".bmad",
            self.project_path / ".bmad" / "versions",
            self.tasks_dir,
            self.tasks_dir / "config",
            self.outputs_dir,
            self.reports_dir,
            self.code_dir,
            self.docs_dir,
            self.logs_dir,
        ]

        for directory in directories:
            directory.mkdir(parents=True, exist_ok=True)
            logger.debug(f"Created directory: {directory}")

        self._create_initial_task_files(output_type, task_type)
        self._create_version_index()

        return {
            "project_path": str(self.project_path),
            "tasks_dir": str(self.tasks_dir),
            "outputs_dir": str(self.outputs_dir),
            "logs_dir": str(self.logs_dir),
            "version_index": self.version_index.to_dict(),
        }

    def _create_initial_task_files(
        self, output_type: OutputType, task_type: str
    ) -> None:
        """创建初始任务文件"""

        requirement_content = f"""# 需求描述

## 基本信息

- **项目名称**: {self.project_name}
- **任务类型**: {task_type}
- **输出类型**: {output_type.value}
- **创建时间**: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}

## 任务描述

{self.task_description}

## 详细需求

### 功能需求
[待补充 - 由需求分析师填写]

### 非功能需求
- 性能要求:
- 安全要求:
- 兼容性要求:

### 约束条件
- 技术约束:
- 资源约束:
- 时间约束:

## 验收标准

[待补充]
"""

        design_content = f"""# 设计文档

## 基本信息

- **项目名称**: {self.project_name}
- **任务类型**: {task_type}
- **设计时间**: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}
- **状态**: 待设计

## 系统架构

### 架构概览
[待补充 - 由架构师填写]

### 技术栈
[待补充]

### 模块设计
[待补充]

## 数据流

[待补充 - 包含数据流图]

## 接口设计

[待补充]

## 安全设计

[待补充]

## 部署方案

[待补充]
"""

        assignment_content = f"""# 任务分解和模型指派

## 基本信息

- **项目名称**: {self.project_name}
- **任务类型**: {task_type}
- **分配时间**: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}

## 任务分解

[待补充 - 由任务分析器自动生成]

## 角色分配

[待补充 - 由角色生成器自动生成]

## 模型指派

### GLM Coding Plan 模型分配

| 角色名称 | 主模型 | 备选模型 | 理由 |
|---------|--------|----------|------|
| [待补充] | [待补充] | [待补充] | [待补充] |

### 回退链

```
主模型 (GLM) → 备选1 (GLM) → 备选2 (GLM) → kimi-coding/k2p5 (绝对回退)
```

## 执行计划

### 阶段划分
[待补充]

### 时间估算
[待补充]

### 依赖关系
[待补充]

## 上下文预算

[待补充 - 由上下文预算管理器生成]
"""

        # 写入文件
        (self.tasks_dir / "requirement.md").write_text(
            requirement_content, encoding="utf-8"
        )
        (self.tasks_dir / "design.md").write_text(design_content, encoding="utf-8")
        (self.tasks_dir / "assignment.md").write_text(
            assignment_content, encoding="utf-8"
        )

        logger.info(f"Created task files: requirement.md, design.md, assignment.md")

    def _create_version_index(self) -> None:
        """创建版本索引文件"""
        self.version_index_path.parent.mkdir(parents=True, exist_ok=True)
        self._save_version_index()
        logger.info(f"Created version index: {self.version_index_path}")

    def _load_or_create_version_index(self) -> VersionIndex:
        """加载或创建版本索引"""
        if self.version_index_path.exists():
            try:
                with open(self.version_index_path, "r", encoding="utf-8") as f:
                    data = json.load(f)

                versions = {}
                for ver_str, ver_data in data.get("versions", {}).items():
                    versions[ver_str] = VersionInfo(
                        version=ver_data["version"],
                        created_at=ver_data["created_at"],
                        status=TaskStatus(ver_data["status"]),
                        output_type=OutputType(ver_data["output_type"]),
                        changes=ver_data["changes"],
                        output_files=ver_data.get("output_files", []),
                        audit_score=ver_data.get("audit_score"),
                        iterations=ver_data.get("iterations", 1),
                        user_feedback=ver_data.get("user_feedback", []),
                    )

                return VersionIndex(
                    project_name=data["project_name"],
                    created_at=data["created_at"],
                    task_description=data["task_description"],
                    current_version=data["current_version"],
                    versions=versions,
                )
            except Exception as e:
                logger.warning(f"Failed to load version index: {e}, creating new one")

        return VersionIndex(
            project_name=self.project_name,
            created_at=datetime.now().isoformat(),
            task_description=self.task_description[:200],
            current_version="",
        )

    def _save_version_index(self) -> None:
        """保存版本索引"""
        self.version_index_path.write_text(
            json.dumps(self.version_index.to_dict(), indent=2, ensure_ascii=False),
            encoding="utf-8",
        )

    def create_new_version(
        self,
        output_type: OutputType,
        changes: List[str],
        status: TaskStatus = TaskStatus.IN_PROGRESS,
    ) -> str:
        """
        创建新版本

        Args:
            output_type: 输出类型
            changes: 变更说明
            status: 初始状态

        Returns:
            版本号 (如 "v1.0", "v1.1", "v2.0")
        """
        version = self._generate_version_number(output_type)

        # 创建版本目录
        if output_type == OutputType.REPORT:
            version_dir = self.reports_dir / version
        elif output_type == OutputType.CODE:
            version_dir = self.code_dir / version
        elif output_type == OutputType.DOCUMENT:
            version_dir = self.docs_dir / version
        else:
            version_dir = self.outputs_dir / "mixed" / version

        # 先创建版本目录本身
        version_dir.mkdir(parents=True, exist_ok=True)

        # 再创建子目录
        if output_type == OutputType.CODE:
            (version_dir / "src").mkdir(exist_ok=True)
            (version_dir / "docs").mkdir(exist_ok=True)
        elif output_type == OutputType.MIXED:
            (version_dir / "reports").mkdir(exist_ok=True)
            (version_dir / "code").mkdir(exist_ok=True)
            (version_dir / "docs").mkdir(exist_ok=True)

        version_info = VersionInfo(
            version=version,
            created_at=datetime.now().isoformat(),
            status=status,
            output_type=output_type,
            changes=changes,
        )

        self.version_index.add_version(version_info)
        self._save_version_index()

        logger.info(f"Created version {version} with output type {output_type.value}")
        return version

    def _generate_version_number(self, output_type: OutputType) -> str:
        """生成版本号"""
        if not self.version_index.versions:
            return "v1.0"

        current = self.version_index.current_version
        if not current:
            return "v1.0"

        latest = self.version_index.get_latest_version()
        if not latest:
            return "v1.0"

        if latest.output_type != output_type:
            return "v1.0"

        major, minor = map(int, current[1:].split("."))
        minor += 1
        return f"v{major}.{minor}"

    def save_report(
        self,
        version: str,
        report_content: str,
        meta: Optional[Dict[str, Any]] = None,
    ) -> None:
        """
        保存报告到指定版本

        Args:
            version: 版本号
            report_content: 报告内容（Markdown格式）
            meta: 元数据
        """
        version_dir = self.reports_dir / version
        report_file = version_dir / "report.md"
        meta_file = version_dir / "meta.json"

        version_dir.mkdir(parents=True, exist_ok=True)

        report_file.write_text(report_content, encoding="utf-8")

        if meta:
            meta_file.write_text(
                json.dumps(meta, indent=2, ensure_ascii=False), encoding="utf-8"
            )

        version_info = self.version_index.get_version(version)
        if version_info:
            if "report.md" not in version_info.output_files:
                version_info.output_files.append("report.md")
            self._save_version_index()

        logger.info(f"Saved report to version {version}")

    def save_code(
        self,
        version: str,
        code_content: Dict[str, str],
        meta: Optional[Dict[str, Any]] = None,
    ) -> None:
        """
        保存代码到指定版本

        Args:
            version: 版本号
            code_content: 代码内容字典 {file_path: content}
            meta: 元数据
        """
        version_dir = self.code_dir / version
        src_dir = version_dir / "src"

        for file_path, content in code_content.items():
            file_full_path = src_dir / file_path
            file_full_path.parent.mkdir(parents=True, exist_ok=True)
            file_full_path.write_text(content, encoding="utf-8")

            version_info = self.version_index.get_version(version)
            if version_info and file_path not in version_info.output_files:
                version_info.output_files.append(file_path)

        if meta:
            meta_file = version_dir / "meta.json"
            meta_file.write_text(
                json.dumps(meta, indent=2, ensure_ascii=False), encoding="utf-8"
            )

        self._save_version_index()
        logger.info(f"Saved code to version {version}")

    def save_document(
        self,
        version: str,
        document_content: str,
        meta: Optional[Dict[str, Any]] = None,
    ) -> None:
        """
        保存文档到指定版本

        Args:
            version: 版本号
            document_content: 文档内容（Markdown格式）
            meta: 元数据
        """
        version_dir = self.docs_dir / version
        doc_file = version_dir / "content.md"
        meta_file = version_dir / "meta.json"

        doc_file.write_text(document_content, encoding="utf-8")

        if meta:
            meta_file.write_text(
                json.dumps(meta, indent=2, ensure_ascii=False), encoding="utf-8"
            )

        version_info = self.version_index.get_version(version)
        if version_info:
            if "content.md" not in version_info.output_files:
                version_info.output_files.append("content.md")
            self._save_version_index()

        logger.info(f"Saved document to version {version}")

    def update_version_status(
        self,
        version: str,
        status: TaskStatus,
        audit_score: Optional[int] = None,
        iterations: Optional[int] = None,
        user_feedback: Optional[List[str]] = None,
    ) -> None:
        """
        更新版本状态

        Args:
            version: 版本号
            status: 新状态
            audit_score: 审计分数
            iterations: 迭代次数
            user_feedback: 用户反馈
        """
        version_info = self.version_index.get_version(version)
        if version_info:
            version_info.status = status
            if audit_score is not None:
                version_info.audit_score = audit_score
            if iterations is not None:
                version_info.iterations = iterations
            if user_feedback is not None:
                version_info.user_feedback.extend(user_feedback)

            self._save_version_index()
            logger.info(f"Updated version {version} status to {status.value}")

    def update_assignment_document(
        self,
        role_flow: Any,
        model_routing: Any,
        context_budget_report: str,
    ) -> None:
        """
        更新任务分解和模型指派文档

        Args:
            role_flow: 角色流程
            model_routing: 模型路由
            context_budget_report: 上下文预算报告
        """
        assignment_content = f"""# 任务分解和模型指派

## 基本信息

- **项目名称**: {self.project_name}
- **更新时间**: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}

## 任务分解

### 角色流程概览
- **总角色数**: {role_flow.total_roles if role_flow else 0}
- **执行顺序**: {" → ".join(role_flow.execution_order) if role_flow else "无"}

### 角色详情
"""

        if role_flow:
            for role in role_flow.roles:
                assignment_content += f"""
#### {role.title}
- **角色ID**: {role.name}
- **描述**: {role.description}
- **职责**:
"""
                for resp in role.responsibilities:
                    assignment_content += f"  - {resp}\n"

                assignment_content += f"- **所需技能**: {', '.join(role.required_skills) if role.required_skills else '无'}\n"
                assignment_content += f"- **前置依赖**: {', '.join(role.input_from) if role.input_from else '无'}\n"
                assignment_content += f"- **输出到**: {', '.join(role.output_to) if role.output_to else '无'}\n"
                assignment_content += f"- **预计时间**: {role.estimated_time if role.estimated_time else '待估算'}\n"

        assignment_content += "\n## 模型指派\n\n### GLM Coding Plan 模型分配\n\n| 角色名称 | 主模型 | 备选模型 | 理由 |\n|---------|--------|----------|------|\n"

        if model_routing and model_routing.mappings:
            for mapping in model_routing.mappings:
                role = (
                    role_flow.roles[0].title
                    if role_flow and role_flow.roles
                    else mapping.role_id
                )
                assignment_content += f"| {mapping.role_id} | {mapping.primary_model} | {', '.join(mapping.fallback_models)} | {mapping.reasoning[:50]}... |\n"

        assignment_content += f"""
### 回退链

```
主模型 (GLM) → 备选1 (GLM) → 备选2 (GLM) → kimi-coding/k2p5 (绝对回退)
```

### 成本估算
- **预估成本等级**: {model_routing.estimated_cost_tier if model_routing else "未知"}
- **模型使用统计**: {json.dumps(model_routing.model_usage, indent=2) if model_routing else "无"}

## 执行计划

### 阶段划分
"""

        if role_flow:
            for i, role_name in enumerate(role_flow.execution_order, 1):
                role = next((r for r in role_flow.roles if r.name == role_name), None)
                title = role.title if role else role_name
                assignment_content += f"{i}. {title}\n"

        assignment_content += "\n## 上下文预算\n\n"
        assignment_content += context_budget_report

        assignment_content += "\n## 执行配置\n\n- **最大重试次数**: 3\n- **审计通过阈值**: 85分\n- **每阶段最大迭代次数**: 5\n"

        (self.tasks_dir / "assignment.md").write_text(
            assignment_content, encoding="utf-8"
        )
        logger.info("Updated assignment.md with role flow and model routing")

    def update_design_document(
        self,
        design_content: str,
        architect_name: str = "AI架构师",
    ) -> None:
        """
        更新设计文档

        Args:
            design_content: 设计内容
            architect_name: 架构师名称
        """
        (self.tasks_dir / "design.md").write_text(design_content, encoding="utf-8")
        logger.info(f"Updated design.md by {architect_name}")

    def update_requirement_document(
        self,
        requirement_content: str,
        analyst_name: str = "AI分析师",
    ) -> None:
        """
        更新需求文档

        Args:
            requirement_content: 需求内容
            analyst_name: 分析师名称
        """
        (self.tasks_dir / "requirement.md").write_text(
            requirement_content, encoding="utf-8"
        )
        logger.info(f"Updated requirement.md by {analyst_name}")

    def get_version_list(self) -> List[Dict[str, Any]]:
        """获取所有版本列表"""
        versions = []
        for ver_str, ver_info in self.version_index.versions.items():
            versions.append(
                {
                    "version": ver_str,
                    "created_at": ver_info.created_at,
                    "status": ver_info.status.value,
                    "output_type": ver_info.output_type.value,
                    "audit_score": ver_info.audit_score,
                    "iterations": ver_info.iterations,
                }
            )

        return sorted(versions, key=lambda x: x["created_at"], reverse=True)

    def get_version_summary(self) -> str:
        """获取版本摘要"""
        versions = self.get_version_list()

        lines = ["# 版本索引", ""]
        lines.append(f"**当前版本**: {self.version_index.current_version}")
        lines.append(f"**总版本数**: {len(versions)}")
        lines.append("")
        lines.append("## 版本历史")
        lines.append("")
        lines.append("| 版本 | 类型 | 状态 | 审计分数 | 迭代次数 | 创建时间 |")
        lines.append("|------|------|------|----------|----------|----------|")

        for v in versions:
            audit_str = str(v["audit_score"]) if v["audit_score"] else "-"
            lines.append(
                f"| {v['version']} | {v['output_type']} | {v['status']} | {audit_str} | {v['iterations']} | {v['created_at']} |"
            )

        return "\n".join(lines)

    def get_structure_summary(self) -> str:
        """获取目录结构摘要"""
        lines = ["# 任务目录结构", ""]
        lines.append(f"**项目路径**: {self.project_path}")
        lines.append(f"**项目名称**: {self.project_name}")
        lines.append("")

        lines.append("## 目录结构")
        lines.append("```")
        lines.append(f"{self.project_name}/")
        lines.append("├── .bmad/")
        lines.append("│   └── versions/")
        lines.append("│       └── version-index.json")
        lines.append("├── tasks/")
        lines.append("│   ├── requirement.md")
        lines.append("│   ├── design.md")
        lines.append("│   ├── assignment.md")
        lines.append("│   └── config/")
        lines.append("│       └── task-config.json")
        lines.append("├── outputs/")
        lines.append("│   ├── reports/")
        lines.append("│   │   └── v{version}/")
        lines.append("│   │       ├── report.md")
        lines.append("│   │       └── meta.json")
        lines.append("│   ├── code/")
        lines.append("│   │   └── v{version}/")
        lines.append("│   │       ├── src/")
        lines.append("│   │       ├── docs/")
        lines.append("│   │       └── meta.json")
        lines.append("│   └── docs/")
        lines.append("│       └── v{version}/")
        lines.append("│           ├── content.md")
        lines.append("│           └── meta.json")
        lines.append("└── logs/")
        lines.append("    ├── execution.log")
        lines.append("    └── audit.log")
        lines.append("```")

        if self.version_index.versions:
            lines.append("")
            lines.append("## 版本信息")
            lines.append("")
            for ver_str, ver_info in self.version_index.versions.items():
                lines.append(f"### {ver_str}")
                lines.append(f"- **状态**: {ver_info.status.value}")
                lines.append(f"- **类型**: {ver_info.output_type.value}")
                lines.append(f"- **创建时间**: {ver_info.created_at}")
                lines.append(f"- **输出文件**: {len(ver_info.output_files)} 个")
                if ver_info.audit_score:
                    lines.append(f"- **审计分数**: {ver_info.audit_score}")
                if ver_info.iterations > 1:
                    lines.append(f"- **迭代次数**: {ver_info.iterations}")
                lines.append("")

        return "\n".join(lines)


# 便捷函数
def create_task_directory(
    project_path: str,
    task_description: str,
    output_type: OutputType = OutputType.MIXED,
    task_type: str = "general",
) -> TaskDirectoryManager:
    """
    便捷函数：创建任务目录

    Args:
        project_path: 项目路径
        task_description: 任务描述
        output_type: 输出类型
        task_type: 任务类型

    Returns:
        TaskDirectoryManager 实例
    """
    manager = TaskDirectoryManager(project_path, task_description)
    manager.create_task_structure(output_type=output_type, task_type=task_type)
    return manager


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Task Directory Manager")
    parser.add_argument("--project", required=True, help="Project path")
    parser.add_argument("--task", required=True, help="Task description")
    parser.add_argument("--type", default="general", help="Task type")
    parser.add_argument(
        "--output",
        default="mixed",
        choices=["report", "code", "document", "mixed"],
        help="Output type",
    )

    args = parser.parse_args()

    output_type_map = {
        "report": OutputType.REPORT,
        "code": OutputType.CODE,
        "document": OutputType.DOCUMENT,
        "mixed": OutputType.MIXED,
    }

    manager = create_task_directory(
        args.project,
        args.task,
        output_type=output_type_map[args.output],
        task_type=args.type,
    )

    print(f"Task directory created at: {args.project}")
    print(f"Structure summary:\n{manager.get_structure_summary()}")
