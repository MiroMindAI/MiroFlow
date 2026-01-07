from src.agents.registry import build_agent_from_config
import asyncio
import dotenv
from omegaconf import OmegaConf
cfg = OmegaConf.load("config/agent_gaia-validation-gpt5-single-agent.yaml")
cfg = OmegaConf.to_container(cfg, resolve=True)
import logging
import os
from src.logging.logger import setup_logger
from src.logging.task_tracer import TaskTracer, set_current_tracer, reset_current_tracer
from pathlib import Path
logger = setup_logger(level="WARNING")

example_ctx_1 = {'task_description':"Is Spain oa country of Europe?"}
example_ctx_2 = {
    'task_description': 'What is the first country listed in the XLSX file that have names starting with Co?',
    'task_file_name': os.path.abspath('data/FSI-2023-DOWNLOAD.xlsx')
}

async def entrypoint():
    agent = build_agent_from_config(cfg)
    tracer = TaskTracer(log_path=Path("logs/task.log"))
    token = set_current_tracer(tracer)
    tracer.start()  # 初始化并开始记录
    print(agent)
    try:
        ret = await agent.run(
            example_ctx_2
        )
    finally:
        # 使用新的 API：通过 finish() 的参数传递 final_boxed_answer
        tracer.finish(status="completed")
        reset_current_tracer(token)
    return ret  # 返回 agent 对象或任何你需要的值

if __name__ == "__main__":
    dotenv.load_dotenv()
    result = asyncio.run(entrypoint())
    import json
    json.dump(result, open('task_result.json', 'w'), indent = 4)
