#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
BMAD-EVO v3.0 - 串行7专家联动分析系统
关键特性：
1. 顺序执行：专家0 -> 专家1 -> ... -> 专家6
2. 逐个完成：每个专家完成后再启动下一个
3. 上下文传递：前面专家的结果传递给后续专家
4. 实时进度：Todo/Checked List显示
5. 高质量Prompt：确保输出符合预期
"""

import sys
import json
import requests
import time
from pathlib import Path
from datetime import datetime
from typing import Dict, Tuple, Optional

sys.stdout.reconfigure(encoding="utf-8")

# 配置
API_KEY = "sk-sp-68f6997fc9924babb9f6b50c03a5a529"
BASE_URL = "https://coding.dashscope.aliyuncs.com/v1"
TIMEOUT = 120  # 每个专家120秒超时


def print_header(text):
    print("\n" + "=" * 80)
    print(text)
    print("=" * 80)


def print_separator():
    print("-" * 80)


def call_model(model: str, prompt: str, system: str = "") -> Tuple[bool, str]:
    """调用单个模型"""
    headers = {
        "Authorization": f"Bearer {API_KEY}",
        "Content-Type": "application/json",
    }

    messages = []
    if system:
        messages.append({"role": "system", "content": system})
    messages.append({"role": "user", "content": prompt})

    payload = {
        "model": model,
        "messages": messages,
        "temperature": 0.7,
        "max_tokens": 2000,
    }

    try:
        response = requests.post(
            f"{BASE_URL}/chat/completions",
            headers=headers,
            json=payload,
            timeout=TIMEOUT,
        )

        if response.status_code == 200:
            data = response.json()
            text = data["choices"][0]["message"]["content"]
            return True, text
        else:
            return False, f"HTTP {response.status_code}: {response.text[:200]}"

    except requests.exceptions.Timeout:
        return False, f"Timeout ({TIMEOUT}s)"
    except Exception as e:
        return False, str(e)


# 任务列表
TASKS = [
    {
        "phase": 0,
        "name": "最新情报整合师",
        "model": "kimi-k2.5",
        "desc": "基于真实情报，提取关键投资信息",
    },
    {
        "phase": 1,
        "name": "地缘政治分析师",
        "model": "glm-5",
        "desc": "分析博弈格局和冲突演进路径",
    },
    {
        "phase": 2,
        "name": "能源经济学家",
        "model": "kimi-k2.5",
        "desc": "预测油价、天然气、能源产品价格",
    },
    {
        "phase": 3,
        "name": "战略情报专家",
        "model": "glm-5",
        "desc": "分析利益相关方驱动力和隐藏议程",
    },
    {
        "phase": 4,
        "name": "全球影响评估师",
        "model": "kimi-k2.5",
        "desc": "评估大宗商品、美元指数、美债趋势",
    },
    {
        "phase": 5,
        "name": "投资策略顾问",
        "model": "qwen3.5-plus",
        "desc": "化工、粮食板块投资建议",
    },
    {
        "phase": 6,
        "name": "风险管理师",
        "model": "qwen3.5-plus",
        "desc": "构建概率化演进路径和风险矩阵",
    },
]

# 基础情报
INTELLIGENCE = """
【2026年3月美以伊朗冲突 - 核心情报】

【战事时间线】
- D1 (2月28日): 冲突爆发，美以发动"史诗狂怒行动"
- D2 (3月1日): 伊朗最高领袖哈梅内伊确认遇害
- D19 (3月18日): 伊朗居民区遭袭，12死116伤
- D20 (3月19日): 海湾12国联合声明谴责伊朗
- D22 (3月21日): 纳坦兹核设施遭袭
- D24 (3月23日): 内塔尼亚胡软化，考虑协议结束
- D28 (3月27日): 美以空袭伊朗两大钢铁厂
- D30 (3月29日): 阿联酋、巴林铝厂遭袭
- D31 (3月30日): 当前，冲突持续31天

