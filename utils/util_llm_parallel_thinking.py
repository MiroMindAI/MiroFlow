# SPDX-FileCopyrightText: 2025 MiromindAI
#
# SPDX-License-Identifier: Apache-2.0


import asyncio
import glob
import json
import os
import sys
from typing import Dict, List, Any, Optional, Tuple, Literal

from openai import AsyncOpenAI
from openai import APIError, APIConnectionError, RateLimitError, APITimeoutError
from pydantic import BaseModel
from tenacity import stop_after_attempt, wait_exponential
from tenacity.asyncio import AsyncRetrying

from eval_utils import verify_answer_for_datasets
from dotenv import load_dotenv

load_dotenv()

OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY")


class ExtractedAnswer(BaseModel):
    reasoning: str
    final_answer: str
    strict: Literal[True] = True  # 100% reliability


# Constants
# BENCHMARK_NAME = "xbench-ds"  # Benchmark name for evaluation


BENCHMARK_NAME = "gaia-validation"  # Benchmark name for evaluation
RESULTS_DIRS = ["<your_results_dirs>"]

DEFAULT_MODEL = "o3"
OPENAI_BASE_URL = "https://api.openai.com/v1"
MAX_RETRY_ATTEMPTS = 3
RETRY_WAIT_MIN = 1  # seconds
RETRY_WAIT_MAX = 10  # seconds
MAX_CONCURRENT_REQUESTS = 25  # Maximum concurrent API requests
SEMAPHORE_TIMEOUT = 300  # Timeout for acquiring semaphore in seconds
VERBOSE = True

# O3 Pricing (per 1M tokens)
O3_INPUT_PRICE = 2.00  # $2.00 per 1M input tokens
O3_CACHED_INPUT_PRICE = 0.50  # $0.50 per 1M cached input tokens
O3_OUTPUT_PRICE = 8.00  # $8.00 per 1M output tokens


def process_message_history(main_agent_message_history: Dict[str, Any]) -> str:
    """Process and concatenate message history content."""
    try:
        message_history = main_agent_message_history["message_history"]

        # Process the second-to-last message content
        # preliminary_content = message_history[-2]["content"]
        # preliminary_content = preliminary_content.replace("## Final Answer", "## Preliminary Answer")

        # Process the last message content
        final_content = message_history[-1]["content"][0]["text"]
        final_content = final_content.replace(
            "O3 extracted final answer:", "## Final Answer Reasoning\n"
        )

        # Concatenate the two parts
        # combined_content = preliminary_content + "\n\n" + final_content
        combined_content = final_content
        return combined_content

    except (KeyError, IndexError, TypeError) as e:
        print(f"Warning: Could not process message history: {e}")
        return ""


def extract_from_log(
    run_dir: str, task_score_dict: Dict[str, List[Dict[str, Any]]]
) -> None:
    """Extract task data from log files in a run directory."""
    try:
        log_files = glob.glob(os.path.join(run_dir, "*attempt*"))
        for log_file in log_files:
            try:
                task_id = log_file.split("/")[-1].split("_")[1]
                with open(log_file, "r") as f:
                    data = json.load(f)
                    if task_id not in task_score_dict:
                        task_score_dict[task_id] = []
                    task_score_dict[task_id].append(
                        # select some keys from data
                        {
                            "task_id": data["task_id"],
                            "task_name": data["task_name"],
                            "ground_truth": data["ground_truth"],
                            "final_boxed_answer": data["final_boxed_answer"],
                            "input": data["input"],
                            "agent_summary": process_message_history(
                                data["main_agent_message_history"]
                            ),
                        }
                    )
            except (json.JSONDecodeError, KeyError, IOError) as e:
                print(f"Warning: Could not process log file {log_file}: {e}")
                continue
    except Exception as e:
        print(f"Error processing run directory {run_dir}: {e}")
        raise


