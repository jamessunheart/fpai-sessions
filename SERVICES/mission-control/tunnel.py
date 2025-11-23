from pyngrok import ngrok
import time
import sys

def start_tunnel():
    try:
        # Establish connectivity
        public_url = ngrok.connect(8080).public_url
        print(f"ngrok tunnel \"{public_url}\" -> \"http://127.0.0.1:8080\"")
        
        # Keep alive
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("Shutting down tunnel...")
        sys.exit(0)
    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    start_tunnel()

