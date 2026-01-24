from typing import Union
from pathlib import Path
from omegaconf import DictConfig, OmegaConf
from omegaconf.errors import ConfigInheritanceError


def load_omegaconf_with_base(
    path: Union[str, Path],
    *,
    base_key: str = "_base_",
    drop_base_key: bool = True,
) -> DictConfig:
    """
    Load an OmegaConf config file with recursive `_base_` inheritance.

    Rules:
    - If config contains `_base_`, load that base file relative to current file's directory.
    - Recursively resolve bases.
    - Merge order: base first, then child (child overrides base).
    - Detect cycles.

    Args:
        path: Path to the config yaml file.
        base_key: Key used to reference base config file.
        drop_base_key: Whether to remove base_key from final merged config.

    Returns:
        DictConfig: merged config (still an OmegaConf DictConfig).
    """
    path = Path(path).resolve()
    if not path.is_file():
        raise FileNotFoundError(f"Config file not found: {path}")

    visited: list[Path] = []

    def _load_recursive(p: Path) -> DictConfig:
        p = p.resolve()
        if p in visited:
            chain = " -> ".join(str(x) for x in visited + [p])
            raise ConfigInheritanceError(
                f"Cycle detected in {base_key} inheritance: {chain}"
            )

        visited.append(p)
        cfg = OmegaConf.load(p)

        # If base_key is missing, return as-is
        if base_key not in cfg or cfg[base_key] is None:
            visited.pop()
            return cfg

        base_ref = cfg[base_key]
        if not isinstance(base_ref, str) or not base_ref.strip():
            raise ConfigInheritanceError(
                f"Invalid {base_key} value in {p}: expected non-empty string, got {base_ref!r}"
            )

        base_path = (p.parent / base_ref).resolve()
        if not base_path.is_file():
            raise FileNotFoundError(
                f"Base config referenced by {p} not found: {base_path}"
            )

        base_cfg = _load_recursive(base_path)

        # Merge: base first, child second (child overrides)
        merged = OmegaConf.merge(base_cfg, cfg)

        if drop_base_key and base_key in merged:
            # safe delete (OmegaConf supports del)
            del merged[base_key]

        visited.pop()
        return merged

    return _load_recursive(path)
