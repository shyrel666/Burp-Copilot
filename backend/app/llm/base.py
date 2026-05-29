from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import AsyncIterator
from dataclasses import dataclass


@dataclass(frozen=True)
class HealthCheckResult:
    ok: bool
    reason: str


class BaseLLMProvider(ABC):
    @abstractmethod
    async def analyze(self, system_prompt: str, user_prompt: str) -> str:
        raise NotImplementedError

    async def analyze_stream(self, system_prompt: str, user_prompt: str) -> AsyncIterator[str]:
        result = await self.analyze(system_prompt, user_prompt)
        yield result

    @abstractmethod
    async def repair_json(self, invalid_text: str, error: str) -> str:
        raise NotImplementedError

    @abstractmethod
    async def health_check(self) -> HealthCheckResult:
        raise NotImplementedError

    async def aclose(self) -> None:
        """Release resources held by the provider. Override in subclasses."""
        pass
