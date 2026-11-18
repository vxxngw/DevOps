# Kiểm chứng phần backup và đường dẫn sau refactor

Chạy trực tiếp các bước CI trên Windows với working tree sau base `008183a`, không phải một Jenkins build mới:

- `ci.pipeline lint`: Ruff/format, ESLint, Prettier và frontend build đều exit 0.
- `ci.pipeline unit`: **110 passed, 8 skipped**, có [JUnit](junit-unit.xml). 8 skip thuộc integration cần dịch vụ riêng; không tính là đã chạy integration.
- `ci.infrastructure`: Terraform 1.17.2 fmt/init/validate, schema/policy **28 resource mỗi namespace**, **7 source Ansible** và **6 file Bash** đều qua. Bash parse mỗi file riêng, gồm thư mục con. Không tạo VM/cluster và không chạy Ansible convergence.

Lượt quét trực tiếp toàn working tree đã được dừng để tránh đọc cache và dữ liệu local bị ignore; `working-tree-secrets.log` rỗng không phải bằng chứng scan đạt. Lượt quét đúng các blob dự định commit được ghi riêng trong `indexed-secret-scan.json` khi thực sự hoàn tất. Không mở rộng allowlist hoặc commit env/dump để làm scanner đạt.

[Probe đầu](runtime-probes.json) ghi lỗi RemoteProtocolError khi Windows truy cập cổng 8000/8001, trong khi health/ready/metrics bên trong API/publisher/worker đều 200 và frontend/worker truy cập được. Không kết luận chắc nguyên nhân gốc chỉ từ triệu chứng này.

Đã restart riêng hai container API/publisher hiện có, exit 0. [Probe sau](runtime-probes-after-restart.json): 8 URL qua `localhost`/`127.0.0.1` đều 200, 9 health/ready/metrics trong container đều 200 và frontend wget exit 0. Giữ nguyên image/DB/volume/Jenkins; đây là runtime dev image có sẵn, chưa phải image build từ thay đổi mới. [Restore drill riêng](../backup-restore-20261115T134405Z/README.md) mới là kiểm API source hiện tại trên DB phục hồi.

Jenkins/build/push mới đang chờ dung lượng C; GHCR còn thiếu file token có quyền publish đúng namespace. Không suy kết quả native thành publication, timer, VM, Kubernetes, autoscale hoặc monitoring đã chạy.
