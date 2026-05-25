from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass


@dataclass(frozen=True)
class HealthCheckResult:
    ok: bool
    reason: str


class BaseLLMProvider(ABC):
    @abstractmethod
    async def analyze(self, system_prompt: str, user_prompt: str) -> str:
        raise NotImplementedError

    @abstractmethod
    async def repair_json(self, invalid_text: str, error: str) -> str:
        raise NotImplementedError

    @abstractmethod
    async def health_check(self) -> HealthCheckResult:
        raise NotImplementedError
