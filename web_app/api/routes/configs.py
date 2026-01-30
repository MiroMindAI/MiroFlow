# SPDX-FileCopyrightText: 2025 MiromindAI
#
# SPDX-License-Identifier: Apache-2.0

"""Configuration listing endpoint."""

from fastapi import APIRouter, Depends

from ...core.config import AppConfig
from ...models.task import ConfigListResponse
from ..dependencies import get_config

router = APIRouter(prefix="/api/configs", tags=["configs"])


@router.get("", response_model=ConfigListResponse)
async def list_configs(
    config: AppConfig = Depends(get_config),
) -> ConfigListResponse:
    """List available agent configuration files."""
    configs = []
    config_dir = config.configs_dir

    for f in config_dir.glob("agent*.yaml"):
        configs.append(str(f.relative_to(config.project_root)))

    # Sort but put default first
    configs = sorted(configs)
    default = config.default_config
    if default in configs:
        configs.remove(default)
        configs.insert(0, default)

    return ConfigListResponse(configs=configs, default=default)
