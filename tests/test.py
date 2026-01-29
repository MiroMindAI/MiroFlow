from __future__ import annotations

import re
from pathlib import Path
from typing import Any, Dict, Tuple

from src.skill import SkillError

_FRONTMATTER_RE = re.compile(r"\A---\s*\n(.*?)\n---\s*\n(.*)\Z", re.S | re.M)


def _parse_frontmatter(md_text: str) -> Tuple[Dict[str, Any], str]:
    m = _FRONTMATTER_RE.match(md_text)
    if not m:
        raise SkillError("SKILL.md missing frontmatter (must start with --- and close with ---)")

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


skill_md = Path("src/skill/skills/Math/SKILL.md")
text = skill_md.read_text(encoding="utf-8")
print(repr(text))
fm, _body = _parse_frontmatter(text)
print(fm)
