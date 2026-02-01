"""Webhook service for external integrations"""

import logging
import hashlib
import hmac
import json
import asyncio
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any, Tuple

import httpx
from sqlalchemy.orm import Session

from ..models.webhook import Webhook, WebhookDelivery
from ..schemas.webhook import WebhookCreate, WebhookUpdate
from ..core.events import Event, EventType

logger = logging.getLogger(__name__)


# Available webhook events
WEBHOOK_EVENTS = [
    {"event": "router_added", "description": "When a new router is added"},
    {"event": "router_removed", "description": "When a router is removed"},
    {"event": "router_updated", "description": "When router information is updated"},
    {"event": "router_offline", "description": "When a router goes offline"},
    {"event": "router_online", "description": "When a router comes back online"},
    {"event": "scan_completed", "description": "When a network scan completes"},
    {"event": "update_started", "description": "When an update operation starts"},
    {"event": "update_completed", "description": "When an update operation completes"},
    {"event": "update_failed", "description": "When an update operation fails"},
    {"event": "backup_created", "description": "When a backup is created"},
    {"event": "backup_failed", "description": "When a backup operation fails"},
    {"event": "script_executed", "description": "When a custom script is executed"},
    {"event": "alert_created", "description": "When an alert is created"},
]


class WebhookService:
    """Service for managing webhooks and delivering payloads"""

    def __init__(self, db: Session):
        self.db = db

    def create_webhook(self, webhook_data: WebhookCreate, user_id: Optional[int] = None) -> Webhook:
        """Create a new webhook"""
        webhook = Webhook(
            name=webhook_data.name,
            description=webhook_data.description,
            url=webhook_data.url,
            method=webhook_data.method,
            headers=webhook_data.headers,
            auth_type=webhook_data.auth_type,
            auth_config=webhook_data.auth_config,
            content_type=webhook_data.content_type,
            payload_template=webhook_data.payload_template,
            include_signature=webhook_data.include_signature,
            events=webhook_data.events,
            router_filter=webhook_data.router_filter,
            retry_count=webhook_data.retry_count,
            retry_delay=webhook_data.retry_delay,
            timeout=webhook_data.timeout,
            enabled=webhook_data.enabled,
            created_by=user_id
        )

        # Generate secret key for signatures
        if webhook.include_signature and not webhook.secret_key:
            import secrets
            webhook.secret_key = secrets.token_urlsafe(32)

        self.db.add(webhook)
        self.db.commit()
        self.db.refresh(webhook)
        logger.info(f"Webhook created: {webhook.name}")
        return webhook

    def update_webhook(
        self,
        webhook_id: int,
        webhook_data: WebhookUpdate
    ) -> Optional[Webhook]:
        """Update a webhook"""
        webhook = self.db.query(Webhook).filter(Webhook.id == webhook_id).first()
        if not webhook:
            return None

        update_data = webhook_data.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            setattr(webhook, field, value)

        self.db.commit()
        self.db.refresh(webhook)
        return webhook

    def delete_webhook(self, webhook_id: int) -> bool:
        """Delete a webhook"""
        webhook = self.db.query(Webhook).filter(Webhook.id == webhook_id).first()
        if not webhook:
            return False

        self.db.delete(webhook)
        self.db.commit()
        return True

    def get_webhook(self, webhook_id: int) -> Optional[Webhook]:
        """Get webhook by ID"""
        return self.db.query(Webhook).filter(Webhook.id == webhook_id).first()

    def list_webhooks(
        self,
        enabled_only: bool = False,
        skip: int = 0,
        limit: int = 100
    ) -> Tuple[List[Webhook], int]:
        """List webhooks"""
        query = self.db.query(Webhook)

        if enabled_only:
            query = query.filter(Webhook.enabled == True)

        total = query.count()
        webhooks = query.offset(skip).limit(limit).all()
        return webhooks, total

    async def test_webhook(
        self,
        webhook_id: int,
        event_type: str = "test",
        data: Dict[str, Any] = None
    ) -> Dict[str, Any]:
        """Test a webhook with sample data"""
        webhook = self.get_webhook(webhook_id)
        if not webhook:
            return {"success": False, "error": "Webhook not found"}

        test_data = data or {
            "message": "Test webhook delivery",
            "timestamp": datetime.utcnow().isoformat()
        }

        try:
            result = await self._deliver_webhook(
                webhook,
                event_type,
                test_data,
                is_test=True
            )

            # Update webhook status
            webhook.verified = result["success"]
            self.db.commit()

            return result

        except Exception as e:
            return {"success": False, "error": str(e)}

    async def process_event(self, event: Event):
        """Process an event and trigger matching webhooks"""
        event_type_str = event.type.value if isinstance(event.type, EventType) else event.type

        # Find matching webhooks
        webhooks = self.db.query(Webhook).filter(
            Webhook.enabled == True
        ).all()

        for webhook in webhooks:
            if not self._webhook_matches_event(webhook, event_type_str, event):
                continue

            # Queue delivery
            asyncio.create_task(
                self._deliver_webhook(webhook, event_type_str, event.data)
            )

    def _webhook_matches_event(self, webhook: Webhook, event_type: str, event: Event) -> bool:
        """Check if a webhook should be triggered for an event"""
        # Check event type
        if webhook.events and event_type not in webhook.events:
            return False

        # Check router filter
        if webhook.router_filter and event.router_id:
            router_filter = webhook.router_filter
            if "ids" in router_filter and router_filter["ids"]:
                if event.router_id not in router_filter["ids"]:
                    return False

        return True

    async def _deliver_webhook(
        self,
        webhook: Webhook,
        event_type: str,
        event_data: Dict[str, Any],
        is_test: bool = False
    ) -> Dict[str, Any]:
        """Deliver webhook payload"""
        # Prepare payload
        payload = self._prepare_payload(webhook, event_type, event_data)

        # Prepare headers
        headers = dict(webhook.headers) if webhook.headers else {}
        headers["Content-Type"] = webhook.content_type
        headers["User-Agent"] = "MikroTik-Mass-Updater-Webhook/1.0"

        # Add authentication
        self._add_auth_headers(headers, webhook)

        # Add signature if enabled
        body = json.dumps(payload)
        if webhook.include_signature and webhook.secret_key:
            signature = self._generate_signature(body, webhook.secret_key)
            headers["X-Webhook-Signature"] = signature
            headers["X-Webhook-Signature-256"] = f"sha256={signature}"

        # Create delivery record
        delivery = WebhookDelivery(
            webhook_id=webhook.id,
            event_type=event_type,
            event_data=event_data,
            request_url=webhook.url,
            request_method=webhook.method,
            request_headers=headers,
            request_body=body,
            status="pending"
        )

        if not is_test:
            self.db.add(delivery)
            self.db.commit()
            self.db.refresh(delivery)

        # Attempt delivery
        result = await self._send_request(
            webhook,
            headers,
            body,
            delivery if not is_test else None
        )

        if not is_test:
            # Update webhook stats
            webhook.last_triggered = datetime.utcnow()
            webhook.last_status = "success" if result["success"] else "failed"
            webhook.total_deliveries += 1
            if result["success"]:
                webhook.successful_deliveries += 1
            else:
                webhook.failed_deliveries += 1
            self.db.commit()

        return result

    def _prepare_payload(
        self,
        webhook: Webhook,
        event_type: str,
        event_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Prepare webhook payload"""
        if webhook.payload_template:
            # Use Jinja2 template
            from jinja2 import Template
            template = Template(webhook.payload_template)
            payload_str = template.render(
                event_type=event_type,
                data=event_data,
                timestamp=datetime.utcnow().isoformat()
            )
            return json.loads(payload_str)
        else:
            # Default payload
            return {
                "event": event_type,
                "data": event_data,
                "timestamp": datetime.utcnow().isoformat(),
                "source": "mikrotik-mass-updater"
            }

    def _add_auth_headers(self, headers: Dict[str, str], webhook: Webhook):
        """Add authentication headers"""
        if not webhook.auth_type or webhook.auth_type == "none":
            return

        config = webhook.auth_config or {}

        if webhook.auth_type == "basic":
            import base64
            credentials = f"{config.get('username', '')}:{config.get('password', '')}"
            encoded = base64.b64encode(credentials.encode()).decode()
            headers["Authorization"] = f"Basic {encoded}"

        elif webhook.auth_type == "bearer":
            token = config.get("token", "")
            headers["Authorization"] = f"Bearer {token}"

        elif webhook.auth_type == "custom":
            custom_header = config.get("header", "Authorization")
            custom_value = config.get("value", "")
            headers[custom_header] = custom_value

    def _generate_signature(self, body: str, secret: str) -> str:
        """Generate HMAC signature for payload"""
        signature = hmac.new(
            secret.encode(),
            body.encode(),
            hashlib.sha256
        ).hexdigest()
        return signature

    async def _send_request(
        self,
        webhook: Webhook,
        headers: Dict[str, str],
        body: str,
        delivery: Optional[WebhookDelivery] = None
    ) -> Dict[str, Any]:
        """Send HTTP request"""
        start_time = datetime.utcnow()

        try:
            async with httpx.AsyncClient(timeout=webhook.timeout) as client:
                if webhook.method.upper() == "POST":
                    response = await client.post(
                        webhook.url,
                        content=body,
                        headers=headers
                    )
                else:
                    response = await client.put(
                        webhook.url,
                        content=body,
                        headers=headers
                    )

            duration_ms = int((datetime.utcnow() - start_time).total_seconds() * 1000)

            # Update delivery record
            if delivery:
                delivery.response_status = response.status_code
                delivery.response_headers = dict(response.headers)
                delivery.response_body = response.text[:10000]  # Limit size
                delivery.sent_at = datetime.utcnow()
                delivery.duration_ms = duration_ms

                if response.status_code >= 200 and response.status_code < 300:
                    delivery.status = "success"
                else:
                    delivery.status = "failed"
                    delivery.error_message = f"HTTP {response.status_code}"

                self.db.commit()

            return {
                "success": 200 <= response.status_code < 300,
                "status_code": response.status_code,
                "response_body": response.text[:1000],
                "duration_ms": duration_ms
            }

        except Exception as e:
            duration_ms = int((datetime.utcnow() - start_time).total_seconds() * 1000)

            if delivery:
                delivery.status = "failed"
                delivery.error_message = str(e)
                delivery.duration_ms = duration_ms

                # Schedule retry if applicable
                if delivery.attempt_count < webhook.retry_count:
                    delivery.status = "retrying"
                    delivery.next_retry_at = datetime.utcnow() + timedelta(seconds=webhook.retry_delay)
                    asyncio.create_task(self._retry_delivery(delivery.id))

                self.db.commit()

            return {
                "success": False,
                "error": str(e),
                "duration_ms": duration_ms
            }

    async def _retry_delivery(self, delivery_id: int):
        """Retry a failed delivery"""
        delivery = self.db.query(WebhookDelivery).filter(
            WebhookDelivery.id == delivery_id
        ).first()

        if not delivery or delivery.status != "retrying":
            return

        webhook = delivery.webhook
        if not webhook or not webhook.enabled:
            delivery.status = "failed"
            self.db.commit()
            return

        # Wait for retry delay
        if delivery.next_retry_at:
            delay = (delivery.next_retry_at - datetime.utcnow()).total_seconds()
            if delay > 0:
                await asyncio.sleep(delay)

        # Increment attempt count
        delivery.attempt_count += 1
        self.db.commit()

        # Retry request
        headers = delivery.request_headers or {}
        await self._send_request(
            webhook,
            headers,
            delivery.request_body,
            delivery
        )

    def get_deliveries(
        self,
        webhook_id: Optional[int] = None,
        status: Optional[str] = None,
        skip: int = 0,
        limit: int = 100
    ) -> Tuple[List[WebhookDelivery], int]:
        """Get webhook deliveries"""
        query = self.db.query(WebhookDelivery)

        if webhook_id:
            query = query.filter(WebhookDelivery.webhook_id == webhook_id)
        if status:
            query = query.filter(WebhookDelivery.status == status)

        total = query.count()
        deliveries = query.order_by(
            WebhookDelivery.created_at.desc()
        ).offset(skip).limit(limit).all()

        return deliveries, total

    def get_available_events(self) -> List[Dict[str, Any]]:
        """Get list of available webhook events"""
        return WEBHOOK_EVENTS

    def resend_delivery(self, delivery_id: int) -> Optional[WebhookDelivery]:
        """Resend a failed delivery"""
        delivery = self.db.query(WebhookDelivery).filter(
            WebhookDelivery.id == delivery_id
        ).first()

        if not delivery:
            return None

        # Reset delivery for retry
        delivery.status = "pending"
        delivery.attempt_count = 0
        delivery.error_message = None
        self.db.commit()

        # Queue delivery
        asyncio.create_task(self._retry_delivery(delivery.id))

        return delivery
