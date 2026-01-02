# SPDX-FileCopyrightText: 2025 MiromindAI
#
# SPDX-License-Identifier: Apache-2.0

import asyncio
import logging
import os
import socket
import threading
from contextlib import contextmanager
from contextvars import ContextVar
from functools import lru_cache
from pathlib import Path
from typing import Literal, Optional

import hydra
import zmq
import zmq.asyncio
from rich.console import Console
from rich.logging import RichHandler


# ============================================================================
# Constants
# ============================================================================

TASK_CONTEXT_VAR: ContextVar[str | None] = ContextVar("CURRENT_TASK_ID", default=None)


# ============================================================================
# Network Utilities
# ============================================================================

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


def _extract_port_from_address(addr: str) -> int:
    """Extract port number from ZMQ address."""
    try:
        return int(addr.split(":")[-1])
    except (ValueError, IndexError):
        return 6000


# ============================================================================
# ZMQ Manager
# ============================================================================

class ZMQManager:
    """Manages ZMQ address and socket operations."""
    
    def __init__(self, default_address: str = "tcp://127.0.0.1:6000"):
        """Initialize ZMQ manager."""
        self._address = default_address
    
    @property
    def address(self) -> str:
        """Get the current ZMQ address."""
        return self._address
    
    @address.setter
    def address(self, value: str) -> None:
        """Set the ZMQ address."""
        self._address = value
    
    def bind_socket(self, sock, bind_addr: str) -> str:
        """Bind ZMQ socket to an available port and return the actual address."""
        port = _extract_port_from_address(bind_addr)
        
        try:
            available_port = find_available_port(port)
            actual_addr = f"tcp://127.0.0.1:{available_port}"
            sock.bind(actual_addr)
            self._address = actual_addr
            return actual_addr
        except RuntimeError:
            # Fallback to random port
            port = sock.bind_to_random_port("tcp://127.0.0.1")
            actual_addr = f"tcp://127.0.0.1:{port}"
            self._address = actual_addr
            return actual_addr


# ============================================================================
# ZMQ Log Handler
# ============================================================================

class ZMQLogHandler(logging.Handler):
    """Custom logging handler that sends logs via ZMQ PUSH socket."""
    
    def __init__(self, zmq_manager: Optional[ZMQManager] = None, addr: Optional[str] = None, tool_name: str = "unknown_tool"):
        """Initialize ZMQ log handler."""
        super().__init__()
        self._zmq_manager = zmq_manager or _global_zmq_manager
        ctx = zmq.Context()
        self.sock = ctx.socket(zmq.PUSH)
        
        # Use the manager's address if no specific address is provided
        if addr is None:
            addr = self._zmq_manager.address
        
        # Try to connect to the address
        try:
            self.sock.connect(addr)
            logging.getLogger(__name__).info(f"ZMQ handler connected to: {addr}")
        except zmq.error.ZMQError as e:
            logging.getLogger(__name__).warning(
                f"Could not connect to ZMQ listener at {addr}: {e}"
            )
            logging.getLogger(__name__).warning("Disabling ZMQ logging for this handler")
            self.sock = None
        
        self.task_id = os.environ.get("TASK_ID", "0")
        self.tool_name = tool_name
    
    def emit(self, record):
        """Emit a log record via ZMQ."""
        if self.sock is None:
            return
        
        try:
            msg = f"{record.getMessage()}"
            self.sock.send_string(f"{self.task_id}||{self.tool_name}||{msg}")
        except Exception:
            self.handleError(record)


# ============================================================================
# ZMQ Listener
# ============================================================================

class ZMQListener:
    """Manages ZMQ log listener."""
    
    def __init__(self, zmq_manager: Optional[ZMQManager] = None):
        """Initialize ZMQ listener."""
        self._zmq_manager = zmq_manager or _global_zmq_manager
        self._running = False
    
    async def listen(self, bind_addr: str = "tcp://127.0.0.1:6000"):
        """Start async ZMQ log listener that receives and processes log messages."""
        ctx = zmq.asyncio.Context()
        sock = ctx.socket(zmq.PULL)
        
        # Bind to available port
        actual_addr = self._zmq_manager.bind_socket(sock, bind_addr)
        logging.getLogger(__name__).info(f"ZMQ listener bound to: {actual_addr}")
        
        root_logger = logging.getLogger()
        self._running = True
        
        while self._running:
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
    
    def start_in_thread(self, bind_addr: str = "tcp://127.0.0.1:6000", daemon: bool = True):
        """Start ZMQ listener in a separate thread."""
        def run_listener():
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            loop.run_until_complete(self.listen(bind_addr))
        
        thread = threading.Thread(target=run_listener, daemon=daemon)
        thread.start()
        return thread
    
    def stop(self):
        """Stop the listener."""
        self._running = False


# ============================================================================
# Task Logging
# ============================================================================

class TaskFilter(logging.Filter):
    """Filter that only allows log records from a specific task."""
    
    def __init__(self, task_id: str):
        """Initialize task filter."""
        super().__init__()
        self.task_id = task_id
    
    def filter(self, record: logging.LogRecord) -> bool:
        """Check if record matches the task ID."""
        return getattr(record, "task_id", None) == self.task_id


