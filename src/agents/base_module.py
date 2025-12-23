from pdb import run
import json
from omegaconf import DictConfig

from abc import ABC, abstractmethod

from pydantic import NonNegativeInt

from src.tool.manager import ToolManager
from src.llm.provider_client_base import build_llm_client
from typing import List, Optional
from omegaconf import DictConfig
from src.logging.decorators import span
from typing import Any
from src.utils.prompt_manager import PromptTemplateReader
from types import MappingProxyType
from immutables import Map
from omegaconf import OmegaConf 
from src.tool.manager import get_mcp_server_configs_from_tool_cfg_paths
from hydra import compose, initialize
from omegaconf import ListConfig
from src.utils.tool_utils import expose_sub_agents_as_tools



class AgentContextDict(dict):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
    
class BaseAgentModule(ABC):
    USE_PROPAGATE_MODULE_CONFIGS = ("llm", "tools", "prompt")
    _instance_counters = {}

    def __init_subclass__(cls, **kwargs):
        super().__init_subclass__(**kwargs)
    
    @classmethod
    def get_instance_count(cls):
        return cls._instance_counters.get(cls.__name__, 0)

    @classmethod
    def get_instance_name(cls, cfg):
        #if cfg is not None and 'name' in cfg:
        #return cfg['name']
        #else:
        return f"{cls.__name__}_call_{cls.get_instance_count()}"

    def create_sub_module(self, sub_agent_cfg: DictConfig | dict, name: str = None):
        from src.agents.registry import build_agent

        sub_agent_cfg = OmegaConf.create(sub_agent_cfg)

        propagated = {
            k: self.cfg[k]
            for k in self.USE_PROPAGATE_MODULE_CONFIGS
            if k in self.cfg and k not in sub_agent_cfg
        }

        merged_cfg = OmegaConf.merge(sub_agent_cfg, propagated)
        return build_agent(merged_cfg)

    #@property
    def __init__(self, cfg: Optional[DictConfig | dict] = None, parent = None):
        #assert isinstance(self.PROPAGATE_MODULE_CONFIGS, tuple), "PROPAGATE_MODULE_CONFIGS must be a tuple"
        
        self._parent = parent
        self.name = self.get_instance_name(cfg)
        self.__class__._instance_counters[self.__class__.__name__] = self.get_instance_count() + 1

        if isinstance(cfg, dict):
            cfg = DictConfig(cfg)
        self.cfg = cfg
    
        if hasattr(self.cfg, "llm") and not hasattr(self, "llm_client"):
            self.llm_client = build_llm_client(llm_config=self.cfg.get("llm"))
        if not hasattr(self, "tool_manager"):
            if not hasattr(self.cfg, "tools"):
                self.cfg.tools = OmegaConf.create([])
            mcp_server_configs = get_mcp_server_configs_from_tool_cfg_paths(
                cfg_paths = self.cfg.tools
            )
            self.tool_manager = ToolManager(mcp_server_configs)
        if hasattr(self.cfg, "prompt") and not hasattr(self, "prompt_manager"):
            self.prompt_manager = PromptTemplateReader(config_path = self.cfg.prompt)
        
        self.sub_agents = self.cfg.get('sub_agents')

            
    @abstractmethod
    async def run_internal(self, ctx: AgentContextDict) -> AgentContextDict:
        pass
    
    @span()
    async def run(self, ctx: AgentContextDict) -> AgentContextDict:
        await self.post_initialize()
        ret = await self.run_internal(ctx)
        return ret

    async def run_as_mcp_tool(self, ctx: AgentContextDict, return_ctx_key: str) -> AgentContextDict:
        ret = await self.run(ctx)
        if return_ctx_key in ret:
            return {
                'server_name': 'AgentWorker', #TODO
                'tool_name': 'execute_subtask',
                'result': ret[return_ctx_key]
            }
        else:
            raise ValueError(f"Return context key '{return_ctx_key}' not found in result")

    async def post_initialize(self):
        await self.init_tool_definitions()

    @staticmethod
    def get_mcp_server_definitions_from_tool_definitions(tool_definitions: list[dict[str, Any]]) -> str:
        mcp_server_definitions = ""
        if tool_definitions and len(tool_definitions) > 0:
            for server in tool_definitions:
                mcp_server_definitions += f"## Server name: {server['name']}\n"
                if "tools" in server and len(server["tools"]) > 0:
                    for tool in server["tools"]:
                        mcp_server_definitions += f"### Tool name: {tool['name']}\n"
                        mcp_server_definitions += f"Description: {tool['description']}\n"
        return mcp_server_definitions
            #actions
    
    async def init_tool_definitions(self):
        if hasattr(self.cfg, "tools") or hasattr(self.cfg, "sub_agents"):
            if hasattr(self.cfg, "tools"):
                tool_definitions = await self.tool_manager.get_all_tool_definitions()
                tool_mcp_server_definitions = self.get_mcp_server_definitions_from_tool_definitions(tool_definitions)
            else:
                tool_definitions, tool_mcp_server_definitions = [], ""
            if hasattr(self.cfg, "sub_agents") and len(self.cfg['sub_agents']) > 0:
                sub_agent_names = self.cfg['sub_agents'].keys()
                subagent_as_tool_definitions = expose_sub_agents_as_tools(sub_agent_names)
                sub_agent_mcp_server_definitions = self.get_mcp_server_definitions_from_tool_definitions(subagent_as_tool_definitions)
            else:
                subagent_as_tool_definitions, sub_agent_mcp_server_definitions = [], ""
            self.tool_definitions = tool_definitions + subagent_as_tool_definitions
            self.mcp_server_definitions = tool_mcp_server_definitions + sub_agent_mcp_server_definitions
        else:
            self.tool_definitions = []
            self.mcp_server_definitions = []

    async def run_sub_agents_as_mcp_tools(self, sub_agent_calls: list[dict]) -> list[tuple[str, dict]]:
        #check if sub-agents are valid
        for call in sub_agent_calls:
            if call['server_name'] not in self.sub_agents:
                raise ValueError(f"Sub-agent {call['server_name']} not found in sub-agents")
        sub_agent_results = []
        for agent_call in sub_agent_calls:
            #dynamic initialization of sub-agent
            sub_agent = self.create_sub_module(self.sub_agents[agent_call['server_name']], name = 'sub_agent') #TODO 区分不同subagent
            sub_agent_result = await sub_agent.run_as_mcp_tool(AgentContextDict(
                task_description = agent_call['arguments']
            ), return_ctx_key = 'summary')
            sub_agent_results.append((agent_call['id'], sub_agent_result))
        return sub_agent_results

    
    @classmethod
    def build(cls, cfg: DictConfig | dict):
        instance = cls(cfg)
        #await instance.initialize()
        return instance

    def __repr__(self):
        container = OmegaConf.to_container(self.cfg, resolve=True)
        cfg_str = json.dumps(container, indent=2)
        return f"{self.__class__.__name__}(cfg={cfg_str})"



