"""
Enhanced WebSocket handlers for real-time features
"""

from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import Dict, List, Set, Optional
import json
import asyncio
from datetime import datetime
import logging

from app.core.dependencies import get_db
from app.core.security import verify_token
from app.models.user import User
from app.services.notification_service import NotificationService, NotificationType

websocket_router = APIRouter()
logger = logging.getLogger(__name__)


class ConnectionManager:
    def __init__(self):
        # Store active connections by user ID
        self.active_connections: Dict[int, Set[WebSocket]] = {}
        # Store connection metadata
        self.connection_info: Dict[WebSocket, Dict] = {}
        # Notification service
        self.notification_service = NotificationService()

    async def connect(self, websocket: WebSocket, user_id: int, user_info: dict):
        """Accept new WebSocket connection"""
        await websocket.accept()

        # Add to user's connections
        if user_id not in self.active_connections:
            self.active_connections[user_id] = set()
        self.active_connections[user_id].add(websocket)

        # Store connection metadata
        self.connection_info[websocket] = {
            "user_id": user_id,
            "user_info": user_info,
            "connected_at": datetime.utcnow(),
            "last_activity": datetime.utcnow()
        }

        logger.info(f"User {user_id} ({user_info.get('username')}) connected via WebSocket")

        # Send welcome message
        await self.send_personal_message(websocket, {
            "type": "connection_established",
            "message": "Welcome to EmberFrame V2!",
            "user_info": user_info,
            "server_time": datetime.utcnow().isoformat()
        })

        # Notify user about active sessions
        await self.send_session_info(user_id)

    async def disconnect(self, websocket: WebSocket):
        """Handle WebSocket disconnection"""
        connection_info = self.connection_info.get(websocket)
        if not connection_info:
            return

        user_id = connection_info["user_id"]
        username = connection_info["user_info"].get("username", "Unknown")

        # Remove from connections
        if user_id in self.active_connections:
            self.active_connections[user_id].discard(websocket)
            if not self.active_connections[user_id]:
                del self.active_connections[user_id]

        # Remove connection info
        del self.connection_info[websocket]

        logger.info(f"User {user_id} ({username}) disconnected from WebSocket")

    async def send_personal_message(self, websocket: WebSocket, message: dict):
        """Send message to specific WebSocket connection"""
        try:
            message["timestamp"] = datetime.utcnow().isoformat()
            await websocket.send_text(json.dumps(message))

            # Update last activity
            if websocket in self.connection_info:
                self.connection_info[websocket]["last_activity"] = datetime.utcnow()

        except Exception as e:
            logger.error(f"Error sending personal message: {e}")
            await self.disconnect(websocket)

    async def send_user_message(self, user_id: int, message: dict):
        """Send message to all connections of a specific user"""
        if user_id not in self.active_connections:
            return

        disconnected = []
        for websocket in self.active_connections[user_id]:
            try:
                await self.send_personal_message(websocket, message)
            except:
                disconnected.append(websocket)

        # Clean up disconnected sockets
        for websocket in disconnected:
            await self.disconnect(websocket)

    async def broadcast_message(self, message: dict, exclude_user: Optional[int] = None):
        """Send message to all connected users"""
        message["timestamp"] = datetime.utcnow().isoformat()

        for user_id, connections in self.active_connections.items():
            if exclude_user and user_id == exclude_user:
                continue

            disconnected = []
            for websocket in connections:
                try:
                    await websocket.send_text(json.dumps(message))
                except:
                    disconnected.append(websocket)

            # Clean up disconnected sockets
            for websocket in disconnected:
                await self.disconnect(websocket)

    async def send_notification(self, user_id: int, title: str, message: str,
                              notification_type: NotificationType = NotificationType.INFO,
                              data: Optional[dict] = None):
        """Send notification to specific user"""
        notification = {
            "type": "notification",
            "title": title,
            "message": message,
            "notification_type": notification_type.value,
            "data": data or {},
            "id": f"notif_{user_id}_{datetime.utcnow().timestamp()}"
        }

        await self.send_user_message(user_id, notification)

    async def send_system_notification(self, title: str, message: str,
                                     notification_type: NotificationType = NotificationType.INFO):
        """Send system notification to all users"""
        notification = {
            "type": "system_notification",
            "title": title,
            "message": message,
            "notification_type": notification_type.value,
            "id": f"system_{datetime.utcnow().timestamp()}"
        }

        await self.broadcast_message(notification)

    async def send_session_info(self, user_id: int):
        """Send session information to user"""
        if user_id not in self.active_connections:
            return

        connection_count = len(self.active_connections[user_id])
        session_info = {
            "type": "session_info",
            "active_sessions": connection_count,
            "total_users_online": len(self.active_connections)
        }

        await self.send_user_message(user_id, session_info)

    async def handle_file_upload_progress(self, user_id: int, filename: str, progress: int):
        """Send file upload progress"""
        message = {
            "type": "file_upload_progress",
            "filename": filename,
            "progress": progress
        }
        await self.send_user_message(user_id, message)

    async def handle_file_operation(self, user_id: int, operation: str,
                                  filename: str, status: str = "completed"):
        """Send file operation status"""
        message = {
            "type": "file_operation",
            "operation": operation,
            "filename": filename,
            "status": status
        }
        await self.send_user_message(user_id, message)

    async def send_desktop_event(self, user_id: int, event_type: str, data: dict):
        """Send desktop-specific events"""
        message = {
            "type": "desktop_event",
            "event_type": event_type,
            "data": data
        }
        await self.send_user_message(user_id, message)

    def get_online_users(self) -> List[dict]:
        """Get list of online users"""
        online_users = []
        for user_id, connections in self.active_connections.items():
            if connections:  # User has active connections
                # Get user info from any connection
                connection = next(iter(connections))
                user_info = self.connection_info[connection]["user_info"]
                online_users.append({
                    "user_id": user_id,
                    "username": user_info.get("username"),
                    "connection_count": len(connections),
                    "connected_at": self.connection_info[connection]["connected_at"].isoformat()
                })

        return online_users

    def get_user_connection_count(self, user_id: int) -> int:
        """Get number of active connections for user"""
        return len(self.active_connections.get(user_id, set()))