class TaskLoggingManager:
    """Manages task-specific logging."""
    
    def __init__(self):
        """Initialize task logging manager."""
        self._task_handlers: dict[str, logging.Handler] = {}
    
    def setup_log_record_factory(self):
        """Setup custom log record factory that includes task context."""
        old_factory = logging.getLogRecordFactory()
        
        def record_factory(*args, **kwargs):
            record = old_factory(*args, **kwargs)
            record.task_id = TASK_CONTEXT_VAR.get()
            return record
        
        logging.setLogRecordFactory(record_factory)
    
    def create_task_logger(self, task_id: str, log_dir: Path) -> logging.Handler:
        """Create a file handler for task-specific logging."""
        log_dir.mkdir(parents=True, exist_ok=True)
        file_path = log_dir / f"task_{task_id}.log"
        file_handler = logging.FileHandler(file_path, encoding="utf-8")
        formatter = logging.Formatter("%(asctime)s [%(levelname)s] %(name)s: %(message)s")
        file_handler.setFormatter(formatter)
        file_handler.addFilter(TaskFilter(task_id))
        logging.getLogger().addHandler(file_handler)
        self._task_handlers[task_id] = file_handler
        return file_handler
    
    @contextmanager
    def task_logging_context(self, task_id: str, log_dir: Path):
        """Context manager for task-specific logging."""
        token = TASK_CONTEXT_VAR.set(task_id)
        handler = self.create_task_logger(task_id, log_dir / "task_logs")
        try:
            yield
        finally:
            TASK_CONTEXT_VAR.reset(token)
            logging.getLogger().removeHandler(handler)
            handler.close()
            if task_id in self._task_handlers:
                del self._task_handlers[task_id]


# ============================================================================
# Logger Manager
# ============================================================================

class LoggerManager:
    """Main manager for all logging functionality."""
    
    _instance: Optional['LoggerManager'] = None
    
    def __new__(cls):
        """Singleton pattern implementation."""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
    
    def __init__(self):
        """Initialize logger manager."""
        if hasattr(self, '_initialized'):
            return
        self._initialized = True
        self._zmq_manager = ZMQManager()
        self._task_manager = TaskLoggingManager()
        self._zmq_listener: Optional[ZMQListener] = None
    
    @property
    def zmq_address(self) -> str:
        """Get ZMQ address."""
        return self._zmq_manager.address
    
    @zmq_address.setter
    def zmq_address(self, value: str) -> None:
        """Set ZMQ address."""
        self._zmq_manager.address = value
    
    def remove_all_console_handlers(self):
        """Remove all console handlers (StreamHandler/RichHandler) from all loggers."""
        for name, logger in logging.Logger.manager.loggerDict.items():
            if isinstance(logger, logging.Logger):
                handlers_to_remove = []
                for h in logger.handlers:
                    if isinstance(h, (logging.StreamHandler, RichHandler)):
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
    
    def initialize_for_benchmark(self, print_task_logs: bool = False):
        """Initialize logging for benchmark evaluation."""
        # Start ZMQ listener for monitoring tool logs
        self._zmq_listener = ZMQListener(self._zmq_manager)
        self._zmq_listener.start_in_thread(daemon=True)
        logging.basicConfig(handlers=[])
        self._task_manager.setup_log_record_factory()
        if not print_task_logs:
            self.remove_all_console_handlers()


# ============================================================================
# Global Instance
# ============================================================================

_global_logger_manager = LoggerManager()
_global_zmq_manager = _global_logger_manager._zmq_manager
_global_task_manager = _global_logger_manager._task_manager


# ============================================================================
# Utility Functions
# ============================================================================

@lru_cache
def setup_logger(
    level: Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"] | int = "INFO",
    to_console: bool = True,
) -> logging.Logger:
    """Configure and return a logger instance."""
    logger = logging.getLogger("miroflow")
    
    # Remove existing handlers
    for handler in logger.handlers[:]:
        logger.removeHandler(handler)
    
    # Add console handler if requested
    if to_console:
        console_handler = RichHandler(
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
        console_handler.setFormatter(formatter)
        logger.addHandler(console_handler)
    
    logger.setLevel(level)
    logger.propagate = True
    
    return logger


def setup_mcp_logger(
    level: Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"] | int = "INFO",
    tool_name: str = "unknown_tool"
):
    """Setup MCP (Model Context Protocol) logging with ZMQ handler."""
    root = logging.getLogger()
    
    # Remove existing handlers
    for handler in root.handlers[:]:
        root.removeHandler(handler)
        handler.close()
    
    # Remove all handlers from fastmcp child loggers
    # Exclude "miroflow" logger to preserve its handlers (e.g., RichHandler from setup_logger)
    logger_dict = logging.Logger.manager.loggerDict
    for name, logger in logger_dict.items():
        if isinstance(logger, logging.Logger) and name != "miroflow":
            for handler in logger.handlers[:]:
                logger.removeHandler(handler)
                handler.close()
            logger.propagate = True
    
    # Add ZMQ handler
    zmq_handler = ZMQLogHandler(tool_name=tool_name)
    zmq_handler.setFormatter(
        logging.Formatter("[TOOL] %(asctime)s %(levelname)s: %(message)s")
    )
    root.addHandler(zmq_handler)
    
    root.setLevel(level)
    root.propagate = True


# ============================================================================
# Backward Compatibility Functions
# ============================================================================


@contextmanager
def task_logging_context(task_id: str, log_dir: Path):
    """Context manager for task-specific logging. (Backward compatibility)"""
    with _global_task_manager.task_logging_context(task_id, log_dir):
        yield


def init_logging_for_benchmark_evaluation(print_task_logs: bool = False):
    """Initialize logging for benchmark evaluation. (Backward compatibility)"""
    _global_logger_manager.initialize_for_benchmark(print_task_logs)