async def select_best_solution(
    prompt: str,
    n_runs: int,
    model: str = DEFAULT_MODEL,
    semaphore: Optional[asyncio.Semaphore] = None,
) -> str:
    """Select the best solution using LLM with retry logic and concurrency control."""

    async def _make_api_call():
        """Make the actual API call with proper error handling."""
        api_key = OPENAI_API_KEY

        if not api_key:
            raise ValueError("OPENAI_API_KEY environment variable not set")

        client = AsyncOpenAI(
            base_url=OPENAI_BASE_URL,
            api_key=api_key,
        )

        completion = await client.beta.chat.completions.parse(
            model=model,
            messages=[
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": prompt},
                    ],
                }
            ],
            response_format=ExtractedAnswer,
        )

        response = completion.choices[0].message.content
        if not response:
            raise ValueError("Empty response from API")

        # Parse the structured response
        parsed_response = json.loads(response)

        # Get usage information
        usage = completion.usage
        return parsed_response, usage

    # Use semaphore for concurrency control if provided
    if semaphore:
        async with semaphore:
            return await _retry_api_call(_make_api_call)
    else:
        return await _retry_api_call(_make_api_call)


async def _retry_api_call(api_call_func):
    """Retry logic for API calls using AsyncRetrying."""
    async for attempt in AsyncRetrying(
        stop=stop_after_attempt(MAX_RETRY_ATTEMPTS),
        wait=wait_exponential(multiplier=1, min=RETRY_WAIT_MIN, max=RETRY_WAIT_MAX),
        reraise=True,
    ):
        with attempt:
            try:
                return await api_call_func()
            except (
                APIError,
                APIConnectionError,
                RateLimitError,
                APITimeoutError,
                ConnectionError,
            ) as e:
                print(
                    f"Retryable API error (attempt {attempt.retry_state.attempt_number}): {e}"
                )
                raise  # Let tenacity handle the retry
            except Exception as e:
                print(f"Non-retryable error in select_best_solution: {e}")
                raise


def load_task_data(results_dir: str) -> Dict[str, List[Dict[str, Any]]]:
    """Load task data from all run directories."""
    run_dirs = glob.glob(os.path.join(results_dir, "run_*"))
    run_dirs = [d for d in run_dirs if os.path.isdir(d)]

    task_score_dict: Dict[str, List[Dict[str, Any]]] = {}
    for run_dir in run_dirs:
        extract_from_log(run_dir, task_score_dict)

    return task_score_dict


def load_combined_task_data(
    results_dirs: List[str],
) -> Tuple[Dict[str, List[Dict[str, Any]]], int]:
    """Load and combine task data from multiple result directories."""
    combined_dict: Dict[str, List[Dict[str, Any]]] = {}
    total_runs = 0

    for results_dir in results_dirs:
        if not os.path.exists(results_dir):
            print(f"Warning: Skipping non-existent directory: {results_dir}")
            continue
        task_data = load_task_data(results_dir)
        run_count = len(
            [
                d
                for d in os.listdir(results_dir)
                if os.path.isdir(os.path.join(results_dir, d)) and d.startswith("run_")
            ]
        )
        total_runs += run_count

        for task_id, data_list in task_data.items():
            if task_id not in combined_dict:
                combined_dict[task_id] = []
            combined_dict[task_id].extend(data_list)

    return combined_dict, total_runs


