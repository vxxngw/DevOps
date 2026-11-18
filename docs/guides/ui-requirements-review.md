# Rà soát yêu cầu giao diện Soft Minimal

Ngày14/11/2026, kiểm tra lại **bản đang chạy tại http://localhost:18080** sau yêu cầu “double check”. Phạm vi là giao diện và trải nghiệm đặt lịch trong yêu cầu mới nhất; không thay kết quả ma trận DevOps/PDF.

Kết luận: các yêu cầu giao diện đã được triển khai và kiểm chứng trong môi trường local. Lượt rà soát phát hiện hai nhóm thiếu sót, đã sửa và kiểm tra lại thành công. Chữ cơ sở16px, tiêu đề trang28–32px và tiêu đề nội dung24px; chú thích/nhãn phụ có cỡ12–15px để phân cấp, không phải mọi chữ đều16px. Không coi thử nghiệm viewport bằng Edge là kiểm tra mọi thiết bị/trình duyệt thực.

## Đối chiếu từng yêu cầu

| Yêu cầu người dùng | Kết quả thực tế | Bằng chứng |
|---|---|---|
| Nền#F3F7FA, thẻ#FFFFFF | Đúng giá trị CSS đo trên trình duyệt | [Inspection](../evidence/soft-minimal-inspection-20261114T054357Z/metadata.json) |
| UI#286789, chữ#223443/#566874, viền#D8E2E9 | Đúng toàn bộ; logo/tên thương hiệu giữ#103783 theo yêu cầu trước | [Inspection](../evidence/soft-minimal-inspection-20261114T054357Z/metadata.json) |
| Inter, chữ cơ sở16px và phân cấp rõ | Font Inter thực tải từ local, gồm tiếng Việt; body16px, h1 28–32px, h2 nội dung24px; có chữ phụ nhỏ hơn | [CSS/font thực](../evidence/soft-minimal-inspection-20261114T054357Z/metadata.json) |
| Thoáng, khoảng cách nhất quán, responsive | Login/chọn giờ/xem lại không tràn ngang ở320/390/768/1440px; lịch hẹn và2màn hình admin cũng được kiểm tra4độ rộng | [12probes booking](../evidence/soft-minimal-inspection-20261114T054357Z/metadata.json), [12probes history/admin](../evidence/ui-requirements-final-20261114T054356Z/metadata.json) |
| Thẻ12px, nút/input8–10px, bóng rất nhẹ | Container `.card`12px; nút/input8px, các nút chọn bác sĩ/ngày8–10px; shadow nhẹ. Thẻ lịch hẹn bên trong cũng được đồng bộ12px khi rà soát | [Giá trị đo](../evidence/soft-minimal-inspection-20261114T054357Z/metadata.json), `frontend/src/app/styles.css` |
| Nút chính xanh, icon nét mảnh, input có nhãn | Nút#286789; icon SVG stroke1.6, nhãn liên kết input; focus hiển thị rõ | `frontend/src/components/ui/icons.tsx`, `frontend/src/app/App.tsx`, [ảnh login](../evidence/soft-minimal-inspection-20261114T054357Z/login-desktop.png) |
| Phân biệt giờ được chọn/hết chỗ | Có màu, dấu kiểm/nhãn và trạng thái disabled; dùng dữ liệu giờ bận thực trong smoke | [Browser11checks](../evidence/ui-double-check-20261114T054401Z/metadata.json) |
| Luồng từng bước, xem lại trước xác nhận | Chọn bác sĩ → Chọn lịch → Xem lại; sửa/quay lại giữ giờ và tùy chọn nhắc | [Smoke thật](../evidence/ui-double-check-20261114T054401Z/metadata.json), [audit15](../evidence/ui-requirements-final-20261114T054356Z/metadata.json) |
| Nhắc lịch dễ bật/tắt | Công tắc ở bước xem lại và lịch hẹn, PATCH lưu thực; được bật lại trước hạn; hủy dừng nhắc | [Smoke thật](../evidence/ui-double-check-20261114T054401Z/metadata.json), [suite backend30](../evidence/integration-20261113T192650Z/metadata.json) |
| Đang xử lý, thành công, lỗi | Có tải giờ, nút đang đặt/disabled, thành công, lỗi request; trạng thái nhắc chờ/đang gửi/thử lại/SENT/FAILED được hiển thị riêng email xác nhận | [Smoke thật](../evidence/ui-double-check-20261114T054401Z/metadata.json), [audit trạng thái giả lập](../evidence/ui-requirements-final-20261114T054356Z/metadata.json) |
| Ngôn ngữ lịch sự, hướng dẫn cụ thể | Thông báo lỗi yêu cầu thử lại/chọn giờ khác, nêu lịch đã lưu khi email lỗi; thời gian giờ Việt Nam | [Lỗi mạng](../evidence/ui-requirements-final-20261114T054356Z/network-error.png), [lỗi nhắc lịch](../evidence/ui-requirements-final-20261114T054356Z/reminder-failure.png) |
| Giữ dữ liệu khi lỗi | Đã kiểm tra sai đăng nhập,503, mất mạng,502HTML,409giờ bận; giữ email/giờ/công tắc và cùng key khi retry cùng nội dung | [Smoke](../evidence/ui-double-check-20261114T054401Z/metadata.json), [audit](../evidence/ui-requirements-final-20261114T054356Z/metadata.json) |

