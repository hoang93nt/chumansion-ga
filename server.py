"""
Gà — Chu Mansion Chatbot
Facebook Messenger + Claude AI
Deploy: Render.com (free tier)
"""

import os
import json
import requests
import threading
import time
from datetime import datetime
from flask import Flask, request, jsonify
import anthropic

app = Flask(__name__)

PAGE_TOKEN   = os.environ["PAGE_ACCESS_TOKEN"]
VERIFY_TOKEN = os.environ["VERIFY_TOKEN"]
SHEETS_URL   = os.environ.get("SHEETS_CSV_URL", "")
claude = anthropic.Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])

# ── Cache phòng trống ──
room_cache = {"data": "", "updated_at": ""}

def fetch_rooms():
    if not SHEETS_URL:
        return
    try:
        resp = requests.get(SHEETS_URL, timeout=10)
        if resp.status_code == 200:
            lines = resp.text.strip().split("\n")
            rows = []
            for line in lines[3:8]:
                cols = line.split(",")
                if len(cols) >= 6:
                    ten  = cols[0].strip().strip('"')
                    tong = cols[1].strip()
                    con  = cols[3].strip()
                    gia  = cols[4].strip()
                    gia_cn = cols[5].strip() if len(cols) > 5 else ""
                    rows.append(f"  - {ten}: con {con}/{tong} phong | {gia}d/dem thuong | {gia_cn}d cuoi tuan")
            now = datetime.now().strftime("%H:%M %d/%m")
            room_cache["data"] = "\n".join(rows)
            room_cache["updated_at"] = now
            print(f"[ROOMS] Cap nhat luc {now}")
    except Exception as e:
        print(f"[ROOMS] Loi: {e}")

def schedule_rooms():
    while True:
        now = datetime.now()
        if now.hour in [6, 14] and now.minute == 0:
            fetch_rooms()
            time.sleep(61)
        time.sleep(30)

fetch_rooms()
threading.Thread(target=schedule_rooms, daemon=True).start()

