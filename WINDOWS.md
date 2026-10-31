# QTC AI VIDEO EDITOR trên Windows

## Chỉ cần thực hiện các thao tác này

1. Cài **Python 3.12 x64** từ https://www.python.org/downloads/windows/. Chọn **Add Python to PATH** và Tcl/Tk. Khuyến nghị 3.12 để dùng bộ PyTorch đã kiểm thử.
2. Cài **FFmpeg**, bao gồm ffprobe. Có thể mở PowerShell và dán:

   ```powershell
   winget install --id Gyan.FFmpeg --exact
   ```

   Sau khi cài, đóng/mở lại PowerShell. Nếu không có winget, tải theo https://ffmpeg.org/download.html, thêm thư mục `bin` có `ffmpeg.exe` và `ffprobe.exe` vào PATH.
3. Tải https://github.com/trecongaming-collab/qtc-test bằng **Code → Download ZIP**, giải nén vào thư mục có quyền ghi, ví dụ `C:\Projects\qtc-test`.
4. Bấm đúp **`setup-ai-windows.cmd`**. Chờ cài PyTorch CPU, OpenCV, SciPy và hai trọng số công khai ResNet18/SSDLite. Cần Internet lần cài đầu, khoảng 58 MB trọng số và thư viện lớn hơn nhiều. Không gửi video của bạn đi, không có phí API, không cần khóa.
5. Chọn một trong hai cách sử dụng bên dưới.

Các tệp CMD/Tkinter đã kiểm tra mã trên Linux; **chưa được chạy trên một máy Windows thật**. Pipeline Python/FFmpeg và mô hình thật đã chạy/kiểm thử trên Linux. Nếu lỗi cài đặt, giữ cửa sổ để đọc thông báo.

## Cách A — Giao diện web, xem trước và tạo lại

Bấm đúp **`start-windows.cmd`**, giữ cửa sổ mở. Khi thấy `Uvicorn running`, mở **http://localhost:8000 trên cùng máy Windows** bằng Chrome hoặc Edge.

- Đợi thông báo **AI cục bộ sẵn sàng**.
- Chọn **5–20 video** SDR và **một bản nhạc dài hơn bản dựng**.
- Chọn Cinematic Travel/Luxury/Energetic/Relaxing/TikTok Viral, Full HD/4K và dọc/ngang.
- Bấm **AI dựng video**, chờ tiến độ. Xem trước, tải MP4 và đọc bằng chứng chọn cảnh.
- Bấm **Tạo phiên bản khác** để dựng lại bằng nguồn/phân tích đã lưu. Có thể đổi phong cách/tỷ lệ/độ phân giải trước khi bấm. Không cần upload lại; video cũ được giữ. Nếu timeline không thay đổi được vì quá ít lựa chọn, ứng dụng thông báo rõ.

Mặc định 20 GiB/tệp và 100 GiB/tác vụ; cần đủ ổ đĩa cho tệp tạm, bản sao nguồn và output. Chưa stress-test tệp 20 GiB. Thư mục dữ liệu web là `work/jobs`. `start-windows.cmd` chuyển TEMP/TMP của tiến trình sang `work/tmp`.

## Cách B — DJI lớn, không upload hay sao chép nguồn

Bấm đúp **`edit-local-windows.cmd`** để mở cửa sổ chọn tệp:

1. Chọn 5–20 video trực tiếp từ ổ đĩa.
2. Chọn nhạc và nơi lưu MP4; nên chọn ổ còn nhiều dung lượng.
3. Chọn phong cách, tỷ lệ, độ phân giải và thời lượng, bấm **AI dựng video**.
4. Chờ xong rồi bấm **Mở video đã xuất**.

Mỗi bản nằm trong thư mục con `QTC-…`, có `result.mp4`, timeline và báo cáo. Mặc định lưu ở `output/` của dự án. Không di chuyển/xóa nguồn trong khi chạy. Giao diện này đọc trực tiếp đường dẫn trên máy, dùng cùng pipeline AI như web; hiện tạo lại bằng cách dựng lần nữa vào thư mục con mới, chưa có nút đổi variant như trên web.

