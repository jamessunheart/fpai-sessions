"""
WebSocket Endpoint
Per Spec - real-time bidirectional chat
"""

from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from datetime import datetime
import json
import uuid
import asyncio

from app.services.memory import SESSION_MANAGER, MessageSource
from app.services.reasoning import reason_about_intent
from app.services.orchestrator import orchestrator_client
from app.services.data_extractor import extract_keyvalue_data, generate_data_prompt
from app.services.response_formatter import format_combined_response
from app.utils.logging import get_logger
from app.services.registry_info import DROPLET_REGISTRY

log = get_logger(__name__)

router = APIRouter()

# Track active WebSocket connections
active_connections: dict[str, WebSocket] = {}


def get_welcome_message() -> str:
    """Generate welcome message for new WebSocket connections"""
    welcome = "👋 **Welcome to Chat Orchestrator!**\n\n"
    welcome += "I can understand natural language requests like:\n"
    welcome += "  • \"Show me all registered items\"\n"
    welcome += "  • \"Get the system status\"\n"
    welcome += "  • \"I want to register a new user\"\n"
    welcome += "  • \"What's the dashboard showing?\"\n\n"
    welcome += "💡 For POST requests (register, route, etc.), I'll ask you for data in key:value format.\n\n"
    welcome += "What would you like to know?"
    return welcome


async def send_typing_indicator(websocket: WebSocket, session_id: str):
    """Send typing indicator to client"""
    try:
        await websocket.send_json({
            "type": "typing",
            "session_id": session_id,
            "timestamp": datetime.utcnow().isoformat() + "Z"
        })
    except Exception as e:
        log.warning("typing_indicator_failed", error=str(e))


async def send_message(websocket: WebSocket, content: str, session_id: str):
    """Send message to client"""
    try:
        await websocket.send_json({
            "type": "message",
            "content": content,
            "session_id": session_id,
            "timestamp": datetime.utcnow().isoformat() + "Z"
        })
    except Exception as e:
        log.error("send_message_failed", error=str(e))
        raise


async def send_error(websocket: WebSocket, error_msg: str, session_id: str):
    """Send error message to client"""
    try:
        await websocket.send_json({
            "type": "error",
            "content": error_msg,
            "session_id": session_id,
            "timestamp": datetime.utcnow().isoformat() + "Z"
        })
    except Exception as e:
        log.error("send_error_failed", error=str(e))


