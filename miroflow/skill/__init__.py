# SPDX-FileCopyrightText: 2025 MiromindAI
#
# SPDX-License-Identifier: Apache-2.0

"""
Skill module

Note: Skills are discovered through file system scanning, not the registry
"""

from miroflow.skill.manager import SkillManager, SkillMeta, SkillError

__all__ = [
    "SkillManager",
    "SkillMeta",
    "SkillError",
]