# ── System prompt Gà — học từ 32 conversations chốt cọc thành công ──
GA_PROMPT = """Mày là Gà — nhân viên tư vấn đặt phòng của Chu Mansion Đà Lạt. Mày là con pet của khách sạn, tên Gà, vừa dễ thương vừa chốt đơn cực ngọt.

CÁCH NÓI CHUYỆN — học từ 32 conversations chốt cọc thực tế:
- Xưng "em", gọi khách "chị/anh/mình/bạn" — đọc context để chọn
- Cực thân thiện, tự nhiên: "người đẹp ơi", "nha", "nè", "neg", "ạ", "hen", "ù"
- Hay dùng: "Dạ", "Oker lun!", "Oker nè", "E xin sdt nha", "Hong sao hết nghen"
- Ngắn gọn, xuống dòng rõ. Không bullet points. Không formal.
- MỖI TIN TỐI ĐA 2-3 DÒNG NGẮN. Không viết dài. Chọn ý quan trọng nhất thôi.
- Ví dụ đúng: "Dạ em nghe ạ" rồi xuống dòng "Mình đi mấy người nha chị?"
- Ví dụ sai: liệt kê 5-6 dòng thông tin cùng lúc
- Viết tắt thoải mái: "dc" = được, "vs" = và, "k" = không, "ù" = ừ, "neg" = nhé

THÔNG TIN KHÁCH SẠN:
Tên: Chu Mansion - Chill & Grill and Pickleball
Địa chỉ: 231 Phù Đổng Thiên Vương, P.8, Đà Lạt (cạnh A1 Nguyễn Hữu Cảnh)
Hotline lễ tân: 0798 285 287 | Sale: 0896 404 572
Cách chợ: 2km, 7–10 phút đi xe

GIÁ PHÒNG ngày thường:
- Superior (Sup): 400–500k/đêm
- Deluxe view sân vườn: 500–600k/đêm
- Vip / Tổ chim (bồn tắm gỗ): 800–900k/đêm
- Family (2 giường): 700–1.000k/đêm
- Ngày lễ/cuối tuần: +30–50%
- Đặt trực tiếp LUÔN rẻ hơn Agoda/Booking

TIỆN ÍCH:
- Pickleball: 2h free khi đặt trực tiếp, sau đó 120k/giờ
- Bida: miễn phí hoàn toàn
- Xe máy: 130–150k/ngày (AB, Vision, Vario đời mới)
- Bãi đậu xe ô tô trong sân (kế sân Pickleball)
- BBQ: có, hỗ trợ than + dọn dẹp, đồ ăn tự chuẩn bị
- Trà chiều + nướng khoai buổi tối: có
- Không có ăn sáng

CHÍNH SÁCH:
- Check in: 14h. Có phòng trống hỗ trợ từ 12h. Sớm hơn phụ thu 30–50%
- Check out: trước 11h30. Out trễ 1–2h phụ thu 150k. Sau 18h tính thêm 1 ngày
- Pet: nhận, phụ thu 200k/lượt, ưu tiên phòng Deluxe
- Cọc trước để giữ phòng, còn lại thanh toán tại KS
- Đặt qua app không được tặng 2h pickleball free

QUY TRÌNH CHỐT ĐƠN (học từ 32 conv thành công):
1. Hỏi ngay: số người + ngày nếu chưa có
2. Báo giá ngắn: "Dạ deluxe 550 - sup 450 ạ"
3. Khách OK → "E xin sdt chốt bill nha"
4. Gửi bill đúng format:
   [Tên] [SĐT]
   In [ngày] — out [ngày] ([số] đêm)
   [số] phòng [loại] [giá] * [đêm] = [tổng]
   Tổng [số]đ
   Cọc giúp e [số]đ nha
5. Gửi địa chỉ + hotline:
   Khách sạn Chumansion 231 phù đổng thiên vương p.8
   Hotline lễ tân: 0798285287 | Sale: 0896404572
6. Mời Zalo: "Add hotline zalo call video check phòng tránh lừa đảo, an tâm r em gửi stk cọc nha"
7. Xác nhận cọc: "Đã cọc [số]. Còn [số]"

SAU KHI CHỐT CỌC — gửi list quán ăn:
"Nhà em có list quán ăn must try gửi mình nha:
Mì nấm · Cà ri Chàaa · Mì quảng cô 6 · Miến trộn đệ nhất
CF: Hana land · Villa D'Hiver · Tiệm cf người thương ơi
Bánh: Blue dream bread · Caneles Đà Lạt
Nhậu/nướng: Rụ · The Hot · OM · Túi nướng Lavender"

XỬ LÝ TÌNH HUỐNG:
- Hết phòng: "Tiếc quá [ngày] nhà em full r ạ. Mình linh động [ngày khác] dc k, em còn phòng đẹp lắm"
- So Agoda: "Đặt ở đây rẻ hơn nha, check thử đi" → chốt luôn
- Khách do dự: nhấn mạnh tiện ích, "mình đặt em tính giảm thêm nha"
- Nhóm đông: tư vấn combo phòng, giảm giá từ đêm thứ 2

QUAN TRỌNG:
- Mỗi tin PHẢI kết bằng câu hỏi hoặc hành động cụ thể
- Xuống dòng giữa các ý cho dễ đọc
- Tự nhiên như người thật chat — không đọc script"""

# Lưu lịch sử hội thoại (in-memory, reset khi server restart)
histories = {}

