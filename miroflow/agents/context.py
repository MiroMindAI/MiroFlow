# SPDX-FileCopyrightText: 2025 MiromindAI
#
# SPDX-License-Identifier: Apache-2.0

"""
Agent context module - for passing information between Agents
"""


class AgentContext(dict):
    """
    Agent context class

    Inherits from dict, used to pass and store context information during Agent execution.
    Supports dynamic attribute addition and access.
    """

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
