from abc import ABC, abstractmethod
import dataclasses
from typing import Any


@dataclasses.dataclass
class BaseAgentPrompt(ABC):
    """
    Abstract base class for agent prompt templates.
    All agent prompt classes should inherit from this and implement the required methods.
    """

    is_main_agent: bool = True

    def __init__(self, *args, **kwargs):
        pass

    @abstractmethod
    def generate_system_prompt_with_mcp_tools(
        self, mcp_servers: list[Any], chinese_context: bool = False, **kwargs
    ) -> str:
        """
        Generate the system prompt with mcp tools for the agent.

        Args:
            date (datetime.datetime): The current date.
            mcp_servers (list[Any]): List of MCP server configurations.
            chinese_context (bool, optional): Whether to use Chinese context. Defaults to False.
            **kwargs: Additional keyword arguments for extensibility.

        Returns:
            str: The system prompt string.

        Raises:
            NotImplementedError: This method must be implemented by subclasses.
        """
        raise NotImplementedError(
            "Subclasses must implement generate_mcp_system_prompt with support for extra kwargs."
        )

    @abstractmethod
    def generate_summarize_prompt(
        self,
        task_description: str,
        task_failed: bool = False,
        chinese_context: bool = False,
        **kwargs,
    ) -> str:
        """
        Generate the summarize prompt for the agent.

        Args:
            task_description (str): The description of the task.
            task_failed (bool, optional): Whether the task failed. Defaults to False.
            agent_type (str, optional): The type of the agent. Defaults to "".
            chinese_context (bool, optional): Whether to use Chinese context. Defaults to False.
            **kwargs: Additional keyword arguments for extensibility.

        Returns:
            str: The summarize prompt string.

        Raises:
            NotImplementedError: This method must be implemented by subclasses.
        """
        raise NotImplementedError(
            "Subclasses must implement generate_summarize_prompt with support for extra kwargs."
        )

    def expose_agent_as_tool(self, subagent_name: str, **kwargs) -> dict:
        """
        Expose this agent as a tool.
        Main agent does not need to expose itself as tools.
        Sub-agents should implement this method to expose themselves as tools.

        Args:
            subagent_name (str): The name of the subagent.
            **kwargs: Additional keyword arguments for extensibility.

        Returns:
            dict: The tool definition dictionary with 'name' and 'tools' keys.
        """
        if self.is_main_agent:
            return {}
        else:
            raise NotImplementedError(
                "Subclasses must implement expose_agent_as_tool with support for extra kwargs."
            )

            # Output Example (this code will never be executed):
            tool_definition = dict(
                name=subagent_name,  # Name MUST starts with 'agent-'
                tools=[
                    dict(
                        name="execute_subtask",
                        description="This tool is an agent that performs various subtasks to collect information and execute specific actions... ",
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
            return tool_definition
