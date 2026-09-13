"""
🚀 FASTAPI BACKEND SERVER FOR VINBUS REACT AGENT CHATBOT
Cung cấp REST API & Static Web Server cho Giao diện Trò chuyện VinBus ReAct Agent.
"""

import os
import sys
import json
from typing import List, Dict, Any, Optional
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, JSONResponse
from pydantic import BaseModel
from dotenv import load_dotenv

# Ensure src path is in sys.path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from mcp_server import MCPAcademicServer
from providers import get_llm_provider
from app import run_react_agent, load_test_cases, save_waterfall_trace

load_dotenv()

app = FastAPI(
    title="VinBus Customer Service ReAct Agent API",
    version="2026.1.0",
    description="API Gateway cho VinBus ReAct AI Agent với MCP Server integration"
)

# Enable CORS for local dev flexibilty
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Global instances
mcp_server = MCPAcademicServer()
provider = get_llm_provider()

class ChatRequest(BaseModel):
    query: str
    history: Optional[List[Dict[str, Any]]] = []

class ChatResponse(BaseModel):
    final_answer: str
    logs: List[Dict[str, Any]]
    history: List[Dict[str, Any]]

@app.get("/api/info")
def get_info():
    """Trả về thông tin cấu hình hệ thống & Test Cases"""
    tests = []
    try:
        tests = load_test_cases()
    except Exception:
        pass
    
    return {
        "provider": provider.__class__.__name__,
        "model": getattr(provider, "model_name", "Unknown"),
        "mcp_server": mcp_server.server_name,
        "tools_count": len(mcp_server.list_tools()),
        "tools": mcp_server.list_tools(),
        "test_cases": tests
    }

@app.post("/api/chat", response_model=ChatResponse)
def chat_endpoint(req: ChatRequest):
    """Xử lý hội thoại từ Web UI với ReAct Agent & MCP Server"""
    if not req.query or not req.query.strip():
        raise HTTPException(status_code=400, detail="Câu hỏi không được để trống.")
    
    try:
        trace_logs, updated_history = run_react_agent(
            user_query=req.query.strip(),
            provider=provider,
            mcp_server=mcp_server,
            history=req.history
        )
        
        # Save to trace file for observability
        save_waterfall_trace(trace_logs)
        
        # Extract final answer
        final_ans = "Đã xử lý xong."
        if updated_history and updated_history[-1].get("role") == "assistant":
            final_ans = updated_history[-1].get("content", "")
            
        return {
            "final_answer": final_ans,
            "logs": trace_logs,
            "history": updated_history
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Lỗi hệ thống: {str(e)}")

@app.get("/api/trace")
def get_trace_log():
    """Lấy log trace Waterfall mới nhất từ docs/trace_waterfall.json"""
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    trace_path = os.path.join(base_dir, "docs", "trace_waterfall.json")
    if os.path.exists(trace_path):
        try:
            with open(trace_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            return data
        except Exception as e:
            return {"error": str(e)}
    return []

# Mount static web UI directory
web_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "web")
os.makedirs(web_dir, exist_ok=True)
app.mount("/static", StaticFiles(directory=web_dir), name="static")

@app.get("/")
def read_root():
    """Serve index.html at root URL"""
    index_file = os.path.join(web_dir, "index.html")
    if os.path.exists(index_file):
        return FileResponse(index_file)
    return {"message": "Web UI index.html not found"}

if __name__ == "__main__":
    import uvicorn
    print("🚀 Đang khởi chạy VinBus ReAct Agent Web API tại http://localhost:8000 ...")
    uvicorn.run("server:app", host="0.0.0.0", port=8000, reload=True)
