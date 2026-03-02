# SPDX-FileCopyrightText: 2025 MiromindAI
#
# SPDX-License-Identifier: Apache-2.0

"""
Agent base class module
"""

import json
from omegaconf import DictConfig, OmegaConf

from abc import ABC, abstractmethod


from miroflow.tool.manager import ToolManager
from miroflow.llm import build_llm_client
from typing import Optional, Any
from miroflow.logging.decorators import span
from miroflow.utils.prompt_utils import PromptManager
from miroflow.utils.tool_utils import expose_sub_agents_as_tools
from miroflow.skill.manager import SkillManager
from miroflow.agents.context import AgentContext


class BaseAgent(ABC):
    """Agent base class"""

    USE_PROPAGATE_MODULE_CONFIGS = ("llm", "tools", "prompt")
    _instance_counters = {}

    def __init_subclass__(cls, **kwargs):
        super().__init_subclass__(**kwargs)

    @classmethod
    def get_instance_count(cls):
        return cls._instance_counters.get(cls.__name__, 0)

    @classmethod
    def get_instance_name(cls, cfg):
        if cfg is not None and "name" in cfg:
            return cfg["name"]
        else:
            return f"{cls.__name__}_call_{cls.get_instance_count()}"

    def create_sub_module(self, sub_agent_cfg: DictConfig | dict, name: str = None):
        from miroflow.agents.factory import build_agent

        sub_agent_cfg = OmegaConf.create(sub_agent_cfg)

        propagated = {
            k: self.cfg[k]
            for k in self.USE_PROPAGATE_MODULE_CONFIGS
            if k in self.cfg and k not in sub_agent_cfg
        }

        merged_cfg = OmegaConf.merge(sub_agent_cfg, propagated)
        return build_agent(merged_cfg)

    def __init__(self, cfg: Optional[DictConfig | dict] = None, parent=None):
        self._parent = parent
        self.name = self.get_instance_name(cfg)
        self.__class__._instance_counters[self.__class__.__name__] = (
            self.get_instance_count() + 1
        )

        if isinstance(cfg, dict):
            cfg = DictConfig(cfg)
        self.cfg = cfg

        # if hasattr(self.cfg, "llm") and not hasattr(self, "llm_client"):
        self.llm_client = build_llm_client(cfg=self.cfg.get("llm"))
        self.prompt_manager = PromptManager(config_path=self.cfg.get("prompt"))
        self.sub_agents = self.cfg.get("sub_agents")

        # Parse tool_blacklist from config
        tool_blacklist = self._parse_tool_blacklist(self.cfg.get("tool_blacklist"))
        self.tool_manager = ToolManager(
            cfg=self.cfg.get("tools"), tool_blacklist=tool_blacklist
        )
        self.skill_manager = SkillManager(skill_dirs=self.cfg.get("skills"))

    def _parse_tool_blacklist(self, blacklist_cfg) -> set:
        """
        Parse tool_blacklist config into a set of (server_name, tool_name) tuples.

        Config format:
            tool_blacklist:
              - server: "tool-code"
                tool: "create_sandbox"
              - server: "tool-search-and-scrape-webpage"
                tool: "sogou_search"

        Returns:
            Set of (server_name, tool_name) tuples
        """
        if not blacklist_cfg:
            return set()

        blacklist = set()
        for item in blacklist_cfg:
            # Handles both regular dict and OmegaConf DictConfig
            if hasattr(item, "get") and item.get("server") and item.get("tool"):
                blacklist.add((str(item.get("server")), str(item.get("tool"))))
        return blacklist

    @abstractmethod
    async def run_internal(self, ctx: AgentContext) -> AgentContext:
        pass

    @span()
    async def run(self, ctx: AgentContext) -> AgentContext:
        await self.post_initialize()
        ret = await self.run_internal(ctx)
        return ret

    async def run_as_mcp_tool(
        self, ctx: AgentContext, return_ctx_key: str
    ) -> AgentContext:
        ret = await self.run(ctx)
        if return_ctx_key in ret:
            return {
                "server_name": "AgentWorker",
                "tool_name": "execute_subtask",
                "result": ret[return_ctx_key],
            }
        else:
            raise ValueError(
                f"Return context key '{return_ctx_key}' not found in result"
            )

    async def post_initialize(self):
        await self.init_tool_definitions()

    @staticmethod
    def get_mcp_server_definitions_from_tool_definitions(
        tool_definitions: list[dict[str, Any]],
    ) -> str:
        mcp_server_definitions = ""
        if tool_definitions and len(tool_definitions) > 0:
            for server in tool_definitions:
                mcp_server_definitions += f"\n## Server name: {server['name']}\n"
                if "tools" in server and len(server["tools"]) > 0:
                    for tool in server["tools"]:
                        mcp_server_definitions += f"\n### Tool name: {tool['name']}\n"
                        mcp_server_definitions += (
                            f"Description: {tool['description']}\n"
                        )
                        mcp_server_definitions += (
                            f"\nInput JSON schema: {tool['schema']}\n"
                        )
        return mcp_server_definitions

    async def init_tool_definitions(self):
        if (
            hasattr(self.cfg, "tools")
            or hasattr(self.cfg, "sub_agents")
            or hasattr(self.cfg, "skills")
        ):
            if hasattr(self.cfg, "tools"):
                tool_definitions = await self.tool_manager.get_all_tool_definitions()
                tool_mcp_server_definitions = (
                    self.get_mcp_server_definitions_from_tool_definitions(
                        tool_definitions
                    )
                )
            else:
                tool_definitions, tool_mcp_server_definitions = [], ""
            if hasattr(self.cfg, "sub_agents") and len(self.cfg["sub_agents"]) > 0:
                sub_agent_names = self.cfg["sub_agents"].keys()
                subagent_as_tool_definitions = expose_sub_agents_as_tools(
                    sub_agent_names
                )
                sub_agent_mcp_server_definitions = (
                    self.get_mcp_server_definitions_from_tool_definitions(
                        subagent_as_tool_definitions
                    )
                )
            else:
                subagent_as_tool_definitions, sub_agent_mcp_server_definitions = [], ""
            if hasattr(self.cfg, "skills"):
                skills_as_tool_definitions = (
                    self.skill_manager.get_all_skills_definitions()
                )
                skills_mcp_server_definitions = (
                    self.get_mcp_server_definitions_from_tool_definitions(
                        skills_as_tool_definitions
                    )
                )
            else:
                skills_as_tool_definitions, skills_mcp_server_definitions = [], ""
            self.tool_definitions = (
                tool_definitions
                + subagent_as_tool_definitions
                + skills_as_tool_definitions
            )
            self.mcp_server_definitions = (
                tool_mcp_server_definitions
                + sub_agent_mcp_server_definitions
                + skills_mcp_server_definitions
            )
        else:
            self.tool_definitions = []
            self.mcp_server_definitions = []

    async def run_sub_agents_as_mcp_tools(
        self, sub_agent_calls: list[dict]
    ) -> list[tuple[str, dict]]:
        # check if sub-agents are valid
        for call in sub_agent_calls:
            if call["server_name"] not in self.sub_agents:
                raise ValueError(
                    f"Sub-agent {call['server_name']} not found in sub-agents"
                )
        sub_agent_results = []
        for agent_call in sub_agent_calls:
            # dynamic initialization of sub-agent
            sub_agent = self.create_sub_module(
                self.sub_agents[agent_call["server_name"]], name="sub_agent"
            )
            sub_agent_result = await sub_agent.run_as_mcp_tool(
                AgentContext(task_description=agent_call["arguments"]),
                return_ctx_key="summary",
            )
            sub_agent_results.append((agent_call["id"], sub_agent_result))
        return sub_agent_results

    @classmethod
    def build(cls, cfg: DictConfig | dict):
        instance = cls(cfg)
        return instance

    def __repr__(self):
        container = OmegaConf.to_container(self.cfg, resolve=True)
        cfg_str = json.dumps(container, indent=2)
        return f"{self.__class__.__name__}(cfg={cfg_str})"
