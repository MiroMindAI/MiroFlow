import glob
import json
import os
import sys
import re
import ast
import types


def str_to_pricing(pricing_str):
    if "fee" not in pricing_str:
        return float(eval(pricing_str))
    else:
        return eval(f"lambda fee: {pricing_str}")


def _update_tool_usage(total_usage: dict, usage: dict):
    for key, value in usage.items():
        if key not in total_usage:
            total_usage[key] = value
        else:
            if not isinstance(value, dict):
                try:
                    total_usage[key] += value
                except TypeError:
                    raise TypeError(
                        f"Type error when updating tool usage with {total_usage[key]} and {value}"
                    )

            elif isinstance(value, dict) and "sandbox_" not in key:
                for sub_key, sub_value in value.items():
                    if sub_key not in total_usage[key]:
                        total_usage[key][sub_key] = sub_value
                    else:
                        try:
                            total_usage[key][sub_key] += sub_value
                        except TypeError:
                            raise TypeError(
                                f"Type error when updating tool usage with {total_usage[key][sub_key]} and {sub_value}"
                            )
            else:
                for sub_key, sub_value in value.items():
                    total_usage[key][sub_key] = sub_value


def extract_tool_usage_from_log(run_dir, tool_usage_dict):
    # Traverse all task_{task_id}_attempt_*.log files to extract score
    log_files = glob.glob(os.path.join(run_dir, "task_*_attempt_*.json"))
    for log_file in log_files:
        task_id = log_file.split("/")[-1].split("_")[1]
        tool_usage_dict[task_id] = {}
        total_usage = {}
        with open(log_file, "r") as f:
            data = json.load(f)
        for d in data["step_logs"]:
            if d["step_name"] == "tool_usage":
                log = d["message"]
                log = ast.literal_eval(log)
                _update_tool_usage(total_usage, log)
        for tool, usage in total_usage.items():
            if tool.startswith("sandbox_"):
                if f"E2B_{usage["cpu"]}_{usage["mem"]}" not in tool_usage_dict[task_id]:
                    tool_usage_dict[task_id][f"E2B_{usage["cpu"]}_{usage["mem"]}"] = 0
                tool_usage_dict[task_id][f"E2B_{usage["cpu"]}_{usage["mem"]}"] += (
                    usage["end_time"] - usage["start_time"]
                )
                continue
            if tool not in tool_usage_dict[task_id]:
                tool_usage_dict[task_id][tool] = usage
            else:
                if not isinstance(usage, dict):
                    try:
                        tool_usage_dict[task_id][tool] += usage
                    except TypeError:
                        raise TypeError(
                            f"Type error when updating tool usage with {tool_usage_dict[task_id][tool]} and {usage}"
                        )
                else:
                    for sub_key, sub_value in usage.items():
                        if sub_key not in tool_usage_dict[task_id][tool]:
                            tool_usage_dict[task_id][tool][sub_key] = sub_value
                        else:
                            try:
                                tool_usage_dict[task_id][tool][sub_key] += sub_value
                            except TypeError:
                                raise TypeError(
                                    f"Type error when updating tool usage with {tool_usage_dict[task_id][tool][sub_key]} and {sub_value}"
                                )


def extract_llm_usage_from_log(run_dir, llm_usage_dict):
    # Traverse all task_{task_id}_attempt_*.log files to extract score
    log_files = glob.glob(os.path.join(run_dir, "task_*_attempt_*.json"))
    for log_file in log_files:
        task_id = log_file.split("/")[-1].split("_")[1]
        llm_usage_dict[task_id] = {}
        with open(log_file, "r") as f:
            data = json.load(f)
        for d in data["step_logs"]:
            if d["step_name"] == "usage_calculation":
                log = d["message"]
                model_match = re.search(r"Usage log:\s*\[(.*?)\]", log)
                if model_match:
                    model_raw = model_match.group(1)
                    model_formatted = model_raw.replace(" | ", "|")
                else:
                    raise ValueError(f"Model not found in log: {log}")

                cached_read_match = re.search(r"Cached Read:\s*(\d+)", log)
                cached_read_input = (
                    int(cached_read_match.group(1)) if cached_read_match else None
                )
                cached_write_match = re.search(r"Cached Write:\s*(\d+)", log)
                cached_write_input = (
                    int(cached_write_match.group(1)) if cached_write_match else None
                )

                uncached_match = re.search(r"Uncached:\s*(\d+)", log)
                uncached_input = (
                    int(uncached_match.group(1)) if uncached_match else None
                )

                total_output_match = re.search(r"Total Output:\s*(\d+)", log)
                total_output = (
                    int(total_output_match.group(1)) if total_output_match else None
                )

                total_fee_match = re.search(r"Total Fee:\s*(\d+(?:\.\d+)?)", log)
                total_fee = float(total_fee_match.group(1)) if total_fee_match else None

                if model_formatted in llm_usage_dict[task_id]:
                    llm_usage_dict[task_id][model_formatted]["cached_read_input"] += (
                        cached_read_input
                    )
                    llm_usage_dict[task_id][model_formatted]["cached_write_input"] += (
                        cached_write_input
                    )
                    llm_usage_dict[task_id][model_formatted]["uncached_input"] += (
                        uncached_input
                    )
                    llm_usage_dict[task_id][model_formatted]["total_output"] += (
                        total_output
                    )
                    llm_usage_dict[task_id][model_formatted]["total_fee"] += total_fee
                else:
                    llm_usage_dict[task_id][model_formatted] = {
                        "cached_read_input": cached_read_input,
                        "cached_write_input": cached_write_input,
                        "uncached_input": uncached_input,
                        "total_output": total_output,
                        "total_fee": total_fee,
                    }


