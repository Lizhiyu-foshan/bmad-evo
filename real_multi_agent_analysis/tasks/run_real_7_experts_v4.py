#!/usr/bin/env python3
"""
BMAD-EVO v3.0 v4 - 真实7专家协同分析
修复：增加错误处理、重试机制、真实展示每个模型的调用过程
"""

import sys
import json
import requests
import time
from pathlib import Path
from typing import Dict, List, Any, Optional
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum

sys.stdout.reconfigure(encoding="utf-8")

# API配置
ALI_API_KEY = "sk-sp-68f6997fc9924babb9f6b50c03a5a529"
ALI_BASE_URL = "https://coding.dashscope.aliyuncs.com/v1"

MODEL_MAPPING = {
    "glm-5": "glm-5",
    "kimi-k2.5": "kimi-k2.5",
    "qwen3.5-plus": "qwen3.5-plus",
    "minimax-m2.5": "MiniMax-M2.5",
}


class TaskStatus(Enum):
    PENDING = "[待执行]"
    IN_PROGRESS = "[执行中]"
    COMPLETED = "[已完成]"
    FAILED = "[失败]"
    RETRYING = "[重试中]"


@dataclass
class AnalystTask:
    phase: int
    name: str
    model: str
    focus: str
    status: TaskStatus = TaskStatus.PENDING
    output: str = ""
    error: str = ""
    duration: str = ""
    api_calls: int = 0


