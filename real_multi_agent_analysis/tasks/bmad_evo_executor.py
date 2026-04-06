#!/usr/bin/env python3
"""
BMAD-EVO v3.0 - 标准任务执行器
遵循规则：
1. 3次重试机制
2. 失败后回退到默认模型（主会话模型）
3. 完整的进度追踪和透明度
4. 所有文件保存在任务目录下
"""

import sys
import json
import requests
import time
from pathlib import Path
from typing import Dict, List, Tuple, Optional
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum

sys.stdout.reconfigure(encoding="utf-8")

# ============================================================================
# 配置
# ============================================================================
ALI_API_KEY = "sk-sp-68f6997fc9924babb9f6b50c03a5a529"
ALI_BASE_URL = "https://coding.dashscope.aliyuncs.com/v1"

# 模型配置
MODEL_CONFIG = {
    "minimax-m2.5": {"name": "MiniMax-M2.5", "timeout": 60, "max_tokens": 4000},
    "glm-5": {"name": "GLM-5", "timeout": 90, "max_tokens": 4000},
    "kimi-k2.5": {"name": "Kimi K2.5", "timeout": 90, "max_tokens": 4000},
    "qwen3.5-plus": {"name": "Qwen3.5-Plus", "timeout": 60, "max_tokens": 4000},
}

# 默认回退模型
DEFAULT_FALLBACK_MODEL = "kimi-k2.5"

# 重试配置
MAX_RETRIES = 3
RETRY_DELAY = 3


# ============================================================================
# 数据类
# ============================================================================
class TaskStatus(Enum):
    PENDING = "⏳ 待执行"
    IN_PROGRESS = "🔄 执行中"
    RETRYING = "🔄 重试中"
    COMPLETED = "✅ 已完成"
    FALLBACK = "⚠️  已回退"
    FAILED = "❌ 失败"


@dataclass
class AnalystTask:
    phase: int
    name: str
    model: str
    role: str
    status: TaskStatus = TaskStatus.PENDING
    output: str = ""
    error: str = ""
    api_calls: int = 0
    retry_count: int = 0
    used_fallback: bool = False
    duration: float = 0.0
    fallback_reason: str = ""


