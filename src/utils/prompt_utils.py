import yaml
from jinja2 import Environment, StrictUndefined


class PromptTemplateReader:
    def __init__(self, config_path: str):
        """
        Load YAML containing templates and components.
        """
        with open(config_path, "r", encoding="utf-8") as f:
            self.config = yaml.safe_load(f)

        # StrictUndefined 会在参数缺失时报错，如果你想容忍缺失就改成 Undefined
        self.env = Environment(undefined=StrictUndefined)

    def _validate_required_context(self, section_cfg: dict, context: dict, section_name: str):
        required = section_cfg.get("required_context", [])
        missing = [k for k in required if k not in context]

        if missing:
            raise ValueError(
                f"[PromptRenderer] Section '{section_name}' missing required context keys: {missing}"
            )

    def _render_components(self, section_cfg: dict, context: dict, section_name: str, component: str = None) -> str:
        rendered_parts = []

        if component:
            components = [component]
        else:
            components = section_cfg["components"]

        for comp_name in components:
            if comp_name not in section_cfg:
                raise KeyError(
                    f"[PromptRenderer] Component '{comp_name}' not found under section '{section_name}'."
                )

            raw_template = section_cfg[comp_name]
            template = self.env.from_string(raw_template)
            rendered_text = template.render(**context).strip()

            if rendered_text:  # skip empty blocks
                rendered_parts.append(rendered_text)

        return "\n\n".join(rendered_parts)

    def render_prompt(self, prompt_name: str, context: dict) -> str:
        """
        Render a single prompt section (e.g., initial_user_text, system_prompt).
        """
        section_cfg = self.config["template"][prompt_name]

        # 1. validate required context fields
        self._validate_required_context(section_cfg, context, prompt_name)

        # 2. render components in order
        return self._render_components(section_cfg, context, prompt_name)

    def render_prompt_component(self, prompt_name: str, context: dict, component: str) -> str:
        """
        Render a single component of a prompt section (e.g., basic_system_prompt, chinese_context_extra_prompt).
        """
        section_cfg = self.config["template"][prompt_name]

        return self._render_components(section_cfg, context, prompt_name, component)

# ============================================================
# Example Usage
# ============================================================
if __name__ == "__main__":
    renderer = PromptTemplateReader("/home/muyan_zhong/dev/MiroFlow-baseline/config/agent_prompts/prompt_v0.yaml")

    context = {
        "task_description": "Explain the concept of reinforcement learning.",
        "file_input": {
            "file_type": "pdf",
            "file_name": "notes.pdf",
            "absolute_file_path": "/workspace/notes.pdf"
        },
        "formatted_date": "2025-12-01",
        "chinese_context": True,
        "mcp_server_definitions": "{...schema...}"
    }

    # Render specific section
    print(renderer.render_prompt("initial_user_text", context))

    # Or render all at once
    #all_outputs = renderer.render_all(context)
    #print(all_outputs["system_prompt"])