# Global connection manager instance
manager = ConnectionManager()


async def get_websocket_user(websocket: WebSocket, token: str, db: Session):
    """Authenticate WebSocket connection"""
    try:
        # Verify JWT token
        payload = verify_token(token)
        user_id = payload.get("sub")

        if not user_id:
            await websocket.close(code=4001, reason="Invalid token")
            return None

        # Get user from database
        user = db.query(User).filter(User.id == int(user_id)).first()
        if not user or not user.is_active:
            await websocket.close(code=4002, reason="User not found or inactive")
            return None

        return user

    except Exception as e:
        logger.error(f"WebSocket authentication error: {e}")
        await websocket.close(code=4003, reason="Authentication failed")
        return None


@websocket_router.websocket("/notifications")
async def websocket_endpoint(websocket: WebSocket, token: str, db: Session = Depends(get_db)):
    """Main WebSocket endpoint for real-time notifications"""

    # Authenticate user
    user = await get_websocket_user(websocket, token, db)
    if not user:
        return

    user_info = {
        "id": user.id,
        "username": user.username,
        "email": user.email,
        "is_admin": user.is_admin
    }

    # Connect user
    await manager.connect(websocket, user.id, user_info)

    try:
        while True:
            # Receive message from client
            data = await websocket.receive_text()

            try:
                message = json.loads(data)
                await handle_client_message(websocket, user.id, message, db)
            except json.JSONDecodeError:
                await manager.send_personal_message(websocket, {
                    "type": "error",
                    "message": "Invalid JSON format"
                })
            except Exception as e:
                logger.error(f"Error handling client message: {e}")
                await manager.send_personal_message(websocket, {
                    "type": "error",
                    "message": "Internal server error"
                })

    except WebSocketDisconnect:
        await manager.disconnect(websocket)
    except Exception as e:
        logger.error(f"WebSocket error: {e}")
        await manager.disconnect(websocket)


async def handle_client_message(websocket: WebSocket, user_id: int, message: dict, db: Session):
    """Handle incoming client messages"""
    message_type = message.get("type")

    if message_type == "ping":
        # Respond to ping with pong
        await manager.send_personal_message(websocket, {
            "type": "pong",
            "timestamp": datetime.utcnow().isoformat()
        })

    elif message_type == "desktop_event":
        # Handle desktop-specific events
        event_data = message.get("data", {})
        await handle_desktop_event(user_id, event_data, db)

    elif message_type == "request_online_users":
        # Send list of online users (admin only)
        user = db.query(User).filter(User.id == user_id).first()
        if user and user.is_admin:
            online_users = manager.get_online_users()
            await manager.send_personal_message(websocket, {
                "type": "online_users",
                "users": online_users
            })

    elif message_type == "send_message":
        # Send message to another user (if authorized)
        target_user_id = message.get("target_user_id")
        msg_content = message.get("message")

        if target_user_id and msg_content:
            await manager.send_user_message(target_user_id, {
                "type": "user_message",
                "from_user_id": user_id,
                "message": msg_content
            })

    else:
        await manager.send_personal_message(websocket, {
            "type": "error",
            "message": f"Unknown message type: {message_type}"
        })


