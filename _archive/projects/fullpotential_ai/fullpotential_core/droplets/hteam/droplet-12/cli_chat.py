"""
Terminal CLI for testing Chat Orchestrator functionality
Run this script to interactively test your chat API
"""

import httpx
import sys
from typing import Optional

# Default server URL
DEFAULT_URL = "http://127.0.0.1:8012"


class ChatCLI:
    """Interactive terminal chat client"""
    
    def __init__(self, base_url: str = DEFAULT_URL):
        self.base_url = base_url.rstrip('/')
        self.session_id: Optional[str] = None
        self.client = httpx.Client(timeout=30.0)
    
    def print_header(self):
        """Print welcome header"""
        print("\n" + "=" * 60)
        print("  Chat Orchestrator - Terminal CLI")
        print("=" * 60)
        print(f"Server: {self.base_url}")
        print("Type 'exit' or 'quit' to end the session")
        print("Type 'new' to start a new session")
        print("Type 'session' to see current session ID")
        print("-" * 60 + "\n")
    
    def print_response(self, response_data: dict):
        """Pretty print the response"""
        print("\n" + "-" * 60)
        print("RESPONSE:")
        print("-" * 60)
        
        if "response" in response_data:
            print(response_data["response"])
        
        if "session_id" in response_data:
            self.session_id = response_data["session_id"]
            print(f"\n[Session ID: {response_data['session_id'][:8]}...]")
        
        if "trace_id" in response_data:
            print(f"[Trace ID: {response_data['trace_id']}]")
        
        if "timestamp" in response_data:
            print(f"[Timestamp: {response_data['timestamp']}]")
        
        print("-" * 60 + "\n")
    
    def send_message(self, message: str) -> Optional[dict]:
        """Send a message to the chat API"""
        url = f"{self.base_url}/api/chat"
        
        payload = {
            "message": message
        }
        
        if self.session_id:
            payload["session_id"] = self.session_id
        
        try:
            response = self.client.post(url, json=payload)
            response.raise_for_status()
            return response.json()
        except httpx.HTTPStatusError as e:
            print(f"\n❌ HTTP Error {e.response.status_code}: {e.response.text}\n")
            return None
        except httpx.RequestError as e:
            print(f"\n❌ Connection Error: {str(e)}\n")
            print(f"Make sure the server is running at {self.base_url}")
            return None
        except Exception as e:
            print(f"\n❌ Error: {str(e)}\n")
            return None
    
    def check_server(self) -> bool:
        """Check if server is reachable"""
        try:
            response = self.client.get(f"{self.base_url}/health", timeout=5.0)
            return response.status_code == 200
        except:
            return False
    
    def run(self):
        """Run the interactive CLI"""
        self.print_header()
        
        # Check server connection
        print("Checking server connection...")
        if not self.check_server():
            print(f"❌ Cannot connect to server at {self.base_url}")
            print("Make sure the server is running:")
            print("  python -m app.main")
            print("\nOr specify a different URL:")
            print("  python cli_chat.py http://localhost:8012")
            return
        print("✅ Server is reachable\n")
        
        # Main loop
        while True:
            try:
                # Get user input
                user_input = input("You: ").strip()
                
                if not user_input:
                    continue
                
                # Handle special commands
                if user_input.lower() in ['exit', 'quit', 'q']:
                    print("\n👋 Goodbye!\n")
                    break
                
                if user_input.lower() == 'new':
                    self.session_id = None
                    print("\n🆕 New session started\n")
                    continue
                
                if user_input.lower() == 'session':
                    if self.session_id:
                        print(f"\n📋 Current Session ID: {self.session_id}\n")
                    else:
                        print("\n📋 No active session (will create one on first message)\n")
                    continue
                
                # Send message
                print("\n⏳ Processing...")
                response = self.send_message(user_input)
                
                if response:
                    self.print_response(response)
                else:
                    print("❌ Failed to get response from server\n")
            
            except KeyboardInterrupt:
                print("\n\n👋 Interrupted. Goodbye!\n")
                break
            except EOFError:
                print("\n\n👋 Goodbye!\n")
                break
            except Exception as e:
                print(f"\n❌ Unexpected error: {str(e)}\n")
        
        self.client.close()


def main():
    """Main entry point"""
    # Get URL from command line or use default
    base_url = DEFAULT_URL
    if len(sys.argv) > 1:
        base_url = sys.argv[1]
    
    cli = ChatCLI(base_url)
    cli.run()


if __name__ == "__main__":
    main()

