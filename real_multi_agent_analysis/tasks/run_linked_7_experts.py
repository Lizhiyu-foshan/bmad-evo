#!/usr/bin/env python3
"""
BMAD-EVO v3.0 - 7专家联动协同分析系统
关键特性：
1. 专家顺序执行，传递分析结果
2. 每个专家参考前面专家的观点
3. 最终综合汇总，联动思考
4. 3次重试+默认模型回退
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

# 配置
ALI_API_KEY = "sk-sp-68f6997fc9924babb9f6b50c03a5a529"
ALI_BASE_URL = "https://coding.dashscope.aliyuncs.com/v1"

MODEL_CONFIG = {
    "minimax-m2.5": {"name": "MiniMax-M2.5", "timeout": 120},
    "glm-5": {"name": "GLM-5", "timeout": 120},
    "kimi-k2.5": {"name": "Kimi K2.5", "timeout": 120},
    "qwen3.5-plus": {"name": "Qwen3.5-Plus", "timeout": 120},
}

DEFAULT_FALLBACK_MODEL = "kimi-k2.5"
MAX_RETRIES = 3
RETRY_DELAY = 5


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


class LinkedAnalysisSystem:
    def __init__(self, task_name: str):
        self.task_name = task_name
        self.output_dir = Path("./results")
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.tasks: List[AnalystTask] = []
        self.cumulative_context = ""  # 累积的分析上下文
        self.headers = {
            "Authorization": f"Bearer {ALI_API_KEY}",
            "Content-Type": "application/json",
        }
        self.log_file = (
            self.output_dir
            / f"execution_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"
        )

    def log(self, message: str):
        timestamp = datetime.now().strftime("%H:%M:%S")
        log_line = f"[{timestamp}] {message}"
        print(log_line)
        with open(self.log_file, "a", encoding="utf-8") as f:
            f.write(log_line + "\n")

    def call_model(
        self, model: str, prompt: str, system_prompt: str, timeout: int
    ) -> Tuple[bool, str, str]:
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})

        payload = {
            "model": model,
            "messages": messages,
            "temperature": 0.7,
            "max_tokens": 4000,
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

    def execute_analyst(self, task: AnalystTask) -> str:
        """执行单个分析师（带重试和回退）"""
        self.log(f"\n{'=' * 80}")
        self.log(f"🔄 启动专家{task.phase}: {task.name}")
        self.log(f"   模型: {task.model}")
        self.log(f"   角色: {task.role}")
        self.log(f"{'=' * 80}")

        start_time = time.time()

        # 获取该专家的Prompt（包含累积上下文）
        system_prompt, user_prompt = self.get_prompts_for_analyst(task.phase)

        # 尝试调用目标模型（最多3次）
        for attempt in range(MAX_RETRIES):
            task.retry_count = attempt + 1
            task.status = TaskStatus.RETRYING if attempt > 0 else TaskStatus.IN_PROGRESS

            self.log(f"\n📤 第 {attempt + 1}/{MAX_RETRIES} 次调用 {task.model}...")
            task.api_calls += 1

            timeout = MODEL_CONFIG.get(task.model, {}).get("timeout", 120)
            success, output, error = self.call_model(
                task.model, user_prompt, system_prompt, timeout
            )

            if success:
                self.log(f"✅ 调用成功！输出长度: {len(output)} 字符")
                task.status = TaskStatus.COMPLETED
                task.duration = time.time() - start_time

                # 更新累积上下文
                self.update_context(task, output)
                return output
            else:
                self.log(f"❌ 调用失败: {error}")
                if attempt < MAX_RETRIES - 1:
                    self.log(f"⏳ 等待 {RETRY_DELAY} 秒后重试...")
                    time.sleep(RETRY_DELAY)

        # 3次都失败，回退到默认模型
        self.log(
            f"\n⚠️  {task.model} 连续 {MAX_RETRIES} 次失败，切换到默认模型 {DEFAULT_FALLBACK_MODEL}"
        )
        task.used_fallback = True
        task.status = TaskStatus.FALLBACK

        fallback_timeout = MODEL_CONFIG.get(DEFAULT_FALLBACK_MODEL, {}).get(
            "timeout", 120
        )
        task.api_calls += 1

        success, output, error = self.call_model(
            DEFAULT_FALLBACK_MODEL, user_prompt, system_prompt, fallback_timeout
        )

        if success:
            self.log(f"✅ 回退模型调用成功！输出长度: {len(output)} 字符")
            task.status = TaskStatus.COMPLETED
            task.duration = time.time() - start_time
            self.update_context(task, output)
            return output
        else:
            self.log(f"❌ 回退模型也失败: {error}")
            task.status = TaskStatus.FAILED
            task.error = error
            task.duration = time.time() - start_time
            return f"[分析失败: {error}]"

    def get_prompts_for_analyst(self, phase: int) -> Tuple[str, str]:
        """为每个专家准备Prompt（包含前面专家的分析）"""

        base_intelligence = """
