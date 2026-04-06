# BMAD-EVO v3.0 - Model Availability Test Report

**Test Time**: 2026-03-30 14:47:11  
**API Endpoint**: https://coding.dashscope.aliyuncs.com/v1  
**Models Tested**: 4  

## Summary

| Model ID | Model Name | Role | Status | Response Time | Note |
|----------|------------|------|--------|---------------|------|
| minimax-m2.5 | MiniMax-M2.5 | Latest Intelligence Integrator | FAILED | 1.64s | HTTP 400: {"error":{"code":"invalid_parameter_erro |
| glm-5 | GLM-5 | Geopolitical Analyst / Strategic Intelligence | SUCCESS | 2.74s | OK |
| kimi-k2.5 | Kimi K2.5 | Energy Economist / Global Impact Assessor | SUCCESS | 1.60s | OK |
| qwen3.5-plus | Qwen3.5-Plus | Investment Strategy Advisor / Risk Manager | FAILED | 60.92s | Timeout |


## Statistics

- **Available Models**: 2/4 (50%)
- **Unavailable Models**: 2/4 (50%)

## Available Model Config

```python
AVAILABLE_MODELS = {
    "glm-5": {
        "name": "GLM-5",
        "role": "Geopolitical Analyst / Strategic Intelligence",
        "timeout": 90
    },
    "kimi-k2.5": {
        "name": "Kimi K2.5",
        "role": "Energy Economist / Global Impact Assessor",
        "timeout": 90
    },
}
```

---

**Test Complete**  
**BMAD-EVO v3.0 Model Availability Test**
