"""
Test script for running a single task with a configured agent.

This script demonstrates how to execute a single task using the miroflow
framework. It loads agent configuration, initializes the agent, and runs
a single task attempt with optional file input.
"""

# Initialize tracer first before any other local imports
# This must be done before importing other modules that use the tracer
from src.logging.task_tracer import set_tracer

# Standard library imports
import asyncio
import json
import os

# Third-party imports
import dotenv

# Local imports (after tracer initialization)
from config import load_config
from src.agents import build_agent_from_config
from src.utils.eval_utils import Task
from src.utils.task_utils import run_single_task


# Configuration constants
CONFIG_PATH = "config/agent_gaia-validation-text-only_mirothinker_single_agent.yaml"
OVERRIDES = ["benchmark.execution.max_concurrent=1"]

# Task constants
# Simple text-based task example
# TASK_DESCRIPTION = "Is Spain a country of Europe?"
# TASK_FILE_PATH = None

# Example of a task with file input
TASK_DESCRIPTION = (
    "I’m researching species that became invasive after people who kept them as pets released them. There’s a certain species of fish that was popularized as a pet by being the main character of the movie Finding Nemo. According to the USGS, where was this fish found as a nonnative species, before the year 2020? I need the answer formatted as the five-digit zip codes of the places the species was found, separated by commas if there is more than one place."
)
# TASK_FILE_PATH = os.path.abspath('data/FSI-2023-DOWNLOAD.xlsx')


if __name__ == "__main__":
    """
    Execute a single task attempt with the configured agent.
    """
    # Load environment variables from .env file
    dotenv.load_dotenv()

    # Load configuration
    print(f"Loading configuration from: {CONFIG_PATH}")
    cfg = load_config(CONFIG_PATH, *OVERRIDES)
    print(f"Output directory: {cfg.output_dir}")
    set_tracer(cfg.output_dir)

    # Build the agent from configuration
    agent = build_agent_from_config(cfg=cfg)

    # Execute the task asynchronously
    result = asyncio.run(
        run_single_task(
            cfg=cfg,
            agent=agent,
            task=Task(
                task_id="task_1",
                task_question=TASK_DESCRIPTION,
                # file_path=TASK_FILE_PATH
            ),
            attempt_num=1
        )
    )
    
    # Save result to JSON file in the configured output directory
    output_dir = cfg.output_dir
    os.makedirs(output_dir, exist_ok=True)
    output_file = os.path.join(output_dir, 'task_result.json')
    
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(result.model_response, f, indent=4, ensure_ascii=False)
    
    print(f"Task result saved to {output_file}")