def get_ga_reply(user_id: str, text: str) -> str:
    """Gọi Claude API để Gà trả lời"""
    if user_id not in histories:
        histories[user_id] = []

    histories[user_id].append({"role": "user", "content": text})

    # Giữ tối đa 20 turns để tránh token quá dài
    history = histories[user_id][-20:]

    # Thêm thông tin phòng trống realtime vào prompt
    room_info = ""
    if room_cache["data"]:
        room_info = f"""

PHONG TRONG HIEN TAI (cap nhat {room_cache['updated_at']}):
{room_cache['data']}
Luu y: Day la so lieu cap nhat 2 lan/ngay (6h va 14h). Neu khach hoi chac chan hay noi "theo lich em co..." va push chot ngay."""

    system_with_rooms = GA_PROMPT + room_info

    try:
        response = claude.messages.create(
            model="claude-sonnet-4-5",
            max_tokens=400,
            system=system_with_rooms,
            messages=history
        )
        reply = response.content[0].text
        histories[user_id].append({"role": "assistant", "content": reply})
        return reply
    except Exception as e:
        print(f"Claude API error: {e}")
        return "Dạ em đang bận xíu\n\nMình nhắn lại sau hoặc gọi hotline 0798 285 287 để em hỗ trợ ngay nha!"


def send_message(recipient_id: str, text: str):
    """Gửi tin nhắn qua Messenger API"""
    url = f"https://graph.facebook.com/v19.0/me/messages?access_token={PAGE_TOKEN}"
    
    # Messenger giới hạn 2000 ký tự/tin — chia nhỏ nếu cần
    if len(text) <= 2000:
        messages = [text]
    else:
        messages = [text[i:i+1990] for i in range(0, len(text), 1990)]

    for msg in messages:
        payload = {
            "recipient": {"id": recipient_id},
            "message": {"text": msg},
            "messaging_type": "RESPONSE"
        }
        try:
            resp = requests.post(url, json=payload, timeout=10)
            if resp.status_code != 200:
                print(f"Send error: {resp.status_code} {resp.text}")
        except Exception as e:
            print(f"Send exception: {e}")


@app.route("/feedback", methods=["POST"])
def feedback():
    """Nhận feedback từ người test"""
    data = request.get_json(silent=True)
    if data:
        print(f"\n{'='*50}")
        print(f"FEEDBACK [{data.get('time','')}]")
        print(f"Nội dung: {data.get('feedback','')}")
        print(f"History gần nhất:")
        for m in data.get('history', []):
            role = 'GÀ' if m['role'] == 'assistant' else 'KHÁCH'
            print(f"  [{role}]: {m['content'][:100]}")
        print(f"{'='*50}\n")
    return jsonify({"ok": True})


@app.route("/webhook", methods=["GET"])
def webhook_verify():
    """Facebook verify webhook"""
    mode = request.args.get("hub.mode")
    token = request.args.get("hub.verify_token")
    challenge = request.args.get("hub.challenge")

    if mode == "subscribe" and token == VERIFY_TOKEN:
        print("Webhook verified!")
        return challenge, 200
    return "Verification failed", 403


@app.route("/webhook", methods=["POST"])
def webhook_receive():
    """Nhận và xử lý tin nhắn từ Messenger"""
    data = request.get_json(silent=True)
    if not data:
        return "OK", 200

    for entry in data.get("entry", []):
        for event in entry.get("messaging", []):
            sender_id = event.get("sender", {}).get("id")
            if not sender_id:
                continue

            # Chỉ xử lý text message
            msg = event.get("message", {})
            text = msg.get("text", "").strip()

            if text and not msg.get("is_echo"):
                print(f"[IN] {sender_id}: {text}")
                reply = get_ga_reply(sender_id, text)
                print(f"[OUT] Gà: {reply}")
                send_message(sender_id, reply)

    return "OK", 200


@app.route("/", methods=["GET"])
def frontend():
    """Serve giao diện chat cho bạn bè test"""
    with open("frontend.html", "r", encoding="utf-8") as f:
        return f.read(), 200, {"Content-Type": "text/html; charset=utf-8"}


@app.route("/health", methods=["GET"])
def health():
    return "Gà đang hoạt động 🐔", 200


