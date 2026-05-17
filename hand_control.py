"""
╔══════════════════════════════════════════════════════════╗
║   HAND GESTURE CONTROLLER — San Andreas Unity            ║
║   Điều khiển GTA bằng cử chỉ tay (MediaPipe + OpenCV)   ║
╚══════════════════════════════════════════════════════════╝

Cử chỉ được hỗ trợ:
  ✊ Nắm tay (Closed_Fist)   → FIST       → Chạy tiến
  🖐 Bàn tay mở (Open_Palm) → OPEN       → Dừng / Phanh
  ☝️ Chỉ lên (Pointing_Up)  → POINT_UP   → Nhảy
  👍 Ngón cái (Thumb_Up)    → THUMB_UP   → Tăng tốc
  ✌️ Chữ V (Victory)        → VICTORY    → Vào / Ra xe
  ❌ Không có tay            → NONE       → Dừng nhập

Giao tiếp: UDP → Unity port 5005
"""

import cv2
import socket
import time
import sys
import numpy as np
import mediapipe as mp
from mediapipe.tasks import python
from mediapipe.tasks.python import vision

# ──────────────────────────────────────────────
#  1. CẤU HÌNH UDP
# ──────────────────────────────────────────────
UDP_IP   = "127.0.0.1"
UDP_PORT = 5005
sock     = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
print(f"📡 UDP Client sẵn sàng → {UDP_IP}:{UDP_PORT}")

# ──────────────────────────────────────────────
#  2. ÁNH XẠ CỬ CHỈ MediaPipe → Lệnh Unity
# ──────────────────────────────────────────────
GESTURE_MAP = {
    "Closed_Fist" : "FIST",
    "Open_Palm"   : "OPEN",
    "Pointing_Up" : "POINT_UP",
    "Thumb_Up"    : "THUMB_UP",
    "Victory"     : "VICTORY",
    "ILoveYou"    : "VICTORY",   # ký hiệu 🤟 cũng dùng làm vào xe
}

GESTURE_DISPLAY = {
    "FIST"     : ("✊ Chạy tiến",    (0,  200, 100)),
    "OPEN"     : ("🖐 Dừng/Phanh",  (0,  100, 255)),
    "POINT_UP" : ("☝ Nhảy",         (255, 200,  0)),
    "THUMB_UP" : ("👍 Tăng tốc",    (0,  255, 200)),
    "VICTORY"  : ("✌ Vào/Ra xe",    (200,  0, 255)),
    "NONE"     : ("❌ Chờ...",       (80,  80, 80)),
}

CONFIDENCE_THRESHOLD = 0.72

# ──────────────────────────────────────────────
#  3. TRẠNG THÁI TOÀN CỤC
# ──────────────────────────────────────────────
last_gesture    : str   = "NONE"
last_sent_time  : float = 0.0
RESEND_INTERVAL : float = 0.5   # giây – gửi lại cùng lệnh để tránh Unity bỏ sót

# MediaPipe hand-landmark drawer
mp_hands    = mp.solutions.hands
mp_drawing  = mp.solutions.drawing_utils
mp_styles   = mp.solutions.drawing_styles

# ──────────────────────────────────────────────
#  4. CALLBACK NHẬN DIỆN CỬ CHỈ
# ──────────────────────────────────────────────
def on_gesture_result(
    result: vision.GestureRecognizerResult,
    output_image: mp.Image,
    timestamp_ms: int
):
    global last_gesture, last_sent_time

    if result.gestures:
        top   = result.gestures[0][0]
        name  = top.category_name
        score = top.score

        if score >= CONFIDENCE_THRESHOLD and name in GESTURE_MAP:
            cmd = GESTURE_MAP[name]
        else:
            cmd = "NONE"
    else:
        cmd = "NONE"

    now = time.monotonic()
    # Gửi khi cử chỉ thay đổi HOẶC theo định kỳ (để Unity không bỏ sót)
    if cmd != last_gesture or (now - last_sent_time) >= RESEND_INTERVAL:
        sock.sendto(cmd.encode(), (UDP_IP, UDP_PORT))
        last_sent_time = now
        if cmd != last_gesture:
            emoji, _ = GESTURE_DISPLAY.get(cmd, ("?", (255,255,255)))
            print(f"  → Gửi: {cmd:12s}  [{emoji}]")
        last_gesture = cmd

# ──────────────────────────────────────────────
#  5. KHỞI TẠO GESTURE RECOGNIZER
# ──────────────────────────────────────────────
MODEL_PATH = "gesture_recognizer.task"
base_opts  = python.BaseOptions(model_asset_path=MODEL_PATH)
options    = vision.GestureRecognizerOptions(
    base_options               = base_opts,
    running_mode               = vision.RunningMode.LIVE_STREAM,
    num_hands                  = 1,
    min_hand_detection_confidence = 0.5,
    min_hand_presence_confidence  = 0.5,
    min_tracking_confidence       = 0.5,
    result_callback            = on_gesture_result,
)

