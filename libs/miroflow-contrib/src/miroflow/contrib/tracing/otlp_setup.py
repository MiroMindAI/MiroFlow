# SPDX-FileCopyrightText: 2025 MiromindAI
#
# SPDX-License-Identifier: Apache-2.0

"""
author: lei.lei@shanda.com
time: 2025/06/30 16:50
description: bootstrap for open telemetry trace provider.
"""

from .otlp_exporter import FanoutExporter, NoopExporter, OtelExporter
from .processors import BatchTraceProcessor, ConsoleSpanExporter
from .provider import DefaultTraceProvider, TraceProvider
from .setup import set_trace_provider

# _old_provider = get_trace_provider()


def bootstrap_silent_trace_provider() -> TraceProvider:
    noop_exporter = NoopExporter()
    batch_processor = BatchTraceProcessor(exporter=noop_exporter)
    provider = DefaultTraceProvider()
    provider.set_processors([batch_processor])
    set_trace_provider(provider)
    return provider


def bootstrap_otlp_trace_provider() -> TraceProvider:
    console_exporter = ConsoleSpanExporter()
    otel_exporter = OtelExporter(endpoint="http://localhost:4318/v1/traces")
    fanout_exporter = FanoutExporter(exporters=[console_exporter, otel_exporter])
    batch_processor = BatchTraceProcessor(exporter=fanout_exporter)
    provider = DefaultTraceProvider()
    provider.set_processors([batch_processor])
    # _old_provider = get_trace_provider()
    set_trace_provider(provider)
    return provider


# def shutdown_otlp_trace_provider():
#     """
#     Shutdown the OTLP trace provider and restore the old provider.
#     """
#     provider = get_trace_provider()
#     if isinstance(provider, DefaultTraceProvider):
#         provider.shutdown()
#     set_trace_provider(_old_provider)
#     return _old_provider
