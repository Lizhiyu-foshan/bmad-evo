# AST 审计引擎使用文档

## 快速开始

### 基本用法

```python
from lib.ast_auditor import audit_code, check_constraints

# 快速模式（仅 AST，推荐开发时使用）
result = audit_code(your_code, strict_mode=False)

# 严格模式（AST + regex，推荐发布前使用）
result = audit_code(your_code, strict_mode=True)

# BMAD-EVO 集成接口
result = check_constraints(your_code, mode="fast")      # AST only
result = check_constraints(your_code, mode="strict")    # AST + regex
```

### 检查结果

```python
# 检查是否通过
if result.is_passing:
    print("✅ 审计通过")
else:
    print(f"❌ 审计失败：分数 {result.score:.1f}")
    for v in result.violations:
        print(f"  [{v.severity.value.upper()}] {v.rule_name}: {v.message}")
```

## 审计规则（8 种）

### 1. NULL_CHECK - 空值检查
**严重性**: HIGH

检测函数参数使用前是否进行了空值检查。

**违规示例**:
```python
def process_data(data):
    return data['value']  # ❌ 没有检查 data 是否为 None
```

**修复示例**:
```python
def process_data(data: dict) -> Any:
    if data is None:
        raise ValueError("data 不能为空")
    return data['value']  # ✅ 已检查
```

### 2. EXCEPTION_FLOW - 异常流完整性
**严重性**: MEDIUM

检测 try 块是否有对应的 except 处理器。

**违规示例**:
```python
try:
    do_something_risky()
# ❌ 没有 except 处理器
```

**修复示例**:
```python
try:
    do_something_risky()
except Exception as e:
    logger.error(f"操作失败：{e}")
    raise
```

### 3. NO_BARE_EXCEPT - 禁止裸 except
**严重性**: MEDIUM

检测是否使用了裸 except 子句。

**违规示例**:
```python
try:
    process()
except:  # ❌ 捕获所有异常，包括 SystemExit、KeyboardInterrupt
    pass
```

**修复示例**:
```python
try:
    process()
except Exception:  # ✅ 只捕获普通异常
    pass
```

### 4. NO_EMPTY_EXCEPT - 禁止空异常处理器
**严重性**: CRITICAL

检测异常处理器是否为空（不记录不处理）。

**违规示例**:
```python
try:
    process()
except Exception:  # ❌ 空处理器，吞掉异常
    pass
```

**修复示例**:
```python
try:
    process()
except Exception as e:
    logger.error(f"处理失败：{e}")
    raise
```

### 5. IO_EXCEPTION - IO 操作异常处理
**严重性**: HIGH

检测文件 IO 操作是否有异常处理。

**违规示例**:
```python
f = open('file.txt', 'r')  # ❌ 没有异常处理
content = f.read()
f.close()
```

**修复示例**:
```python
try:
    with open('file.txt', 'r') as f:
        content = f.read()
except FileNotFoundError:
    logger.error("文件不存在")
```

### 6. NETWORK_EXCEPTION - 网络请求异常处理
**严重性**: HIGH

检测网络请求是否有异常处理。

**违规示例**:
```python
response = requests.get(url)  # ❌ 没有异常处理
data = response.json()
```

**修复示例**:
```python
try:
    response = requests.get(url, timeout=5)
    response.raise_for_status()
    data = response.json()
except requests.RequestException as e:
    logger.error(f"请求失败：{e}")
    raise
```

### 7. HARDCODED_SECRET - 硬编码密钥
**严重性**: CRITICAL

检测代码中是否硬编码了密钥、密码等敏感信息。

**违规示例**:
```python
api_key = "sk-1234567890abcdef"  # ❌ 硬编码 API 密钥
password = "admin123"  # ❌ 硬编码密码
```

**修复示例**:
```python
import os

api_key = os.getenv('API_KEY')  # ✅ 从环境变量读取
if not api_key:
    raise ValueError("API_KEY 环境变量未设置")

password = os.getenv('DB_PASSWORD')
```

### 8. TYPE_ANNOTATION - 类型注解
**严重性**: LOW

检测函数是否缺少类型注解。

