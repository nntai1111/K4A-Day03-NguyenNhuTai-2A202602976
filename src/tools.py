"""
🛠️ TOOL DEFINITIONS & EXECUTION BACKEND - VINBUS CUSTOMER SERVICE ASSISTANT
Mã nguồn chứa danh sách Tool Schemas (JSON Schema) và Execution Layer cho VinBus.
"""

import json
from typing import Dict, Any

# ==============================================================================
# 1. KHAI BÁO TOOL SCHEMAS CHUẨN NATIVE JSON SCHEMA (TASK 1.2)
# ==============================================================================

TOOLS_SCHEMA = [
    # Tool 1: Tra cứu lộ trình tuyến xe bus điện VinBus hoặc danh sách toàn bộ các tuyến
    {
        "name": "bus_route_query",
        "description": "Tra cứu lộ trình, điểm dừng, giờ chạy của một tuyến xe cụ thể qua route_id (ví dụ 'E01', 'E02', 'E03') HOẶC liệt kê danh sách tất cả các tuyến xe bus điện VinBus hiện có khi truyền route_id='ALL' hoặc không biết mã tuyến.",
        "parameters": {
            "type": "object",
            "properties": {
                "route_id": {
                    "type": "string",
                    "description": "Mã tuyến xe bus điện VinBus (ví dụ 'E01', 'E02', 'E03' hoặc 'ALL' để lấy danh sách tất cả các tuyến)"
                }
            },
            "required": []
        }
    },
    
    # Tool 2: Đăng ký vé tháng xe bus điện VinBus
    {
        "name": "register_monthly_pass",
        "description": "Đăng ký vé tháng xe bus điện VinBus cho hành khách (ưu đãi cho sinh viên, người cao tuổi, phổ thông).",
        "parameters": {
            "type": "object",
            "properties": {
                "passenger_name": {
                    "type": "string",
                    "description": "Họ và tên đầy đủ của hành khách đăng ký"
                },
                "phone_number": {
                    "type": "string",
                    "description": "Số điện thoại liên hệ của hành khách"
                },
                "route_id": {
                    "type": "string",
                    "description": "Mã tuyến xe bus điện đăng ký vé tháng (ví dụ: 'E01', 'E02', 'Tất cả các tuyến')"
                },
                "pass_type": {
                    "type": "string",
                    "description": "Đối tượng đăng ký: 'Học sinh/Sinh viên', 'Người cao tuổi', 'Tập thể', 'Phổ thông'"
                },
                "start_month": {
                    "type": "string",
                    "description": "Tháng bắt đầu áp dụng vé tháng (ví dụ: '10/2026')"
                }
            },
            "required": ["passenger_name", "phone_number", "route_id", "pass_type"]
        }
    }
]

# ==============================================================================
# 2. MÔ PHỎNG DỮ LIỆU & HÀM THỰC THI TOOL (EXECUTION LAYER)
# ==============================================================================

VINBUS_DATABASE = {
    "E01": {
        "route_name": "Tuyến E01: Bến xe Mỹ Đình - Vinhomes Ocean Park",
        "departure": "Bến xe Mỹ Đình",
        "destination": "Vinhomes Ocean Park (Gia Lâm)",
        "operating_hours": "05:00 - 22:30 hàng ngày",
        "frequency": "15 - 20 phút / chuyến",
        "ticket_price_single": "8.000 VNĐ",
        "ticket_price_monthly": "100.000 VNĐ (Ưu đãi HS/SV) / 200.000 VNĐ (Phổ thông)",
        "stops": ["Bến xe Mỹ Đình", "Cầu Giấy", "Kim Mã", "Nguyễn Văn Cừ", "Vinhomes Ocean Park"]
    },
    "E02": {
        "route_name": "Tuyến E02: Hào Nam - Vinhomes Ocean Park",
        "departure": "Ga Cát Linh / Hào Nam",
        "destination": "Vinhomes Ocean Park",
        "operating_hours": "05:00 - 22:00 hàng ngày",
        "frequency": "15 phút / chuyến",
        "ticket_price_single": "8.000 VNĐ",
        "ticket_price_monthly": "100.000 VNĐ (HS/SV) / 200.000 VNĐ (Phổ thông)",
        "stops": ["Hào Nam", "Tràng Thi", "Trần Hưng Đạo", "Cầu Vĩnh Tuy", "Vinhomes Ocean Park"]
    },
    "E03": {
        "route_name": "Tuyến E03: Mỹ Đình (Hàm Nghi) - Vinhomes Ocean Park",
        "departure": "Hàm Nghi (Mỹ Đình)",
        "destination": "Vinhomes Ocean Park",
        "operating_hours": "05:05 - 22:10 hàng ngày",
        "frequency": "20 phút / chuyến",
        "ticket_price_single": "9.000 VNĐ",
        "ticket_price_monthly": "100.000 VNĐ (HS/SV) / 200.000 VNĐ (Phổ thông)",
        "stops": ["Hàm Nghi", "Thái Hà", "Chùa Bộc", "Cầu Thanh Trì", "Vinhomes Ocean Park"]
    }
}


