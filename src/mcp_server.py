"""
🔌 MODEL CONTEXT PROTOCOL (MCP) SERVER MODULE - VINBUS CUSTOMER SERVICE
Mô phỏng kiến trúc MCP Server (Client-Server Architecture) cung cấp công cụ chuẩn hóa.
"""

import json
import sys
from typing import Dict, Any, List
from tools import TOOLS_SCHEMA, dispatch_tool_call

if sys.stdout.encoding != 'utf-8':
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass

class MCPAcademicServer:
    """
    Giả lập MCP Server tuân thủ chuẩn giao thức Model Context Protocol cho VinBus
    """
    def __init__(self, server_name: str = "vinbus-customer-service-mcp-server"):
        self.server_name = server_name
        self.version = "2026.1.0"
        
    def list_tools(self) -> List[Dict[str, Any]]:
        """Trả về danh sách các Tools chuẩn giao thức MCP"""
        return TOOLS_SCHEMA
        
    def call_tool(self, tool_name: str, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """
        [TASK 2.1] HỌC VIÊN HOÀN THIỆN HÀM THỰC THI TOOL TRÊN MCP SERVER
        Thực thi request gọi Tool theo chuẩn MCP JSON-RPC 2.0
        """
        # 1. Gọi hàm dispatch_tool_call để lấy JSON string kết quả từ Tool Router
        raw_result_str = dispatch_tool_call(tool_name, arguments)
        
        # 2. Chuyển đổi JSON string thành Python Dictionary
        try:
            content = json.loads(raw_result_str)
        except Exception:
            content = {"raw_output": raw_result_str}
            
        # 3. Đóng gói phản hồi theo tiêu chuẩn giao thức MCP JSON-RPC 2.0
        return {
            "jsonrpc": "2.0",
            "server": self.server_name,
            "tool": tool_name,
            "result": content
        }


if __name__ == "__main__":
    print("==========================================================")
    print("🔌 KIỂM THỬ ĐỘC LẬP MCP SERVER (vinbus-customer-service-mcp-server)")
    print("==========================================================")
    
    server = MCPAcademicServer()
    tools = server.list_tools()
    print(f"✅ Khởi tạo thành công MCP Server: {server.server_name} (Version: {server.version})")
    print(f"📦 Số lượng Tools công bố: {len(tools)}")
    
    # Kiểm tra thử nghiệm gọi tool
    test_result = server.call_tool("bus_route_query", {"route_id": "E01"})
    print(f"✅ Phản hồi JSON-RPC từ MCP Server:")
    print(json.dumps(test_result, ensure_ascii=False, indent=2))