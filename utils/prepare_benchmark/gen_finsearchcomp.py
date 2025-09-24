# SPDX-FileCopyrightText: 2025 MiromindAI
#
# SPDX-License-Identifier: Apache-2.0

from typing import Generator, MutableMapping

from datasets import load_dataset

from utils.prepare_benchmark.common import Task

def gen_finsearchcomp(hf_token: str) -> Generator[Task, None, None]:
    """
    Generate FinSearchComp dataset tasks in MiroFlow format
    
    Args:
        hf_token: Hugging Face token for dataset access
        
    Yields:
        Task: Standardized task objects
    """
    dataset = load_dataset("ByteSeedXpert/FinSearchComp")
    
    for split_name, split_data in dataset.items():
        for idx, sample in enumerate(split_data):
            # Extract task information
            task_id = sample.get("prompt_id", f"finsearchcomp_{split_name}_{idx}")
            task_question = sample.get("prompt", "")
            response_reference = sample.get("response_reference", "")
            judge_prompt_template = sample.get("judge_prompt_template", "")
            judge_system_prompt = sample.get("judge_system_prompt", "")
            label = sample.get("label", "")
            
            # Create metadata dictionary
            metadata: MutableMapping = {
                "judge_prompt_template": judge_prompt_template,
                "judge_system_prompt": judge_system_prompt,
                "label": label,
                "source": "ByteSeedXpert/FinSearchComp",
                "split": split_name,
                "original_id": sample.get("prompt_id", ""),
                "dataset_name": "FinSearchComp"
            }
            
            # Create standardized Task object
            task = Task(
                task_id=task_id,
                task_question=task_question,
                ground_truth=response_reference,  # Futurex-Online doesn't have ground truth
                file_path=None,   # No file attachments
                metadata=metadata,
            )
            
            yield task
    return
    