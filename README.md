# QTC Travel Vlog

Ứng dụng cục bộ dựng highlight du lịch bằng **Python + FFmpeg**, giao diện tiếng Việt. Tải nhiều video DJI, chọn nhạc nền, dựng nền có tiến độ, xem trước và tải MP4. Không cần khóa API.

## Chạy

Yêu cầu Python 3.10+ và FFmpeg/ffprobe có `libx264` trong PATH.

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python -m uvicorn app.main:app --host 127.0.0.1 --port 8000
```

Mở http://127.0.0.1:8000. Trên Windows kích hoạt bằng `.venv\Scripts\activate`.

Chọn 1–20 video MP4/MOV/MKV/M4V (tối đa 2 GiB/tệp và tổng 10 GiB), tùy chọn MP3/WAV/M4A/AAC/FLAC/OGG, thời lượng 30–45 giây, rồi bấm **Dựng hành trình**. Cần đủ khoảng 45–90 giây cảnh khác nhau, có thể nhiều hơn nếu footage trùng hoặc kém chất lượng. Một worker dựng lần lượt, tối đa 3 tác vụ đang tải/chờ/chạy.

Bản xuất: **1080 × 1920, 9:16, 30 FPS, MP4 H.264, CRF 18, yuv420p, AAC 192 kbps, faststart**. Nguồn thấp hơn 1080p sẽ được phóng lớn, không thể khôi phục chi tiết không có trong nguồn. Thời gian dựng phụ thuộc CPU và độ phân giải DJI.

## Những gì bản này thực sự làm

- Giải mã toàn thời lượng mỗi video, chấm điểm mẫu grayscale 96×54 ở **2 FPS**, chia cửa sổ 4 giây. Không phân tích từng khung hình gốc bằng AI.
- Ước lượng nét bằng Laplacian, phơi sáng bằng tỉ lệ pixel hợp lệ, chuyển động bằng sai khác khung liên tiếp. Loại cửa sổ dưới ngưỡng; so thumbnail để giảm cảnh gần giống; không sử dụng lại cùng cửa sổ.
- Mở đầu bằng điểm kỹ thuật cao nhất; ưu tiên xen kẽ nguồn video sau đó. Cắt theo lưới nhịp ước lượng 60–150 BPM từ năng lượng onset của nhạc. Đoạn cuối chốt theo thời lượng yêu cầu. Đây không phải beat tracker chuyên nghiệp.
- Cắt thẳng tự nhiên, fade đầu/cuối; speed ramp video mượt 2x → 1x → 2x ở một số cảnh khi bật. Audio tại hai đầu ramp dùng tốc độ trung bình để giữ độ dài tương ứng.
- Crop dọc giữa khung hình, chỉnh contrast/saturation và xanh nhẹ nhất quán. Hòa âm gốc ở mức thấp nếu bật, fade biên cảnh, trộn nhạc và limiter để hạn chế clipping. Không phân biệt tiếng gió, tiếng người và tiếng thiên nhiên.
- Nếu không tải nhạc, tạo một bản ambient có nhịp **100 BPM bằng tổng hợp âm thanh trong mã nguồn**. Đây là âm thanh minh họa đơn giản, không phải nhạc cinematic được tuyển chọn. Người dùng tự chọn nhạc phù hợp và quyền sử dụng.
- Báo cáo JSON gồm điểm cảnh, đoạn nguồn, timeline, BPM, các giới hạn và metadata đầu ra. Chỉ báo hoàn thành sau khi FFmpeg xuất thành công và ffprobe đọc được kết quả.
- Nếu thiếu cảnh đạt chất lượng/khác biệt, báo lỗi và yêu cầu thêm footage; không tự kéo dài bằng lặp cảnh hay tạo nội dung giả.

## Giới hạn rõ ràng

Chưa có AI hiểu nội dung, nhận diện nhân vật/POV/phong cảnh, kể chuyện ngữ nghĩa, đánh giá thẩm mỹ, theo dõi chủ thể, optical flow để đo rung hay chống rung. Các kiểm tra ảnh chỉ là heuristic, có thể bỏ nhầm cảnh đẹp hoặc bỏ sót rung/mờ. Bộ lọc màu hiện dành cho **SDR**; cần chuyển đổi DJI D-Log/HDR sang SDR đúng profile trước. Không tự cân màu từng camera, không AI nâng độ nét, không tạo nhạc qua API.

Đã tham khảo skill Remotion được yêu cầu. Bản hoạt động này dùng Python/FFmpeg và HTML video, **chưa tích hợp Remotion Player/Studio hay renderer**. Đây là lựa chọn cho stack kỹ thuật Python/FFmpeg trong yêu cầu.

Ứng dụng dành cho một người dùng trên máy tin cậy, chưa có đăng nhập hay cô lập tài khoản. Mặc định chỉ bind localhost. Không mở công khai nguyên trạng. Đường dẫn công việc là UUID nhưng không thay thế xác thực. Upload được multipart spool trước khi handler kiểm tra kích thước; nếu triển khai cần reverse proxy giới hạn body và quota đĩa. Không có tính năng hủy tác vụ ở bản này.

Tệp lưu ở `work/jobs/<uuid>`; đặt `QTC_DATA_DIR` để đổi nơi lưu. Bản dựng gián đoạn khi khởi động lại được đánh dấu lỗi. Nguồn, kết quả và log được giữ trên đĩa, không tự xóa; khi không còn tác vụ chạy, xóa thư mục công việc để giải phóng dung lượng. Chạy một Uvicorn worker; chưa hỗ trợ nhiều tiến trình hoặc hàng đợi phân tán.

## Kiểm thử

```bash
pip install -r requirements-dev.txt
python -m unittest discover -s tests -v
```

Kiểm thử tích hợp chạy FFmpeg thật (không mock): nguồn có/không có audio, ambient/nhạc tải lên, ramp, đầu ra H.264/AAC và thời lượng; render ở 180×320 để kiểm tra nhanh. Kiểm tra thêm ở 1080×1920 qua API được ghi ở `VALIDATION.md`.

API:

- `POST /api/jobs`: multipart `videos` (lặp nhiều tệp), `music` tùy chọn, `duration`, `ramp`, `nature`.
- `GET /api/jobs/{id}`: trạng thái, tiến độ, thông báo.
- `GET /api/jobs/{id}/video`: xem trước; thêm `?download=true` để tải.
- `GET /api/jobs/{id}/report`: báo cáo JSON.
- `GET /api/health`: kiểm tra FFmpeg/ffprobe.

## Truy cập và Windows

Hướng dẫn đầy đủ: `WINDOWS.md`. Trên Windows có thể bấm đúp `start-windows.cmd` sau khi cài Python và FFmpeg. Server nghe trên `0.0.0.0:8000`; trên cùng máy mở http://localhost:8000.

Địa chỉ localhost trong môi trường cloud chỉ dùng bên trong môi trường đó. Phiên này chưa có công cụ tạo URL chuyển tiếp cổng, nên đổi host sang `0.0.0.0` không tự tạo một liên kết preview truy cập được từ máy người dùng.
