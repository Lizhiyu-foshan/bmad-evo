"""
BMAD-EVO v3.0 - ResilientExecutor
弹性执行器

功能:
- 带失败回退的执行
- 主模型失败 → 备选模型 → k2.5终极回退
- 记录执行日志
"""

import json
import logging
import subprocess
import tempfile
import time
from dataclasses import dataclass, asdict, field
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Any, Callable

logger = logging.getLogger(__name__)


@dataclass
class ExecutionLog:
    """执行日志条目"""
    timestamp: str
    role_id: str
    model: str
    attempt: int
    success: bool
    execution_time: float
    error: Optional[str] = None
    output_preview: str = ""


@dataclass
class ExecutionResult:
    """执行结果"""
    role_id: str
    success: bool
    output: str
    final_model: str
    total_attempts: int
    execution_logs: List[ExecutionLog]
    total_execution_time: float
    error: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "role_id": self.role_id,
            "success": self.success,
            "output": self.output,
            "final_model": self.final_model,
            "total_attempts": self.total_attempts,
            "execution_logs": [asdict(log) for log in self.execution_logs],
            "total_execution_time": self.total_execution_time,
            "error": self.error
        }


class ResilientExecutor:
    """
    弹性执行器
    提供多层失败回退机制
    """
    
    # 终极回退模型
    ULTIMATE_FALLBACK = "kimi-coding/k2p5"
    
    def __init__(
        self,
        project_path: Optional[str] = None,
        max_retries: int = 3,
        timeout: int = 300,
        enable_logging: bool = True
    ):
        self.project_path = Path(project_path) if project_path else Path.cwd()
        self.max_retries = max_retries
        self.timeout = timeout
        self.enable_logging = enable_logging
        
        # 日志存储
        self.logs: List[ExecutionLog] = []
        self.logs_dir = self.project_path / ".bmad" / "execution_logs"
        if self.enable_logging:
            self.logs_dir.mkdir(parents=True, exist_ok=True)
        
        logger.info(f"ResilientExecutor initialized (max_retries={max_retries}, timeout={timeout})")
    
    def execute(
        self,
        role_id: str,
        role_name: str,
        role_description: str,
        system_prompt: str,
        task_context: str,
        model_chain: List[str],
        context_from_previous: Optional[str] = None
    ) -> ExecutionResult:
        """
        弹性执行任务
        
        Args:
            role_id: 角色ID
            role_name: 角色名称
            role_description: 角色描述
            system_prompt: 系统提示词
            task_context: 任务上下文
            model_chain: 模型回退链 [主模型, 备选1, 备选2, ...]
            context_from_previous: 前一阶段的输出
            
        Returns:
            ExecutionResult: 执行结果
        """
        start_time = time.time()
        logs = []
        
        # 确保有终极回退
        if self.ULTIMATE_FALLBACK not in model_chain:
            model_chain = model_chain + [self.ULTIMATE_FALLBACK]
        
        logger.info(f"Executing role '{role_id}' with {len(model_chain)} models in chain")
        
        # 构建完整提示词
        prompt = self._build_execution_prompt(
            role_name, role_description, system_prompt,
            task_context, context_from_previous
        )
        
        # 尝试每个模型
        for attempt, model in enumerate(model_chain, 1):
            attempt_start = time.time()
            
            try:
                logger.info(f"Attempt {attempt}/{len(model_chain)}: using {model}")
                
                output = self._call_model(model, prompt)
                execution_time = time.time() - attempt_start
                
                # 记录成功日志
                log = ExecutionLog(
                    timestamp=datetime.now().isoformat(),
                    role_id=role_id,
                    model=model,
                    attempt=attempt,
                    success=True,
                    execution_time=execution_time,
                    output_preview=output[:200] + "..." if len(output) > 200 else output
                )
                logs.append(log)
                self._save_log(log)
                
                total_time = time.time() - start_time
                
                logger.info(f"Role '{role_id}' executed successfully with {model} "
                           f"(attempt {attempt}, time={total_time:.2f}s)")
                
                return ExecutionResult(
                    role_id=role_id,
                    success=True,
                    output=output,
                    final_model=model,
                    total_attempts=attempt,
                    execution_logs=logs,
                    total_execution_time=total_time
                )
                
            except Exception as e:
                execution_time = time.time() - attempt_start
                error_msg = str(e)
                
                logger.warning(f"Attempt {attempt} failed: {error_msg}")
                
                # 记录失败日志
                log = ExecutionLog(
                    timestamp=datetime.now().isoformat(),
                    role_id=role_id,
                    model=model,
                    attempt=attempt,
                    success=False,
                    execution_time=execution_time,
                    error=error_msg
                )
                logs.append(log)
                self._save_log(log)
                
                # 如果不是最后一个模型，继续尝试
                if attempt < len(model_chain):
                    logger.info(f"Falling back to next model: {model_chain[attempt]}")
                    continue
                else:
                    # 所有模型都失败了
                    total_time = time.time() - start_time
                    
                    logger.error(f"All models failed for role '{role_id}'")
                    
                    # 生成失败回退输出
                    fallback_output = self._generate_fallback_output(
                        role_id, role_name, task_context, error_msg
                    )
                    
                    return ExecutionResult(
                        role_id=role_id,
                        success=False,
                        output=fallback_output,
                        final_model="fallback",
                        total_attempts=attempt,
                        execution_logs=logs,
                        total_execution_time=total_time,
                        error=f"All models failed. Last error: {error_msg}"
                    )
        
        # 不应该到达这里
        total_time = time.time() - start_time
        return ExecutionResult(
            role_id=role_id,
            success=False,
            output="",
            final_model="none",
            total_attempts=len(model_chain),
            execution_logs=logs,
            total_execution_time=total_time,
            error="Unexpected execution path"
        )
    
    def _build_execution_prompt(
        self,
        role_name: str,
        role_description: str,
        system_prompt: str,
        task_context: str,
        context_from_previous: Optional[str]
    ) -> str:
        """构建执行提示词"""
        parts = [
            f"# {role_name}",
            f"\n{role_description}",
            f"\n## 系统指令\n{system_prompt}",
            f"\n## 任务上下文\n{task_context}"
        ]
        
        if context_from_previous:
            parts.append(f"\n## 前置阶段输出\n{context_from_previous}")
        
        parts.append("\n## 你的任务\n请基于以上信息，完成你的职责并输出结果。")
        
        return "\n".join(parts)
    
    def _call_model(self, model: str, prompt: str) -> str:
        """调用模型"""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as f:
            f.write(prompt)
            prompt_file = f.name
        
        try:
            cmd = [
                "openclaw", "sessions", "spawn",
                "--model", model,
                "--task-file", prompt_file,
                "--timeout", str(self.timeout),
                "--cleanup", "keep"
            ]
            
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=self.timeout + 30
            )
            
            if result.returncode != 0:
                raise RuntimeError(f"Model call failed: {result.stderr}")
            
            return result.stdout
            
        finally:
            try:
                Path(prompt_file).unlink(missing_ok=True)
            except:
                pass
    
    def _generate_fallback_output(
        self,
        role_id: str,
        role_name: str,
        task_context: str,
        error: str
    ) -> str:
        """生成回退输出（当所有模型都失败时）"""
        return f"""# {role_name} - 执行失败回退输出

## 状态
⚠️ **执行失败** - 所有模型调用均失败

## 错误信息
```
{error}
```

## 任务上下文
{task_context}

## 建议操作
1. 检查网络连接和 API 可用性
2. 稍后重试任务
3. 手动完成此角色的职责

## 回退输出
此为自动生成的回退输出，表明该阶段未能成功完成。
角色: {role_id}
时间: {datetime.now().isoformat()}
"""
    
    def _save_log(self, log: ExecutionLog):
        """保存日志"""
        if not self.enable_logging:
            return
        
        # 添加到内存
        self.logs.append(log)
        
        # 保存到文件
        log_file = self.logs_dir / f"{log.role_id}_{log.timestamp[:10]}.jsonl"
        
        with open(log_file, 'a', encoding='utf-8') as f:
            f.write(json.dumps(asdict(log), ensure_ascii=False) + "\n")
    
    def get_execution_history(
        self,
        role_id: Optional[str] = None,
        limit: int = 100
    ) -> List[ExecutionLog]:
        """获取执行历史"""
        logs = self.logs
        
        if role_id:
            logs = [log for log in logs if log.role_id == role_id]
        
        return logs[-limit:]
    
    def get_execution_stats(self) -> Dict[str, Any]:
        """获取执行统计"""
        if not self.logs:
            return {
                "total_executions": 0,
                "success_rate": 0.0,
                "avg_execution_time": 0.0
            }
        
        total = len(self.logs)
        successful = sum(1 for log in self.logs if log.success)
        avg_time = sum(log.execution_time for log in self.logs) / total
        
        # 按模型统计
        model_stats = {}
        for log in self.logs:
            if log.model not in model_stats:
                model_stats[log.model] = {"total": 0, "success": 0}
            model_stats[log.model]["total"] += 1
            if log.success:
                model_stats[log.model]["success"] += 1
        
        return {
            "total_executions": total,
            "successful": successful,
            "failed": total - successful,
            "success_rate": successful / total if total > 0 else 0.0,
            "avg_execution_time": avg_time,
            "model_stats": model_stats
        }
    
    def export_logs(self, output_file: Optional[str] = None) -> str:
        """导出日志"""
        if output_file is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            output_file = str(self.logs_dir / f"execution_logs_{timestamp}.json")
        
        data = {
            "exported_at": datetime.now().isoformat(),
            "total_logs": len(self.logs),
            "logs": [asdict(log) for log in self.logs]
        }
        
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        
        return output_file


