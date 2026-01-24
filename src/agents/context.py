# SPDX-FileCopyrightText: 2025 MiromindAI
#
# SPDX-License-Identifier: Apache-2.0

"""
Agent 上下文模块 - 用于在 Agent 之间传递信息
"""


class AgentContext(dict):
    """
    Agent 上下文类

    继承自 dict，用于在 Agent 执行过程中传递和存储上下文信息。
    支持动态添加和访问属性。
    """

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
