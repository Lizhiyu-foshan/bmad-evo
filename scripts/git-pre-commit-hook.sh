#!/bin/bash
# Git Pre-commit Hook for BMAD-EVO
# 自动在 commit 前检查代码质量
#
# 安装方式:
#   cp scripts/git-pre-commit-hook.sh .git/hooks/pre-commit
#   chmod +x .git/hooks/pre-commit
#
# 跳过检查:
#   git commit -m "msg" --no-verify

set -e

echo "🔍 BMAD-EVO 代码质量检查..."
echo ""

# 获取暂存区中的 Python 文件
FILES=$(git diff --cached --name-only --diff-filter=ACM | grep '\.py$' || true)

if [ -z "$FILES" ]; then
    echo "✅ 没有 Python 文件需要检查"
    exit 0
fi

# 获取脚本所在目录的父目录（BMAD-EVO 根目录）
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BMAD_ROOT="$(dirname "$SCRIPT_DIR")"

# 检查模式（可以通过环境变量配置）
AUDIT_MODE="${BMAD_AUDIT_MODE:-fast}"

echo "检查文件:"
for FILE in $FILES; do
    echo "  - $FILE"
done
echo ""
echo "审计模式：$AUDIT_MODE"
echo "-" * 80

# 审计每个文件
FAILED=0
for FILE in $FILES; do
    if [ -f "$FILE" ]; then
        echo ""
        echo "📄 检查：$FILE"
        
        if python3 "$BMAD_ROOT/quick_audit.py" --mode "$AUDIT_MODE" --exit-code "$FILE"; then
            echo "  ✅ 通过"
        else
            echo "  ❌ 失败"
            FAILED=1
        fi
    fi
done

echo ""
echo "=" * 80

if [ $FAILED -ne 0 ]; then
    echo ""
    echo "❌ 代码质量检查失败！请修复问题后重新 commit"
    echo ""
    echo "提示："
    echo "  - 使用 --no-verify 跳过检查（不推荐）"
    echo "  - 使用 BMAD_AUDIT_MODE=strict 进行更严格检查"
    echo "  - 在代码中添加 # noqa 注释跳过特定检查"
    echo ""
    exit 1
else
    echo ""
    echo "✅ 所有文件通过检查！"
    echo ""
    exit 0
fi
