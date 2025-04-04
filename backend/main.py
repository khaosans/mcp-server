from fastapi import FastAPI, WebSocket, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import JSONResponse, StreamingResponse
import logging
import os
from web3 import Web3
from dotenv import load_dotenv
import requests
import json
from typing import Dict, Any, Optional
import asyncio
from pathlib import Path
from .morpho_constants import (
    BASE_RPC_URL,
    MORPHO_LENS_ADDRESS,
    MORPHO_FACTORY_ADDRESS,
    MORPHO_LENS_ABI,
    MORPHO_FACTORY_ABI,
    MARKETS,
    MOCK_POSITIONS
)

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize FastAPI app
app = FastAPI()

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize Web3 and contracts
try:
    w3 = Web3(Web3.HTTPProvider(BASE_RPC_URL))
    if not w3.is_connected():
        raise Exception("Failed to connect to Base network")
    logger.info("Successfully connected to Base network")
    
    # Initialize Morpho Lens contract
    morpho_lens = w3.eth.contract(
        address=Web3.to_checksum_address(MORPHO_LENS_ADDRESS),
        abi=MORPHO_LENS_ABI
    )
    logger.info(f"Initialized Morpho Lens contract at {MORPHO_LENS_ADDRESS}")
    
    # Initialize Morpho Factory contract
    morpho_factory = w3.eth.contract(
        address=Web3.to_checksum_address(MORPHO_FACTORY_ADDRESS),
        abi=MORPHO_FACTORY_ABI
    )
    logger.info(f"Initialized Morpho Factory contract at {MORPHO_FACTORY_ADDRESS}")
except Exception as e:
    logger.error(f"Failed to initialize Web3: {e}")
    raise

# Get the absolute path to the public directory
PUBLIC_DIR = Path(__file__).parent.parent / "public"
if not PUBLIC_DIR.exists():
    PUBLIC_DIR.mkdir(parents=True)

# Mount static files
app.mount("/public", StaticFiles(directory=str(PUBLIC_DIR)), name="public")

@app.get("/")
async def root():
    """Health check endpoint"""
    return {"status": "ok", "message": "Server is running"}

@app.get("/files")
async def list_files():
    """List available files in the public directory"""
    files = []
    for file in PUBLIC_DIR.glob("**/*"):
        if file.is_file():
            files.append(str(file.relative_to(PUBLIC_DIR)))
    return {"files": files}

@app.get("/tools")
async def list_tools():
    """List available tools and their descriptions"""
    return {
        "tools": [
            {
                "id": "summarize",
                "name": "Text Summarizer",
                "description": "Summarizes the given text",
                "parameters": {
                    "text": {
                        "type": "string",
                        "description": "Text to summarize"
                    }
                }
            },
            {
                "id": "morpho_get_position",
                "name": "Morpho Position Checker",
                "description": "Gets the position of a wallet in a specific Morpho pool",
                "parameters": {
                    "wallet": {
                        "type": "string",
                        "description": "Ethereum wallet address"
                    },
                    "pool_id": {
                        "type": "string",
                        "description": "Pool identifier (e.g., 'cbETH/USDC')",
                        "enum": ["cbBTC/USDC", "cbETH/USDC", "wstETH/USDC", "USDbC/USDC"]
                    }
                }
            }
        ]
    }

async def stream_tool_response(request: Dict[str, Any]):
    """Stream tool responses as SSE events"""
    try:
        task = request.get("task")
        if not task:
            yield "data: " + json.dumps({"error": "No task specified"}) + "\n\n"
            return

        if task == "summarize":
            text = request.get("text", "")
            yield "data: " + json.dumps(await summarize_text(text)) + "\n\n"
        elif task == "morpho_get_position":
            wallet = request.get("wallet")
            pool_id = request.get("pool_id")
            if not wallet or not pool_id:
                yield "data: " + json.dumps({"error": "Missing wallet or pool_id"}) + "\n\n"
                return
            yield "data: " + json.dumps(await get_morpho_position(wallet, pool_id)) + "\n\n"
        else:
            yield "data: " + json.dumps({"error": f"Unknown task: {task}"}) + "\n\n"
    except Exception as e:
        logger.error(f"Error running tool: {e}")
        yield "data: " + json.dumps({"error": str(e)}) + "\n\n"

@app.post("/tools")
async def run_tool(request: Request):
    """Run a specific tool based on the request"""
    try:
        body = await request.json()
        return StreamingResponse(
            stream_tool_response(body),
            media_type="text/event-stream"
        )
    except Exception as e:
        logger.error(f"Error processing request: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    """WebSocket endpoint for real-time communication"""
    await websocket.accept()
    connection_open = True
    try:
        while True:
            data = await websocket.receive_text()
            try:
                message = json.loads(data)
                # Echo back the message for now
                await websocket.send_json({"status": "received", "message": message})
            except json.JSONDecodeError:
                await websocket.send_json({"status": "error", "message": "Invalid JSON"})
    except Exception as e:
        logger.error(f"WebSocket error: {e}")
        if connection_open:
            await websocket.close()
            connection_open = False

async def summarize_text(text: str) -> Dict[str, Any]:
    """Summarize the given text"""
    # For now, just echo the text
    return {"summary": text}

async def get_morpho_position(wallet: str, pool_id: str) -> Dict[str, Any]:
    """Get Morpho position for a wallet in a specific pool"""
    try:
        # Validate addresses
        wallet_address = Web3.to_checksum_address(wallet)
        market_id = MARKETS.get(pool_id)
        
        if not market_id:
            raise ValueError(f"Invalid pool_id: {pool_id}")
            
        logger.info(f"Fetching position for wallet {wallet_address} in pool {pool_id} (market ID: {market_id})")
        
        try:
            # Get position from Morpho Lens using market ID
            position = morpho_lens.functions.position(market_id, wallet_address).call()
            
            return {
                "wallet": wallet_address,
                "pool_id": pool_id,
                "market_id": market_id,
                "position": {
                    "supply": str(position[0]),
                    "borrow": str(position[1]),
                    "collateral": str(position[2])
                },
                "source": "chain"
            }
        except Exception as e:
            logger.warning(f"Failed to get on-chain position, falling back to mock data: {str(e)}")
            
            # Fall back to mock data
            mock_data = MOCK_POSITIONS.get(wallet_address, {}).get(pool_id)
            if mock_data:
                logger.info("Using mock data for position")
                return {
                    "wallet": wallet_address,
                    "pool_id": pool_id,
                    "market_id": market_id,
                    **mock_data,
                    "source": "mock"
                }
            else:
                # If no mock data, return empty position
                logger.info("No mock data found, returning empty position")
                return {
                    "wallet": wallet_address,
                    "pool_id": pool_id,
                    "market_id": market_id,
                    "supply_shares": "0",
                    "borrow_shares": "0",
                    "collateral": "0",
                    "source": "empty"
                }
            
    except ValueError as e:
        logger.error(f"Error getting Morpho position: {str(e)}")
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Unexpected error getting Morpho position: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8080) 