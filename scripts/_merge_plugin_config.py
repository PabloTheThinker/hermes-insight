#!/usr/bin/env python3
"""Merge hermes-insight into HERMES_HOME/config.yaml without clobbering plugins.enabled."""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path


def _safe_agent_id(value: str) -> str:
    cleaned = re.sub(r"[^a-zA-Z0-9._-]+", "-", value.strip().lower())
    return cleaned.strip("-._")[:64]


def _enabled_plugins(text: str) -> set[str] | None:
    """Parse enabled plugins when PyYAML is available, without rewriting config."""
    try:
        import yaml  # type: ignore

        data = yaml.safe_load(text) or {}
    except Exception:
        inline = re.search(r"(?m)^  enabled:\s*\[([^\]]*)\]", text)
        if inline:
            return {
                item.strip().strip("\"'").replace("_", "-")
                for item in inline.group(1).split(",")
                if item.strip()
            }
        block = re.search(
            r"(?ms)^  enabled:\s*\n((?:    - .*\n?)*)",
            text,
        )
        if block:
            return {
                match.group(1).strip().strip("\"'").replace("_", "-")
                for match in re.finditer(r"(?m)^    -\s+(.+?)\s*$", block.group(1))
            }
        return set()
    if not isinstance(data, dict):
        return set()
    plugins = data.get("plugins") or {}
    if not isinstance(plugins, dict):
        return set()
    enabled = plugins.get("enabled") or []
    if isinstance(enabled, str):
        enabled = [enabled]
    if not isinstance(enabled, list):
        return set()
    return {str(item).strip().replace("_", "-") for item in enabled}


def _ensure_enabled(text: str) -> str:
    plugin_key = re.search(r"(?m)^plugins:[ \t]*(.*)$", text)
    if plugin_key and plugin_key.group(1).strip() not in {"", "{}"}:
        raise ValueError(
            "unsupported inline plugins mapping; expand `plugins:` to a YAML block"
        )
    enabled = _enabled_plugins(text)
    if enabled is not None and "hermes-insight" in enabled:
        return text
    if re.search(r"(?m)^plugins:[ \t]*\{\}[ \t]*$", text):
        return re.sub(
            r"(?m)^plugins:[ \t]*\{\}[ \t]*$",
            "plugins:\n  enabled:\n    - hermes-insight\n  entries: {}",
            text,
            count=1,
        )
    if not re.search(r"(?m)^plugins:[ \t]*(?:#.*)?$", text):
        return text.rstrip() + "\n\nplugins:\n  enabled:\n    - hermes-insight\n  entries: {}\n"

    inline = re.search(r"(?m)^  enabled:\s*\[([^\]]*)\]\s*(?:#.*)?$", text)
    if inline:
        inner = inline.group(1).strip()
        replacement = (inner + ", hermes-insight") if inner else "hermes-insight"
        return text[: inline.start(1)] + replacement + text[inline.end(1) :]

    block = re.search(r"(?m)^  enabled:\s*$", text)
    if block:
        line_end = text.find("\n", block.end())
        insert_at = len(text) if line_end < 0 else line_end + 1
        return text[:insert_at] + "    - hermes-insight\n" + text[insert_at:]

    plugin_line = re.search(r"(?m)^plugins:[ \t]*(?:#.*)?$", text)
    assert plugin_line is not None
    line_end = text.find("\n", plugin_line.end())
    insert_at = len(text) if line_end < 0 else line_end + 1
    return text[:insert_at] + "  enabled:\n    - hermes-insight\n" + text[insert_at:]


def merge_config(text: str, home: Path, agent: str = "") -> str:
    """Merge one plugin entry while preserving unrelated config text and comments."""
    agent = _safe_agent_id(agent)
    text = _ensure_enabled(text)
    if agent:
        db = home / "memories" / "hermes-insight" / "agents" / f"{agent}.insight.db"
    else:
        db = home / "memories" / "hermes-insight" / "insight.db"
    db.parent.mkdir(parents=True, exist_ok=True)

    entry_lines = ["    hermes-insight:\n"]
    if agent:
        entry_lines.append(f"      agent_id: {json.dumps(agent)}\n")
    entry_lines.append(f"      db_path: {json.dumps(str(db))}\n")
    entry_block = "".join(entry_lines)

    if re.search(r"(?m)^    hermes-insight:\s*$", text):
        text = re.sub(
            r"(?m)^    hermes-insight:\s*\n(?:      .*\n)*",
            entry_block,
            text,
            count=1,
        )
    elif re.search(r"(?m)^  entries:\s*\{\}\s*$", text):
        text = re.sub(
            r"(?m)^  entries:\s*\{\}\s*$",
            "  entries:\n" + entry_block.rstrip("\n"),
            text,
            count=1,
        )
    elif re.search(r"(?m)^  entries:\s*$", text):
        text = re.sub(
            r"(?m)^(  entries:\s*\n)",
            r"\1" + entry_block,
            text,
            count=1,
        )
    else:
        plugin_line = re.search(r"(?m)^plugins:[ \t]*(?:#.*)?$", text)
        if plugin_line:
            line_end = text.find("\n", plugin_line.end())
            insert_at = len(text) if line_end < 0 else line_end + 1
            text = text[:insert_at] + "  entries:\n" + entry_block + text[insert_at:]
    return text if text.endswith("\n") else text + "\n"


def main() -> int:
    if len(sys.argv) < 2:
        print("usage: _merge_plugin_config.py HERMES_HOME [agent_id]", file=sys.stderr)
        return 2
    home = Path(sys.argv[1]).expanduser().resolve()
    agent = _safe_agent_id(sys.argv[2] if len(sys.argv) > 2 else "")
    cfg_path = home / "config.yaml"
    text = cfg_path.read_text(encoding="utf-8") if cfg_path.exists() else ""
    original = text
    try:
        text = merge_config(text, home, agent)
    except ValueError as exc:
        print(f"-- config merge refused: {exc}", file=sys.stderr)
        return 1

    if text != original:
        bak = cfg_path.with_suffix(cfg_path.suffix + ".bak-insight-install")
        if original and not bak.exists():
            bak.write_text(original, encoding="utf-8")
        cfg_path.write_text(text, encoding="utf-8")
        backup_note = f" (backup {bak.name})" if original else ""
        print(f"-- config merged{backup_note}")
    else:
        print("-- config left as-is (already wired or no safe merge)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