【2026年3月美以伊朗冲突 - 核心情报】

【战事动态】
- 冲突持续31天（2026年2月28日爆发）
- 军事行动代号：美国"史诗狂怒行动" + 以色列"咆哮的狮子"
- 3月1日：伊朗最高领袖哈梅内伊确认遇害，穆杰塔巴接任
- 3月18日：伊朗居民区遭袭，12死116伤
- 3月21日：纳坦兹核设施遭袭，无放射性泄漏
- 3月27日：美以空袭伊朗两大钢铁厂
- 3月29日：阿联酋、巴林铝厂遭袭

【油价与能源】
- 布伦特原油：$112-116/桶（已涨50%）
- WTI原油：$99-101/桶
- 花旗预测：若海峡长期关闭，Q2-Q3均价$130/桶
- 伊朗威胁：可能达$200/桶
- 霍尔木兹海峡：伊朗宣布关闭，全球1/5石油运输受阻

【粮食与化工】
- 国际小麦：$225-242/吨，较年初+16.49%
- 国内玉米：2447元/吨
- 尿素：1800-1900元/吨，供应风险增加

【航运与保险】
- SCFI运价指数：1710.35（+221点）
- 战争险保费：单日跳涨50%
- 绕行好望角：交货延迟14-20天

【各国表态】
- 美国：特朗普主导攻击，要求48小时开放海峡
- 以色列：内塔尼亚胡3月23日软化，考虑协议结束
- 伊朗：新领袖坚决反击，威胁打击沙特石油设施
- 海湾12国：3月19日联合声明谴责伊朗
- 中国：呼吁停火，撤侨3000人
- 欧洲：英法德联合谴责但称"不是我们的战争"
"""

        prompts = {
            0: {
                "system": "You are the Latest Intelligence Integrator. Synthesize raw intelligence into structured investment-relevant insights.",
                "user": f"Based on the following real intelligence, extract key information for investment analysis:\n\n{base_intelligence}\n\nPlease provide:\n1. Key timeline events with dates\n2. Critical price data (oil, grains, chemicals, shipping)\n3. Changes in country positions\n4. The 3 most important intelligence points for investors\n5. Uncertainties and limitations\n\nOutput in structured format.",
            },
            1: {
                "system": "You are the Geopolitical Analyst. Analyze the geopolitical game based on real warfare and country positions.",
                "user": f"Based on the intelligence and the previous expert's analysis:\n\n{base_intelligence}\n\nPrevious Expert Analysis:\n{self.cumulative_context[:2000]}\n\nPlease analyze:\n1. Real intentions behind Israel's March 23 softening (tactical delay or genuine?)\n2. Deep reasons for Gulf states' collective shift (fear of Iran? US pressure?)\n3. Decision-making logic of Iran's new leadership\n4. Three most likely conflict evolution paths with probabilities\n\nConsider how the intelligence affects geopolitical risk assessment.",
            },
            2: {
                "system": "You are the Energy Economist. Predict oil, gas, and energy product price trends.",
                "user": f"Based on real energy data and previous experts' geopolitical analysis:\n\n{base_intelligence}\n\nPrevious Analysis Context:\n{self.cumulative_context[:2000]}\n\nPlease predict:\n1. Oil price ranges for next 1/3/6 months (with specific numbers and probabilities)\n2. Natural gas price trends (European TTF, US Henry Hub, Asian LNG)\n3. Energy price matrix under various scenarios\n4. Impact of geopolitical evolution on energy markets\n\nMust provide quantitative predictions.",
            },
            3: {
                "system": "You are the Strategic Intelligence Expert. Analyze stakeholders' driving forces and hidden agendas.",
                "user": f"Based on real intelligence and previous economic/geopolitical analysis:\n\n{base_intelligence}\n\nPrevious Analysis Context:\n{self.cumulative_context[:2000]}\n\nPlease deep-dive:\n1. Trump's real objectives (election considerations? oil group interests? Israel lobby?)\n2. Netanyahu's domestic political pressures\n3. Power base of Iran's new leadership\n4. Saudi Crown Prince's calculations\n5. Hidden red lines of all parties\n\nReveal underlying motivations and game theory dynamics.",
            },
            4: {
                "system": "You are the Global Impact Assessor. Analyze commodities, USD index, and Treasury trends.",
                "user": f"Based on all previous analyses (geopolitical + energy + strategic):\n\nPrevious Analysis Context:\n{self.cumulative_context[:2500]}\n\nPlease assess:\n1. Commodity price trends (crude, gold, copper, aluminum, wheat, corn, soybeans)\n2. US Dollar Index trajectory (safe-haven demand, Fed policy)\n3. Treasury yield changes (inflation expectations, safe-haven demand)\n4. Global inflation impact (US, Europe, China CPI effects)\n5. Central bank monetary policy responses\n\nProvide 1/3/6-month quantitative forecasts.",
            },
            5: {
                "system": "You are the Investment Strategy Advisor. Provide actionable investment recommendations.",
                "user": f"Based on comprehensive analysis from all previous experts:\n\nPrevious Analysis Context:\n{self.cumulative_context[:3000]}\n\nPlease provide:\n1. Chemical sector recommendations (urea, methanol, ethylene) - specific stocks/futures, entry points, stop-loss\n2. Agriculture sector recommendations (wheat, corn, soybeans) - futures allocation, agricultural stocks\n3. Energy sector recommendations (traditional vs new energy) - specific tickers, targets, stop-loss\n4. Industrial metals recommendations (aluminum, copper, steel)\n5. Cross-asset allocation strategy (stocks, bonds, commodities, cash ratios)\n\nMust be actionable with specific numbers and percentages.",
            },
            6: {
                "system": "You are the Risk Manager. Build probabilistic evolution paths and risk matrices.",
                "user": f"Based on ALL previous expert analyses (intelligence + geopolitical + energy + strategic + impact + investment):\n\nPrevious Analysis Context:\n{self.cumulative_context[:3500]}\n\nPlease construct:\n1. Scenario analysis with probabilities:\n   - Scenario A: Quick ceasefire (probability?%)\n   - Scenario B: Long-term standoff (probability?%)\n   - Scenario C: Full-scale war (probability?%)\n   - Scenario D: Proxy war expansion (probability?%)\n\n2. Investment change matrix under each scenario:\n   | Asset | Scenario A | Scenario B | Scenario C | Scenario D |\n   | Oil | $? | $? | $? | $? |\n   | Gold | $? | $? | $? | $? |\n   | USD | ? | ? | ? | ? |\n   etc.\n\n3. Key trigger signals (red/orange/yellow/green alerts)\n4. Dynamic hedging strategies\n5. Final investment recommendation (conservative/balanced/aggressive allocations)\n\nMust quantify everything with specific probabilities and price ranges.",
            },
        }

        return prompts.get(phase, ("You are an analyst.", "Please analyze."))

    def update_context(self, task: AnalystTask, output: str):
        """更新累积上下文"""
        self.cumulative_context += f"\n\n{'=' * 60}\n"
        self.cumulative_context += f"专家{task.phase}: {task.name}\n"
        self.cumulative_context += f"{'=' * 60}\n"
        self.cumulative_context += output[:2000]  # 限制长度避免过长
        self.cumulative_context += "\n"

    def display_progress(self):
        """显示进度看板"""
        print("\n" + "=" * 100)
        print("📊 BMAD-EVO 7专家联动分析 - 实时进度")
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

            status_line = f"{icon} 专家{task.phase}: {task.name}"

            if task.status == TaskStatus.COMPLETED:
                fallback_mark = " [回退]" if task.used_fallback else ""
                status_line += f"{fallback_mark} | {len(task.output)}字 | {task.duration:.0f}秒 | API:{task.api_calls}次"
            elif task.status == TaskStatus.FAILED:
                status_line += " | 失败"

            print(status_line)

        completed = sum(1 for t in self.tasks if t.status == TaskStatus.COMPLETED)
        fallback = sum(1 for t in self.tasks if t.used_fallback)
        failed = sum(1 for t in self.tasks if t.status == TaskStatus.FAILED)

        print("\n" + "-" * 100)
        print(f"📈 进度: {completed}/7 完成 | ⚠️ {fallback} 回退 | ❌ {failed} 失败")
        print("=" * 100)

    def run_analysis(self):
        """运行完整的7专家联动分析"""
        print("\n" + "🚀" * 50)
        print("🚀 BMAD-EVO v3.0 - 7专家联动协同分析系统")
        print("🚀" * 50)
        print(f"\n📋 任务：{self.task_name}")
        print("🎯 特性：")
        print("   • 专家顺序执行，传递分析结果")
        print("   • 每个专家参考前面专家的观点")
        print("   • 3次重试+默认模型回退")
        print("   • 最终综合汇总，联动思考")
        print("\n⏱️ 预计总耗时：15-20分钟")
        print("=" * 100)

        # 定义7个专家
        experts = [
            (0, "最新情报整合师", "minimax-m2.5", "整合情报，提取关键投资信息"),
            (1, "地缘政治分析师", "glm-5", "分析博弈格局和冲突演进"),
            (2, "能源经济学家", "kimi-k2.5", "预测能源价格趋势"),
            (3, "战略情报专家", "glm-5", "分析利益相关方驱动力"),
            (4, "全球影响评估师", "kimi-k2.5", "评估大宗商品和宏观趋势"),
            (5, "投资策略顾问", "qwen3.5-plus", "给出具体投资建议"),
            (6, "风险管理师", "qwen3.5-plus", "构建概率化演进路径"),
        ]

        # 初始化任务
        for phase, name, model, role in experts:
            task = AnalystTask(phase=phase, name=name, model=model, role=role)
            self.tasks.append(task)

        self.display_progress()

        # 顺序执行每个专家
        for task in self.tasks:
            output = self.execute_analyst(task)
            task.output = output
            self.display_progress()

        # 生成最终报告
        self.generate_final_report()

    def generate_final_report(self):
        """生成最终联动分析报告"""
        self.log("\n" + "=" * 100)
        self.log("📊 生成最终联动分析报告...")
        self.log("=" * 100)

        completed = sum(1 for t in self.tasks if t.status == TaskStatus.COMPLETED)
        fallback = sum(1 for t in self.tasks if t.used_fallback)

        report = f"""# {self.task_name}
