"""Per-job in-process pub/sub for SSE. Each subscriber gets its own queue."""
from __future__ import annotations

import asyncio
from collections import defaultdict


class EventBus:
    def __init__(self) -> None:
        self._subs: dict[str, set[asyncio.Queue]] = defaultdict(set)

    async def publish(self, job_id: str, event_type: str, data: dict) -> None:
        payload = {"type": event_type, "data": data}
        for q in list(self._subs.get(job_id, ())):
            await q.put(payload)

    def emitter(self, job_id: str):
        async def emit(event_type: str, data: dict) -> None:
            await self.publish(job_id, event_type, data)
        return emit

    async def subscribe(self, job_id: str):
        q: asyncio.Queue = asyncio.Queue()
        self._subs[job_id].add(q)
        try:
            while True:
                yield await q.get()
        finally:
            self._subs[job_id].discard(q)


bus = EventBus()
