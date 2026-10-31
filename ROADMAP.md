# Đánh giá mã cũ và triển khai theo giai đoạn

## Trước nâng cấp

| Yêu cầu | Bản QTC Travel Studio cũ |
| --- | --- |
| Tải video/nhạc, dựng MP4, preview/download | Có |
| Phân tích ảnh | Chỉ grayscale 2 FPS, Laplacian/phơi sáng/sai khác ảnh |
| AI thị giác / nhận diện người | Chưa có |
| Độ rung / bố cục | Sai khác ảnh đơn giản; chưa optical flow hoặc bố cục |
| Chọn cảnh / trùng lặp | Heuristic thumbnail, không ngữ nghĩa |
| Câu chuyện | Xếp theo điểm và xen nguồn, chưa bốn phần |
| Nhạc | Lưới onset năng lượng đơn giản, chưa năng lượng/cao trào toàn track |
| Màu | Một preset cố định, chưa so nguồn |
| Phong cách / 4K / ngang / tạo lại | Chưa có |
| Gửi dữ liệu tới AI ngoài | Không |

## Giai đoạn 1 — AI thật chạy trên máy (đã triển khai)

ResNet18 ImageNet-1K + SSDLite320 COCO, SHA-256 trọng số, setup download riêng, runtime không tự tải mô hình. Nhãn, confidence, bounding box và embedding được giữ trong phân tích. Thiếu mô hình thì báo chưa sẵn sàng; không thay bằng kết quả giả.

Đây là mô hình nhận diện ảnh có phạm vi giới hạn, không phải VLM hiểu video tổng quát. Phong cảnh ánh xạ từ một tập con nhãn ImageNet, người/đồ vật theo COCO. Không có nhận diện danh tính, địa danh, POV hay sự kiện du lịch tổng quát đáng tin cậy.

## Giai đoạn 2 — Phân tích và Editing Planner (đã triển khai)

8 FPS, optical flow + RANSAC ước lượng chuyển động/rung; đo nét/phơi sáng/bố cục; embedding+pHash chống trùng. Quét năng lượng nhạc, chọn excerpt, spectral flux/autocorrelation tạo beat có confidence và điểm cao trào. Nhịp yếu có cảnh báo.

Planner xác định bốn phần, dùng nội dung/motion/quality/source diversity để chấm lựa chọn, phân bố mật độ cắt, ưu tiên beat. Timeline có lý do và fingerprint; variant thay đổi lựa chọn trong các ứng viên chất lượng gần nhau một cách xác định. Đây là planner dựa trên ràng buộc sử dụng bằng chứng AI, không phải LLM sinh câu chuyện. Thẩm mỹ và bố cục vẫn là proxy đo ảnh, chưa có aesthetic model được huấn luyện.

## Giai đoạn 3 — Dựng và sản phẩm (đã triển khai)

Năm preset; dissolve có giới hạn; speed ramp theo cảnh/cao trào; cân màu thống kê có giới hạn; crop neo người; Full HD/4K dọc/ngang; kiểm tra metadata và decode toàn bộ đầu ra. Web có trạng thái mô hình, preview/download, bằng chứng chọn cảnh và tạo lại không upload nguồn.

Windows có setup/launcher và GUI chọn trực tiếp video lớn để tránh sao chép upload. Chưa có máy Windows để xác minh native; logic và pipeline được kiểm thử trên Linux. Giới hạn 20 GiB là cấu hình, chưa kiểm thử stress dữ liệu thật ở kích thước đó.

## Giai đoạn tiếp theo — chưa triển khai / không tuyên bố hoàn thành

- VLM hiểu cảnh/sự kiện/hành động tổng quát và LLM kể chuyện du lịch theo mục tiêu người dùng.
- Mô hình thẩm mỹ/video-quality chuyên dụng được huấn luyện; đánh giá benchmark và đối chiếu người dựng.
- Nhận diện/giữ chân trời, tracking chủ thể liên tục, chống rung và xử lý rolling shutter.
- Pipeline D-Log/HDR với LUT/profile cụ thể và quản lý màu đã kiểm chứng.
- Beat/downbeat/structure model chuyên nhạc và cắt theo phách mạnh đáng tin cậy với mọi thể loại.
- GPU, queue bền vững, hủy/tiếp tục job, nhiều tài khoản, stress test video hàng chục GiB trên Windows.

Chưa có API AI ngoài. Nếu bổ sung, cần nêu dịch vụ, chi phí, khóa API và xin phép riêng trước khi gửi bất kỳ frame/âm thanh/video riêng tư nào. Bản hiện tại không phát sinh phí API.
