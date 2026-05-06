# 增量数据采集修复方案

## 问题诊断

### 5个根因

| # | 问题 | 严重度 | 位置 |
|---|------|--------|------|
| P1 | `DataCollectionPlanner.plan_for_role()` 被调用但**从未定义**，运行必崩 | **致命** | `thinking_chain.py:457` |
| P2 | 即使 `plan_for_role` 存在，它只是"规划"采集需求，**没有任何代码执行实际数据采集**（web搜索/API调用） | **致命** | `thinking_chain.py` 整个类 |
| P3 | `get_pre_execution_context()` 返回的 `enhanced_context` 在编排器中被创建后**未传入角色执行函数** | **严重** | `workflow_orchestrator_v3_final.py:369-386` |
| P4 | `ThinkingChainExecutor` 缺少 `execute_full_chain()` 统一入口方法 | **中等** | `thinking_chain.py` |
| P5 | OpenCode 环境中实际执行分析时绕过了代码路径（直接让LLM写报告），未调用框架代码 | **运行时** | 执行层面 |

### 数据流断裂图

```
当前设计（断裂的）:
                                        
  plan_for_role()  ← 不存在！→  AttributeError
       │                                
  (如果存在)                           
       ↓                                
  DataCollectionSpec  → 只打印，不执行  
       │                                
       ↓                                
  enhanced_context   → 未传入 _execute_phase_with_iteration
       │                                
       ✘  角色拿到的是空的/初始的上下文，无实时数据
```

```
期望设计:
  plan_for_role() → DataCollectionSpec
       ↓
  DataCollector.execute(spec) → 实时数据
       ↓
  enhanced_context（含实时数据）→ 注入角色执行
       ↓
  角色基于实时数据分析
```

---

## 修改计划

### 修改 1: 新建 `lib/v4/data_collector.py`（新文件）

**目的**: 实际执行数据采集，是当前完全缺失的核心组件

```
class DataCollector:
    """增量数据采集执行器"""
    
    def __init__(self, config):
        self.http_client = requests.Session()
        self.cache = {}  # 同一次分析中缓存，避免重复请求
        self.sources = {
            "market_price": self._fetch_market_price,
            "news_headlines": self._fetch_news,
            "economic_data": self._fetch_economic_data,
            "commodity_price": self._fetch_commodity_price,
        }
    
    def execute(self, spec: DataCollectionSpec) -> str:
        """执行数据采集，返回格式化的采集结果文本"""
        # 根据 spec.queries 和 spec.sources 选择采集方法
        # 调用对应的数据源
        # 格式化为 Markdown 文本返回
        
    def _fetch_market_price(self, queries) -> str:
        """从 tradingeconomics 或类似源抓取市场价格"""
        # 逐个 query 调用 web API
        # 例如: gold price, oil price, S&P 500, VIX 等
        
    def _fetch_news(self, queries) -> str:
        """从新闻源抓取最新头条"""
        # 使用 requests 请求 oilprice.com / news API
        
    def _fetch_economic_data(self, queries) -> str:
        """从 BLS / Fed 等源抓取经济数据"""
        # CPI, unemployment, Fed funds rate 等
        
    def _fetch_commodity_price(self, queries) -> str:
        """从 kitco 等源抓取大宗商品价格"""
        # gold, silver, copper, wheat 等
        
    def _call_url(self, url, timeout=30) -> str:
        """底层 HTTP 请求，带缓存和错误处理"""
```

**关键设计决策**:
- 使用 `requests`（已在环境中可用）
- 结果缓存：同一分析中相同 query 不重复请求
- 超时保护：单次请求 30s 上限
- 错误容忍：单个源失败不影响其他源，返回部分结果+失败说明
- 结果格式化为 Markdown 文本，直接可注入角色 prompt

**预估行数**: ~250-350 行

---

### 修改 2: 补全 `DataCollectionPlanner.plan_for_role()`（thinking_chain.py）

**目的**: 补上 P1 缺失的方法

```python
def plan_for_role(
    self,
    role_name: str,
    role_description: str,
    role_responsibilities: List[str],
    task_description: str,
    existing_data_summary: str,
    previous_roles_output: str,
) -> DataCollectionSpec:
    """分析角色需求，输出结构化的数据采集规格"""
    # 用 LLM 分析该角色需要什么额外数据
    # 对比 existing_data 中已有的内容
    # 输出 DataCollectionSpec（queries, sources, priority）
```

**实现方式**: 调用 LLM 分析角色职责 + 已有数据 → 输出结构化的 `DataCollectionSpec`

**预估行数**: ~80-100 行

---

### 修改 3: 串联采集流程（thinking_chain.py `get_pre_execution_context`）

**目的**: 让 `plan_for_role` → `DataCollector.execute()` 的链条接通

