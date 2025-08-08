import asyncio
import copy
import time
import warnings
from typing import Any, TypeVar
from dataclasses import dataclass

# Type variables for better type relationships
_PrepResult = TypeVar("_PrepResult")
_ExecResult = TypeVar("_ExecResult")

# More specific parameter types
ParamValue = str | int | float | bool | None | list[Any] | dict[str, Any]
SharedData = dict[str, Any]
Params = dict[str, ParamValue]


class BaseNode[_PrepResult, _ExecResult]:
    params: Params
    successors: dict[str, "BaseNode[Any, Any]"]
    cur_retry: int

    def __init__(self) -> None:
        self.params, self.successors = {}, {}

    def set_params(self, params: Params) -> None:
        self.params = params

    def add_downstream(
        self, node: "BaseNode[Any, Any]", action: str = "default"
    ) -> "BaseNode[Any, Any]":
        if action in self.successors:
            warnings.warn(f"Overwriting successor for action '{action}'")
        self.successors[action] = node
        return node

    def prep(self, shared: SharedData) -> _PrepResult:
        return None  # type: ignore

    def exec(self, prep_res: _PrepResult) -> _ExecResult:
        return None  # type: ignore

    def post(
        self, shared: SharedData, prep_res: _PrepResult, exec_res: _ExecResult
    ) -> str:
        return None  # type: ignore

    def _exec(self, prep_res: _PrepResult) -> _ExecResult:
        return self.exec(prep_res)

    def _run(self, shared: SharedData) -> str:
        p = self.prep(shared)
        e = self._exec(p)
        return self.post(shared, p, e)

    def run(self, shared: SharedData) -> str:
        if self.successors:
            warnings.warn("Node won't run successors. Use Flow.")
        return self._run(shared)

    def __rshift__(self, other: "BaseNode[Any, Any]") -> "BaseNode[Any, Any]":
        return self.add_downstream(other)

    def __sub__(self, action: str) -> "_ConditionalTransition":
        if isinstance(action, str):
            return _ConditionalTransition(self, action)
        raise TypeError("Action must be a string")


@dataclass
class _ConditionalTransition:
    src: BaseNode[Any, Any]
    action: str

    def __rshift__(self, tgt: BaseNode[Any, Any]) -> BaseNode[Any, Any]:
        return self.src.add_downstream(tgt, self.action)


class Node[_PrepResult, _ExecResult](BaseNode[_PrepResult, _ExecResult]):
    max_retries: int
    wait: int | float

    def __init__(self, max_retries: int = 1, wait: int | float = 0) -> None:
        super().__init__()
        self.max_retries, self.wait = max_retries, wait

    def exec_fallback(self, prep_res: _PrepResult, exc: Exception) -> _ExecResult:
        raise exc

    def _exec(self, prep_res: _PrepResult) -> _ExecResult:
        for self.cur_retry in range(self.max_retries):
            try:
                return self.exec(prep_res)
            except Exception as e:
                if self.cur_retry == self.max_retries - 1:
                    return self.exec_fallback(prep_res, e)
                if self.wait > 0:
                    time.sleep(self.wait)
        raise RuntimeError("Should not reach here")


class BatchNode[_PrepResult, _ExecResult](Node[list[_PrepResult], list[_ExecResult]]):
    def _exec(self, prep_res: list[_PrepResult]) -> list[_ExecResult]:
        return [super(BatchNode, self)._exec(i) for i in prep_res]


@dataclass
class Flow[_PrepResult, Any](BaseNode[_PrepResult, Any]):
    start_node: BaseNode[Any, Any]

    def start(self, start: BaseNode[Any, Any]) -> BaseNode[Any, Any]:
        self.start_node = start
        return start

    def get_next_node(
        self, curr: BaseNode[Any, Any], action: str | None
    ) -> BaseNode[Any, Any] | None:
        nxt = curr.successors.get(action or "default")
        if not nxt and curr.successors:
            warnings.warn(f"Flow ends: '{action}' not found in {list(curr.successors)}")
        return nxt

    def _orch(self, shared: SharedData, params: Params | None = None) -> Any:
        curr, p, last_action = (
            copy.copy(self.start_node),
            (params or {**self.params}),
            None,
        )
        while curr:
            curr.set_params(p)
            last_action = curr._run(shared)
            curr = copy.copy(self.get_next_node(curr, last_action))
        return last_action

    def _run(self, shared: SharedData) -> str:
        p = self.prep(shared)
        o = self._orch(shared)
        return self.post(shared, p, o)

    def post(self, shared: SharedData, prep_res: _PrepResult, exec_res: Any) -> str:
        return exec_res


