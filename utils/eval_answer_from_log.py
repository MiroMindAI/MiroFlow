# SPDX-FileCopyrightText: 2025 MiromindAI
#
# SPDX-License-Identifier: Apache-2.0

import glob
import json
import os
import sys

from utils.eval_utils import verify_answer_for_datasets


async def main(input_dir: str, benchmark_name: str):
    if not os.path.isdir(input_dir):
        print(f"Input directory does not exist: {input_dir}")
        sys.exit(1)

    # Find all log files (json) recursively in input_dir
    log_files = glob.glob(os.path.join(input_dir, "*Z.json"))
    if not log_files:
        print(f"No log files found in {input_dir}")
        sys.exit(1)

    print(f"Found {len(log_files)} log files in {input_dir}")

    success_id = []
    fail_id = []
    for log_file in log_files:
        try:
            with open(log_file, "r", encoding="utf-8") as f:
                data = json.load(f)
            # Extract relevant fields
            question = data.get("task_question", "")
            ground_truth = data.get("ground_truth", "")
            predicted_answer = data.get("final_boxed_answer", "")
            metadata = data.get("input", {}).get("metadata", {})

            # If already has judge result, skip
            # if "judge_result" in data and data["judge_result"] in ("CORRECT", "INCORRECT"):
            #     print(f"Log {log_file} already has judge result: {data['judge_result']}")
            #     continue
            # Call LLM judge
            result = await verify_answer_for_datasets(
                openai_client=None,  # type: ignore
                benchmark_name=benchmark_name,
                question=question,
                target=ground_truth,
                predicted_answer=predicted_answer,
                metadata=metadata,  # Now metadata is available from log files
            )
            print(f"{os.path.basename(log_file)}: {result}")
            # Optionally, update the log file with the result
            # data["judge_result"] = result
            # with open(log_file, "w", encoding="utf-8") as f:
            #     json.dump(data, f, ensure_ascii=False, indent=2)
            if result == "CORRECT":
                success_id.append(log_file)
            else:
                fail_id.append(log_file)
        except Exception as e:
            print(f"Error processing {log_file}: {e}")

    print(f"Processed {len(log_files)} files.")
    print(f"Success {len(success_id)} files.")
    print(f"Fail {len(fail_id)} files.")
    print(f"Success rate: {len(success_id) / len(log_files)}")
    print(f"Fail rate: {len(fail_id) / len(log_files)}")
