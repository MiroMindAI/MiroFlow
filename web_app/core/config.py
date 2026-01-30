# SPDX-FileCopyrightText: 2025 MiromindAI
#
# SPDX-License-Identifier: Apache-2.0

"""Application configuration settings."""

import os
from dataclasses import dataclass, field
from pathlib import Path


@dataclass
class AppConfig:
    """Configuration for MiroFlow Web API."""

    # Server settings
    host: str = "0.0.0.0"
    port: int = 8000
    debug: bool = False

    # Paths (relative to project root)
    project_root: Path = field(
        default_factory=lambda: Path(__file__).parent.parent.parent
    )
    sessions_dir: Path = field(
        default_factory=lambda: Path(__file__).parent.parent / "sessions"
    )
    uploads_dir: Path = field(
        default_factory=lambda: Path(__file__).parent.parent / "uploads"
    )
    configs_dir: Path = field(
        default_factory=lambda: Path(__file__).parent.parent.parent / "config"
    )
    logs_dir: Path = field(
        default_factory=lambda: Path(__file__).parent.parent.parent
        / "logs"
        / "web_runs"
    )

    # Default configuration
    default_config: str = "config/agent_gradio_demo.yaml"

    # Task settings
    max_concurrent_tasks: int = 4
    default_poll_interval_ms: int = 2000

    # Upload settings
    max_upload_size_mb: int = 100
    allowed_extensions: set[str] = field(
        default_factory=lambda: {
            ".xlsx",
            ".xls",
            ".csv",
            ".pdf",
            ".doc",
            ".docx",
            ".txt",
            ".json",
            ".png",
            ".jpg",
            ".jpeg",
            ".mp3",
            ".wav",
            ".mp4",
        }
    )

    def __post_init__(self):
        """Load settings from environment variables."""
        self.host = os.getenv("MIROFLOW_HOST", self.host)
        self.port = int(os.getenv("MIROFLOW_PORT", self.port))
        self.debug = os.getenv("MIROFLOW_DEBUG", "").lower() in ("true", "1", "yes")


# Global config instance
config = AppConfig()