# ──────────────────────────────────────────────
#  6. VẼ HUD LÊN FRAME
# ──────────────────────────────────────────────
def draw_hud(frame: np.ndarray, gesture: str, fps: float) -> np.ndarray:
    h, w = frame.shape[:2]

    label, color = GESTURE_DISPLAY.get(gesture, ("???", (255,255,255)))

    # Thanh nền phía trên
    overlay = frame.copy()
    cv2.rectangle(overlay, (0, 0), (w, 70), (20, 20, 30), -1)
    frame = cv2.addWeighted(overlay, 0.75, frame, 0.25, 0)

    # Tên cử chỉ
    cv2.putText(frame, label,
                (15, 45), cv2.FONT_HERSHEY_SIMPLEX, 1.2,
                color, 3, cv2.LINE_AA)

    # FPS
    cv2.putText(frame, f"FPS: {fps:4.1f}",
                (w - 150, 45), cv2.FONT_HERSHEY_SIMPLEX, 0.9,
                (200, 200, 200), 2, cv2.LINE_AA)

    # Thanh nền phía dưới – bảng phím tắt
    overlay2 = frame.copy()
    cv2.rectangle(overlay2, (0, h - 90), (w, h), (20, 20, 30), -1)
    frame = cv2.addWeighted(overlay2, 0.75, frame, 0.25, 0)

    guide = "✊Tiến  🖐Dừng  ☝Nhảy  👍Sprint  ✌Xe  |  Q thoát"
    cv2.putText(frame, guide,
                (10, h - 55), cv2.FONT_HERSHEY_SIMPLEX, 0.55,
                (180, 180, 180), 1, cv2.LINE_AA)

    cv2.putText(frame, f"UDP → {UDP_IP}:{UDP_PORT}",
                (10, h - 20), cv2.FONT_HERSHEY_SIMPLEX, 0.5,
                (100, 200, 100), 1, cv2.LINE_AA)

    return frame


# ──────────────────────────────────────────────
#  7. VÒNG LẶP CHÍNH
# ──────────────────────────────────────────────
print("\n👀 Đang mở webcam... Giơ tay lên để điều khiển game!")
print("   Nhấn Q để thoát.\n")

cap = cv2.VideoCapture(0)
if not cap.isOpened():
    print("❌ Không thể mở webcam!")
    sys.exit(1)

cap.set(cv2.CAP_PROP_FRAME_WIDTH,  640)
cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
cap.set(cv2.CAP_PROP_FPS, 30)

timestamp = 0
fps_prev_time = time.monotonic()
fps_display   = 0.0

with vision.GestureRecognizer.create_from_options(options) as recognizer:
    # Tải MediaPipe Hands để vẽ landmark
    with mp_hands.Hands(
        model_complexity        = 0,
        max_num_hands           = 1,
        min_detection_confidence= 0.5,
        min_tracking_confidence = 0.5,
    ) as hands_drawer:

        while cap.isOpened():
            ok, frame = cap.read()
            if not ok:
                print("⚠️  Frame rỗng, bỏ qua...")
                continue

            # Lật ngang (gương)
            frame = cv2.flip(frame, 1)

            # FPS
            now = time.monotonic()
            fps_display = 1.0 / max(now - fps_prev_time, 1e-6)
            fps_prev_time = now

            # ── Gửi vào GestureRecognizer (bất đồng bộ) ──
            rgb_mp = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            mp_img = mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb_mp)
            recognizer.recognize_async(mp_img, timestamp)
            timestamp += 1

            # ── Vẽ landmark bàn tay ──
            results_draw = hands_drawer.process(rgb_mp)
            if results_draw.multi_hand_landmarks:
                for lm in results_draw.multi_hand_landmarks:
                    mp_drawing.draw_landmarks(
                        frame, lm,
                        mp_hands.HAND_CONNECTIONS,
                        mp_styles.get_default_hand_landmarks_style(),
                        mp_styles.get_default_hand_connections_style(),
                    )

            # ── HUD ──
            frame = draw_hud(frame, last_gesture, fps_display)

            cv2.imshow("🤚 Hand Gesture Control — San Andreas Unity", frame)

            if cv2.waitKey(1) & 0xFF == ord('q'):
                print("\n👋 Đã thoát.")
                break

cap.release()
cv2.destroyAllWindows()
sock.sendto(b"NONE", (UDP_IP, UDP_PORT))
sock.close()
print("✅ Đã dọn dẹp và đóng kết nối UDP.")