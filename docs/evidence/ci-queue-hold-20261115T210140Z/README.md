# Push tài liệu và giữ build do thiếu dung lượng

Thực hiện **04:01–04:03 ngày 16/11/2026 Việt Nam**, tương ứng 21:01–21:03 UTC ngày15/11. [Snapshot trước thay đổi](before.json) xác nhận controller18090 chỉ có folder `an-uyen`, một pipeline thuộc bootstrap, executor rảnh, agent online, build14/13 đã kết thúc và queue rỗng. Không thay Jenkins cũ8080.

POST `/quietDown` được đọc lại `quietingDown=true`, đúng reason trong [hold.json](hold.json). Không gọi shutdown/restart, disable job, đổi credential hoặc bỏ gate. C chỉ còn vài MiB; mở lại khi C≥5GiB, D≥3GiB, agent online và vẫn đúng người sở hữu hold theo [runbook](../../runbooks/ci-low-disk.md). Các ngưỡng là lựa chọn vận hành, không phải tiêu chí PDF.

Commit `75406f886530eb07877135da2241c279b9b9534b` đã **push thật** lên `codex/team-four-handoff`. `git ls-remote` và GitHub REST đọc lại cùng SHA. [metadata.json](metadata.json) xác nhận webhook push được HTTP202, đúng repoID1457478642/ref/SHA; Jenkins queue29 có cùng source, publish/deploy=false, bị giữ vì quiet-down. Jenkins gần nhất vẫn14SUCCESS cho source cũ, không có build mới đã chạy để báo đạt.

Đây là kiểm chứng **push → webhook → queue**, chưa phải kiểm chứng toàn pipeline hoặc registry/deploy. Main vẫn protected=false/API403; `.registry-token` chưa có. Không giả định tên/thành tích hoặc review của thành viên. Việc mở PR nháp bị bộ duyệt tự động chặn vì còn thiếu ủy quyền rõ từ người dùng; chưa tạo PR, chưa request reviewer/approve/merge.

Source của receipt push này là `75406f8`. Tài liệu runbook và bundle này được bổ sung ở commit tiếp theo; không dùng queue29 làm CI cho commit bổ sung đó. File JSON giữ byte gốc, không chứa credential hoặc raw webhook headers.