def create_parallel_thinking_gaia_prompt(
    task_data: List[Dict[str, Any]], n_runs: int
) -> str:
    """Create prompt for parallel thinking for GAIA benchmark."""
    #     prompt = f"""You are an expert evaluator. Your task is to analyze multiple answers to a question and determine the final answer based on majority vote.

    # Question:
    # {task_data[0]["input"]}

    # Refer to the following {n_runs} solutions and select the best solution. Make sure the answer is in `\\boxed{{}}`.
    #     """
    # Generate agent summaries with markdown formatting
    agent_summaries = []
    for i, d in enumerate(task_data, 1):
        agent_summaries.append(
            f"**Agent Summary {i}:**\n```markdown\n{d['agent_summary']}\n```"
        )

    prompt = f"""You are an expert evaluator working with me to determine the best answer from multiple agent summaries. I need your help to analyze these detailed summaries and extract the final answers to determine the best solution.

Question: {task_data[0]["input"]}

Agent Summaries:
{"\n\n".join(agent_summaries)}

Here's how we can approach this together:

**Understanding Equivalence:**
I'd like you to group answers that are equivalent according to these precise normalization rules:

For numerical answers:
   - Remove symbols "$", "%", and "," then convert to float numbers and compare
   - Examples: "1.5" equals "1.50", "$1,000" equals "1000", "50%" equals "50"
   - Must be exactly equal as float numbers after normalization

For text answers (single text, not lists):
   - Remove all spaces and punctuation, convert to lowercase, then compare
   - Examples: "sea gull" equals "seagull", "New York!" equals "newyork"
   - Note: "NYC" ≠ "New York City" (becomes "nyc" vs "newyorkcity" - different words)

For list answers (containing commas or semicolons):
   - Split into elements, lists must have same length
   - Compare elements in the same position
   - For each element: if it's a number, use number rules; if text, remove spaces only (keep punctuation), convert to lowercase
   - All corresponding elements must match

**Important:** Valid answers always exist for these questions. Ignore responses containing "none", "not found", or similar expressions indicating no answer exists.

**Special Interpret Rules:**
- **Long List Rule**: Any numerical list with >10 elements should be interpreted as a single summary number (sum, count, average, etc.) for equivalence comparison, regardless of question wording.
- **Instruction Priority Rule**: If agent summary mentions a conditional-vs-unconditional issue in Potential Weaknesses, correct the answer by applying unconditional instructions over conditional instructions.
- **Percentage Comparison Rule**: If the answer needs to compare two percentages (percent above or below), calculate the direct difference between percentages, not the relative change ratio.
- **Percentage Trivial Rule**: If the question asks for a percentage answer, discard trivial answers like 0 or 100 as they are unlikely to be correct.
- **Birthplace Rule**: If the answer is related to birthplaces, use the historical names at the time of birth, not the current names.
- **Time Distinction Rule**: Pay attention to time references in questions, especially distinguishing between release time and award time, as they are typically in different years.

**Your Task:**
Please analyze these agent summaries thoughtfully and follow these steps:
1. **Extract answers**: Extract the final answer from each agent summary (look for \\boxed{{}} format, extract only the content inside the braces)
2. **Apply interpret rules**: Apply the Special Interpret Rules above to each answer. ONLY use the specific interpret rules I provided. If any answer requires correction, apply the same correction to all agents with the same original answer, regardless of their process quality.
3. **Assess information gathering**: Cross-compare all agent summaries to identify any agents with clear information gathering defects. Mainly Focus on the information collection process, unless there is evidence of critical inaccuracy in the gathered information. ONLY exclude agents if you find obvious signs of: (a) critically incomplete information gathering that other agents successfully obtained, or (b) clear information bias where the agent accessed wrong sources while others accessed correct ones. Be extremely conservative - when in doubt, include the agent.
4. **Group answers**: Group answers that are equivalent (using both original form and interpreted form for comparison) from reliable agents only
5. **Count support**: Count support for each group 
6. **Select winner**: Choose the group with the most support, then select one exact original answer from that winning group

**IMPORTANT:** Your final_answer must be exactly one of the original answer contents that were inside the \\boxed{{}} sections, with NO modifications and NO \\boxed{{}} wrapper.

Please respond in JSON format:
{{
    "reasoning": "Show your step-by-step analysis: (1) extracted answers, (2) interpret rules applications to each answer, (3) information gathering assessment and agent exclusions, (4) grouping with equivalence explanations, (5) group support counts, (6) winning group selection",
    "final_answer": "The exact content from inside one of the \\boxed{{}} sections"
}}
"""
    #     for i, d in enumerate(task_data):
    #         prompt += f"""
    # {'-'*100}
    # Solution {i+1}:
    # {d["main_agent_message_history"]["message_history"][-2]["content"]}
    # {d["main_agent_message_history"]["message_history"][-1]["content"][0]["text"]}
    # """
    return prompt