def calculate_tool_fee(usage_dict):
    total_fee = 0
    with open("utils/usage/pricing.json", "r") as f:
        pricing = json.load(f)
    pricing = pricing["tool"]
    for _, _usage in usage_dict.items():
        for tool, usage in _usage.items():
            ToolInPricing = False
            if "openrouter" in tool:
                total_fee += usage["cost"]
                ToolInPricing = True
            elif "E2B" in tool:
                mem = int(int(tool.split("_")[-1]) / (1024 * 1024))
                cpu = int(tool.split("_")[1])
                total_fee += (
                    eval(pricing["E2B"]["cpu"]) * cpu
                    + eval(pricing["E2B"]["mem"]) * mem
                )
                ToolInPricing = True
            else:
                for key in pricing.keys():
                    if key.lower() in tool.lower():
                        if not isinstance(pricing[key], dict):
                            pricing_temp = str_to_pricing(pricing[key])
                            total_fee += (
                                pricing_temp * usage
                                if not isinstance(pricing_temp, types.FunctionType)
                                else pricing_temp(usage) * usage
                            )
                            ToolInPricing = True
                        else:
                            for model, fee in pricing[key].items():
                                if model in tool:
                                    if isinstance(fee, dict):
                                        for i in fee.keys():
                                            if i not in usage:
                                                continue
                                            # total_fee += eval(fee[i]) * usage[i]
                                            pricing_temp = str_to_pricing(fee[i])
                                            total_fee += (
                                                pricing_temp * usage[i]
                                                if not isinstance(
                                                    pricing_temp, types.FunctionType
                                                )
                                                else pricing_temp(usage[i]) * usage[i]
                                            )
                                    else:
                                        # total_fee += eval(fee) * usage
                                        pricing_temp = str_to_pricing(fee)
                                        total_fee += (
                                            pricing_temp * usage
                                            if not isinstance(
                                                pricing_temp, types.FunctionType
                                            )
                                            else pricing_temp(usage) * usage
                                        )
                                    ToolInPricing = True
                                    break
                        break
            if not ToolInPricing:
                raise ValueError(f"Tool {tool} not found in pricing")
    return total_fee


def calculate_llm_fee(usage_dict):
    total_fee = 0
    with open("utils/usage/pricing.json", "r") as f:
        pricing = json.load(f)
    pricing = pricing["llm"]
    for _, _usage in usage_dict.items():
        for model, usage in _usage.items():
            FindModel = False
            if usage["total_fee"] > 0:
                assert (
                    "openrouter" in model.lower()
                ), f"Model {model} not found in openrouter but has total fee!"
                total_fee += usage["total_fee"] * 1.055
                FindModel = True
            else:
                if "openrouter" not in model.lower():
                    model_client = model.split("|")[0]
                    model_name = model.split("|")[1]
                    for client, model_dict in pricing.items():
                        if client.lower() in model_client.lower():
                            for name, fee in model_dict.items():
                                if name.lower() == model_name.lower():
                                    FindModel = True
                                    for token_type in fee.keys():
                                        if token_type == "total_fee":
                                            continue
                                        # total_fee += eval(fee[token_type]) * usage[token_type]
                                        pricing_temp = str_to_pricing(fee[token_type])
                                        total_fee += (
                                            pricing_temp * usage[token_type]
                                            if not isinstance(
                                                pricing_temp, types.FunctionType
                                            )
                                            else pricing_temp(usage[token_type])
                                            * usage[token_type]
                                        )
                                    break
                            break
            if not FindModel:
                raise ValueError(f"Model {model} not found in pricing")
    return total_fee


def calculate_average_fee(results_dir):
    if not os.path.exists(results_dir):
        print(f"Results directory does not exist: {results_dir}")
        sys.exit(1)

    # print(f"Analyzing results from: {results_dir}")

    tool_usage_dict = {}
    llm_usage_dict = {}
    extract_tool_usage_from_log(results_dir, tool_usage_dict)
    extract_llm_usage_from_log(results_dir, llm_usage_dict)
    # print(tool_usage_dict)
    # print(llm_usage_dict)
    total_tool_fee = calculate_tool_fee(tool_usage_dict)
    total_llm_fee = calculate_llm_fee(llm_usage_dict)
    # print(f"Total tool fee: {total_tool_fee}")
    # print(f"Total llm fee: {total_llm_fee}")
    # print(f"Total fee: {total_tool_fee + total_llm_fee}")
    count = sum(
        1
        for f in os.listdir(results_dir)
        if f.endswith(".json") and os.path.isfile(os.path.join(results_dir, f))
    )
    return (total_tool_fee + total_llm_fee) / count


def scan_error_logs(base_dir="logs"):
    def _find_2025_dirs(root):
        try:
            with os.scandir(root) as it:
                for entry in it:
                    if not entry.is_dir():
                        continue
                    if entry.name.startswith("2025"):
                        yield entry.path
                    else:
                        yield from _find_2025_dirs(entry.path)
        except PermissionError:
            pass
        except FileNotFoundError:
            pass

    for d in _find_2025_dirs(base_dir):
        print(d)
        print("Average fee:", calculate_average_fee(d))


scan_error_logs("logs")
