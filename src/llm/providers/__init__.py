# SPDX-FileCopyrightText: 2025 MiromindAI
#
# SPDX-License-Identifier: Apache-2.0

import os
import importlib
import pkgutil
import inspect

# Dynamically import all classes from all .py files in this directory (excluding __init__.py)
__all__ = []

package_dir = os.path.dirname(__file__)

for module_info in pkgutil.iter_modules([package_dir]):
    module_name = module_info.name
    if module_name == "__init__":
        continue  # Skip __init__.py
    # Import the module
    module = importlib.import_module(f"{__name__}.{module_name}")
    # Inspect all classes defined in the module
    for name, obj in inspect.getmembers(module, inspect.isclass):
        # Only include classes defined in this module (not imported ones)
        if obj.__module__ == module.__name__:
            globals()[name] = obj
            __all__.append(name)
