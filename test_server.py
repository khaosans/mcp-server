import asyncio
import websockets
import requests
import json
from typing import Dict, Any, Optional
import sys
import logging
from datetime import datetime

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class ServerTester:
    def __init__(self):
        self.base_url = "http://localhost:8080"
        self.ws_url = "ws://localhost:8080/ws"
        self.results: Dict[str, bool] = {}
        self.test_start_time = datetime.now()
        
        # Test wallet with known Morpho positions
        self.wallet_address = "0x2E2Ea30Ba045Df4bC38e80cF11E119E12e06C1C2"
        self.pool_id = "cbBTC/USDC"
        
        # Known valid market addresses
        self.valid_markets = {
            "cbBTC/USDC": "0x38f3D1F44Cbe64A033CA1A63889f9d6a6F2E8E37",
            "cbETH/USDC": "0x0d1Fe8eAdb0a3e44C4Cc9D73De8dA50C1E475832",
            "wstETH/USDC": "0x9D9EBCc8E7B4eF061C0F7Bab532d1710b874f789",
            "USDbC/USDC": "0x0B1A02A7309dFbfAD1Cd623dF63DD56e12F36f36"
        }

    def print_result(self, test_name: str, success: bool, message: str = ""):
        """Print test result with emoji and formatting"""
        self.results[test_name] = success
        status = "✅ PASS" if success else "❌ FAIL"
        duration = (datetime.now() - self.test_start_time).total_seconds()
        print(f"\n{status} - {test_name} ({duration:.2f}s)")
        if message:
            print(f"   Message: {message}")

    async def test_server_health(self):
        """Test basic server health and connectivity"""
        try:
            response = requests.get(self.base_url)
            response.raise_for_status()
            self.print_result("Server Health", True, "Server is up and responding")
        except Exception as e:
            self.print_result("Server Health", False, f"Server health check failed: {str(e)}")

    async def test_files_endpoint(self):
        """Test the /files endpoint with validation"""
        try:
            response = requests.get(f"{self.base_url}/files")
            response.raise_for_status()
            data = response.json()
            
            # Validate response structure
            if not isinstance(data, dict):
                raise ValueError("Response is not a dictionary")
            
            matches = data.get('matches', [])
            if not isinstance(matches, list):
                raise ValueError("'matches' is not a list")
            
            self.print_result("Files Endpoint", True, 
                            f"Found {len(matches)} files, response structure valid")
        except Exception as e:
            self.print_result("Files Endpoint", False, str(e))

    async def test_tools_endpoint(self):
        """Test the /tools endpoint with multiple tasks"""
        tasks = [
            {
                "task": "summarize",
                "text": "This is a test message that should be summarized."
            },
            {
                "task": "morpho_get_position",
                "wallet": self.wallet_address,
                "pool_id": self.pool_id
            }
        ]
        
        for task in tasks:
            try:
                logger.info(f"Testing tools endpoint with task: {task['task']}")
                response = requests.post(
                    f"{self.base_url}/tools",
                    json=task
                )
                
                # Log response details
                logger.info(f"Response status: {response.status_code}")
                logger.info(f"Response headers: {dict(response.headers)}")
                
                try:
                    response_content = response.json()
                    logger.info(f"Response content: {json.dumps(response_content, indent=2)}")
                except Exception as e:
                    logger.error(f"Could not parse response as JSON: {str(e)}")
                    logger.error(f"Raw response: {response.text}")
                
                if response.status_code == 200:
                    self.print_result(f"Tools Endpoint - {task['task']}", True, 
                                    f"Response: {json.dumps(response_content, indent=2)}")
                else:
                    error_detail = "Unknown error"
                    try:
                        error_response = response.json()
                        error_detail = error_response.get("detail", str(response.text))
                    except:
                        error_detail = str(response.text)
                    
                    self.print_result(f"Tools Endpoint - {task['task']}", False,
                                    f"HTTP error {response.status_code}: {error_detail}")
            except Exception as e:
                self.print_result(f"Tools Endpoint - {task['task']}", False, str(e))

    async def test_websocket(self):
        """Test WebSocket connection with multiple messages"""
        try:
            async with websockets.connect(self.ws_url) as websocket:
                # Test multiple messages
                messages = [
                    "Hello WebSocket!",
                    json.dumps({"type": "test", "data": "JSON message"}),
                    "Final message"
                ]
                
                for msg in messages:
                    await websocket.send(msg)
                    response = await websocket.recv()
                    logger.info(f"WebSocket message sent: {msg}")
                    logger.info(f"WebSocket response received: {response}")
                
                # Gracefully close
                await websocket.close(code=1000, reason="Test completed")
                self.print_result("WebSocket", True, "Successfully sent multiple messages")
        except Exception as e:
            if "code = 1000" in str(e):
                self.print_result("WebSocket", True, "Connection closed normally")
            else:
                self.print_result("WebSocket", False, str(e))

    async def test_static_file(self):
        """Test static file serving with validation"""
        try:
            response = requests.get(f"{self.base_url}/public/test.txt")
            response.raise_for_status()
            
            # Validate content type
            content_type = response.headers.get('content-type', '')
            if 'text/plain' not in content_type:
                raise ValueError(f"Unexpected content type: {content_type}")
            
            content = response.text
            if not content:
                raise ValueError("Empty file content")
            
            self.print_result("Static File", True, 
                            f"Content type: {content_type}, Content: {content}")
        except Exception as e:
            self.print_result("Static File", False, str(e))

    async def test_morpho_position_tool(self):
        """Test Morpho position tool with validation"""
        try:
            # Test with known valid market
            market_address = self.valid_markets.get(self.pool_id)
            if not market_address:
                raise ValueError(f"No valid market address found for pool {self.pool_id}")
            
            test_data = {
                "task": "morpho_get_position",
                "wallet": self.wallet_address,
                "pool_id": self.pool_id
            }
            
            logger.info(f"Testing Morpho Position Tool with data: {json.dumps(test_data, indent=2)}")
            logger.info(f"Using market address: {market_address}")
            
            response = requests.post(
                f"{self.base_url}/tools",
                json=test_data
            )
            
            # Log response details
            logger.info(f"Response status: {response.status_code}")
            logger.info(f"Response headers: {dict(response.headers)}")
            
            try:
                response_content = response.json()
                logger.info(f"Response content: {json.dumps(response_content, indent=2)}")
            except Exception as e:
                logger.error(f"Could not parse response as JSON: {str(e)}")
                logger.error(f"Raw response: {response.text}")
            
            if response.status_code == 200:
                data = response.json()
                required_fields = ["supply_shares", "borrow_shares", "collateral"]
                missing_fields = [field for field in required_fields if field not in data]
                
                if missing_fields:
                    self.print_result("Morpho Position Tool", False,
                                    f"Missing required fields: {missing_fields}")
                else:
                    self.print_result("Morpho Position Tool", True,
                                    f"Position data: {json.dumps(data, indent=2)}")
            else:
                error_detail = "Unknown error"
                try:
                    error_response = response.json()
                    error_detail = error_response.get("detail", str(response.text))
                except:
                    error_detail = str(response.text)
                
                self.print_result("Morpho Position Tool", False,
                                f"HTTP error {response.status_code}: {error_detail}")
        except Exception as e:
            self.print_result("Morpho Position Tool", False, str(e))
            import traceback
            logger.error(f"Traceback: {traceback.format_exc()}")

    def print_summary(self):
        """Print detailed test summary with statistics"""
        print("\n📊 Test Summary:")
        print("=" * 50)
        total = len(self.results)
        passed = sum(1 for v in self.results.values() if v)
        failed = total - passed
        duration = (datetime.now() - self.test_start_time).total_seconds()
        
        print(f"⏱️  Total Duration: {duration:.2f}s")
        print(f"📝 Total Tests: {total}")
        print(f"✅ Passed: {passed}")
        print(f"❌ Failed: {failed}")
        print(f"📈 Success Rate: {(passed/total)*100:.1f}%")
        
        if failed > 0:
            print("\n❌ Failed Tests:")
            for test_name, success in self.results.items():
                if not success:
                    print(f"   - {test_name}")
        
        print("=" * 50)

async def main():
    print("\n🚀 Starting Server Tests...")
    print("=" * 50)
    print(f"⏰ Start Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"🌐 Base URL: http://localhost:8080")
    print("=" * 50)
    
    tester = ServerTester()
    
    # Run all tests
    await tester.test_server_health()
    await tester.test_files_endpoint()
    await tester.test_tools_endpoint()
    await tester.test_websocket()
    await tester.test_static_file()
    await tester.test_morpho_position_tool()
    
    # Print summary
    tester.print_summary()
    
    # Exit with appropriate status code
    sys.exit(0 if all(tester.results.values()) else 1)

if __name__ == "__main__":
    asyncio.run(main())