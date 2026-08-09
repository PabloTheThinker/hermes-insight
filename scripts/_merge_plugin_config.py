#!/usr/bin/env python3
"""Merge hermes-insight into HERMES_HOME/config.yaml without clobbering plugins.enabled."""

from __future__ import annotations

import re
import sys
from pathlib import Path


def main() -> int:
    if len(sys.argv) < 2:
        print("usage: _merge_plugin_config.py HERMES_HOME [agent_id]", file=sys.stderr)
        return 2
    home = Path(sys.argv[1]).expanduser().resolve()
    agent = (sys.argv[2] if len(sys.argv) > 2 else "").strip()
    cfg_path = home / "config.yaml"
    if not cfg_path.exists():
        print(f"-- no config.yaml at {cfg_path} (plugin copied; enable manually)")
        return 0

    text = cfg_path.read_text(encoding="utf-8")
    original = text
    changed = False

    if "plugins:" not in text:
        text += "\nplugins:\n  enabled:\n    - hermes-insight\n  entries:\n"
        changed = True

    # Ensure hermes-insight is enabled
    if not re.search(r"hermes[-_]insight", text):
        m = re.search(r"(enabled:\s*\[)([^\]]*)(\])", text)
        if m:
            inner = m.group(2).strip()
            new_inner = (inner + ", hermes-insight") if inner else "hermes-insight"
            # clean double commas
            new_inner = re.sub(r",\s*,", ",", new_inner)
            text = text[: m.start(2)] + new_inner + text[m.end(2) :]
            changed = True
        elif re.search(r"^(\s*)enabled:\s*$", text, re.M):
            text = re.sub(
                r"(^(\s*)enabled:\s*\n)",
                r"\1\2  - hermes-insight\n",
                text,
                count=1,
                flags=re.M,
            )
            changed = True
        else:
            # append under plugins
            text = re.sub(
                r"(plugins:\s*\n)",
                r"\1  enabled:\n    - hermes-insight\n",
                text,
                count=1,
            )
            changed = True

    if agent:
        db = home / "memories" / "hermes-insight" / "agents" / f"{agent}.insight.db"
    else:
        db = home / "memories" / "hermes-insight" / "insight.db"
    db.parent.mkdir(parents=True, exist_ok=True)

    entry_lines = ["    hermes-insight:\n"]
    if agent:
        entry_lines.append(f"      agent_id: {agent}\n")
    entry_lines.append(f"      db_path: {db}\n")
    entry_block = "".join(entry_lines)

    # Upsert entries.hermes-insight
    if re.search(r"hermes-insight:\s*\n(?:\s{2,}[a-z_].*\n)*", text):
        # replace existing block roughly
        text2, n = re.subn(
            r"    hermes-insight:\n(?:      .*\n)*",
            entry_block,
            text,
            count=1,
        )
        if n:
            text = text2
            changed = True
    else:
        if re.search(r"entries:\s*\{\}", text):
            text = text.replace("entries: {}", "entries:\n" + entry_block, 1)
            changed = True
        elif re.search(r"entries:\s*$", text, re.M):
            text = re.sub(r"(entries:\s*\n)", r"\1" + entry_block, text, count=1)
            changed = True
        elif "plugins:" in text:
            text = re.sub(
                r"(plugins:\s*\n)",
                r"\1  entries:\n" + entry_block,
                text,
                count=1,
            )
            changed = True

    if text != original and changed:
        bak = cfg_path.with_suffix(cfg_path.suffix + ".bak-insight-install")
        if not bak.exists():
            bak.write_text(original, encoding="utf-8")
        cfg_path.write_text(text, encoding="utf-8")
        print(f"-- config merged (backup {bak.name})")
    else:
        print("-- config left as-is (already wired or no safe merge)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
