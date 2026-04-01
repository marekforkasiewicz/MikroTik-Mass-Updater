"""WebSocket endpoints for real-time updates"""

import asyncio
from typing import Dict, Optional, Set
from fastapi import APIRouter, WebSocket, WebSocketDisconnect, status

from ..database import SessionLocal
from ..models.task import Task
from ..models.user import APIKey, User
from ..core.security import decode_token, verify_api_key
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


async def _authenticate_websocket(websocket: WebSocket) -> Optional[User]:
    """Authenticate websocket clients via access-token cookie, bearer token, or API key."""
    token = websocket.cookies.get("access_token")

    if not token:
        authorization = websocket.headers.get("authorization", "")
        if authorization.startswith("Bearer "):
            token = authorization[7:]

    if not token:
        token = websocket.query_params.get("token")

    api_key = websocket.headers.get("x-api-key") or websocket.query_params.get("api_key")

    db = SessionLocal()
    try:
        if token:
            payload = decode_token(token)
            if payload and payload.get("type") == "access":
                user_id = payload.get("sub")
                if user_id:
                    user = db.query(User).filter(User.id == int(user_id)).first()
                    if user and user.is_active:
                        return user

        if api_key:
            prefix = api_key[:8] if len(api_key) >= 8 else api_key
            api_key_records = db.query(APIKey).filter(
                APIKey.key_prefix == prefix,
                APIKey.is_active == True
            ).all()

            for key_record in api_key_records:
                if verify_api_key(api_key, key_record.key_hash):
                    if key_record.expires_at and key_record.expires_at < __import__("datetime").datetime.utcnow():
                        continue
                    user = key_record.user
                    if user and user.is_active:
                        key_record.last_used_at = __import__("datetime").datetime.utcnow()
                        db.commit()
                        return user
        return None
    finally:
        db.close()


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
    user = await _authenticate_websocket(websocket)
    if not user:
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
        return

    await manager.connect(websocket, task_id)

    try:
        db = SessionLocal()
        last_progress = -1
        last_status = None
        last_message = None

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
            current_message = getattr(task, 'current_message', None)
            if task.progress != last_progress or task.status != last_status or current_message != last_message:
                last_progress = task.progress
                last_status = task.status
                last_message = current_message

                await websocket.send_json({
                    "task_id": task_id,
                    "status": task.status,
                    "progress": task.progress,
                    "total": task.total,
                    "current_item": task.current_item,
                    "current_message": current_message,
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
    user = await _authenticate_websocket(websocket)
    if not user:
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
        return

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
