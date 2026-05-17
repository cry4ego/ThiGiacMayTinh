import urllib.request

# Đường dẫn URL chính xác (đã sửa "floati6" thành "float16")
url = "https://storage.googleapis.com/mediapipe-models/gesture_recognizer/gesture_recognizer/float16/1/gesture_recognizer.task"

# Tải file về
urllib.request.urlretrieve(url, "gesture_recognizer.task")
print("✅ Model downloaded successfully!")