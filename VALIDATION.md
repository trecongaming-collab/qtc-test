# Xác minh QTC AI VIDEO EDITOR — 31/10/2026

## Bộ kiểm thử

Môi trường thực tế: Linux, Python 3.12, FFmpeg 7.1.5, PyTorch 2.5.1 CPU, torchvision 0.20.1; CPU inference/encoding.

- `python -m unittest discover -s tests -v`: **24 bài được phát hiện, 23 đạt, 1 skip có chủ đích** cho encode 4K nặng. Bản chạy cuối khoảng 41 giây trong môi trường này.
- `QTC_TEST_4K=1 PYTHONPATH=tests python -m unittest test_ai_integration.ActualFormats -v`: **bài 4K riêng đạt**, thực hiện bốn encode H.264/AAC thật với Full HD/4K và hai tỷ lệ; mỗi video 2 giây. Khoảng 210 giây trong một lần chạy có tải CPU đồng thời. Đây không phải benchmark Windows.
- `compileall` cho `app/`, `scripts/`, `tests/`; `git diff --check` đạt.

Phạm vi kiểm tra: nhịp click có BPM biết trước và đoạn năng lượng mạnh; từ chối nhạc im lặng; timeline bốn phần, không dùng lại cửa sổ, variant khác nhau, phong cách đổi mật độ cắt, thiếu nguồn/trùng/lỗi chất lượng; API yêu cầu 5–20 video và nhạc, giới hạn body, trạng thái cấu hình; H.264/AAC, ramp và hai đường audio của pipeline cũ; xuất đen/im lặng bị từ chối; decode toàn bộ bản xuất.

## Mô hình pretrained thật

Đã tải từ PyTorch, kiểm tra hash khi tải, chạy inference thật (không mock nhãn). Runtime không tự download; kiểm thử chặn hàm tải trọng số mà inference vẫn hoạt động.

| Mô hình | SHA-256 trọng số |
| --- | --- |
| ResNet18 ImageNet-1K | `f37072fd47e89c5e827621c5baffa7500819f7896bbacec160b1a16c560e07ec` |
| SSDLite320 MobileNetV3 COCO | `a79551df90c79834bcd3bb3845ef9d966b5449a3a9b2833ae8404778ca5d65d2` |

Ảnh công khai PyTorch Hub: nhãn Samoyed **0.8846**, detector dog **0.7493**. Ảnh astronaut từ scikit-image: detector person **0.9099**. Nhãn ImageNet trên người có thể sai/không phù hợp (ImageNet không có lớp person tổng quát); detector COCO cung cấp bằng chứng người riêng. Các confidence không phải độ chính xác trên bộ DJI.

Thiếu file trọng số được kiểm thử là lỗi rõ ràng, không chuyển sang nhãn giả hoặc âm thầm gọi API ngoài.

## Pipeline AI và trình duyệt

Bộ mẫu gồm **năm clip chuyển động máy giả lập từ ảnh công khai**, tạo bằng `scripts/prepare_ai_samples.py`, kèm nhạc beat/năng lượng tổng hợp. Mục đích là kiểm tra pipeline; **không phải footage DJI du lịch thật hoặc đánh giá thẩm mỹ bởi người dựng**. Không commit ảnh/video mẫu hoặc nguồn riêng tư.

Đã chạy từ giao diện web: chọn năm video và nhạc → AI suy luận/đo chất lượng → planner bốn phần → FFmpeg → preview/download MP4 → tạo bản khác bằng phân tích đã lưu.

| Thuộc tính | Bản đầu | Bản tạo lại |
| --- | --- | --- |
| Video | H.264 | H.264 |
| Kích thước | 1080 × 1920 | 1920 × 1080 |
| FPS | 30 | 30 |
| Audio | AAC 48 kHz | AAC 48 kHz |
| Thời lượng | 15.0 giây | 15.0 giây |
| Toàn bộ file giải mã được | Có | Có |
| Timeline thay đổi | — | Có, fingerprint khác |
| Dùng lại phân tích nguồn | — | Có |

Bản đầu tải từ Chromium: **10,062,690 byte**. Video HTML phát được; không có lỗi JavaScript. Đủ bốn chip chương, xem được bằng chứng chọn cảnh. Viewport 390 px không tràn ngang. Sau tải lại trang, phục hồi tác vụ/kết quả, thời lượng 15 và tỷ lệ 16:9 của bản đã hoàn tất. Kiểm tra ảnh chụp desktop/mobile.

Đo nội dung thật trên MP4 Full HD đã tải:

- Độ lệch chuẩn RGB tại 25%/50%/75%: **76.7242, 81.7245, 42.7389** (ảnh không phẳng/đen).
- RMS audio mono giải mã: **0.0156305**, có tín hiệu âm thanh.
- Có kiểm thử riêng từ chối video đen và âm thanh im lặng.

Bộ kiểm thử tích hợp AI kích thước nhỏ cũng chạy inference thật và dựng hai bản, xác nhận chapter, privacy, fingerprint và cache. Planner-only tests dùng fixture số có ghi nhãn rõ; fixture này không đi vào ứng dụng và không thay thế kết quả inference runtime.

## Giới hạn xác minh

- Không có máy Windows để chạy native CMD/Tkinter. Các launcher/GUI được rà soát và compile Python; pipeline chung chạy thực tế trên Linux. Cần xác minh tiếp trên Windows 3.12 x64.
- Chưa stress-test nguồn hàng chục GiB, 20 video dài, RAM thấp, lỗi ổ đĩa giữa encode hay job kéo dài; 20 GiB/100 GiB là giới hạn cấu hình.
- Encode 4K thực tế mới dùng sample **2 giây**, không phải benchmark dựng 30–90 giây từ DJI 4K gốc.
- Chưa có kiểm thử chất lượng nghệ thuật trên một bộ DJI đủ dài: không tuyên bố AI hiểu hoàn chỉnh câu chuyện, thẩm mỹ hoặc nhận diện phong cảnh đạt độ chính xác cụ thể.
- Bố cục/thẩm mỹ/chất lượng là proxy đo ảnh; âm nhạc là DSP; planner là tối ưu theo ràng buộc dùng kết quả mô hình thật. Chưa có aesthetic model, music structure model hoặc LLM viết câu chuyện.
- Chưa có API AI ngoài, không gửi video riêng tư tới dịch vụ bên ngoài. Không đưa video/dữ liệu công việc/trọng số lên GitHub.
- Môi trường cloud này chưa có công cụ tạo URL preview bên ngoài; localhost chỉ dùng trong môi trường chạy. Trên Windows dùng localhost của chính máy đó.