# BMAD-EVO v3.0 - 7专家联动协同分析报告

**生成时间**: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}  
**执行状态**: {completed}/7 专家成功完成  
**使用回退模型**: {fallback} 个专家  
**总API调用**: {sum(t.api_calls for t in self.tasks)} 次  
**总耗时**: {sum(t.duration for t in self.tasks) / 60:.1f} 分钟  

---

## 执行摘要

本次分析采用**7专家联动协同模式**：
- ✅ 专家顺序执行，后一个专家参考前一个专家的分析
- ✅ 累积上下文传递，形成完整的分析链条
- ✅ 每个专家最多3次重试，失败后自动回退到默认模型
- ✅ 最终综合所有专家观点，形成联动结论

### 统计

| 指标 | 数值 |
|------|------|
| 总专家数 | 7 |
| 成功完成 | {completed} |
| 使用回退 | {fallback} |
| 完全失败 | {7 - completed} |

---

## 第一部分：专家分析详细结果（联动模式）

"""

        # 添加每个专家的详细分析
        for task in self.tasks:
            report += f"""
### 专家{task.phase}: {task.name}

**目标模型**: {task.model}  
**分配角色**: {task.role}  
**执行状态**: {task.status.value}  
**API调用**: {task.api_calls} 次（含{task.retry_count}次重试）  
**执行耗时**: {task.duration:.1f} 秒  
"""
            if task.used_fallback:
                report += f"**⚠️ 使用回退模型**: {DEFAULT_FALLBACK_MODEL}  \n"

            report += f"""
