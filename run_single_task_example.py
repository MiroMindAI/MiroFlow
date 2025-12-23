from src.agents.registry import build_agent_from_config
import asyncio
import dotenv
from omegaconf import OmegaConf
cfg = OmegaConf.load("config/agent_gaia-validation-gpt5_new_version.yaml")
cfg = OmegaConf.to_container(cfg, resolve=True)
import logging
from src.logging.logger import bootstrap_logger
from src.logging.task_tracer import TaskTracer, set_current_tracer, reset_current_tracer
from pathlib import Path
logger = bootstrap_logger(level="WARNING")

async def entrypoint():
    agent = build_agent_from_config(cfg)
    tracer = TaskTracer(log_path=Path("./task.log"))
    token = set_current_tracer(tracer)
    tracer.start()  # 初始化并开始记录
    print(agent)
    try:
        ret = await agent.run({'task_description':"Is Spain oa country of Europe?"})
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