def create_parallel_thinking_xbench_prompt(
    task_data: List[Dict[str, Any]], n_runs: int
) -> str:
    """Create prompt for parallel thinking for XBench benchmark (Chinese)."""
    # Generate agent summaries with markdown formatting
    agent_summaries = []
    for i, d in enumerate(task_data, 1):
        agent_summaries.append(
            f"**智能体总结 {i}：**\n```markdown\n{d['agent_summary']}\n```"
        )

    prompt = f"""你是一位专业的评估专家，我需要你帮助我从多个智能体总结中确定最佳答案。请分析这些详细总结并提取最终答案来确定最佳解决方案。

问题：{task_data[0]["input"]}

智能体总结：
{"\n\n".join(agent_summaries)}

让我们一起来解决这个问题：

**等价性理解：**
按照XBench评判标准对答案进行等价分组：

- 只关注答案之间是否存在**实质性差异**，不要过度关注格式细节
- 对于数值题目，允许**可接受的微小误差范围**内的差异
- 如果答案在语义上**一致**，即使表述方式不同也视为等价
- 存在任何**不一致、歧义、不等价**的情况则视为不同答案
- 不要重新解题或为不同答案辩护，专注于判断答案是否一致

**重要：** 这些问题总是存在有效答案。忽略包含"无"、"未找到"或类似表示无答案的回答。

**数值答案要求：** 对于数值答案，避免使用"约"、"大约"等模糊表达，即使题目中有此类询问也要给出尽可能的精确值。

**特殊解释规则：**
- **地点明确规则**：对于地点名称，总是主动添加地理位置、所属城市、区域、线路等限定词来增强表述的准确性和完整性。
- **数值单位规则**：数值答案应包含数量单位，具体采用何种表述形式以及单位，应根据问题的具体问法和要求以及中文日常表述习惯来决定。
    - 注意”列车“是名词，不是数量单位，”辆“是其数量单位。
- **序数词规则**：当答案涉及排序或顺序时，使用"第一"、"第二"等完整的序数词表述。

**你的任务：**
请仔细分析这些智能体总结并按照以下步骤进行：
1. **提取答案**：从每个智能体总结中提取最终答案（寻找\\boxed{{}}格式，只提取大括号内的内容）
2. **应用解释规则**：对每个答案应用上述特殊解释规则。仅使用我提供的特定解释规则。如果任何答案需要纠正，对所有具有相同原始答案的智能体应用相同纠正，无论其过程质量如何。
3. **评估信息收集**：交叉比较所有智能体总结，识别任何具有明显信息收集缺陷的智能体。主要关注信息收集过程，不关注答案的正确性。仅在发现明显迹象时排除智能体：(a) 其他智能体成功获得的关键不完整信息收集，或 (b) 智能体访问错误来源而其他智能体访问正确来源的明显信息偏差。极其保守——有疑虑时包含智能体。如果因为问题答案而排除任何智能体，排除所有具有相同答案的智能体。
4. **分组答案**：仅对可靠智能体的答案进行等价分组（使用原始形式和解释形式进行比较）
5. **计算支持**：计算每组的支持数
6. **选择获胜者**：选择支持最多的组，然后将获胜答案改写为简短的表述形式（短语或词汇，禁止完整句子，禁止描述性或解释性表述）

**重要：** 你的最终答案必须是尽可能简短的表述，使用短语或词汇，严禁使用完整句子、描述性或解释性内容。遵循上述特殊解释规则。

请用JSON格式回复：
{{
    "reasoning": "显示你的逐步分析：(1) 提取的答案，(2) 对每个答案的解释规则应用，(3) 信息收集评估和智能体排除，(4) 分组和等价性解释，(5) 组支持计数，(6) 获胜组选择",
    "final_answer": "简短的表述（短语或词汇，禁止完整句子，遵循特殊解释规则）"
}}
"""
    return prompt


