# SPDX-FileCopyrightText: 2025 MiromindAI
#
# SPDX-License-Identifier: Apache-2.0

"""
Sequential Agent - executes multiple sub-modules in sequence
"""

from miroflow.registry import register, ComponentType
from miroflow.agents.base import BaseAgent
from miroflow.agents.context import AgentContext
from omegaconf import DictConfig, ListConfig, OmegaConf
from typing import List


@register(ComponentType.AGENT, "SequentialAgentModule")
class SequentialAgent(BaseAgent):
    """Sequential execution agent module"""

    def __init__(
        self,
        cfg: DictConfig | ListConfig = {"type": "SequentialAgentModule"},
        modules: List[BaseAgent] = None,
    ):
        super().__init__(cfg)

        # Support both DictConfig (with 'modules' key) and ListConfig (direct list)
        if modules is not None:
            cfgs = [m.cfg for m in modules]
            self.cfg = OmegaConf.create(
                {"type": "SequentialAgentModule", "modules": cfgs}
            )
            self.modules = modules
        else:
            if isinstance(cfg, DictConfig):
                if "modules" not in cfg:
                    raise ValueError(
                        "SequentialAgentModule config must have field `modules`. \n"
                        + str(cfg)
                    )
            else:
                cfg = OmegaConf.create(
                    {"type": "SequentialAgentModule", "modules": cfg}
                )
            self.cfg = cfg

            from miroflow.agents.factory import build_agent

            self.modules = [build_agent(cfg) for cfg in self.cfg.modules]

    async def run_internal(
        self, ctx: AgentContext = {}, *args, **kwargs
    ) -> AgentContext:
        for m in self.modules:
            patch_ctx = await m.run(ctx, *args, **kwargs)
            ctx.update(patch_ctx)
        return ctx

    def __repr__(self):
        _repr_ = f"{self.__class__.__name__}"
        for m in self.modules:
            _repr_ += f"\n{m}"
        return _repr_


# Backward compatible alias
SequentialAgentModule = SequentialAgent