class RealMultiAgentSystem:
    def __init__(self):
        self.tasks: List[AnalystTask] = []
        self.results = {}

    def call_model(
        self, model: str, prompt: str, system_prompt: str, max_retries: int = 2
    ) -> Dict:
        """真实调用模型，带重试机制"""
        headers = {
            "Authorization": f"Bearer {ALI_API_KEY}",
            "Content-Type": "application/json",
        }

        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})

        payload = {
            "model": MODEL_MAPPING.get(model, model),
            "messages": messages,
            "temperature": 0.7,
            "max_tokens": 4000,
        }

        for attempt in range(max_retries + 1):
            try:
                print(f"    🔄 API调用尝试 {attempt + 1}/{max_retries + 1}...")
                response = requests.post(
                    f"{ALI_BASE_URL}/chat/completions",
                    headers=headers,
                    json=payload,
                    timeout=120,
                )
                response.raise_for_status()
                data = response.json()

                return {
                    "success": True,
                    "text": data["choices"][0]["message"]["content"],
                    "model": model,
                    "usage": data.get("usage", {}),
                    "error": None,
                }
            except Exception as e:
                error_msg = str(e)
                print(f"    ❌ 调用失败: {error_msg[:100]}")
                if attempt < max_retries:
                    print(f"    ⏳ 等待3秒后重试...")
                    time.sleep(3)
                else:
                    return {
                        "success": False,
                        "text": "",
                        "model": model,
                        "usage": {},
                        "error": error_msg,
                    }

    def run_analysis(self):
        """运行真实的7专家分析"""
        print("\n" + "=" * 100)
        print("🚀 BMAD-EVO v3.0 v4 - 真实7专家协同分析系统")
        print("=" * 100)
        print("\n📋 本系统将真实调用7个不同的AI模型进行协同分析")
        print("🎯 每个专家将独立分析并返回结果")
        print("⏱️  预计总耗时: 10-15分钟")
        print("=" * 100)

        # 定义7个专家
        experts = [
            (0, "最新情报整合师", "minimax-m2.5", "整合真实情报，提取关键投资信息"),
            (1, "地缘政治分析师", "glm-5", "分析各国博弈格局和冲突演进路径"),
            (2, "能源经济学家", "kimi-k2.5", "预测油价、天然气、能源产品价格趋势"),
            (3, "战略情报专家", "glm-5", "分析利益相关方驱动力量和隐藏议程"),
            (4, "全球影响评估师", "kimi-k2.5", "评估大宗商品、美元指数、美债趋势"),
            (5, "投资策略顾问", "qwen3.5-plus", "化工、粮食板块投资建议"),
            (6, "风险管理师", "qwen3.5-plus", "构建概率化演进路径和风险矩阵"),
        ]

        # 初始化任务
        for phase, name, model, focus in experts:
            task = AnalystTask(phase=phase, name=name, model=model, focus=focus)
            self.tasks.append(task)

        # 顺序执行（真实调用每个模型）
        for i, task in enumerate(self.tasks):
            self._execute_single_analyst(task, i)
            self._show_progress()

        # 汇总结果
        self._compile_results()

    def _execute_single_analyst(self, task: AnalystTask, index: int):
        """执行单个分析师（真实API调用）"""
        print(f"\n{'=' * 100}")
        print(f"🔄 启动专家{task.phase}: {task.name}")
        print(f"📌 模型: {task.model}")
        print(f"🎯 任务: {task.focus}")
        print(f"{'=' * 100}")

        task.status = TaskStatus.IN_PROGRESS
        start_time = datetime.now()

        # 根据专家类型准备不同的prompt
        prompts = self._get_prompts_for_analyst(task.phase)

        print(f"\n📤 发送请求到模型...")
        result = self.call_model(task.model, prompts["user"], prompts["system"])
        task.api_calls += 1

        end_time = datetime.now()
        duration = (end_time - start_time).total_seconds()
        task.duration = f"{duration:.1f}秒"

        if result["success"]:
            task.output = result["text"]
            task.status = TaskStatus.COMPLETED
            print(f"\n✅ 专家{task.phase}分析成功！")
            print(f"📊 输出长度: {len(result['text'])} 字符")
            print(f"⏱️  耗时: {task.duration}")
            print(f"📝 前200字预览: {result['text'][:200]}...")
        else:
            task.output = f"[分析失败: {result['error'][:100]}]"
            task.error = result["error"]
            task.status = TaskStatus.FAILED
            print(f"\n❌ 专家{task.phase}分析失败！")
            print(f"⚠️  错误: {result['error'][:200]}")

        # 保存结果
        self.results[f"expert_{task.phase}"] = {
            "name": task.name,
            "model": task.model,
            "status": task.status.value,
            "output": task.output,
            "duration": task.duration,
            "error": task.error,
        }

    def _get_prompts_for_analyst(self, phase: int) -> Dict[str, str]:
        """为每个专家准备特定的prompt"""

        base_intelligence = """
当前真实情报（2026年3月30日）：
- 冲突持续31天（2月28日爆发）
- 油价：布伦特$112-116/桶（+50%）
- 霍尔木兹海峡：伊朗宣布关闭
- 以色列：3月23日态度软化，考虑协议结束
- 海湾12国：3月19日联合声明谴责伊朗
- 伊朗：新领袖穆杰塔巴接任，哈梅内伊遇害
"""

        prompts = {
            0: {
                "system": "你是最新情报整合专家。基于提供的情报，提取关键时间节点、价格数据和各国立场变化。",
                "user": f"请基于以下真实情报，提取关键投资信息：\n{base_intelligence}\n\n请输出：\n1. 关键时间节点（标注日期）\n2. 重要价格数据（油价、粮食、化工）\n3. 各国立场关键变化\n4. 对投资影响最大的3个情报点",
            },
            1: {
                "system": "你是地缘政治分析专家。分析各国博弈格局和冲突可能的演进路径。",
                "user": f"基于以下真实情报，分析地缘政治博弈：\n{base_intelligence}\n\n请分析：\n1. 以色列3月23日态度软化的真实意图\n2. 海湾12国集体转向的原因\n3. 冲突最可能的3种演进路径及概率",
            },
            2: {
                "system": "你是能源经济专家。预测油价、天然气等能源产品价格趋势。",
                "user": f"基于以下真实能源数据，预测价格趋势：\n{base_intelligence}\n\n当前数据：\n- 布伦特：$112-116/桶\n- 花旗预测：若海峡关闭，Q2-Q3均价$130/桶\n- 伊朗威胁：可能达$200/桶\n\n请预测：\n1. 未来1/3/6个月的油价区间\n2. 天然气价格趋势\n3. 各种情景下的能源价格矩阵",
            },
            3: {
                "system": "你是战略情报专家。分析各方利益集团的驱动力量和隐藏议程。",
                "user": f"基于以下真实情报，分析各方博弈：\n{base_intelligence}\n\n请分析：\n1. 特朗普政府的真实目标\n2. 内塔尼亚胡的国内政治压力\n3. 伊朗新领导层的决策逻辑\n4. 沙特王储的考量\n5. 各方未公开的真实红线",
            },
            4: {
                "system": "你是全球宏观经济学家。分析大宗商品、美元指数、美债趋势。",
                "user": f"基于以下真实数据，分析宏观影响：\n{base_intelligence}\n\n当前数据：\n- 油价：+50%\n- 小麦：较年初+16.49%\n- 尿素：1800-1900元/吨\n- 战争险保费：+50%\n\n请预测：\n1. 大宗商品价格趋势\n2. 美元指数走势\n3. 美债收益率变化\n4. 全球通胀影响",
            },
            5: {
                "system": "你是投资策略专家。基于分析给出化工、粮食等板块的投资建议。",
                "user": f"基于以下真实数据，给出投资建议：\n{base_intelligence}\n\n请给出：\n1. 化工板块投资建议（尿素、甲醇等）\n2. 粮食农业投资建议（小麦、玉米、豆粕）\n3. 能源板块投资建议\n4. 具体股票/期货标的和入场点位",
            },
            6: {
                "system": "你是风险管理专家。构建概率化演进路径和风险矩阵。",
                "user": f"基于以下真实情报，构建风险框架：\n{base_intelligence}\n\n请输出：\n1. 情景分析与概率（快速停火、长期对峙、全面战争）\n2. 各情景下投资品变化矩阵\n3. 关键触发信号（红/橙/黄/绿警报）\n4. 动态对冲策略\n5. 最终投资建议（保守/平衡/激进型配置）",
            },
        }

        return prompts.get(phase, {"system": "", "user": "请分析当前局势"})

    def _show_progress(self):
        """显示进度"""
        print("\n" + "=" * 100)
        print("📊 实时进度看板")
        print("=" * 100)

        completed = sum(1 for t in self.tasks if t.status == TaskStatus.COMPLETED)
        failed = sum(1 for t in self.tasks if t.status == TaskStatus.FAILED)

        for task in self.tasks:
            icon = {
                TaskStatus.PENDING: "⏳",
                TaskStatus.IN_PROGRESS: "🔄",
                TaskStatus.COMPLETED: "✅",
                TaskStatus.FAILED: "❌",
            }.get(task.status, "⏳")

            status_text = f"{icon} 专家{task.phase}: {task.name}"
            if task.status == TaskStatus.COMPLETED:
                status_text += f" | ✅ 完成 ({task.duration}) | {len(task.output)}字"
            elif task.status == TaskStatus.FAILED:
                status_text += f" | ❌ 失败"
            print(status_text)

        print("\n" + "-" * 100)
        print(
            f"📈 进度: {completed}/7 完成 | {failed}/7 失败 | 成功率: {completed / 7 * 100:.0f}%"
        )
        print("=" * 100)

    def _compile_results(self):
        """汇总所有结果"""
        print("\n" + "=" * 100)
        print("📊 生成最终综合分析报告...")
        print("=" * 100)

        completed = sum(1 for t in self.tasks if t.status == TaskStatus.COMPLETED)

        if completed == 0:
            print("\n❌ 所有专家分析失败，无法生成报告")
            return

        # 构建报告
        report = f"""# 美以伊朗冲突投资决策分析报告
# BMAD-EVO v3.0 v4 - 真实7专家协同分析

**报告时间**: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}  
**分析状态**: {completed}/7 专家成功完成  
**数据来源**: 2026年3月30日真实收集的情报  

---

## 专家分析详细结果

"""

        for task in self.tasks:
            report += f"""
### 专家{task.phase}: {task.name}

**模型**: {task.model}  
**状态**: {"✅ 完成" if task.status == TaskStatus.COMPLETED else "❌ 失败"}  
**耗时**: {task.duration}  
**API调用次数**: {task.api_calls}

**分析结果**:

{task.output if task.output else "[分析失败，无输出]"}

---
"""

        # 保存报告
        output_dir = Path("./real_multi_agent_analysis")
        output_dir.mkdir(exist_ok=True)

        report_file = output_dir / "real_7_experts_analysis_report.md"
        with open(report_file, "w", encoding="utf-8") as f:
            f.write(report)

        print(f"\n✅ 报告已生成！")
        print(f"📄 文件路径: {report_file}")
        print(f"📊 文件大小: {len(report)} 字符")
        print(f"📈 成功率: {completed}/7 ({completed / 7 * 100:.1f}%)")

        # 如果成功率低，给出警告
        if completed < 4:
            print("\n⚠️ 警告: 多数专家分析失败，报告可能不够全面")
            print("💡 建议: 检查API连接状态或稍后重试")


if __name__ == "__main__":
    system = RealMultiAgentSystem()
    system.run_analysis()
