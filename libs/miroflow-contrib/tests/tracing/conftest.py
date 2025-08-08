# SPDX-FileCopyrightText: 2025 MiromindAI
# SPDX-FileCopyrightText: 2025 OpenAI
#
# SPDX-License-Identifier: Apache-2.0
# SPDX-License-Identifier: MIT

from __future__ import annotations

import pytest
from testing_processor import SPAN_PROCESSOR_TESTING

from miroflow.contrib.tracing import set_trace_processors
from miroflow.contrib.tracing.setup import get_trace_provider


# This fixture will run once before any tests are executed
@pytest.fixture(scope="session", autouse=True)
def setup_span_processor():
    # set_trace_provider(DefaultTraceProvider())
    set_trace_processors([SPAN_PROCESSOR_TESTING])


# This fixture will run before each test
@pytest.fixture(autouse=True)
def clear_span_processor():
    SPAN_PROCESSOR_TESTING.force_flush()
    SPAN_PROCESSOR_TESTING.shutdown()
    SPAN_PROCESSOR_TESTING.clear()


# This fixture will run after all tests end
@pytest.fixture(autouse=True, scope="session")
def shutdown_trace_provider():
    yield
    get_trace_provider().shutdown()
