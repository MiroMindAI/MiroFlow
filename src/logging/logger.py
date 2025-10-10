# SPDX-FileCopyrightText: 2025 MiromindAI
#
# SPDX-License-Identifier: Apache-2.0

import os
import zmq
import zmq.asyncio
import logging
from functools import lru_cache
from pathlib import Path
from typing import Literal, Dict
from contextvars import ContextVar
import hydra
from rich.console import Console
from rich.logging import RichHandler
import asyncio
import threading
from contextlib import contextmanager
TASK_CONTEXT_VAR: ContextVar[str | None] = ContextVar("CURRENT_TASK_ID", default=None)

class ZMQLogHandler(logging.Handler):
    def __init__(self, addr="tcp://127.0.0.1:6000", tool_name="unknown_tool"):
        super().__init__()
        ctx = zmq.Context()
        self.sock = ctx.socket(zmq.PUSH)
        self.sock.connect(addr)
        self.task_id = os.environ.get("TASK_ID", "0")
        self.tool_name = tool_name

    def emit(self, record):
        try:
            msg = f"{record.getMessage()}"
            self.sock.send_string(f"{self.task_id}||{self.tool_name}||{msg}")
        except Exception:
            self.handleError(record)

async def zmq_log_listener(bind_addr="tcp://127.0.0.1:6000"):
    ctx = zmq.asyncio.Context()
    sock = ctx.socket(zmq.PULL)
    sock.bind(bind_addr)

    root_logger = logging.getLogger()

    while True:
        raw = await sock.recv_string()
        if "|" in raw:
            task_id, tool_name, msg = raw.split("||", 2)

            record = root_logger.makeRecord(
                name=f'[TOOL] {tool_name}',
                level=logging.INFO,
                fn="", lno=0, msg=msg, args=(),
                exc_info=None
            )
            record.task_id = task_id

            root_logger.handle(record)
        else:
            root_logger.info(raw)

def start_zmq_listener():
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    loop.run_until_complete(zmq_log_listener())

def setup_mcp_logging(level="INFO", addr="tcp://127.0.0.1:6000", tool_name="unknown_tool"):
    root = logging.getLogger()
    root.setLevel(level)

    # Remove root handlers
    for h in root.handlers[:]:
        root.removeHandler(h)
        h.close()

    # Remove all handlers from fastmcp child loggers
    for name, logger in logging.Logger.manager.loggerDict.items():
        if isinstance(logger, logging.Logger):
            for h in logger.handlers[:]:
                logger.removeHandler(h)
                h.close()
            logger.propagate = True  # 确保冒泡到 root

    # Re-add the ZMQ handler
    handler = ZMQLogHandler(addr=addr, tool_name=tool_name)
    handler.setFormatter(logging.Formatter("[TOOL] %(asctime)s %(levelname)s: %(message)s"))
    root.addHandler(handler)

def setup_log_record_factory():
    old_factory = logging.getLogRecordFactory()
    def record_factory(*args, **kwargs):
        record = old_factory(*args, **kwargs)
        record.task_id = TASK_CONTEXT_VAR.get()
        return record
    logging.setLogRecordFactory(record_factory)

class TaskFilter(logging.Filter):
    def __init__(self, task_id: str):
        super().__init__()
        self.task_id = task_id
    
    def filter(self, record: logging.LogRecord) -> bool:
        return getattr(record, "task_id", None) == self.task_id

def make_task_logger(task_id: str, log_dir: Path) -> logging.Handler:
    log_dir.mkdir(parents=True, exist_ok=True)
    file_path = log_dir / f"task_{task_id}.log"
    fh = logging.FileHandler(file_path, encoding="utf-8")
    fmt = logging.Formatter("%(asctime)s [%(levelname)s] %(name)s: %(message)s")
    fh.setFormatter(fmt)
    fh.addFilter(TaskFilter(task_id))
    logging.getLogger().addHandler(fh)
    return fh

def remove_all_console_handlers():
    """
    移除当前进程中所有 logger 上的 console handler (StreamHandler/RichHandler)。
    """
    for name, logger in logging.Logger.manager.loggerDict.items():
        if isinstance(logger, logging.Logger):
            handlers_to_remove = []
            for h in logger.handlers:
                if isinstance(h, logging.StreamHandler) or isinstance(h, RichHandler):
                    handlers_to_remove.append(h)
            for h in handlers_to_remove:
                logger.removeHandler(h)
                h.close()

    root_logger = logging.getLogger()
    handlers_to_remove = []
    for h in root_logger.handlers:
        if isinstance(h, logging.StreamHandler):
            handlers_to_remove.append(h)
    for h in handlers_to_remove:
        root_logger.removeHandler(h)
        h.close()

@contextmanager
def task_logging_context(task_id: str, log_dir: Path):
    token = TASK_CONTEXT_VAR.set(task_id)
    handler = make_task_logger(task_id, log_dir / "task_logs")
    try:
        yield
    finally:
        TASK_CONTEXT_VAR.reset(token)
        logging.getLogger().removeHandler(handler)
        handler.close()

def init_logging_for_benchmark_evaluation(print_task_logs=False):
    threading.Thread(target=start_zmq_listener, daemon=True).start() #monitoring tool logs
    logging.basicConfig(handlers=[]) 
    setup_log_record_factory()
    if not print_task_logs:
        remove_all_console_handlers()  

@lru_cache
def bootstrap_logger(
    level: Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"] | int = "INFO",
    logger_name: str = "miroflow",
    logger: logging.Logger | None = None,
    log_dir: str | Path | None = None,   # 日志存储目录
    log_filename: str = "miroflow.log",  # 默认日志文件名
    to_console: bool = True,             # 是否显示到 console
) -> logging.Logger:
    """Configure only this logger, not the root logger"""
    if logger is None:
        logger = logging.getLogger(logger_name)

    for handler in logger.handlers[:]:
        logger.removeHandler(handler)

    if to_console:
        handler = RichHandler(
            console=Console(
                stderr=True,
                width=200,
                color_system=None,   
                force_terminal=False,
                legacy_windows=False,
            ),
            rich_tracebacks=True,
            tracebacks_suppress=[hydra],
            tracebacks_show_locals=True,
            show_level=False,
        )
        formatter = logging.Formatter("[%(levelname)s] %(message)s")
        handler.setFormatter(formatter)
        logger.addHandler(handler)

    if log_dir is not None:
        log_dir = Path(log_dir)
        log_dir.mkdir(parents=True, exist_ok=True)
        file_path = log_dir / log_filename
        file_handler = logging.FileHandler(file_path, encoding="utf-8")
        file_handler.setFormatter(logging.Formatter(
            "%(asctime)s [%(levelname)s] %(name)s: %(message)s"
        ))
        logger.addHandler(file_handler)

    logger.setLevel(level)
    logger.propagate = True

    return logger
