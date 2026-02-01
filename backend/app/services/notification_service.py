"""Notification service for sending alerts via various channels"""

import logging
import asyncio
import json
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any

import httpx
from sqlalchemy.orm import Session

from ..models.notification import NotificationChannel, NotificationRule, NotificationLog
from ..schemas.notification import (
    NotificationChannelCreate, NotificationChannelUpdate,
    NotificationRuleCreate, NotificationRuleUpdate
)
from ..core.events import Event, EventType

logger = logging.getLogger(__name__)


class NotificationService:
    """Service for managing and sending notifications"""

    def __init__(self, db: Session):
        self.db = db

    # Channel management
    def create_channel(self, channel_data: NotificationChannelCreate, user_id: Optional[int] = None) -> NotificationChannel:
        """Create a notification channel"""
        channel = NotificationChannel(
            name=channel_data.name,
            channel_type=channel_data.channel_type,
            config=channel_data.config,
            enabled=channel_data.enabled,
            created_by=user_id
        )
        self.db.add(channel)
        self.db.commit()
        self.db.refresh(channel)
        logger.info(f"Notification channel created: {channel.name}")
        return channel

    def update_channel(self, channel_id: int, channel_data: NotificationChannelUpdate) -> Optional[NotificationChannel]:
        """Update a notification channel"""
        channel = self.db.query(NotificationChannel).filter(NotificationChannel.id == channel_id).first()
        if not channel:
            return None

        update_data = channel_data.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            setattr(channel, field, value)

        self.db.commit()
        self.db.refresh(channel)
        return channel

    def delete_channel(self, channel_id: int) -> bool:
        """Delete a notification channel"""
        channel = self.db.query(NotificationChannel).filter(NotificationChannel.id == channel_id).first()
        if not channel:
            return False

        self.db.delete(channel)
        self.db.commit()
        return True

    def get_channel(self, channel_id: int) -> Optional[NotificationChannel]:
        """Get channel by ID"""
        return self.db.query(NotificationChannel).filter(NotificationChannel.id == channel_id).first()

    def list_channels(self) -> List[NotificationChannel]:
        """List all channels"""
        return self.db.query(NotificationChannel).all()

    async def test_channel(self, channel_id: int, message: str = "Test notification") -> Dict[str, Any]:
        """Test a notification channel"""
        channel = self.get_channel(channel_id)
        if not channel:
            return {"success": False, "error": "Channel not found"}

        try:
            await self._send_to_channel(channel, "Test Notification", message)
            channel.last_test = datetime.utcnow()
            channel.last_test_status = "success"
            channel.verified = True
            self.db.commit()
            return {"success": True, "message": "Test notification sent"}
        except Exception as e:
            channel.last_test = datetime.utcnow()
            channel.last_test_status = "failed"
            self.db.commit()
            return {"success": False, "error": str(e)}

    # Rule management
    def create_rule(self, rule_data: NotificationRuleCreate) -> NotificationRule:
        """Create a notification rule"""
        rule = NotificationRule(
            name=rule_data.name,
            channel_id=rule_data.channel_id,
            event_types=rule_data.event_types,
            router_filter=rule_data.router_filter,
            severity_filter=rule_data.severity_filter,
            cooldown_seconds=rule_data.cooldown_seconds,
            max_per_hour=rule_data.max_per_hour,
            aggregate=rule_data.aggregate,
            aggregate_window=rule_data.aggregate_window,
            custom_template=rule_data.custom_template,
            include_details=rule_data.include_details,
            enabled=rule_data.enabled
        )
        self.db.add(rule)
        self.db.commit()
        self.db.refresh(rule)
        return rule

    def update_rule(self, rule_id: int, rule_data: NotificationRuleUpdate) -> Optional[NotificationRule]:
        """Update a notification rule"""
        rule = self.db.query(NotificationRule).filter(NotificationRule.id == rule_id).first()
        if not rule:
            return None

        update_data = rule_data.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            setattr(rule, field, value)

        self.db.commit()
        self.db.refresh(rule)
        return rule

    def delete_rule(self, rule_id: int) -> bool:
        """Delete a notification rule"""
        rule = self.db.query(NotificationRule).filter(NotificationRule.id == rule_id).first()
        if not rule:
            return False

        self.db.delete(rule)
        self.db.commit()
        return True

    def list_rules(self, channel_id: Optional[int] = None) -> List[NotificationRule]:
        """List notification rules"""
        query = self.db.query(NotificationRule)
        if channel_id:
            query = query.filter(NotificationRule.channel_id == channel_id)
        return query.all()

    # Notification sending
    async def process_event(self, event: Event):
        """Process an event and send notifications based on rules"""
        event_type_str = event.type.value if isinstance(event.type, EventType) else event.type

        # Find matching rules
        rules = self.db.query(NotificationRule).filter(
            NotificationRule.enabled == True
        ).all()

        for rule in rules:
            if not self._rule_matches_event(rule, event_type_str, event):
                continue

            if not self._check_throttling(rule):
                continue

            channel = rule.channel
            if not channel or not channel.enabled:
                continue

            try:
                subject, body = self._format_notification(rule, event)
                await self._send_to_channel(channel, subject, body)

                # Log success
                self._log_notification(
                    channel_id=channel.id,
                    rule_id=rule.id,
                    event_type=event_type_str,
                    event_data=event.data,
                    status="sent",
                    subject=subject,
                    body=body
                )

                # Update rule stats
                rule.last_triggered = datetime.utcnow()
                rule.trigger_count += 1
                self.db.commit()

            except Exception as e:
                logger.error(f"Failed to send notification: {e}")
                self._log_notification(
                    channel_id=channel.id,
                    rule_id=rule.id,
                    event_type=event_type_str,
                    event_data=event.data,
                    status="failed",
                    error_message=str(e)
                )

    def _rule_matches_event(self, rule: NotificationRule, event_type: str, event: Event) -> bool:
        """Check if a rule matches an event"""
        # Check event type
        if rule.event_types and event_type not in rule.event_types:
            return False

        # Check router filter
        if rule.router_filter and event.router_id:
            router_filter = rule.router_filter
            if "ids" in router_filter and router_filter["ids"]:
                if event.router_id not in router_filter["ids"]:
                    return False

        # Check severity filter
        if rule.severity_filter:
            severity = event.data.get("severity", "info")
            if severity not in rule.severity_filter:
                return False

        return True

    def _check_throttling(self, rule: NotificationRule) -> bool:
        """Check if notification is within rate limits"""
        if rule.last_triggered:
            cooldown = timedelta(seconds=rule.cooldown_seconds)
            if datetime.utcnow() - rule.last_triggered < cooldown:
                return False

        # Check hourly limit
        hour_ago = datetime.utcnow() - timedelta(hours=1)
        recent_count = self.db.query(NotificationLog).filter(
            NotificationLog.rule_id == rule.id,
            NotificationLog.created_at > hour_ago,
            NotificationLog.status == "sent"
        ).count()

        if recent_count >= rule.max_per_hour:
            return False

        return True

    def _format_notification(self, rule: NotificationRule, event: Event) -> tuple:
        """Format notification subject and body"""
        event_type = event.type.value if isinstance(event.type, EventType) else event.type
        data = event.data

        if rule.custom_template:
            # Use Jinja2 template
            from jinja2 import Template
            template = Template(rule.custom_template)
            body = template.render(event=event, data=data)
            subject = f"MikroTik Alert: {event_type}"
        else:
            subject = f"MikroTik Alert: {event_type}"
            body = self._default_format(event_type, data, rule.include_details)

        return subject, body

    def _default_format(self, event_type: str, data: dict, include_details: bool) -> str:
        """Default notification format"""
        lines = [f"Event: {event_type}", f"Time: {datetime.utcnow().isoformat()}"]

        if data.get("router_ip"):
            lines.append(f"Router: {data.get('router_identity', 'Unknown')} ({data['router_ip']})")

        if data.get("message"):
            lines.append(f"Message: {data['message']}")

        if include_details and data:
            lines.append("\nDetails:")
            for key, value in data.items():
                if key not in ["router_ip", "router_identity", "message"]:
                    lines.append(f"  {key}: {value}")

        return "\n".join(lines)

    async def _send_to_channel(self, channel: NotificationChannel, subject: str, body: str):
        """Send notification to a specific channel"""
        channel_type = channel.channel_type
        config = channel.config

        if channel_type == "email":
            await self._send_email(config, subject, body)
        elif channel_type == "slack":
            await self._send_slack(config, subject, body)
        elif channel_type == "telegram":
            await self._send_telegram(config, subject, body)
        elif channel_type == "webhook":
            await self._send_webhook(config, subject, body)
        elif channel_type == "discord":
            await self._send_discord(config, subject, body)
        else:
            raise ValueError(f"Unknown channel type: {channel_type}")

    async def _send_email(self, config: dict, subject: str, body: str):
        """Send email notification"""
        try:
            import aiosmtplib
            from email.mime.text import MIMEText

            msg = MIMEText(body)
            msg["Subject"] = subject
            msg["From"] = config.get("from_address")
            msg["To"] = ", ".join(config.get("to_addresses", []))

            await aiosmtplib.send(
                msg,
                hostname=config.get("smtp_host"),
                port=config.get("smtp_port", 587),
                username=config.get("username"),
                password=config.get("password"),
                use_tls=config.get("use_tls", True)
            )
        except ImportError:
            logger.warning("aiosmtplib not installed, email notifications disabled")
            raise

    async def _send_slack(self, config: dict, subject: str, body: str):
        """Send Slack notification"""
        webhook_url = config.get("webhook_url")
        if not webhook_url:
            raise ValueError("Slack webhook URL not configured")

        payload = {
            "text": f"*{subject}*\n{body}",
            "username": config.get("username", "MikroTik Updater")
        }

        if config.get("channel"):
            payload["channel"] = config["channel"]

        async with httpx.AsyncClient() as client:
            response = await client.post(webhook_url, json=payload)
            response.raise_for_status()

    async def _send_telegram(self, config: dict, subject: str, body: str):
        """Send Telegram notification"""
        bot_token = config.get("bot_token")
        chat_ids = config.get("chat_ids", [])

        if not bot_token or not chat_ids:
            raise ValueError("Telegram bot token or chat IDs not configured")

        message = f"*{subject}*\n\n{body}"

        async with httpx.AsyncClient() as client:
            for chat_id in chat_ids:
                url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
                await client.post(url, json={
                    "chat_id": chat_id,
                    "text": message,
                    "parse_mode": "Markdown"
                })

    async def _send_webhook(self, config: dict, subject: str, body: str):
        """Send webhook notification"""
        url = config.get("url")
        if not url:
            raise ValueError("Webhook URL not configured")

        payload = {
            "subject": subject,
            "body": body,
            "timestamp": datetime.utcnow().isoformat()
        }

        headers = config.get("headers", {})
        method = config.get("method", "POST").upper()

        async with httpx.AsyncClient() as client:
            if method == "POST":
                response = await client.post(url, json=payload, headers=headers)
            else:
                response = await client.put(url, json=payload, headers=headers)
            response.raise_for_status()

    async def _send_discord(self, config: dict, subject: str, body: str):
        """Send Discord notification"""
        webhook_url = config.get("webhook_url")
        if not webhook_url:
            raise ValueError("Discord webhook URL not configured")

        payload = {
            "embeds": [{
                "title": subject,
                "description": body,
                "color": 3447003  # Blue color
            }]
        }

        async with httpx.AsyncClient() as client:
            response = await client.post(webhook_url, json=payload)
            response.raise_for_status()

    def _log_notification(
        self,
        channel_id: int,
        rule_id: Optional[int],
        event_type: str,
        event_data: dict,
        status: str,
        subject: Optional[str] = None,
        body: Optional[str] = None,
        error_message: Optional[str] = None
    ):
        """Log a notification attempt"""
        log = NotificationLog(
            channel_id=channel_id,
            rule_id=rule_id,
            event_type=event_type,
            event_data=event_data,
            status=status,
            subject=subject,
            body=body,
            error_message=error_message,
            sent_at=datetime.utcnow() if status == "sent" else None
        )
        self.db.add(log)
        self.db.commit()

    def get_logs(
        self,
        channel_id: Optional[int] = None,
        status: Optional[str] = None,
        limit: int = 100
    ) -> List[NotificationLog]:
        """Get notification logs"""
        query = self.db.query(NotificationLog)
        if channel_id:
            query = query.filter(NotificationLog.channel_id == channel_id)
        if status:
            query = query.filter(NotificationLog.status == status)
        return query.order_by(NotificationLog.created_at.desc()).limit(limit).all()
