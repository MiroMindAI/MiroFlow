# SPDX-FileCopyrightText: 2025 MiromindAI
# SPDX-FileCopyrightText: 2025 Dima Tisnek <dimaqq@gmail.com>
#
# SPDX-License-Identifier: Apache-2.0
"""
convert span.export() to OpenTelemetry JSON format.
this largely mirror the implementation in
https://github.com/dimaqq/otlp-json/blob/e7490fe003309a1b3e8d238f6fc77362a57c220a/otlp_json/__init__.py#L1
"""

import json
import logging
from typing import Any, Mapping, Sequence

import dateutil.parser as dt_parser

from .spans import NoOpSpan, Span, SpanError
from .traces import Trace

logger = logging.getLogger("miroflow.contrib.tracing.otlp_json")


def _ensure_homogeneous(
    value: Sequence[int | float | str | bool],
) -> Sequence[int | float | str | bool]:
    # TODO: empty lists are allowed, aren't they?
    if len(types := {type(v) for v in value}) > 1:
        raise ValueError(f"Attribute value arrays must be homogeneous, got {types=}")
    return value


def _anyvalue(v: Any) -> dict[str, Any]:
    """
    implementation from
    https://github.com/dimaqq/otlp-json/blob/e7490fe003309a1b3e8d238f6fc77362a57c220a/otlp_json/__init__.py#L112

    defintion of `AnyValue`:
    ```proto
    // from https://github.com/open-telemetry/opentelemetry-proto/blob/5b0dc1089080af1dcae23278ad7b70b905909182/opentelemetry/proto/common/v1/common.proto#L1
    // AnyValue is used to represent any type of attribute value. AnyValue may contain a
    // primitive value such as a string or integer or it may contain an arbitrary nested
    // object containing arrays, key-value lists and primitives.
    message AnyValue {
      // The value is one of the listed fields. It is valid for all values to be unspecified
      // in which case this AnyValue is considered to be "empty".
      oneof value {
        string string_value = 1;
        bool bool_value = 2;
        int64 int_value = 3;
        double double_value = 4;
        ArrayValue array_value = 5;
        KeyValueList kvlist_value = 6;
        bytes bytes_value = 7;
      }
    }

    // ArrayValue is a list of AnyValue messages. We need ArrayValue as a message
    // since oneof in AnyValue does not allow repeated fields.
    message ArrayValue {
      // Array of values. The array may be empty (contain 0 elements).
      repeated AnyValue values = 1;
    }

    // KeyValueList is a list of KeyValue messages. We need KeyValueList as a message
    // since `oneof` in AnyValue does not allow repeated fields. Everywhere else where we need
    // a list of KeyValue messages (e.g. in Span) we use `repeated KeyValue` directly to
    // avoid unnecessary extra wrapping (which slows down the protocol). The 2 approaches
    // are semantically equivalent.
    message KeyValueList {
      // A collection of key/value pairs of key-value pairs. The list may be empty (may
      // contain 0 elements).
      // The keys MUST be unique (it is not allowed to have more than one
      // value with the same key).
      repeated KeyValue values = 1;
    }
    ```
    """
    if isinstance(v, bool):
        return {"boolValue": bool(v)}
    if isinstance(v, int):
        return {"intValue": str(int(v))}
    if isinstance(v, float):
        return {"doubleValue": float(v)}
    if isinstance(v, bytes):
        # FIXME: not reached!
        # The API/SDK coerces bytes to str or drops the attribute, see comment in:
        # https://github.com/open-telemetry/opentelemetry-python/issues/4118
        return {"bytesValue": bytes(v).hex()}
    if isinstance(v, str):
        return {"stringValue": str(v)}
    if isinstance(v, Sequence):
        return {
            "arrayValue": {"values": [_anyvalue(e) for e in _ensure_homogeneous(v)]}
        }
    if isinstance(v, Mapping):
        return {"kvlistValue": {"values": [{k: _anyvalue(vv) for k, vv in v.items()}]}}

    raise ValueError(f"Cannot convert attribute value of {type(v)=}")