# ============================================================================
# 核心类
# ============================================================================
class BMADEVOExecutor:
    """BMAD-EVO标准执行器"""

    def __init__(self, task_name: str, output_dir: str = "./results"):
        self.task_name = task_name
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.tasks: List[AnalystTask] = []
        self.headers = {
            "Authorization": f"Bearer {ALI_API_KEY}",
            "Content-Type": "application/json",
        }
        self.log_file = (
            self.output_dir
            / f"execution_log_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
        )

    def log(self, message: str):
        """记录日志"""
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        log_line = f"[{timestamp}] {message}"
        print(log_line)
        with open(self.log_file, "a", encoding="utf-8") as f:
            f.write(log_line + "\n")

    def call_model(
        self, model: str, prompt: str, system_prompt: str, timeout: int = 60
    ) -> Tuple[bool, str, str]:
        """
        调用单个模型
        返回: (是否成功, 输出内容, 错误信息)
        """
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})

        payload = {
            "model": model,
            "messages": messages,
            "temperature": 0.7,
            "max_tokens": MODEL_CONFIG.get(model, {}).get("max_tokens", 4000),
        }

        try:
            response = requests.post(
                f"{ALI_BASE_URL}/chat/completions",
                headers=self.headers,
                json=payload,
                timeout=timeout,
            )

            if response.status_code == 200:
                data = response.json()
                text = data["choices"][0]["message"]["content"]
                return True, text, ""
            else:
                error = f"HTTP {response.status_code}: {response.text[:200]}"
                return False, "", error

        except requests.exceptions.Timeout:
            return False, "", f"Timeout ({timeout}s)"
        except Exception as e:
            return False, "", str(e)

    def call_model_with_retry_and_fallback(
        self, task: AnalystTask, prompt: str, system_prompt: str
    ) -> str:
        """
        调用模型（带3次重试+回退机制）
        遵循BMAD-EVO规则
        """
        model = task.model
        config = MODEL_CONFIG.get(model, {})
        timeout = config.get("timeout", 60)

        self.log(f"\n{'=' * 80}")
        self.log(f"🔄 专家{task.phase}: {task.name}")
        self.log(f"   目标模型: {model} ({config.get('name', model)})")
        self.log(f"   超时设置: {timeout}秒")
        self.log(f"   最大重试: {MAX_RETRIES}次")
        self.log(f"{'=' * 80}")

        # 尝试调用目标模型（最多3次）
        for attempt in range(MAX_RETRIES):
            task.retry_count = attempt + 1
            task.status = TaskStatus.RETRYING if attempt > 0 else TaskStatus.IN_PROGRESS

            self.log(f"\n📤 第 {attempt + 1}/{MAX_RETRIES} 次调用 {model}...")
            task.api_calls += 1

            success, output, error = self.call_model(
                model, prompt, system_prompt, timeout
            )

            if success:
                self.log(f"✅ 调用成功！输出长度: {len(output)} 字符")
                task.status = TaskStatus.COMPLETED
                return output
            else:
                self.log(f"❌ 调用失败: {error}")
                if attempt < MAX_RETRIES - 1:
                    self.log(f"⏳ 等待 {RETRY_DELAY} 秒后重试...")
                    time.sleep(RETRY_DELAY)

        # 3次都失败，回退到默认模型
        self.log(f"\n⚠️  {model} 连续 {MAX_RETRIES} 次调用失败")
        self.log(f"🔄 触发回退机制，切换到默认模型: {DEFAULT_FALLBACK_MODEL}")

        task.used_fallback = True
        task.fallback_reason = f"{model} 连续{MAX_RETRIES}次调用失败"
        task.status = TaskStatus.FALLBACK

        # 调用默认模型
        self.log(f"📤 调用默认模型 {DEFAULT_FALLBACK_MODEL}...")
        task.api_calls += 1

        success, output, error = self.call_model(
            DEFAULT_FALLBACK_MODEL,
            prompt,
            system_prompt,
            MODEL_CONFIG.get(DEFAULT_FALLBACK_MODEL, {}).get("timeout", 90),
        )

        if success:
            self.log(f"✅ 回退模型调用成功！输出长度: {len(output)} 字符")
            task.status = TaskStatus.COMPLETED
            return output
        else:
            self.log(f"❌ 回退模型也失败: {error}")
            task.status = TaskStatus.FAILED
            task.error = f"目标模型和回退模型都失败: {error}"
            return f"[分析失败: {task.error}]"

    def display_progress(self):
        """显示进度看板"""
        print("\n" + "=" * 100)
        print("📊 BMAD-EVO 执行进度看板")
        print("=" * 100)

        for task in self.tasks:
            icon = {
                TaskStatus.PENDING: "⏳",
                TaskStatus.IN_PROGRESS: "🔄",
                TaskStatus.RETRYING: "🔄",
                TaskStatus.COMPLETED: "✅",
                TaskStatus.FALLBACK: "⚠️",
                TaskStatus.FAILED: "❌",
            }.get(task.status, "⏳")

            status_line = f"{icon} 专家{task.phase}: {task.name} ({task.model})"

            if task.status == TaskStatus.COMPLETED:
                if task.used_fallback:
                    status_line += f" | ⚠️  使用回退模型"
                else:
                    status_line += f" | ✅ 完成"
                status_line += f" | {len(task.output)}字 | API调用:{task.api_calls}次"
            elif task.status == TaskStatus.FALLBACK:
                status_line += f" | ⚠️  回退中..."
            elif task.status == TaskStatus.FAILED:
                status_line += f" | ❌ 失败"

            print(status_line)

        completed = sum(1 for t in self.tasks if t.status == TaskStatus.COMPLETED)
        fallback = sum(1 for t in self.tasks if t.used_fallback)
        failed = sum(1 for t in self.tasks if t.status == TaskStatus.FAILED)

        print("\n" + "-" * 100)
        print(
            f"📈 统计: ✅ {completed}完成 | ⚠️  {fallback}回退 | ❌ {failed}失败 | 总计:{len(self.tasks)}"
        )
        print("=" * 100)

    def generate_report(self) -> str:
        """生成最终报告"""
        completed = sum(1 for t in self.tasks if t.status == TaskStatus.COMPLETED)
        fallback = sum(1 for t in self.tasks if t.used_fallback)

        report = f"""# {self.task_name}分析报告
# BMAD-EVO v3.0 标准执行报告

**生成时间**: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}  
**执行状态**: {completed}/{len(self.tasks)} 专家成功完成  
**使用回退模型**: {fallback} 个专家  
**执行日志**: {self.log_file.name}  

---

## 执行摘要

本次分析遵循BMAD-EVO v3.0规则：
- ✅ 每个模型最多3次重试
- ✅ 失败后自动回退到默认模型（{DEFAULT_FALLBACK_MODEL}）
- ✅ 完整的API调用追踪
- ✅ 透明的执行日志

### 统计

| 指标 | 数值 |
|------|------|
| 总专家数 | {len(self.tasks)} |
| 成功完成 | {completed} ({completed / len(self.tasks) * 100:.0f}%) |
| 使用回退 | {fallback} ({fallback / len(self.tasks) * 100:.0f}%) |
| 完全失败 | {len(self.tasks) - completed} ({(len(self.tasks) - completed) / len(self.tasks) * 100:.0f}%) |
| 总API调用 | {sum(t.api_calls for t in self.tasks)} 次 |

---

## 专家分析详细结果

"""

        for task in self.tasks:
            report += f"""
### 专家{task.phase}: {task.name}

**目标模型**: {task.model} ({MODEL_CONFIG.get(task.model, {}).get("name", task.model)})  
**分配角色**: {task.role}  
**执行状态**: {task.status.value}  
"""
            if task.used_fallback:
                report += f"**⚠️ 使用回退模型**: {DEFAULT_FALLBACK_MODEL}  \n"
                report += f"**回退原因**: {task.fallback_reason}  \n"

            report += f"""**API调用次数**: {task.api_calls} 次（含重试）  
**重试次数**: {task.retry_count} 次  
**执行耗时**: {task.duration:.1f}秒  

**分析结果**:

{task.output if task.output else "[无输出]"}

---
"""

        # 添加回退模型说明
        if fallback > 0:
            report += """
## 回退模型说明

以下专家因目标模型连续3次调用失败，已自动切换至默认模型完成分析：

| 专家 | 原模型 | 回退原因 |
|------|--------|----------|
"""
            for task in self.tasks:
                if task.used_fallback:
                    report += (
                        f"| {task.name} | {task.model} | {task.fallback_reason} |\n"
                    )

            report += f"""
**默认回退模型**: {DEFAULT_FALLBACK_MODEL}  
**说明**: 回退模型同样具备分析能力，结果可信，但可能在特定领域专业性略有差异。

---
"""

        report += """
## 系统说明

本报告由BMAD-EVO v3.0系统生成，遵循以下规则：
1. 每个子任务独立调用指定AI模型
2. 失败时自动重试最多3次
3. 连续失败后回退到默认模型
4. 所有执行过程透明记录

---

**报告完成**  
**BMAD-EVO v3.0 Standard Executor**
"""

        return report

    def save_results(self, report: str):
        """保存结果"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

        # 保存Markdown报告
        md_file = self.output_dir / f"{self.task_name}_report_{timestamp}.md"
        with open(md_file, "w", encoding="utf-8") as f:
            f.write(report)

        # 保存JSON数据
        json_data = {
            "task_name": self.task_name,
            "timestamp": timestamp,
            "tasks": [
                {
                    "phase": t.phase,
                    "name": t.name,
                    "model": t.model,
                    "status": t.status.value,
                    "output": t.output,
                    "api_calls": t.api_calls,
                    "retry_count": t.retry_count,
                    "used_fallback": t.used_fallback,
                    "duration": t.duration,
                }
                for t in self.tasks
            ],
        }
        json_file = self.output_dir / f"{self.task_name}_data_{timestamp}.json"
        with open(json_file, "w", encoding="utf-8") as f:
            json.dump(json_data, f, ensure_ascii=False, indent=2)

        self.log(f"\n💾 报告已保存: {md_file}")
        self.log(f"💾 数据已保存: {json_file}")

        return md_file, json_file


# ============================================================================
# 示例用法
# ============================================================================
def example_usage():
    """示例：如何创建并执行一个7专家分析任务"""

    # 1. 创建执行器
    executor = BMADEVOExecutor(
        task_name="oil_investment_analysis", output_dir="./results"
    )

    # 2. 定义7个专家
    experts = [
        (0, "最新情报整合师", "minimax-m2.5", "整合情报，提取关键信息"),
        (1, "地缘政治分析师", "glm-5", "分析博弈格局"),
        (2, "能源经济学家", "kimi-k2.5", "预测能源价格"),
        (3, "战略情报专家", "glm-5", "分析利益驱动"),
        (4, "全球影响评估师", "kimi-k2.5", "评估宏观影响"),
        (5, "投资策略顾问", "qwen3.5-plus", "给出投资建议"),
        (6, "风险管理师", "qwen3.5-plus", "构建风险框架"),
    ]

    # 3. 初始化任务
    for phase, name, model, role in experts:
        task = AnalystTask(phase=phase, name=name, model=model, role=role)
        executor.tasks.append(task)

    # 4. 显示初始状态
    executor.display_progress()

    # 5. 执行每个专家（这里需要补充具体的prompts）
    print("\n⚠️ 提示：这是一个示例框架，需要补充具体的分析prompts才能运行")
    print("💡 请根据具体任务需求，完善prompts后执行")


if __name__ == "__main__":
    example_usage()
