# QTC AI VIDEO EDITOR

Ứng dụng dựng video **chạy cục bộ**: đưa vào 5–20 video và một bản nhạc, chọn phong cách, AI thị giác phân tích, Editing Planner tạo timeline rồi FFmpeg xuất MP4. Có giao diện web xem trước/tải về/tạo lại và giao diện đọc trực tiếp video lớn trên Windows.

**AI thật đã tích hợp:** ResNet18 pretrained ImageNet-1K và SSDLite320 MobileNetV3 pretrained COCO. Không giả nhãn AI, không dùng cắt ngẫu nhiên, không gọi API AI bên ngoài. **Chưa có mô hình thẩm mỹ chuyên dụng hoặc LLM kể chuyện**; planner dựa trên ràng buộc và kết quả suy luận thị giác thật.

## Bắt đầu trên Windows — không cần lập trình

1. Cài **Python 3.12 x64** từ python.org, chọn **Add Python to PATH** và giữ tùy chọn Tcl/Tk. Cài FFmpeg có `ffprobe`; hướng dẫn trong [WINDOWS.md](WINDOWS.md).
2. Tải repository bằng **Code → Download ZIP**, giải nén vào thư mục bạn có quyền ghi.
3. Bấm đúp **`setup-ai-windows.cmd`** một lần. Cần Internet để tải thư viện PyTorch CPU và khoảng **58 MB trọng số công khai**. Không cần khóa API, không có phí API. Cài thư viện có thể tốn vài GB ổ đĩa.
4. Bấm đúp **`start-windows.cmd`**, giữ cửa sổ mở rồi truy cập **http://localhost:8000 trên chính máy Windows đó**. Chọn 5–20 video, nhạc đủ dài và bấm **AI dựng video**.
5. Chờ hoàn tất, xem trước, bấm tải MP4. **Tạo phiên bản khác** tái sử dụng nguồn và phân tích đã lưu; bạn có thể đổi phong cách/tỷ lệ/độ phân giải trước khi tạo lại. Nếu không có đủ lựa chọn để thay đổi timeline, ứng dụng thông báo rõ.

**DJI dung lượng lớn:** bấm đúp **`edit-local-windows.cmd`**, chọn trực tiếp tệp trên ổ đĩa và nơi lưu. Không cần upload qua trình duyệt hay sao chép nguồn. Kết quả nằm trong thư mục con `QTC-…/result.mp4` ở nơi bạn chọn (mặc định `output/`). Nút **Mở video đã xuất** mở trình phát trên Windows. Giao diện Windows này đã kiểm tra mã/biên dịch Python; chưa có máy Windows để kiểm thử native. Pipeline xử lý bên dưới được kiểm thử thực tế trên Linux.

## Những phần đã triển khai

