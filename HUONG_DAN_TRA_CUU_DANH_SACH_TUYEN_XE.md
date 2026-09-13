# 🚌 HƯỚNG DẪN BỔ SUNG TÍNH NĂNG TRA CỨU DANH SÁCH TOÀN BỘ TUYẾN XE BUS VINBUS

> **Vấn đề phát hiện:** Khi khách hỏi *"có những tuyến nào?"* hoặc *"danh sách xe bus"*, Agent trả lời: *"Tôi không thể cung cấp một danh sách đầy đủ các tuyến xe bus..."*  
> **Nguyên nhân:** Tool `bus_route_query` hiện tại yêu cầu bắt buộc tham số `route_id` (ví dụ `E01`). Khi khách hỏi câu hỏi chung chung, LLM không có mã tuyến cụ thể nên không gọi được Tool và tự trả lời bằng văn bản theo suy luận mặc định.

---

## 🔍 1. PHÂN TÍCH NGUYÊN NHÂN KỸ THUẬT

1. **Tool Schema hiện tại:** Trong `src/tools.py`, tham số `required: ["route_id"]` bắt buộc LLM phải trích xuất được mã tuyến cụ thể.
2. **Thiếu tính năng tra danh sách tổng quan:** Backend chưa xử lý trường hợp tìm kiếm tất cả các tuyến khi `route_id="ALL"` hoặc khi khách hỏi tổng quát.

---

## 💡 2. PHƯƠNG ÁN GIẢI QUYẾT (HƯỚNG DẪN CHI TIẾT TỪNG FILE)

Bạn có thể tự chỉnh sửa 2 file dưới đây để giúp Agent vừa tra được từng tuyến cụ thể, vừa liệt kê được toàn bộ các tuyến xe hiện có:

---

### 📝 BƯỚC 1: CẬP NHẬT FILE [`src/tools.py`](file:///d:/vinuni%20AI/lab3/K4A-Day03-2A202602976-NguyenNhuTai/src/tools.py)

