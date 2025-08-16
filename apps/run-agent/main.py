import dotenv
import fire
import hydra
from miroflow.logging.logger import bootstrap_logger
from miroflow.prebuilt.config import config_name, config_path, debug_config
from rich.traceback import install

import calculate_average_score
import calculate_score_from_log
import common_benchmark
import eval_answer_from_log
import llm_solution_selector
import llm_majority_voter
import trace_single_task


def print_config(*args):
    dotenv.load_dotenv()
    logger = bootstrap_logger()
    with hydra.initialize_config_dir(config_dir=config_path(), version_base=None):
        cfg = hydra.compose(config_name=config_name(), overrides=list(args))
        debug_config(cfg, logger)


if __name__ == "__main__":
    install(suppress=[fire, hydra], show_locals=True)
    fire.Fire(
        {
            "print-config": print_config,
            "trace": trace_single_task.main,
            "common-benchmark": common_benchmark.main,
            "eval-answer": eval_answer_from_log.main,
            "avg-score": calculate_average_score.main,
            "score-from-log": calculate_score_from_log.main,
            "llm-solution-selector": llm_solution_selector.main,
            "llm-majority-voter": llm_majority_voter.main,
        }
    )