def execute_bus_route_query(route_id: str = "ALL") -> str:
    """Thực thi tra cứu lộ trình xe bus theo mã tuyến hoặc lấy danh sách tất cả các tuyến"""
    if not route_id:
        route_id = "ALL"
        
    clean_route_id = str(route_id).strip().upper()
    
    # Trường hợp hỏi danh sách tất cả các tuyến
    if clean_route_id in ["ALL", "DANH_SACH", "DANH SACH", "TẤT CẢ", "TAT CA", "TẤT CẢ CÁC TUYẾN"]:
        all_routes = []
        for rid, rinfo in VINBUS_DATABASE.items():
            all_routes.append({
                "route_id": rid,
                "route_name": rinfo["route_name"],
                "departure": rinfo["departure"],
                "destination": rinfo["destination"],
                "operating_hours": rinfo["operating_hours"]
            })
        return json.dumps({
            "status": "SUCCESS",
            "route_id": "ALL",
            "message": "Danh sách các tuyến xe bus điện VinBus hiện có",
            "data": all_routes
        }, ensure_ascii=False)
        
    # Trường hợp tra cứu chi tiết một tuyến cụ thể
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


def execute_register_monthly_pass(passenger_name: str, phone_number: str, route_id: str, pass_type: str = "Phổ thông", start_month: str = "10/2026") -> str:
    """Thực thi đăng ký vé tháng xe bus điện VinBus"""
    price_map = {
        "Học sinh/Sinh viên": "100.000 VNĐ/tháng",
        "Người cao tuổi": "Miễn phí (Thẻ ưu tiên)",
        "Tập thể": "140.000 VNĐ/tháng",
        "Phổ thông": "200.000 VNĐ/tháng"
    }
    fee = price_map.get(pass_type, "200.000 VNĐ/tháng")
    registration_code = f"VB-PASS-{phone_number[-4:] if len(phone_number)>=4 else '8888'}"
    
    return json.dumps({
        "status": "SUCCESS",
        "registration_code": registration_code,
        "passenger_name": passenger_name,
        "phone_number": phone_number,
        "route_id": route_id,
        "pass_type": pass_type,
        "start_month": start_month,
        "fee": fee,
        "message": f"Đăng ký vé tháng xe bus điện VinBus thành công cho hành khách {passenger_name}! Mã đăng ký: {registration_code}, Tuyến: {route_id}, Mức phí: {fee}, Áp dụng từ tháng: {start_month}."
    }, ensure_ascii=False)


# Router gọi tool thực tế
TOOL_ROUTER = {
    "bus_route_query": execute_bus_route_query,
    "register_monthly_pass": execute_register_monthly_pass
}

def dispatch_tool_call(tool_name: str, arguments: Dict[str, Any]) -> str:
    """Hàm trung chuyển thực thi tool"""
    if tool_name in TOOL_ROUTER:
        try:
            return TOOL_ROUTER[tool_name](**arguments)
        except Exception as e:
            return json.dumps({"status": "EXECUTION_ERROR", "error": str(e)}, ensure_ascii=False)
    return json.dumps({"status": "UNKNOWN_TOOL", "error": f"Tool '{tool_name}' không tồn tại!"}, ensure_ascii=False)
