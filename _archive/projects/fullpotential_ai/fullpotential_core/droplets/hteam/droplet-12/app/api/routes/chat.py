"""
Chat Endpoints
Per Spec - direct chat API for web/mobile clients
"""

from fastapi import APIRouter, HTTPException,Depends
from datetime import datetime
import uuid
import json
import asyncio

from app.models.chat import (
    ChatRequest,
    ChatResponse,
    AnalyzeRequest,
    AnalyzeResponse
)
from app.services.memory import SESSION_MANAGER, MessageSource
from app.services.reasoning import reason_about_intent, analyze_text
from app.services.orchestrator import orchestrator_client
from app.models.udc import TaskCreate, TaskPayload # Import new models
from app.services.data_extractor import (
    extract_keyvalue_data,
    generate_data_prompt
)
from app.services.response_formatter import format_combined_response
from app.utils.logging import get_logger
from app.services.registry_info import DROPLET_REGISTRY
from app.utils.auth import verify_jwt_token
log = get_logger(__name__)

router = APIRouter()



@router.post("/chat", response_model=ChatResponse)
async def chat(
    request: ChatRequest,
    token_data: dict = Depends(verify_jwt_token)
):
    """
    Direct chat endpoint for web/mobile clients.
    Per Spec - POST /chat endpoint.
    NO JWT required (public chat interface).
    
    Flow:
    1. User types message in chat interface
    2. Message sent directly to this endpoint
    3. Process with AI reasoning
    4. Route queries through Orchestrator 10
    5. Format and return response
    """
    log.info(
        "chat_request_received",
        message_length=len(request.message),
        session_id=request.session_id,
        has_metadata=bool(request.metadata)
    )
    
    # Generate or use provided session ID
    session_id = request.session_id or str(uuid.uuid4())
    
    # Get or create session
    conversation = SESSION_MANAGER.get_session(session_id)
    conversation.set_source(MessageSource.CHAT, request.metadata)
    
    # Add user message to history
    conversation.add_message("user", request.message, request.metadata)
    
    try:
        # Check for cancel command
        if request.message.lower().strip() in ['cancel', 'abort', 'stop', 'nevermind']:
            conversation.clear_pending()
            response_text = "✅ Action cancelled. What else would you like to do?"
            conversation.add_message("assistant", response_text)
            
            return ChatResponse(
                response=response_text,
                session_id=session_id,
                trace_id=str(uuid.uuid4()),
                timestamp=datetime.utcnow().isoformat() + "Z"
            )
        
        # Check if there's a pending action waiting for data
        pending = conversation.get_pending_action()
        
        if pending:
            log.info("processing_pending_action", pending=pending)
            
            # Try to extract data
            extracted_data = extract_keyvalue_data(request.message)
            
            if not extracted_data:
                # Still no data - ask again
                droplet_key = pending['droplet']
                droplet_info = DROPLET_REGISTRY.get(droplet_key)
                response_text = generate_data_prompt(
                    pending['endpoint'],
                    droplet_info['name'] if droplet_info else droplet_key
                )
                
                conversation.add_message("assistant", response_text)
                conversation.set_pending_action(pending)  # Keep pending
                
                return ChatResponse(
                    response=response_text,
                    session_id=session_id,
                    trace_id=str(uuid.uuid4()),
                    timestamp=datetime.utcnow().isoformat() + "Z"
                )
            
            # Execute pending POST with data
            droplet_id = pending['droplet'].split('_')[1]
            
            result = await orchestrator_client.send_via_orchestrator(
                target_id=droplet_id,
                action=f"/{pending['endpoint']}",
                data=extracted_data
            )
            
            if result is None:
                response_text = "❌ Failed to send request to backend. Please try again."
            else:
                from app.services.data_extractor import parse_validation_error
                # Check if it's a validation error
                is_validation_error, missing_fields, error_msg = parse_validation_error(result)
                
                if is_validation_error:
                    if missing_fields:
                       response_text = f"❌ **Missing required fields:** {', '.join(missing_fields)}\n\n"
                       response_text += "Please provide these fields:\n\n"
                       response_text += "**Format:** " + " ".join([f"{f}:value" for f in missing_fields])

                    else:
                        response_text = f"Validation error: {error_msg}. Please provide the correct data"
                        response_text += "Please provide the correct data in this format:\n"
                        response_text += "**key:value key2:value2**"
                    conversation.set_pending_action(pending)
                elif "error" in result:
                    error_msg = result.get("error", "Unknown error")
                    response_text = f"Request failed: {error_msg}"
                else:
                     droplet_info = DROPLET_REGISTRY.get(pending['droplet'])
                     droplet_name = droplet_info['name'] if droplet_info else pending['droplet']
                
                     response_text = f"✅ Successfully executed **{pending['endpoint']}** on **{droplet_name}**!\n\n"
                     response_text += f"**Data sent:**\n```json\n{json.dumps(extracted_data, indent=2)}\n```\n\n"
                
                     if isinstance(result, dict):
                       if 'trace_id' in result:
                        response_text += f"🔍 Trace ID: `{result['trace_id']}`"
                       if 'id' in result or 'item_id' in result:
                         item_id = result.get('id') or result.get('item_id')
                         response_text += f"📋 Created ID: `{item_id}`"
            
            conversation.add_message("assistant", response_text)
            
            return ChatResponse(
                response=response_text,
                session_id=session_id,
                trace_id=str(uuid.uuid4()),
                timestamp=datetime.utcnow().isoformat() + "Z"
            )
        
        # No pending action - reason about new intent
        reasoning_result = await reason_about_intent(request.message, conversation)
        
        # Handle reasoning errors
        if reasoning_result.action_type == "error":
            response_text = f"⚠️ {reasoning_result.reasoning}"
            conversation.add_message("assistant", response_text)
            
            return ChatResponse(
                response=response_text,
                session_id=session_id,
                trace_id=str(uuid.uuid4()),
                timestamp=datetime.utcnow().isoformat() + "Z"
            )
        
        # Handle clarification needed
        if reasoning_result.needs_clarification:
            clarification = reasoning_result.clarification_message or "Please provide more details."
            
            # Store pending query if exists
            if reasoning_result.queries:
                query = reasoning_result.queries[0]
                conversation.set_pending_action({
                    'droplet': query['droplet'],
                    'endpoint': query['endpoint'],
                    'method': query['method']
                })
            
            conversation.add_message("assistant", clarification)
            
            return ChatResponse(
                response=clarification,
                session_id=session_id,
                trace_id=str(uuid.uuid4()),
                timestamp=datetime.utcnow().isoformat() + "Z"
            )
        
        # Execute queries
        queries = reasoning_result.queries
        if not queries:
            response_text = "I understood your request but couldn't determine which action to take. Could you rephrase?"
            conversation.add_message("assistant", response_text)
            
            return ChatResponse(
                response=response_text,
                session_id=session_id,
                trace_id=str(uuid.uuid4()),
                timestamp=datetime.utcnow().isoformat() + "Z"
            )

        # --- ORIGINAL LOGIC: Direct orchestrator calls ---
        
        # Execute queries via orchestrator
        results = []
        for query in queries:
            droplet_id = query['droplet'].split('_')[1]
            endpoint = query['endpoint']
            method = query.get('method', 'GET')
            
            # Send request via orchestrator
            if method == 'POST':
                result = await orchestrator_client.send_via_orchestrator(
                    target_id=droplet_id,
                    action=f"/{endpoint}",
                    data=query.get('extracted_data', {})
                )
            else:  # GET
                result = await orchestrator_client.send_via_orchestrator(
                    target_id=droplet_id,
                    action=f"/{endpoint}",
                    data=None
                )
            
            results.append({
                'query': query,
                'result': result
            })
        
        # Format response based on results
        # response_text = format_combined_response(results, reasoning_result)
        combined_data = {}
        
        for query in queries:
            droplet_id = query['droplet'].split('_')[1]
            endpoint = query['endpoint']
            method = query.get('method', 'GET')
            droplet_key = query['droplet']
            
            try:
                # Send request via orchestrator
                if method == 'POST':
                    result = await orchestrator_client.send_via_orchestrator(
                        target_id=droplet_id,
                        action=f"/{endpoint}",
                        data=query.get('extracted_data', {})
                    )
                else:  # GET
                    result = await orchestrator_client.send_via_orchestrator(
                        target_id=droplet_id,
                        action=f"/{endpoint}",
                        data=None
                    )
                
                # Store result by droplet key
                combined_data[droplet_key] = result
                
            except Exception as e:
                log.error(f"Query failed for {droplet_key}: {str(e)}", exc_info=True)
                combined_data[droplet_key] = {
                    "error": str(e)
                }
        
        source = conversation.source.value if conversation.source else "chat"
        response_text = await format_combined_response(combined_data, source)
         
        conversation.add_message("assistant", response_text)
        
        # if not queries:
        #     response_text = "I understood your request but couldn't determine which action to take. Could you rephrase?"
        #     conversation.add_message("assistant", response_text)
            
        #     return ChatResponse(
        #         response=response_text,
        #         session_id=session_id,
        #         trace_id=str(uuid.uuid4()),
        #         timestamp=datetime.utcnow().isoformat() + "Z"
        #     )

        # # --- CORRECTED LOGIC FOR TASK CREATION ---
        
        # tasks_to_create = []
        # for query in queries:
        #     # Look up droplet capabilities from our registry info
        #     droplet_info = DROPLET_REGISTRY.get(query.get("droplet"), {})
        #     # Pick the first capability as the requirement, or default to 'any'
        #     capability = droplet_info.get("capabilities", ["any"])[0]

        #     task = TaskCreate(
        #         # From AI reasoning:
        #         task_type=query.get("endpoint", "generic_task"),
        #         required_capability=capability,
        #         payload=TaskPayload(**query.get('extracted_data', {})),
                
        #         # Add richer context:
        #         title=f"Chat Task: {query.get('endpoint')} on {query.get('droplet')}",
        #         description=f"Initiated from user message: '{request.message}'",
                
        #         # Use defaults from the model for these, can be customized later:
        #         priority=3,
        #         max_retries=3
        #     )
        #     tasks_to_create.append(orchestrator_client.create_task(task))

        # # Execute all task creation requests in parallel
        # results = await asyncio.gather(*tasks_to_create, return_exceptions=True)
        
        # created_tasks = []
        # failed_tasks = []
        
        # for i, result in enumerate(results):
        #     query = queries[i]
        #     title = f"{query.get('endpoint')} on {query.get('droplet')}"
        #     if isinstance(result, Exception) or not result:
        #         failed_tasks.append(title)
        #     else:
        #         task_id = result.get("task_id", "N/A")
        #         created_tasks.append(f"• **{title}** (ID: `{task_id}`)")

        # # Format a response based on the results
        # if created_tasks:
        #     response_text = "✅ I have successfully created the following tasks for you:\n"
        #     response_text += "\n".join(created_tasks)
        # else:
        #     response_text = "❌ Unfortunately, I was unable to create any tasks for your request."

        # if failed_tasks:
        #     response_text += "\n\n⚠️ The following tasks failed to be created:\n"
        #     response_text += "\n".join([f"• {title}" for title in failed_tasks])

        conversation.add_message("assistant", response_text)
        
        return ChatResponse(
            response=response_text,
            session_id=session_id,
            trace_id=str(uuid.uuid4()),
            timestamp=datetime.utcnow().isoformat() + "Z"
        )
        
    except Exception as e:
        log.error("chat_processing_error", error=str(e), exc_info=True)
        
        error_msg = "❌ An error occurred while processing your request. Please try again."
        conversation.add_message("assistant", error_msg)
        
        return ChatResponse(
            response=error_msg,
            session_id=session_id,
            trace_id=str(uuid.uuid4()),
            timestamp=datetime.utcnow().isoformat() + "Z"
        )



@router.post("/analyze", response_model=AnalyzeResponse)
async def analyze(request: AnalyzeRequest):
    """
    Text analysis endpoint (stateless).
    Per Spec - POST /analyze endpoint.
    NO JWT required, NO session persistence.
    """
    log.info("analyze_request_received", text_length=len(request.text))
    
    try:
        # Perform analysis
        analysis_result = await analyze_text(request.text)
        
        return AnalyzeResponse(
            analysis=analysis_result,
            timestamp=datetime.utcnow().isoformat() + "Z"
        )
        
    except Exception as e:
        log.error("analysis_error", error=str(e), exc_info=True)
        
        return AnalyzeResponse(
            analysis={
                "error": "Analysis failed",
                "details": str(e)
            },
            timestamp=datetime.utcnow().isoformat() + "Z"
        )