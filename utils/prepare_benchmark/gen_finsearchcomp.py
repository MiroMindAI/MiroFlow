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
            ground_truth_finance = sample.get("ground_truth", "")
            
            # Create metadata dictionary with all original fields
            metadata: MutableMapping = {
                "source": "ByteSeedXpert/FinSearchComp",
                "split": split_name,
                "original_id": sample.get("prompt_id", ""),
                "dataset_name": "FinSearchComp",
                "response_reference": response_reference,
                "ground_truth_finance": ground_truth_finance,
            }
            
            # Add all other fields from sample to metadata (including judge prompts)
            for key, value in sample.items():
                if key not in ["prompt_id", "prompt", "response_reference", "ground_truth"]:
                    metadata[key] = value
            
            # Determine the primary ground truth for evaluation
            # Priority: response_reference > ground_truth_finance
            if response_reference:
                ground_truth_task = response_reference
            elif ground_truth_finance:
                ground_truth_task = ground_truth_finance
            else:
                ground_truth_task = ""  # Fallback to empty string
            
            # Create standardized Task object
            task = Task(
                task_id=task_id,
                task_question=task_question,
                ground_truth=ground_truth_task,
                file_path=None,   # No file attachments
                metadata=metadata,
            )
            
            yield task
    return
    