在 `ThinkingChainExecutor` 中:
```python
def __init__(self, ...):
    ...
    self.data_collector = DataCollector()  # 新增

def get_pre_execution_context(self, role_name, initial_data):
    ...
    spec = self.data_planner.plan_for_role(...)   # 修改 2 补全
    collected = self.data_collector.execute(spec)  # 修改 1 新增
    self.state.collected_data[role_name] = collected  # 记录采集结果
    ...
    # 将 collected 数据注入 context_parts
    context_parts.append(f"## 实时采集数据\n{collected}")
    ...
```

**预估改动**: ~15 行改动

---

### 修改 4: 编排器传入 `enhanced_context`（workflow_orchestrator_v3_final.py）

**目的**: 修复 P3 — 让角色执行时能拿到增量数据

当前代码 (line 369-386):
```python
enhanced_context, collection_spec = tc.get_pre_execution_context(...)
# enhanced_context 被创建但未使用！
phase_result = self._execute_phase_with_iteration(role, task_description, ...)
```

修改为:
```python
enhanced_context, collection_spec = tc.get_pre_execution_context(...)
phase_result = self._execute_phase_with_iteration(
    role, task_description, phase_num,
    additional_context=enhanced_context  # 新参数
)
```

同时修改 `_execute_phase_with_iteration` 和 `_execute_agent_with_feedback` 的签名，接收并使用 `additional_context`。

**预估改动**: ~30 行改动

---

### 修改 5: 添加 `execute_full_chain()` 入口（thinking_chain.py）

**目的**: 修复 P4 — 提供统一入口方法

```python
def execute_full_chain(
    self,
    task_description: str,
    initial_data: str,
    role_executor: Callable[[str, str, str], str],
) -> Dict[str, Any]:
    """
    完整思考链执行入口
    
    Args:
        task_description: 任务描述
        initial_data: 初始采集数据
        role_executor: 角色执行回调函数 (role_name, context) -> output
    
    Returns:
        完整的执行结果
    """
    # 1. 正向执行（含增量采集+双向反馈）
    # 2. 自我反思
    # 3. 如需修正，触发重新执行
    # 4. 返回最终结果
```

**预估行数**: ~60-80 行

---

### 修改 6: 配置文件更新（config/bmad.json）

在 `analysis.thinking_chain` 中新增:

```json
{
  "thinking_chain": {
    "data_collection": {
      "enabled": true,
      "sources": {
        "market_prices": "https://tradingeconomics.com",
        "commodity_prices": "https://kitco.com",
        "energy_news": "https://oilprice.com",
        "economic_data": "https://tradingeconomics.com/united-states"
      },
      "cache_ttl_seconds": 300,
      "request_timeout": 30,
      "max_retries": 2,
      "user_agent": "BMAD-EVO/4.0"
    }
  }
}
```

**预估改动**: ~20 行 JSON

---

## 文件改动汇总

| 文件 | 操作 | 改动量 | 说明 |
|------|------|--------|------|
| `lib/v4/data_collector.py` | **新建** | ~300 行 | 核心缺失组件：实际执行数据采集 |
| `lib/v4/thinking_chain.py` | 修改 | ~200 行 | 补 `plan_for_role` + 串联 `DataCollector` + 添加 `execute_full_chain` |
| `lib/v4/__init__.py` | 修改 | ~5 行 | 导出 `DataCollector` |
| `agents/workflow_orchestrator_v3_final.py` | 修改 | ~30 行 | 传入 `enhanced_context` |
| `config/bmad.json` | 修改 | ~20 行 | 添加数据采集源配置 |
| `tests/test_thinking_chain.py` | **新建** | ~200 行 | 测试新增功能 |

**总改动量**: ~750 行（其中 ~500 行新代码，~250 行修改）

---

## 风险评估

| 风险 | 概率 | 影响 | 缓解措施 |
|------|------|------|----------|
| 外部网站改版导致抓取失败 | 中 | 单源失败不影响整体 | 多源降级 + 缓存 |
| requests 超时拖慢分析 | 低 | 整体时间增加 | 30s 超时 + 异步可选 |
| LLM 规划的 query 质量差 | 中 | 采集到无关数据 | 人工审核 + 模板兜底 |
| 修改引入新 bug | 低 | 已有功能受影响 | 单元测试覆盖 |

---

## 实施优先级

```
P1 → P2 → P3 → P4 → P5 → P6
 ↓     ↓     ↓     ↓
必须   必须   必须   必须       P6 可后续补充
```

P1-P4 是核心链路，缺一不可。P5 和 P6 是改进，可后续迭代。

---

## 验证标准

完成后，运行以下验证:

1. `python tests/test_thinking_chain.py` — 单元测试通过
2. 手动验证: 用一个简单任务运行 `_step6_thinking_chain_execution`
3. 检查 `thinking_chain_log.json` 中 `collected_data` 字段非空
4. 检查角色报告中引用了实时数据（非编造数字）
