# 🧠 HƯỚNG DẪN BỔ SUNG KHẢ NĂNG GHI NHỚ HỘI THOẠI (CONTEXT WINDOW / CHAT MEMORY) CHO REACT AGENT

> **Vấn đề phát hiện:** Khi trò chuyện đa lượt (`--interactive`), Agent bị "mất trí nhớ" giữa các lượt hỏi (ví dụ: lượt 1 nói muốn đăng ký vé tháng E01, lượt 2 nhập tên/SĐT thì Agent không nhớ lượt 1 là đang đăng ký vé tháng tuyến nào).  
> **Nguyên nhân:** Agent chưa duy trì **Conversation History / Context Window (Bộ nhớ hội thoại)** mà chỉ gửi câu hỏi hiện tại sang LLM ở mỗi lượt.

---

## 🔍 1. BẢN CHẤT KỸ THUẬT: CONTEXT WINDOW VÀ CHAT MEMORY

### ❌ Cơ chế hiện tại (Single-turn / Stateless):
Ở mỗi lượt trò chuyện, hệ thống chỉ gửi:
```json
[
  {"role": "system", "content": "System Prompt VinBus..."},
  {"role": "user", "content": "Câu hỏi hiện tại (ví dụ: 'tài, 0327800152')"}
]
```
👉 LLM **không nhận được** các tin nhắn ở các lượt trước nên không có ngữ cảnh để gọi tool đúng!

---

### ✅ Cơ chế sau khi nâng cấp (Multi-turn Chat Memory):
Hệ thống duy trì mảng `chat_history` tích lũy tất cả các lượt hỏi - đáp - kết quả quan sát (Observation):
```json
[
  {"role": "system", "content": "System Prompt VinBus..."},
  {"role": "user", "content": "Tôi muốn đăng ký vé tháng tuyến E01"},
  {"role": "assistant", "content": "Vui lòng cung cấp Họ tên, SĐT, Đối tượng, Tháng..."},
  {"role": "user", "content": "Tài, 0327800152, sinh viên, 10/2026"}
]
```
👉 LLM nhìn thấy **toàn bộ cửa sổ ngữ cảnh (Context Window)**, tự động ghép `tuyến E01` từ tin nhắn trước với `Tài, 0327800152, sinh viên, 10/2026` ở tin nhắn sau để kích hoạt ngay `register_monthly_pass`!

---

## 🛠️ 2. CHI TIẾT CÁC BƯỚC NÂNG CẤP MÃ NGUỒN

### 📝 BƯỚC 1: CẬP NHẬT `src/providers.py` (Hỗ trợ nhận `chat_history`)