| Phần | Cách hoạt động thực tế |
| --- | --- |
| Hiểu ảnh | ResNet18 cung cấp nhãn ImageNet và embedding 512 chiều; ánh xạ một số nhãn sang bờ biển/thiên nhiên/kiến trúc/đồ ăn/di chuyển/nội thất. Phạm vi nhãn có giới hạn, không phải mô hình hiểu video tổng quát. |
| Người và đồ vật | SSDLite COCO phát hiện người, xe, động vật… trên ảnh mẫu, kèm confidence và bounding box. Không nhận diện danh tính. |
| Phân tích toàn nguồn | Giải mã toàn video, đo mẫu **8 FPS**, chia cửa sổ 4 giây; chạy hai mô hình tại đầu/giữa/cuối mỗi cửa sổ. Có thể bỏ sót sự kiện thoáng qua giữa các mẫu. |
| Chất lượng | Laplacian, pixel phơi sáng, optical flow Lucas–Kanade và affine RANSAC để ước lượng độ nét/ánh sáng/chuyển động/rung. Không phải mô hình chất lượng được huấn luyện và chưa chống rung. |
| Bố cục/thẩm mỹ | Cân bằng mật độ cạnh, màu sắc và vị trí chủ thể. Đây là **proxy heuristic**, không giả làm điểm của mô hình thẩm mỹ. |
| Trùng lặp | So pHash + cosine embedding thật + màu để loại cửa sổ gần giống. Không dùng lại cùng cửa sổ nguồn; có thể loại nhầm hoặc bỏ sót cảnh trùng. |
| Âm nhạc | Quét năng lượng toàn bản nhạc (tối đa 30 phút), chọn đoạn phù hợp, spectral flux + autocorrelation để ước lượng beat và đường năng lượng. Không có mô hình AI âm nhạc; nhịp yếu được báo rõ và không giả beat. |
| Editing Planner | Tối ưu điểm kỹ thuật, nội dung, đa dạng nguồn và chuyển động theo bốn phần mở đầu/phát triển/cao trào/kết thúc. Cắt gần beat, cao trào theo năng lượng nhạc. Đây là **planner dựa trên ràng buộc**, chưa hiểu hành trình ngữ nghĩa như người dựng phim. |
| Dựng | Dissolve có giới hạn, cắt theo timeline, speed ramp mượt ở đoạn chuyển động/cao trào đủ điều kiện, giữ âm gốc nếu bật, fade toàn phim, nhạc và limiter. |
| Cân màu | Đo RGB trung vị từng nguồn, điều chỉnh thống kê có giới hạn + preset phong cách. Chỉ SDR, chưa có colorist AI hay chuyển DJI D-Log/HDR chuyên biệt. Nguồn có tag HDR PQ/HLG bị từ chối với hướng dẫn chuyển SDR. D-Log không luôn được nhận diện tự động. |
| Crop | Ưu tiên vị trí trung vị người được phát hiện, còn lại crop giữa. Chưa tracking theo thời gian. |
| Báo cáo | `analysis.json`, `music.json`, `timeline.json`, `report.json`: nhãn/confidence, đối tượng, lý do chọn, chương, thời điểm nguồn, trọng số SHA-256, giới hạn và kết quả kiểm chứng MP4. |

Năm preset: **Cinematic Travel, Luxury, Energetic, Relaxing, TikTok Viral**. Mỗi preset điều khiển mật độ cắt, mức dissolve, màu, âm gốc và ramp. “TikTok Viral” không bảo đảm lượt xem. Muốn cắt nhanh cần nhiều cảnh khác biệt hơn.

## Đầu ra và kiểm chứng

MP4 **H.264, yuv420p, 30 FPS, CRF 18, AAC 192 kbps / 48 kHz, faststart**. Hỗ trợ:

| Cấu hình | 9:16 | 16:9 |
| --- | --- | --- |
| Full HD | 1080 × 1920 | 1920 × 1080 |
| 4K | 2160 × 3840 | 3840 × 2160 |

Thời lượng 15–90 giây (mặc định 36). Nguồn cần đủ dài và đa dạng; nếu thiếu cảnh đạt chất lượng, báo lỗi thay vì lặp/kéo dài giả. 4K không phục hồi chi tiết từ nguồn thấp. Ghép tối đa bốn decoder mỗi lượt để hạn chế RAM; có thể cần vài lượt encode, tốn CPU và ổ đĩa. 4K CPU có thể chậm đáng kể. Phụ thuộc cấu hình máy, không có cam kết thời gian dựng.

Chỉ báo hoàn thành sau khi ffprobe kiểm tra codec/kích thước/FPS/thời lượng/audio và FFmpeg **giải mã toàn bộ cả hình và tiếng** thành công; đo ảnh mẫu và RMS âm thanh để phát hiện bản xuất đen/im lặng. Kiểm thử trình duyệt và cấu hình thực tế xem [VALIDATION.md](VALIDATION.md).

## Riêng tư và vận hành

