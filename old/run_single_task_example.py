import asyncio
import json
from pathlib import Path

import dotenv
from omegaconf import OmegaConf

from src.agents.registry import build_agent_from_config
from src.logging.task_tracer import (
    init_tracer,
    get_tracer,
    set_current_task_context_var,
    TaskContextVar,
)

init_tracer(log_path="logs")

cfg = OmegaConf.load("config/agent_single-test.yaml")
cfg = OmegaConf.to_container(cfg, resolve=True)


example_ctx_1 = {"task_description": "What is the feeling of Jam today in afternoon?"}
# example_ctx_2 = {
#     'task_description': 'What is the first country listed in the XLSX file that have names starting with Co?',
#     'task_file_name': os.path.abspath('data/FSI-2023-DOWNLOAD.xlsx')
# }


async def entrypoint():
    agent = build_agent_from_config(cfg)
    tracer = get_tracer(log_path=Path("logs"))
    _ = set_current_task_context_var(TaskContextVar(task_id="example_task", run_id=1))
    tracer.start()  # 初始化并开始记录
    print(agent)
    ret = await agent.run(
        example_ctx_1
    )  # Use example_ctx_1 since example_ctx_2 is commented out
    return ret  # 返回 agent 对象或任何你需要的值


if __name__ == "__main__":
    dotenv.load_dotenv()
    result = asyncio.run(entrypoint())

    json.dump(result, open("task_result.json", "w"), indent=4)
