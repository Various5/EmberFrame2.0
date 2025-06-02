"""
Notification service
"""

from typing import List, Dict, Any
from enum import Enum


class NotificationType(Enum):
    INFO = "info"
    SUCCESS = "success"
    WARNING = "warning"
    ERROR = "error"


class NotificationService:
    def __init__(self):
        self.subscribers = {}

    async def send_notification(
        self,
        user_id: int,
        message: str,
        type: NotificationType = NotificationType.INFO,
        data: Dict[str, Any] = None
    ):
        """Send notification to user"""
        notification = {
            "id": f"notif_{user_id}_{len(self.subscribers)}",
            "message": message,
            "type": type.value,
            "data": data or {},
            "timestamp": "2024-01-01T00:00:00Z"  # Use actual timestamp
        }

        # Here you would implement actual notification delivery
        # For example: WebSocket, email, push notification, etc.
        print(f"Notification for user {user_id}: {message}")

        return notification

    async def broadcast_notification(
        self,
        message: str,
        type: NotificationType = NotificationType.INFO,
        data: Dict[str, Any] = None
    ):
        """Broadcast notification to all users"""
        notification = {
            "message": message,
            "type": type.value,
            "data": data or {},
            "timestamp": "2024-01-01T00:00:00Z"
        }

        # Implement broadcast logic
        print(f"Broadcast notification: {message}")

        return notification
