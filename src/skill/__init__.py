# SPDX-FileCopyrightText: 2025 MiromindAI
#
# SPDX-License-Identifier: Apache-2.0

"""
Skill 模块

注意：Skill 不走注册机制，而是通过文件系统扫描发现
"""

from src.skill.manager import SkillManager, SkillMeta, SkillError

__all__ = [
    "SkillManager",
    "SkillMeta",
    "SkillError",
]
