import dotenv
import fire
import hydra
from miroflow.logging.logger import bootstrap_logger
from miroflow.prebuilt.config import config_name, config_path, debug_config
from rich.traceback import install

import calculate_average_score
import calculate_score_from_log
import eval_answer_from_log
import trace_single_task


def print_config(*args):
    dotenv.load_dotenv()
    logger = bootstrap_logger()
    with hydra.initialize_config_dir(config_dir=config_path(), version_base=None):
        cfg = hydra.compose(config_name=config_name(), overrides=list(args))
        debug_config(cfg, logger)


if __name__ == "__main__":
    install(suppress=[fire, hydra], show_locals=True)
    import sys

    if len(sys.argv) < 2:
        print("Available commands:")
        print("  print-config    - Print configuration")
        print("  trace          - Run single task trace")
        print("  common-benchmark - Run benchmark evaluation")
        print("  eval-answer    - Evaluate answers from log")
        print("  avg-score      - Calculate average score")
        print("  score-from-log - Calculate score from log")
        print("\nExample: python main.py common-benchmark")
        sys.exit(1)

    command = sys.argv[1]
    args = sys.argv[2:]

    if command == "print-config":
        print_config(*args)
    elif command == "trace":
        trace_single_task.main(*args)
    elif command == "common-benchmark":
        # For common-benchmark, call it directly - it will use @hydra.main
        import subprocess

        subprocess.run(["python", "common_benchmark.py"] + args)
    elif command == "eval-answer":
        eval_answer_from_log.main(*args)
    elif command == "avg-score":
        calculate_average_score.main(*args)
    elif command == "score-from-log":
        calculate_score_from_log.main(*args)
    else:
        print(f"Unknown command: {command}")
        sys.exit(1)
