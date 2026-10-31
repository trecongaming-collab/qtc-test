# Xác minh ngày 31/10/2026

## Kiểm thử tự động

`python -m unittest discover -s tests -v`: **8 kiểm thử đạt**, chạy khoảng 19 giây trong môi trường này.

- Trang chủ, health check; từ chối thời lượng/đuôi tệp sai; UUID và đường dẫn không hợp lệ.
- Kế hoạch dựng đúng thời lượng; không dùng lại cùng cửa sổ; loại trường hợp trùng lặp/không đủ chất lượng.
- Nhịp click 120 BPM được ước lượng trong sai số kiểm tra ±5 BPM.
- Nguồn quá ngắn được báo lỗi rõ ràng.
- Dựng FFmpeg thật ở kích thước nhỏ: nguồn có/không có audio, ambient mặc định/nhạc ngoài, speed ramp và H.264/AAC, thời lượng 30 và 31 giây.

## Kiểm tra hệ thống ở cấu hình xuất thật

Kiểm tra multipart API với nhiều tệp đầu vào. Bản dựng dùng 9 cửa sổ từ test pattern tổng hợp. Các thông số bên dưới thuộc bản kiểm thử tổng hợp, không phải video riêng tư.

Bản tải qua trình duyệt được ffprobe xác nhận:

| Thuộc tính | Kết quả |
| --- | --- |
| Video | H.264 |
| Kích thước | 1080 × 1920 |
| FPS | 30/1 |
| Audio | AAC, 48 kHz |
| Thời lượng container | 30.021029 giây |
| Kích thước tải | 10,909,838 byte |

Chromium/Playwright xác nhận: chọn nhiều video, cập nhật thanh thời lượng, khôi phục tác vụ qua tải lại trang, xem trước MP4 phát được, tải xuống đúng tên `QTC-travel-vlog.mp4`. Không có lỗi JavaScript; viewport 390 px không tràn ngang. Kiểm tra trực quan ảnh chụp desktop và mobile. Bộ script trình duyệt nằm trong `work/` phục vụ xác minh, không là dependency runtime của ứng dụng.

## Giới hạn dữ liệu và phạm vi

Không đưa footage, tên tệp riêng tư, nhật ký tác vụ hoặc dữ liệu upload vào repository. Chưa kiểm thử upload gần giới hạn 2 GiB hay vận hành nhiều người dùng.

Đây là ứng dụng local Python/FFmpeg, không có AI/API bên ngoài và chưa tích hợp Remotion Player/Studio. Máy chủ chạy trên localhost; việc bind toàn bộ giao diện mạng đã bị bộ duyệt tự động chặn do nguy cơ lộ video. Bản local đã chạy và kiểm thử thành công.