class WorkflowExecutor:
    """
    工作流执行器
    协调多个角色的顺序/并行执行
    """
    
    def __init__(
        self,
        project_path: str,
        max_retries: int = 3,
        timeout: int = 300
    ):
        self.project_path = Path(project_path)
        self.executor = ResilientExecutor(
            project_path=project_path,
            max_retries=max_retries,
            timeout=timeout
        )
        
        # 角色输出缓存
        self.role_outputs: Dict[str, str] = {}
        
        logger.info("WorkflowExecutor initialized")
    
    def execute_workflow(
        self,
        roles: List[Dict[str, Any]],
        model_routing: Dict[str, List[str]],
        task_context: str,
        parallel_groups: Optional[List[List[str]]] = None
    ) -> Dict[str, ExecutionResult]:
        """
        执行工作流
        
        Args:
            roles: 角色列表
            model_routing: 模型路由 {role_id: [model_chain]}
            task_context: 任务上下文
            parallel_groups: 可并行执行的组
            
        Returns:
            执行结果 {role_id: ExecutionResult}
        """
        results = {}
        
        if parallel_groups:
            # 按组执行
            for group in parallel_groups:
                # 这里简化处理，实际应该用多线程/多进程并行
                for role_id in group:
                    role = self._find_role(roles, role_id)
                    if role:
                        result = self._execute_role(role, model_routing, task_context)
                        results[role_id] = result
                        if result.success:
                            self.role_outputs[role_id] = result.output
        else:
            # 顺序执行
            for role in roles:
                role_id = role.get("id")
                result = self._execute_role(role, model_routing, task_context)
                results[role_id] = result
                if result.success:
                    self.role_outputs[role_id] = result.output
        
        return results
    
    def _find_role(self, roles: List[Dict[str, Any]], role_id: str) -> Optional[Dict[str, Any]]:
        """查找角色"""
        for role in roles:
            if role.get("id") == role_id:
                return role
        return None
    
    def _execute_role(
        self,
        role: Dict[str, Any],
        model_routing: Dict[str, List[str]],
        task_context: str
    ) -> ExecutionResult:
        """执行单个角色"""
        role_id = role.get("id")
        role_name = role.get("name")
        role_description = role.get("description", "")
        responsibilities = role.get("responsibilities", [])
        
        # 构建系统提示词
        system_prompt = self._build_role_system_prompt(role)
        
        # 获取模型链
        model_chain = model_routing.get(role_id, ["kimi-coding/k2p5"])
        
        # 获取前置阶段输出
        context_from_previous = self._build_context_from_previous(role)
        
        # 执行
        return self.executor.execute(
            role_id=role_id,
            role_name=role_name,
            role_description=role_description,
            system_prompt=system_prompt,
            task_context=task_context,
            model_chain=model_chain,
            context_from_previous=context_from_previous
        )
    
    def _build_role_system_prompt(self, role: Dict[str, Any]) -> str:
        """构建角色系统提示词"""
        responsibilities = role.get("responsibilities", [])
        required_skills = role.get("required_skills", [])
        
        parts = [
            f"你是 {role.get('name', 'AI助手')}。",
            "\n## 职责",
        ]
        
        for resp in responsibilities:
            parts.append(f"- {resp}")
        
        if required_skills:
            parts.append("\n## 所需技能")
            for skill in required_skills:
                parts.append(f"- {skill}")
        
        parts.append("\n## 输出要求")
        parts.append("- 使用 Markdown 格式")
        parts.append("- 提供清晰、结构化的输出")
        parts.append("- 确保输出可以直接被下一阶段使用")
        
        return "\n".join(parts)
    
    def _build_context_from_previous(self, role: Dict[str, Any]) -> Optional[str]:
        """构建前置阶段上下文"""
        input_from = role.get("input_from", [])
        
        if not input_from or input_from == ["user"]:
            return None
        
        contexts = []
        for source in input_from:
            if source == "user":
                continue
            if source in self.role_outputs:
                contexts.append(f"## {source} 输出\n{self.role_outputs[source]}\n")
        
        return "\n---\n".join(contexts) if contexts else None
    
    def get_workflow_summary(self) -> Dict[str, Any]:
        """获取工作流执行摘要"""
        return self.executor.get_execution_stats()


