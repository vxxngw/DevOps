# Khôi phục WSL/Docker và kiểm chứng Jenkins – 15/11/2026

**Cập nhật sau khôi phục:** [CI/runtime mới](evidence/ci-runtime-latest.json) đã có agentonline, normal4/5SUCCESS,33test trong stageintegration khôngskip, đủ5imageSHA0CRITICAL và pushwebhook thật. Phần tường thuật sớm bên dưới được giữ theo thời điểm, không coi các câu “chưa integration/agent” cũ là trạng thái hiện tại. GHCR/review/VM/cluster vẫn chưa nghiệm thu.

Trạng thái mới nằm trong [ci-runtime-latest.json](evidence/ci-runtime-latest.json). Đây là tiến độ kiểm chứng bổ sung, không chuyển toàn bộ Mốc 2–4 sang VERIFIED.

| Hạng mục | Kết quả thực tế | Giới hạn |
|---|---|---|
| WSL Ubuntu22.04 | Chạy được shell; Ansible syntax, Bash và Vault synthetic qua lại trong phiên này | Không phải Ansible trên VM hoặc changed=0 |
| Docker Desktop/engine | Server29.9.3; chuyển active VHDX sang D đã kiểm chứng, inventory giữ nguyên; controller/engine riêng hoạt động | [Bằng chứng chuyển ổ](evidence/docker-storage-latest.json); image dev cũ, không suy thành build mới |
| Jenkins dự án | http://localhost:18090 hoạt động; useSecurity=true, anonymous API trả403 | Không cấp credential cho Jenkins cũ8080 |
| Cấu hình Jenkins | Folder an-uyen, credential clinic-github, agent clinic-ci-linux và job clinic-pipeline đã tạo; Git client Jenkins đọc đúng SHA nhánh codex/milestone-4 | Credential GHCR chưa có |
| Jenkinsfile | Parser thật từng fail vì timestamps() cần plugin chưa cài; bỏ tùy chọn đó rồi parser qua | Chưa có build pipeline, plugin set không thay đổi; timestamp vẫn có trong evidence/artifact |
| Build agent | Image built/run, offline=false, UID1000;13tool probes qua; Docker mutualTLS tới rootless engine | [CI mới](evidence/ci-runtime-latest.json); privileged bootstrap của engine vẫn là giới hạn local |
| VM/cluster | Preflight tiếp tục BLOCKED | Thiếu quyền KVM, libvirt/QEMU, RAM và disk cho3VM; không cấp quyền hoặc tạo VM trong phiên này |

Docker trước khôi phục báo `preparing block device /dev/sde ... no such device or address`. Sau khi dừng Desktop, sao lưu dữ liệu, terminate **riêng docker-desktop** và khởi động Desktop lại, engine đã chạy. Không reset Docker, không unregister distro hay xóa volume; Ubuntu không bị shutdown toàn bộ. Chưa đủ bằng chứng kết luận file ext4 hỏng hoặc một nguyên nhân gốc khác; chỉ xác nhận triệu chứng và cách khôi phục đã chạy.

Bản sao mới nằm trên ổ D trong `.ci-local/recovery-backups`, ngoài Git và Docker context. Cả data VHDX13.645.119.488byte và bootstrap VHDX100.663.296byte được giữ mở chỉ đọc độc quyền khi copy, kiểm lại byte count/SHA256 của bản sao. D:\DockerBackup từ chối ghi thêm nên dùng thư mục private trong workspace; giữ backup cũ và nguồn C. Đây là snapshot **trước** khi cấu hình credential/job Jenkins mới, không khẳng định nó chứa các thay đổi sau snapshot.

Cập nhật sau yêu cầu thực hiện trực tiếp15/11: đã chuyển bằng backend API nội bộ mà frontend Docker sử dụng khi Apply, không sửa JSON bằng tay. VHD tại `D:\DockerData\active\DockerDesktopWSL\disk\docker_data.vhdx` bị giữ mở, file data C cũ không còn; backend trả đúng settingD. Giữ nguyên14container/14volume/15image; Jenkins đăng nhập được, anonymous403. Có bản sao data+settings mới nhất kiểm SHA256 trước chuyển; bootstrap còn bị Windows giữ nên dùng các bản backup bootstrap đã kiểm trước đó. Xem [runbook và số đo](runbooks/docker-storage-migration.md). Các snapshot mô tả C ở trên được giữ như lịch sử, không phải trạng thái hiện tại.

Kiểm thử mã mới:81passed/8integration skipped; kiểm thử riêng driver scanner10passed có JUnit. Các bài integration cần dịch vụ riêng chưa chạy trong phiên này. Sửa scanner M4 dùng chung helper bảo mật: cache/temp trênD, ignorefile rỗng, ignore-unfixed=false; lỗi registry/scanner giữ gate đóng và tiếp tục các image độc lập. Kết quả scan thực được lưu riêng khi hoàn tất, không suy từ unit test.

Cập nhật CI tiếp theo15/11: agent online, Jenkins4/5SUCCESS và hai gate âm đã có evidence thật; full-stack SHA7healthy/non-root, migration/seed0 và email body đặt/hủy đã qua. Xem [hồ sơ mới](evidence/ci-runtime-latest.json). Bước tiếp: GHCR SHA/digest khi có credential và kiểm PRmain phù hợp. Webhook thật, VM/cluster, promotion/approval, monitoring ingest/cảnh báo, scale/tải/rollback/video vẫn chưa nghiệm thu. Sau chuyển đã chạy smoke đặt/hủy lịch và email trên image dev cũ; không thay integration của source M2/M4 mới.

Đối chiếu thực tế: cả8plugin trực tiếp đúng version/active, controller numExecutors=0; engine uid1000/rootless và SecurityOptions có rootless/seccomp/cgroupns. Đây là kiểm chứng controller/engine, không thay image-agent/CI build.


Quét image giám sát đã hoàn tất: **8/8 digest, không có CRITICAL**, dùng Trivy0.76.2, cache/temp trênD, không ignore-unfixed và ignorefile rỗng. Lượt đầu Elasticsearch hết thời gian trong khi tải JavaDB953MiB, không có report nên gate đóng; lượt retry với cache và TRIVY_TIMEOUT=15m đã qua cả8. Có [bằng chứng scan](evidence/ops-security-latest.json); gate consumer đối chiếu report gốc/hash/digest/freshness đã qua. Đây là quét từ xa, không phải8image đã chạy hoặc stack giám sát được nghiệm thu.

Bản audit công bố chỉ che trường checksum SHA1 package mà Gitleaks nhầm thành Sourcegraph token; CVE/target và mọi kết quả được giữ nguyên, không thêm allowlist. Report gốc trong ci-out/observability-images vẫn giữ hash đúng cho bootstrap; bản audit đã che không dùng làm gate input. Lượt timeout và metadata gate thất bại trước đó được giữ lại.


Sau các build đã xác minh, Docker có lượt dừng với log ENOSPC khi ghi init.log trên C. Đã dùng Desktopstop → terminate riêng docker-desktop → Desktopstart để khôi phục, engine29.9.3/Jenkins/agentonline, queue trống; VHDactiveD giữmở và backend đúngD. Snapshot Cpagefile allocated20994MiB; chưa kết luận đầy đủ tác nhân làm đầy C tại thời điểm lỗi, không sửa pagefile hay xóa file người dùng. Xem runtime-recovery-after-log-enospc.json trong bundleCI; các SUCCESS trước sự cố vẫn là bằng chứng lịch sử, không suy thành uptime liên tục.
