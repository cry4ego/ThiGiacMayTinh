@echo off
chcp 65001 > nul
title Hand Gesture Controller - San Andreas Unity
cls
echo.
echo  ╔══════════════════════════════════════════════════════════╗
echo  ║   HAND GESTURE CONTROLLER — San Andreas Unity            ║
echo  ║   Điều khiển GTA bằng cử chỉ tay (MediaPipe + OpenCV)   ║
echo  ╚══════════════════════════════════════════════════════════╝
echo.
echo  Cử chỉ hỗ trợ:
echo    ✊ Nắm tay    → Chạy tiến / Ga xe
echo    🖐 Bàn tay mở → Dừng / Phanh
echo    ☝ Chỉ lên    → Nhảy
echo    👍 Ngón cái  → Tăng tốc (Sprint)
echo    ✌ Chữ V      → Vào / Ra xe
echo.
echo  [1/2] Đảm bảo Unity đã mở và game đang chạy...
echo  [2/2] Khởi động Hand Gesture Detector...
echo.
pause

cd /d "%~dp0"
.\venv\Scripts\python.exe hand_control.py

echo.
echo  ✅ Đã dừng Hand Gesture Controller.
pause