# 便捷函数
def execute_with_fallback(
    role_id: str,
    role_name: str,
    system_prompt: str,
    task_context: str,
    model_chain: List[str],
    project_path: Optional[str] = None,
    timeout: int = 300
) -> ExecutionResult:
    """便捷函数：弹性执行"""
    executor = ResilientExecutor(project_path=project_path, timeout=timeout)
    return executor.execute(
        role_id=role_id,
        role_name=role_name,
        role_description="",
        system_prompt=system_prompt,
        task_context=task_context,
        model_chain=model_chain
    )


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Resilient Executor")
    parser.add_argument("--role-id", required=True, help="Role ID")
    parser.add_argument("--role-name", required=True, help="Role name")
    parser.add_argument("--system-prompt", required=True, help="System prompt")
    parser.add_argument("--task-context", required=True, help="Task context")
    parser.add_argument("--models", required=True, help="Model chain (comma-separated)")
    parser.add_argument("--project", default=".", help="Project path")
    
    args = parser.parse_args()
    
    logging.basicConfig(level=logging.INFO)
    
    model_chain = [m.strip() for m in args.models.split(",")]
    
    result = execute_with_fallback(
        role_id=args.role_id,
        role_name=args.role_name,
        system_prompt=args.system_prompt,
        task_context=args.task_context,
        model_chain=model_chain,
        project_path=args.project
    )
    
    print(json.dumps(result.to_dict(), indent=2, ensure_ascii=False))
