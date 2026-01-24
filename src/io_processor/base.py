# SPDX-FileCopyrightText: 2025 MiromindAI
#
# SPDX-License-Identifier: Apache-2.0

"""
IO 处理器基类

IO 处理器是一种特殊的 Agent，专门用于处理输入和输出。
它们继承自 BaseAgent，但有特定的用途。
"""

from src.agents.base import BaseAgent


class BaseIOProcessor(BaseAgent):
    """
    IO 处理器基类

    IO 处理器用于：
    - 输入处理：生成提示、处理用户输入
    - 输出处理：生成摘要、提取最终答案
    """

    pass
