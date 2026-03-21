"""
BMAD-EVO v3.0 - ModelRouter
模型智能路由器

功能:
- 为每个角色选择最优模型
- 配置备选模型
- 根据角色职责匹配模型能力
"""

import json
import logging
from dataclasses import dataclass, asdict
from typing import Dict, List, Optional, Any
from enum import Enum

logger = logging.getLogger(__name__)


class ModelCapability(Enum):
    """模型能力标签"""
    CODE_GENERATION = "code_generation"      # 代码生成
    CODE_REVIEW = "code_review"              # 代码审查
    ARCHITECTURE = "architecture"            # 架构设计
    ANALYSIS = "analysis"                    # 分析能力
    WRITING = "writing"                      # 文档写作
    CREATIVE = "creative"                    # 创意思维
    LOGIC = "logic"                          # 逻辑推理
    LONG_CONTEXT = "long_context"            # 长上下文
    SPEED = "speed"                          # 响应速度
    COST_EFFICIENT = "cost_efficient"        # 成本效益


@dataclass
class ModelConfig:
    """模型配置"""
    id: str
    name: str
    provider: str
    context_window: int
    capabilities: List[ModelCapability]
    strengths: List[str]
    weaknesses: List[str]
    cost_tier: str  # low, medium, high
    typical_latency: str  # fast, medium, slow


@dataclass
class RoleModelMapping:
    """角色到模型的映射"""
    role_id: str
    primary_model: str
    fallback_models: List[str]
    reasoning: str  # 选择理由


@dataclass
class RoutingResult:
    """路由结果"""
    mappings: List[RoleModelMapping]
    total_roles: int
    model_usage: Dict[str, int]  # 模型使用统计
    estimated_cost_tier: str
    model_used: str = ""
    execution_time: float = 0.0
    error: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "mappings": [asdict(m) for m in self.mappings],
            "total_roles": self.total_roles,
            "model_usage": self.model_usage,
            "estimated_cost_tier": self.estimated_cost_tier,
            "model_used": self.model_used,
            "execution_time": self.execution_time,
            "error": self.error
        }


# 预定义的模型能力表（参考信息，不硬编码决策）
AVAILABLE_MODELS = {
    "kimi-coding/k2p5": ModelConfig(
        id="kimi-coding/k2p5",
        name="Kimi K2.5",
        provider="kimi-coding",
        context_window=262144,
        capabilities=[
            ModelCapability.CODE_GENERATION,
            ModelCapability.CODE_REVIEW,
            ModelCapability.ARCHITECTURE,
            ModelCapability.ANALYSIS,
            ModelCapability.LONG_CONTEXT,
            ModelCapability.LOGIC
        ],
        strengths=["代码能力强", "综合能力均衡", "长上下文"],
        weaknesses=["成本较高"],
        cost_tier="high",
        typical_latency="medium"
    ),
    "zhipu/glm-5": ModelConfig(
        id="zhipu/glm-5",
        name="GLM-5",
        provider="zhipu",
        context_window=128000,
        capabilities=[
            ModelCapability.ANALYSIS,
            ModelCapability.WRITING,
            ModelCapability.LOGIC,
            ModelCapability.CREATIVE
        ],
        strengths=["中文理解好", "逻辑推理强", "性价比"],
        weaknesses=["代码能力一般"],
        cost_tier="medium",
        typical_latency="medium"
    ),
    "minimax/minimax-m2.5": ModelConfig(
        id="minimax/minimax-m2.5",
        name="MiniMax-M2.5",
        provider="minimax",
        context_window=204800,
        capabilities=[
            ModelCapability.CODE_GENERATION,
            ModelCapability.LONG_CONTEXT,
            ModelCapability.ANALYSIS
        ],
        strengths=["长上下文", "代码生成", "成本效益"],
        weaknesses=["知名度较低"],
        cost_tier="medium",
        typical_latency="medium"
    ),
    "alibaba/qwen3.5-plus": ModelConfig(
        id="alibaba/qwen3.5-plus",
        name="Qwen3.5 Plus",
        provider="alibaba",
        context_window=128000,
        capabilities=[
            ModelCapability.CODE_GENERATION,
            ModelCapability.ANALYSIS,
            ModelCapability.SPEED,
            ModelCapability.COST_EFFICIENT
        ],
        strengths=["速度快", "成本低", "中文好"],
        weaknesses=["超长上下文能力有限"],
        cost_tier="low",
        typical_latency="fast"
    ),
    "kimi-coding/k2.5-turbo": ModelConfig(
        id="kimi-coding/k2.5-turbo",
        name="Kimi K2.5 Turbo",
        provider="kimi-coding",
        context_window=131072,
        capabilities=[
            ModelCapability.SPEED,
            ModelCapability.COST_EFFICIENT,
            ModelCapability.CODE_GENERATION
        ],
        strengths=["速度快", "性价比高"],
        weaknesses=["精度略低于k2.5"],
        cost_tier="medium",
        typical_latency="fast"
    )
}


