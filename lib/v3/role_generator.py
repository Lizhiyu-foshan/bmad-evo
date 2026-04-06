"""
BMAD-EVO v3.0 - DynamicRoleGenerator
动态角色生成器

功能:
- 根据任务分析结果动态生成角色
- 不硬编码角色列表
- 简单任务1-2角色，复杂任务才多角色
- 标记可并行角色
- 定义角色间的输入输出关系
"""

import json
import logging
import subprocess
import tempfile
import time
from dataclasses import dataclass, asdict, field
from pathlib import Path
from typing import Dict, List, Optional, Any

logger = logging.getLogger(__name__)


@dataclass
class RoleDefinition:
    """角色定义"""

    name: str
    title: str
    description: str
    responsibilities: List[str]
    input_from: List[str]  # 输入来源角色
    output_to: List[str]  # 输出目标角色
    can_parallel: bool
    estimated_time: str
    required_skills: List[str]
    model_requirement: str  # 对模型的要求描述

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class RoleFlow:
    """角色流程"""

    task_description: str
    task_type: str
    complexity: int
    roles: List[RoleDefinition]
    execution_order: List[str]
    parallel_groups: List[List[str]]
    rationale: str
    model_used: str = ""
    execution_time: float = 0.0
    error: Optional[str] = None

    @property
    def total_roles(self) -> int:
        """返回角色总数"""
        return len(self.roles)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "task_description": self.task_description,
            "task_type": self.task_type,
            "complexity": self.complexity,
            "roles": [r.to_dict() for r in self.roles],
            "execution_order": self.execution_order,
            "parallel_groups": self.parallel_groups,
            "rationale": self.rationale,
            "model_used": self.model_used,
            "execution_time": self.execution_time,
            "error": self.error,
        }


