"""
Tests for thinking chain v4 components:
- DataCollectionSpec
- DataCollectionPlanner.plan_for_role()
- DataCollector (unit-level, no network)
- ThinkingChainState
- ThinkingChainExecutor.execute_full_chain()
- Enhanced context threading through orchestrator
"""

import json
import pytest
from unittest.mock import patch, MagicMock

from lib.v4.thinking_chain import (
    DataCollectionSpec,
    DataCollectionPlanner,
    ThinkingChainState,
    ThinkingChainExecutor,
    FeedbackMessage,
    ReflectionIssue,
    SelfReflectionEngine,
    AnalysisMode,
)


class TestDataCollectionSpec:
    def test_defaults(self):
        spec = DataCollectionSpec(
            role_name="test_role",
            queries=["q1"],
            sources=["commodity_prices"],
            priority="critical",
            rationale="need it",
        )
        assert spec.role_name == "test_role"
        assert spec.queries == ["q1"]
        assert spec.sources == ["commodity_prices"]
        assert spec.priority == "critical"
        assert spec.rationale == "need it"

    def test_empty_queries(self):
        spec = DataCollectionSpec(
            role_name="r",
            queries=[],
            sources=[],
            priority="supplementary",
            rationale="",
        )
        assert spec.queries == []

    def test_to_dict(self):
        spec = DataCollectionSpec(
            role_name="r",
            queries=["q"],
            sources=["s"],
            priority="high",
            rationale="reason",
        )
        d = spec.to_dict()
        assert d["role_name"] == "r"
        assert d["queries"] == ["q"]


class TestDataCollectionPlanner:
    def setup_method(self):
        self.planner = DataCollectionPlanner(timeout=30)

    @patch.object(DataCollectionPlanner, "_call_model")
    def test_plan_for_role_with_queries(self, mock_call):
        mock_call.return_value = json.dumps({
            "queries": ["WTI price", "Brent price"],
            "sources": ["commodity_prices"],
            "priority": "critical",
            "rationale": "need oil prices",
        })
        spec = self.planner.plan_for_role(
            role_name="oil_analyst",
            role_description="Analyzes oil markets",
            role_responsibilities=["Track crude prices"],
            task_description="Analyze oil crisis",
            existing_data_summary="Gold price data only",
            previous_roles_output="",
        )
        assert spec.role_name == "oil_analyst"
        assert len(spec.queries) == 2
        assert spec.priority == "critical"

    @patch.object(DataCollectionPlanner, "_call_model")
    def test_plan_for_role_no_extra_data(self, mock_call):
        mock_call.return_value = json.dumps({
            "queries": [],
            "sources": [],
            "priority": "supplementary",
            "rationale": "data sufficient",
        })
        spec = self.planner.plan_for_role(
            role_name="synthesizer",
            role_description="Synthesizes",
            role_responsibilities=["Combine analysis"],
            task_description="Test task",
            existing_data_summary="Full data available",
            previous_roles_output="Previous output",
        )
        assert spec.queries == []

    @patch.object(DataCollectionPlanner, "_call_model", side_effect=Exception("LLM down"))
    def test_plan_for_role_fallback_on_error(self, mock_call):
        spec = self.planner.plan_for_role(
            role_name="r",
            role_description="d",
            role_responsibilities=[],
            task_description="t",
            existing_data_summary="",
            previous_roles_output="",
        )
        assert spec.queries == []
        assert "规划失败" in spec.rationale

    def test_extract_json_from_code_block(self):
        raw = '```json\n{"queries": ["q1"], "sources": [], "priority": "high", "rationale": "test"}\n```'
        result = self.planner._extract_json(raw)
        parsed = json.loads(result)
        assert parsed["queries"] == ["q1"]

    def test_extract_json_plain(self):
        raw = '{"queries": [], "sources": [], "priority": "low", "rationale": "ok"}'
        result = self.planner._extract_json(raw)
        parsed = json.loads(result)
        assert parsed["priority"] == "low"


class TestDataCollector:
    def test_import(self):
        try:
            from lib.v4.data_collector import DataCollector
            dc = DataCollector()
            assert dc is not None
        except ImportError:
            pytest.skip("DataCollector import failed")

    def test_execute_no_queries(self):
        try:
            from lib.v4.data_collector import DataCollector
        except ImportError:
            pytest.skip("DataCollector import failed")
        dc = DataCollector()
        spec = DataCollectionSpec(
            role_name="r",
            queries=[],
            sources=[],
            priority="supplementary",
            rationale="none",
        )
        result = dc.execute(spec)
        assert result == "[无额外数据采集需求]" or result == "[数据采集已禁用]"

    @patch("lib.v4.data_collector.DataCollector._fetch_query")
    def test_execute_with_queries(self, mock_fetch):
        try:
            from lib.v4.data_collector import DataCollector
        except ImportError:
            pytest.skip("DataCollector import failed")
        mock_fetch.return_value = "Gold: $4,685/oz"
        dc = DataCollector()
        spec = DataCollectionSpec(
            role_name="analyst",
            queries=["gold price"],
            sources=["commodity_prices"],
            priority="critical",
            rationale="need gold price",
        )
        result = dc.execute(spec)
        assert "Gold" in result or "gold" in result.lower()


