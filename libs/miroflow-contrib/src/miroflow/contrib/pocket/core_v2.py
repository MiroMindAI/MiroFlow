from typing import Any, Protocol, TypeVar
from dataclasses import dataclass
import copy
from abc import ABC, abstractmethod
import warnings

A, B = TypeVar("A"), TypeVar("B")
Context = Any


class Node[A, B](ABC):
    @abstractmethod
    def prep(self, ctx: Context) -> A: ...

    @abstractmethod
    def exec(self, prep: A) -> B: ...

    @abstractmethod
    def post(self, ctx: Context, prep: A, exec: B) -> str: ...

    def run(self, ctx: Context) -> str:
        p = self.prep(ctx)
        e = self.exec(p)
        return self.post(ctx, p, e)


class Flowable(Protocol):
    @property
    def successors(self) -> dict[str, "Node[Any, Any]"]: ...


class FlowableMixin:
    def handle(self: Flowable, action: str) -> "Node[Any, Any] | None":
        return self.successors.get(action, None)

    def add_successor(
        self: Flowable, action: str, node: "Node[Any, Any]"
    ) -> "Node[Any, Any]":
        if action in self.successors:
            warnings.warn(f"Overwriting successor for action '{action}'")
        self.successors[action] = node
        return node


@dataclass
class Flow:
    start: Node[Any, Any]

    def flow(self, ctx: Context) -> str:
        curr, last_action = (copy.copy(self.start), "default")
        while curr is not None:
            last_action = curr.run(ctx)
            next_node = curr.successors.get(last_action, None)
            curr = copy.copy(next_node)
        return last_action
