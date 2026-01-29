#!/usr/bin/env python3
"""
Test script: Extract name and description from SKILL.md files
"""

from __future__ import annotations

import re
import sys
from pathlib import Path
from typing import Any, Dict, Tuple

# Regex pattern to match YAML front matter
# Uses \A and \Z for string start/end, \s matches whitespace
_FRONTMATTER_RE = re.compile(r"\A---\s*\n(.*?)\n---\s*\n(.*)\Z", re.S | re.M)


def _parse_frontmatter(md_text: str) -> Tuple[Dict[str, Any], str]:
    """
    Parse YAML front matter from a Markdown file

    Args:
        md_text: Markdown file content

    Returns:
        Tuple[Dict[str, Any], str]: (frontmatter dict, body content)
    """
    m = _FRONTMATTER_RE.match(md_text)
    if not m:
        raise ValueError("SKILL.md missing frontmatter (must start with --- and close with ---)")

    fm_raw, body = m.group(1), m.group(2)
    meta: Dict[str, Any] = {}

    # Simple line-by-line parsing
    lines = fm_raw.splitlines()
    i = 0
    while i < len(lines):
        line = lines[i].rstrip()
        i += 1
        if not line.strip() or line.strip().startswith("#"):
            continue

        # list block: key:
        if re.match(r"^[A-Za-z_][A-Za-z0-9_-]*:\s*$", line):
            key = line.split(":")[0].strip()
            items = []
            while i < len(lines):
                li = lines[i].rstrip()
                if not li.strip():
                    i += 1
                    continue
                if re.match(r"^[A-Za-z_][A-Za-z0-9_-]*:\s*", li):
                    break
                mm = re.match(r"^\s*-\s*(.+?)\s*$", li)
                if mm:
                    items.append(mm.group(1))
                    i += 1
                    continue
                # fallback: stop
                break
            meta[key] = items
            continue

        # key: value
        mm = re.match(r"^([A-Za-z_][A-Za-z0-9_-]*)\s*:\s*(.+)\s*$", line)
        if not mm:
            continue

        key, val = mm.group(1), mm.group(2).strip()
        # tags: [a, b]
        if val.startswith("[") and val.endswith("]"):
            inner = val[1:-1].strip()
            meta[key] = [x.strip() for x in inner.split(",") if x.strip()]
        else:
            # Remove wrapping quotes (simple handling)
            if (val.startswith('"') and val.endswith('"')) or (
                val.startswith("'") and val.endswith("'")
            ):
                val = val[1:-1]
            meta[key] = val

    return meta, body


def test_parse_skill_md(skill_md_path: str):
    """
    Test parsing a SKILL.md file

    Args:
        skill_md_path: Path to SKILL.md file
    """
    skill_md = Path(skill_md_path)

    if not skill_md.exists():
        print(f"Error: File not found: {skill_md_path}", file=sys.stderr)
        return False

    try:
        # Read file content
        text = skill_md.read_text(encoding="utf-8")
        print("=" * 60)
        print(f"File path: {skill_md_path}")
        print("=" * 60)
        print("\nFile content:")
        print("-" * 60)
        print(text)
        print("-" * 60)

        # Parse frontmatter
        fm, body = _parse_frontmatter(text)

        # Extract name and description
        name = str(fm.get("name", "")).strip()
        description = str(fm.get("description", "")).strip()

        print("\nParse result:")
        print("=" * 60)
        print(f"Name: {name}")
        print(f"Description: {description}")
        print("\nAll frontmatter fields:")
        for key, value in fm.items():
            print(f"  {key}: {value}")
        print("\nBody content (first 100 characters):")
        print(body[:100] + "..." if len(body) > 100 else body)
        print("=" * 60)

        # Validate required fields
        if not name or not description:
            print("Warning: Missing required field 'name' or 'description'", file=sys.stderr)
            return False

        print("\n✓ Parse successful!")
        return True

    except Exception as e:
        print(f"Error: Parse failed - {e}", file=sys.stderr)
        import traceback

        traceback.print_exc()
        return False


if __name__ == "__main__":
    # Default test with Math/SKILL.md
    default_path = "src/skill/skills/Math/SKILL.md"

    # If command line argument provided, use it as path
    if len(sys.argv) > 1:
        skill_path = sys.argv[1]
    else:
        skill_path = default_path

    success = test_parse_skill_md(skill_path)
    sys.exit(0 if success else 1)
