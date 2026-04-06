#!/usr/bin/env python3
"""
BMAD-EVO v3.0 - Model Availability Test
Tests all model connections and response capability
"""

import sys
import json
import requests
import time
import argparse
from datetime import datetime
from typing import Dict, List, Tuple

sys.stdout.reconfigure(encoding="utf-8")

# Configuration
ALI_API_KEY = "sk-sp-68f6997fc9924babb9f6b50c03a5a529"
ALI_BASE_URL = "https://coding.dashscope.aliyuncs.com/v1"

# Available models
AVAILABLE_MODELS = {
    "minimax-m2.5": {
        "name": "MiniMax-M2.5",
        "role": "Latest Intelligence Integrator",
        "timeout": 60,
    },
    "glm-5": {
        "name": "GLM-5",
        "role": "Geopolitical Analyst / Strategic Intelligence",
        "timeout": 90,
    },
    "kimi-k2.5": {
        "name": "Kimi K2.5",
        "role": "Energy Economist / Global Impact Assessor",
        "timeout": 90,
    },
    "qwen3.5-plus": {
        "name": "Qwen3.5-Plus",
        "role": "Investment Strategy Advisor / Risk Manager",
        "timeout": 60,
    },
}


class ModelTester:
    def __init__(self):
        self.results = {}
        self.headers = {
            "Authorization": f"Bearer {ALI_API_KEY}",
            "Content-Type": "application/json",
        }

    def test_model(
        self, model_id: str, config: Dict, wait_time: int = 0
    ) -> Tuple[bool, str, float]:
        """Test single model"""
        print(f"\n{'=' * 80}")
        print(f"Testing Model: {config['name']} ({model_id})")
        print(f"   Role: {config['role']}")
        print(f"   Timeout: {config['timeout']}s")
        print(f"{'=' * 80}")

        if wait_time > 0:
            print(f"Waiting {wait_time}s to avoid rate limiting...")
            time.sleep(wait_time)

        test_prompt = "Please reply 'Test successful' in three words only."
        system_prompt = "You are a test assistant. Reply exactly as requested."

        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": test_prompt},
        ]

        payload = {
            "model": model_id,
            "messages": messages,
            "temperature": 0.7,
            "max_tokens": 100,
        }

        start_time = time.time()
        try:
            print(f"Sending test request...")
            response = requests.post(
                f"{ALI_BASE_URL}/chat/completions",
                headers=self.headers,
                json=payload,
                timeout=config["timeout"],
            )
            elapsed = time.time() - start_time

            print(f"Response time: {elapsed:.2f}s")
            print(f"HTTP Status: {response.status_code}")

            if response.status_code == 200:
                data = response.json()
                text = data["choices"][0]["message"]["content"]
                print(f"SUCCESS!")
                print(f"Response: {text[:100]}")
                return True, text, elapsed
            else:
                error_msg = f"HTTP {response.status_code}: {response.text[:200]}"
                print(f"FAILED: {error_msg}")
                return False, error_msg, elapsed

        except requests.exceptions.Timeout:
            elapsed = time.time() - start_time
            print(f"FAILED: Request timeout ({config['timeout']}s)")
            return False, "Timeout", elapsed
        except Exception as e:
            elapsed = time.time() - start_time
            print(f"FAILED: {str(e)}")
            return False, str(e), elapsed

    def run_all_tests(self, wait_between: int = 3) -> Dict:
        """Test all models"""
        print("\n" + "=" * 80)
        print("BMAD-EVO v3.0 - Model Availability Test")
        print("=" * 80)
        print(f"\nTest Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"API Endpoint: {ALI_BASE_URL}")
        print(f"Models to test: {len(AVAILABLE_MODELS)}")
        print(
            f"Estimated time: {len(AVAILABLE_MODELS) * (60 + wait_between) // 60} minutes"
        )
        print("=" * 80)

        results = {}

        for i, (model_id, config) in enumerate(AVAILABLE_MODELS.items(), 1):
            print(f"\n\nProgress: [{i}/{len(AVAILABLE_MODELS)}]")

            wait_time = wait_between if i > 1 else 0
            success, output, elapsed = self.test_model(model_id, config, wait_time)

            results[model_id] = {
                "name": config["name"],
                "role": config["role"],
                "success": success,
                "output": output,
                "response_time": elapsed,
                "timestamp": datetime.now().isoformat(),
            }

        return results

    def generate_report(self, results: Dict) -> str:
        """Generate test report"""
        report = f"""# BMAD-EVO v3.0 - Model Availability Test Report

**Test Time**: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}  
**API Endpoint**: {ALI_BASE_URL}  
**Models Tested**: {len(AVAILABLE_MODELS)}  

## Summary

| Model ID | Model Name | Role | Status | Response Time | Note |
|----------|------------|------|--------|---------------|------|
"""

        for model_id, result in results.items():
            status_icon = "SUCCESS" if result["success"] else "FAILED"
            time_str = f"{result['response_time']:.2f}s"
            note = "OK" if result["success"] else result["output"][:50]

            report += f"| {model_id} | {result['name']} | {result['role']} | {status_icon} | {time_str} | {note} |\n"

        successful = sum(1 for r in results.values() if r["success"])
        failed = len(results) - successful

        report += f"""

## Statistics

- **Available Models**: {successful}/{len(results)} ({successful / len(results) * 100:.0f}%)
- **Unavailable Models**: {failed}/{len(results)} ({failed / len(results) * 100:.0f}%)

## Available Model Config

```python
AVAILABLE_MODELS = {{
"""

        for model_id, result in results.items():
            if result["success"]:
                config = AVAILABLE_MODELS[model_id]
                report += f'''    "{model_id}": {{
        "name": "{result["name"]}",
        "role": "{result["role"]}",
        "timeout": {config["timeout"]}
    }},
'''

        report += """}
```

---

**Test Complete**  
**BMAD-EVO v3.0 Model Availability Test**
"""

        return report

    def save_results(self, results: Dict, report: str):
        """Save test results"""
        # Save JSON
        json_file = (
            f"model_test_results_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        )
        with open(json_file, "w", encoding="utf-8") as f:
            json.dump(results, f, ensure_ascii=False, indent=2)
        print(f"\nJSON results saved: {json_file}")

        # Save Markdown
        md_file = f"model_test_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.md"
        with open(md_file, "w", encoding="utf-8") as f:
            f.write(report)
        print(f"Markdown report saved: {md_file}")

        return json_file, md_file


def main():
    parser = argparse.ArgumentParser(description="BMAD-EVO Model Availability Test")
    parser.add_argument(
        "--wait", type=int, default=3, help="Wait time between models (seconds)"
    )
    args = parser.parse_args()

    tester = ModelTester()
    results = tester.run_all_tests(wait_between=args.wait)

    # Generate report
    report = tester.generate_report(results)

    # Display report
    print("\n\n" + "=" * 80)
    print("Test Report")
    print("=" * 80)
    print(report)

    # Save results
    json_file, md_file = tester.save_results(results, report)

    # Final status
    successful = sum(1 for r in results.values() if r["success"])
    print("\n" + "=" * 80)
    if successful == len(results):
        print("All models test PASSED! System ready.")
    elif successful >= len(results) // 2:
        print(
            f"Partial success ({successful}/{len(results)}), system can run in degraded mode."
        )
    else:
        print(
            f"Most models failed ({successful}/{len(results)}), please check API configuration."
        )
    print("=" * 80)


if __name__ == "__main__":
    main()