class ModelRouter:
    """
    模型智能路由器
    根据角色特性和任务需求，为每个角色选择最优模型
    """
    
    PRIMARY_MODEL = "alibaba/qwen3.5-plus"
    FALLBACK_MODEL = "kimi-coding/k2p5"
    
    def __init__(self):
        self.models = AVAILABLE_MODELS
        logger.info(f"ModelRouter initialized with {len(self.models)} models")
    
    def route(
        self,
        roles: List[Dict[str, Any]],
        task_type: str,
        complexity_score: int,
        budget_constraint: Optional[str] = None
    ) -> RoutingResult:
        """
        为角色分配模型
        
        Args:
            roles: 角色列表
            task_type: 任务类型
            complexity_score: 复杂度评分
            budget_constraint: 预算约束 (low, medium, high, None)
            
        Returns:
            RoutingResult: 路由结果
        """
        import time
        start_time = time.time()
        
        logger.info(f"Routing models for {len(roles)} roles (task_type={task_type}, "
                   f"complexity={complexity_score})")
        
        # 构建路由提示词
        prompt = self._build_routing_prompt(
            roles, task_type, complexity_score, budget_constraint
        )
        
        # 调用模型进行智能路由
        try:
            result = self._call_model(self.PRIMARY_MODEL, prompt)
            model_used = self.PRIMARY_MODEL
        except Exception as e:
            logger.warning(f"Primary model failed: {e}, using fallback")
            try:
                result = self._call_model(self.FALLBACK_MODEL, prompt)
                model_used = self.FALLBACK_MODEL
            except Exception as e2:
                logger.error(f"Fallback also failed: {e2}")
                # 使用启发式路由作为最终回退
                return self._heuristic_route(
                    roles, task_type, complexity_score, budget_constraint,
                    execution_time=time.time() - start_time,
                    error=f"Both models failed: {e}, {e2}"
                )
        
        execution_time = time.time() - start_time
        
        # 解析结果
        try:
            routing_result = self._parse_routing_result(
                result, roles, model_used, execution_time
            )
            logger.info(f"Routing completed: {len(routing_result.mappings)} mappings, "
                       f"cost_tier={routing_result.estimated_cost_tier}")
            return routing_result
        except Exception as e:
            logger.error(f"Failed to parse routing result: {e}")
            return self._heuristic_route(
                roles, task_type, complexity_score, budget_constraint,
                execution_time=execution_time,
                error=str(e)
            )
    
    def _build_routing_prompt(
        self,
        roles: List[Dict[str, Any]],
        task_type: str,
        complexity_score: int,
        budget_constraint: Optional[str]
    ) -> str:
        """构建路由提示词"""
        
        # 构建角色信息
        roles_info = []
        for role in roles:
            roles_info.append({
                "id": role.get("id"),
                "name": role.get("name"),
                "description": role.get("description", ""),
                "responsibilities": role.get("responsibilities", []),
                "required_skills": role.get("required_skills", [])
            })
        
        # 构建模型信息
        models_info = []
        for model_id, config in self.models.items():
            models_info.append({
                "id": model_id,
                "name": config.name,
                "context_window": config.context_window,
                "strengths": config.strengths,
                "weaknesses": config.weaknesses,
                "cost_tier": config.cost_tier,
                "latency": config.typical_latency
            })
        
        budget_str = f"\n- **预算约束**: {budget_constraint}" if budget_constraint else ""
        
        return f"""你是一个智能模型路由专家。请为每个角色选择最合适的AI模型。

## 任务信息
- **任务类型**: {task_type}
- **复杂度评分**: {complexity_score}/10
{budget_str}

## 可用模型
```json
{json.dumps(models_info, indent=2, ensure_ascii=False)}
```

## 需要分配的角色
```json
{json.dumps(roles_info, indent=2, ensure_ascii=False)}
```

## 路由规则

### 模型选择原则
1. **代码相关角色**（开发、架构、测试）→ 优先选代码能力强的模型 (kimi-coding/k2p5, minimax/minimax-m2.5)
2. **分析规划角色**（需求分析、产品经理）→ 优先选逻辑分析强的模型 (zhipu/glm-5, alibaba/qwen3.5-plus)
3. **简单任务** → 优先选速度快、成本低的模型 (alibaba/qwen3.5-plus)
4. **复杂任务**（复杂度>7）→ 优先选综合能力强的模型 (kimi-coding/k2p5)
5. **长文档处理** → 优先选上下文窗口大的模型 (kimi-coding/k2p5, minimax/minimax-m2.5)

### 备选模型配置
每个角色必须配置2-3个备选模型（按优先级排序），当主模型失败时按顺序回退。

### 成本考虑
- 低预算: 优先使用 alibaba/qwen3.5-plus
- 中等预算: 平衡使用各类模型
- 高预算: 优先使用 kimi-coding/k2p5 等高端模型

## 输出格式
必须返回有效的 JSON，不要包含任何其他文字：

```json
{{
  "mappings": [
    {{
      "role_id": "角色id",
      "primary_model": "主模型id",
      "fallback_models": ["备选1", "备选2"],
      "reasoning": "选择理由"
    }}
  ],
  "estimated_cost_tier": "low|medium|high",
  "optimization_notes": "优化建议"
}}
```
"""
    
    def _call_model(self, model: str, prompt: str) -> str:
        """调用模型"""
        import subprocess
        import tempfile
        from pathlib import Path
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as f:
            f.write(prompt)
            prompt_file = f.name
        
        try:
            cmd = [
                "openclaw", "sessions", "spawn",
                "--model", model,
                "--task-file", prompt_file,
                "--timeout", "120",
                "--cleanup", "keep"
            ]
            
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=130
            )
            
            if result.returncode != 0:
                raise RuntimeError(f"Model call failed: {result.stderr}")
            
            return result.stdout
            
        finally:
            try:
                Path(prompt_file).unlink(missing_ok=True)
            except:
                pass
    
    def _parse_routing_result(
        self,
        raw_output: str,
        roles: List[Dict[str, Any]],
        model_used: str,
        execution_time: float
    ) -> RoutingResult:
        """解析路由结果"""
        
        json_str = self._extract_json(raw_output)
        data = json.loads(json_str)
        
        mappings_data = data.get("mappings", [])
        mappings = []
        model_usage = {}
        
        for mapping_data in mappings_data:
            role_id = mapping_data.get("role_id")
            primary = mapping_data.get("primary_model")
            
            # 统计模型使用
            model_usage[primary] = model_usage.get(primary, 0) + 1
            
            mapping = RoleModelMapping(
                role_id=role_id,
                primary_model=primary,
                fallback_models=mapping_data.get("fallback_models", []),
                reasoning=mapping_data.get("reasoning", "")
            )
            mappings.append(mapping)
        
        # 为未映射的角色添加默认值
        mapped_role_ids = {m.role_id for m in mappings}
        for role in roles:
            if role.get("id") not in mapped_role_ids:
                # 添加默认映射
                mappings.append(RoleModelMapping(
                    role_id=role.get("id"),
                    primary_model="kimi-coding/k2p5",
                    fallback_models=["alibaba/qwen3.5-plus", "zhipu/glm-5"],
                    reasoning="Default fallback mapping"
                ))
                model_usage["kimi-coding/k2p5"] = model_usage.get("kimi-coding/k2p5", 0) + 1
        
        return RoutingResult(
            mappings=mappings,
            total_roles=len(mappings),
            model_usage=model_usage,
            estimated_cost_tier=data.get("estimated_cost_tier", "medium"),
            model_used=model_used,
            execution_time=execution_time
        )
    
    def _heuristic_route(
        self,
        roles: List[Dict[str, Any]],
        task_type: str,
        complexity_score: int,
        budget_constraint: Optional[str],
        execution_time: float = 0.0,
        error: Optional[str] = None
    ) -> RoutingResult:
        """启发式路由（当模型调用失败时使用）"""
        
        mappings = []
        model_usage = {}
        
        for role in roles:
            role_id = role.get("id")
            role_name = role.get("name", "").lower()
            responsibilities = [r.lower() for r in role.get("responsibilities", [])]
            skills = [s.lower() for s in role.get("required_skills", [])]
            
            # 启发式规则
            is_code_related = any(kw in role_name or any(kw in r for r in responsibilities)
                                 for kw in ["开发", "代码", "测试", "架构", "programming", "code", "test"])
            is_analysis = any(kw in role_name or any(kw in r for r in responsibilities)
                             for kw in ["分析", "产品", "需求", "analysis", "product", "requirement"])
            
            # 选择主模型
            if budget_constraint == "low":
                primary = "alibaba/qwen3.5-plus"
            elif complexity_score >= 8 or is_code_related:
                primary = "kimi-coding/k2p5"
            elif is_analysis:
                primary = "zhipu/glm-5"
            else:
                primary = "alibaba/qwen3.5-plus"
            
            # 选择备选
            if primary == "kimi-coding/k2p5":
                fallbacks = ["alibaba/qwen3.5-plus", "zhipu/glm-5"]
            elif primary == "zhipu/glm-5":
                fallbacks = ["alibaba/qwen3.5-plus", "kimi-coding/k2p5"]
            else:
                fallbacks = ["kimi-coding/k2p5", "zhipu/glm-5"]
            
            model_usage[primary] = model_usage.get(primary, 0) + 1
            
            mappings.append(RoleModelMapping(
                role_id=role_id,
                primary_model=primary,
                fallback_models=fallbacks,
                reasoning=f"Heuristic: code_related={is_code_related}, analysis={is_analysis}"
            ))
        
        # 确定成本等级
        if "kimi-coding/k2p5" in model_usage and model_usage["kimi-coding/k2p5"] > len(roles) / 2:
            cost_tier = "high"
        elif "alibaba/qwen3.5-plus" in model_usage and model_usage["alibaba/qwen3.5-plus"] > len(roles) / 2:
            cost_tier = "low"
        else:
            cost_tier = "medium"
        
        return RoutingResult(
            mappings=mappings,
            total_roles=len(mappings),
            model_usage=model_usage,
            estimated_cost_tier=cost_tier,
            model_used="heuristic",
            execution_time=execution_time,
            error=error
        )
    
    def _extract_json(self, text: str) -> str:
        """从文本中提取 JSON"""
        if "```json" in text:
            start = text.find("```json") + 7
            end = text.find("```", start)
            if end > start:
                return text[start:end].strip()
        
        if "```" in text:
            start = text.find("```") + 3
            end = text.find("```", start)
            if end > start:
                return text[start:end].strip()
        
        start = text.find("{")
        end = text.rfind("}")
        if start >= 0 and end > start:
            return text[start:end+1]
        
        return text
    
    def get_model_for_role(self, role_id: str, routing_result: RoutingResult) -> Optional[RoleModelMapping]:
        """获取角色的模型映射"""
        for mapping in routing_result.mappings:
            if mapping.role_id == role_id:
                return mapping
        return None
    
    def get_fallback_chain(self, role_id: str, routing_result: RoutingResult) -> List[str]:
        """获取角色的模型回退链"""
        mapping = self.get_model_for_role(role_id, routing_result)
        if mapping:
            return [mapping.primary_model] + mapping.fallback_models
        return ["kimi-coding/k2p5", "alibaba/qwen3.5-plus"]


# 便捷函数
def route_models(
    roles: List[Dict[str, Any]],
    task_type: str,
    complexity_score: int,
    budget_constraint: Optional[str] = None
) -> RoutingResult:
    """便捷函数：为角色分配模型"""
    router = ModelRouter()
    return router.route(roles, task_type, complexity_score, budget_constraint)


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Model Router")
    parser.add_argument("--roles-file", required=True, help="JSON file with roles")
    parser.add_argument("--type", default="general", help="Task type")
    parser.add_argument("--complexity", type=int, default=5, help="Complexity score")
    parser.add_argument("--budget", help="Budget constraint (low/medium/high)")
    
    args = parser.parse_args()
    
    logging.basicConfig(level=logging.INFO)
    
    with open(args.roles_file, 'r') as f:
        roles = json.load(f)
    
    result = route_models(roles, args.type, args.complexity, args.budget)
    print(json.dumps(result.to_dict(), indent=2, ensure_ascii=False))
