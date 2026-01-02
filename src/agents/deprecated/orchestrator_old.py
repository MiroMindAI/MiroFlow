import pathlib
import traceback
import os
import contextvars
from dataclasses import dataclass, field
from datetime import datetime
from omegaconf import DictConfig

from src.agents.agent_node import AgentNode, TaskInput, AgentCaller
from src.logging.logger import setup_logger
from src.logging.task_tracer import TaskTracer

LOGGER_LEVEL = os.getenv("LOGGER_LEVEL", "INFO")
logger = setup_logger(level=LOGGER_LEVEL)

@dataclass
class TaskRunContext:
    task_log: TaskTracer
    called_counter: dict[str, int] = field(default_factory=dict)

_current_task_context: contextvars.ContextVar[TaskRunContext | None] = contextvars.ContextVar(
    'current_task_context', default=None
)

def get_current_task_log() -> TaskTracer | None:
    ctx = _current_task_context.get()
    return ctx.task_log if ctx else None

def get_current_task_context() -> TaskRunContext | None:
    return _current_task_context.get()

class Orchestrator:  
    def __init__(self, cfg: DictConfig):
        self.cfg = cfg
        self.agent_nodes = {}
        
        for agent_name, agent_cfg in self.cfg.agent_nodes.items():
            self.agent_nodes[agent_name] = AgentNode(
                name=agent_name, 
                cfg=agent_cfg, 
                agent_caller=self._make_call_agent_fn(agent_name)
            )

    def _make_call_agent_fn(self, caller_name: str) -> AgentCaller:
        async def _call(target_agent_id: str, agent_input: TaskInput):
            return await self._call_agent_internal(target_agent_id, agent_input, caller_name)
        return _call

    async def _call_agent_internal(self, agent_name: str, agent_input: TaskInput, caller_name: str):
        ctx = _current_task_context.get()
        if ctx is None:
            raise RuntimeError("No task context found. Call run_task() first.")
        
        agent_node = self.agent_nodes[agent_name]
        await agent_node.init_tool_definitions()
        
        current_count = ctx.called_counter.get(agent_name, 0)
        ret = await agent_node.run(
            input=agent_input, 
            call_info=dict(caller_id=caller_name, called_count=current_count)
        )
        ctx.called_counter[agent_name] = current_count + 1
        return ret

    async def run_task(
        self,
        task_name: str,
        task_id: str,
        task_description: str,
        task_file_name: str | None,
        log_path: pathlib.Path,
        dataset_name: str | None = None,
        ground_truth: str | None = None,
        metadata: dict | None = None,
    ) -> tuple[str | None, TaskTracer]:
        task_log = TaskTracer(
            log_path=log_path,
            task_name=task_name,
            task_id=task_id,
            task_file_name=task_file_name,
            ground_truth=ground_truth,
            input={
                "task_description": task_description,
                "task_file_name": task_file_name,
                "metadata": metadata or {},
            },
        )
        
        ctx = TaskRunContext(
            task_log=task_log,
            called_counter={name: 0 for name in self.agent_nodes}
        )
        token = _current_task_context.set(ctx)
        
        result = None
        try:
            task_log.status = "running"
            input_ = TaskInput(
                task_description=task_description, 
                task_file_name=task_file_name, 
                task_id=task_id,
                dataset_name=dataset_name
            )
            result = await self._call_agent_internal(
                agent_name='main_agent', 
                agent_input=input_, 
                caller_name='entrypoint'
            )
            task_log.status = "completed"

        except Exception as e:
            error_details = traceback.format_exc()
            logger.error(f"An error occurred during task {task_id}", exc_info=True)
            task_log.status = "interrupted"
            task_log.error = error_details

        finally:
            _current_task_context.reset(token)
            
            task_log.end_time = datetime.now()
            task_log.log_step(
                "task_execution_finished",
                f"Task {task_id} execution completed with status: {task_log.status}",
            )
            task_log.save()
            logger.debug(f"--- Finished Task Execution: {task_id} ---")

        return result, task_log

