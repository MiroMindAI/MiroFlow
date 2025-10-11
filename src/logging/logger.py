# SPDX-FileCopyrightText: 2025 MiromindAI
#
# SPDX-License-Identifier: Apache-2.0

import os
import zmq
import zmq.asyncio
import logging
from functools import lru_cache
from pathlib import Path
from typing import Literal
from contextvars import ContextVar
import hydra
from rich.console import Console
from rich.logging import RichHandler
import asyncio
import threading
from contextlib import contextmanager
import socket

TASK_CONTEXT_VAR: ContextVar[str | None] = ContextVar("CURRENT_TASK_ID", default=None)

# Global variable to store the actual ZMQ address being used
_ZMQ_ADDRESS: str = "tcp://127.0.0.1:6000"


def find_available_port(start_port: int = 6000, max_attempts: int = 10) -> int:
    """Find an available port starting from start_port."""
    for port in range(start_port, start_port + max_attempts):
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.bind(("127.0.0.1", port))
                return port
        except OSError:
            continue
    raise RuntimeError(
        f"Could not find an available port in range {start_port}-{start_port + max_attempts - 1}"
    )


def get_zmq_address() -> str:
    """Get the current ZMQ address."""
    return _ZMQ_ADDRESS


def set_zmq_address(address: str) -> None:
    """Set the ZMQ address."""
    global _ZMQ_ADDRESS
    _ZMQ_ADDRESS = address


def _extract_port_from_address(addr: str) -> int:
    """Extract port number from ZMQ address."""
    try:
        return int(addr.split(":")[-1])
    except (ValueError, IndexError):
        return 6000


def _bind_zmq_socket(sock, bind_addr: str) -> str:
    """Bind ZMQ socket to an available port and return the actual address."""
    port = _extract_port_from_address(bind_addr)

    try:
        available_port = find_available_port(port)
        actual_addr = f"tcp://127.0.0.1:{available_port}"
        sock.bind(actual_addr)
        return actual_addr
    except RuntimeError:
        # Fallback to random port
        port = sock.bind_to_random_port("tcp://127.0.0.1")
        return f"tcp://127.0.0.1:{port}"


class ZMQLogHandler(logging.Handler):
    def __init__(self, addr=None, tool_name="unknown_tool"):
        super().__init__()
        ctx = zmq.Context()
        self.sock = ctx.socket(zmq.PUSH)

        # Use the global ZMQ address if no specific address is provided
        if addr is None:
            addr = get_zmq_address()

        # Try to connect to the address
        try:
            self.sock.connect(addr)
            logging.getLogger(__name__).info(f"ZMQ handler connected to: {addr}")
        except zmq.error.ZMQError as e:
            # If connection fails, disable the handler
            logging.getLogger(__name__).warning(
                f"Could not connect to ZMQ listener at {addr}: {e}"
            )
            logging.getLogger(__name__).warning(
                "Disabling ZMQ logging for this handler"
            )
            self.sock = None

        self.task_id = os.environ.get("TASK_ID", "0")
        self.tool_name = tool_name

    def emit(self, record):
        if self.sock is None:
            return

        try:
            msg = f"{record.getMessage()}"
            self.sock.send_string(f"{self.task_id}||{self.tool_name}||{msg}")
        except Exception:
            self.handleError(record)


async def zmq_log_listener(bind_addr="tcp://127.0.0.1:6000"):
    ctx = zmq.asyncio.Context()
    sock = ctx.socket(zmq.PULL)

    # Bind to available port
    actual_addr = _bind_zmq_socket(sock, bind_addr)
    set_zmq_address(actual_addr)
    logging.getLogger(__name__).info(f"ZMQ listener bound to: {actual_addr}")

    root_logger = logging.getLogger()

    while True:
        raw = await sock.recv_string()
        if "||" in raw:
            task_id, tool_name, msg = raw.split("||", 2)

            record = root_logger.makeRecord(
                name=f"[TOOL] {tool_name}",
                level=logging.INFO,
                fn="",
                lno=0,
                msg=msg,
                args=(),
                exc_info=None,
            )
            record.task_id = task_id

            root_logger.handle(record)
        else:
            root_logger.info(raw)


def start_zmq_listener():
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    loop.run_until_complete(zmq_log_listener())


def setup_mcp_logging(level="INFO", addr=None, tool_name="unknown_tool"):
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
            logger.propagate = True  # Ensure bubbling to root

    # Re-add the ZMQ handler (will use global address if addr is None)
    handler = ZMQLogHandler(addr=addr, tool_name=tool_name)
    handler.setFormatter(
        logging.Formatter("[TOOL] %(asctime)s %(levelname)s: %(message)s")
    )
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
    Remove all console handlers (StreamHandler/RichHandler) from all loggers in the current process.
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
    threading.Thread(
        target=start_zmq_listener, daemon=True
    ).start()  # monitoring tool logs
    logging.basicConfig(handlers=[])
    setup_log_record_factory()
    if not print_task_logs:
        remove_all_console_handlers()


@lru_cache
def bootstrap_logger(
    level: Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"] | int = "INFO",
    logger_name: str = "miroflow",
    logger: logging.Logger | None = None,
    log_dir: str | Path | None = None,  # Log storage directory
    log_filename: str = "miroflow.log",  # Default log filename
    to_console: bool = True,  # Whether to display to console
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
        file_handler.setFormatter(
            logging.Formatter("%(asctime)s [%(levelname)s] %(name)s: %(message)s")
        )
        logger.addHandler(file_handler)

    logger.setLevel(level)
    logger.propagate = True

    return logger
