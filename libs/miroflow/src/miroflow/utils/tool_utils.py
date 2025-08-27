# SPDX-FileCopyrightText: 2025 MiromindAI
#
# SPDX-License-Identifier: Apache-2.0

import sys

from mcp import StdioServerParameters
from omegaconf import DictConfig, OmegaConf

from miroflow.logging.logger import bootstrap_logger

logger = bootstrap_logger()


# MCP server configuration generation function
def create_mcp_server_parameters(
    cfg: DictConfig, agent_cfg: DictConfig, logs_dir: str | None = None
):
    """Define and return MCP server configuration list"""
    ENABLE_CLAUDE_VISION = cfg.agent.tool_config["tool-image-video"][
        "enable_claude_vision"
    ]
    ENABLE_OPENAI_VISION = cfg.agent.tool_config["tool-image-video"][
        "enable_openai_vision"
    ]

    configs = []
    if agent_cfg.get("tools", None) is not None and "tool-code" in agent_cfg["tools"]:
        # Prepare environment variables for tool-code
        tool_code_env = {"E2B_API_KEY": cfg.env.e2b_api_key}

        # Add logs_dir to environment if provided
        if logs_dir:
            tool_code_env["LOGS_DIR"] = str(logs_dir)

        configs.append(
            {
                "name": "tool-code",
                "params": StdioServerParameters(
                    command=sys.executable,
                    args=["-m", "miroflow.tool.mcp_servers.python_server"],
                    env=tool_code_env,
                ),
            }
        )

    if (
        agent_cfg.get("tools", None) is not None
        and "tool-image-video" in agent_cfg["tools"]
    ):
        configs.append(
            {
                "name": "tool-image-video",
                "params": StdioServerParameters(
                    command=sys.executable,
                    args=["-m", "miroflow.tool.mcp_servers.vision_mcp_server"],
                    env={
                        "ANTHROPIC_API_KEY": cfg.env.anthropic_api_key,
                        "ANTHROPIC_BASE_URL": cfg.env.anthropic_base_url,
                        "OPENAI_API_KEY": cfg.env.openai_api_key,
                        "OPENAI_BASE_URL": cfg.env.openai_base_url,
                        "ENABLE_CLAUDE_VISION": ENABLE_CLAUDE_VISION,
                        "ENABLE_OPENAI_VISION": ENABLE_OPENAI_VISION,
                        "GEMINI_API_KEY": cfg.env.gemini_api_key,
                    },
                ),
            }
        )

    if agent_cfg.get("tools", None) is not None and "tool-audio" in agent_cfg["tools"]:
        configs.append(
            {
                "name": "tool-audio",
                "params": StdioServerParameters(
                    command=sys.executable,
                    args=["-m", "miroflow.tool.mcp_servers.audio_mcp_server"],
                    env={
                        "OPENAI_API_KEY": cfg.env.openai_api_key,
                    },
                ),
            }
        )

    if (
        agent_cfg.get("tools", None) is not None
        and "tool-reasoning" in agent_cfg["tools"]
    ):
        configs.append(
            {
                "name": "tool-reasoning",
                "params": StdioServerParameters(
                    command=sys.executable,
                    args=[
                        "-m",
                        "miroflow.tool.mcp_servers.reasoning_mcp_server",
                    ],
                    env={
                        "ANTHROPIC_API_KEY": cfg.env.anthropic_api_key,
                        "ANTHROPIC_BASE_URL": cfg.env.anthropic_base_url,
                        "OPENROUTER_API_KEY": cfg.env.openrouter_api_key,
                        "OPENROUTER_BASE_URL": cfg.env.openrouter_base_url,
                    },
                ),
            }
        )

    if (
        agent_cfg.get("tools", None) is not None
        and "tool-markitdown" in agent_cfg["tools"]
    ):
        configs.append(
            {
                "name": "tool-markitdown",
                "params": StdioServerParameters(
                    command="markitdown-mcp",
                ),
            }
        )

    if (
        agent_cfg.get("tools", None) is not None
        and "tool-reading" in agent_cfg["tools"]
    ):
        configs.append(
            {
                "name": "tool-reading",
                "params": StdioServerParameters(
                    command=sys.executable,
                    args=[
                        "-m",
                        "miroflow.tool.mcp_servers.reading_mcp_server",
                    ],
                ),
            }
        )

    if (
        agent_cfg.get("tools", None) is not None
        and "tool-browsing" in agent_cfg["tools"]
    ):
        configs.append(
            {
                "name": "tool-browsing",
                "params": StdioServerParameters(
                    command=sys.executable,
                    args=["-m", "miroflow.tool.mcp_servers.browsing_mcp_server"],
                    env={
                        "ANTHROPIC_API_KEY": cfg.env.anthropic_api_key,
                        "ANTHROPIC_BASE_URL": cfg.env.anthropic_base_url,
                        "OPENROUTER_API_KEY": cfg.env.openrouter_api_key,
                        "OPENROUTER_BASE_URL": cfg.env.openrouter_base_url,
                    },
                ),
            }
        )

    if not (
        OmegaConf.is_missing(cfg, "env.serper_api_key")
        or OmegaConf.is_missing(cfg, "env.jina_api_key")
    ):
        if (
            agent_cfg.get("tools", None) is not None
            and "tool-serper-search" in agent_cfg["tools"]
        ):
            configs.append(
                {
                    "name": "tool-serper-search",
                    "params": StdioServerParameters(
                        command="npx",
                        args=["-y", "serper-search-scrape-mcp-server"],
                        env={"SERPER_API_KEY": cfg.env.serper_api_key},
                    ),
                }
            )
        if (
            agent_cfg.get("tools", None) is not None
            and "tool-searching" in agent_cfg["tools"]
        ):
            configs.append(
                {
                    "name": "tool-searching",
                    "params": StdioServerParameters(
                        command=sys.executable,
                        args=[
                            "-m",
                            "miroflow.tool.mcp_servers.searching_mcp_server",
                        ],
                        env={
                            "SERPER_API_KEY": cfg.env.serper_api_key,
                            "JINA_API_KEY": cfg.env.jina_api_key,
                            "GEMINI_API_KEY": cfg.env.gemini_api_key,
                            "REMOVE_SNIPPETS": cfg.env.remove_snippets,
                            "REMOVE_KNOWLEDGE_GRAPH": cfg.env.remove_knowledge_graph,
                            "REMOVE_ANSWER_BOX": cfg.env.remove_answer_box,
                        },
                    ),
                }
            )
    else:
        logger.debug(
            "Warning: SERPER_API_KEY or JINA_API_KEY not set, some search tools will be unavailable."
        )

    blacklist = set()
    for black_list_item in agent_cfg.get("tool_blacklist", []):
        blacklist.add((black_list_item[0], black_list_item[1]))
    return configs, blacklist