**分析结果**:

{task.output}

---
"""

        # 添加联动分析汇总
        report += """
## 第二部分：联动分析综合结论

### 一、各专家核心观点联动

"""

        # 尝试生成综合结论（使用回退模型）
        synthesis_prompt = f"""Based on the following 7-expert linked analysis, provide a comprehensive synthesis:

Expert Analyses Summary:
{self.cumulative_context[:4000]}

Please provide:
1. Key consensus points across all experts
2. Contradictions or uncertainties identified
3. Overall conflict evolution assessment
4. Unified investment recommendation integrating all perspectives
5. Critical risk factors that all experts agree on

Synthesize in Chinese, 500-800 words."""

        self.log("\n🔄 生成联动综合分析...")
        success, synthesis, _ = self.call_model(
            DEFAULT_FALLBACK_MODEL,
            synthesis_prompt,
            "You are a synthesis expert integrating multiple analyst perspectives.",
            120,
        )

        if success:
            report += synthesis
        else:
            report += "[综合分析生成失败，请参考各专家独立分析]"

        report += """

---

## 第三部分：风险提示与局限性

### 使用回退模型的专家
"""

        if fallback > 0:
            report += """
以下专家因目标模型连续3次调用失败，已自动切换至默认模型完成分析：

| 专家 | 原模型 | 回退原因 |
|------|--------|----------|
"""
            for task in self.tasks:
                if task.used_fallback:
                    report += f"| {task.name} | {task.model} | 连续{MAX_RETRIES}次调用失败 |\n"

            report += f"""
