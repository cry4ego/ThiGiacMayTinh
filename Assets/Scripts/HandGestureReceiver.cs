using System;
using System.Net;
using System.Net.Sockets;
using System.Text;
using System.Threading;
using UnityEngine;
using SanAndreasUnity.Behaviours;
using SanAndreasUnity.Behaviours.Vehicles;

/// <summary>
/// Nhận lệnh điều khiển cử chỉ tay qua UDP từ Python (MediaPipe)
/// và áp dụng vào nhân vật hoặc xe trong game San Andreas Unity.
/// 
/// Cử chỉ hỗ trợ:
///   FIST       → Tiến (W)
///   OPEN       → Phanh / Dừng
///   POINT_UP   → Nhảy (Space)
///   THUMB_UP   → Tăng tốc (Sprint)
///   VICTORY    → Vào/Ra xe (F)
///   NONE       → Không có tay → dừng nhập
/// </summary>
public class HandGestureReceiver : MonoBehaviour
{
    [Header("UDP Settings")]
    [Tooltip("Cổng UDP lắng nghe lệnh từ Python")]
    public int udpPort = 5005;

    [Header("Debug")]
    public bool showDebugGUI = true;

    // --- UDP ---
    private UdpClient _udpClient;
    private Thread _receiveThread;
    private bool _isRunning = false;

    // --- Trạng thái cử chỉ hiện tại (thread-safe) ---
    private volatile string _currentGesture = "NONE";
    private string _lastLoggedGesture = "";

    // --- Trạng thái input giả lập ---
    private bool _fakeForward    = false;
    private bool _fakeBrake      = false;
    private bool _fakeJump       = false;
    private bool _fakeSprint     = false;
    private bool _fakeEnterVehicle = false;

    // Để kích hoạt "nhấn một lần" (GetButtonDown)
    private bool _pendingJump    = false;
    private bool _pendingEnter   = false;

    // --- GUI ---
    private GUIStyle _labelStyle;
    private Texture2D _bgTexture;

    // ─────────────────────────────────────────────
    //  Unity Lifecycle
    // ─────────────────────────────────────────────

    private void Awake()
    {
        DontDestroyOnLoad(this.gameObject);
    }

    private void Start()
    {
        StartUDPServer();
        Debug.Log($"[HandGestureReceiver] 👋 Listening on UDP port {udpPort}");
    }

    private void Update()
    {
        // Cập nhật trạng thái input dựa trên cử chỉ hiện tại
        ApplyGestureInput(_currentGesture);

        // Inject input vào PlayerController (nhân vật đi bộ)
        InjectPedInput();

        // Inject input vào VehicleController (khi lái xe)
        InjectVehicleInput();
    }

    private void OnDestroy()
    {
        StopUDPServer();
    }

    private void OnApplicationQuit()
    {
        StopUDPServer();
    }

    // ─────────────────────────────────────────────
    //  UDP Server (chạy trên thread riêng)
    // ─────────────────────────────────────────────

    private void StartUDPServer()
    {
        try
        {
            _udpClient = new UdpClient(udpPort);
            _isRunning = true;
            _receiveThread = new Thread(ReceiveLoop)
            {
                IsBackground = true,
                Name = "HandGestureUDP"
            };
            _receiveThread.Start();
        }
        catch (Exception e)
        {
            Debug.LogError($"[HandGestureReceiver] ❌ Không thể khởi động UDP: {e.Message}");
        }
    }

    private void StopUDPServer()
    {
        _isRunning = false;
        _udpClient?.Close();
        _receiveThread?.Abort();
    }

    private void ReceiveLoop()
    {
        IPEndPoint remoteEP = new IPEndPoint(IPAddress.Any, 0);
        while (_isRunning)
        {
            try
            {
                byte[] data = _udpClient.Receive(ref remoteEP);
                string message = Encoding.UTF8.GetString(data).Trim().ToUpper();
                _currentGesture = message;
            }
            catch (SocketException)
            {
                // Bỏ qua khi socket bị đóng
            }
            catch (Exception e)
            {
                Debug.LogWarning($"[HandGestureReceiver] UDP Error: {e.Message}");
            }
        }
    }

    // ─────────────────────────────────────────────
    //  Ánh xạ cử chỉ → trạng thái input
    // ─────────────────────────────────────────────

