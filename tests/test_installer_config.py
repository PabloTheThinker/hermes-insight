"""Plugin config merge preserves enablement and unrelated settings."""

from __future__ import annotations

import importlib.util
from pathlib import Path

import pytest


SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "_merge_plugin_config.py"
SPEC = importlib.util.spec_from_file_location("merge_plugin_config", SCRIPT)
assert SPEC and SPEC.loader
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


def test_existing_entry_does_not_mask_missing_enablement(tmp_path: Path):
    original = """model:
  default: local/test
plugins:
  enabled:
    - another-plugin
  entries:
    hermes-insight:
      db_path: "/old/path.db"
"""
    merged = MODULE.merge_config(original, tmp_path, "worker")
    assert "    - another-plugin" in merged
    assert "    - hermes-insight" in merged
    assert merged.count("    hermes-insight:") == 1
    assert 'agent_id: "worker"' in merged
    assert "model:\n  default: local/test" in merged


def test_inline_enablement_is_extended_once(tmp_path: Path):
    original = "plugins:\n  enabled: [alpha]\n  entries: {}\n"
    merged = MODULE.merge_config(original, tmp_path)
    assert "enabled: [alpha, hermes-insight]" in merged
    again = MODULE.merge_config(merged, tmp_path)
    assert again.count("enabled: [alpha, hermes-insight]") == 1
    assert again.count("    hermes-insight:") == 1


def test_empty_config_is_created_and_agent_id_is_sanitized(tmp_path: Path):
    merged = MODULE.merge_config("", tmp_path, "../../Client One")
    assert "plugins:" in merged
    assert "    - hermes-insight" in merged
    assert "    hermes-insight:" in merged
    assert 'agent_id: "client-one"' in merged
    assert ".." not in merged


def test_unsupported_inline_plugin_mapping_fails_without_rewrite(tmp_path: Path):
    with pytest.raises(ValueError, match="inline plugins mapping"):
        MODULE.merge_config("plugins: {enabled: [alpha]}\n", tmp_path)
