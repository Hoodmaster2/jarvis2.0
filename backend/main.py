"""
JARVIS Backend - Main entry point
FastAPI server that connects Ollama, agents, memory, skills, and voice.
"""
import argparse
import uvicorn
from api.server import create_app

def main():
    parser = argparse.ArgumentParser(description="JARVIS Backend Server")
    parser.add_argument("--host", type=str, default="127.0.0.1", help="Host address")
    parser.add_argument("--port", type=int, default=8765, help="Port number")
    parser.add_argument("--config", type=str, default=None, help="Config file path")
    parser.add_argument("--log-level", type=str, default="info", help="Log level")
    args = parser.parse_args()

    app = create_app(config_path=args.config)
    uvicorn.run(app, host=args.host, port=args.port, log_level=args.log_level)

if __name__ == "__main__":
    main()
