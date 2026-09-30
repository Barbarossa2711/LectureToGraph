"""In-process publish/subscribe per job for server-sent events. Each subscriber gets its own queue."""
from __future__ import annotations

import asyncio
from collections import defaultdict


class EventBus:
    """Distributes job events to all subscribers of that job."""

    def __init__(self) -> None:
        """Create an event bus without subscribers."""
        self._subs: dict[str, set[asyncio.Queue]] = defaultdict(set)

    async def publish(self, job_id: str, event_type: str, data: dict) -> None:
        """
        Send an event to every current subscriber of a job.

        :param job_id: The job the event belongs to.
        :param event_type: The event type, e.g. "log" or "gate".
        :param data: The event payload.
        :return: None
        """
        payload = {"type": event_type, "data": data}
        for q in list(self._subs.get(job_id, ())):
            await q.put(payload)

    def emitter(self, job_id: str):
        """
        Bind publish to one job.

        :param job_id: The job the events belong to.
        :return: An async function emit(event_type, data).
        """
        async def emit(event_type: str, data: dict) -> None:
            """
            Publish an event for the bound job.

            :param event_type: The event type.
            :param data: The event payload.
            :return: None
            """
            await self.publish(job_id, event_type, data)
        return emit

    async def subscribe(self, job_id: str):
        """
        Receive the events of a job until the consumer stops iterating.

        :param job_id: The job to subscribe to.
        :return: An async generator of {"type": ..., "data": ...} events.
        """
        q: asyncio.Queue = asyncio.Queue()
        self._subs[job_id].add(q)
        try:
            while True:
                yield await q.get()
        finally:
            self._subs[job_id].discard(q)


bus = EventBus()