async def process_websocket_message(
    message_text: str,
    session_id: str,
    websocket: WebSocket
):
    """
    Process incoming WebSocket message.
    Similar to /chat endpoint but with real-time feedback.
    """
    log.info(
        "websocket_message_processing",
        session_id=session_id,
        message_length=len(message_text)
    )
    
    # Get session
    conversation = SESSION_MANAGER.get_session(session_id)
    conversation.set_source(MessageSource.CHAT, {"connection": "websocket"})
    
    # Add user message
    conversation.add_message("user", message_text)
    
    # Send typing indicator
    await send_typing_indicator(websocket, session_id)
    
    try:
        # Check for cancel
        if message_text.lower().strip() in ['cancel', 'abort', 'stop', 'nevermind']:
            conversation.clear_pending()
            response_text = "✅ Action cancelled. What else would you like to do?"
            conversation.add_message("assistant", response_text)
            await send_message(websocket, response_text, session_id)
            return
        
        # Check pending action
        pending = conversation.get_pending_action()
        
        if pending:
            # Extract data
            extracted_data = extract_keyvalue_data(message_text)
            
            if not extracted_data:
                # Ask again
                droplet_key = pending['droplet']
                droplet_info = DROPLET_REGISTRY.get(droplet_key)
                response_text = generate_data_prompt(
                    pending['endpoint'],
                    droplet_info['name'] if droplet_info else droplet_key
                )
                
                conversation.add_message("assistant", response_text)
                conversation.set_pending_action(pending)
                await send_message(websocket, response_text, session_id)
                return
            
            # Execute POST
            droplet_id = pending['droplet'].split('_')[1]
            
            result = await orchestrator_client.send_via_orchestrator(
                target_id=droplet_id,
                action=f"/{pending['endpoint']}",
                data=extracted_data
            )
            
            if result is None:
                response_text = "❌ Failed to send request. Please try again."
            else:
                 from app.services.data_extractor import parse_validation_error
    
    # Check if it's a validation error
                 is_validation_error, missing_fields, error_msg = parse_validation_error(result)
    
                 if is_validation_error:
                      if missing_fields:
                         response_text = f"❌ **Missing required fields:** {', '.join(missing_fields)}\n\n"
                         response_text += "Please provide: " + " ".join([f"{f}:value" for f in missing_fields])
                      else:
                         response_text = f"❌ **Validation Error:**\n\n{error_msg}"
                      conversation.set_pending_action(pending)
                 elif "error" in result:
                        error_msg = result.get("error", "Unknown error")
                        response_text = f"❌ **Request failed:** {error_msg}"    
                 else:
                         droplet_info = DROPLET_REGISTRY.get(pending['droplet'])
                         droplet_name = droplet_info['name'] if droplet_info else pending['droplet']
                         
                         response_text = f"✅ Successfully executed **{pending['endpoint']}** on **{droplet_name}**!\n\n"
                         response_text += f"**Data sent:**\n```json\n{json.dumps(extracted_data, indent=2)}\n```"
                                
     



            conversation.add_message("assistant", response_text)
            await send_message(websocket, response_text, session_id)
            return
        
        # Reason about intent
        reasoning_result = await reason_about_intent(message_text, conversation)
        
        # Handle errors
        if reasoning_result.action_type == "error":
            response_text = f"⚠️ {reasoning_result.reasoning}"
            conversation.add_message("assistant", response_text)
            await send_message(websocket, response_text, session_id)
            return
        
        # Handle clarification
        if reasoning_result.needs_clarification:
            clarification = reasoning_result.clarification_message or "Please provide more details."
            
            if reasoning_result.queries:
                query = reasoning_result.queries[0]
                conversation.set_pending_action({
                    'droplet': query['droplet'],
                    'endpoint': query['endpoint'],
                    'method': query['method']
                })
            
            conversation.add_message("assistant", clarification)
            await send_message(websocket, clarification, session_id)
            return
        
        # Execute queries
        queries = reasoning_result.queries
        
        if not queries:
            response_text = "I understood your request but couldn't determine which action to take."
            conversation.add_message("assistant", response_text)
            await send_message(websocket, response_text, session_id)
            return
        
        # Execute via Orchestrator
        if reasoning_result.action_type == "multiple_queries":
            combined_data = await orchestrator_client.query_multiple_droplets(queries)
        else:
            query = queries[0]
            droplet_id = query['droplet'].split('_')[1]
            
            result = await orchestrator_client.send_via_orchestrator(
                target_id=droplet_id,
                action=f"/{query['endpoint']}",
                data=query.get('extracted_data', {})
            )
            
            combined_data = {query['droplet']: result} if result else {}
        
        if not combined_data:
            response_text = "❌ No data could be retrieved."
            conversation.add_message("assistant", response_text)
            await send_message(websocket, response_text, session_id)
            return
        
        # Format and send response
        formatted_response = await format_combined_response(combined_data, source="chat")
        conversation.add_message("assistant", formatted_response)
        await send_message(websocket, formatted_response, session_id)
        
    except Exception as e:
        log.error(
            "websocket_processing_error",
            session_id=session_id,
            error=str(e),
            exc_info=True
        )
        
        error_msg = "❌ An error occurred while processing your request."
        await send_error(websocket, error_msg, session_id)


@router.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    """
    WebSocket endpoint for real-time chat.
    Per Spec - WebSocket support requirement.
    
    Message format from client:
    {
        "type": "message",
        "content": "user message here",
        "session_id": "optional-session-id"
    }
    
    Message format to client:
    {
        "type": "message|typing|error|welcome",
        "content": "response text",
        "session_id": "session-id",
        "timestamp": "2025-11-12T10:00:00Z"
    }
    """
    await websocket.accept()
    
    # Generate session ID
    session_id = str(uuid.uuid4())
    active_connections[session_id] = websocket
    
    log.info(
        "websocket_connected",
        session_id=session_id,
        client=websocket.client
    )
    
    try:
        # Send welcome message
        welcome = get_welcome_message()
        await websocket.send_json({
            "type": "welcome",
            "content": welcome,
            "session_id": session_id,
            "timestamp": datetime.utcnow().isoformat() + "Z"
        })
        
        # Main message loop
        while True:
            # Receive message
            data = await websocket.receive_text()
            
            try:
                message = json.loads(data)
            except json.JSONDecodeError:
                log.warning("websocket_invalid_json", data=data[:100])
                await send_error(
                    websocket,
                    "Invalid message format. Expected JSON.",
                    session_id
                )
                continue
            
            # Extract fields
            msg_type = message.get("type", "message")
            content = message.get("content", "")
            client_session_id = message.get("session_id")
            
            # Use client session ID if provided
            if client_session_id:
                session_id = client_session_id
                if session_id not in active_connections:
                    active_connections[session_id] = websocket
            
            # Handle message types
            if msg_type == "message" and content:
                await process_websocket_message(content, session_id, websocket)
            else:
                log.warning(
                    "websocket_unknown_message_type",
                    type=msg_type,
                    has_content=bool(content)
                )
    
    except WebSocketDisconnect:
        log.info("websocket_disconnected", session_id=session_id)
        if session_id in active_connections:
            del active_connections[session_id]
    
    except Exception as e:
        log.error(
            "websocket_error",
            session_id=session_id,
            error=str(e),
            exc_info=True
        )
        if session_id in active_connections:
            del active_connections[session_id]
        await websocket.close()


@router.get("/ws/connections")
async def get_connections():
    """Get count of active WebSocket connections"""
    return {
        "active_connections": len(active_connections),
        "sessions": list(active_connections.keys())
    }