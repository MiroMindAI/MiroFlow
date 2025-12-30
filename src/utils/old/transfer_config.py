#!/usr/bin/env python3
"""
将旧版本配置文件转换为新版本配置文件格式。

旧版本结构:
  main_agent:
    ...
  sub_agents:
    agent-worker:
      ...

新版本结构:
  agent_nodes:
    main_agent:
      prompt_config_path: ...
      callable_agent_names:
        - sub_agent
      ...
    sub_agent:
      prompt_config_path: ...
      ...

用法:
  python utils/transfer_config.py <input_yaml> <output_yaml>
  python utils/transfer_config.py config/agent_gaia-validation_claude37sonnet.yaml config/agent_gaia-validation_claude37sonnet_converted.yaml
"""

import argparse
import sys
from pathlib import Path
from ruamel.yaml import YAML
from ruamel.yaml.scalarstring import LiteralScalarString


def transfer_config(input_path: str, output_path: str, base_prompt_dir: str = None):
    """
    将旧版本配置转换为新版本配置。
    
    Args:
        input_path: 输入配置文件路径
        output_path: 输出配置文件路径
        base_prompt_dir: prompt 配置文件的基础目录
    """
    yaml = YAML()
    yaml.preserve_quotes = True
    yaml.default_flow_style = False
    yaml.width = 4096  # 防止长字符串换行
    yaml.indent(mapping=2, sequence=2, offset=2)
    
    with open(input_path, 'r', encoding='utf-8') as f:
        old_config = yaml.load(f)
    
    # 如果没有指定 base_prompt_dir，则使用输入文件的目录
    if base_prompt_dir is None:
        base_prompt_dir = str(Path(input_path).parent.absolute() / "agent_prompts")
    
    new_config = {}
    
    # 1. 保留 defaults 部分
    if 'defaults' in old_config:
        new_config['defaults'] = old_config['defaults']
    
    # 2. 创建 agent_nodes 结构
    new_config['agent_nodes'] = {}
    
    # 3. 转换 main_agent
    if 'main_agent' in old_config:
        main_agent = dict(old_config['main_agent'])
        
        # 移除 prompt_class，添加 prompt_config_path
        if 'prompt_class' in main_agent:
            del main_agent['prompt_class']
        main_agent['prompt_config_path'] = f"{base_prompt_dir}/prompt_main_agent.yaml"
        
        # 确保 output_process 有 format_final_summary
        if 'output_process' in main_agent:
            if 'format_final_summary' not in main_agent['output_process']:
                main_agent['output_process']['format_final_summary'] = True
        
        # 收集 sub_agent 名称用于 callable_agent_names
        sub_agent_names = []
        if 'sub_agents' in old_config:
            for old_name in old_config['sub_agents'].keys():
                # 将 agent-worker 等名称转换为 sub_agent
                new_name = _convert_agent_name(old_name)
                sub_agent_names.append(new_name)
        
        # 添加 callable_agent_names
        if sub_agent_names:
            main_agent['callable_agent_names'] = sub_agent_names
        
        # 重新排序 main_agent 的键，使 prompt_config_path 在前面
        new_config['agent_nodes']['main_agent'] = _reorder_agent_config(main_agent)
    
    # 4. 转换 sub_agents 为 agent_nodes 下的 sub_agent
    if 'sub_agents' in old_config:
        for old_name, sub_agent_config in old_config['sub_agents'].items():
            new_name = _convert_agent_name(old_name)
            sub_agent = dict(sub_agent_config)
            
            # 移除 prompt_class，添加 prompt_config_path
            if 'prompt_class' in sub_agent:
                del sub_agent['prompt_class']
            sub_agent['prompt_config_path'] = f"{base_prompt_dir}/prompt_sub_agent.yaml"
            
            # 确保有 add_message_id
            if 'add_message_id' not in sub_agent:
                sub_agent['add_message_id'] = True
            
            # 重新排序键
            new_config['agent_nodes'][new_name] = _reorder_agent_config(sub_agent)
    
    # 5. 保留其他顶层配置
    preserved_keys = ['defaults', 'main_agent', 'sub_agents']
    for key, value in old_config.items():
        if key not in preserved_keys:
            new_config[key] = value
    
    # 写入新配置文件
    with open(output_path, 'w', encoding='utf-8') as f:
        yaml.dump(new_config, f)
    
    print(f"配置文件已转换: {input_path} -> {output_path}")
    return new_config


def _convert_agent_name(old_name: str) -> str:
    """将旧的 agent 名称转换为新的名称格式"""
    # agent-worker -> sub_agent
    name_mapping = {
        'agent-worker': 'sub_agent',
    }
    return name_mapping.get(old_name, old_name.replace('-', '_'))


def _reorder_agent_config(config: dict) -> dict:
    """重新排序 agent 配置的键，使重要的键在前面"""
    priority_keys = [
        'prompt_config_path',
        'llm',
        'tool_config',
        'max_turns',
        'max_tool_calls_per_turn',
        'input_process',
        'output_process',
        'openai_api_key',
        'add_message_id',
        'keep_tool_result',
        'chinese_context',
        'callable_agent_names',
    ]
    
    ordered = {}
    
    # 先添加优先键
    for key in priority_keys:
        if key in config:
            ordered[key] = config[key]
    
    # 再添加其他键
    for key, value in config.items():
        if key not in ordered:
            ordered[key] = value
    
    return ordered


def main():
    parser = argparse.ArgumentParser(
        description='将旧版本配置文件转换为新版本配置文件格式',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__
    )
    parser.add_argument('input', help='输入配置文件路径')
    parser.add_argument('output', help='输出配置文件路径')
    parser.add_argument(
        '--prompt-dir', 
        default=None,
        help='prompt 配置文件的基础目录 (默认: <input_dir>/agent_prompts)'
    )
    
    args = parser.parse_args()
    
    if not Path(args.input).exists():
        print(f"错误: 输入文件不存在: {args.input}", file=sys.stderr)
        sys.exit(1)
    
    transfer_config(args.input, args.output, args.prompt_dir)


if __name__ == '__main__':
    main()

