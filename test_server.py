import asyncio
import websockets
import requests
import json
from typing import Dict, Any, Optional
import sys
import logging
from datetime import datetime
import sseclient

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
            data = response.json()
            if data.get("status") == "ok":
                self.print_result("Server Health", True, "Server is up and responding")
            else:
                self.print_result("Server Health", False, "Server returned unexpected status")
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
            
            files = data.get('files', [])
            if not isinstance(files, list):
                raise ValueError("'files' is not a list")
            
            self.print_result("Files Endpoint", True, 
                            f"Found {len(files)} files, response structure valid")
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
                    json=task,
                    stream=True,
                    headers={'Accept': 'text/event-stream'}
                )
                
                # Log response details
                logger.info(f"Response status: {response.status_code}")
                logger.info(f"Response headers: {dict(response.headers)}")
                
                if response.status_code == 200:
                    client = sseclient.SSEClient(response)
                    for event in client.events():
                        try:
                            data = json.loads(event.data)
                            if "error" in data:
                                raise ValueError(f"Tool returned error: {data['error']}")
                            self.print_result(f"Tools Endpoint - {task['task']}", True, 
                                           f"Received valid response: {json.dumps(data, indent=2)}")
                            break
                        except json.JSONDecodeError:
                            raise ValueError("Invalid JSON in SSE response")
                else:
                    raise ValueError(f"Unexpected status code: {response.status_code}")
                    
            except Exception as e:
                self.print_result(f"Tools Endpoint - {task['task']}", False, str(e))

    async def test_websocket(self):
        """Test WebSocket connection and message exchange"""
        try:
            async with websockets.connect(self.ws_url) as websocket:
                # Send a test message
                test_message = {"type": "test", "content": "Hello Server"}
                await websocket.send(json.dumps(test_message))
                
                # Wait for response
                response = await websocket.recv()
                response_data = json.loads(response)
                
                if response_data.get("status") == "received":
                    self.print_result("WebSocket", True, "Successfully exchanged messages")
                else:
                    self.print_result("WebSocket", False, "Unexpected response format")
        except Exception as e:
            self.print_result("WebSocket", False, str(e))

    async def test_static_file(self):
        """Test static file serving"""
        try:
            # First, create a test file if it doesn't exist
            test_file = "test.txt"
            test_content = "Hello from MCP Server"
            
            response = requests.get(f"{self.base_url}/public/{test_file}")
            response.raise_for_status()
            
            if response.text.strip() == test_content:
                self.print_result("Static File", True, "Successfully retrieved test file")
            else:
                self.print_result("Static File", False, "File content mismatch")
        except Exception as e:
            self.print_result("Static File", False, str(e))

    async def test_morpho_position_tool(self):
        """Test Morpho position tool with various scenarios"""
        test_cases = [
            {
                "name": "Valid wallet and pool",
                "wallet": self.wallet_address,
                "pool_id": self.pool_id,
                "should_succeed": True
            },
            {
                "name": "Invalid wallet address",
                "wallet": "0xinvalid",
                "pool_id": self.pool_id,
                "should_succeed": False
            },
            {
                "name": "Invalid pool ID",
                "wallet": self.wallet_address,
                "pool_id": "invalid/pool",
                "should_succeed": False
            }
        ]
        
        for test_case in test_cases:
            try:
                response = requests.post(
                    f"{self.base_url}/tools",
                    json={
                        "task": "morpho_get_position",
                        "wallet": test_case["wallet"],
                        "pool_id": test_case["pool_id"]
                    },
                    stream=True,
                    headers={'Accept': 'text/event-stream'}
                )
                
                if response.status_code == 200:
                    client = sseclient.SSEClient(response)
                    for event in client.events():
                        try:
                            data = json.loads(event.data)
                            if "error" in data:
                                if test_case["should_succeed"]:
                                    raise ValueError(f"Unexpected error: {data['error']}")
                                else:
                                    self.print_result(f"Morpho Position - {test_case['name']}", True,
                                                   f"Expected error received: {data['error']}")
                            else:
                                if test_case["should_succeed"]:
                                    self.print_result(f"Morpho Position - {test_case['name']}", True,
                                                   f"Successfully retrieved position: {json.dumps(data, indent=2)}")
                                else:
                                    raise ValueError("Unexpected success response")
                            break
                        except json.JSONDecodeError:
                            raise ValueError("Invalid JSON in SSE response")
                else:
                    raise ValueError(f"Unexpected status code: {response.status_code}")
                    
            except Exception as e:
                if test_case["should_succeed"]:
                    self.print_result(f"Morpho Position - {test_case['name']}", False, str(e))
                else:
                    self.print_result(f"Morpho Position - {test_case['name']}", True,
                                   f"Expected error: {str(e)}")

    def print_summary(self):
        """Print test summary with statistics"""
        total_tests = len(self.results)
        passed_tests = sum(1 for result in self.results.values() if result)
        failed_tests = total_tests - passed_tests
        success_rate = (passed_tests / total_tests) * 100 if total_tests > 0 else 0
        
        print("\n" + "="*50)
        print("📊 Test Summary")
        print("="*50)
        print(f"Total Tests: {total_tests}")
        print(f"✅ Passed: {passed_tests}")
        print(f"❌ Failed: {failed_tests}")
        print(f"Success Rate: {success_rate:.1f}%")
        print("="*50)
        
        if failed_tests > 0:
            print("\nFailed Tests:")
            for test_name, success in self.results.items():
                if not success:
                    print(f"❌ {test_name}")
        
        return success_rate == 100

async def main():
    """Main test runner"""
    tester = ServerTester()
    
    # Run all tests
    await tester.test_server_health()
    await tester.test_files_endpoint()
    await tester.test_tools_endpoint()
    await tester.test_websocket()
    await tester.test_static_file()
    await tester.test_morpho_position_tool()
    
    # Print summary
    success = tester.print_summary()
    
    # Exit with appropriate status code
    sys.exit(0 if success else 1)

if __name__ == "__main__":
    asyncio.run(main())