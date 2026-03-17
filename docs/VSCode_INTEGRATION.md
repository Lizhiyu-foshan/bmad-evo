# BMAD-EVO VSCode 集成指南

## 🎯 目标

在 VSCode 中实现实时的代码质量检查，开发过程中即时反馈。

## 📦 方式 1: 使用 Python 扩展 + 自定义 Linter

### 安装依赖

确保已安装 Python 扩展（ms-python.python）

### 配置 settings.json

在项目根目录创建 `.vscode/settings.json`:

```json
{
  "python.linting.enabled": true,
  "python.linting.lintOnSave": true,
  "python.linting.lintOnType": false,
  
  // 使用 BMAD-EVO 作为自定义 linter
  "python.linting.enabled": true,
  "python.linting.pylintEnabled": false,
  "python.linting.flake8Enabled": false,
  
  // 自定义 BMAD-EVO 检查
  "python.linting.lintArgs": [
    "--max-line-length=100"
  ]
}
```

### 创建任务（Tasks）

创建 `.vscode/tasks.json`:

```json
{
  "version": "2.0.0",
  "tasks": [
    {
      "label": "BMAD-EVO: 快速审计",
      "type": "shell",
      "command": "python3",
      "args": [
        "${workspaceFolder}/quick_audit.py",
        "--mode",
        "fast",
        "${file}"
      ],
      "group": {
        "kind": "build",
        "isDefault": true
      },
      "problemMatcher": {
        "owner": "python",
        "fileLocation": ["relative", "${workspaceFolder}"],
        "pattern": {
          "regexp": "^行 (\\d+):",
          "line": 1
        }
      },
      "presentation": {
        "reveal": "always",
        "panel": "new"
      }
    },
    {
      "label": "BMAD-EVO: 严格审计",
      "type": "shell",
      "command": "python3",
      "args": [
        "${workspaceFolder}/quick_audit.py",
        "--mode",
        "strict",
        "${file}"
      ],
      "group": "build",
      "presentation": {
        "reveal": "always",
        "panel": "new"
      }
    }
  ]
}
```

### 快捷键绑定

创建 `.vscode/keybindings.json`:

```json
[
  {
    "key": "ctrl+shift+b",
    "command": "workbench.action.tasks.runTask",
    "args": "BMAD-EVO: 快速审计"
  },
  {
    "key": "ctrl+shift+alt+b",
    "command": "workbench.action.tasks.runTask",
    "args": "BMAD-EVO: 严格审计"
  }
]
```

## 📦 方式 2: 使用 Code Runner 扩展

### 安装 Code Runner

扩展 ID: `formulahendry.code-runner`

### 配置 settings.json

```json
{
  "code-runner.executorMap": {
    "python": "cd $dir && python3 $workspaceFolder/quick_audit.py --mode fast $fileName"
  },
  "code-runner.runInTerminal": true,
  "code-runner.saveFileBeforeRun": true,
  "code-runner.preserveFocus": false,
  "code-runner.clearPreviousOutput": true
}
```

### 使用方式

1. 打开 Python 文件
2. 按 `Ctrl+Alt+N` 运行审计
3. 在输出面板查看结果

## 📦 方式 3: 使用 Terminal 手动运行

最简单的方式，直接在集成终端运行：

```bash
# 快速模式
python3 quick_audit.py your_file.py

# 严格模式
python3 quick_audit.py --mode strict your_file.py

# 从管道读取
cat your_file.py | python3 quick_audit.py --stdin
```

## 📦 方式 4: 创建 VSCode 扩展（进阶）

如果要深度集成，可以创建专用的 VSCode 扩展。

### 扩展结构

```
bmad-evo-vscode/
├── package.json
├── src/
│   ├── extension.ts
│   └── auditor.ts
└── vsc-extension-quickstart.md
```

### package.json 关键配置