def _keyvalue(kv: dict[str, Any]) -> list[dict[str, Any]]:
    """
    ```proto
    // KeyValue is a key-value pair that is used to store Span attributes, Link
    // attributes, etc.
    message KeyValue {
      string key = 1;
      AnyValue value = 2;
    }

      // Additional attributes that describe the scope. [Optional].
      // Attribute keys MUST be unique (it is not allowed to have more than one
      // attribute with the same key).
      repeated KeyValue attributes = 3;
    ```
    """
    rv = []
    for key, value in kv.items():
        try:
            rv.append(
                {
                    "key": key,
                    "value": _anyvalue(value),
                }
            )
        except ValueError as e:
            logger.warning(
                f"Failed to encode key-value pair {key}: {value} - {e}. Skipping this attribute."
            )
            continue
    return rv


def _unix_nano(timestamp_in_iso: str) -> int:
    """
    Convert an ISO 8601 timestamp to Unix nanoseconds.
    :param timestamp_in_iso: The timestamp in ISO 8601 format.
    :return: The timestamp in Unix nanoseconds.
    """
    dt = dt_parser.parse(timestamp_in_iso)
    ts_in_nano = dt.timestamp() * 1_000_000_000
    return int(ts_in_nano)


def _status(span_error: SpanError | None) -> dict[str, Any]:
    if span_error is None:
        rv = {"code": 0, "message": ""}
        return rv
    rv = {"code": 1, "message": span_error["message"]}
    return rv


def _trace_id(trace_id: str) -> str:
    """
    assume using default trace provider, which generates trace_id in the format:
    input = f"trace_{uuid.uuid4().hex}"
    """
    raw_value = trace_id[len("trace_") :]
    try:
        int_value = int(raw_value, 16)
    except ValueError as e:
        raise ValueError(f"Invalid trace_id format: {trace_id}") from e
    if not 0 <= int_value < 2**128:
        logging.warning(f"The {trace_id=} is out of bounds, take mod to auto fix")
        int_value = int_value % (2**128)
    return hex(int_value)[2:].rjust(32, "0")


def _span_id(span_id: str) -> str:
    """
    assume using default trace provider, which generates span_id in the format:
    input = f"span_{uuid.uuid4().hex[:24]}"
    """
    raw_value = span_id[len("span_") :]
    try:
        int_value = int(raw_value, 16)
    except ValueError as e:
        raise ValueError(f"Invalid span_id format: {span_id}") from e
    if not 0 <= int_value < 2**64:
        logging.warning(f"The {span_id=} is out of bounds, take mod to auto fix")
        int_value = int_value % (2**64)
    return hex(int_value)[2:].rjust(16, "0")


def _span(span_export: dict[str, Any]) -> dict[str, Any]:
    """
    Convert a span export dictionary to the OpenTelemetry format.
    :param span_export: The span export dictionary.
    :return: The span in OpenTelemetry format.
    """
    span_data = span_export.pop("span_data", {})
    span_type = span_data.pop("type", "undefined")
    span_name = span_data.pop("name", "undefined")
    span_data["kind"] = span_type
    # for parent spant id, it is allowed to be empty
    parent_span_id = ""
    if "parent_id" in span_export:
        val = span_export["parent_id"]
        if val is not None and val != "":
            parent_span_id = _span_id(val)
    return {
        "name": span_name if span_name != "undefined" else span_type,
        "kind": 1,  # 1 for internal
        "traceId": _trace_id(span_export["trace_id"]),
        "spanId": _span_id(span_export["id"]),
        "parentSpanId": parent_span_id,
        "flags": 0x100,  # local
        "status": _status(span_export.get("error", {})),
        "startTimeUnixNano": _unix_nano(span_export["started_at"]),
        "endTimeUnixNano": _unix_nano(span_export["ended_at"]),
        "attributes": _keyvalue(span_data),
    }


def encode_spans(spans: list[Trace | Span]) -> bytes:
    scope_spans = []
    for span in spans:
        if isinstance(span, (Trace, NoOpSpan)):
            continue
        span_export = span.export()
        if span_export is not None:
            scope_spans.append(_span(span_export))

    final = {
        "resourceSpans": [
            {
                # TODO: add resource attributes later
                "resource": {
                    "attributes": [
                        {
                            "key": "service.name",
                            "value": {"stringValue": "react-agent-loop"},
                        }
                    ],
                },
                "scopeSpans": [
                    {
                        # TODO: add scope attributes later
                        "scope": {
                            "name": "miroflow.contrib.tracing",
                            "version": "0.1.0",  # TODO: use actual version
                        },
                        "spans": scope_spans,
                    }
                ],
            }
        ]
    }

    return json.dumps(final, separators=(",", ":")).encode("utf-8")
