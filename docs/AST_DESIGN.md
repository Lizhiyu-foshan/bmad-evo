# AST 审计引擎设计文档

## 决策记录（2026-03-17 23:35）

### 用户确认的设计决策

1. **命名规范**: 统一使用 **camelCase** 作为前后端标准
   - 函数名：`auditCode`, `checkConstraints`
   - 变量名：`auditResult`, `violationList`
   - 类名：`PythonASTAnalyzer`, `ASTConstraintChecker`

2. **严格模式**: 默认启动 **严格模式**
   - AST + regex 双重检查
   - 审计分数 < 85 或存在 HIGH 级别违规时阻断流程
   - 不允许静默跳过关键检查

3. **TypeScript AST 配置验证**: 使用 `tsc --showConfig` 命令
   - 验证 tsconfig.json 配置
   - 检查 TypeScript AST 解析器配置
   - 确保严格模式启用

4. **框架支持**: 尽量多支持主流框架
   - Python: FastAPI, Flask, Django
   - JavaScript/TypeScript: Express, NestJS, Next.js
   - 框架特定的约束模板

5. **实现要求**: 直接完整实现，但必须做好测试和代码审计
   - 完整的单元测试覆盖率 > 90%
   - 集成测试验证端到端流程
   - AST 审计引擎自身的代码必须通过审计
   - 遵循"代码修复黄金法则"：先思考，后行动

## 实现计划

### Phase 1: 核心引擎（今晚完成）
- [ ] `lib/ast_auditor.py` - AST 核心审计引擎
- [ ] `lib/typescript_ast.py` - TypeScript AST 分析器
- [ ] 8 种预定义检查规则
- [ ] 支持 `# noqa` 豁免机制

### Phase 2: 约束模板（今晚完成）
- [ ] `templates/constraints/ast-cron-job.yaml` - 定时任务专用
- [ ] `templates/constraints/ast-api-service.yaml` - API 服务专用
- [ ] `templates/constraints/ast-fastapi.yaml` - FastAPI 专用
- [ ] `templates/constraints/ast-express.yaml` - Express 专用

### Phase 3: 集成与测试（今晚完成）
- [ ] 重构 `lib/constraint_checker.py` 支持三种模式
- [ ] 更新 `agents/constraint_auditor.py` 集成 AST
- [ ] 编写完整的单元测试
- [ ] 端到端集成测试
- [ ] 性能基准测试

### Phase 4: 自身审计（最后）
- [ ] 用 AST 引擎审计自己的代码
- [ ] 修复发现的所有问题
- [ ] 记录审计结果到 `docs/SELF_AUDIT_REPORT.md`

## 验收标准

1. **功能完整性**
   - [ ] 所有 8 种检查规则正常工作
   - [ ] 支持 Python 和 TypeScript
   - [ ] 支持至少 4 种框架模板
   - [ ] 严格模式默认启用

2. **性能要求**
   - [ ] Python 文件审计 < 2ms/文件
   - [ ] TypeScript 文件审计 < 5ms/文件
   - [ ] 100 文件批量审计 < 200ms

3. **质量要求**
   - [ ] 单元测试覆盖率 > 90%
   - [ ] 零误报（经过人工验证）
   - [ ] 自身代码通过审计

4. **文档完整性**
   - [ ] `docs/AST_AUDITOR.md` 使用文档
   - [ ] `docs/AST_RULES.md` 规则详细说明
   - [ ] `examples/` 目录下包含所有规则的示例

## 风险缓解

- **过度设计风险**: 先实现核心 8 规则，后续迭代扩展
- **性能风险**: 实现性能测试，确保满足阈值
- **误报风险**: 每条规则必须有人工验证的测试用例
- **破坏性风险**: 遵循代码修复黄金法则，小步验证

---

**创建时间**: 2026-03-17 23:35  
**决策者**: 郎瀚威  
**执行者**: Kimi Claw  
**状态**: 开发中
