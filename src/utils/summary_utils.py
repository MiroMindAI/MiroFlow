# SPDX-FileCopyrightText: 2025 MiromindAI
#
# SPDX-License-Identifier: Apache-2.0

import re
from openai import AsyncOpenAI
from tenacity import retry, stop_after_attempt, wait_exponential
import uuid


def _generate_message_id() -> str:
    """Generate random message ID using common LLM format"""
    # Use 8-character random hex string, similar to OpenAI API format, avoid cross-conversation cache hits
    return f"msg_{uuid.uuid4().hex[:8]}"


@retry(
    wait=wait_exponential(multiplier=15),
    stop=stop_after_attempt(5),
    retry_error_callback=lambda retry_state: print(
        f"Retry attempt {retry_state.attempt_number} for extract_hints"
    ),
)
async def extract_hints(
    question: str,
    api_key: str,
    chinese_context: bool,
    add_message_id: bool,
    base_url: str = "https://api.openai.com/v1",
) -> str:
    """Use LLM to extract task hints"""
    client = AsyncOpenAI(api_key=api_key, timeout=600, base_url=base_url)

    instruction = """Carefully analyze the given task description (question) without attempting to solve it directly. Your role is to identify potential challenges and areas that require special attention during the solving process, and provide practical guidance for someone who will solve this task by actively gathering and analyzing information from the web.

Identify and concisely list key points in the question that could potentially impact subsequent information collection or the accuracy and completeness of the problem solution, especially those likely to cause mistakes, carelessness, or confusion during problem-solving.

The question author does not intend to set traps or intentionally create confusion. Interpret the question in the most common, reasonable, and straightforward manner, without speculating about hidden meanings or unlikely scenarios. However, be aware that mistakes, imprecise wording, or inconsistencies may exist due to carelessness or limited subject expertise, rather than intentional ambiguity.

Additionally, when considering potential answers or interpretations, note that question authors typically favor more common and familiar expressions over overly technical, formal, or obscure terminology. They generally prefer straightforward and common-sense interpretations rather than being excessively cautious or academically rigorous in their wording choices.

Also, consider additional flagging issues such as:
- Potential mistakes or oversights introduced unintentionally by the question author due to his misunderstanding, carelessness, or lack of attention to detail.
- Terms or instructions that might have multiple valid interpretations due to ambiguity, imprecision, outdated terminology, or subtle wording nuances.
- Numeric precision, rounding requirements, formatting, or units that might be unclear, erroneous, or inconsistent with standard practices or provided examples.
- Contradictions or inconsistencies between explicit textual instructions and examples or contextual clues provided within the question itself.

Do NOT attempt to guess or infer correct answers, as complete factual information is not yet available. Your responsibility is purely analytical, proactively flagging points that deserve special attention or clarification during subsequent information collection and task solving. Avoid overanalyzing or listing trivial details that would not materially affect the task outcome.

Here is the question:

"""

    # Add Chinese-specific instructions if enabled
    if chinese_context:
        instruction += """

## 中文分析指导

如果问题涉及中文语境，请特别注意：

- **语言理解**：识别可能存在的中文表达歧义、方言差异或特定语境下的含义
- **文化背景**：考虑可能需要中文文化背景知识才能正确理解的术语或概念
- **信息获取**：标注需要使用中文搜索关键词才能获得准确信息的方面
- **格式要求**：识别中文特有的格式要求、表达习惯或答案形式
- **翻译风险**：标记直接翻译可能导致误解或信息丢失的关键术语
- **时效性**：注意中文信息源的时效性和地域性特征
- **分析输出**：使用中文进行分析和提示，确保语言一致性

"""

    # Add message ID for O3 messages (if configured)
    content = instruction + question
    if add_message_id:
        message_id = _generate_message_id()
        content = f"[{message_id}] {content}"

    response = await client.chat.completions.create(
        model="o3",
        messages=[{"role": "user", "content": content}],
        reasoning_effort="high",
    )

    result = response.choices[0].message.content

    # Check if result is empty, raise exception to trigger retry if empty
    if not result or not result.strip():
        raise ValueError("Hint extraction returned empty result")

    return result


