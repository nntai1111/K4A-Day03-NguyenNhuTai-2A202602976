"""
🚀 CORE AGENT APPLICATION (DAY 03: VINBUS REACT AGENT WITH CHAT MEMORY)
Thực thi so sánh giữa Chatbot Baseline và ReAct Agent kết nối MCP Server cho VinBus.
Hỗ trợ Conversation History / Context Window cho phiên tương tác đa lượt.
"""

import json
import os
import sys
import time
from dotenv import load_dotenv

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

if sys.stdout.encoding != 'utf-8':
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass

from mcp_server import MCPAcademicServer
from prompts import (
    CHATBOT_BASELINE_PROMPT,
    REACT_AGENT_SYSTEM_PROMPT,
    MAX_ITERATIONS
)
from providers import get_llm_provider

load_dotenv()

def load_test_cases():
    """Tải danh sách 5 test cases từ config/test_cases.json"""
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    config_path = os.path.join(base_dir, "config", "test_cases.json")
    if not os.path.exists(config_path):
        config_path = os.path.join(base_dir, "config", "test_cases.example.json")
    with open(config_path, "r", encoding="utf-8") as f:
        return json.load(f)


def save_waterfall_trace(trace_data: list):
    """Ghi vết log Waterfall Trace Log ra file docs/trace_waterfall.json"""
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    docs_dir = os.path.join(base_dir, "docs")
    os.makedirs(docs_dir, exist_ok=True)
    trace_path = os.path.join(docs_dir, "trace_waterfall.json")
    with open(trace_path, "w", encoding="utf-8") as f:
        json.dump(trace_data, f, ensure_ascii=False, indent=2)
    print(f"📊 [OBSERVABILITY]: Đã lưu {len(trace_data)} sự kiện Waterfall Trace tại '{trace_path}'!")


def run_baseline_chatbot(user_query: str, provider):
    """Chạy Chatbot gốc (Cấp 2) không có công cụ gọi Tool"""
    print(f"\n💬 [CHATBOT BASELINE] Câu hỏi: {user_query}")
    response = provider.generate(user_query, system_prompt=CHATBOT_BASELINE_PROMPT)
    print(f"🤖 Chatbot phản hồi:\n{response}")


def run_react_agent(user_query: str, provider, mcp_server: MCPAcademicServer, history: list = None) -> tuple:
    """
    [REACT AGENT LOOP] Thực thi vòng lặp Thought -> Action -> Observation với MCP Server & Chat Memory
    Trả về (trace_logs, updated_history)
    """
    if history is None:
        history = []
        
    current_history = list(history)
    current_history.append({"role": "user", "content": str(user_query)})
    
    print(f"\n🤖 [REACT AGENT] Câu hỏi: {user_query}")
    
    step = 0
    trace_logs = []
    tools_list = mcp_server.list_tools()
    
    while step < MAX_ITERATIONS:
        step += 1
        step_start_time = time.time()
        print(f"\n--- 🔄 Vòng lặp ReAct Loop (Step {step}/{MAX_ITERATIONS}) ---")
        
        # Truyền lịch sử hội thoại cho LLM Provider
        llm_response = provider.generate_with_tools(current_history, tools_list, system_prompt=REACT_AGENT_SYSTEM_PROMPT)
        latency_ms = round((time.time() - step_start_time) * 1000, 2)
        
        thought = llm_response.get("thought", "Đang suy luận...")
        print(f"🧠 [Thought]: {thought}")
        
        # LLM trả về văn bản trực tiếp
        if llm_response.get("type") == "text":
            final_content = llm_response.get("content", "")
            print(f"🏁 [Final Answer]: {final_content}")
            current_history.append({"role": "assistant", "content": str(final_content)})
            trace_logs.append({
                "step": step,
                "query": user_query,
                "action_type": "FINAL_ANSWER",
                "thought": thought,
                "output": final_content,
                "latency_ms": latency_ms
            })
            break
            
        # LLM đề xuất gọi Tool (Action)
        elif llm_response.get("type") == "tool_call":
            tool_name = llm_response.get("tool_name")
            arguments = llm_response.get("arguments", {})
            
            print(f"🛠️ [Action Proposed]: {tool_name}({arguments})")
            
            # Thực thi qua MCP Server
            mcp_result = mcp_server.call_tool(tool_name, arguments)
            obs_data = mcp_result.get("result", {})
            
            if not obs_data:
                print(f"👁️ [Observation từ MCP Server]: {{}}")
                final_answer = "Chưa thể xử lý yêu cầu do MCP Server không trả về dữ liệu."
            else:
                obs_str = json.dumps(obs_data, ensure_ascii=False)
                print(f"👁️ [Observation từ MCP Server]: {obs_str}")
                
                # Tổng hợp câu trả lời cho VinBus
                if obs_data.get("status") == "SUCCESS":
                    if "data" in obs_data:
                        d = obs_data["data"]
                        if isinstance(d, list):
                            routes_list_str = "\n".join([f"- **{r['route_id']}**: {r['route_name']} ({r['departure']} ➡️ {r['destination']}) - {r['operating_hours']}" for r in d])
                            final_answer = f"Danh sách các tuyến xe bus điện VinBus hiện có:\n{routes_list_str}"
                        elif isinstance(d, dict):
                            stops_str = ", ".join(d.get("stops", []))
                            final_answer = (
                                f"Thông tin {d.get('route_name', '')}:\n"
                                f"- Điểm đầu/cuối: {d.get('departure', '')} ➡️ {d.get('destination', '')}\n"
                                f"- Giờ hoạt động: {d.get('operating_hours', '')} | Tần suất: {d.get('frequency', '')}\n"
                                f"- Giá vé: Lượt {d.get('ticket_price_single', '')} | Tháng: {d.get('ticket_price_monthly', '')}\n"
                                f"- Các điểm dừng chính: {stops_str}."
                            )
                        else:
                            final_answer = f"Xử lý thành công: {json.dumps(obs_data, ensure_ascii=False)}"
                    elif "message" in obs_data:
                        final_answer = obs_data["message"]
                    else:
                        final_answer = f"Xử lý thành công: {json.dumps(obs_data, ensure_ascii=False)}"
                elif obs_data.get("status") == "NOT_FOUND":
                    final_answer = obs_data.get("message", "Không tìm thấy thông tin tuyến xe yêu cầu.")
                else:
                    final_answer = f"Phản hồi từ công cụ VinBus: {json.dumps(obs_data, ensure_ascii=False)}"
            
            current_history.append({"role": "assistant", "content": str(final_answer)})
            trace_logs.append({
                "step": step,
                "query": user_query,
                "action_type": "TOOL_EXECUTION",
                "tool_name": tool_name,
                "arguments": arguments,
                "observation": obs_data,
                "latency_ms": latency_ms
            })
            
            print(f"🧠 [Thought]: Đã nhận dữ liệu từ MCP Server VinBus. Tổng hợp kết quả phản hồi khách hàng.")
            print(f"🏁 [Final Answer]: {final_answer}")
            
            trace_logs.append({
                "step": step + 1,
                "query": user_query,
                "action_type": "FINAL_ANSWER",
                "thought": "Tổng hợp thông tin dịch vụ VinBus thành công.",
                "output": final_answer,
                "latency_ms": 10.0
            })
            break

    return trace_logs, current_history


