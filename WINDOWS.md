# Chạy QTC Travel Vlog trên Windows

## 1. Chuẩn bị

Cài Python 3.10 trở lên (khuyến nghị Python 3.12) từ https://www.python.org/downloads/windows/ và bật **Add Python to PATH**. Cài FFmpeg, bao gồm ffprobe; có thể dùng PowerShell:

```powershell
winget install --id Gyan.FFmpeg --exact
```

Sau khi cài, đóng và mở lại PowerShell, kiểm tra:

```powershell
py --version
ffmpeg -version
ffprobe -version
```

Nếu không có winget, tải FFmpeg cho Windows theo https://ffmpeg.org/download.html và thêm thư mục `bin` chứa `ffmpeg.exe`, `ffprobe.exe` vào PATH.

Tải hoặc clone repository https://github.com/trecongaming-collab/qtc-test về máy Windows, ví dụ `C:\Projects\qtc-test`. Thư mục cần có `app` và `requirements.txt`.

## 2. Khởi động

Có thể bấm đúp `start-windows.cmd`. Tệp này tạo môi trường Python, cài thư viện nếu thiếu rồi chạy server. Tệp Windows này được kiểm tra nội dung trong môi trường Linux, chưa được thực thi trên Windows.

Hoặc mở PowerShell và chạy, thay đường dẫn cho đúng máy:

```powershell
cd C:\Projects\qtc-test
py -3 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe -m uvicorn app.main:app --host 0.0.0.0 --port 8000
```

Các lệnh dùng trực tiếp Python trong `.venv`, không cần thay đổi ExecutionPolicy của PowerShell. Nếu máy không có lệnh `py`, dùng `python` thay cho `py -3` khi tạo môi trường.

Giữ cửa sổ PowerShell mở, truy cập **http://localhost:8000** trong Chrome hoặc Edge trên cùng máy Windows. Kiểm tra **http://localhost:8000/api/health** phải trả về `{"ok":true}`. Nhấn Ctrl+C để dừng ứng dụng.

`0.0.0.0` là địa chỉ server lắng nghe, không phải địa chỉ để gõ vào trình duyệt. Trên máy đang chạy ứng dụng, dùng localhost. Nếu truy cập từ một máy khác cùng LAN, dùng `http://<IPv4-máy-Windows>:8000`; tra IPv4 bằng `ipconfig`. Chỉ cho phép Python qua Windows Firewall trên mạng riêng tin cậy khi cần dùng LAN. Ứng dụng chưa có đăng nhập.

## 3. Khi gặp lỗi

- `ffmpeg/ffprobe is not recognized`: sửa PATH và mở lại PowerShell.
- Không mở được localhost: kiểm tra cửa sổ server còn chạy và có thông báo `Uvicorn running`.
- `WinError 10048`/cổng đã sử dụng: dừng phiên ứng dụng cũ, hoặc đổi `--port 8000` thành `--port 8001` và mở http://localhost:8001.
- Thư viện thiếu: chạy lại lệnh pip với `.venv\Scripts\python.exe` như trên.
- Không đủ cảnh: tải thêm footage khác biệt; video quá ngắn không đủ để dựng 30 giây.

## Trạng thái xem trước trong môi trường cloud

Ngày 31/10/2026: FastAPI đã được khởi động lại bằng `--host 0.0.0.0 --port 8000`. Tuy nhiên, công cụ của phiên không cung cấp chức năng chuyển tiếp cổng/tạo URL preview bên ngoài. Việc đổi host không tự tạo đường dẫn truy cập từ trình duyệt trên máy người dùng. `127.0.0.1` trong cloud và `localhost` trên Windows là hai máy khác nhau. Chưa tạo được liên kết preview cloud có thể dùng từ máy người dùng.