```json
{
  "name": "bmad-evo-auditor",
  "displayName": "BMAD-EVO Auditor",
  "description": "AST-powered code quality checker for BMAD-EVO",
  "version": "0.0.1",
  "engines": {
    "vscode": "^1.85.0"
  },
  "activationEvents": [
    "onLanguage:python"
  ],
  "main": "./out/extension.js",
  "contributes": {
    "commands": [
      {
        "command": "bmadevo.audit",
        "title": "BMAD-EVO: Audit Current File"
      }
    ],
    "configuration": {
      "title": "BMAD-EVO Auditor",
      "properties": {
        "bmadevo.auditMode": {
          "type": "string",
          "default": "fast",
          "enum": ["fast", "strict", "regex_only"],
          "description": "审计模式"
        }
      }
    }
  },
  "scripts": {
    "vscode:prepublish": "npm run compile",
    "compile": "tsc -p ./",
    "watch": "tsc -watch -p ./"
  }
}
```

### extension.ts 示例代码

```typescript
import * as vscode from 'vscode';
import { exec } from 'child_process';
import { join } from 'path';

export function activate(context: vscode.ExtensionContext) {
    let disposable = vscode.commands.registerCommand(
        'bmadevo.audit',
        async () => {
            const editor = vscode.window.activeTextEditor;
            if (!editor) {
                return;
            }

            const document = editor.document;
            const config = vscode.workspace.getConfiguration('bmadevo');
            const mode = config.get('auditMode', 'fast');

            const outputChannel = vscode.window.createOutputChannel('BMAD-EVO Audit');
            outputChannel.show();

            const projectRoot = vscode.workspace.workspaceFolders?.[0].uri.fsPath;
            const auditScript = join(projectRoot, 'quick_audit.py');

            const command = `python3 ${auditScript} --mode ${mode} ${document.fileName}`;

            outputChannel.appendLine(`🔍 审计文件：${document.fileName}`);
            outputChannel.appendLine(`模式：${mode}`);
            outputChannel.appendLine('-'.repeat(80));

            exec(command, (error, stdout, stderr) => {
                outputChannel.append(stdout);
                if (stderr) {
                    outputChannel.append(stderr);
                }
                if (error) {
                    vscode.window.showErrorMessage(`审计失败：${error.message}`);
                } else {
                    vscode.window.showInformationMessage('审计完成！查看输出面板获取详情');
                }
            });
        }
    );

    context.subscriptions.push(disposable);
}
```

## 🎯 推荐工作流

### 日常开发
1. 保存文件时自动运行快速审计
2. 使用快捷键 `Ctrl+Shift+B` 手动触发
3. 在问题面板查看错误

### Commit 前
1. 运行严格审计
2. 修复所有 HIGH 和 CRITICAL 问题
3. Git pre-commit hook 自动检查

### CI/CD
1. 在 GitHub Actions 中集成审计
2. 审计失败时阻断合并

## 🔧 Git Pre-commit Hook 集成

项目已提供预配置的 hook：

```bash
# 安装 hook
cd your-project
cp /root/.openclaw/skills/bmad-evo/scripts/git-pre-commit-hook.sh .git/hooks/pre-commit
chmod +x .git/hooks/pre-commit

# 配置审计模式（可选）
export BMAD_AUDIT_MODE=strict
```

Hook 会自动：
- 检查所有暂存的 Python 文件
- 使用快速模式审计（默认）
- 失败时阻断 commit

## 📊 性能参考

| 模式 | 单文件 | 100 文件项目 |
|------|--------|--------------|
| Fast (AST) | <50ms | <5s |
| Strict (AST+regex) | <100ms | <10s |
| Regex only | <30ms | <3s |

## ⚠️ 注意事项

1. **首次运行**：首次运行会编译 Python 文件，可能稍慢
2. **虚拟环境**：确保在正确的项目环境中运行
3. **依赖**：需要安装 `pyyaml`（用于加载约束模板）

## 📚 参考资料

- [BMAD-EVO AST 审计引擎文档](docs/AST_AUDITOR.md)
- [快速审计工具](quick_audit.py)
- [Phase Gateway](agents/phase_gateway.py)

---

**让代码质量检查成为开发流程的自然部分！** 🚀
