"""
Inter-Droplet Processing Endpoint
Per Spec - handle messages from Voice Droplet 6 via Orchestrator 10
"""

from fastapi import APIRouter, HTTPException,Depends
from datetime import datetime
from app.utils.auth import verify_jwt_token
import uuid

from app.models.chat import ProcessRequest, ProcessResponse
from app.services.memory import SESSION_MANAGER, MessageSource
from app.services.reasoning import reason_about_intent
from app.services.orchestrator import orchestrator_client
from app.services.data_extractor import (
    extract_keyvalue_data,
    generate_voice_data_prompt
)
from app.services.response_formatter import format_combined_response
from app.utils.logging import get_logger
from app.services.registry_info import DROPLET_REGISTRY

log = get_logger(__name__)

router = APIRouter()


@router.post("/process", response_model=ProcessResponse)
async def process_message(
    request: ProcessRequest,
    token_data: dict = Depends(verify_jwt_token)
):
    """
    Process messages from other droplets (Voice Droplet 6) via Orchestrator 10.
    Per Spec - POST /process endpoint.
    
    Flow:
    1. Voice 6 sends message to Orchestrator 10
    2. Orchestrator 10 routes to Chat Orchestrator 12 /process
    3. Chat Orchestrator 12 processes with voice-appropriate formatting
    4. Chat Orchestrator 12 sends response to Orchestrator 10
    5. Orchestrator 10 routes back to Voice 6
    
    NO JWT required - Orchestrator handles authentication.
    """
    log.info(
        "process_request_received",
        trace_id=request.trace_id,
        source=request.source,
        target=request.target,
        message_type=request.message_type,
        route_back=request.route_back
    )
    
    # Extract message and metadata from payload
    message_text = request.payload.get("message", "")
    metadata = request.payload.get("metadata", {})
    
    if not message_text:
        log.error("process_request_missing_message", trace_id=request.trace_id)
        raise HTTPException(
            status_code=400,
            detail="Missing 'message' in payload"
        )
    
    # Determine session ID based on source
    if request.source == "6":  # Voice Droplet
        user_id = metadata.get("user_id", "unknown")
        session_id = f"droplet_6_{user_id}"
        source_type = MessageSource.VOICE
    else:
        session_id = metadata.get("session_id") or f"droplet_{request.source}_{uuid.uuid4()}"
        source_type = MessageSource.CHAT
    
    log.info(
        "process_session_info",
        trace_id=request.trace_id,
        session_id=session_id,
        source_type=source_type.value
    )
    
    # Get or create session
    conversation = SESSION_MANAGER.get_session(session_id)
    conversation.set_source(source_type, metadata)
    
    # Add user message to history
    conversation.add_message("user", message_text, metadata)
    
    try:
        # Check for cancel command
        if message_text.lower().strip() in ['cancel', 'abort', 'stop', 'nevermind']:
            conversation.clear_pending()
            
            response_text = "Action cancelled. What else would you like to do?" if source_type == MessageSource.VOICE else "✅ Action cancelled."
            conversation.add_message("assistant", response_text)
            
            return ProcessResponse(
                trace_id=request.trace_id,
                source=str(request.target),  # Our ID (12)
                target=request.route_back or request.source,
                payload={
                    "response": response_text,
                    "session_id": session_id
                },
                timestamp=datetime.utcnow().isoformat() + "Z"
            )
        
        # Check for pending action
        pending = conversation.get_pending_action()
        
        if pending:
            log.info("processing_pending_action_voice", pending=pending)
            
            # Extract data
            extracted_data = extract_keyvalue_data(message_text)
            
            if not extracted_data:
                # Still no data - ask again (voice format)
                droplet_key = pending['droplet']
                droplet_info = DROPLET_REGISTRY.get(droplet_key)
                response_text = generate_voice_data_prompt(
                    pending['endpoint'],
                    droplet_info['name'] if droplet_info else droplet_key
                )
                
                conversation.add_message("assistant", response_text)
                conversation.set_pending_action(pending)
                
                return ProcessResponse(
                    trace_id=request.trace_id,
                    source=str(request.target),
                    target=request.route_back or request.source,
                    payload={
                        "response": response_text,
                        "session_id": session_id
                    },
                    timestamp=datetime.utcnow().isoformat() + "Z"
                )
            
            # Execute pending POST
            droplet_id = pending['droplet'].split('_')[1]
            
            result = await orchestrator_client.send_via_orchestrator(
                target_id=droplet_id,
                action=f"/{pending['endpoint']}",
                data=extracted_data,
                route_back=request.route_back
            )
            
            if result is None:
                response_text = "Failed to send request. Please try again."
            else:


                from app.services.data_extractor import parse_validation_error
                # Check if it's a validation error
                is_validation_error, missing_fields, error_msg = parse_validation_error(result)
                
                if is_validation_error:
                    if missing_fields:
                        response_text = f"Missing required fields: {', '.join(missing_fields)}. "
                        response_text += f"Please provide: {' and '.join(missing_fields)}."
                    else:
                        response_text = f"Validation error: {error_msg}. Please provide the correct data"
                    conversation.set_pending_action(pending)
                elif "error" in result:
                    error_msg = result.get("error", "Unknown error")
                    response_text = f"Request failed: {error_msg}"

                else:
                    droplet_info = DROPLET_REGISTRY.get(pending['droplet'])
                    droplet_name = droplet_info['name'] if droplet_info else pending['droplet']
                    
                    # Voice-appropriate formatting
                    response_text = f"Successfully executed {pending['endpoint']} on {droplet_name}. "
                    response_text += f"Data sent: {', '.join(f'{k} is {v}' for k, v in extracted_data.items())}."
                
             
            conversation.add_message("assistant", response_text)
            
            return ProcessResponse(
                trace_id=request.trace_id,
                source=str(request.target),
                target=request.route_back or request.source,
                payload={
                    "response": response_text,
                    "session_id": session_id
                },
                timestamp=datetime.utcnow().isoformat() + "Z"
            )
        
        # No pending - reason about intent
        reasoning_result = await reason_about_intent(message_text, conversation)
        
        # Handle errors
        if reasoning_result.action_type == "error":
            response_text = reasoning_result.reasoning
            conversation.add_message("assistant", response_text)
            
            return ProcessResponse(
                trace_id=request.trace_id,
                source=str(request.target),
                target=request.route_back or request.source,
                payload={
                    "response": response_text,
                    "session_id": session_id
                },
                timestamp=datetime.utcnow().isoformat() + "Z"
            )
        
        # Handle clarification
        if reasoning_result.needs_clarification:
            clarification = reasoning_result.clarification_message or "Please provide more details."
            
            # Store pending query
            if reasoning_result.queries:
                query = reasoning_result.queries[0]
                conversation.set_pending_action({
                    'droplet': query['droplet'],
                    'endpoint': query['endpoint'],
                    'method': query['method']
                })
            
            conversation.add_message("assistant", clarification)
            
            return ProcessResponse(
                trace_id=request.trace_id,
                source=str(request.target),
                target=request.route_back or request.source,
                payload={
                    "response": clarification,
                    "session_id": session_id
                },
                timestamp=datetime.utcnow().isoformat() + "Z"
            )
        
        # Execute queries
        queries = reasoning_result.queries
        
        if not queries:
            response_text = "I understood your request but could not determine which action to take."
            conversation.add_message("assistant", response_text)
            
            return ProcessResponse(
                trace_id=request.trace_id,
                source=str(request.target),
                target=request.route_back or request.source,
                payload={
                    "response": response_text,
                    "session_id": session_id
                },
                timestamp=datetime.utcnow().isoformat() + "Z"
            )
        
        # Execute queries via Orchestrator
        if reasoning_result.action_type == "multiple_queries":
            combined_data = await orchestrator_client.query_multiple_droplets(
                queries,
                route_back=request.route_back
            )
        else:
            query = queries[0]
            droplet_id = query['droplet'].split('_')[1]
            
            result = await orchestrator_client.send_via_orchestrator(
                target_id=droplet_id,
                action=f"/{query['endpoint']}",
                data=query.get('extracted_data', {}),
                route_back=request.route_back
            )
            
            combined_data = {query['droplet']: result} if result else {}
        
        if not combined_data:
            response_text = "No data could be retrieved from the requested services."
            conversation.add_message("assistant", response_text)
            
            return ProcessResponse(
                trace_id=request.trace_id,
                source=str(request.target),
                target=request.route_back or request.source,
                payload={
                    "response": response_text,
                    "session_id": session_id
                },
                timestamp=datetime.utcnow().isoformat() + "Z"
            )
        
        # Format response (voice-appropriate - no symbols)
        formatted_response = await format_combined_response(
            combined_data,
            source="voice" if source_type == MessageSource.VOICE else "chat"
        )
        
        conversation.add_message("assistant", formatted_response)
        
        return ProcessResponse(
            trace_id=request.trace_id,
            source=str(request.target),
            target=request.route_back or request.source,
            payload={
                "response": formatted_response,
                "session_id": session_id
            },
            timestamp=datetime.utcnow().isoformat() + "Z"
        )
        
    except Exception as e:
        log.error(
            "process_error",
            trace_id=request.trace_id,
            error=str(e),
            exc_info=True
        )
        
        error_msg = "An error occurred while processing your request."
        conversation.add_message("assistant", error_msg)
        
        return ProcessResponse(
            trace_id=request.trace_id,
            source=str(request.target),
            target=request.route_back or request.source,
            payload={
                "response": error_msg,
                "session_id": session_id,
                "error": str(e)
            },
            timestamp=datetime.utcnow().isoformat() + "Z"
        )