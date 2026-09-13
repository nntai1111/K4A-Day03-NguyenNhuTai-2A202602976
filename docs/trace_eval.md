# 📊 BÁO CÁO THU HOẠCH NGHIỆM THU BÀI LAB 3 (BƯỚC 3 — SUBMISSION ARTIFACT)

> **Họ và Tên Học viên:** Nguyễn Như Tài 
> **Mã Sinh Viên / Mã Học viên:** 2A202602976
> **Chủ đề Lựa chọn:** Trợ lý Dịch vụ Khách hàng VinBus: Tra cứu lộ trình tuyến xe bus điện và đăng ký vé tháng.
  

---

## 1. BẢNG CHẤM ĐIỂM AGENTIC FIT SCORING MATRIX (ĐÁNH GIÁ CHỦ ĐỀ)

| Tiêu chí Đánh giá | Mức độ (1 - 5) | Giải trình chi tiết lý do chọn điểm |
| :--- | :---: | :--- |
| **1. Multi-step Reasoning** | 4/ 5 | Bài toán có yêu cầu chia nhỏ nhiều bước suy luận nối tiếp nhau không? Cần suy luận 2 bước khi khách tìm điểm đi/đến ➔ xác định mã tuyến (E01/E02) ➔ tiến hành đăng ký vé tháng. |
| **2. Tool Interaction** | 5/ 5 | Hệ thống có cần kết nối với MCP Server / Cơ sở dữ liệu bên ngoài không? Bắt buộc kết nối CSDL thực tế qua MCP Server để lấy lộ trình chuẩn và ghi nhận thông tin đăng ký vé tháng. |
| **3. Dynamic Decision** | 4/ 5 | Bước tiếp theo có phụ thuộc vào kết quả quan sát bước trước không? Phụ thuộc vào kết quả quan sát (ví dụ nếu tuyến xe không tồn tại sẽ gợi ý tuyến khác thay vì đăng ký). |
| **4. Long Horizon Goal** | 4/ 5 | Hệ thống có phải giữ mục tiêu xuyên suốt qua nhiều lượt xử lý không? Giữ mục tiêu hoàn tất thủ tục đăng ký vé tháng cho khách hàng qua nhiều lượt hỏi đáp. |
| **TỔNG ĐIỂM AGENTIC FIT** | **17/ 20** | *Tổng điểm 17/20 (>12/20): Bài toán VinBus vô cùng phù hợp triển khai Agentic System.*|

---

## 2. TRÍCH XUẤT KẾT QUẢ WATERFALL TRACE LOG (SAU KHI CHẠY TEST SUITE TRÊN API THẬT)

> ⚠️ **YÊU CẦU NGHIỆM THU:** Mở tệp `.env` điền `GEMINI_API_KEY` (hoặc `OPENAI_API_KEY`) để kết nối LLM thật trước khi thực thi `python src/app.py --all`. Bài nộp chỉ dùng Mock Offline Provider sẽ không đạt điểm nghiệm thực tế.

Dán 1 đoạn trích xuất log tiêu biểu từ file `docs/trace_waterfall.json` sinh ra từ phản hồi LLM API thật:

```json
[
  {
    "step": 1,
    "action_type": "TOOL_EXECUTION",
    "tool_name": "bus_route_query",
    "arguments": {
      "route_id": "E01"
    },
    "observation": {
      "status": "SUCCESS",
      "route_id": "E01",
      "data": {
        "route_name": "Tuyến E01: Bến xe Mỹ Đình - Vinhomes Ocean Park",
        "operating_hours": "05:00 - 22:30 hàng ngày"
      }
    },
    "latency_ms": 115.2
  }
]
```

---

## 3. TỔNG KẾT KẾT QUẢ NGHIỆM THU & NỘP BÀI

- [x] Đã điền API Key thật trong `.env` và xác nhận Agent chạy mượt mà trên LLM API thật (Gemini/OpenAI).
- **Tổng số Test Cases đã chạy thành công:** _5_ / 5 test cases.
- **Số lượt gọi Tool qua MCP Server chính xác:** _4_ lượt.
- **Kết quả đẩy Repo nộp bài:** [x] Đã Commit và Push mã nguồn thành công lên GitHub cá nhân.

---

> ✅ **HOÀN TẤT NỘP BÀI:** Sao chép đường link GitHub Repository cá nhân của bạn và dán vào ô nộp bài trên hệ thống LMS VLearn để hoàn tất Bài Lab 3!