Khuyến nghị Full HD trước. 4K encode CPU có thể mất nhiều thời gian và cần nhiều RAM/ổ đĩa; chưa có benchmark Windows hoặc GPU. Nguồn dưới 4K được phóng lớn, không tạo ra chi tiết mới. Nguồn DJI HDR/D-Log cần chuyển SDR đúng profile trước; ứng dụng chưa có pipeline màu chuyên biệt.

## Chạy bằng PowerShell nếu cần chẩn đoán

Không cần đổi ExecutionPolicy hoặc kích hoạt `.venv`:

```powershell
cd C:\Projects\qtc-test
py -3.12 -m venv .venv
.\.venv\Scripts\python.exe -m pip install torch==2.5.1 torchvision==0.20.1 --index-url https://download.pytorch.org/whl/cpu
.\.venv\Scripts\python.exe -m pip install -r requirements-ai.txt
.\.venv\Scripts\python.exe -m app.setup_ai
.\.venv\Scripts\python.exe -m uvicorn app.main:app --host 0.0.0.0 --port 8000
```

Kiểm tra FFmpeg bằng `ffmpeg -version`, `ffprobe -version`. Kiểm tra http://localhost:8000/api/health; trường `ok` và `ai.ready` phải đều là `true`.

Đổi ổ dữ liệu web trước khi chạy (ví dụ):

```powershell
$env:QTC_DATA_DIR="D:\QTC-data\jobs"
.\.venv\Scripts\python.exe -m uvicorn app.main:app --host 127.0.0.1 --port 8000
```

Nếu đổi `QTC_MODEL_DIR`, cần đặt cùng giá trị khi chạy `app.setup_ai` và lúc khởi động. Không đưa thư mục dữ liệu/trọng số lên GitHub.

## Khi gặp lỗi

- **AI chưa sẵn sàng:** chạy lại `setup-ai-windows.cmd`, kiểm tra kết nối và thông báo lỗi. Không cần API key.
- **Không có wheel PyTorch/phụ thuộc xung đột:** kiểm tra đang dùng Python 3.12 x64. Nếu `.venv` được tạo bởi Python khác, đổi tên thư mục đó rồi chạy setup lại.
- **Không có tkinter:** sửa cài Python, thêm Tcl/Tk; hoặc dùng giao diện web.
- **Không có ffmpeg/ffprobe:** sửa PATH, đóng/mở lại cửa sổ ứng dụng.
- **Không đủ cảnh:** thêm footage khác biệt/dài hơn hoặc giảm thời lượng. Cắt nhanh cần nhiều cảnh hơn; hệ thống không tự lặp hay giả cảnh.
- **Nhạc im lặng/quá ngắn:** đổi nhạc có tín hiệu, dài hơn bản dựng.
- **Lỗi HDR:** chuyển nguồn sang SDR đúng profile trước, chưa tự tone-map.
- **Ổ đầy:** dùng cách B, chọn ổ xuất khác, hoặc dọn công việc cũ khi ứng dụng đã tắt. Bản dựng lại trên web dùng chung nguồn của tác vụ gốc; không xóa riêng nguồn đó khi còn cần các phiên bản.
- **WinError 10048 / cổng bận:** tắt ứng dụng cũ hoặc đổi `--port 8000` thành `--port 8001`, rồi mở http://localhost:8001.
- **Không mở được preview cloud:** localhost của Codex là máy khác. Phiên cloud hiện không có công cụ tạo URL chuyển tiếp cổng; dùng localhost trên máy Windows của bạn.

`0.0.0.0` là địa chỉ lắng nghe, không phải URL để nhập vào trình duyệt. Ứng dụng chưa có đăng nhập; chỉ dùng máy/mạng riêng tin cậy. Ctrl+C để dừng web sau khi dựng xong.
