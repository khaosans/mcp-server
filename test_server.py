import asyncio
import websockets
import requests
import json
from typing import Dict, Any
import sys

class ServerTester:
    def __init__(self):
        self.base_url = "http://localhost:8080"
        self.ws_url = "ws://localhost:8080/ws"
        self.results: Dict[str, bool] = {}

    def print_result(self, test_name: str, success: bool, message: str = ""):
        self.results[test_name] = success
        status = "✅ PASS" if success else "❌ FAIL"
        print(f"{status} - {test_name}")
        if message:
            print(f"   Message: {message}")

    async def test_files_endpoint(self):
        """Test the /files endpoint"""
        try:
            response = requests.get(f"{self.base_url}/files")
            response.raise_for_status()
            data = response.json()
            self.print_result("Files Endpoint", True, f"Found {len(data.get('matches', []))} files")
        except Exception as e:
            self.print_result("Files Endpoint", False, str(e))

    async def test_tools_endpoint(self):
        """Test the /tools endpoint"""
        try:
            test_data = {
                "task": "summarize",
                "text": "This is a test message that should be summarized by the tools endpoint."
            }
            response = requests.post(
                f"{self.base_url}/tools",
                json=test_data
            )
            response.raise_for_status()
            data = response.json()
            self.print_result("Tools Endpoint", True, f"Response: {data}")
        except Exception as e:
            self.print_result("Tools Endpoint", False, str(e))

    async def test_websocket(self):
        """Test the WebSocket connection"""
        try:
            async with websockets.connect(self.ws_url) as websocket:
                test_message = "Hello WebSocket!"
                await websocket.send(test_message)
                response = await websocket.recv()
                self.print_result("WebSocket", True, f"Echo response: {response}")
                # Gracefully close the connection
                await websocket.close(code=1000, reason="Test completed")
        except Exception as e:
            if "code = 1000" in str(e):
                self.print_result("WebSocket", True, "Connection closed normally")
            else:
                self.print_result("WebSocket", False, str(e))

    async def test_static_file(self):
        """Test static file serving"""
        try:
            response = requests.get(f"{self.base_url}/public/test.txt")
            response.raise_for_status()
            content = response.text
            self.print_result("Static File", True, f"Content: {content}")
        except Exception as e:
            self.print_result("Static File", False, str(e))

    def print_summary(self):
        """Print test summary"""
        print("\n📊 Test Summary:")
        print("=" * 50)
        total = len(self.results)
        passed = sum(1 for v in self.results.values() if v)
        failed = total - passed
        print(f"Total Tests: {total}")
        print(f"✅ Passed: {passed}")
        print(f"❌ Failed: {failed}")
        print("=" * 50)

async def main():
    print("🚀 Starting Server Tests...")
    print("=" * 50)
    
    tester = ServerTester()
    
    # Run all tests
    await tester.test_files_endpoint()
    await tester.test_tools_endpoint()
    await tester.test_websocket()
    await tester.test_static_file()
    
    # Print summary
    tester.print_summary()
    
    # Exit with appropriate status code
    sys.exit(0 if all(tester.results.values()) else 1)

if __name__ == "__main__":
    asyncio.run(main()) 