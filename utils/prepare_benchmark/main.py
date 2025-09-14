# SPDX-FileCopyrightText: 2025 MiromindAI
#
# SPDX-License-Identifier: Apache-2.0

import dataclasses
import pathlib

import dotenv
import fire

from utils.prepare_benchmark.gen_browsecomp import (
    gen_browsecomp_test,
    gen_browsecomp_zh_test,
)
from utils.prepare_benchmark.gen_frames import gen_frames_test
from utils.prepare_benchmark.gen_gaia import gen_gaia_validation
from utils.prepare_benchmark.gen_gaia_text_only import gen_gaia_text_only
from utils.prepare_benchmark.gen_hle import gen_hle_test
from utils.prepare_benchmark.gen_webwalkerqa import gen_webwalkerqa


@dataclasses.dataclass
class _Env:
    supported = (
        "gaia-val",
        "gaia-val-text-only",
        "frames-test",
        "webwalkerqa",
        "browsecomp-test",
        "browsecomp-zh-test",
        "hle",
    )
    meta_filename = "standardized_data.jsonl"
    data_dir: pathlib.Path
    hf_token: str

    @classmethod
    def from_dotenv(cls):
        cfg = dotenv.dotenv_values()
        base = pathlib.Path.cwd()
        middle = pathlib.Path(cfg.get("DATA_DIR", "./data"))  # type: ignore
        env = cls(
            data_dir=(base / middle).absolute(),
            hf_token=cfg.get("HF_TOKEN", ""),  # type: ignore
        )
        return env


def _prepare_filesystem(env: _Env):
    folder = env.data_dir.absolute()
    folder.mkdir(parents=True, exist_ok=True)
    for dataset in env.supported:
        ds_folder = folder / dataset
        ds_folder.mkdir(parents=True, exist_ok=True)


def _prepare_dataset(env: _Env, dataset: str):
    match dataset:
        case "browsecomp-test":

            def gen():
                for x in gen_browsecomp_test(env.hf_token):
                    yield x

            return gen
        case "browsecomp-zh-test":

            def gen():
                for x in gen_browsecomp_zh_test(env.hf_token):
                    yield x

            return gen
        case "frames-test":

            def gen():
                for x in gen_frames_test(env.hf_token):
                    yield x

            return gen
        case "gaia-val":

            def gen():
                for x in gen_gaia_validation(env.hf_token):
                    yield x

            return gen
        case "gaia-val-text-only":
            return gen_gaia_text_only
        case "webwalkerqa":

            def gen():
                for x in gen_webwalkerqa(env.hf_token):
                    yield x

            return gen
        case "hle":

            def gen():
                for x in gen_hle_test(env.hf_token, env.data_dir):
                    yield x

            return gen
        case _:
            raise ValueError("not supported")


def rm():
    "remove local files from benchmark"
    env = _Env.from_dotenv()
    print(env)
    for dataset in env.supported:
        ds_file = env.data_dir / dataset / env.meta_filename
        ds_file.unlink(missing_ok=True)
        ds_folder = env.data_dir / dataset
        ds_folder.rmdir()
    env.data_dir.rmdir()


def ls():
    "list all supported benchmark"
    env = _Env.from_dotenv()
    print(env)
    for dataset in env.supported:
        ds_folder = env.data_dir / dataset / env.meta_filename
        print(
            "dataset:",
            dataset,
            "file:",
            str(ds_folder.absolute()),
            "status: ",
            ds_folder.exists(),
        )


def get(dataset: str):
    "download a specific benchmark"
    env = _Env.from_dotenv()
    ds_gen = _prepare_dataset(env, dataset)
    _prepare_filesystem(env)
    ds_file = env.data_dir / dataset / env.meta_filename
    with open(ds_file, mode="w") as f:
        for task in ds_gen():
            f.write(task.to_json().decode() + "\n")
    print("\n" + "=" * 80)
    print(f"  Benchmark: {dataset}")
    print(f"  Saved to: {ds_file}")
    print("=" * 80 + "\n")


if __name__ == "__main__":
    fire.Fire(
        {
            "rm": rm,
            "ls": ls,
            "get": get,
        }
    )
