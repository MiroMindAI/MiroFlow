from src.agents.registry import register_module, build_agent
from src.agents.base_module import BaseAgentModule
from omegaconf import DictConfig, ListConfig, OmegaConf
from typing import List

@register_module("SequentialAgentModule")
class SequentialAgentModule(BaseAgentModule):
    def __init__(self, cfg: DictConfig | ListConfig = {'type': 'SequentialAgentModule'}, modules: List[BaseAgentModule] = None):
        super().__init__(cfg)
        # Support both DictConfig (with 'modules' key) and ListConfig (direct list)
        if modules is not None:
            cfgs = [m.cfg for m in modules]
            self.cfg = OmegaConf.create(
                {'type': 'SequentialAgentModule', 
                'modules': cfgs}
            )
            self.modules = modules
        else:
            if isinstance(cfg, DictConfig):
                if 'modules' not in cfg:
                    raise ValueError(f"SequentialAgentModule config must have field `modules`. \n" + str(cfg))
            else:
                cfg = OmegaConf.create({
                    'type': 'SequentialAgentModule',
                    'modules': cfg
                })
            self.cfg = cfg
            self.modules = [build_agent(cfg) for cfg in self.cfg.modules]

    async def run_internal(self, ctx = {}, *args, **kwargs):
        for m in self.modules:
            patch_ctx = await m.run(ctx, *args, **kwargs)
            ctx.update(patch_ctx) #TODO: ctx updating strategy
        return ctx

    def __repr__(self):
        _repr_ = f"{self.__class__.__name__}"
        for m in self.modules:
            _repr_ += f"\n{m}"
        return _repr_