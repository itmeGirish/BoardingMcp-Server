"""Tests for policy loader schema validation and metadata exposure."""

from __future__ import annotations

import json
from pathlib import Path

from app.agents.drafting_agents.policies import policy_loader


def _policy_file_path() -> Path:
    return (
        Path(__file__).resolve().parents[2]
        / "app"
        / "agents"
        / "drafting_agents"
        / "policies"
        / "legal_quality_policy.json"
    )


class TestPolicyLoader:
    def test_validate_policy_shape_accepts_current_policy(self):
        data = json.loads(_policy_file_path().read_text(encoding="utf-8"))
        errors = policy_loader._validate_policy_shape(data)  # noqa: SLF001
        assert errors == []

    def test_validate_policy_shape_rejects_missing_required_blocks(self):
        bad = {"version": "", "global": {"draft_quality": {}, "sanitizer": {}}}
        errors = policy_loader._validate_policy_shape(bad)  # noqa: SLF001
        assert len(errors) >= 1
        assert any("min_draft_length" in e or "version" in e for e in errors)

    def test_get_quality_policy_exposes_validity_metadata(self, monkeypatch):
        monkeypatch.setattr(
            policy_loader,
            "_load_policy_file",
            lambda: {
                "version": "x",
                "global": {"draft_quality": {}, "sanitizer": {}},
                "__policy_valid": False,
                "__policy_errors": ["schema invalid"],
            },
        )
        out = policy_loader.get_quality_policy(document_type="legal_notice", jurisdiction="Karnataka")
        assert out["policy_valid"] is False
        assert out["policy_errors"] == ["schema invalid"]
        assert out["policy_document_type"] == "legal_notice"
        assert out["policy_jurisdiction"] == "karnataka"
