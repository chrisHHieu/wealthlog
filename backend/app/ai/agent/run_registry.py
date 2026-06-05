"""In-memory registry for active streaming agent runs."""

import asyncio
import uuid
from dataclasses import dataclass, field

RUN_CLEANUP_GRACE_SECONDS = 60


@dataclass
class RunState:
    """Live SSE broadcast state for one chat session."""

    current_iteration_events: list[str] = field(default_factory=list)
    subscribers: list[asyncio.Queue] = field(default_factory=list)
    done: bool = False
    lock: asyncio.Lock = field(default_factory=asyncio.Lock)

    async def emit(self, event: str, name: str) -> None:
        async with self.lock:
            if name == "iteration":
                self.current_iteration_events = [event]
            else:
                self.current_iteration_events.append(event)
            subscribers = list(self.subscribers)
        for queue in subscribers:
            await queue.put(event)

    async def reset_iteration_buffer(self) -> None:
        async with self.lock:
            self.current_iteration_events = []

    async def finish(self) -> None:
        async with self.lock:
            self.done = True
            subscribers = list(self.subscribers)
            self.subscribers.clear()
        for queue in subscribers:
            await queue.put(None)

    async def subscribe(self) -> asyncio.Queue:
        queue: asyncio.Queue = asyncio.Queue()
        async with self.lock:
            for event in self.current_iteration_events:
                queue.put_nowait(event)
            if self.done:
                queue.put_nowait(None)
            else:
                self.subscribers.append(queue)
        return queue

    async def unsubscribe(self, queue: asyncio.Queue) -> None:
        async with self.lock:
            try:
                self.subscribers.remove(queue)
            except ValueError:
                pass


active_runs: dict[uuid.UUID, RunState] = {}
