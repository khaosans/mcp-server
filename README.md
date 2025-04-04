# MCP Server

A FastAPI-based server providing WebSocket communication, file management, and tools endpoints.

## 🚀 Features

- 📁 File Management API
- 🔌 WebSocket Communication
- 🛠️ Tools Endpoint
- 📄 Static File Serving
- ✅ Comprehensive Test Suite

## 🛠️ Installation

1. Clone the repository:
```bash
git clone https://github.com/khaosans/mcp-server.git
cd mcp-server
```

2. Create and activate a virtual environment:
```bash
python -m venv venv
source venv/bin/activate  # On Windows: .\venv\Scripts\activate
```

3. Install dependencies:
```bash
pip install -r requirements.txt
```

## 🏃‍♂️ Running the Server

Start the server with:
```bash
uvicorn server:app --reload --host 0.0.0.0 --port 8080
```

## 🧪 Running Tests

Run the test suite with:
```bash
python test_server.py
```

## 📡 API Endpoints

### HTTP Endpoints

- `GET /files?q=<query>`: Search files in the public directory
- `GET /files/{filename}`: Read a specific file
- `POST /tools`: Execute tools (currently supports summarization)
- `GET /public/*`: Serve static files

### WebSocket Endpoint

- `ws://localhost:8080/ws`: WebSocket endpoint for real-time communication

## 📝 License

MIT License

## 👤 Author

[khaosans](https://github.com/khaosans)