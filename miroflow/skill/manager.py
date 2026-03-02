from __future__ import annotations

import logging
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)


@dataclass
class SkillMeta:
    skill_id: str
    name: str
    description: str
    root_dir: Path = Path(".")
    skill_md: Path = Path("SKILL.md")


class SkillError(Exception):
    pass


_FRONTMATTER_RE = re.compile(r"\A---\s*\n(.*?)\n---\s*\n(.*)\Z", re.S | re.M)


def _parse_frontmatter(md_text: str) -> Tuple[Dict[str, Any], str]:
    m = _FRONTMATTER_RE.match(md_text)
    if not m:
        raise SkillError(
            "SKILL.md is missing frontmatter (must start and end with ---)"
        )

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


class SkillManager:
    def __init__(
        self,
        skill_dirs: List[Path],
        allow_python_skills: bool = True,
        allowed_skill_ids: Optional[List[str]] = None,
    ):
        """
        allow_python_skills: Whether to allow loading and executing python skills (recommended to keep True but use with whitelist)
        allowed_skill_ids: If provided, only these skill_ids can be executed (strongly recommended for production)
        """
        self.skill_dirs = skill_dirs
        self.allow_python_skills = allow_python_skills
        self.allowed_skill_ids = set(allowed_skill_ids) if allowed_skill_ids else None

        self._index: Dict[str, SkillMeta] = {}  # skill_id -> meta

    def get_all_skills_definitions(self) -> List[SkillMeta]:
        skills_server_params = []
        index = self.discover()
        logger.info("Discovered skills index: %s", index)
        schema = {
            "type": "object",
            "properties": {"subtask": {"title": "Subtask", "type": "string"}},
            "required": ["subtask"],
        }
        for skill in index.values():
            try:
                skill_tool_definition = dict(
                    name="skills-worker",
                    tools=[
                        dict(
                            name=skill.name,
                            description=skill.description,
                            schema=schema,
                        )
                    ],
                )
                skills_server_params.append(skill_tool_definition)
            except Exception as e:
                raise ValueError(f"Failed to expose skill {skill.name} as a tool: {e}")

        return skills_server_params

    def discover(self) -> Dict[str, SkillMeta]:
        """
        Scan directories and parse the frontmatter of each SKILL.md (loads metadata only, not body/resources)
        """
        index: Dict[str, SkillMeta] = {}

        for skill_dir in self.skill_dirs:
            skill_dir = Path(skill_dir)
            if not skill_dir.is_dir():
                continue
            skill_md = skill_dir / "SKILL.md"
            if not skill_md.exists():
                continue

            try:
                text = skill_md.read_text(encoding="utf-8")
                fm, _body = _parse_frontmatter(text)

                name = str(fm.get("name", "")).strip()
                desc = str(fm.get("description", "")).strip()
                if not name or not desc:
                    raise SkillError("frontmatter must contain name and description")

                meta = SkillMeta(
                    skill_id=skill_dir.name,
                    name=name,
                    description=desc,
                    root_dir=skill_dir,
                    skill_md=skill_md,
                )
                index[meta.skill_id] = meta
            except Exception as e:
                logger.warning("Failed to load skill meta from %s: %s", skill_md, e)

        self._index = index
        return index

    def list(self) -> List[SkillMeta]:
        return sorted(self._index.values(), key=lambda m: m.skill_id)

    def get(self, skill_id: str) -> SkillMeta:
        if skill_id not in self._index:
            raise SkillError(f"Skill not found: {skill_id}")
        return self._index[skill_id]

    def load(self, skill_id: str) -> str:
        # step1: push total skill.md to agent
        meta = self.get(skill_id)

        if (
            self.allowed_skill_ids is not None
            and meta.skill_id not in self.allowed_skill_ids
        ):
            raise SkillError(
                f"Skill '{meta.skill_id}' is not in the allowed_skill_ids whitelist, loading denied."
            )

        text = meta.skill_md.read_text(encoding="utf-8")
        _, body = _parse_frontmatter(text)

        return body

    def execute_skill_command(self, skill_id: str, run_command: str) -> Dict[str, Any]:
        raise NotImplementedError("Skill command execution is not yet supported")

    async def execute_skill_calls_batch(
        self, skill_calls: Tuple[Dict[str, Any]], max_skill_calls: int = 10
    ) -> Tuple[List[Tuple[str, Any]], bool]:
        """
        Execute a batch of skill calls.
        :param skill_calls: Tuple of skill calls
        :param max_skill_calls: Maximum number of skill calls to execute
        :return: Tuple of skill call results and whether the skill calls exceeded the limit
        """
        if len(skill_calls) > max_skill_calls:
            skill_calls = skill_calls[:max_skill_calls]
            exceeded = True
        else:
            exceeded = False

        results = []
        for skill_call in skill_calls:
            call_id = skill_call["id"]
            server_name = skill_call["server_name"]
            skill_name = skill_call["tool_name"]
            result = self.load(skill_id=skill_name)
            result = {
                "server_name": server_name,
                "tool_name": skill_name,
                "result": result,
            }
            # TODO error process
            results.append((call_id, result))

        return results, exceeded