【油价与能源价格】
- 布伦特原油: $112-116/桶 (已涨50%)
- WTI原油: $99-101/桶
- 花旗预测: 若海峡长期关闭，Q2-Q3均价$130/桶
- 伊朗威胁: 可能达$200/桶
- 欧洲能源成本: 已增加60亿欧元
- 霍尔木兹海峡: 伊朗宣布关闭，全球1/5石油运输受阻

【粮食与化工价格】
- 国际小麦: $225-242/吨 (较年初+16.49%)
- 国内玉米: 2447元/吨
- 豆粕: 3439元/吨 (+8%周涨幅)
- 尿素: 1800-1900元/吨 (供应风险增加)

【航运与保险】
- SCFI运价指数: 1710.35 (+221点)
- VLCC运价: 60000-75000美元/天
- 绕行好望角: 交货延迟14-20天
- 战争险保费: 单日跳涨50%
- 保险除外区域: 巴林、科威特、卡塔尔、阿曼

【各国表态】
- 美国: 特朗普主导攻击，要求48小时开放海峡
- 以色列: 内塔尼亚胡3月23日软化，考虑协议结束
- 伊朗: 新领袖穆杰塔巴接任，坚决反击，威胁打击沙特石油设施
- 海湾12国: 3月19日联合声明谴责伊朗，沙特允许美军使用基地
- 中国: 呼吁停火，撤侨3000人，谴责违反国际法
- 欧洲: 英法德联合谴责但称"不是我们的战争"
"""


def get_prompt(phase: int, context: str) -> Tuple[str, str]:
    """获取每个专家的Prompt"""

    if phase == 0:
        # 专家0: 情报整合师
        system = "You are a professional intelligence analyst specializing in extracting key investment information from raw data."
        prompt = f"""Analyze the following real intelligence about the US-Israel-Iran conflict and extract key information for investment decision-making.

REAL INTELLIGENCE:
{INTELLIGENCE}

TASK:
Extract and organize the following:
1. Key timeline events with specific dates
2. Critical price data (oil, grains, chemicals, shipping)
3. Changes in country positions
4. The 3 most important intelligence points for investors
5. Key uncertainties and risks

REQUIREMENTS:
- Be specific with numbers and dates
- Focus on investment relevance
- Output in structured format with clear headings
- Length: 300-500 words"""
        return system, prompt

    elif phase == 1:
        # 专家1: 地缘政治分析师
        system = "You are a geopolitical analysis expert. Analyze international conflicts and power dynamics."
        prompt = f"""Analyze the geopolitical game in the US-Israel-Iran conflict.

CONTEXT:
{INTELLIGENCE}

PREVIOUS EXPERT ANALYSIS:
{context}

TASK:
Analyze the following:
1. Real intentions behind Israel's March 23 softening (tactical delay or genuine?)
2. Deep reasons for Gulf states' collective shift to anti-Iran stance
3. Decision-making logic of Iran's new leadership under Mojtaba Khamenei
4. Three most likely conflict evolution paths with probability estimates

REQUIREMENTS:
- Provide probability estimates for each scenario
- Consider how geopolitical evolution affects energy markets
- Length: 400-600 words
- Be analytical and strategic"""
        return system, prompt

    elif phase == 2:
        # 专家2: 能源经济学家
        system = "You are an energy economics expert. Predict oil, gas, and energy product price trends."
        prompt = f"""Predict energy price trends based on the conflict.

CURRENT DATA:
- Brent crude: $112-116/barrel (+50%)
- WTI: $99-101/barrel
- Strait of Hormuz: Closed by Iran, 20% of global oil transport blocked
- Citi forecast: If strait remains closed, Q2-Q3 average $130/barrel

PREVIOUS EXPERT ANALYSIS:
{context}

TASK:
Predict:
1. Oil price ranges for next 1 month, 3 months, 6 months (with specific numbers and probabilities)
2. Natural gas price trends (European TTF, US Henry Hub, Asian LNG)
3. Energy price matrix under different scenarios (base case, high tension, extreme)

