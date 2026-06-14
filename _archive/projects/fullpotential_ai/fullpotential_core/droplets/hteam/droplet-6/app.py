"""
Main Chainlit application for Full Potential AI voice interface.

This is the core application that handles:
- Message routing
- Claude API integration
- Conversation context management
- Image/vision processing
"""

import chainlit as cl
from anthropic import Anthropic
import uuid
from datetime import datetime
from config import (
    ANTHROPIC_API_KEY,
    MODEL,
    MAX_TOKENS,
    SYSTEM_PROMPT,
)
from dashboard_client import send_transcript, send_response


# Initialize Anthropic client
client = Anthropic(api_key=ANTHROPIC_API_KEY)


@cl.on_chat_start
async def start():
    """
    Initialize the chat session when user connects.
    
    This runs once per session and sets up:
    - Welcome message
    - Conversation history storage
    - Initial system context
    - Voice input UI (Phase 2)
    - Session ID for Droplet 7 integration
    """
    # Generate unique session ID for Droplet 7 integration
    session_id = str(uuid.uuid4())
    cl.user_session.set("session_id", session_id)
    
    # Store conversation history in session
    cl.user_session.set("messages", [])
    
    # Add system message to establish AI personality
    system_message = {
        "role": "system",
        "content": SYSTEM_PROMPT
    }
    
    # Initialize with system message
    messages = cl.user_session.get("messages")
    messages.append(system_message)
    
    # Send welcome message
    await cl.Message(
        content="👋 Full Potential AI here. I'm listening. What's on your mind? 🎤 Click the microphone button to speak!",
        author="Full Potential AI"
    ).send()
    
    print(f"✅ Session started with ID: {session_id}")


@cl.on_message
async def main(message: cl.Message):
    """
    Handle incoming messages from the user.
    
    This is the core message handler that:
    1. Receives user input (text or voice transcript)
    2. Processes images if attached
    3. Sends to Claude API
    4. Returns response to user
    
    Args:
        message: Chainlit message object containing user input
    """
    # Get conversation history from session
    messages = cl.user_session.get("messages")
    
    # Handle images if attached (for Phase 4: Vision)
    import base64
    content_parts = []
    
    # Add text content
    if message.content:
        content_parts.append({"type": "text", "text": message.content})
    
    # Process images if attached
    if message.elements:  # If user uploaded images/files
        for element in message.elements:
            if hasattr(element, "path") and element.path:  # Image file
                try:
                    # Read image as base64
                    with open(element.path, "rb") as image_file:
                        image_data = base64.b64encode(image_file.read()).decode("utf-8")
                        
                        # Determine image type
                        image_type = "image/png"
                        if element.path.endswith(".jpg") or element.path.endswith(".jpeg"):
                            image_type = "image/jpeg"
                        elif element.path.endswith(".webp"):
                            image_type = "image/webp"
                        elif element.path.endswith(".gif"):
                            image_type = "image/gif"
                        
                        # Add image to content (Claude API format)
                        content_parts.append({
                            "type": "image",
                            "source": {
                                "type": "base64",
                                "media_type": image_type,
                                "data": image_data
                            }
                        })
                except Exception as e:
                    print(f"Error processing image: {e}")
    
    # Determine content format for Claude
    # If only text, use string. If images, use content array
    if len(content_parts) == 1 and content_parts[0]["type"] == "text":
        user_content = content_parts[0]["text"]
    else:
        user_content = content_parts
    
    # Get session ID for Droplet 7 integration
    session_id = cl.user_session.get("session_id")
    
    # Forward transcript to Droplet 7 dashboard (non-blocking)
    if message.content and session_id:
        print(f"[App] Forwarding transcript: '{message.content[:50]}...', session_id='{session_id}'")
        try:
            result = await send_transcript(
                transcript=message.content,
                session_id=session_id,
                timestamp=datetime.utcnow().isoformat()
            )
            print(f"[App] Transcript forwarding result: {result}")
        except Exception as e:
            # Don't block main flow if Droplet 7 forwarding fails
            print(f"[App] ⚠️ Failed to send transcript to Droplet 7: {e}")
            import traceback
            print(f"[App] Traceback: {traceback.format_exc()}")
    else:
        print(f"[App] ⚠️ Skipping transcript forwarding - content: {bool(message.content)}, session_id: {session_id}")
    
    # Add user message to history (store as text for simplicity)
    user_message = {
        "role": "user",
        "content": message.content or "[Image]"  # Store text representation
    }
    messages.append(user_message)
    
    # Prepare messages for Claude API
    # Claude expects messages in a specific format
    claude_messages = []
    
    # Convert our message format to Claude's format
    # Skip system message (handled separately)
    for msg in messages:
        if msg["role"] == "system":
            continue  # System messages are handled separately in Claude
        elif msg["role"] == "user":
            # For the current message, use the full content (may include images)
            # For older messages, use stored text
            if msg == user_message:
                claude_messages.append({
                    "role": "user",
                    "content": user_content
                })
            else:
                # For older messages, use text content
                claude_messages.append({
                    "role": "user",
                    "content": msg["content"]
                })
        elif msg["role"] == "assistant":
            claude_messages.append({
                "role": "assistant",
                "content": msg["content"]
            })
    
    try:
        # Call Claude API
        response = client.messages.create(
            model=MODEL,
            max_tokens=MAX_TOKENS,
            system=SYSTEM_PROMPT,  # System prompt for personality
            messages=claude_messages
        )
        
        # Extract response text
        assistant_response = response.content[0].text
        
        # Add assistant response to conversation history
        assistant_message = {
            "role": "assistant",
            "content": assistant_response
        }
        messages.append(assistant_message)
        
        # Update session with new history
        cl.user_session.set("messages", messages)
        
        # Forward response to Droplet 7 dashboard (non-blocking)
        if session_id:
            print(f"[App] Forwarding response: '{assistant_response[:50]}...', session_id='{session_id}'")
            try:
                result = await send_response(
                    response_text=assistant_response,
                    session_id=session_id,
                    timestamp=datetime.utcnow().isoformat()
                )
                print(f"[App] Response forwarding result: {result}")
            except Exception as e:
                # Don't block main flow if Droplet 7 forwarding fails
                print(f"[App] ⚠️ Failed to send response to Droplet 7: {e}")
                import traceback
                print(f"[App] Traceback: {traceback.format_exc()}")
        else:
            print(f"[App] ⚠️ Skipping response forwarding - session_id: {session_id}")
        
        # Send response to user
        await cl.Message(
            content=assistant_response,
            author="Full Potential AI"
        ).send()
        
    except Exception as e:
        # Handle errors gracefully
        error_message = f"⚠️ Error: {str(e)}"
        await cl.Message(
            content=error_message,
            author="System"
        ).send()
        
        # Log error for debugging
        print(f"Error in message handling: {e}")


@cl.on_stop
async def on_stop():
    """
    Handle when user stops the session.
    Currently just clears the session.
    """
    await cl.Message(
        content="Session ended. Conversation context cleared.",
        author="System"
    ).send()
