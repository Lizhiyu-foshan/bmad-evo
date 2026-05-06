#!/usr/bin/env python3
"""
BMAD-EVO config_loader unit tests

Tests:
1. Config loading from file
2. Deep merge with defaults
3. Environment variable overrides
4. get_model_for_component
5. get_model_chain_for_component
6. get_timeout
7. get_quality_threshold
8. get_max_retries
9. get_context_window
10. determine_analysis_mode
11. determine_output_strategy
12. reload_config
"""

import sys
import os
import json
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "lib"))


def _make_temp_config(config_dir: str, config_data: dict) -> str:
    config_path = os.path.join(config_dir, "bmad.json")
    with open(config_path, "w", encoding="utf-8") as f:
        json.dump(config_data, f)
    return config_path


def test_config_loads_from_file():
    print("\n" + "=" * 70)
    print("Test: config loads from file")
    print("=" * 70)

    with tempfile.TemporaryDirectory() as tmpdir:
        _make_temp_config(tmpdir, {
            "models": {
                "primary": "test-model-a",
                "secondary": "test-model-b"
            }
        })

        import config_loader
        config_loader._LOADED_CONFIG = None
        config_loader._CONFIG_DIR = Path(tmpdir)
        config_loader._CONFIG_FILE = Path(tmpdir) / "bmad.json"

        cfg = config_loader.get_config()
        assert cfg["models"]["primary"] == "test-model-a", \
            f"Expected test-model-a, got {cfg['models']['primary']}"
        assert cfg["models"]["secondary"] == "test-model-b", \
            f"Expected test-model-b, got {cfg['models']['secondary']}"

        print("  PASS: config loaded from file correctly")
        config_loader._LOADED_CONFIG = None


def test_deep_merge_defaults():
    print("\n" + "=" * 70)
    print("Test: deep merge with defaults")
    print("=" * 70)

    with tempfile.TemporaryDirectory() as tmpdir:
        _make_temp_config(tmpdir, {
            "models": {
                "primary": "custom-primary"
            }
        })

        import config_loader
        config_loader._LOADED_CONFIG = None
        config_loader._CONFIG_DIR = Path(tmpdir)
        config_loader._CONFIG_FILE = Path(tmpdir) / "bmad.json"

        cfg = config_loader.get_config()

        assert cfg["models"]["primary"] == "custom-primary"
        assert "secondary" in cfg["models"]
        assert "absolute_fallback" in cfg["models"]
        assert "call_defaults" in cfg["models"]

        print("  PASS: deep merge preserves defaults for unspecified keys")
        config_loader._LOADED_CONFIG = None


def test_env_var_overrides():
    print("\n" + "=" * 70)
    print("Test: environment variable overrides")
    print("=" * 70)

    with tempfile.TemporaryDirectory() as tmpdir:
        _make_temp_config(tmpdir, {
            "models": {
                "primary": "file-model"
            }
        })

        import config_loader
        config_loader._LOADED_CONFIG = None
        config_loader._CONFIG_DIR = Path(tmpdir)
        config_loader._CONFIG_FILE = Path(tmpdir) / "bmad.json"

        os.environ["BMAD_PRIMARY_MODEL"] = "env-model-override"
        try:
            cfg = config_loader.get_config()
            assert cfg["models"]["primary"] == "env-model-override", \
                f"Expected env-model-override, got {cfg['models']['primary']}"
            print("  PASS: env var BMAD_PRIMARY_MODEL overrides file config")
        finally:
            del os.environ["BMAD_PRIMARY_MODEL"]
            config_loader._LOADED_CONFIG = None


def test_get_model_for_component():
    print("\n" + "=" * 70)
    print("Test: get_model_for_component")
    print("=" * 70)

    import config_loader
    config_loader._LOADED_CONFIG = None

    primary, fallback = config_loader.get_model_for_component("task_analysis")
    assert isinstance(primary, str) and len(primary) > 0, \
        f"Expected non-empty string, got {primary}"
    assert isinstance(fallback, str) and len(fallback) > 0, \
        f"Expected non-empty string, got {fallback}"
    print(f"  PASS: task_analysis -> primary={primary}, fallback={fallback}")
    config_loader._LOADED_CONFIG = None


def test_get_model_chain():
    print("\n" + "=" * 70)
    print("Test: get_model_chain_for_component")
    print("=" * 70)

    import config_loader
    config_loader._LOADED_CONFIG = None

    chain = config_loader.get_model_chain_for_component("task_analysis")
    assert isinstance(chain, list), f"Expected list, got {type(chain)}"
    assert len(chain) >= 2, f"Expected >=2 models in chain, got {len(chain)}"
    print(f"  PASS: chain for task_analysis = {chain}")
    config_loader._LOADED_CONFIG = None


def test_get_timeout():
    print("\n" + "=" * 70)
    print("Test: get_timeout")
    print("=" * 70)

    import config_loader
    config_loader._LOADED_CONFIG = None

    timeout = config_loader.get_timeout("task_analysis")
    assert isinstance(timeout, int), f"Expected int, got {type(timeout)}"
    assert timeout > 0, f"Expected positive timeout, got {timeout}"
    print(f"  PASS: task_analysis timeout = {timeout}s")

    default_timeout = config_loader.get_timeout("nonexistent_component")
    assert isinstance(default_timeout, int)
    print(f"  PASS: nonexistent_component returns default = {default_timeout}s")
    config_loader._LOADED_CONFIG = None


