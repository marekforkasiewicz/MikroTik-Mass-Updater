"""WebSocket endpoints for real-time updates"""

import asyncio
import json
from typing import Dict, Set
from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Depends
from sqlalchemy.orm import Session

from ..database import get_db, SessionLocal
from ..models.task import Task
from ..core.enums import TaskStatus

router = APIRouter(tags=["websocket"])


class ConnectionManager:
    """Manages WebSocket connections"""

    def __init__(self):
        # task_id -> set of websockets
        self.active_connections: Dict[str, Set[WebSocket]] = {}

    async def connect(self, websocket: WebSocket, task_id: str):
        """Accept a new connection"""
        await websocket.accept()
        if task_id not in self.active_connections:
            self.active_connections[task_id] = set()
        self.active_connections[task_id].add(websocket)

    def disconnect(self, websocket: WebSocket, task_id: str):
        """Remove a connection"""
        if task_id in self.active_connections:
            self.active_connections[task_id].discard(websocket)
            if not self.active_connections[task_id]:
                del self.active_connections[task_id]

    async def send_progress(self, task_id: str, data: dict):
        """Send progress update to all connected clients"""
        if task_id in self.active_connections:
            disconnected = set()
            for websocket in self.active_connections[task_id]:
                try:
                    await websocket.send_json(data)
                except Exception:
                    disconnected.add(websocket)

            # Clean up disconnected clients
            for ws in disconnected:
                self.active_connections[task_id].discard(ws)


manager = ConnectionManager()


@router.websocket("/ws/tasks/{task_id}")
async def task_progress_websocket(websocket: WebSocket, task_id: str):
    """
    WebSocket endpoint for real-time task progress updates.

    Connects to a specific task and receives progress updates:
    {
        "task_id": "...",
        "status": "running",
        "progress": 5,
        "total": 10,
        "current_item": "192.168.1.1",
        "message": "Processing router..."
    }
    """
    await manager.connect(websocket, task_id)

    try:
        db = SessionLocal()
        last_progress = -1
        last_status = None

        while True:
            # Check task status
            task = db.query(Task).filter(Task.id == task_id).first()

            if not task:
                await websocket.send_json({
                    "task_id": task_id,
                    "error": "Task not found"
                })
                break

            # Send update if something changed
            if task.progress != last_progress or task.status != last_status:
                last_progress = task.progress
                last_status = task.status

                await websocket.send_json({
                    "task_id": task_id,
                    "status": task.status,
                    "progress": task.progress,
                    "total": task.total,
                    "current_item": task.current_item,
                    "progress_percent": task.progress_percent
                })

            # If task is complete, send final result and close
            if task.status in [
                TaskStatus.COMPLETED.value,
                TaskStatus.FAILED.value,
                TaskStatus.CANCELLED.value
            ]:
                await websocket.send_json({
                    "task_id": task_id,
                    "status": task.status,
                    "progress": task.progress,
                    "total": task.total,
                    "results": task.results,
                    "error": task.error,
                    "complete": True
                })
                break

            # Refresh session to get latest data
            db.expire_all()

            # Wait before next poll
            await asyncio.sleep(0.5)

    except WebSocketDisconnect:
        pass
    except Exception as e:
        try:
            await websocket.send_json({"error": str(e)})
        except Exception:
            pass
    finally:
        manager.disconnect(websocket, task_id)
        try:
            db.close()
        except Exception:
            pass


@router.websocket("/ws/status")
async def global_status_websocket(websocket: WebSocket):
    """
    WebSocket endpoint for global status updates.

    Sends periodic updates about overall system status:
    - Total routers
    - Online/offline count
    - Running tasks
    """
    await websocket.accept()

    try:
        db = SessionLocal()

        while True:
            from ..models.router import Router

            # Get router stats
            total_routers = db.query(Router).count()
            online_routers = db.query(Router).filter(Router.is_online == True).count()
            needs_update = db.query(Router).filter(Router.has_updates == True).count()

            # Get running tasks
            running_tasks = db.query(Task).filter(
                Task.status == TaskStatus.RUNNING.value
            ).count()

            await websocket.send_json({
                "type": "status",
                "routers": {
                    "total": total_routers,
                    "online": online_routers,
                    "offline": total_routers - online_routers,
                    "needs_update": needs_update
                },
                "tasks": {
                    "running": running_tasks
                }
            })

            db.expire_all()
            await asyncio.sleep(5)

    except WebSocketDisconnect:
        pass
    except Exception:
        pass
    finally:
        try:
            db.close()
        except Exception:
            pass