def expose_sub_agents_as_tools(sub_agents_cfg: DictConfig):
    """Expose sub-agents as tools"""
    sub_agents_server_params = []
    for sub_agent in sub_agents_cfg.keys():
        if "agent-worker" in sub_agent:  # type: ignore
            sub_agents_server_params.append(
                dict(
                    name="agent-worker",
                    tools=[
                        dict(
                            name="execute_subtask",
                            description="This tool is an agent that performs various subtasks to collect information and execute specific actions. It can access the internet, read files, program, and process multimodal content, but is not specialized in complex reasoning or logical thinking. The tool returns processed summary reports rather than raw information - it analyzes, synthesizes, and presents findings in a structured format. The subtask should be clearly defined, include relevant background, and focus on a single, well-scoped objective. It does not perform vague or speculative subtasks. \nArgs: \n\tsubtask: the subtask to be performed. \nReturns: \n\tthe processed summary report of the subtask. ",
                            schema={
                                "type": "object",
                                "properties": {
                                    "subtask": {"title": "Subtask", "type": "string"}
                                },
                                "required": ["subtask"],
                                "title": "execute_subtaskArguments",
                            },
                        )
                    ],
                )
            )
        if "agent-coding" in sub_agent:  # type: ignore
            sub_agents_server_params.append(
                dict(
                    name="agent-coding",
                    tools=[
                        dict(
                            name="solve_problem",
                            description="This tool is an agent that could solve the given subtask by python-coding or command-executing and running the the code on Linux system. The subtask should be clearly defined, include relevant background, and desired output format. It does not perform vague or speculative subtasks. \nArgs: \n\tsubtask: the subtask to be performed. \nReturns: \n\tthe result of the subtask. ",
                            schema={
                                "type": "object",
                                "properties": {
                                    "subtask": {"title": "Subtask", "type": "string"}
                                },
                                "required": ["subtask"],
                                "title": "solve_problemArguments",
                            },
                        )
                    ],
                )
            )
        if "agent-reading" in sub_agent:  # type: ignore
            sub_agents_server_params.append(
                dict(
                    name="agent-reading",
                    tools=[
                        dict(
                            name="read_and_summarize",
                            description="This tool is an agent that performs the subtask of reading documents (not websites) and providing desired summary of the content. The subtask should be clearly defined, include relevant background, and focus of the information. It does not perform vague or speculative subtasks. \nArgs: \n\tsubtask: the subtask to be performed. \nReturns: \n\tthe result of the subtask. ",
                            schema={
                                "type": "object",
                                "properties": {
                                    "subtask": {"title": "Subtask", "type": "string"}
                                },
                                "required": ["subtask"],
                                "title": "read_and_summarizeArguments",
                            },
                        )
                    ],
                )
            )
    return sub_agents_server_params