async def process_single_task(
    task_id: str, data: List[Dict[str, Any]], n_runs: int, semaphore: asyncio.Semaphore
) -> Tuple[str, Dict[str, Any], Any]:
    """Process a single task and return its result."""
    # Choose prompt function based on benchmark
    if "xbench" in BENCHMARK_NAME:
        prompt = create_parallel_thinking_xbench_prompt(data, n_runs)
    elif "gaia" in BENCHMARK_NAME:
        prompt = create_parallel_thinking_gaia_prompt(data, n_runs)
    else:
        raise ValueError(f"Unsupported benchmark name: {BENCHMARK_NAME}")

    response, usage = await select_best_solution(prompt, n_runs, semaphore=semaphore)
    selected_solution = response["final_answer"]
    reasoning = response["reasoning"]
    client = AsyncOpenAI(
        base_url=OPENAI_BASE_URL,
        api_key=OPENAI_API_KEY,
    )

    result = await verify_answer_for_datasets(
        client, BENCHMARK_NAME, "", data[0]["ground_truth"], selected_solution
    )

    task_result = {
        "task_id": task_id,
        "candidate_answers": [d["final_boxed_answer"] for d in data],
        "task_input": data[0]["input"],
        "prompt_input": prompt,
        "ground_truth": data[0]["ground_truth"],
        "selected_solution": selected_solution,
        "selected_solution_result": result,
        "selected_solution_reasoning": reasoning,
    }

    return task_id, task_result, usage


async def process_tasks(
    task_score_dict: Dict[str, List[Dict[str, Any]]],
    n_runs: int,
    max_concurrent_requests: int = MAX_CONCURRENT_REQUESTS,
) -> Dict[str, Dict[str, Any]]:
    """Process all tasks concurrently and select best solutions."""
    # Create semaphore for rate limiting
    semaphore = asyncio.Semaphore(max_concurrent_requests)

    # Create tasks for concurrent execution
    tasks = [
        process_single_task(task_id, data, n_runs, semaphore)
        for task_id, data in task_score_dict.items()
    ]

    total_tasks = len(tasks)
    print(
        f"Processing {total_tasks} tasks concurrently (max {max_concurrent_requests} concurrent requests)..."
    )

    # Process tasks and show progress as they complete
    task_results: Dict[str, Dict[str, Any]] = {}
    completed_tasks = 0

    # Token usage tracking
    total_input_tokens = 0
    total_cached_input_tokens = 0
    total_output_tokens = 0

    for coro in asyncio.as_completed(tasks):
        try:
            result = await coro
            task_id, task_result, usage = result
            task_results[task_id] = task_result
            completed_tasks += 1

            # Update token usage
            if usage:
                total_input_tokens += getattr(usage, "prompt_tokens", 0)
                total_cached_input_tokens += (
                    getattr(usage, "prompt_tokens_details", {}).cached_tokens
                    if hasattr(usage, "prompt_tokens_details")
                    else 0
                )
                total_output_tokens += getattr(usage, "completion_tokens", 0)

            # Show progress indicator
            progress_percent = (completed_tasks / total_tasks) * 100
            if VERBOSE:
                print(
                    f"Progress: {completed_tasks}/{total_tasks} ({progress_percent:.1f}%) - Completed task: {task_id}"
                )
                print(
                    f"  Tokens: Input={total_input_tokens-total_cached_input_tokens}, Cached={total_cached_input_tokens}, Output={total_output_tokens}"
                )
                input_cost = (
                    (total_input_tokens - total_cached_input_tokens)
                    * O3_INPUT_PRICE
                    / 1_000_000
                )
                cached_input_cost = (
                    total_cached_input_tokens * O3_CACHED_INPUT_PRICE / 1_000_000
                )
                output_cost = total_output_tokens * O3_OUTPUT_PRICE / 1_000_000
                total_cost = input_cost + cached_input_cost + output_cost
                print(
                    f"  Costs: Input=${input_cost:.4f}, Cached=${cached_input_cost:.4f}, Output=${output_cost:.4f}, Total=${total_cost:.4f}"
                )

        except Exception as e:
            completed_tasks += 1
            progress_percent = (completed_tasks / total_tasks) * 100
            if VERBOSE:
                print(
                    f"Progress: {completed_tasks}/{total_tasks} ({progress_percent:.1f}%) - Error processing task: {e}"
                )
                print(
                    f"  Tokens: Input={total_input_tokens-total_cached_input_tokens}, Cached={total_cached_input_tokens}, Output={total_output_tokens}"
                )
                input_cost = (
                    (total_input_tokens - total_cached_input_tokens)
                    * O3_INPUT_PRICE
                    / 1_000_000
                )
                cached_input_cost = (
                    total_cached_input_tokens * O3_CACHED_INPUT_PRICE / 1_000_000
                )
                output_cost = total_output_tokens * O3_OUTPUT_PRICE / 1_000_000
                total_cost = input_cost + cached_input_cost + output_cost
                print(
                    f"  Costs: Input=${input_cost:.4f}, Cached=${cached_input_cost:.4f}, Output=${output_cost:.4f}, Total=${total_cost:.4f}"
                )
            # Continue with other tasks instead of failing completely
            continue

    # Final pricing summary
    final_input_cost = (
        (total_input_tokens - total_cached_input_tokens) * O3_INPUT_PRICE / 1_000_000
    )
    final_cached_input_cost = (
        total_cached_input_tokens * O3_CACHED_INPUT_PRICE / 1_000_000
    )
    final_output_cost = total_output_tokens * O3_OUTPUT_PRICE / 1_000_000
    final_total_cost = final_input_cost + final_cached_input_cost + final_output_cost

    print(f"Successfully processed {len(task_results)} out of {total_tasks} tasks")
    print("\n=== FINAL PRICING SUMMARY ===")
    print(
        f"Total Input Tokens: {total_input_tokens-total_cached_input_tokens:,} (${final_input_cost:.4f})"
    )
    print(
        f"Total Cached Input Tokens: {total_cached_input_tokens:,} (${final_cached_input_cost:.4f})"
    )
    print(f"Total Output Tokens: {total_output_tokens:,} (${final_output_cost:.4f})")
    print(f"TOTAL COST: ${final_total_cost:.4f}")
    print("============================\n")

    return task_results