REQUIREMENTS:
- Must provide quantitative predictions with numbers
- Include probability estimates for each scenario
- Consider geopolitical factors from previous analysis
- Length: 400-600 words"""
        return system, prompt

    elif phase == 3:
        # 专家3: 战略情报专家
        system = "You are a strategic intelligence expert. Analyze stakeholder driving forces and hidden agendas."
        prompt = f"""Analyze the hidden forces and agendas behind the conflict.

PREVIOUS EXPERT ANALYSIS:
{context}

TASK:
Deep-dive analysis:
1. Trump's real objectives (election considerations? oil group interests? Israel lobby?)
2. Netanyahu's domestic political pressures and survival logic
3. Power base and decision-making of Iran's new leadership
4. Saudi Crown Prince's strategic calculations
5. Hidden red lines and unspoken motivations of all parties

REQUIREMENTS:
- Reveal underlying motivations
- Apply game theory analysis where appropriate
- Length: 500-700 words
- Be insightful and analytical"""
        return system, prompt

    elif phase == 4:
        # 专家4: 全球影响评估师
        system = "You are a global macroeconomic impact assessor. Analyze commodities, USD, and Treasury trends."
        prompt = f"""Assess global macroeconomic impacts of the conflict.

CURRENT DATA:
- Oil: +50%
- Wheat: +16.49% YTD
- Urea: 1800-1900 RMB/ton
- War risk insurance: +50%

PREVIOUS EXPERT ANALYSIS:
{context}

TASK:
Assess:
1. Commodity price trends (crude, gold, copper, aluminum, wheat, corn, soybeans)
2. US Dollar Index trajectory (safe-haven demand, Fed policy)
3. Treasury yield changes (inflation expectations, safe-haven demand)
4. Global inflation impact (US, Europe, China)

REQUIREMENTS:
- Provide 1-month, 3-month, 6-month quantitative forecasts
- Include specific price targets or ranges
- Consider energy price predictions from previous analysis
- Length: 500-700 words"""
        return system, prompt

    elif phase == 5:
        # 专家5: 投资策略顾问
        system = "You are an investment strategy advisor. Provide actionable investment recommendations."
        prompt = f"""Provide specific investment recommendations based on comprehensive analysis.

PREVIOUS EXPERT ANALYSIS:
{context}

TASK:
Provide:
1. Chemical sector recommendations (urea, methanol, ethylene) - specific stocks/futures, entry points, stop-loss
2. Agriculture sector recommendations (wheat, corn, soybeans) - futures allocation, agricultural stocks
3. Energy sector recommendations (traditional oil companies vs new energy) - specific tickers, targets, stop-loss
4. Cross-asset allocation strategy (stocks, bonds, commodities, cash ratios)

REQUIREMENTS:
- Must be actionable with specific numbers and percentages
- Include entry prices and stop-loss levels
- Provide portfolio allocation percentages
- Length: 500-700 words
- Be practical and specific"""
        return system, prompt

    elif phase == 6:
        # 专家6: 风险管理师
        system = "You are a risk management expert. Build probabilistic evolution paths and risk matrices."
        prompt = f"""Construct risk framework and final investment synthesis.

ALL PREVIOUS EXPERT ANALYSES:
{context}

TASK:
Construct:
1. Scenario analysis with specific probabilities:
   - Scenario A: Quick ceasefire (probability?%)
   - Scenario B: Long-term standoff 3-6 months (probability?%)
   - Scenario C: Full-scale war (probability?%)
   - Scenario D: Proxy war expansion (probability?%)

2. Investment change matrix under each scenario:
   | Asset | Scenario A | Scenario B | Scenario C | Scenario D |
   | Oil | $? | $? | $? | $? |
   | Gold | $? | $? | $? | $? |
   | USD | ? | ? | ? | ? |
   | Chemicals | ? | ? | ? | ? |
   | Grains | ? | ? | ? | ? |

3. Key trigger signals:
   - Red alert (immediate liquidation)
   - Orange alert (reduce 50%)
   - Yellow alert (enhance monitoring)
   - Green opportunity (add positions)

4. Final investment recommendation:
   - Conservative investor allocation
   - Balanced investor allocation
   - Aggressive investor allocation

