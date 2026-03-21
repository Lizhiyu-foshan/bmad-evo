"""
BMAD-EVO v3.0 - TaskAnalyzer
智能任务分析器

功能:
- 调用 alibaba/qwen3.5-plus 分析任务类型
- 评估复杂度 (1-10分)
- 推荐角色数量
- 识别关键技能需求
- 失败回退到 kimi-coding/k2p5
"""

import json
import logging
import subprocess
import tempfile
import time
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Dict, List, Optional, Any

logger = logging.getLogger(__name__)


@dataclass
class TaskAnalysis:
    """任务分析结果"""
    task_description: str
    task_type: str
    complexity_score: int  # 1-10
    recommended_roles_count: int
    key_skills: List[str]
    estimated_duration: str
    risk_factors: List[str]
    success_criteria: List[str]
    model_used: str = ""
    execution_time: float = 0.0
    error: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


class TaskAnalyzer:
    """
    智能任务分析器
    完全由模型驱动，零硬编码规则
    """
    
    # 主模型和回退模型
    PRIMARY_MODEL = "alibaba/qwen3.5-plus"
    FALLBACK_MODEL = "kimi-coding/k2p5"
    
    def __init__(self, timeout: int = 120):
        self.timeout = timeout
        logger.info(f"TaskAnalyzer initialized (primary: {self.PRIMARY_MODEL})")
    
    def analyze(self, task_description: str) -> TaskAnalysis:
        """
        分析任务
        
        Args:
            task_description: 任务描述
            
        Returns:
            TaskAnalysis: 分析结果
        """
        logger.info(f"Analyzing task: {task_description[:100]}...")
        
        # 构建分析提示词
        prompt = self._build_analysis_prompt(task_description)
        
        # 尝试主模型
        start_time = time.time()
        try:
            result = self._call_model(self.PRIMARY_MODEL, prompt)
            model_used = self.PRIMARY_MODEL
        except Exception as e:
            logger.warning(f"Primary model failed: {e}, falling back to {self.FALLBACK_MODEL}")
            try:
                result = self._call_model(self.FALLBACK_MODEL, prompt)
                model_used = self.FALLBACK_MODEL
            except Exception as e2:
                logger.error(f"Fallback model also failed: {e2}")
                execution_time = time.time() - start_time
                return TaskAnalysis(
                    task_description=task_description,
                    task_type="unknown",
                    complexity_score=5,
                    recommended_roles_count=2,
                    key_skills=["general_programming"],
                    estimated_duration="unknown",
                    risk_factors=["model_call_failed"],
                    success_criteria=["complete_task"],
                    model_used="none",
                    execution_time=execution_time,
                    error=f"Both models failed: {e}, {e2}"
                )
        
        execution_time = time.time() - start_time
        
        # 解析结果
        try:
            analysis = self._parse_analysis_result(
                task_description, result, model_used, execution_time
            )
            logger.info(f"Task analysis completed: complexity={analysis.complexity_score}, "
                       f"roles={analysis.recommended_roles_count}")
            return analysis
        except Exception as e:
            logger.error(f"Failed to parse analysis result: {e}")
            return TaskAnalysis(
                task_description=task_description,
                task_type="unknown",
                complexity_score=5,
                recommended_roles_count=2,
                key_skills=["general_programming"],
                estimated_duration="unknown",
                risk_factors=["parse_failed"],
                success_criteria=["complete_task"],
                model_used=model_used,
                execution_time=execution_time,
                error=str(e)
            )
    
    def _build_analysis_prompt(self, task_description: str) -> str:
        """构建任务分析提示词"""
        return f"""你是一个智能任务分析专家。请分析以下任务，并提供结构化的分析结果。

## 任务描述
{task_description}

## 分析要求
请从以下维度分析任务，并以 JSON 格式输出：

1. **task_type**: 任务类型（如：data_processing, web_development, api_design, automation, research等）
2. **complexity_score**: 复杂度评分（1-10，1最简单，10最复杂）
3. **recommended_roles_count**: 推荐角色数量（根据复杂度，简单任务1-2个，复杂任务3-7个）
4. **key_skills**: 关键技能列表（字符串数组，如 ["python", "data_analysis", "api_design"]）
5. **estimated_duration**: 预估完成时间（如："1小时", "1-2天", "1周"）
6. **risk_factors**: 风险因素列表
7. **success_criteria**: 成功标准列表

## 复杂度评估指南
- 1-3分: 简单任务（如：文件格式转换、简单数据处理、单函数实现）→ 1-2个角色
- 4-6分: 中等任务（如：小型API开发、多模块脚本、简单Web页面）→ 2-3个角色
- 7-8分: 复杂任务（如：完整系统开发、多服务架构、复杂算法）→ 3-5个角色
- 9-10分: 极复杂任务（如：大型平台开发、分布式系统、AI系统）→ 5-7个角色

## 输出格式
必须返回有效的 JSON，不要包含任何其他文字：

```json
{{
  "task_type": "任务类型",
  "complexity_score": 5,
  "recommended_roles_count": 3,
  "key_skills": ["skill1", "skill2"],
  "estimated_duration": "1-2天",
  "risk_factors": ["风险1", "风险2"],
  "success_criteria": ["标准1", "标准2"]
}}
```
"""
    
    def _call_model(self, model: str, prompt: str) -> str:
        """
        调用模型 API
        
        使用 openclaw sessions spawn 调用模型
        """
        # 创建临时文件存储提示词
        with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as f:
            f.write(prompt)
            prompt_file = f.name
        
        try:
            # 构建命令
            cmd = [
                "openclaw", "sessions", "spawn",
                "--model", model,
                "--task-file", prompt_file,
                "--timeout", str(self.timeout),
                "--cleanup", "keep"
            ]
            
            logger.debug(f"Calling model: {model}")
            
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=self.timeout + 10
            )
            
            if result.returncode != 0:
                error_msg = result.stderr or "Unknown error"
                raise RuntimeError(f"Model call failed: {error_msg}")
            
            return result.stdout
            
        finally:
            # 清理临时文件
            try:
                Path(prompt_file).unlink(missing_ok=True)
            except:
                pass
    
    def _parse_analysis_result(
        self, 
        task_description: str, 
        raw_output: str, 
        model_used: str,
        execution_time: float
    ) -> TaskAnalysis:
        """解析模型返回的分析结果"""
        
        # 提取 JSON 部分
        json_str = self._extract_json(raw_output)
        
        try:
            data = json.loads(json_str)
        except json.JSONDecodeError as e:
            logger.error(f"JSON parse error: {e}\nRaw output: {raw_output[:500]}")
            # 尝试使用默认值
            return TaskAnalysis(
                task_description=task_description,
                task_type="unknown",
                complexity_score=5,
                recommended_roles_count=2,
                key_skills=["general_programming"],
                estimated_duration="unknown",
                risk_factors=["parse_error"],
                success_criteria=["complete_task"],
                model_used=model_used,
                execution_time=execution_time
            )
        
        # 提取字段，使用默认值
        complexity = self._clamp(int(data.get("complexity_score", 5)), 1, 10)
        roles_count = data.get("recommended_roles_count", self._estimate_roles(complexity))
        
        return TaskAnalysis(
            task_description=task_description,
            task_type=data.get("task_type", "unknown"),
            complexity_score=complexity,
            recommended_roles_count=roles_count,
            key_skills=data.get("key_skills", ["general_programming"]),
            estimated_duration=data.get("estimated_duration", "unknown"),
            risk_factors=data.get("risk_factors", []),
            success_criteria=data.get("success_criteria", []),
            model_used=model_used,
            execution_time=execution_time
        )
    
    def _extract_json(self, text: str) -> str:
        """从文本中提取 JSON"""
        # 尝试从代码块中提取
        if "```json" in text:
            start = text.find("```json") + 7
            end = text.find("```", start)
            if end > start:
                return text[start:end].strip()
        
        # 尝试从 ``` 中提取
        if "```" in text:
            start = text.find("```") + 3
            end = text.find("```", start)
            if end > start:
                return text[start:end].strip()
        
        # 尝试查找 JSON 对象
        start = text.find("{")
        end = text.rfind("}")
        if start >= 0 and end > start:
            return text[start:end+1]
        
        return text
    
    def _clamp(self, value: int, min_val: int, max_val: int) -> int:
        """限制值在范围内"""
        return max(min_val, min(max_val, value))
    
    def _estimate_roles(self, complexity: int) -> int:
        """根据复杂度估算角色数量"""
        if complexity <= 3:
            return 2
        elif complexity <= 6:
            return 3
        elif complexity <= 8:
            return 4
        else:
            return 5


# 便捷函数
def analyze_task(task_description: str, timeout: int = 120) -> TaskAnalysis:
    """
    便捷函数：分析任务
    
    Args:
        task_description: 任务描述
        timeout: 超时时间（秒）
        
    Returns:
        TaskAnalysis: 分析结果
    """
    analyzer = TaskAnalyzer(timeout=timeout)
    return analyzer.analyze(task_description)


if __name__ == "__main__":
    # 简单测试
    import argparse
    
    parser = argparse.ArgumentParser(description="Task Analyzer")
    parser.add_argument("task", help="Task description")
    parser.add_argument("--timeout", type=int, default=120, help="Timeout in seconds")
    
    args = parser.parse_args()
    
    logging.basicConfig(level=logging.INFO)
    
    result = analyze_task(args.task, args.timeout)
    print(json.dumps(result.to_dict(), indent=2, ensure_ascii=False))