**说明**: 回退模型（{DEFAULT_FALLBACK_MODEL}）同样具备分析能力，但在特定领域的专业性可能略有差异。

"""
        else:
            report += "所有专家均使用原生指定模型完成分析，未触发回退机制。\n\n"

        report += """### 分析局限性

1. **时效性**: 基于2026年3月30日情报，局势可能快速变化
2. **信息局限**: 部分情报可能存在信源差异和宣传口径偏差
3. **模型局限**: AI分析基于训练数据和当前信息，可能出现黑天鹅事件
4. **联动局限**: 尽管专家参考前面分析，但仍可能存在逻辑断层

---

**报告完成**  
**BMAD-EVO v3.0 Linked Multi-Agent Analysis System**
"""

        # 保存报告
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        md_file = self.output_dir / f"{self.task_name}_linked_report_{timestamp}.md"
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
            "cumulative_context": self.cumulative_context,
        }
        json_file = self.output_dir / f"{self.task_name}_linked_data_{timestamp}.json"
        with open(json_file, "w", encoding="utf-8") as f:
            json.dump(json_data, f, ensure_ascii=False, indent=2)

        self.log(f"\n✅ 报告已保存: {md_file}")
        self.log(f"✅ 数据已保存: {json_file}")
        self.log(f"✅ 日志已保存: {self.log_file}")

        print("\n" + "=" * 100)
        print("🎉 7专家联动分析完成！")
        print("=" * 100)
        print(f"📄 报告: {md_file}")
        print(f"📊 完成率: {completed}/7 ({completed / 7 * 100:.0f}%)")
        print(f"⏱️  总耗时: {sum(t.duration for t in self.tasks) / 60:.1f} 分钟")
        print("=" * 100)


if __name__ == "__main__":
    system = LinkedAnalysisSystem("Iran_Israel_Conflict_Investment_Analysis")
    system.run_analysis()