@retry(
    wait=wait_exponential(multiplier=15),
    stop=stop_after_attempt(5),
    retry_error_callback=lambda retry_state: print(
        f"Retry attempt {retry_state.attempt_number} for get_gaia_answer_type"
    ),
)
async def get_gaia_answer_type(
    task_description: str, api_key: str, base_url: str = "https://api.openai.com/v1"
) -> str:
    client = AsyncOpenAI(api_key=api_key, timeout=600, base_url=base_url)

    instruction = f"""Input:
`{task_description}`

Question:
Determine the expected data type of the answer. For questions asking to "identify" something, focus on the final answer type, not the identification process. Format requirements in the question often hint at the expected data type. If the question asks you to write a specific word, return string. Choose only one of the four types below:
- number — a pure number (may include decimals or signs), e.g., price, distance, length
- date   — a specific calendar date (e.g., 2025-08-05 or August 5, 2025)
- time   — a specific time of day or formated time cost (e.g., 14:30 or 1:30.12)
- string — any other textual answer

Output:
Return exactly one of the [number, date, time, string], nothing else.
"""
    print(f"Answer type instruction: {instruction}")

    message_id = _generate_message_id()
    response = await client.chat.completions.create(
        model="gpt-4.1",
        messages=[{"role": "user", "content": f"[{message_id}] {instruction}"}],
    )
    answer_type = response.choices[0].message.content
    # Check if result is empty, raise exception to trigger retry if empty
    if not answer_type or not answer_type.strip():
        raise ValueError("answer type returned empty result")

    print(f"Answer type: {answer_type}")

    return answer_type.strip()


