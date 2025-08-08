# SPDX-FileCopyrightText: 2025 MiromindAI
#
# SPDX-License-Identifier: Apache-2.0

# -*- coding: utf-8 -*-
"""
author: lei.lei@shanda.com
time: 2025/07/07 14:39
description: common middleware for LLM client
"""

from miroflow.contrib.tracing.scope import Scope


def get_trace_id() -> str | None:
    trace = Scope.get_current_trace()
    if trace is None:
        return None
    return trace.trace_id