REQUIREMENTS:
- Must quantify everything with specific probabilities and price ranges
- Provide clear risk management guidelines
- Length: 600-800 words
- Be comprehensive and actionable"""
        return system, prompt

    return "You are an analyst.", "Please analyze."


def display_progress(completed_tasks, current_task=None):
    """显示进度看板"""
    print("\n" + "=" * 80)
    print("📊 BMAD-EVO 串行7专家分析 - 实时进度")
    print("=" * 80)

    for task in TASKS:
        phase = task["phase"]
        if phase in completed_tasks:
            status = "✅ 已完成"
            output_len = len(completed_tasks[phase])
        elif current_task == phase:
            status = "🔄 执行中..."
            output_len = ""
        else:
            status = "⏳ 等待"
            output_len = ""

        print(f"{status} 专家{phase}: {task['name']:<20} | {output_len}")

    completed_count = len(completed_tasks)
    print("\n" + "-" * 80)
    print(f"📈 进度: {completed_count}/7 完成 ({completed_count / 7 * 100:.0f}%)")
    print("=" * 80)


def main():
    print_header("🚀 BMAD-EVO v3.0 - 串行7专家联动分析系统")
    print("任务: 美以伊朗冲突投资决策分析")
    print("模式: 顺序执行，逐个完成，传递上下文")
    print("预计耗时: 20-30分钟")
    print_separator()

    results = {}

    # 逐个执行专家
    for task in TASKS:
        phase = task["phase"]
        name = task["name"]
        model = task["model"]

        display_progress(results, phase)

        print_header(f"🔄 启动专家{phase}: {name}")
        print(f"模型: {model}")
        print(f"任务: {task['desc']}")
        print_separator()

        # 准备上下文（前面所有专家的结果）
        context = ""
        if phase > 0:
            for p in range(phase):
                if p in results:
                    context += f"\n=== 专家{p}分析摘要 ===\n"
                    context += results[p][:500] + "\n"

        # 获取Prompt
        system, prompt = get_prompt(phase, context)

        print(f"⏳ 正在调用 {model}...")
        start_time = time.time()

        success, output = call_model(model, prompt, system)

        elapsed = time.time() - start_time

        if success:
            print(f"✅ 调用成功！耗时: {elapsed:.1f}秒")
            print(f"📄 输出长度: {len(output)} 字符")
            print(f"\n📝 输出预览:\n{output[:300]}...")
            results[phase] = output
        else:
            print(f"❌ 调用失败: {output}")
            print("⏳ 5秒后重试...")
            time.sleep(5)

            # 重试一次
            print(f"🔄 重试调用 {model}...")
            success, output = call_model(model, prompt, system)

            if success:
                print(f"✅ 重试成功！")
                results[phase] = output
            else:
                print(f"❌ 重试失败，跳过此专家")
                results[phase] = f"[分析失败: {output}]"

        print_separator()
        time.sleep(2)  # 短暂休息，避免请求过快

    # 最终进度
    display_progress(results)

    # 保存结果
    print_header("💾 保存分析结果")

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

    # 保存为JSON
    json_file = f"serial_analysis_{timestamp}.json"
    with open(json_file, "w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, indent=2)
    print(f"✅ JSON数据已保存: {json_file}")

    # 保存为Markdown报告
    md_file = f"serial_analysis_report_{timestamp}.md"
    with open(md_file, "w", encoding="utf-8") as f:
        f.write(f"""# 美以伊朗冲突 - 串行7专家联动分析报告

**生成时间**: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}  
**执行模式**: 串行顺序执行  
**完成率**: {len(results)}/7  

---

## 专家分析结果

""")
        for phase, output in results.items():
            task_name = TASKS[phase]["name"]
            f.write(f"""
### 专家{phase}: {task_name}

{output}

---
""")

    print(f"✅ Markdown报告已保存: {md_file}")

    print_header("🎉 分析完成！")
    print(f"📊 完成率: {len(results)}/7 ({len(results) / 7 * 100:.0f}%)")
    print(f"💾 结果文件: {json_file}, {md_file}")


if __name__ == "__main__":
    main()
