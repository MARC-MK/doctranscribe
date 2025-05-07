#!/usr/bin/env python
"""
Run the DocTranscribe backend server with enhanced PDF processing capabilities.
This server supports both the primary database-backed mode and a fallback simple mode.
"""
import os
import sys
import socket
import logging
import argparse
import uvicorn

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler("backend.log")
    ]
)

logger = logging.getLogger(__name__)

def is_port_in_use(port, host='0.0.0.0'):
    """Check if a port is in use."""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        return s.connect_ex((host, port)) == 0

def find_available_port(start_port, max_attempts=10):
    """Find an available port starting from start_port."""
    port = start_port
    attempts = 0
    
    while attempts < max_attempts:
        if not is_port_in_use(port):
            return port
        port += 1
        attempts += 1
    
    raise RuntimeError(f"Could not find an available port after {max_attempts} attempts")

def main():
    """Main entry point for the backend server."""
    # Parse command line arguments
    parser = argparse.ArgumentParser(description="Run the DocTranscribe backend server")
    parser.add_argument("--port", type=int, default=int(os.environ.get("PORT", 8080)),
                        help="Port to run the server on (default: 8080)")
    parser.add_argument("--host", type=str, default=os.environ.get("HOST", "0.0.0.0"),
                        help="Host to bind the server to (default: 0.0.0.0)")
    parser.add_argument("--reload", action="store_true", default=os.environ.get("RELOAD", "true").lower() == "true",
                        help="Enable auto-reload for development")
    parser.add_argument("--debug", action="store_true", default=os.environ.get("DEBUG", "false").lower() == "true",
                        help="Enable debug mode")
    parser.add_argument("--mode", choices=["full", "simple"], default="full",
                        help="Server mode: 'full' (with DB) or 'simple' (file-only)")
    
    args = parser.parse_args()
    
    # Check if the port is available, if not find another
    if is_port_in_use(args.port, args.host):
        logger.warning(f"Port {args.port} is already in use.")
        try:
            args.port = find_available_port(args.port + 1)
            logger.info(f"Using alternative port: {args.port}")
        except RuntimeError as e:
            logger.error(str(e))
            return 1
    
    # Print server configuration
    logger.info(f"Starting DocTranscribe backend on {args.host}:{args.port}")
    logger.info(f"Auto reload: {args.reload}, Debug mode: {args.debug}, Mode: {args.mode}")
    
    # Check OpenAI API key
    openai_key = os.environ.get("OPENAI_API_KEY", "")
    if not openai_key:
        logger.warning(
            "No OpenAI API key found in environment variables. "
            "The service will use mock data for handwriting extraction."
        )
    else:
        # Mask the key in logs
        masked_key = f"{openai_key[:4]}...{openai_key[-4:]}" if len(openai_key) > 8 else "****"
        logger.info(f"Using OpenAI API key: {masked_key}")
    
    # Choose which module to run based on mode
    app_module = "simple_pdf_server:app" if args.mode == "simple" else "app.main:app"
    
    # Start server with auto-reload during development
    try:
        uvicorn.run(
            app_module,
            host=args.host,
            port=args.port,
            reload=args.reload,
            log_level="debug" if args.debug else "info"
        )
        return 0
    except Exception as e:
        logger.error(f"Error starting server: {str(e)}")
        return 1

if __name__ == "__main__":
    sys.exit(main()) 