if __name__ == "__main__":
    print("==========================================================")
    print("🚌 VINBUS CUSTOMER SERVICE ASSISTANT - REACT AGENT DEMO")
    print("==========================================================")
    
    provider = get_llm_provider()
    mcp_server = MCPAcademicServer()
    
    print(f"🔌 LLM Provider: {provider.__class__.__name__}")
    print(f"🌐 MCP Server: {mcp_server.server_name}\n")
    
    tests = load_test_cases()
    print(f"✅ Đã tải thành công {len(tests)} Test Cases.\n")
    
    if "--interactive" in sys.argv:
        print("🎮 [INTERACTIVE CHAT] Trò chuyện với Trợ lý VinBus (Đã bật Chat Memory):")
        print("💡 Gợi ý câu hỏi:")
        print("   - Tra cứu: 'Hãy tra cứu lộ trình tuyến xe bus VinBus E01'")
        print("   - Đăng ký: 'Đăng ký vé tháng tuyến E01 cho Nguyễn Văn A, SĐT 0912345678, đối tượng Học sinh/Sinh viên'")
        print("   - Gõ 'exit' để thoát.\n")
        session_history = []
        while True:
            try:
                user_input = input("\n👤 Khách hàng: ").strip()
                if not user_input or user_input.lower() in ["exit", "quit"]:
                    print("👋 Tạm biệt!")
                    break
                logs, session_history = run_react_agent(user_input, provider, mcp_server, history=session_history)
                save_waterfall_trace(logs)
            except (KeyboardInterrupt, EOFError):
                print("\n👋 Đã thoát phiên tương tác.")
                break
    elif "--all" in sys.argv:
        print("🚀 [TEST SUITE MODE] Chạy thử 5 Test Cases nghiệm thu:")
        all_traces = []
        for tc in tests:
            print(f"\n==================================================")
            print(f"🧪 [{tc['id']}] Loại test: {tc['type']}")
            logs, _ = run_react_agent(tc["question"], provider, mcp_server)
            all_traces.extend(logs)
        if all_traces:
            save_waterfall_trace(all_traces)
    else:
        sample_query = tests[1]["question"]
        print(f"--- 🏁 DEMO CHẠY THỬ TC02 ---")
        logs, _ = run_react_agent(sample_query, provider, mcp_server)
        save_waterfall_trace(logs)