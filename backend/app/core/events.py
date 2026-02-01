"""Event system for inter-service communication"""

import asyncio
import logging
from datetime import datetime
from typing import Dict, List, Callable, Any, Optional
from enum import Enum
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)


class EventType(str, Enum):
    """Available event types"""
    # Router events
    ROUTER_ADDED = "router_added"
    ROUTER_REMOVED = "router_removed"
    ROUTER_UPDATED = "router_updated"
    ROUTER_ONLINE = "router_online"
    ROUTER_OFFLINE = "router_offline"

    # Scan events
    SCAN_STARTED = "scan_started"
    SCAN_COMPLETED = "scan_completed"
    SCAN_FAILED = "scan_failed"

    # Update events
    UPDATE_STARTED = "update_started"
    UPDATE_PROGRESS = "update_progress"
    UPDATE_COMPLETED = "update_completed"
    UPDATE_FAILED = "update_failed"

    # Backup events
    BACKUP_CREATED = "backup_created"
    BACKUP_FAILED = "backup_failed"
    RESTORE_STARTED = "restore_started"
    RESTORE_COMPLETED = "restore_completed"
    RESTORE_FAILED = "restore_failed"

    # Script events
    SCRIPT_EXECUTED = "script_executed"
    SCRIPT_FAILED = "script_failed"

    # Schedule events
    SCHEDULE_STARTED = "schedule_started"
    SCHEDULE_COMPLETED = "schedule_completed"
    SCHEDULE_FAILED = "schedule_failed"

    # Alert events
    ALERT_CREATED = "alert_created"
    ALERT_RESOLVED = "alert_resolved"

    # Health events
    HEALTH_WARNING = "health_warning"
    HEALTH_CRITICAL = "health_critical"
    HEALTH_OK = "health_ok"


@dataclass
class Event:
    """Event data structure"""
    type: EventType
    data: Dict[str, Any]
    timestamp: datetime = field(default_factory=datetime.utcnow)
    source: Optional[str] = None
    router_id: Optional[int] = None
    user_id: Optional[int] = None


class EventBus:
    """Simple event bus for publishing and subscribing to events"""

    _instance: Optional["EventBus"] = None
    _handlers: Dict[EventType, List[Callable]]
    _async_handlers: Dict[EventType, List[Callable]]

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._handlers = {}
            cls._instance._async_handlers = {}
        return cls._instance

    def subscribe(self, event_type: EventType, handler: Callable):
        """Subscribe a synchronous handler to an event type"""
        if event_type not in self._handlers:
            self._handlers[event_type] = []
        self._handlers[event_type].append(handler)
        logger.debug(f"Handler subscribed to {event_type.value}")

    def subscribe_async(self, event_type: EventType, handler: Callable):
        """Subscribe an async handler to an event type"""
        if event_type not in self._async_handlers:
            self._async_handlers[event_type] = []
        self._async_handlers[event_type].append(handler)
        logger.debug(f"Async handler subscribed to {event_type.value}")

    def unsubscribe(self, event_type: EventType, handler: Callable):
        """Unsubscribe a handler from an event type"""
        if event_type in self._handlers and handler in self._handlers[event_type]:
            self._handlers[event_type].remove(handler)
        if event_type in self._async_handlers and handler in self._async_handlers[event_type]:
            self._async_handlers[event_type].remove(handler)

    def publish(self, event: Event):
        """Publish an event to all subscribers (sync)"""
        event_type = event.type
        logger.debug(f"Publishing event: {event_type.value}")

        # Call sync handlers
        if event_type in self._handlers:
            for handler in self._handlers[event_type]:
                try:
                    handler(event)
                except Exception as e:
                    logger.error(f"Error in event handler: {e}")

    async def publish_async(self, event: Event):
        """Publish an event to all subscribers (async)"""
        event_type = event.type
        logger.debug(f"Publishing async event: {event_type.value}")

        # Call sync handlers in thread pool
        if event_type in self._handlers:
            for handler in self._handlers[event_type]:
                try:
                    await asyncio.get_event_loop().run_in_executor(None, handler, event)
                except Exception as e:
                    logger.error(f"Error in sync event handler: {e}")

        # Call async handlers
        if event_type in self._async_handlers:
            tasks = []
            for handler in self._async_handlers[event_type]:
                tasks.append(handler(event))
            if tasks:
                await asyncio.gather(*tasks, return_exceptions=True)

    def emit(
        self,
        event_type: EventType,
        data: Dict[str, Any],
        router_id: Optional[int] = None,
        user_id: Optional[int] = None,
        source: Optional[str] = None
    ):
        """Convenience method to create and publish an event"""
        event = Event(
            type=event_type,
            data=data,
            router_id=router_id,
            user_id=user_id,
            source=source
        )
        self.publish(event)
        return event

    async def emit_async(
        self,
        event_type: EventType,
        data: Dict[str, Any],
        router_id: Optional[int] = None,
        user_id: Optional[int] = None,
        source: Optional[str] = None
    ):
        """Convenience method to create and publish an async event"""
        event = Event(
            type=event_type,
            data=data,
            router_id=router_id,
            user_id=user_id,
            source=source
        )
        await self.publish_async(event)
        return event


# Global event bus instance
event_bus = EventBus()


def get_event_bus() -> EventBus:
    """Get the event bus instance"""
    return event_bus
