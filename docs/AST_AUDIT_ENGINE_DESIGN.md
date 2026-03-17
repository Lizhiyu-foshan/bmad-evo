# AST 解析审计引擎设计文档

> **版本**: 1.0.0  
> **日期**: 2026-03-17  
> **状态**: 待评审  
> **工作量**: 2-3 天  
> **预期收益**: 误报率↓70%

---

## 📋 目录

1. [背景与问题](#背景与问题)
2. [设计目标](#设计目标)
3. [技术方案](#技术方案)
4. [架构设计](#架构设计)
5. [核心模块](#核心模块)
6. [约束定义格式](#约束定义格式)
7. [使用示例](#使用示例)
8. [实施计划](#实施计划)
9. [风险评估](#风险评估)

---

## 背景与问题

### 当前实现的问题

BMAD-EVO 当前的 `constraint_checker.py` 存在以下问题：

1. **基于正则表达式的浅层分析**
   ```python
   # 当前实现 - 简单字符串匹配
   if 'for ' in output and 'if ' not in output[:output.find('for ') + 100]:
       violations.append(...)  # 误报！
   ```

2. **误报率高**
   - 无法区分代码和注释
   - 无法理解作用域和上下文
   - 无法识别语义等价的实现

3. **难以扩展**
   - 每个新约束都需要编写复杂的正则
   - 难以处理多语言
   - 无法复用分析结果

### 真实案例

```python
# 这段代码会被误报"缺少空值检查"
def process_items(items):
    """处理项目列表"""
    # 使用了 for 循环，但前面 100 字符内没有 if
    for item in items:
        print(item)

# 当前检查器会报错，因为：
# - 检测到 'for ' 
# - 前 100 字符没有 'if '
# 但实际上函数有责任处理空列表，这是合理的
```

---

## 设计目标

### 核心目标

| 目标 | 当前 | 目标 | 改进 |
|------|------|------|------|
| 误报率 | ~40% | <12% | ↓70% |
| 漏报率 | ~25% | <10% | ↓60% |
| 检查速度 | ~50ms | ~150ms | -60% (可接受) |
| 可维护性 | 低 | 高 | 重构成本↓80% |

### 功能需求

1. **AST 解析**
   - 支持 Python 代码的完整 AST 解析
   - 提取函数、类、控制流等结构
   - 保留行号、列号等位置信息

2. **语义理解**
   - 识别函数参数和返回值
   - 追踪变量作用域
   - 理解控制流（if/for/try/with）

3. **约束检查**
   - 基于 AST 节点的精确匹配
   - 支持路径查询（类似 XPath）
   - 支持自定义规则

4. **可扩展性**
   - 插件化的检查器架构
   - 支持多语言（预留接口）
   - 可热加载新约束

---

## 技术方案

### 技术选型

#### 方案对比

| 方案 | 优点 | 缺点 | 选择 |
|------|------|------|------|
| Python `ast` 模块 | 内置、零依赖、完整 | 仅支持 Python | ✅ 首选 |
| Tree-sitter | 多语言、快速、增量 | 需安装依赖、学习曲线 | 备选 |
| Lib2to3 | 支持语法树转换 | 复杂度过高 | ❌ 不选 |
| RedBaron | 保留格式、可重写 | 性能较差 | ❌ 不选 |

### 核心技术栈

```
Python ast 模块 (内置)
    ↓
ast.NodeVisitor / ast.NodeTransformer
    ↓
自定义 AST 分析器
    ↓
约束规则引擎
```

### 为什么选择 Python ast？

1. **零依赖** - Python 内置，无需安装
2. **完整支持** - 覆盖 Python 所有语法特性
3. **成熟稳定** - 标准库，长期维护
4. **性能足够** - 单次解析 <100ms（1000 行代码）

---

## 架构设计

### 整体架构

```
┌─────────────────────────────────────────────────────────┐
│                    AST 审计引擎                          │
├─────────────────────────────────────────────────────────┤
│                                                         │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐ │
│  │  代码解析器  │  │  约束规则库  │  │  检查器插件  │ │
│  │   Parser     │  │    Rules     │  │   Checkers   │ │
│  └──────┬───────┘  └──────┬───────┘  └──────┬───────┘ │
│         │                 │                 │          │
│         └─────────────────┼─────────────────┘          │
│                           │                            │
│                  ┌────────▼────────┐                   │
│                  │   AST 遍历器    │                   │
│                  │    Visitor      │                   │
│                  └────────┬────────┘                   │
│                           │                            │
│         ┌─────────────────┼─────────────────┐          │
│         │                 │                 │          │
│  ┌──────▼───────┐  ┌──────▼───────┐  ┌──────▼───────┐ │
│  │ 违规检测器   │  │  证据收集器  │  │  修复建议器  │ │
│  │  Detector    │  │  Collector   │  │  Suggester   │ │
│  └──────┬───────┘  └──────┬───────┘  └──────┬───────┘ │
│         │                 │                 │          │
│         └─────────────────┼─────────────────┘          │
│                           │                            │
│                  ┌────────▼────────┐                   │
│                  │   审计报告生成  │                   │
│                  │     Report      │                   │
│                  └─────────────────┘                   │
│                                                         │
└─────────────────────────────────────────────────────────┘
```

### 数据流

```
源代码
  ↓
[1] ast.parse() → AST 树
  ↓
[2] ConstraintVisitor.visit() → 遍历节点
  ↓
[3] 检查器插件匹配规则 → Violation[]
  ↓
[4] 计算得分 → AuditResult
  ↓
[5] 生成报告 → Markdown / JSON
```

---

## 核心模块

### 1. AST 解析器 (ASTParser)

**职责**: 将源代码解析为 AST 树

```python
# lib/ast_parser.py

import ast
from typing import Optional, Dict, Any

class ASTParser:
    """AST 解析器"""
    
    def __init__(self, source_code: str, filename: str = "<code>"):
        self.source = source_code
        self.filename = filename
        self.tree: Optional[ast.AST] = None
        self.lines = source_code.splitlines()
    
    def parse(self) -> ast.AST:
        """解析源代码为 AST"""
        try:
            self.tree = ast.parse(self.source, filename=self.filename)
            return self.tree
        except SyntaxError as e:
            raise ASTParseError(f"语法错误：{e}", lineno=e.lineno, offset=e.offset)
    
    def get_node_at_line(self, lineno: int) -> Optional[ast.AST]:
        """获取指定行号的 AST 节点"""
        if not self.tree:
            return None
        
        for node in ast.walk(self.tree):
            if hasattr(node, 'lineno') and node.lineno == lineno:
                return node
        return None
    
    def get_source_segment(self, node: ast.AST) -> str:
        """获取节点对应的源代码片段"""
        if hasattr(node, 'lineno') and hasattr(node, 'end_lineno'):
            start = node.lineno - 1
            end = node.end_lineno
            return '\n'.join(self.lines[start:end])
        return ""


class ASTParseError(Exception):
    """AST 解析错误"""
    def __init__(self, message: str, lineno: int = None, offset: int = None):
        super().__init__(message)
        self.lineno = lineno
        self.offset = offset
```

### 2. AST 遍历器 (ConstraintVisitor)

**职责**: 遍历 AST 树，调用检查器插件

```python
# lib/constraint_visitor.py

import ast
from typing import List, Callable
from dataclasses import dataclass

@dataclass
class VisitorContext:
    """遍历上下文"""
    tree: ast.AST
    source: str
    lines: List[str]
    violations: List[Violation]
    
class ConstraintVisitor(ast.NodeVisitor):
    """AST 约束遍历器"""
    
    def __init__(self, checkers: List[Callable]):
        self.checkers = checkers
        self.context = None
    
    def visit(self, node: ast.AST, context: VisitorContext):
        """访问节点并运行检查器"""
        self.context = context
        
        # 运行所有检查器
        for checker in self.checkers:
            violations = checker(node, context)
            context.violations.extend(violations)
        
        # 继续遍历子节点
        self.generic_visit(node)
    
    def audit(self, tree: ast.AST, source: str) -> List[Violation]:
        """执行完整审计"""
        lines = source.splitlines()
        context = VisitorContext(
            tree=tree,
            source=source,
            lines=lines,
            violations=[]
        )
        
        self.visit(tree, context)
        return context.violations
```

### 3. 检查器插件 (Checker Plugins)

**职责**: 实现具体的约束检查逻辑

#### 示例 1: 边界检查器

```python
# checkers/boundary_checker.py

import ast
from typing import List

def check_boundary(node: ast.AST, context: VisitorContext) -> List[Violation]:
    """边界检查器"""
    violations = []
    
    # 检查函数定义
    if isinstance(node, ast.FunctionDef):
        violations.extend(_check_function_boundary(node, context))
    
    return violations

def _check_function_boundary(node: ast.FunctionDef, context: VisitorContext) -> List[Violation]:
    """检查函数的边界处理"""
    violations = []
    
    # 检查是否有参数但缺少 None 检查
    has_params = len(node.args.args) > 0
    has_none_check = False
    
    # 遍历函数体，查找 None 检查
    for stmt in ast.walk(node):
        if isinstance(stmt, ast.Compare):
            # 检查是否有 'x is None' 或 'x is not None'
            if any(isinstance(op, (ast.Is, ast.IsNot)) for op in stmt.ops):
                has_none_check = True
                break
    
    if has_params and not has_none_check:
        violations.append(Violation(
            constraint_type=ConstraintType.BOUNDARY_CHECK,
            severity=Severity.HIGH,
            description="函数缺少输入参数的空值检查",
            evidence=context.get_source_segment(node)[:100],
            suggestion="添加: if param is None: raise ValueError(...)",
            line_number=node.lineno
        ))
    
    return violations
```

#### 示例 2: 异常处理检查器

```python
# checkers/exception_checker.py

def check_exception_handling(node: ast.AST, context: VisitorContext) -> List[Violation]:
    """异常处理检查器"""
    violations = []
    
    # 检查 Try 节点
    if isinstance(node, ast.Try):
        violations.extend(_check_try_except(node, context))
    
    # 检查网络/IO 操作是否有 try 包裹
    if isinstance(node, ast.Call):
        violations.extend(_check_io_call(node, context))
    
    return violations

def _check_try_except(node: ast.Try, context: VisitorContext) -> List[Violation]:
    """检查 try-except 的规范性"""
    violations = []
    
    # 检查是否有裸 except
    for handler in node.handlers:
        if handler.type is None:
            violations.append(Violation(
                constraint_type=ConstraintType.EXCEPTION_HANDLING,
                severity=Severity.MEDIUM,
                description="使用了裸 except: 子句",
                evidence="except: 没有指定异常类型",
                suggestion="使用 except Exception: 或具体异常类型",
                line_number=handler.lineno
            ))
    
    return violations

def _check_io_call(node: ast.Call, context: VisitorContext) -> List[Violation]:
    """检查 IO 调用是否有异常处理"""
    violations = []
    
    # 检测网络请求
    if isinstance(node.func, ast.Attribute):
        if node.func.attr in ['get', 'post', 'put', 'delete']:
            # 检查是否在 try 块内（简化版，实际需要向上遍历父节点）
            if not _is_in_try_block(node, context):
                violations.append(Violation(
                    constraint_type=ConstraintType.EXCEPTION_HANDLING,
                    severity=Severity.HIGH,
                    description="网络请求缺少异常处理",
                    evidence=f"requests.{node.func.attr}()",
                    suggestion="添加 try-except 捕获 requests.Timeout 等异常",
                    line_number=node.lineno
                ))
    
    return violations

def _is_in_try_block(node: ast.AST, context: VisitorContext) -> bool:
    """检查节点是否在 try 块内（简化实现）"""
    # 实际需要维护父节点映射，这里简化
    return False
```

### 4. 违规检测器 (ViolationDetector)

**职责**: 收集、分类、去重违规项

```python
# lib/violation_detector.py

from typing import List, Dict
from collections import defaultdict

class ViolationDetector:
    """违规检测器"""
    
    def __init__(self):
        self.violations = []
        self.stats = defaultdict(int)
    
    def add(self, violation: Violation):
        """添加违规项"""
        self.violations.append(violation)
        self.stats[violation.constraint_type.value] += 1
        self.stats[f"{violation.severity.value}_count"] += 1
    
    def get_high_priority(self) -> List[Violation]:
        """获取高优先级违规"""
        return [v for v in self.violations if v.severity == Severity.HIGH]
    
    def get_must_fix_types(self) -> List[str]:
        """获取必须修复的约束类型"""
        high_types = set()
        for v in self.violations:
            if v.severity == Severity.HIGH:
                high_types.add(v.constraint_type.value)
        return list(high_types)
    
    def deduplicate(self) -> List[Violation]:
        """去重违规项"""
        seen = set()
        unique = []
        
        for v in self.violations:
            key = (v.constraint_type, v.description, v.line_number)
            if key not in seen:
                seen.add(key)
                unique.append(v)
        
        self.violations = unique
        return unique
```

### 5. 修复建议器 (FixSuggester)

**职责**: 为每个违规项生成修复建议

```python
# lib/fix_suggester.py

import ast
from typing import Optional

class FixSuggester:
    """修复建议生成器"""
    
    def suggest_fix(self, violation: Violation, context: VisitorContext) -> str:
        """生成修复建议"""
        
        if violation.constraint_type == ConstraintType.BOUNDARY_CHECK:
            return self._suggest_boundary_fix(violation, context)
        
        elif violation.constraint_type == ConstraintType.EXCEPTION_HANDLING:
            return self._suggest_exception_fix(violation, context)
        
        # ... 其他类型
        
        return violation.suggestion  # 默认使用检查器的建议
    
    def _suggest_boundary_fix(self, violation: Violation, context: VisitorContext) -> str:
        """生成边界检查修复建议"""
        # 可以生成具体的代码片段
        return """
建议修复：
```python
def process_data(data):
    if data is None:
        raise ValueError("data 不能为空")
    # 或者提供默认值
    # data = data or []
    
    # ... 原有逻辑
```
""".strip()
```

### 6. 审计报告生成器 (ReportGenerator)

**职责**: 生成 Markdown/JSON 报告

（复用现有的 `audit_report.py`，只需适配新的数据结构）

---

## 约束定义格式

### YAML 格式（增强版）

```yaml
# constraints.yaml

version: "2.0"  # 新增版本号

constraints:
  boundary_check:
    - id: "BC-001"  # 新增 ID
      name: "函数参数空值检查"
      description: "函数必须检查输入参数是否为空"
      severity: high
      enabled: true
      
      # AST 规则（新增）
      ast_rule:
        node_type: FunctionDef
        condition: |
          node.args.args and 
          not has_none_check(node)
      
      # 传统正则规则（向后兼容）
      regex_pattern: "def\\s+\\w+\\("  # 可选
      
      suggestion: |
        添加空值检查:
        if param is None:
            raise ValueError("param 不能为空")
  
  exception_handling:
    - id: "EH-001"
      name: "网络请求异常处理"
      description: "网络请求必须包裹在 try-except 中"
      severity: high
      enabled: true
      
      ast_rule:
        node_type: Call
        condition: |
          is_network_call(node) and 
          not in_try_block(node)
      
      suggestion: |
        添加异常处理:
        try:
            response = requests.get(url)
        except requests.Timeout as e:
            logger.error(f"请求超时：{e}")
```

### 规则条件语法

使用 Python 表达式作为条件：

```python
# 条件示例
node.args.args and not has_none_check(node)
is_network_call(node) and not in_try_block(node)
len(node.body) > 50  # 函数超过 50 行
```

内置辅助函数：
- `has_none_check(node)` - 检查是否有 None 检查
- `in_try_block(node)` - 检查是否在 try 块内
- `is_network_call(node)` - 检查是否是网络调用
- `is_io_operation(node)` - 检查是否是 IO 操作

---

## 使用示例

### 基本使用

```python
from lib.ast_audit_engine import ASTAuditEngine

# 初始化引擎
engine = ASTAuditEngine(constraints_path="constraints.yaml")

# 审计代码
code = """
def process_data(data):
    result = requests.get(data['url'])
    for item in result.json():
        print(item)
    return result
"""

result = engine.audit(code)

# 检查结果
if not result.passed:
    print(f"审计未通过，得分：{result.score}")
    for v in result.violations:
        print(f"- [{v.severity}] {v.description}")
        print(f"  行号：{v.line_number}")
        print(f"  建议：{v.suggestion}")
```

### CLI 使用

```bash
# 审计单个文件
bmad-evo audit-ast --file src/main.py

# 审计整个目录
bmad-evo audit-ast --dir src/ --recursive

# 生成 HTML 报告
bmad-evo audit-ast --file src/main.py --format html --output report.html

# 只检查特定约束类型
bmad-evo audit-ast --file src/main.py --types boundary_check,exception_handling
```

### 集成到现有流程

```python
# 在 constraint_auditor.py 中替换检查器

class ConstraintAuditor:
    def __init__(self, project_path: str):
        # ... 原有代码
        
        # 新增 AST 引擎
        from lib.ast_audit_engine import ASTAuditEngine
        self.ast_engine = ASTAuditEngine(constraints_path)
    
    def audit(self, output: str, phase: str, ...) -> AuditResult:
        # 使用 AST 引擎替代原有检查器
        result = self.ast_engine.audit(output)
        
        # ... 后续处理保持不变
```

---

## 实施计划

### 阶段划分

| 阶段 | 任务 | 工作量 | 产出 |
|------|------|--------|------|
| **Day 1 AM** | 核心解析器 | 4h | `ast_parser.py`<br>`constraint_visitor.py` |
| **Day 1 PM** | 检查器插件框架 | 4h | `checker_interface.py`<br>`boundary_checker.py` |
| **Day 2 AM** | 异常处理检查器 | 4h | `exception_checker.py`<br>`code_structure_checker.py` |
| **Day 2 PM** | 集成测试 | 4h | 测试用例<br>对比报告 |
| **Day 3** | 优化与文档 | 6h | 性能优化<br>使用文档 |

### 每日里程碑

#### Day 1: 核心功能
- [x] AST 解析器实现
- [x] 遍历器框架
- [x] 第一个检查器（边界检查）
- [ ] 单元测试覆盖

#### Day 2: 功能完善
- [ ] 异常处理检查器
- [ ] 代码结构检查器
- [ ] 集成到现有审计流程
- [ ] 对比测试（新旧引擎）

#### Day 3: 优化发布
- [ ] 性能优化（缓存、并行）
- [ ] 误报率对比报告
- [ ] 用户文档
- [ ] 版本发布

---

## 风险评估

### 技术风险

| 风险 | 概率 | 影响 | 缓解措施 |
|------|------|------|----------|
| AST 解析失败（语法错误） | 中 | 高 | 捕获异常，降级到正则检查 |
| 性能下降超过 200% | 低 | 中 | 缓存解析结果、并行处理 |
| 误报率未降低 70% | 中 | 高 | 保留旧引擎作为 fallback，逐步调优 |

### 实施风险

| 风险 | 概率 | 影响 | 缓解措施 |
|------|------|------|----------|
| 工作量估算不足 | 中 | 中 | 优先实现核心检查器，其他后续迭代 |
| 与现有流程不兼容 | 低 | 高 | 设计适配器，保持接口一致 |
| 学习曲线陡峭 | 中 | 低 | 编写详细文档和示例 |

### 回滚方案

如果 AST 引擎出现问题：

1. **立即回滚**: 设置环境变量 `BMAD_USE_AST=0` 切换回正则引擎
2. **渐进迁移**: 只对新约束使用 AST，旧约束保留正则
3. **混合模式**: 同时运行两个引擎，取并集（性能换质量）

---

## 成功标准

### 定量指标

- [ ] 误报率从 40% 降低到 <12%
- [ ] 漏报率从 25% 降低到 <10%
- [ ] 单次审计时间 <200ms（1000 行代码）
- [ ] 单元测试覆盖率 >80%

### 定性指标

- [ ] 代码可读性提升（团队反馈）
- [ ] 新约束开发效率提升（从 1 天到 2 小时）
- [ ] 用户满意度提升（问卷反馈）

---

## 附录

### A. AST 节点类型参考

常用节点类型：

```python
ast.FunctionDef      # 函数定义
ast.ClassDef         # 类定义
ast.Return           # return 语句
ast.If               # if 语句
ast.For              # for 循环
ast.While            # while 循环
ast.Try              # try-except
ast.With             # with 语句
ast.Call             # 函数调用
ast.Attribute        # 属性访问
ast.Name             # 变量名
ast.Compare          # 比较运算
ast.BoolOp           # 布尔运算 (and/or)
```

### B. 辅助工具

推荐工具：

- `ast.dump()` - 打印 AST 树结构
- `ast.walk()` - 遍历所有节点
- `ast.NodeVisitor` - 访问者模式
- `ast.NodeTransformer` - 转换 AST

### C. 测试用例模板

```python
def test_boundary_check_function_without_none_check():
    code = """
def process_data(data):
    return data['key']
"""
    result = engine.audit(code)
    
    assert not result.passed
    assert len(result.violations) == 1
    assert result.violations[0].constraint_type == ConstraintType.BOUNDARY_CHECK
    assert result.violations[0].severity == Severity.HIGH
```

---

**文档结束**

📝 **下一步行动**:
1. 用户评审本设计文档
2. 确认技术方案和约束定义格式
3. 开始实施（预计 2-3 天）
4. 对比测试并生成报告
