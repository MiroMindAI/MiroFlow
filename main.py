# SPDX-FileCopyrightText: 2025 MiromindAI
#
# SPDX-License-Identifier: Apache-2.0

# import src.utils.calculate_average_score
# import src.utils.calculate_score_from_log
import common_benchmark
# import dotenv
# import src.utils.eval_answer_from_log
import fire
import hydra
# import src.utils.trace_single_task
# import src.utils.prepare_benchmark.main
from src.logging.logger import bootstrap_logger
from config import config_name, config_path, debug_config
from rich.traceback import install
import os

LOGGER_LEVEL = os.getenv("LOGGER_LEVEL", "INFO")


def print_config(*args):
    dotenv.load_dotenv()
    print("LOGGER_LEVEL=", LOGGER_LEVEL)
    logger = bootstrap_logger(level=LOGGER_LEVEL)
    with hydra.initialize_config_dir(config_dir=config_path(), version_base=None):
        cfg = hydra.compose(config_name=config_name(), overrides=list(args))
        debug_config(cfg, logger)


if __name__ == "__main__":
    install(suppress=[fire, hydra], show_locals=True)
    fire.Fire(
        {
            "print-config": print_config,
            # "trace": src.utils.trace_single_task.main,
            "common-benchmark": common_benchmark.main,
            # "eval-answer": src.utils.eval_answer_from_log.main,
            # "avg-score": src.utils.calculate_average_score.main,
            # "score-from-log": src.utils.calculate_score_from_log.main,
            # "prepare-benchmark": src.utils.prepare_benchmark.main,
        }
    )
