from fastapi import FastAPI, WebSocket, Request, HTTPException, WebSocketDisconnect
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, JSONResponse
from pathlib import Path
from fastapi.middleware.cors import CORSMiddleware
from web3 import Web3
from morpho_constants import (
    BASE_RPC_URL,
    MORPHO_LENS_ADDRESS,
    MORPHO_FACTORY_ADDRESS,
    MORPHO_LENS_ABI,
    MORPHO_FACTORY_ABI,
    MARKETS
)
import os
import logging
import traceback
from typing import Dict, Any
import requests
import time
from dotenv import load_dotenv
import json
import asyncio

# Load environment variables
load_dotenv('.env.local')

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger("mcp_server")

app = FastAPI()
BASE = Path(__file__).parent.resolve()

# Global variables for Web3 and contracts
w3 = None
morpho_lens = None
morpho_factory = None

# Add Basescan API configuration
BASESCAN_API_KEY = os.getenv("BASESCAN_API_KEY", "")  # Get from .env
BASESCAN_API_URL = "https://api.basescan.org/api"

# Initialize Web3 for Base chain
try:
    w3 = Web3(Web3.HTTPProvider(BASE_RPC_URL))
    if not w3.is_connected():
        logger.error(f"Failed to connect to Base RPC: {BASE_RPC_URL}")
    else:
        logger.info(f"Connected to Base chain. Current block: {w3.eth.block_number}")
        
    # Initialize Morpho Lens contract
    try:
        # Convert address to checksum format
        lens_address = w3.to_checksum_address(MORPHO_LENS_ADDRESS)
        morpho_lens = w3.eth.contract(address=lens_address, abi=MORPHO_LENS_ABI)
        logger.info(f"Initialized Morpho Lens contract at {lens_address}")
    except Exception as e:
        logger.error(f"Error initializing Morpho Lens contract: {str(e)}")
        morpho_lens = None
        
    # Initialize Morpho Factory contract
    try:
        # Convert address to checksum format
        factory_address = w3.to_checksum_address(MORPHO_FACTORY_ADDRESS)
        morpho_factory = w3.eth.contract(address=factory_address, abi=MORPHO_FACTORY_ABI)
        logger.info(f"Initialized Morpho Factory contract at {factory_address}")
    except Exception as e:
        logger.error(f"Error initializing Morpho Factory contract: {str(e)}")
        morpho_factory = None
except Exception as e:
    logger.error(f"Error initializing Web3: {str(e)}")
    logger.error(traceback.format_exc())
    # We'll initialize these as None and handle errors in the functions
    w3 = None
    morpho_lens = None
    morpho_factory = None

# CORS (for web/public agent access)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount public directory
app.mount("/public", StaticFiles(directory=BASE / "public"), name="public")

# File search
@app.get("/files")
def search_files(q: str = ""):
    base = BASE / "public"
    return {
        "matches": [str(p.relative_to(base)) for p in base.rglob("*") if q.lower() in p.name.lower()]
    }

# Read a file
@app.get("/files/{filename}")
def read_file(filename: str):
    file_path = BASE / "public" / filename
    if not file_path.exists():
        raise HTTPException(status_code=404, detail="File not found")
    return FileResponse(file_path)

def verify_contract_on_basescan(address: str) -> bool:
    """Verify if a contract exists and is verified on Basescan."""
    try:
        # First check if there's contract code at the address
        code = w3.eth.get_code(address)
        if not code:
            logger.error(f"No contract code found at address: {address}")
            return False
            
        logger.info(f"Contract code found at address: {address}")
            
        # Then check contract verification status on Basescan
        params = {
            "module": "contract",
            "action": "getabi",
            "address": address,
            "apikey": BASESCAN_API_KEY
        }
        
        logger.info(f"Checking contract verification on Basescan for address: {address}")
        response = requests.get(BASESCAN_API_URL, params=params)
        
        if response.status_code == 200:
            result = response.json()
            logger.info(f"Basescan API response: {result}")
            
            if result["status"] == "1" and result["message"] == "OK":
                logger.info(f"Contract verified on Basescan: {address}")
                return True
            else:
                logger.warning(f"Contract not verified on Basescan: {address}. Response: {result}")
                return False
        else:
            logger.error(f"Failed to get response from Basescan API. Status code: {response.status_code}")
            return False
            
    except Exception as e:
        logger.error(f"Error verifying contract on Basescan: {str(e)}")
        logger.error(f"Traceback: {traceback.format_exc()}")
        return False

async def summarize_text(text: str) -> Dict[str, Any]:
    """Summarize the given text"""
    # For now, just echo the text
    return {"summary": text}

async def get_morpho_position(wallet_address: str, pool_id: str) -> Dict[str, Any]:
    """Get Morpho position for a wallet in a specific pool"""
    try:
        # Validate addresses
        wallet_address = Web3.to_checksum_address(wallet_address)
        
        # Get market ID from pool_id
        market_id = MARKETS.get(pool_id)
        if not market_id:
            raise HTTPException(status_code=400, detail=f"Invalid pool_id: {pool_id}")
        
        # Log the attempt to fetch position
        logger.info(f"Fetching position for wallet {wallet_address} in pool {pool_id} (market_id: {market_id})")
        
        try:
            # Get position from Morpho Lens
            position = morpho_lens.functions.position(
                market_id,  # This is now a bytes32 market ID
                wallet_address
            ).call()
            
            return {
                "wallet": wallet_address,
                "pool_id": pool_id,
                "market_id": market_id,
                "supply_shares": str(position[0]),
                "borrow_shares": str(position[1]),
                "collateral": str(position[2]),
                "source": "on-chain"
            }
        except Exception as e:
            logger.warning(f"Failed to get position from chain: {str(e)}")
            logger.info("Using mock data for position")
            
            # Return mock data for testing
            return {
                "wallet": wallet_address,
                "pool_id": pool_id,
                "market_id": market_id,
                "supply_shares": "1000000000000000000",
                "borrow_shares": "0",
                "collateral": "500000000000000000",
                "source": "mock"
            }
            
    except ValueError as e:
        logger.error(f"Validation error: {str(e)}")
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Error getting Morpho position: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

# Tools endpoint
@app.post("/tools")
async def run_tool(request: Dict[str, Any]):
    """Run a specific tool based on the request"""
    try:
        task = request.get("task")
        if not task:
            raise HTTPException(status_code=400, detail="No task specified")

        if task == "summarize":
            text = request.get("text", "")
            return await summarize_text(text)
        elif task == "morpho_get_position":
            wallet = request.get("wallet")
            pool_id = request.get("pool_id")
            if not wallet or not pool_id:
                raise HTTPException(status_code=400, detail="Missing wallet or pool_id")
            return await get_morpho_position(wallet, pool_id)
        else:
            raise HTTPException(status_code=400, detail=f"Unknown task: {task}")
    except Exception as e:
        logger.error(f"Error running tool: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# WebSocket echo (agent interface)
@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    """WebSocket endpoint for real-time communication"""
    await websocket.accept()
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
    finally:
        await websocket.close()

@app.get("/")
async def root():
    """Health check endpoint"""
    return JSONResponse({"status": "ok", "message": "Server is running"})