class DynamicRoleGenerator:
    """
    动态角色生成器
    完全由模型驱动，根据任务动态生成最适合的角色流程
    """

    PRIMARY_MODEL = "glm-4.7"
    FALLBACK_MODEL = "glm-5.1"

    def __init__(self, timeout: int = 180):
        self.timeout = timeout
        logger.info(f"DynamicRoleGenerator initialized (primary: {self.PRIMARY_MODEL})")

    def generate(
        self, task_description: str, task_analysis: Dict[str, Any]
    ) -> RoleFlow:
        """
        生成角色流程

        Args:
            task_description: 任务描述
            task_analysis: 任务分析结果 (来自 TaskAnalyzer)

        Returns:
            RoleFlow: 角色流程
        """
        logger.info(f"Generating roles for: {task_description[:100]}...")

        # 构建提示词
        prompt = self._build_generation_prompt(task_description, task_analysis)

        # 尝试主模型
        start_time = time.time()
        try:
            result = self._call_model(self.PRIMARY_MODEL, prompt)
            model_used = self.PRIMARY_MODEL
        except Exception as e:
            logger.warning(
                f"Primary model failed: {e}, falling back to {self.FALLBACK_MODEL}"
            )
            try:
                result = self._call_model(self.FALLBACK_MODEL, prompt)
                model_used = self.FALLBACK_MODEL
            except Exception as e2:
                logger.error(f"Fallback model also failed: {e2}")
                execution_time = time.time() - start_time
                return self._create_fallback_flow(
                    task_description,
                    task_analysis,
                    execution_time,
                    f"Both models failed: {e}, {e2}",
                )

        execution_time = time.time() - start_time

        # 解析结果
        try:
            flow = self._parse_flow_result(
                task_description, task_analysis, result, model_used, execution_time
            )
            logger.info(
                f"Role generation completed: {len(flow.roles)} roles, "
                f"parallel_groups={len(flow.parallel_groups)}"
            )
            return flow
        except Exception as e:
            logger.error(f"Failed to parse role generation result: {e}")
            return self._create_fallback_flow(
                task_description, task_analysis, execution_time, str(e)
            )

    def _build_generation_prompt(
        self, task_description: str, task_analysis: Dict[str, Any]
    ) -> str:
        """构建角色生成提示词"""
        complexity = task_analysis.get("complexity_score", 5)
        recommended_roles = task_analysis.get("recommended_roles_count", 3)
        key_skills = task_analysis.get("key_skills", ["general_programming"])
        task_type = task_analysis.get("task_type", "unknown")

        return f"""你是一个专业的软件开发团队架构师。请为一个AI协作开发任务设计最优的角色流程。

## 任务描述
{task_description}

## 任务分析
- 任务类型: {task_type}
- 复杂度: {complexity}/10
- 推荐角色数: {recommended_roles}
- 关键技能: {", ".join(key_skills)}

## 角色生成原则

**重要：不要为了流程而设定流程！只设计必要的角色。**

1. **简单任务** (复杂度1-3): 1-2个角色即可
   - 示例：数据清洗 → 分析师 + 工程师
   - 示例：简单脚本 → 需求理解 + 开发实现

2. **中等任务** (复杂度4-6): 2-3个角色
   - 示例：小型API → 需求设计 + 开发 + 测试

3. **复杂任务** (复杂度7-8): 3-5个角色
   - 示例：完整系统 → 分析 + 设计 + 开发 + 测试 + 部署

4. **极复杂任务** (复杂度9-10): 5-7个角色
   - 示例：大型平台 → 完整流程 + 专家角色

## 角色设计指南

每个角色应包含：
- name: 角色标识名（英文小写+下划线）
- title: 角色显示名称（中文）
- description: 角色职责描述
- responsibilities: 具体职责列表
- input_from: 输入来源角色（空数组表示第一个角色）
- output_to: 输出目标角色（空数组表示最后一个角色）
- can_parallel: 是否可与其他角色并行
- estimated_time: 预计执行时间（如"10-15分钟"）
- required_skills: 所需技能列表
- model_requirement: 对AI模型的要求描述

## 输出格式 (JSON)

```json
{{
  "rationale": "为什么选择这些角色的简要说明",
  "roles": [
    {{
      "name": "requirement_analyst",
      "title": "需求分析师",
      "description": "深入理解需求并提炼关键功能点",
      "responsibilities": ["需求分析", "功能拆解", "边界识别"],
      "input_from": [],
      "output_to": ["solution_designer"],
      "can_parallel": false,
      "estimated_time": "10-15分钟",
      "required_skills": ["requirements_analysis", "domain_knowledge"],
      "model_requirement": "强逻辑推理能力，能准确理解需求"
    }}
  ],
  "execution_order": ["requirement_analyst", "solution_designer", "developer"],
  "parallel_groups": []  // 没有可并行角色时为空数组
}}
```

**注意**:
- 角色之间必须有清晰的输入输出关系
- 只有真正可以独立进行的任务才标记为并行
- 保持角色精简，不要过度拆分
"""

    def _call_model(self, model: str, prompt: str) -> str:
        """调用模型"""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False) as f:
            f.write(prompt)
            prompt_file = f.name

        try:
            cmd = [
                "openclaw",
                "sessions",
                "spawn",
                "--model",
                model,
                "--task-file",
                prompt_file,
                "--timeout",
                str(self.timeout),
                "--cleanup",
                "keep",
            ]

            result = subprocess.run(
                cmd, capture_output=True, text=True, timeout=self.timeout + 10
            )

            if result.returncode != 0:
                raise RuntimeError(f"Model call failed: {result.stderr}")

            return result.stdout

        finally:
            try:
                Path(prompt_file).unlink(missing_ok=True)
            except Exception:
                pass

    def _parse_flow_result(
        self,
        task_description: str,
        task_analysis: Dict[str, Any],
        raw_output: str,
        model_used: str,
        execution_time: float,
    ) -> RoleFlow:
        """解析角色生成结果"""

        json_str = self._extract_json(raw_output)

        try:
            data = json.loads(json_str)
        except json.JSONDecodeError as e:
            logger.error(f"JSON parse error: {e}")
            raise

        # 解析角色
        roles = []
        for role_data in data.get("roles", []):
            role = RoleDefinition(
                name=role_data.get("name", "unknown"),
                title=role_data.get("title", "未知角色"),
                description=role_data.get("description", ""),
                responsibilities=role_data.get("responsibilities", []),
                input_from=role_data.get("input_from", []),
                output_to=role_data.get("output_to", []),
                can_parallel=role_data.get("can_parallel", False),
                estimated_time=role_data.get("estimated_time", "10分钟"),
                required_skills=role_data.get("required_skills", []),
                model_requirement=role_data.get("model_requirement", "通用能力"),
            )
            roles.append(role)

        return RoleFlow(
            task_description=task_description,
            task_type=task_analysis.get("task_type", "unknown"),
            complexity=task_analysis.get("complexity_score", 5),
            roles=roles,
            execution_order=data.get("execution_order", [r.name for r in roles]),
            parallel_groups=data.get("parallel_groups", []),
            rationale=data.get("rationale", "动态生成"),
            model_used=model_used,
            execution_time=execution_time,
        )

    def _create_fallback_flow(
        self,
        task_description: str,
        task_analysis: Dict[str, Any],
        execution_time: float,
        error: str,
    ) -> RoleFlow:
        """创建回退流程（当模型调用失败时使用）"""
        complexity = task_analysis.get("complexity_score", 5)
        task_type = task_analysis.get("task_type", "unknown")

        # 根据复杂度创建默认角色
        if complexity <= 3:
            roles = [
                RoleDefinition(
                    name="task_understander",
                    title="任务理解者",
                    description="理解任务需求并制定执行计划",
                    responsibilities=["需求理解", "计划制定"],
                    input_from=[],
                    output_to=["task_executor"],
                    can_parallel=False,
                    estimated_time="5-10分钟",
                    required_skills=["analysis"],
                    model_requirement="逻辑推理能力",
                ),
                RoleDefinition(
                    name="task_executor",
                    title="任务执行者",
                    description="执行具体任务",
                    responsibilities=["代码实现", "结果验证"],
                    input_from=["task_understander"],
                    output_to=[],
                    can_parallel=False,
                    estimated_time="15-20分钟",
                    required_skills=["coding"],
                    model_requirement="代码能力",
                ),
            ]
        else:
            roles = [
                RoleDefinition(
                    name="requirement_analyst",
                    title="需求分析师",
                    description="分析需求",
                    responsibilities=["需求分析"],
                    input_from=[],
                    output_to=["developer"],
                    can_parallel=False,
                    estimated_time="10分钟",
                    required_skills=["analysis"],
                    model_requirement="分析能力",
                ),
                RoleDefinition(
                    name="developer",
                    title="开发工程师",
                    description="实现功能",
                    responsibilities=["代码实现"],
                    input_from=["requirement_analyst"],
                    output_to=["qa_engineer"],
                    can_parallel=False,
                    estimated_time="30分钟",
                    required_skills=["coding"],
                    model_requirement="代码能力",
                ),
                RoleDefinition(
                    name="qa_engineer",
                    title="测试工程师",
                    description="测试验证",
                    responsibilities=["测试验证"],
                    input_from=["developer"],
                    output_to=[],
                    can_parallel=False,
                    estimated_time="15分钟",
                    required_skills=["testing"],
                    model_requirement="测试能力",
                ),
            ]

        return RoleFlow(
            task_description=task_description,
            task_type=task_type,
            complexity=complexity,
            roles=roles,
            execution_order=[r.name for r in roles],
            parallel_groups=[],
            rationale=f"回退默认流程（模型调用失败: {error[:50]}...）",
            model_used="fallback",
            execution_time=execution_time,
            error=error,
        )

    def _extract_json(self, text: str) -> str:
        """从文本中提取 JSON"""
        if "```json" in text:
            start = text.find("```json") + 7
            end = text.find("```", start)
            if end > start:
                return text[start:end].strip()

        if "```" in text:
            start = text.find("```") + 3
            end = text.find("```", start)
            if end > start:
                return text[start:end].strip()

        start = text.find("{")
        end = text.rfind("}")
        if start >= 0 and end > start:
            return text[start : end + 1]

        return text


# 便捷函数
def generate_roles(
    task_description: str, task_analysis: Dict[str, Any], timeout: int = 180
) -> RoleFlow:
    """
    便捷函数：生成角色流程

    Args:
        task_description: 任务描述
        task_analysis: 任务分析结果
        timeout: 超时时间

    Returns:
        RoleFlow: 角色流程
    """
    generator = DynamicRoleGenerator(timeout=timeout)
    return generator.generate(task_description, task_analysis)


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Dynamic Role Generator")
    parser.add_argument("task", help="Task description")
    parser.add_argument(
        "--complexity", type=int, default=5, help="Complexity score (1-10)"
    )
    parser.add_argument("--timeout", type=int, default=180, help="Timeout in seconds")

    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO)

    analysis = {
        "task_type": "unknown",
        "complexity_score": args.complexity,
        "recommended_roles_count": 3,
        "key_skills": ["general_programming"],
    }

    result = generate_roles(args.task, analysis, args.timeout)
    print(json.dumps(result.to_dict(), indent=2, ensure_ascii=False))
