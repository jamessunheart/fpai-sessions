"""
Alerts Service - Main FastAPI Application

Centralized notification service for all droplets.
Supports Telegram, SMS, and other channels with rate limiting and queuing.
"""
from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from contextlib import asynccontextmanager
from datetime import datetime
import logging
import time

from app.config import settings
from app.models import (
    SendNotificationRequest,
    SendTemplateRequest,
    NotificationResponse,
    NotificationStatus,
    NotificationChannel,
    UDCMessage,
)
from app.queue import notification_queue
from app.worker import worker
from app.templates import MessageTemplates
from app.channels import TelegramChannel, SMSChannel

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Track service start time for uptime
service_start_time = time.time()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager"""
    # Startup
    logger.info("Starting Alerts Service...")
    await worker.start()
    logger.info("Alerts Service started successfully")

    yield

    # Shutdown
    logger.info("Shutting down Alerts Service...")
    await worker.stop()
    logger.info("Alerts Service shutdown complete")


# Create FastAPI app
app = FastAPI(
    title="Alerts Service",
    description="Centralized notification service - Telegram, SMS, Email",
    version=settings.APP_VERSION,
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Global exception handler
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """Handle unexpected errors"""
    logger.error(f"Unhandled exception: {exc}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content={"detail": "Internal server error", "error": str(exc)}
    )


# ============================================================================
# UDC ENDPOINTS (Required for all droplets)
# ============================================================================

@app.get("/health", tags=["UDC"])
async def health_check():
    """
    UDC Health Check

    Returns service health status with uptime and version info.
    """
    uptime_seconds = int(time.time() - service_start_time)

    return {
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat(),
        "uptime_seconds": uptime_seconds,
        "version": settings.APP_VERSION
    }


@app.get("/capabilities", tags=["UDC"])
async def capabilities():
    """
    UDC Capabilities

    Returns information about what this service can do.
    """
    telegram = TelegramChannel()
    sms = SMSChannel()

    return {
        "service_name": settings.SERVICE_NAME,
        "droplet_id": settings.DROPLET_ID,
        "capabilities": [
            "send_telegram",
            "send_sms",
            "queue_management",
            "rate_limiting",
            "template_rendering",
            "delivery_tracking",
        ],
        "channels": {
            "telegram": telegram.is_configured(),
            "sms": sms.is_configured(),
        },
        "templates": list(MessageTemplates.list_templates().keys())
    }


@app.get("/state", tags=["UDC"])
async def state():
    """
    UDC State

    Returns current operational state of the service.
    """
    stats = await notification_queue.get_queue_stats()

    return {
        "status": "active",
        "queued": stats["total_queued"],
        "sent_today": stats["sent_today"],
        "queue_details": stats["queued"]
    }


@app.get("/dependencies", tags=["UDC"])
async def dependencies():
    """
    UDC Dependencies

    Returns services this droplet depends on.
    """
    return {
        "required_services": [
            {
                "name": "Telegram Bot API",
                "url": "https://api.telegram.org",
                "configured": bool(settings.TELEGRAM_BOT_TOKEN)
            }
        ],
        "optional_services": [
            {
                "name": "Twilio SMS",
                "url": "https://api.twilio.com",
                "configured": bool(settings.TWILIO_ACCOUNT_SID)
            }
        ]
    }


@app.post("/message", tags=["UDC"])
async def receive_message(message: UDCMessage):
    """
    UDC Message Receiver

    Receives messages from other services via the UDC protocol.
    Automatically queues notifications based on message type.
    """
    try:
        payload = message.payload

        # Handle notification requests
        if message.message_type == "task_assignment":
            channel = NotificationChannel(payload.get("channel", "telegram"))
            text = payload.get("text", "")
            recipient = payload.get("recipient", settings.TELEGRAM_STEWARD_CHAT_ID)

            message_id = await notification_queue.enqueue(
                channel=channel,
                recipient=recipient,
                message=text,
            )

            return {
                "received": True,
                "status": "queued",
                "message_id": message_id
            }

        # Unknown message type
        return {
            "received": True,
            "status": "unknown_type",
            "message_type": message.message_type
        }

    except Exception as e:
        logger.error(f"Error processing UDC message: {e}")
        raise HTTPException(status_code=400, detail=str(e))


# ============================================================================
# BUSINESS ENDPOINTS
# ============================================================================

@app.post("/send", tags=["Notifications"])
async def send_notification(request: SendNotificationRequest) -> NotificationResponse:
    """
    Send a notification

    Queue a notification for delivery on the specified channel.
    """
    try:
        message_id = await notification_queue.enqueue(
            channel=request.channel,
            recipient=request.recipient,
            message=request.message,
            priority=request.priority,
        )

        return NotificationResponse(
            message_id=message_id,
            status=NotificationStatus.QUEUED,
        )

    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Error queueing notification: {e}")
        raise HTTPException(status_code=500, detail="Failed to queue notification")


@app.post("/send/template", tags=["Notifications"])
async def send_template_notification(request: SendTemplateRequest) -> NotificationResponse:
    """
    Send a templated notification

    Render a template with provided data and queue for delivery.
    """
    try:
        # Render template
        message = MessageTemplates.render(request.template, request.data)

        # Queue notification
        message_id = await notification_queue.enqueue(
            channel=request.channel,
            recipient=request.recipient,
            message=message,
            priority=request.priority,
        )

        return NotificationResponse(
            message_id=message_id,
            status=NotificationStatus.QUEUED,
        )

    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Error sending template notification: {e}")
        raise HTTPException(status_code=500, detail="Failed to send template")


@app.post("/send/telegram/buttons", tags=["Notifications"])
async def send_telegram_with_buttons(request: Request):
    """
    Send a Telegram message with inline keyboard buttons

    This endpoint is used by proof-witness to send interactive proof confirmations.

    Request body:
    {
        "recipient": "default" or chat_id,
        "message": "The message text",
        "buttons": [[{"text": "✅ Yes", "callback_data": "confirm:123"}]]
    }
    """
    try:
        data = await request.json()
        recipient = data.get("recipient", "default")
        message = data.get("message", "")
        buttons = data.get("buttons", [])

        if not message:
            raise HTTPException(status_code=400, detail="Message is required")

        if not buttons:
            raise HTTPException(status_code=400, detail="Buttons are required")

        # Send via Telegram channel
        telegram = TelegramChannel()

        if not telegram.is_configured():
            raise HTTPException(status_code=503, detail="Telegram bot not configured")

        success = await telegram.send_with_buttons(recipient, message, buttons)

        if success:
            return {
                "status": "sent",
                "channel": "telegram",
                "recipient": recipient
            }
        else:
            raise HTTPException(status_code=500, detail="Failed to send message")

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error sending Telegram message with buttons: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/queue", tags=["Queue"])
async def get_queue():
    """
    Get current queue status

    Returns queue statistics and pending notifications.
    """
    return await notification_queue.get_queue_stats()


@app.get("/history", tags=["Queue"])
async def get_history(limit: int = 100, offset: int = 0):
    """
    Get notification history

    Returns sent notifications with pagination.
    """
    history = await notification_queue.get_history(limit, offset)
    return {
        "total": len(history),
        "limit": limit,
        "offset": offset,
        "notifications": [n.model_dump() for n in history]
    }


@app.get("/status/{message_id}", tags=["Queue"])
async def get_notification_status(message_id: str):
    """
    Get status of a specific notification

    Track delivery status by message ID.
    """
    notification = await notification_queue.get_status(message_id)
    if not notification:
        raise HTTPException(status_code=404, detail="Notification not found")

    return notification.model_dump()


@app.post("/channels/{channel}/test", tags=["Channels"])
async def test_channel(channel: NotificationChannel):
    """
    Test a notification channel

    Verify that a channel is configured and operational.
    """
    if channel == NotificationChannel.TELEGRAM:
        handler = TelegramChannel()
    elif channel == NotificationChannel.SMS:
        handler = SMSChannel()
    else:
        raise HTTPException(status_code=400, detail="Unknown channel")

    if not handler.is_configured():
        return {
            "channel": channel.value,
            "configured": False,
            "operational": False,
            "message": f"{channel.value} is not configured"
        }

    is_working = await handler.test()

    return {
        "channel": channel.value,
        "configured": True,
        "operational": is_working,
        "message": "OK" if is_working else "Channel test failed"
    }


@app.get("/templates", tags=["Templates"])
async def list_templates():
    """
    List available message templates

    Get all predefined notification templates.
    """
    templates = MessageTemplates.list_templates()
    return {
        "templates": templates,
        "count": len(templates)
    }


@app.post("/templates", tags=["Templates"])
async def add_template(name: str, template: str):
    """
    Add a new message template

    Create a custom notification template.
    """
    MessageTemplates.add_template(name, template)
    return {
        "message": "Template added successfully",
        "name": name,
        "template": template
    }


# ============================================================================
# TELEGRAM WEBHOOKS (For interactive buttons)
# ============================================================================

@app.post("/webhooks/telegram", tags=["Webhooks"])
async def telegram_webhook(request: Request):
    """
    Handle Telegram webhook updates (button clicks, messages, etc.)

    This enables interactive proof confirmations via inline buttons.
    """
    import httpx

    try:
        update = await request.json()
        logger.info(f"Telegram webhook received: {update}")

        # Handle callback query (button click)
        if "callback_query" in update:
            callback_query = update["callback_query"]
            callback_data = callback_query.get("data", "")
            callback_id = callback_query.get("id")
            user = callback_query.get("from", {})
            username = user.get("username", "unknown")

            logger.info(f"Button clicked by {username}: {callback_data}")

            # Parse callback data: "confirm:abc123" or "reject:abc123" or "edit:abc123"
            parts = callback_data.split(":", 1)
            if len(parts) == 2:
                action, proof_id = parts

                # Forward to proof-witness service
                proof_witness_url = "http://localhost:8900"

                if action == "confirm":
                    # Confirm the proof
                    async with httpx.AsyncClient() as client:
                        response = await client.post(
                            f"{proof_witness_url}/confirm/{proof_id}",
                            timeout=10.0
                        )

                        if response.status_code == 200:
                            # Acknowledge the button click
                            telegram = TelegramChannel()
                            await telegram.answer_callback(callback_id, "✅ Proof confirmed!")
                            logger.info(f"Proof {proof_id} confirmed by {username}")
                        else:
                            await telegram.answer_callback(callback_id, "❌ Failed to confirm")
                            logger.error(f"Failed to confirm proof {proof_id}")

                elif action == "reject":
                    # Reject the proof
                    async with httpx.AsyncClient() as client:
                        response = await client.post(
                            f"{proof_witness_url}/reject/{proof_id}",
                            timeout=10.0
                        )

                        telegram = TelegramChannel()
                        if response.status_code == 200:
                            await telegram.answer_callback(callback_id, "⏭️ Skipped")
                            logger.info(f"Proof {proof_id} rejected by {username}")
                        else:
                            await telegram.answer_callback(callback_id, "❌ Failed to skip")

                elif action == "edit":
                    # TODO: Show edit interface
                    telegram = TelegramChannel()
                    await telegram.answer_callback(callback_id, "✏️ Edit not implemented yet")

            return {"status": "ok", "processed": "callback_query"}

        # Handle regular messages (future: voice notes, photos)
        elif "message" in update:
            message = update["message"]
            logger.info(f"Message received: {message.get('text', '(no text)')}")
            return {"status": "ok", "processed": "message"}

        return {"status": "ok", "processed": "unknown"}

    except Exception as e:
        logger.error(f"Telegram webhook error: {e}", exc_info=True)
        return {"status": "error", "message": str(e)}


# ============================================================================
# ROOT
# ============================================================================

@app.get("/", tags=["System"])
async def root():
    """Redirect to API documentation"""
    return {
        "service": "Alerts",
        "version": settings.APP_VERSION,
        "droplet_id": settings.DROPLET_ID,
        "docs": "/docs",
        "health": "/health"
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=settings.PORT,
        reload=settings.DEBUG
    )