async def handle_desktop_event(user_id: int, event_data: dict, db: Session):
    """Handle desktop-specific events"""
    event_type = event_data.get("event_type")

    if event_type == "window_opened":
        app_name = event_data.get("app_name")
        await manager.send_desktop_event(user_id, "window_opened", {
            "app_name": app_name,
            "timestamp": datetime.utcnow().isoformat()
        })

    elif event_type == "file_operation":
        operation = event_data.get("operation")
        filename = event_data.get("filename")

        await manager.handle_file_operation(user_id, operation, filename)

    elif event_type == "user_activity":
        # Log user activity
        activity_type = event_data.get("activity_type")
        logger.info(f"User {user_id} activity: {activity_type}")


# Additional WebSocket routes for specific features

@websocket_router.websocket("/file-operations")
async def file_operations_websocket(websocket: WebSocket, token: str, db: Session = Depends(get_db)):
    """WebSocket for file operation updates"""
    user = await get_websocket_user(websocket, token, db)
    if not user:
        return

    await websocket.accept()

    try:
        while True:
            data = await websocket.receive_text()
            message = json.loads(data)

            # Handle file operation messages
            if message.get("type") == "upload_progress":
                filename = message.get("filename")
                progress = message.get("progress", 0)

                await manager.handle_file_upload_progress(user.id, filename, progress)

    except WebSocketDisconnect:
        pass
    except Exception as e:
        logger.error(f"File operations WebSocket error: {e}")


@websocket_router.websocket("/system-monitor")
async def system_monitor_websocket(websocket: WebSocket, token: str, db: Session = Depends(get_db)):
    """WebSocket for system monitoring (admin only)"""
    user = await get_websocket_user(websocket, token, db)
    if not user or not user.is_admin:
        await websocket.close(code=4004, reason="Admin access required")
        return

    await websocket.accept()

    try:
        while True:
            # Send system statistics every 30 seconds
            await asyncio.sleep(30)

            system_stats = {
                "type": "system_stats",
                "online_users": len(manager.active_connections),
                "total_connections": sum(len(conns) for conns in manager.active_connections.values()),
                "timestamp": datetime.utcnow().isoformat()
            }

            await websocket.send_text(json.dumps(system_stats))

    except WebSocketDisconnect:
        pass
    except Exception as e:
        logger.error(f"System monitor WebSocket error: {e}")


# Utility functions for other services to use

async def notify_user(user_id: int, title: str, message: str,
                     notification_type: NotificationType = NotificationType.INFO,
                     data: Optional[dict] = None):
    """Send notification to user (to be used by other services)"""
    await manager.send_notification(user_id, title, message, notification_type, data)


async def notify_file_operation(user_id: int, operation: str, filename: str, status: str = "completed"):
    """Notify user about file operation"""
    await manager.handle_file_operation(user_id, operation, filename, status)


async def broadcast_system_message(title: str, message: str,
                                 notification_type: NotificationType = NotificationType.INFO):
    """Broadcast system message to all users"""
    await manager.send_system_notification(title, message, notification_type)


async def send_desktop_event(user_id: int, event_type: str, data: dict):
    """Send desktop event to user"""
    await manager.send_desktop_event(user_id, event_type, data)


def get_online_user_count() -> int:
    """Get number of online users"""
    return len(manager.active_connections)


def get_user_connection_count(user_id: int) -> int:
    """Get number of active connections for user"""
    return manager.get_user_connection_count(user_id)


# Background task to clean up inactive connections
async def cleanup_inactive_connections():
    """Clean up inactive WebSocket connections"""
    while True:
        try:
            await asyncio.sleep(300)  # Run every 5 minutes

            current_time = datetime.utcnow()
            inactive_connections = []

            for websocket, info in manager.connection_info.items():
                # Consider connection inactive if no activity for 30 minutes
                if (current_time - info["last_activity"]).total_seconds() > 1800:
                    inactive_connections.append(websocket)

            # Disconnect inactive connections
            for websocket in inactive_connections:
                try:
                    await manager.disconnect(websocket)
                    await websocket.close(code=4005, reason="Connection timeout")
                except:
                    pass

            if inactive_connections:
                logger.info(f"Cleaned up {len(inactive_connections)} inactive WebSocket connections")

        except Exception as e:
            logger.error(f"Error in connection cleanup task: {e}")


# Start cleanup task
asyncio.create_task(cleanup_inactive_connections())