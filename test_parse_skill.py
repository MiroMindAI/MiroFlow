#!/usr/bin/env python3
"""
测试脚本：提取 SKILL.md 文件中的 name 和 description
"""

from __future__ import annotations

import re
import sys
from pathlib import Path
from typing import Any, Dict, Tuple

# 修复后的正则表达式：匹配 YAML front matter
# 使用 \A 和 \Z 表示字符串的开始和结束，\s 匹配空白字符
_FRONTMATTER_RE = re.compile(r"\A---\s*\n(.*?)\n---\s*\n(.*)\Z", re.S | re.M)


def _parse_frontmatter(md_text: str) -> Tuple[Dict[str, Any], str]:
    """
    解析 Markdown 文件的 YAML front matter

    Args:
        md_text: Markdown 文件内容

    Returns:
        Tuple[Dict[str, Any], str]: (frontmatter 字典, 正文内容)
    """
    m = _FRONTMATTER_RE.match(md_text)
    if not m:
        raise ValueError("SKILL.md 缺少 frontmatter（必须以 --- 开头并闭合 ---）")

    fm_raw, body = m.group(1), m.group(2)
    meta: Dict[str, Any] = {}

    # 简易行解析
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
            # 去掉包裹引号（简单处理）
            if (val.startswith('"') and val.endswith('"')) or (
                val.startswith("'") and val.endswith("'")
            ):
                val = val[1:-1]
            meta[key] = val

    return meta, body


def test_parse_skill_md(skill_md_path: str):
    """
    测试解析 SKILL.md 文件

    Args:
        skill_md_path: SKILL.md 文件路径
    """
    skill_md = Path(skill_md_path)

    if not skill_md.exists():
        print(f"错误：文件不存在: {skill_md_path}", file=sys.stderr)
        return False

    try:
        # 读取文件内容
        text = skill_md.read_text(encoding="utf-8")
        print("=" * 60)
        print(f"文件路径: {skill_md_path}")
        print("=" * 60)
        print("\n文件内容:")
        print("-" * 60)
        print(text)
        print("-" * 60)

        # 解析 frontmatter
        fm, body = _parse_frontmatter(text)

        # 提取 name 和 description
        name = str(fm.get("name", "")).strip()
        description = str(fm.get("description", "")).strip()

        print("\n解析结果:")
        print("=" * 60)
        print(f"Name: {name}")
        print(f"Description: {description}")
        print("\n所有 frontmatter 字段:")
        for key, value in fm.items():
            print(f"  {key}: {value}")
        print("\n正文内容（前100个字符）:")
        print(body[:100] + "..." if len(body) > 100 else body)
        print("=" * 60)

        # 验证必需字段
        if not name or not description:
            print("警告：缺少必需的字段 'name' 或 'description'", file=sys.stderr)
            return False

        print("\n✓ 解析成功！")
        return True

    except Exception as e:
        print(f"错误：解析失败 - {e}", file=sys.stderr)
        import traceback

        traceback.print_exc()
        return False


if __name__ == "__main__":
    # 默认测试 Math/SKILL.md
    default_path = "src/skill/skills/Math/SKILL.md"

    # 如果提供了命令行参数，使用参数作为路径
    if len(sys.argv) > 1:
        skill_path = sys.argv[1]
    else:
        skill_path = default_path

    success = test_parse_skill_md(skill_path)
    sys.exit(0 if success else 1)