def test_get_quality_threshold():
    print("\n" + "=" * 70)
    print("Test: get_quality_threshold")
    print("=" * 70)

    import config_loader
    config_loader._LOADED_CONFIG = None

    threshold = config_loader.get_quality_threshold("pass_threshold", 85)
    assert isinstance(threshold, int), f"Expected int, got {type(threshold)}"
    assert threshold > 0
    print(f"  PASS: pass_threshold = {threshold}")
    config_loader._LOADED_CONFIG = None


def test_get_max_retries():
    print("\n" + "=" * 70)
    print("Test: get_max_retries")
    print("=" * 70)

    import config_loader
    config_loader._LOADED_CONFIG = None

    retries = config_loader.get_max_retries("workflow", 3)
    assert isinstance(retries, int), f"Expected int, got {type(retries)}"
    assert retries > 0
    print(f"  PASS: workflow max_retries = {retries}")
    config_loader._LOADED_CONFIG = None


def test_get_context_window():
    print("\n" + "=" * 70)
    print("Test: get_context_window")
    print("=" * 70)

    import config_loader
    config_loader._LOADED_CONFIG = None

    inp, out = config_loader.get_context_window("glm-5.1")
    assert isinstance(inp, int) and inp > 0, f"Expected positive int, got {inp}"
    assert isinstance(out, int) and out > 0, f"Expected positive int, got {out}"
    print(f"  PASS: glm-5.1 context_window = input:{inp}, output:{out}")
    config_loader._LOADED_CONFIG = None


def test_determine_analysis_mode():
    print("\n" + "=" * 70)
    print("Test: determine_analysis_mode")
    print("=" * 70)

    import config_loader
    config_loader._LOADED_CONFIG = None

    low = config_loader.determine_analysis_mode(3)
    assert low == "simple", f"Expected 'simple' for complexity 3, got {low}"

    high = config_loader.determine_analysis_mode(8)
    assert high == "complex_thinking_chain", \
        f"Expected 'complex_thinking_chain' for complexity 8, got {high}"

    mid = config_loader.determine_analysis_mode(7)
    assert mid == "complex_thinking_chain", \
        f"Expected 'complex_thinking_chain' for complexity 7, got {mid}"

    print(f"  PASS: complexity 3 -> {low}, 7 -> {mid}, 8 -> {high}")
    config_loader._LOADED_CONFIG = None


def test_determine_output_strategy():
    print("\n" + "=" * 70)
    print("Test: determine_output_strategy")
    print("=" * 70)

    import config_loader
    config_loader._LOADED_CONFIG = None

    strategy = config_loader.determine_output_strategy()
    assert isinstance(strategy, dict), f"Expected dict, got {type(strategy)}"
    assert "output_format" in strategy, f"Expected 'output_format' key, got {list(strategy.keys())}"
    print(f"  PASS: output_strategy = {strategy}")
    config_loader._LOADED_CONFIG = None


def test_reload_config():
    print("\n" + "=" * 70)
    print("Test: reload_config")
    print("=" * 70)

    with tempfile.TemporaryDirectory() as tmpdir:
        _make_temp_config(tmpdir, {
            "models": {"primary": "first-model"}
        })

        import config_loader
        config_loader._LOADED_CONFIG = None
        config_loader._CONFIG_DIR = Path(tmpdir)
        config_loader._CONFIG_FILE = Path(tmpdir) / "bmad.json"

        cfg1 = config_loader.get_config()
        assert cfg1["models"]["primary"] == "first-model"

        _make_temp_config(tmpdir, {
            "models": {"primary": "second-model"}
        })

        config_loader.reload_config()
        cfg2 = config_loader.get_config()
        assert cfg2["models"]["primary"] == "second-model", \
            f"Expected second-model after reload, got {cfg2['models']['primary']}"

        print("  PASS: reload picks up file changes")
        config_loader._LOADED_CONFIG = None


def test_thinking_chain_config():
    print("\n" + "=" * 70)
    print("Test: get_thinking_chain_config")
    print("=" * 70)

    import config_loader
    config_loader._LOADED_CONFIG = None

    tc_cfg = config_loader.get_thinking_chain_config()
    assert isinstance(tc_cfg, dict), f"Expected dict, got {type(tc_cfg)}"
    assert "max_re_executions_per_role" in tc_cfg, f"Missing max_re_executions_per_role key, got {list(tc_cfg.keys())}"
    assert "max_reflection_rounds" in tc_cfg, f"Missing max_reflection_rounds key, got {list(tc_cfg.keys())}"
    print(f"  PASS: thinking_chain config = max_re={tc_cfg['max_re_executions_per_role']}, "
          f"max_reflection={tc_cfg['max_reflection_rounds']}")
    config_loader._LOADED_CONFIG = None


def run_all_tests():
    tests = [
        test_config_loads_from_file,
        test_deep_merge_defaults,
        test_env_var_overrides,
        test_get_model_for_component,
        test_get_model_chain,
        test_get_timeout,
        test_get_quality_threshold,
        test_get_max_retries,
        test_get_context_window,
        test_determine_analysis_mode,
        test_determine_output_strategy,
        test_reload_config,
        test_thinking_chain_config,
    ]

    passed = 0
    failed = 0
    for test in tests:
        try:
            test()
            passed += 1
        except Exception as e:
            failed += 1
            print(f"  FAIL: {test.__name__} - {e}")

    print("\n" + "=" * 70)
    print(f"Results: {passed} passed, {failed} failed, {passed + failed} total")
    print("=" * 70)
    return failed == 0


if __name__ == "__main__":
    success = run_all_tests()
    sys.exit(0 if success else 1)