def save_results(
    results_dir: str, task_results: Dict[str, Dict[str, Any]], n_runs: int
) -> None:
    """Save results to files."""
    try:
        # Save detailed results
        results_file = os.path.join(
            results_dir, f"llm_parallel_thinking_{n_runs}runs.json"
        )
        with open(results_file, "w") as f:
            json.dump(task_results, f, ensure_ascii=False, indent=4)

        # Calculate and save accuracy
        correct_count = sum(
            1
            for data in task_results.values()
            if data["selected_solution_result"] == "CORRECT"
        )
        accuracy = correct_count / len(task_results) if task_results else 0.0

        print(f"Accuracy: {accuracy}")

        accuracy_file = os.path.join(
            results_dir, f"llm_parallel_thinking_accuracy_{n_runs}runs.txt"
        )
        with open(accuracy_file, "w") as f:
            f.write(f"Accuracy: {accuracy}")

    except IOError as e:
        print(f"Error saving results: {e}")
        raise


async def main(
    results_dir: str, max_concurrent_requests: int = MAX_CONCURRENT_REQUESTS
) -> None:
    """Main function to analyze results and select best solutions."""
    if not os.path.exists(results_dir):
        print(f"Results directory does not exist: {results_dir}")
        sys.exit(1)

    print(f"Analyzing results from: {results_dir}")

    # Load task data from all runs
    task_score_dict = load_task_data(results_dir)
    if not task_score_dict:
        print("No task data found")
        return

    # Get number of runs
    run_dirs = glob.glob(os.path.join(results_dir, "run_*"))
    n_runs = len([d for d in run_dirs if os.path.isdir(d)])

    # Process all tasks
    task_results = await process_tasks(task_score_dict, n_runs, max_concurrent_requests)

    # Save results
    save_results(results_dir, task_results, n_runs)


if __name__ == "__main__":
    max_concurrent_requests = MAX_CONCURRENT_REQUESTS

    # Use single or multiple directory mode based on whether results_dirs is defined above
    results_dirs = RESULTS_DIRS

    if results_dirs:
        # Multiple directories mode
        combined_dict, total_runs = load_combined_task_data(results_dirs)
        if not combined_dict:
            print("No task data found")
            sys.exit(1)
        print(
            f"Loaded {len(combined_dict)} tasks with {total_runs} total runs from {len(results_dirs)} directories"
        )

        async def main_combined():
            task_results = await process_tasks(
                combined_dict, total_runs, max_concurrent_requests
            )
            save_results(os.path.dirname(results_dirs[0]), task_results, total_runs)

        asyncio.run(main_combined())
    else:
        # Single directory mode
        # asyncio.run(main(results_dir, max_concurrent_requests))
        pass