@retry(
    wait=wait_exponential(multiplier=15),
    stop=stop_after_attempt(5),
    retry_error_callback=lambda retry_state: print(
        f"Retry attempt {retry_state.attempt_number} for extract_gaia_final_answer"
    ),
)
async def extract_gaia_final_answer(
    task_description_detail: str,
    summary: str,
    api_key: str,
    chinese_context: bool,
    base_url: str = "https://api.openai.com/v1",
) -> str:
    """Use LLM to extract final answer from summary"""
    answer_type = await get_gaia_answer_type(task_description_detail, api_key, base_url)

    client = AsyncOpenAI(api_key=api_key, timeout=600, base_url=base_url)

    # Add Chinese-specific instructions and output format if enabled
    chinese_supplement = ""
    output_format_section = """
# Output Format

Return your analysis in this exact format:

**Step-by-step Analysis:**
[Your detailed reasoning process]

**Final Answer:** \\boxed{...}

**Confidence:** [0-100 integer]

**Supporting Evidence:** [Brief summary of evidence that supports this answer]

**Potential Weaknesses:** [Any limitations, uncertainties, or factors that might make this answer incorrect - be objective and thorough]
"""

    if chinese_context:
        chinese_supplement = """

## 中文答案抽取指导

如果原始问题或代理总结涉及中文内容，请遵循以下指导：

- **语境理解**：在分析代理总结和原始问题时，保持对中文语境的敏感性，理解可能的文化背景和表达习惯
- **答案识别**：在识别最佳答案时，优先考虑符合中文表达习惯的答案形式
- **格式处理**：对于中文特有的格式要求（如中文日期格式、中文数字表达等），确保答案符合中文用户的期望
- **术语准确性**：保持中文术语的准确性，避免因直译造成的表达不当
- **分析过程**：整个分析和推理过程应使用中文进行，确保语言一致性
- **最终答案**：确保最终答案符合中文语境下的表达方式和格式要求

---

"""
        output_format_section = """
# 输出格式

请严格按照以下格式返回你的分析：

**逐步分析：**
[你的详细推理过程]

**最终答案：** \\boxed{...}

**置信度：** [0-100整数]

**支持证据：** [支持此答案的证据简要总结]

**潜在不足：** [任何限制、不确定性或可能使此答案错误的因素 - 要客观且全面]
"""

    # Common confidence assessment section (unified for all languages)
    common_confidence_section = (
        """
# Confidence Assessment

Provide a confidence score (0-100) based on objective criteria for how likely this answer is to be judged correct by an automated verifier:

**Calibration Guidelines (use these as objective anchors):**
- **85-100**: Direct factual evidence found, no contradictions, formatting requirements clearly satisfied
- **70-84**: Strong supporting evidence with minor gaps or slight formatting uncertainty  
- **55-69**: Moderate evidence but requires interpretation, or some conflicting information exists
- **40-54**: Limited evidence, significant uncertainty, multiple plausible answers possible
- **25-39**: Weak evidence, mostly reasoning-based, likely incomplete information
- **0-24**: No supporting evidence found, pure speculation, or contradicts known facts

**Objective Calibration Checks:**
1. **Evidence Verifiability**: Can the key facts be directly verified from the agent summary?
2. **Contradiction Test**: Does anything in the summary contradict this answer?  
3. **Completeness Test**: Does the summary contain sufficient information to answer confidently?
4. **Formatting Clarity**: Are the format requirements unambiguous and correctly followed?

Rate conservatively - if unsure between two ranges, choose the lower one.

---
"""
        + chinese_supplement
        + output_format_section
    )

    full_prompts = {
        "time": f"""# Inputs

* **Original Question**: `{task_description_detail}`
* **Agent Summary**: `{summary}`

---

# Task

1. **Independently derive** the best possible answer, step by step, based solely on evidence and reasoning from the Agent Summary. **Ignore the summary's "Final Answer" field** at this stage.
2. **Compare** your derived answer to the final answer provided in the Agent Summary (ignoring formatting and phrasing requirements at this stage).  
– If both are well supported by the summary's evidence, choose the one with stronger or clearer support.  
– If only one is well supported, use that one.
3. **Revise** your chosen answer to fully satisfy all formatting and phrasing requirements listed below (**Formatting rules**, **Additional constraints**, **Common pitfalls to avoid**, and **Quick reference examples**). These requirements override those in the original question if there is any conflict.

If no answer is clearly supported by the evidence, provide a well-justified educated guess. **Always wrap your final answer in a non-empty \\boxed{{...}}.**

---

# Output Guidelines

1. **Box the answer**
Wrap the answer in `\\boxed{{}}`.

2. **Answer type**
The boxed content must be a time.

3. **Formatting rules**
* Follow every formatting instruction in the original question (units, rounding, decimal places, etc.).
* Do **not** add any units (e.g., "s", "second", "seconds"), unless required.
* Ensure the correct unit (e.g., hours versus thousand hours); if the question specifies "thousand hours" or "1000 hours", treat it as the required unit — output a number like 13 (thousand hours) instead of 13000 (hours).
* If the question's written instructions for precision or rounding differ from the examples, treat the examples as authoritative — match their number of decimal places and rounding style.

4. **Additional constraints**
* If the **Agent Summary** is incomplete or unclear, provide the best possible answer (educated guess).

5. **Common pitfalls to avoid**
* Minor mismatches in the required format.
* Unit-conversion errors, especially with uncommon units.
* Incorrect precision, rounding or scale (e.g., 0.01 vs 0.001), **double-check the required level**.
* Conflicts between textual instructions and example formatting, just follow the example: if the question says to "retain the percentile" but the example shows 0.001, use 0.001 rather than 0.01.

---

# Quick reference examples

* If the question says to "rounding the seconds to the nearest hundredth", but the example shows "0.001", 1:23.4567 → 1:23.457
* If the question says to "rounding the seconds to the nearest hundredth", but the example shows "0.001", 10:08.47445 → 10:08.474
* If the question says to "round to one decimal place", but the example shows "0.01", 2:17.456 → 2:17.46
* If the question says to "round to the nearest minute", but the example keeps seconds ("0:45"), 3:44.8 → 3:45
* If the question says "keep three decimal places", but the example shows "0.1", 1:03.987 → 1:03.1
* If the question asks for "thousand hours", 13000 -> 13 

---
"""
        + common_confidence_section,
        "number": f"""# Inputs

* **Original Question**: `{task_description_detail}`
* **Agent Summary**: `{summary}`

---

# Task

1. **Independently derive** the best possible answer, step by step, based solely on evidence and reasoning from the Agent Summary. **Ignore the summary's "Final Answer" field** at this stage.
2. **Compare** your derived answer to the final answer provided in the Agent Summary (ignoring formatting and phrasing requirements at this stage).  
– If both are well supported by the summary's evidence, choose the one with stronger or clearer support.  
– If only one is well supported, use that one.
– For questions involving calculations, if your answer and the Agent Summary's final answer are numerically similar, prefer the summary's answer.
3. **Revise** your chosen answer to fully satisfy all formatting and phrasing requirements listed below (**Formatting rules**, **Additional constraints**, **Common pitfalls to avoid**, and **Quick reference examples**). These requirements override those in the original question if there is any conflict.

If no answer is clearly supported by the evidence, provide a well-justified educated guess. **Always wrap your final answer in a non-empty \\boxed{{...}}.**

---

# Output Guidelines

1. **Box the answer**
Wrap the answer in `\\boxed{{}}`.

2. **Answer type**
The boxed content must be a single number.

3. **Formatting rules**
* Follow every formatting instruction in the original question (units, rounding, decimal places, etc.).
* Use digits only; do **not** use words, commas or symbols (e.g., "$", "!", "?", "/").
* Do **not** add any units (e.g., "%", "$", "USD", "Å", "m", "m^2", "m^3"), unless required.
* Ensure the correct unit (e.g., grams versus kilograms, meters versus kilometers, hours versus thousand hours); if the question specifies "thousand hours" or "1000 hours", treat it as the required unit — output a number like 13 (thousand hours) instead of 13000 (hours).

4. **Additional constraints**
* If the **Agent Summary** is incomplete or unclear, provide the best possible answer (educated guess).

5. **Common pitfalls to avoid**
* Minor mismatches in the required format.
* Unit-conversion errors, especially with uncommon units.
* Incorrect precision, rounding or scale (e.g., 0.01 vs 0.001), **double-check the required level**.
* Conflicts between textual instructions and example formatting, just follow the example: if the question says to "retain the percentile" but the example shows 0.001, use 0.001 rather than 0.01.
* Do not partially convert text-based numbers—ensure full and accurate conversion (e.g., "one hundred million" → 100000000, not 100).

---

# Quick reference examples

* $100 → 100
* 100 USD → 100
* €50 → 50
* £75 → 75
* ¥1,000 → 1000
* 1,234 m → 1234
* 3,456,789 kg → 3456789
* 70% → 70
* 12.5% → 12.5
* 0.045 m³ → 0.045
* 0.045 m^3 → 0.045
* −40 °C → -40
* 100 km/h → 100
* 5000 m^2 → 5000
* 2.54 cm → 2.54
* 50 kg → 50
* 4.0 L → 4
* 13 thousand hours → 13
* Page 123/456 → 123/456
* 100 million → 100000000
* 200 Ω → 200
* 200 Å → 200
* 9.81 m/s² → 9.81
* 0 dB → 0

---
"""
        + common_confidence_section,
        "string": f"""# Inputs

* **Original Question**: `{task_description_detail}`
* **Agent Summary**: `{summary}`

---

# Task

1. **Independently derive** the best possible answer, step by step, based solely on evidence and reasoning from the Agent Summary. **Ignore the summary's "Final Answer" field** at this stage.
2. **Compare** your derived answer to the final answer provided in the Agent Summary (ignoring formatting and phrasing requirements at this stage).  
– If both are well supported by the summary's evidence, choose the one with stronger or clearer support.  
– If only one is well supported, use that one.
3. **Revise** your chosen answer to fully satisfy all formatting and phrasing requirements listed below (**Formatting rules**, **Additional constraints**, **Common pitfalls to avoid**, and **Quick reference examples**). These requirements override those in the original question if there is any conflict.

If no answer is clearly supported by the evidence, provide a well-justified educated guess. **Always wrap your final answer in a non-empty \\boxed{{...}}.**

---

# Output Guidelines

1. **Box the answer**
Wrap the final answer in \\boxed{{...}}.

2. **Answer type**
The boxed content must be **one** of:
* a single short phrase (fewest words possible)
* a comma-separated list of numbers and/or strings

3. **Formatting rules**
* Follow every formatting instruction in the original question (alphabetization, sequencing, units, rounding, decimal places, etc.).
* Omit articles and abbreviations unless explicitly present in the expected answer.
* If a string contains numeric information, spell out the numbers **unless** the question itself shows them as digits.
* Do **not** end the answer with ".", "!", "?", or any other punctuation.
* Use only standard ASCII quotation marks ("" and ''), **not** stylized or curly quotation marks (such as “ ” ‘ ’).
* Remove invisible or non-printable characters.
* If the output is lists, apply the rules item-by-item.
* Avoid unnecessary elaboration - keep the answer as short as possible
    - Do **not** add "count", "number", "count of", "total", or similar quantifying words when the noun itself already refers to the quantity (e.g., use the bare noun form only).
    - No geographical modifiers (e.g., "Western", "Southern"), 
    - Use the simplest, most commonly accepted term for a substance or object (e.g., "diamond" instead of "crystalline diamond", "silicon" instead of "silicon crystals")
* For mathematical symbols, match the symbol style in the question; never substitute LaTeX commands (e.g., use ≤, not \\leq, use pure text, not \\text{{}}, use ↔, not \\leftrightarrow).
* For birthplaces, give the name as it was at the time of birth, not the current name.

4. **Additional constraints**
* If the Agent Summary is incomplete or unclear, provide the best possible answer (educated guess).
* Keep the answer as short and direct as possible—no explanations or parenthetical notes.

5. **Common pitfalls to avoid**
* Minor mismatches between required and produced formats.
* Conflicts between textual instructions and example formatting—follow the example.
* **Names**: give only the commonly used first + last name (no middle name unless requested).
* **Countries**: use the common name (e.g., "China", "Brunei")
* **Locations**: output only the requested location name, without including time, modifiers (e.g., "The Castle", "The Hotel")
* When the question provides examples of expected format (e.g., "ripe strawberries" not "strawberries"), follow the exact wording style shown in the examples, preserving all descriptive terms and adjectives as demonstrated.
* Answer with historically location names when the Agent Summary provides. Never override a historically location name. For example, a birthplace should be referred to by the name it had at the time of birth (i.e., answer the original name).
* For questions asking to "identify" something, focus on the final answer, not the identification process.

---

# Quick reference examples

* INT. THE CASTLE – DAY 1 → The Castle
* INT. THE HOTEL – NIGHT → The Hotel
* INT. THE SPACESHIP – DAWN → The Spaceship
* INT. THE LIBRARY – EVENING → The Library
* INT. CLASSROOM #3 – MORNING → Classroom #3
* People's Republic of China → China
* citation count → citations
* Brunei Darussalam → Brunei
* United States of America → United States
* Republic of Korea → South Korea
* New York City, USA → New York City
* São Paulo (Brazil) → São Paulo
* John Michael Doe → John Doe
* Mary Anne O'Neil → Mary O'Neil
* Dr. Richard Feynman → Richard Feynman
* INT. ZONE 42 – LEVEL B2 → Zone 42 – Level B2
* INT. THE UNDERWATER BASE – MIDNIGHT → The Underwater Base
* Sam’s Home → Sam's Home
* Mike’s phone → Mike's phone

---
"""
        + common_confidence_section,
    }

    full_prompt = full_prompts.get(
        answer_type if answer_type in ["number", "time"] else "string"
    )

    print("Extract Final Answer Prompt:")
    print(full_prompt)

    message_id = _generate_message_id()
    response = await client.chat.completions.create(
        model="o3",
        messages=[{"role": "user", "content": f"[{message_id}] {full_prompt}"}],
    )
    result = response.choices[0].message.content

    # Check if result is empty, raise exception to trigger retry if empty
    if not result or not result.strip():
        raise ValueError("Final answer extraction returned empty result")

    # Verify boxed answer exists
    boxed_match = re.search(r"\\boxed{([^}]*)}", result)
    if not boxed_match:
        raise ValueError("Final answer extraction returned empty answer")

    print("response:", result)

    # Return the full response directly for downstream LLM processing
    # This contains all structured information: analysis, boxed answer, confidence, evidence, and weaknesses
    return result


