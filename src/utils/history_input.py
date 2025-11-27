# for turn_history in history:
#     for message in turn_history["main_agent"]:
#         # 去掉 <think>...</think> 标签及其内容
#         content = message["content"]
#         if isinstance(content, str):
#             content = re.sub(r'<think>.*?</think>', '', content, flags=re.DOTALL).strip()
#         message_history.append({"role": message["role"], "content": content})
import re

def to_blockquote(text: str) -> str:
    result_lines = []
    for line in text.splitlines():
        if line.strip() == '':
            result_lines.append('>')
            continue

        m = re.match(r'^(?P<prefix>(?:>\s*)+)', line)
        if m:
            level = m.group('prefix').count('>')
            content = line[m.end():]
            if content.strip() == '':
                result_lines.append('>' * (level + 1))
            else:
                result_lines.append(('>' * (level + 1)) + ' ' + content.lstrip())
        else:
            result_lines.append('> ' + line)
    return '\n'.join(result_lines) + ""

def make_muti_turn_prompt(history: list[dict], task_description: str) -> str:
    """
    Generate a multi-turn prompt from conversation history.
    
    Args:
        history: List of turn dictionaries containing conversation history
        
    Returns:
        Formatted string with conversation history
    """
    if not history:
        return ""
    
    parts = ["---\n\n"]
    parts.append("There has been a conversation with the user. Please continue the conversation.\n\n")
    
    for turn_id, turn in enumerate(history):
        # Extract user message from turn
        user_message = ""
        assistant_message = ""
        
        for message in turn.get("main_agent", []):
            content = message.get("content", "")
            if isinstance(content, str):
                content = re.sub(r'<think>.*?</think>', '', content, flags=re.DOTALL).strip()
            
            if message.get("role") == "user":
                user_message = content
            elif message.get("role") == "assistant":
                assistant_message = content
        
        # Build turn information
        parts.extend([
            f"- Turn {turn_id + 1}\n\n",
            f"User Prompt:\n\n{to_blockquote(user_message)}\n\n",
        ])
    
        parts.append(f"Assistant:\n\n{to_blockquote(assistant_message)}\n\n")

    parts.extend([
        f"- Below is the user's prompt on this turn:\n\n",
        f"{task_description}\n\n"
    ])
    
    parts.append("---\n\n")
    
    return "".join(parts)