## Hai nhóm thiếu sót đã sửa

1. **Tải lại khung giờ sau lỗi:** ngày chọn ban đầu rỗng, dù đã tải được dữ liệu. Đã khôi phục ngày còn hợp lệ hoặc tự chọn ngày đầu tiên, hiển thị khung giờ để tiếp tục ngay.
2. **Trạng thái email nhắc lịch:** trước đây chỉ có mô tả lịch nhắc và SENT; thiếu chờ gửi/đang gửi/thử lại/FAILED. Đã bổ sung thông báo riêng; FAILED có `role=alert` và hướng dẫn xem lại giờ khám, không che trạng thái email xác nhận đã SENT.

[Lượt trước sửa](../evidence/ui-requirements-before-20261114T053603Z/metadata.json) có8pass/5fail;5test lỗi tương ứng hai nhóm trên. [Sau sửa](../evidence/ui-requirements-after-20261114T053824Z/metadata.json)13/13pass. [Lượt cuối](../evidence/ui-requirements-final-20261114T054356Z/metadata.json)15/15pass, thêm responsive history/admin. Không ghi đè các lượt trước.

## Phạm vi bằng chứng

- **11checks smoke**: trình duyệt → Nginx → API → PostgreSQL → RabbitMQ → SMTP/Mailpit thật; booking/hủy và bật/tắt nhắc được lưu thật. Dữ liệu synthetic do test tạo, dọn theo ID cụ thể.
- **15checks audit**: login/doctors/slots từ API thật; lỗi mạng/HTTP và trạng thái nhắc được giả lập tại trình duyệt để kiểm tra UI. Không cố ý làm SMTP production lỗi, không ghi trạng thái FAILED giả vào DB. Không dùng lượt này làm bằng chứng gửi email thật.
- **Inspection**: đo palette/font/radius, so hash JS/CSS được phục vụ với dist, kiểm tra logo và bố cục. Build Vite/Docker frontend và recreate/wait exit0;7dịch vụ đang healthy, migrationhead20261114_01.
- Suite backend30pass đã có trước lượt rà soát; thay đổi lần này chỉ frontend. Nhắc đến hạn được kiểm thử bằng đồng hồ truyền vào scheduler trên DB test, không tuyên bố đã chờ một giờ thực. Mailpit local chưa chứng minh gửi ra hộp thư ngoài.

**Toàn bộ đồ án DevOps chưa hoàn thành:** Jenkins pipeline/registry, Terraform/Ansible, Kubernetes/HPA/KEDA, dashboard/alert/log tập trung và security gates còn theo trạng thái riêng trong [compliance-matrix.md](../compliance-matrix.md). RabbitMQ đã chạy không đồng nghĩa toàn bộ thử thách queue monitoring/KEDA đã đạt.