    private void ApplyGestureInput(string gesture)
    {
        // Reset tất cả
        _fakeForward      = false;
        _fakeBrake        = false;
        _fakeJump         = false;
        _fakeSprint       = false;
        _fakeEnterVehicle = false;

        if (_lastLoggedGesture != gesture)
        {
            Debug.Log($"[HandGestureReceiver] 🤚 Gesture: {gesture}");
            _lastLoggedGesture = gesture;
        }

        switch (gesture)
        {
            case "FIST":
                // Nắm tay → Chạy về phía trước
                _fakeForward = true;
                break;

            case "OPEN":
                // Bàn tay mở → Phanh/Dừng
                _fakeBrake = true;
                break;

            case "POINT_UP":
                // Chỉ lên → Nhảy (trigger một lần)
                _fakeJump = true;
                _pendingJump = true;
                break;

            case "THUMB_UP":
                // Giơ ngón cái → Tăng tốc/Sprint
                _fakeForward = true;
                _fakeSprint  = true;
                break;

            case "VICTORY":
                // Chữ V → Vào/Ra xe
                _fakeEnterVehicle = true;
                _pendingEnter = true;
                break;

            case "NONE":
            default:
                // Không làm gì cả
                break;
        }
    }

    // ─────────────────────────────────────────────
    //  Inject vào Ped (nhân vật đi bộ)
    // ─────────────────────────────────────────────

    private void InjectPedInput()
    {
        var ped = Ped.Instance;
        if (ped == null || ped.IsInVehicle)
            return;

        if (_fakeForward)
        {
            // Di chuyển nhân vật về phía camera đang nhìn
            Transform camTransform = Camera.main != null ? Camera.main.transform : ped.transform;
            Vector3 forward = camTransform.forward;
            forward.y = 0f;
            forward.Normalize();

            ped.Movement = forward;
            ped.Heading  = forward;

            if (_fakeSprint)
                ped.IsSprintOn = true;
            else
                ped.IsRunOn = true;
        }

        if (_fakeJump && _pendingJump)
        {
            ped.OnJumpButtonPressed();
            _pendingJump = false;
        }

        if (_fakeEnterVehicle && _pendingEnter)
        {
            ped.OnSubmitPressed();
            _pendingEnter = false;
        }
    }

    // ─────────────────────────────────────────────
    //  Inject vào Vehicle (khi đang lái xe)
    // ─────────────────────────────────────────────

    private void InjectVehicleInput()
    {
        var ped = Ped.Instance;
        if (ped == null || !ped.IsInVehicle)
            return;

        var vehicle = ped.CurrentVehicle;
        if (vehicle == null)
            return;

        var input = vehicle.Input;

        if (_fakeForward)
            input.accelerator = _fakeSprint ? 1.0f : 0.6f;
        else if (_fakeBrake)
            input.accelerator = -0.5f;
        else
            input.accelerator = 0f;

        input.isHandBrakeOn = _fakeBrake;

        vehicle.Input = input;

        if (_fakeEnterVehicle && _pendingEnter)
        {
            ped.OnSubmitPressed(); // Thoát khỏi xe
            _pendingEnter = false;
        }
    }

    // ─────────────────────────────────────────────
    //  Debug GUI
    // ─────────────────────────────────────────────

    private void OnGUI()
    {
        if (!showDebugGUI) return;

        if (_labelStyle == null)
        {
            _labelStyle = new GUIStyle(GUI.skin.box)
            {
                fontSize = 16,
                fontStyle = FontStyle.Bold,
                alignment = TextAnchor.MiddleLeft,
                padding = new RectOffset(10, 10, 8, 8)
            };
            _labelStyle.normal.textColor = Color.white;

            _bgTexture = new Texture2D(1, 1);
            _bgTexture.SetPixel(0, 0, new Color(0f, 0f, 0f, 0.7f));
            _bgTexture.Apply();
            _labelStyle.normal.background = _bgTexture;
        }

        string gestureEmoji = _currentGesture switch
        {
            "FIST"      => "✊ FIST  → Chạy/Tiến",
            "OPEN"      => "🖐 OPEN  → Dừng/Phanh",
            "POINT_UP"  => "☝️ POINT → Nhảy",
            "THUMB_UP"  => "👍 THUMB → Tăng tốc",
            "VICTORY"   => "✌️ VICTORY → Vào/Ra xe",
            "NONE"      => "❌ NONE   → Chờ...",
            _           => $"❓ {_currentGesture}"
        };

        Rect boxRect = new Rect(10, 10, 350, 90);
        GUI.Box(boxRect,
            $"🤖 Hand Gesture Controller\n" +
            $"UDP Port: {udpPort}\n" +
            $"Cử chỉ: {gestureEmoji}",
            _labelStyle);
    }
}