Mở file [`src/providers.py`](file:///d:/vinuni%20AI/lab3/K4A-Day03-2A202602976-NguyenNhuTai/src/providers.py) và cập nhật hàm `generate_with_tools` trong lớp `OpenAIProvider` để kiểm tra nếu `prompt` là danh sách tin nhắn lịch sử (`list`) thì sử dụng làm `messages`:

```python
# Sửa lại hàm generate_with_tools trong OpenAIProvider (khoảng dòng 159-211)

def generate_with_tools(self, prompt: Any, tools_schema: List[Dict[str, Any]], system_prompt: str = "") -> Dict[str, Any]:
    if not self.api_key or self.api_key == "your_openai_api_key_here":
        print("ℹ️ [OpenAI Provider]: Chưa tìm thấy OPENAI_API_KEY hợp lệ. Tự động chuyển sang Mock Offline.")
        return MockOfflineProvider().generate_with_tools(prompt, tools_schema, system_prompt)

    try:
        from openai import OpenAI
        client = OpenAI(api_key=self.api_key)

        tools = []
        for tool in tools_schema:
            if not tool.get("name"):
                continue
            tools.append({
                "type": "function",
                "function": {
                    "name": tool["name"],
                    "description": tool.get("description", ""),
                    "parameters": tool.get("parameters", {})
                }
            })

        # XÂY DỰNG DANH SÁCH MESSAGES HỖ TRỢ CHAT HISTORY
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
            
        if isinstance(prompt, list):
            # Nếu prompt đã là danh sách lịch sử hội thoại
            messages.extend(prompt)
        else:
            # Nếu prompt là chuỗi văn bản đơn lẻ
            messages.append({"role": "user", "content": str(prompt)})

        response = client.chat.completions.create(
            model=self.model_name,
            messages=messages,
            tools=tools if tools else None,
            tool_choice="auto" if tools else None
        )

        msg = response.choices[0].message
        if msg.tool_calls:
            call = msg.tool_calls[0]
            args = json.loads(call.function.arguments) if call.function.arguments else {}
            return {
                "type": "tool_call",
                "tool_name": call.function.name,
                "arguments": args,
                "thought": f"OpenAI quyết định gọi công cụ '{call.function.name}' với tham số: {json.dumps(args, ensure_ascii=False)}"
            }
        else:
            return {
                "type": "text",
                "content": msg.content or "",
                "thought": "OpenAI phản hồi trực tiếp bằng văn bản (không cần gọi công cụ)."
            }
    except Exception as e:
        print(f"⚠️ [OpenAI API Warning]: Không thể kết nối live API ({str(e)}). Tự động fallback về Mock.")
        return MockOfflineProvider().generate_with_tools(prompt, tools_schema, system_prompt)
```

---

### 📝 BƯỚC 2: CẬP NHẬT `src/app.py` (Lưu giữ `chat_history` qua các lượt đàm thoại)

Mở file [`src/app.py`](file:///d:/vinuni%20AI/lab3/K4A-Day03-2A202602976-NguyenNhuTai/src/app.py) và cập nhật hàm `run_react_agent` để hỗ trợ nhận tham số `history` và cập nhật lịch sử hội thoại:

```python
def run_react_agent(user_query: str, provider, mcp_server: MCPAcademicServer, history: list = None) -> tuple:
    """
    [REACT AGENT LOOP] Thực thi vòng lặp Thought -> Action -> Observation với MCP Server & Chat Memory
    Trả về (trace_logs, updated_history)
    """
    if history is None:
        history = []
        
    print(f"\n🤖 [REACT AGENT] Câu hỏi: {user_query}")
    
    # Thêm câu hỏi hiện tại của user vào lịch sử hội thoại
    history.append({"role": "user", "content": user_query})
    
    step = 0
    trace_logs = []
    tools_list = mcp_server.list_tools()
    
    while step < MAX_ITERATIONS:
        step += 1
        step_start_time = time.time()
        print(f"\n--- 🔄 Vòng lặp ReAct Loop (Step {step}/{MAX_ITERATIONS}) ---")
        
        # Truyền toàn bộ history sang LLM Provider
        llm_response = provider.generate_with_tools(history, tools_list, system_prompt=REACT_AGENT_SYSTEM_PROMPT)
        latency_ms = round((time.time() - step_start_time) * 1000, 2)
        
        thought = llm_response.get("thought", "Đang suy luận...")
        print(f"🧠 [Thought]: {thought}")
        
        # LLM trả lời văn bản trực tiếp
        if llm_response.get("type") == "text":
            final_content = llm_response.get("content", "")
            print(f"🏁 [Final Answer]: {final_content}")
            
            # Cập nhật phản hồi của Assistant vào lịch sử hội thoại
            history.append({"role": "assistant", "content": final_content})
            
            trace_logs.append({
                "step": step,
                "query": user_query,
                "action_type": "FINAL_ANSWER",
                "thought": thought,
                "output": final_content,
                "latency_ms": latency_ms
            })
            break
            
        # LLM đề xuất gọi Tool
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
                
                if obs_data.get("status") == "SUCCESS":
                    if "data" in obs_data:
                        d = obs_data["data"]
                        stops_str = ", ".join(d.get("stops", []))
                        final_answer = (
                            f"Thông tin {d.get('route_name', '')}:\n"
                            f"- Điểm đầu/cuối: {d.get('departure', '')} ➡️ {d.get('destination', '')}\n"
                            f"- Giờ hoạt động: {d.get('operating_hours', '')} | Tần suất: {d.get('frequency', '')}\n"
                            f"- Giá vé: Lượt {d.get('ticket_price_single', '')} | Tháng: {d.get('ticket_price_monthly', '')}\n"
                            f"- Các điểm dừng chính: {stops_str}."
                        )
                    elif "message" in obs_data:
                        final_answer = obs_data["message"]
                    else:
                        final_answer = f"Xử lý thành công: {json.dumps(obs_data, ensure_ascii=False)}"
                elif obs_data.get("status") == "NOT_FOUND":
                    final_answer = obs_data.get("message", "Không tìm thấy thông tin tuyến xe yêu cầu.")
                else:
                    final_answer = f"Phản hồi từ công cụ VinBus: {json.dumps(obs_data, ensure_ascii=False)}"
            
            # Cập nhật kết quả phản hồi vào lịch sử hội thoại
            history.append({"role": "assistant", "content": final_answer})
            
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

    return trace_logs, history
```

Và cập nhật chế độ `interactive` trong `src/app.py`:

```python
    if "--interactive" in sys.argv:
        print("🎮 [INTERACTIVE CHAT] Trò chuyện với Trợ lý VinBus (Đã bật Chat Memory):")
        session_history = []  # Lưu lịch sử hội thoại suốt phiên trò chuyện
        while True:
            try:
                user_input = input("\n👤 Khách hàng: ").strip()
                if not user_input or user_input.lower() in ["exit", "quit"]:
                    print("👋 Tạm biệt!")
                    break
                logs, session_history = run_react_agent(user_input, provider, mcp_server, history=session_history)
                save_waterfall_trace(logs)
            except (KeyboardInterrupt, EOFError):
                break
```

---

## 🧪 3. THỬ NGHIỆM LẠI KỊCH BẢN KHI CÓ CHAT MEMORY

Khởi động lại CLI Chat:
```powershell
.venv\Scripts\python.exe src/app.py --interactive
```

**Kịch bản hội thoại mẫu:**
1. **Lượt 1:**
   - 👤 **Khách hàng:** `Tôi muốn đăng ký vé tháng tuyến E01`
   - 🤖 **Agent:** `Để đăng ký vé tháng cho tuyến E01, vui lòng cho biết Họ tên, SĐT, Đối tượng, Tháng...`
2. **Lượt 2:**
   - 👤 **Khách hàng:** `Tài, 0327800152, sinh viên, 10/2026`
   - 🤖 **Agent:** *(Tự động kết hợp E01 ở Lượt 1 với thông tin ở Lượt 2)* ➔ Kích hoạt Tool `register_monthly_pass({'passenger_name': 'Tài', 'phone_number': '0327800152', 'route_id': 'E01', 'pass_type': 'Học sinh/Sinh viên', 'start_month': '10/2026'})` ➔ **Thành công 100%!**