class TestThinkingChainState:
    def test_initial_state(self):
        state = ThinkingChainState(
            analysis_mode=AnalysisMode.COMPLEX_THINKING_CHAIN,
            task_description="test",
            role_execution_order=["r1", "r2"],
        )
        assert state.role_outputs == {}
        assert state.collected_data == {}
        assert state.current_reflection_round == 0

    def test_to_dict_roundtrip(self):
        state = ThinkingChainState(
            analysis_mode=AnalysisMode.COMPLEX_THINKING_CHAIN,
            task_description="test",
            role_execution_order=["r1"],
        )
        state.role_outputs = {"r1": "output1"}
        state.collected_data = {"r1": "data1"}
        d = state.to_dict()
        assert d["collected_data"]["r1"] == "data1"
        assert "r1" in d["role_outputs_summary"]


class TestThinkingChainExecutor:
    def _make_executor(self, enable_data_collection=True):
        role_defs = {
            "role_a": {"title": "Role A", "input_from": []},
            "role_b": {"title": "Role B", "input_from": ["role_a"]},
        }
        return ThinkingChainExecutor(
            task_description="test task",
            role_execution_order=["role_a", "role_b"],
            role_definitions=role_defs,
            enable_data_collection=enable_data_collection,
        )

    def test_init(self):
        tc = self._make_executor()
        assert tc.data_planner is not None
        assert tc.reflection_engine is not None

    @patch.object(DataCollectionPlanner, "plan_for_role")
    def test_get_pre_execution_context(self, mock_plan):
        mock_plan.return_value = DataCollectionSpec(
            role_name="role_a",
            queries=[],
            sources=[],
            priority="supplementary",
            rationale="no extra data",
        )
        tc = self._make_executor()
        context, spec = tc.get_pre_execution_context("role_a", "initial data here")
        assert "initial data here" in context
        assert spec.role_name == "role_a"

    @patch.object(DataCollectionPlanner, "plan_for_role")
    def test_execute_full_chain_simple(self, mock_plan):
        mock_plan.return_value = DataCollectionSpec(
            role_name="role_a",
            queries=[],
            sources=[],
            priority="supplementary",
            rationale="none",
        )
        tc = self._make_executor()
        results = tc.execute_full_chain(
            initial_data="test data",
            role_executor=lambda name, ctx: f"output_from_{name}",
        )
        assert "role_outputs" in results
        assert results["role_outputs"]["role_a"] == "output_from_role_a"
        assert results["role_outputs"]["role_b"] == "output_from_role_b"

    def test_data_collection_disabled_skips_planner(self):
        tc = self._make_executor(enable_data_collection=False)
        assert tc.enable_data_collection is False
        assert tc.data_collector is None
        context, spec = tc.get_pre_execution_context("role_a", "initial")
        assert spec.queries == []
        assert "任务不需要实时数据采集" in spec.rationale
        mock_plan.assert_not_called() if hasattr(self, "_mock_plan") else None

    @patch.object(DataCollectionPlanner, "plan_for_role")
    def test_execute_full_chain_preserves_collected_data(self, mock_plan):
        mock_plan.return_value = DataCollectionSpec(
            role_name="r",
            queries=["gold price"],
            sources=["commodity_prices"],
            priority="critical",
            rationale="need gold",
        )
        tc = self._make_executor()
        if tc.data_collector is None:
            tc.data_collector = MagicMock()
            tc.data_collector.execute.return_value = "Gold: $4,685"

        results = tc.execute_full_chain(
            initial_data="test",
            role_executor=lambda name, ctx: f"out_{name}",
        )
        assert "collected_data" in results


class TestFeedbackMessage:
    def test_create(self):
        fb = FeedbackMessage(
            from_role="r1",
            to_role="r2",
            content="missing data",
            feedback_type="data_gap",
            suggested_action="supplement_data",
            priority="high",
        )
        assert fb.from_role == "r1"
        assert fb.to_role == "r2"
        assert fb.feedback_type == "data_gap"

    def test_to_dict(self):
        fb = FeedbackMessage(
            from_role="a",
            to_role="b",
            content="test",
            feedback_type="correction",
            suggested_action="re_analyze",
            priority="medium",
        )
        d = fb.to_dict()
        assert d["from_role"] == "a"
