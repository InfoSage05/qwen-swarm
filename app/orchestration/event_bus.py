import asyncio
from typing import Callable, Dict, List, Any
import logging

logger = logging.getLogger(__name__)

class EventBus:
    """Async event bus for agent communication."""
    
    def __init__(self):
        self.subscribers: Dict[str, List[Callable]] = {}

    def subscribe(self, event_type: str, callback: Callable):
        if event_type not in self.subscribers:
            self.subscribers[event_type] = []
        self.subscribers[event_type].append(callback)

    async def publish(self, event_type: str, data: Any = None):
        logger.info(f"Event Published: {event_type}")
        if event_type in self.subscribers:
            tasks = [callback(data) for callback in self.subscribers[event_type]]
            if tasks:
                await asyncio.gather(*tasks)