- Tải mô hình chỉ thực hiện khi bạn chạy `app.setup_ai`; lúc dựng, mô hình được đọc từ ổ đĩa, không tự download và không gửi khung hình/âm thanh tới bên thứ ba. Chưa tích hợp API trả phí; không cần cấu hình khóa. Mọi tích hợp cloud AI trong tương lai cần sự cho phép riêng trước khi gửi media.
- Video, âm thanh, trọng số, output, cache, log và tệp bí mật bị loại khỏi Git. Không đưa footage của bạn vào GitHub.
- Web upload mặc định tối đa **20 GiB/tệp, 100 GiB/tác vụ**, tối đa 2 giờ mỗi video. Có thể chỉnh `QTC_MAX_FILE_GB`, `QTC_MAX_TOTAL_GB`. Các giới hạn này là cấu hình, **chưa được stress-test bằng tệp 20 GiB**.
- Multipart spool tệp tạm rồi sao chép vào công việc, cần đủ dung lượng cho nguồn/tệp tạm/bản dựng. Trình khởi động Windows chuyển TEMP/TMP sang `work/tmp`. Kiểm tra dung lượng trống; với nguồn lớn nên dùng `edit-local-windows.cmd`.
- Web có một worker dựng, tối đa ba tác vụ chờ/chạy. Lưu vào `work/jobs/<uuid>`, đổi bằng `QTC_DATA_DIR`. Trọng số lưu `work/models`, đổi bằng `QTC_MODEL_DIR` trước khi cài và chạy. Dữ liệu không tự xóa; tắt ứng dụng rồi xóa các thư mục công việc không cần (các phiên bản dựng lại dùng chung nguồn của công việc gốc).
- Ứng dụng cho một người dùng/máy tin cậy, chưa có đăng nhập, quota tài khoản, queue phân tán hay nút hủy. Không mở công khai nguyên trạng. Bind `0.0.0.0` phục vụ truy cập mạng riêng khi cần; mở `localhost` trên cùng máy. Phiên cloud không tự có URL preview công khai.

## Chạy thủ công / Linux

Yêu cầu Python 3.10–3.12, FFmpeg >= 6 có libx264; khuyến nghị Python 3.12.

```bash
python -m venv .venv
source .venv/bin/activate
pip install torch==2.5.1 torchvision==0.20.1 --index-url https://download.pytorch.org/whl/cpu
pip install -r requirements-ai.txt
python -m app.setup_ai
python -m uvicorn app.main:app --host 127.0.0.1 --port 8000
```

Không có AI đã cài thì UI hiển thị hướng dẫn và tắt nút dựng AI; không âm thầm chuyển heuristic. Pipeline classic cũ chỉ giữ tương thích API bằng `mode=classic`, không xuất hiện như chế độ AI.

Đọc trực tiếp nguồn qua CLI (thư mục output mới/rỗng):

```bash
python -m app.cli --videos clip1.mp4 clip2.mp4 clip3.mp4 clip4.mp4 clip5.mp4 --music music.wav --output output/my-edit --style cinematic --resolution 1080p --aspect 9:16 --duration 36
```

## Kiểm thử

```bash
pip install -r requirements-dev.txt
python -m unittest discover -s tests -v
```

Các kiểm thử mô hình thật được skip rõ nếu chưa có trọng số. Chuẩn bị **mẫu công khai**, không dùng footage riêng:

```bash
python scripts/prepare_ai_samples.py
python -m unittest discover -s tests -v
QTC_TEST_4K=1 python -m unittest discover -s tests -p test_ai_integration.py -v
```

Script mẫu download ảnh từ PyTorch Hub/scikit-image, dựng clip chuyển động máy giả lập và tạo nhạc tổng hợp. Ảnh/mẫu nằm trong `work/`, không commit. Không gọi API AI. Với PowerShell đặt `$env:QTC_TEST_4K="1"` trước khi chạy kiểm thử 4K.

Lộ trình, đánh giá trước/sau và phần chưa làm: [ROADMAP.md](ROADMAP.md).

## API chính

- `GET /api/health`, `GET /api/config`: trạng thái FFmpeg, mô hình và giới hạn.
- `POST /api/jobs`: multipart `videos` (5–20 tệp), `music`, `style`, `duration`, `resolution`, `aspect`, `ramp`, `nature`.
- `GET /api/jobs/{id}`: trạng thái, tiến độ và chương.
- `GET /api/jobs/{id}/video?download=true`: tải MP4; bỏ query để xem trong player.
- `GET /api/jobs/{id}/report`, `GET /api/jobs/{id}/timeline`: báo cáo/lịch dựng.
- `POST /api/jobs/{id}/regenerate`: JSON tùy chọn `style`, `resolution`, `aspect`; tự tăng variant, giữ nguồn và tái dùng phân tích, không tải lại video.
