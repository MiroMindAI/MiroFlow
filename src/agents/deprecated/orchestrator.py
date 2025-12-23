# from src.agents.registry import register_module
# from src.agents.base_module import BaseAgentModule
# from src.agents.modules.sequential import Sequential
# from omegaconf import DictConfig
# from typing import List
# from src.logging.decorators import span_decorator

# class Orchestrator:
#     def __init__(self):
#         pass

#     async def apply_patch(self, ctx, patch_ctx):
#         #async with self.lock: 
#         for key, value in patch_ctx.items():
#             if key in ctx:
#                 ctx[key] = value
#             else:
#                 ctx[key] = value
#         return ctx

#     async def run_node(self, module, ctx = {}, *args, **kwargs):
#         patch_ctx = await span_decorator(name=f"{module.__class__.__name__}:run")(module.run)(ctx, *args, **kwargs)
#         await self.apply_patch(ctx, patch_ctx)
#         return ctx

#     async def run_workflow(self, workflow, ctx = {}, *args, **kwargs):
#         for module in workflow.modules:
#             patch_ctx = await span_decorator(name=f"{module.__class__.__name__}:run")(module.run)(ctx, *args, **kwargs)
#             await self.apply_patch(ctx, patch_ctx)
#         return ctx

#     async def run(self, entity, ctx = {}, *args, **kwargs):
#         if isinstance(entity, Sequential):
#             return await self.run_workflow(entity, ctx, *args, **kwargs)
#         elif isinstance(entity, BaseAgentModule):
#             return await self.run_node(entity, ctx, *args, **kwargs)
#         else:
#             raise ValueError("Invalid entity type")