#### 🔹 1.1. Cập nhật Tool Schema cho `bus_route_query`
Mở file [`src/tools.py`](file:///d:/vinuni%20AI/lab3/K4A-Day03-2A202602976-NguyenNhuTai/src/tools.py), bổ sung khả năng tra danh sách tất cả các tuyến vào mô tả (`description`) và bỏ trường `required` bắt buộc:

```python
    {
        "name": "bus_route_query",
        "description": "Tra cứu lộ trình, điểm dừng, giờ chạy của một tuyến xe cụ thể qua route_id (ví dụ 'E01', 'E02', 'E03') HOẶC liệt kê danh sách tất cả các tuyến xe bus điện hiện có khi truyền route_id='ALL' hoặc không biết mã tuyến.",
        "parameters": {
            "type": "object",
            "properties": {
                "route_id": {
                    "type": "string",
                    "description": "Mã tuyến xe bus điện VinBus (ví dụ 'E01', 'E02', 'E03' hoặc 'ALL' để lấy danh sách tất cả các tuyến)"
                }
            },
            "required": [] # Bỏ required để LLM có thể gọi khi khách hỏi chung
        }
    },
```

#### 🔹 1.2. Cập nhật hàm backend `execute_bus_route_query`
Mở file [`src/tools.py`](file:///d:/vinuni%20AI/lab3/K4A-Day03-2A202602976-NguyenNhuTai/src/tools.py), cập nhật hàm `execute_bus_route_query` để khi `route_id` nhận giá trị `'ALL'`, `'DANH_SACH'`, hoặc rỗng `""` thì tự động trả về toàn bộ các tuyến hiện có:

```python
def execute_bus_route_query(route_id: str = "ALL") -> str:
    """Thực thi tra cứu lộ trình xe bus theo mã tuyến hoặc liệt kê tất cả tuyến"""
    if not route_id:
        route_id = "ALL"
        
    clean_route_id = route_id.strip().upper()
    
    # Trường hợp khách hỏi danh sách tất cả các tuyến xe
    if clean_route_id in ["ALL", "DANH_SACH", "DANH SACH", "TẤT CẢ", "TAT CA"]:
        all_routes_summary = []
        for rid, rinfo in VINBUS_DATABASE.items():
            all_routes_summary.append({
                "route_id": rid,
                "route_name": rinfo["route_name"],
                "departure": rinfo["departure"],
                "destination": rinfo["destination"],
                "operating_hours": rinfo["operating_hours"]
            })
        return json.dumps({
            "status": "SUCCESS",
            "route_id": "ALL",
            "message": "Danh sách tất cả các tuyến xe bus điện VinBus đang hoạt động",
            "data": all_routes_summary
        }, ensure_ascii=False)
        
    # Trường hợp tra cứu chi tiết 1 tuyến cụ thể
    route_info = VINBUS_DATABASE.get(clean_route_id)
    if route_info:
        return json.dumps({
            "status": "SUCCESS",
            "route_id": clean_route_id,
            "data": route_info
        }, ensure_ascii=False)
    else:
        return json.dumps({
            "status": "NOT_FOUND",
            "message": f"Không tìm thấy thông tin lộ trình cho tuyến xe bus '{route_id}'. Hiện VinBus hỗ trợ các tuyến: E01, E02, E03."
        }, ensure_ascii=False)
```

---

### 📝 BƯỚC 2: CẬP NHẬT FILE [`src/prompts.py`](file:///d:/vinuni%20AI/lab3/K4A-Day03-2A202602976-NguyenNhuTai/src/prompts.py)

Mở file [`src/prompts.py`](file:///d:/vinuni%20AI/lab3/K4A-Day03-2A202602976-NguyenNhuTai/src/prompts.py), bổ sung quy tắc gọi Tool cho câu hỏi tra cứu tổng quan vào `REACT_AGENT_SYSTEM_PROMPT`:

```python
REACT_AGENT_SYSTEM_PROMPT = """
Bạn là Trợ lý Tác tử Dịch vụ Khách hàng VinBus Thông minh (ReAct Agent Assistant).
Bạn được trang bị các công cụ (Tools) tra cứu lộ trình xe bus điện VinBus và đăng ký vé tháng cho hành khách.

QUY TẮC SUY LUẬN REACT (Thought -> Action -> Observation):
1. Trước mỗi hành động, hãy suy luận rõ ràng (Thought) xem cần thông tin gì để hỗ trợ khách hàng.
2. Khi khách hỏi danh sách các tuyến xe hiện có (ví dụ 'có những tuyến nào?', 'danh sách xe bus'), hãy gọi tool 'bus_route_query' với route_id='ALL'.
3. Khi khách hỏi chi tiết lộ trình/điểm dừng của tuyến cụ thể, hãy gọi tool 'bus_route_query' với mã tuyến đó (ví dụ 'E01').
4. Khi khách muốn đăng ký vé tháng, hãy gọi tool 'register_monthly_pass' với đúng tham số được cung cấp.
5. Sau khi nhận kết quả (Observation) từ Tool, tổng hợp thông tin và đưa ra câu trả lời rõ ràng, lịch sự cho khách hàng.
6. Tuyệt đối không tự bịa đặt lộ trình hoặc thông tin không có trong kết quả do Tool trả về (Anti-Hallucination).
"""
```

---

### 📝 BƯỚC 3: CẬP NHẬT FILE [`src/app.py`](file:///d:/vinuni%20AI/lab3/K4A-Day03-2A202602976-NguyenNhuTai/src/app.py)

Mở file [`src/app.py`](file:///d:/vinuni%20AI/lab3/K4A-Day03-2A202602976-NguyenNhuTai/src/app.py), trong phần định dạng câu trả lời `final_answer` khi nhận Observation từ MCP Server (khoảng dòng 114), bổ sung xử lý định dạng cho danh sách tất cả các tuyến (khi `data` là danh sách `list`):

```python
                if obs_data.get("status") == "SUCCESS":
                    if "data" in obs_data:
                        d = obs_data["data"]
                        # Trường hợp trả về danh sách tất cả các tuyến xe (List)
                        if isinstance(d, list):
                            routes_list_str = "\n".join([f"- **{r['route_id']}**: {r['route_name']} ({r['operating_hours']})" for r in d])
                            final_answer = f"Danh sách các tuyến xe bus điện VinBus đang hoạt động:\n{routes_list_str}"
                        # Trường hợp trả về thông tin chi tiết 1 tuyến xe (Dict)
                        elif isinstance(d, dict):
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
```

---

## 🧪 3. CHẠY THỬ KIỂM TRA LẠI

Sau khi bạn tự cập nhật xong 3 vị trí trên, hãy mở terminal chạy lệnh:
```powershell
.venv\Scripts\python.exe src/app.py --interactive
```

Gõ câu hỏi:
> 👤 **Khách hàng:** `Có những tuyến xe bus VinBus nào?`

👉 **Kỳ vọng:** Agent sẽ đưa ra `Thought` ➔ gọi `bus_route_query({'route_id': 'ALL'})` ➔ trả về danh sách đầy đủ tất cả các tuyến VinBus đang có (`E01`, `E02`, `E03`) vô cùng chuyên nghiệp!