@retry(
    wait=wait_exponential(multiplier=15),
    stop=stop_after_attempt(5),
    retry_error_callback=lambda retry_state: print(
        f"Retry attempt {retry_state.attempt_number} for extract_browsecomp_zh_final_answer"
    ),
)
async def extract_browsecomp_zh_final_answer(
    task_description_detail: str,
    summary: str,
    api_key: str,
    base_url: str = "https://api.openai.com/v1",
) -> str:
    """Use LLM to extract final answer from summary"""
    client = AsyncOpenAI(api_key=api_key, timeout=600, base_url=base_url)

    chinese_supplement = """

## 中文答案抽取指导

如果原始问题或代理总结涉及中文内容，请遵循以下指导：

- **语境理解**：在分析代理总结和原始问题时，保持对中文语境的敏感性，理解可能的文化背景和表达习惯
- **答案识别**：在识别最佳答案时，优先考虑符合中文表达习惯的答案形式
- **格式处理**：对于中文特有的格式要求（如中文日期格式、中文数字表达等），确保答案符合中文用户的期望
- **术语准确性**：保持中文术语的准确性，避免因直译造成的表达不当
- **分析过程**：整个分析和推理过程应使用中文进行，确保语言一致性
- **最终答案**：确保最终答案符合中文语境下的表达方式和格式要求
- **等价名称**：如果最终答案有多种等价名称，请在响应中明确提及 **所有** 等价的中英文名称

---

"""
    output_format_section = """
# 输出格式

请严格按照以下格式返回你的分析：

**逐步分析：**
[你的详细推理过程]

**最终答案：** \\boxed{...}

**置信度：** [0-100整数]

**支持证据：** [支持此答案的证据总结]
"""

    # Common confidence assessment section (unified for all languages)
    common_confidence_section = (
        """
# 置信度评估

请根据客观标准，对该答案被自动验证器判定为正确的可能性进行打分（0-100分）：

**校准指南（请以此为客观参考）：**
- **85-100**：有直接的事实证据支持，无矛盾，格式要求完全满足
- **70-84**：有强有力的支持证据，但存在小的缺口或格式略有不确定
- **55-69**：有一定证据，但需要解释，或存在部分相互矛盾的信息
- **40-54**：证据有限，不确定性较大，可能存在多个合理答案
- **25-39**：证据薄弱，主要依赖推理，信息可能不完整
- **0-24**：没有支持证据，纯属猜测，或与已知事实相矛盾

**客观校准检查：**
1. **证据可验证性**：关键事实能否直接从代理总结中验证？
2. **矛盾检测**：总结中是否有内容与该答案相矛盾？
3. **完整性检查**：总结中是否包含足够信息以有信心地作答？
4. **格式清晰度**：格式要求是否明确且被正确遵循？

请保守打分——如果在两个区间之间犹豫，请选择较低的分数。

---
"""
        + chinese_supplement
        + output_format_section
    )

    full_prompt = (
        f"""# 输入

* **原始问题**：`{task_description_detail}`
* **Agent总结**：`{summary}`

---

# 任务

1. **独立推导**：仅根据Agent总结中的证据和推理，逐步独立推导出最优答案。**此阶段请忽略总结中的“最终答案”字段。**
2. **对比**：将你推导出的答案与Agent总结中给出的最终答案进行对比（此阶段忽略格式和表述要求）。  
   – 如果两者都得到了总结证据的有力支持，选择支持更充分或更清晰的那个。  
   – 如果只有一个答案有充分证据支持，则采用该答案。
3. **修订**：将你选定的答案修订为完全符合下方所有格式和表述要求（**格式规则**、**附加约束**、**常见错误**）。
4. **输出**：你需要在输出中展现你的分析过程，并给出最终答案。

如果没有答案能被证据明确支持，请给出有充分理由的最佳猜测。**最终答案必须用非空的 \\boxed{{...}} 包裹。**

---

# 输出指南

1. **答案加框**
用 `\\boxed{{}}` 包裹最终答案。

2. **格式规则**
* 严格遵循原始问题中的所有格式说明（单位、四舍五入、保留小数位等）。
* 确保使用正确的单位（如小时与千小时）；如果题目要求“千小时”或“1000小时”，则以此为准——输出如 13（千小时），而不是 13000（小时）。
* 如果题目的文字说明与示例在精度或四舍五入上有出入，以示例为准——匹配其小数位数和四舍五入方式。
* 如题目答案是地名、人名、组织名、国家名等，请给出标准全称，并用括号注释常用说法或等价说法（如有）。
* 如题目答案有多种称呼方式、翻译方式，请给出所有中英文等价表达，并用明确标注“等价表达不唯一”。

3. **附加约束**
* 如果**Agent总结**内容不完整或不清晰，请给出最佳答案（合理猜测）。
* 如果一个答案实体有多个名称、说法、叫法，请在最终答案用括号注释**所有等价的名称**，包括官方中英文对照（如有）。

4. **常见错误**
* 拥有官方中文名称的英文实体没有给出中文名称。
* 拥有多个等价表达的答案、只给出了一种说法。

"""
        + common_confidence_section
    )

    print("Extract Final Answer Prompt:")
    print(full_prompt)

    message_id = _generate_message_id()
    response = await client.chat.completions.create(
        model="o3",
        messages=[{"role": "user", "content": f"[{message_id}] {full_prompt}"}],
        reasoning_effort="medium",
    )
    result = response.choices[0].message.content

    # Check if result is empty, raise exception to trigger retry if empty
    if not result or not result.strip():
        raise ValueError("Final answer extraction returned empty result")

    # Verify boxed answer exists
    boxed_match = re.search(r"\\boxed{([^}]*)}", result)
    if not boxed_match:
        raise ValueError("Final answer extraction returned empty answer")

    print("response:", result)

    # Return the full response directly for downstream LLM processing
    # This contains all structured information: analysis, boxed answer, confidence, evidence, and weaknesses
    return result