class BatchFlow(Flow[list[Params], Any]):
    def _run(self, shared: SharedData) -> str:
        pr = self.prep(shared)
        for bp in pr:
            self._orch(shared, {**self.params, **bp})
        return self.post(shared, pr, None)


class AsyncNode[_PrepResult, _ExecResult](Node[_PrepResult, _ExecResult]):
    async def prep_async(self, shared: SharedData) -> _PrepResult:
        return None  # type: ignore

    async def exec_async(self, prep_res: _PrepResult) -> _ExecResult:
        return None  # type: ignore

    async def exec_fallback_async(
        self, prep_res: _PrepResult, exc: Exception
    ) -> _ExecResult:
        raise exc

    async def post_async(
        self, shared: SharedData, prep_res: _PrepResult, exec_res: _ExecResult
    ) -> str:
        return None  # type: ignore

    async def _exec(self, prep_res: _PrepResult) -> _ExecResult:
        for self.cur_retry in range(self.max_retries):
            try:
                return await self.exec_async(prep_res)
            except Exception as e:
                if self.cur_retry == self.max_retries - 1:
                    return await self.exec_fallback_async(prep_res, e)
                if self.wait > 0:
                    await asyncio.sleep(self.wait)
        raise RuntimeError("Should not reach here")

    async def run_async(self, shared: SharedData) -> str:
        if self.successors:
            warnings.warn("Node won't run successors. Use AsyncFlow.")
        return await self._run_async(shared)

    async def _run_async(self, shared: SharedData) -> str:
        p = await self.prep_async(shared)
        e = await self._exec(p)
        return await self.post_async(shared, p, e)

    def _run(self, shared: SharedData) -> str:
        raise RuntimeError("Use run_async.")


class AsyncBatchNode(AsyncNode[list[_PrepResult] | None, list[_ExecResult], str]):
    async def _exec(self, prep_res: list[_PrepResult] | None) -> list[_ExecResult]:
        if prep_res is None:
            return []
        return [await super(AsyncBatchNode, self)._exec(i) for i in prep_res]


class AsyncParallelBatchNode(
    AsyncNode[list[_PrepResult] | None, list[_ExecResult], str]
):
    async def _exec(self, prep_res: list[_PrepResult] | None) -> list[_ExecResult]:
        if prep_res is None:
            return []
        return await asyncio.gather(
            *(super(AsyncParallelBatchNode, self)._exec(i) for i in prep_res)
        )


class AsyncFlow(Flow[_PrepResult, Any], AsyncNode[_PrepResult, Any]):
    async def _orch_async(
        self, shared: SharedData, params: Params | None = None
    ) -> Any:
        curr, p, last_action = (
            copy.copy(self.start_node),
            (params or {**self.params}),
            None,
        )
        while curr:
            curr.set_params(p)
            last_action = (
                await curr._run_async(shared)
                if isinstance(curr, AsyncNode)
                else curr._run(shared)
            )
            curr = copy.copy(self.get_next_node(curr, last_action))
        return last_action

    async def _run_async(self, shared: SharedData) -> str:
        p = await self.prep_async(shared)
        o = await self._orch_async(shared)
        return await self.post_async(shared, p, o)

    async def post_async(
        self, shared: SharedData, prep_res: _PrepResult, exec_res: Any
    ) -> str:
        return exec_res


class AsyncBatchFlow(
    AsyncFlow[list[Params] | None, Any, str],
    BatchFlow[list[Params] | None, Any, str],
):
    async def _run_async(self, shared: SharedData) -> str:
        pr = await self.prep_async(shared) or []
        for bp in pr:
            await self._orch_async(shared, {**self.params, **bp})
        return await self.post_async(shared, pr, None)


class AsyncParallelBatchFlow(
    AsyncFlow[list[Params] | None, Any, str],
    BatchFlow[list[Params] | None, Any, str],
):
    async def _run_async(self, shared: SharedData) -> str:
        pr = await self.prep_async(shared) or []
        await asyncio.gather(
            *(self._orch_async(shared, {**self.params, **bp}) for bp in pr)
        )
        return await self.post_async(shared, pr, None)