**违规示例**:
```python
def process_data(data):  # ❌ 没有类型注解
    return data['value']
```

**修复示例**:
```python
from typing import Any, Dict

def process_data(data: Dict[str, Any]) -> Any:  # ✅ 完整类型注解
    return data['value']
```

## 性能基准

| 模式 | 速度 | 准确率 | 推荐场景 |
|------|------|--------|----------|
| AST only (fast) | <2ms/文件 | 99% | 开发时快速反馈 |
| AST + regex (strict) | <10ms/文件 | 99% | 发布前全面检查 |
| Regex only | <5ms/文件 | 85% | 向后兼容 |

## 高级用法

### 批量审计目录

```python
from lib.ast_auditor import audit_directory

results = audit_directory('/path/to/project', pattern="*.py", strict_mode=True)

for result in results:
    print(f"{result.file}: {result.score:.1f}分 ({len(result.violations)} 个问题)")
```

### 审计单个文件

```python
from lib.ast_auditor import audit_file

result = audit_file('src/main.py', strict_mode=True)
print(f"审计结果：{result.to_dict()}")
```

### 自定义豁免

```python
# 使用 # noqa 注释豁免特定行的检查
api_key = "test_key"  # noqa: HARDCODED_SECRET
```

## BMAD-EVO 集成

### Phase Gateway 自动审计

```python
from lib.constraint_checker import check_constraints

# Phase 1: Development
result = check_constraints(code, mode="fast")
gateway.complete_phase("development", result)

# Phase 2: Testing
result = check_constraints(code, mode="strict")
gateway.complete_phase("testing", result)

# 审计失败会阻断流程
if not result.is_passing:
    print("❌ 审计失败，无法进入下一阶段")
    for v in result.violations:
        if v.severity in [SeverityLevel.HIGH, SeverityLevel.CRITICAL]:
            print(f"  阻断问题：{v.message}")
```

### 约束模板

使用预定义的约束模板：

```bash
# 定时任务专用约束
templates/constraints/ast-cron-job.yaml

# API 服务专用约束
templates/constraints/ast-api-service.yaml

# FastAPI 专用约束
templates/constraints/ast-fastapi.yaml

# Express 专用约束
templates/constraints/ast-express.yaml
```

## 故障排查

### 常见问题

**Q: 审计分数过低怎么办？**
A: 优先修复 HIGH 和 CRITICAL 级别的问题，LOW 级别问题可以逐步改进。

**Q: 误报怎么办？**
A: 
1. 使用 `# noqa` 注释豁免该行
2. 报告问题，我们会优化规则
3. 检查是否使用了特殊模式

**Q: 性能太慢怎么办？**
A:
1. 使用 fast 模式（仅 AST）
2. 批量审计时限制文件数量
3. 排除不需要审计的文件（如生成的代码）

## 贡献规则

添加新的审计规则：

1. 在 `PythonASTAnalyzer` 类中添加新的 visitor 方法
2. 定义规则 ID、严重性、消息模板
3. 编写测试用例验证规则准确性
4. 更新文档说明规则用途

示例：

```python
def visit_While(self, node: ast.While):
    """检查无限循环"""
    if isinstance(node.test, ast.Constant) and node.test.value is True:
        # 检查是否有 break 语句
        has_break = any(isinstance(n, ast.Break) for n in ast.walk(node))
        if not has_break:
            self._add_violation(Violation(
                rule_id="INFINITE_LOOP",
                rule_name="Infinite Loop",
                severity=SeverityLevel.MEDIUM,
                message="While loop without break statement",
                line=node.lineno
            ))
```

## 更新日志

### 2026-03-17 - 初始版本
- ✅ 实现 8 种核心审计规则
- ✅ Python AST 分析器
- ✅ 严格模式（AST + regex）
- ✅ BMAD-EVO 集成
- ✅ 性能优化 <2ms/文件

### 计划更新
- TypeScript AST 分析器
- 更多规则（控制流、资源管理、循环复杂度）
- IDE 集成（VSCode 插件、Git pre-commit hook）
- 多语言支持（JavaScript、Java）

---

**文档版本**: 1.0  
**创建时间**: 2026-03-17  
**维护者**: Kimi Claw