@app.route("/chat", methods=["POST"])
def chat():
    """API cho frontend web"""
    data = request.get_json(silent=True)
    if not data:
        return jsonify({"error": "no data"}), 400

    messages = data.get("messages", [])
    if not messages:
        return jsonify({"error": "no messages"}), 400

    try:
        response = claude.messages.create(
            model="claude-sonnet-4-5",
            max_tokens=400,
            system=GA_PROMPT,
            messages=messages[-20:]
        )
        reply = response.content[0].text
        return jsonify({"reply": reply})
    except Exception as e:
        print(f"Claude API error: {e}")
        return jsonify({"error": str(e)}), 500


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)


# ═══════════════════════════════════════
# ZALO OA WEBHOOK
# ═══════════════════════════════════════

ZALO_OA_TOKEN = os.environ.get("ZALO_OA_TOKEN", "")
ZALO_SECRET   = os.environ.get("ZALO_SECRET", "")

def send_zalo_message(user_id: str, text: str):
    """Gửi tin nhắn qua Zalo OA API"""
    if not ZALO_OA_TOKEN:
        return
    url = "https://openapi.zalo.me/v3.0/oa/message/cs"
    headers = {
        "Content-Type": "application/json",
        "access_token": ZALO_OA_TOKEN
    }
    # Zalo giới hạn 2000 ký tự/tin
    chunks = [text[i:i+1990] for i in range(0, len(text), 1990)]
    for chunk in chunks:
        payload = {
            "recipient": {"user_id": user_id},
            "message": {"text": chunk}
        }
        try:
            resp = requests.post(url, json=payload, headers=headers, timeout=10)
            if resp.status_code != 200:
                print(f"[ZALO] Send error: {resp.status_code} {resp.text}")
        except Exception as e:
            print(f"[ZALO] Exception: {e}")


@app.route("/zalo-webhook", methods=["GET"])
def zalo_verify():
    """Zalo verify webhook"""
    return jsonify({"error": 0})


@app.route("/zalo-webhook", methods=["POST"])
def zalo_receive():
    """Nhận và xử lý tin nhắn từ Zalo OA — trả 200 ngay, xử lý background"""
    data = request.get_json(silent=True, force=True) or {}

    def process():
        event_type = data.get("event_name", "")
        print(f"[ZALO] Event: {event_type}")

        if event_type == "user_send_text":
            sender = data.get("sender", {})
            user_id = sender.get("id", "")
            message = data.get("message", {})
            text = message.get("text", "").strip()
            if user_id and text:
                print(f"[ZALO IN] {user_id}: {text}")
                reply = get_ga_reply(f"zalo_{user_id}", text)
                print(f"[ZALO OUT] Gà: {reply}")
                send_zalo_message(user_id, reply)

        elif event_type == "follow":
            follower = data.get("follower", {})
            user_id = follower.get("id", "")
            if user_id:
                welcome = "Dạ em nghe ạ\n\nCảm ơn mình đã quan tâm đến Chu Mansion Đà Lạt 🏡\n\nCho em hỏi mình đang cần tìm phòng hay có điều gì cần em hỗ trợ nha?"
                send_zalo_message(user_id, welcome)

    threading.Thread(target=process, daemon=True).start()
    return jsonify({"error": 0}), 200


@app.route("/zalo_verifierN8QZTOkRS5uBwCe3WC1W0GQtwoBgmJvwCZKv.html", methods=["GET"])
def zalo_domain_verify():
    """Zalo domain verification file"""
    html = """<html><head><meta name="zalo-platform-site-verification" content="N8QZTOkRS5uBwCe3WC1W0GQtwoBgmJvwCZKv"/></head><body>N8QZTOkRS5uBwCe3WC1W0GQtwoBgmJvwCZKv</body></html>"""
    return html, 200, {"Content-Type": "text/html; charset=utf-8"}

