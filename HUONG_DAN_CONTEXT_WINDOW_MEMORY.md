# 🧠 HƯỚNG DẪN CHI TIẾT SỬA LỖI & BỔ SUNG CONTEXT WINDOW / CHAT MEMORY

> **Cập nhật:** Hướng dẫn sửa triệt để 2 lỗi khi bật Chat Memory:
> 1. `OpenAI 400 Error: Missing required parameter: 'messages[1].content[0].type'`
> 2. `AttributeError: 'list' object has no attribute 'lower'` khi fallback về Mock.

---

## 📌 1. NGUYÊN NHÂN GÂY NÊN LỖI

### 🔴 Lỗi 1: OpenAI API báo lỗi 400 (`Missing required parameter...`)
- **Nguyên nhân:** OpenAI Chat Completion API bắt buộc trường `content` trong các tin nhắn `messages` phải là **chuỗi văn bản (String)**.
- Khi ta lưu `history.append({"role": "assistant", "content": final_answer})`, nếu `final_answer` hoặc dữ liệu `observation` vô tình là kiểu dữ liệu `dict` hoặc `list`, OpenAI sẽ tưởng đó là mảng nội dung đa phương thức (Multimodal Array) và bắt buộc phải có thuộc tính `"type"`.

### 🔴 Lỗi 2: Fallback về Mock bị crash `AttributeError: 'list' object has no attribute 'lower'`
- **Nguyên nhân:** Trong `MockOfflineProvider.generate_with_tools`, hàm cũ xử lý `prompt_lower = prompt.lower()`. Khi `prompt` truyền vào là một mảng `list` lịch sử hội thoại, kiểu `list` không có phương thức `.lower()`.

---

## 🛠️ 2. VỊ TRÍ VÀ ĐOẠN CODE CẦN SỬA CHI TIẾT

---

### 📝 BƯỚC 1: SỬA FILE [`src/providers.py`](file:///d:/vinuni%20AI/lab3/K4A-Day03-2A202602976-NguyenNhuTai/src/providers.py)

#### 🔹 1.1. Sửa hàm `generate_with_tools` trong `MockOfflineProvider` (Khoảng dòng 37):
Thay thế hàm `generate_with_tools` của `MockOfflineProvider` bằng mã sau:

```python
    def generate_with_tools(self, prompt: Any, tools_schema: List[Dict[str, Any]], system_prompt: str = "") -> Dict[str, Any]:
        # Ép kiểu prompt về string an toàn nếu prompt là list
        if isinstance(prompt, list):
            prompt_str = " ".join([str(m.get("content", "")) for m in prompt if isinstance(m, dict)])
            prompt_lower = prompt_str.lower()
        else:
            prompt_lower = str(prompt).lower()
            
        # Mô phỏng nhận diện intent gọi Tool cho VinBus
        if "e01" in prompt_lower and ("đăng ký" in prompt_lower or "vé tháng" in prompt_lower):
            return {
                "type": "tool_call",
                "tool_name": "register_monthly_pass",
                "arguments": {"passenger_name": "Tài", "phone_number": "0327800152", "route_id": "E01", "pass_type": "Học sinh/Sinh viên", "start_month": "10/2026"},
                "thought": "Khách hàng muốn đăng ký vé tháng tuyến E01. Tôi sẽ gọi tool register_monthly_pass."
            }
        elif "e01" in prompt_lower or "lộ trình" in prompt_lower:
            return {
                "type": "tool_call",
                "tool_name": "bus_route_query",
                "arguments": {"route_id": "E01"},
                "thought": "Khách hàng yêu cầu tra cứu lộ trình xe bus E01. Tôi sẽ gọi tool bus_route_query."
            }
        else:
            return {
                "type": "text",
                "content": "Xin chào! Xe bus điện VinBus phục vụ hành khách từ 05:00 - 22:30 hàng ngày.",
                "thought": "Câu hỏi chung, trả lời trực tiếp."
            }
```

---

#### 🔹 1.2. Sửa hàm `generate_with_tools` trong `OpenAIProvider` (Khoảng dòng 159):
Thay thế toàn bộ đoạn xử lý `messages` trong `OpenAIProvider.generate_with_tools` bằng mã nguồn chuẩn ép kiểu string:

```python
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

            # XÂY DỰNG MESSAGES CHUẨN ÉP KIỂU STRING ĐỂ TRÁNH LỖI 400 OPENAI
            messages = []
            if system_prompt:
                messages.append({"role": "system", "content": str(system_prompt)})
                
            if isinstance(prompt, list):
                for msg in prompt:
                    if isinstance(msg, dict):
                        role = msg.get("role", "user")
                        content = msg.get("content", "")
                        # Ép kiểu content về string nếu không phải string
                        if not isinstance(content, str):
                            content = json.dumps(content, ensure_ascii=False)
                        messages.append({"role": role, "content": content})
            else:
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

### 📝 BƯỚC 2: SỬA FILE [`src/app.py`](file:///d:/vinuni%20AI/lab3/K4A-Day03-2A202602976-NguyenNhuTai/src/app.py)

Cập nhật `run_react_agent` và khối `if "--interactive" in sys.argv:`:

```python
def run_react_agent(user_query: str, provider, mcp_server: MCPAcademicServer, history: list = None) -> tuple:
    if history is None:
        history = []
        
    current_history = list(history)
    current_history.append({"role": "user", "content": user_query})
    
    print(f"\n🤖 [REACT AGENT] Câu hỏi: {user_query}")
    
    step = 0
    trace_logs = []
    tools_list = mcp_server.list_tools()
    
    while step < MAX_ITERATIONS:
        step += 1
        step_start_time = time.time()
        print(f"\n--- 🔄 Vòng lặp ReAct Loop (Step {step}/{MAX_ITERATIONS}) ---")
        
        llm_response = provider.generate_with_tools(current_history, tools_list, system_prompt=REACT_AGENT_SYSTEM_PROMPT)
        latency_ms = round((time.time() - step_start_time) * 1000, 2)
        
        thought = llm_response.get("thought", "Đang suy luận...")
        print(f"🧠 [Thought]: {thought}")
        
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
            
        elif llm_response.get("type") == "tool_call":
            tool_name = llm_response.get("tool_name")
            arguments = llm_response.get("arguments", {})
            
            print(f"🛠️ [Action Proposed]: {tool_name}({arguments})")
            
            mcp_result = mcp_server.call_tool(tool_name, arguments)
            obs_data = mcp_result.get("result", {})
            
            if not obs_data:
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
```

Và ở phần `__main__` trong `src/app.py`:
```python
    if "--interactive" in sys.argv:
        print("🎮 [INTERACTIVE CHAT] Trò chuyện với Trợ lý VinBus (Đã bật Chat Memory):")
        session_history = []
        while True:
            try:
                user_input = input("\n👤 Khách hàng: ").strip()
                if not user_input or user_input.lower() in ["exit", "quit"]:
                    break
                logs, session_history = run_react_agent(user_input, provider, mcp_server, history=session_history)
                save_waterfall_trace(logs)
            except (KeyboardInterrupt, EOFError):
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
```

---

## 🧪 3. CHẠY THỬ VÀ KIỂM TRA

Mở terminal chạy lại:
```powershell
.venv\Scripts\python.exe src/app.py --interactive
```
👉 Bạn sẽ thấy Agent ghi nhớ chính xác ngữ cảnh đăng ký vé tháng tuyến E01 từ các tin nhắn trước mà không còn bị lỗi 400 hay AttributeError nữa!
