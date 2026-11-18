# Postmortem – CHƯA HOÀN THÀNH sản phẩm nhóm

Chưa có postmortem sự cố vận hành do nhóm xác nhận. Không chuyển lỗi cố ý trong demo thành sự cố ngoài ý muốn. Sự cố thực quan sát trong phiên Codex: Docker engine mất kết nối EOF/HTTP500 khi build, sau đó phục hồi báo phiên bản mới; image PostgreSQL bookworm cục bộ có /etc/passwd rỗng, container non-root không khởi động. Nguyên nhân chưa xác định; không kết luận upstream lỗi, thiếu RAM hay image corruption khi chưa có đủ bằng chứng.

Nhóm có thể điều tra sự cố triển khai này và bổ sung postmortem có trách nhiệm thực, hoặc dùng sự cố thực khác. Cần có: chủ sự cố và người review; thời điểm/timeline theo UTC và giờ Việt Nam; tác động; detection; nguyên nhân có evidence và các giả thuyết loại trừ; xử lý; hành động phòng ngừa có owner/hạn; verification sau sửa. Hiện chưa coi SUB2c đã đạt.

## Bản kỹ thuật của sự cố triển khai đã quan sát

Tác động: chặn khởi động/kiểm chứng dev; management/metrics không truy cập được dù AMQP khỏe; request qua frontend lỗi sau recreate API. Chỉ dữ liệu giả lập và project clinic-dev; không có production để báo ảnh hưởng bệnh nhân hoặc SLA. Chưa đo chính xác tổng thời gian downtime. Người phụ trách/reviewer/hạn khắc phục của nhóm: chưa được cung cấp, không tự gán tên.

| UTC 13/11/2026 (giờ Việt Nam +7, sang14/11) | Quan sát / bằng chứng |
|---|---|
| 17:22:54→17:23:59 | Smoke có email body và broker outage/recovery pass, sau đó RemoteProtocolError tại management; exit1. Metadata runtime-20261113T172254Z |
| Trước17:30:52 | Diagnostics chỉ có AMQP/clustering; file /etc/rabbitmq/enabled_plugins đo được0byte. Thay artifact sinh bằng printf trong cache bằng source file có test -s, rebuild; có listener15672/15692 thật |
| 17:30:52→17:30:54 | Smoke HTTPStatusError trước tạo lịch, trong lúc API mới hơn frontend đang chạy. Nginx cấu hình cũ resolve upstream khi startup; nghi ngờ giữ IP API cũ sau recreate |
| 17:33:08→17:36:08 | Sau sửa DNS proxy, smoke exit0: recreate API vẫn phục hồi route; broker stop/recovery; SIGKILL worker→lease/recovery114.781s; email hủy3lịch thành công |
| 17:38:24→17:38:34 | Browser stack thật6checks pass, JS/CSS served hash khớp build |
| 17:44:25 | Hủy qua API đúng3lịch của lượt smoke lỗi trước đó; giữ lịch sử và nhận email hủy |
| 17:46:26 trở đi | Integration cuối19/19pass, lưu raw JSON stdout và JUnit |

Nguyên nhân xác nhận: plugin file rỗng làm plugin không bật; chỉ kiểm tra ping broker đã không phát hiện thiếu management/metrics. Nguyên nhân sâu vì sao artifact cache rỗng khi engine EOF/update **chưa xác định**. Với Nginx, stale DNS là giả thuyết phù hợp cấu hình và thời điểm; sửa resolver động và regression recreate API đã pass, nhưng không có capture upstream IP trước lỗi để khẳng định mọi nguyên nhân mạng khác đã bị loại trừ.

Hành động đã làm: source-control file plugin không secret và build guard test -s; PostgreSQL Alpine pinned digest/volume riêng sau kiểm tra user/version; dynamic DNS Docker cho proxy và lỗi gateway dễ hiểu trên UI; kiểm chứng listener/HTTP metrics, business smoke/fault/browser thay health-only; cleanup theo ID/window/correlation cụ thể, không reset DB; giữ cả failed evidence.

Việc còn lại: nhóm review/root-cause Docker cache, gán owner/hạn thật; đưa preflight management/metrics và regression vào Jenkins; Trivy/gitleaks trước release; giám sát tập trung với alert thật. Đây là postmortem kỹ thuật có dữ liệu thực, **chưa** tự xác nhận sản phẩm postmortem nhóm hoàn tất hoặc sự cố đã diễn ra trên production.
