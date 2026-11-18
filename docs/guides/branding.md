# Nhận diện An Uyên Hospital

Nhận diện hiện tại theo thông tin chủ dự án cung cấp ngày14/11/2026; yêu cầu Soft Minimal sau đó cập nhật màu UI:

- Tên hiển thị: **An Uyên Hospital**.
- Màu logo và tên thương hiệu: **#103783**. Màu UI chính mới: **#286789** cho nút, liên kết, focus và lựa chọn, theo yêu cầu Soft Minimal mới nhất.
- Logo đang dùng trên header/favicon: `frontend/public/brand/an-uyen-logo-blue.svg`, màu **#103783** theo yêu cầu cập nhật của chủ dự án. SVG nhúng hình gốc và dùng bộ lọc sRGB để đổi màu, không vẽ lại nét logo.
- Ảnh nguồn vẫn giữ nguyên ở `frontend/public/brand/an-uyen-logo.jpg`; SHA256 `d98805068434ba4745e2bc0b93a03e76158a0550216c93ade36da63b11f88d3f`. Hash ảnh nhúng trong SVG cũng khớp nguồn.
- UI dùng nền#F3F7FA, thẻ#FFFFFF, chữ#223443/#566874, viền#D8E2E9 và Inter. [Thiết kế Soft Minimal và bằng chứng mới](soft-minimal.md) ghi đầy đủ các giá trị đo trên trình duyệt.

Tên mới áp dụng ở header/footer, tiêu đề trình duyệt/favicon, OpenAPI và tên người gửi/tiêu đề/nội dung email. Host/email dev `.test`, tên service/queue/DB giữ vai trò kỹ thuật, không phải tên thương hiệu hiển thị.

Các bằng chứng lịch sử sau lần đổi nhận diện ban đầu (trước Soft Minimal):

- TypeScript/Vite build và Docker build app/frontend thành công; các service healthy.
- [Suite Linux](../evidence/integration-20261113T183741Z/metadata.json):19/19 unit + integration pass (gồm4test broker/SMTP thật); không gọi cả19là test SMTP.
- [Browser smoke](../evidence/ui-an-uyen-20261113T183851Z/metadata.json):6checks pass; đặt/hủy lịch, email SENT, quyền patient/admin và responsive.
- [Inspection nhận diện](../evidence/branding-20261113T183956Z/metadata.json): logo HTTP200 và SHA256 khớp file gốc; nút chính thực tế rgb(16,55,131) trên desktop/mobile; không tràn ngang; OpenAPI và email nhận trong Mailpit đều mang tên An Uyên Hospital.
- [Ảnh desktop](../evidence/branding-20261113T183956Z/login-desktop.png), [mobile](../evidence/branding-20261113T183956Z/login-mobile.png), [header](../evidence/branding-20261113T183956Z/brand-header.png).
- [Kiểm tra native](../evidence/20261113T183544Z/metadata.json): lint/format/dependencies exit0;13pass/6skip đúng scope SQLite. Các skip được kiểm tra bằng runner Linux riêng.

Đây là xác nhận nhận diện trong môi trường dev, không thay bằng chứng các mốc Jenkins/IaC/K8s/monitoring/security còn thiếu. Mã vẫn UNCOMMITTED; metadata ghi source/bundle hash.

## Cập nhật logo xanh

ImageGen chế độ built-in đã được dùng để tạo bản đổi màu thử; [prompt và kết quả lựa chọn](../evidence/logo-blue-imagegen-prompt.txt) được lưu nguyên văn. Bản PNG thử có pixel #0D3982/#0C3882 nên không dùng làm asset cuối. Bản web cuối là SVG nhúng ảnh nguồn nguyên byte, áp màu cố định sRGB(16,55,131) qua mask của hình gốc; không dùng silhouette do AI vẽ lại.

Build Vite/Docker frontend đã chạy thành công. [Inspection trình duyệt](../evidence/logo-blue-20261113T185004Z/metadata.json) xác nhận logo/favicon cùng SVG, HTTP200, hash asset phục vụ khớp file, ảnh nhúng khớp nguồn, desktop/mobile không tràn ngang. Ba điểm pixel đặc trong ảnh render đều ARGB **ff103783**.

[Header xanh thực tế](../evidence/logo-blue-20261113T185004Z/header.png) · [Desktop](../evidence/logo-blue-20261113T185004Z/login-desktop.png) · [Mobile](../evidence/logo-blue-20261113T185004Z/login-mobile.png). Các evidence logo vàng bên trên là lịch sử trước yêu cầu đổi màu, không bị ghi đè. Không chạy lại các test DB/broker cho thay đổi màu/logo này.
