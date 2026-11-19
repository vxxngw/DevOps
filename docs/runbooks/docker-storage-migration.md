# Phương án chuyển dữ liệu Docker sang ổ D

Trạng thái cập nhật **15/11/2026: VERIFIED trong phạm vi chuyển ổ và khôi phục runtime local hiện có**. Docker đang dùng `D:\DockerData\active\DockerDesktopWSL\disk\docker_data.vhdx`. [Bằng chứng mới nhất](../evidence/docker-storage-latest.json): file D đang bị giữ mở, file dữ liệu C ở vị trí cũ không còn, setting backend trỏ đúng D; 14 container ID, 14 volume và 15 image ID giữ nguyên. Jenkins riêng18090 vẫn bật security, anonymous API403. Các ghi nhận lỗi và số đo bên dưới là lịch sử trước khi chuyển thành công.

Người dùng đã yêu cầu thực hiện trực tiếp. Công cụ cửa sổ tiếp tục lỗi khởi tạo, nên sau khi đọc mã tĩnh của Docker Desktop đã cài, đã dùng đúng backend endpoint mà frontend gọi khi Apply: `POST /app/settings/gui`, chỉ đổi `vm.resources.wslDataFolder`. Docker tự chuyển và khởi động lại; HTTP200 và đường dẫn thực được lưu trong evidence. Đây là API nội bộ theo phiên bản đang cài, không phải giao diện CLI công khai. Không tự sửa settings-store, registry WSL, tạo junction hay di chuyển/xóa VHDX bằng tay. Không unregister/reset distro hoặc shutdown toàn bộ WSL.

Ngay trước chuyển đã giữ data VHDX nguồn mở chỉ đọc độc quyền, sao lưu **13.668.188.160byte** và kiểm SHA256 bản sao: `D:\CODE\OOPs\Do_An\.ci-local\recovery-backups\before-recovery-20261115T024145`. Settings cũng được sao lưu; bootstrap vẫn bị Windows giữ sau khi terminate riêng docker-desktop nên không nằm trong bản sao mới này. Những bản bootstrap đã kiểm hash trước đó và mọi backup cũ vẫn được giữ. Dữ liệu C được Docker tự chuyển đi trong thao tác Apply, không phải một bước xóa nguồn thủ công.

Sau chuyển, C trống **15.941.672.960byte (~14,85GiB)**, D trống **8.110.608.384byte (~7,55GiB)** tại thời điểm probe. Bốn container dependency/frontend cũ được khởi động lại bằng `docker start`; không rebuild/recreate hay chạy lại migration/seed. Luồng đặt lịch → email Mailpit và hủy lịch → notification SENT đã chạy thật trên **image dev có sẵn**, không thay nghiệm thu image M2/M4 mới. Đây không phải backup/restore PostgreSQL theo rubric hoặc một build Jenkins.

[Backup thực tế](../evidence/docker-storage-20261114T073814Z/backup-manifest.json) khớp SHA256 cả data disk, bootstrap disk và settings khi Desktop đã dừng. [Bản sao D và thử cấu hình](../evidence/docker-migration-20261114T074728Z/copy-and-settings.json) chỉ là COPIED_AND_CONFIGURED_NOT_VERIFIED. Kiểm tra live sau khi engine phục hồi cho thấy data disk C bị giữ mở, bản D mở độc quyền được: **Docker vẫn dùng C**. Trường WslDataFolder thêm thủ công chưa có hiệu lực; không dùng nó làm cách chuyển được hỗ trợ. Script thử này đã rút khỏi repo, không chạy lại.

Trước khi thực hiện trực tiếp: công cụ điều khiển cửa sổ lỗi khởi tạo; người dùng đã nhận hướng dẫn dùng Settings chọn **D:\DockerData\active** (Docker tự thêm thư mục con tùy phiên bản) rồi Apply, tránh bản sao cũ trong D:\DockerData\DockerDesktopWSL. Bản D cũ là snapshot; lần chuyển thành công đã dùng dữ liệu C mới nhất, không kích hoạt snapshot cũ.

Ở lần thử cũ, automatic approval review đã từ chối đề xuất xóa data disk C trước khi chứng minh Docker đọc D vì rủi ro mất dữ liệu. Không có disk gốc nào bị xóa thủ công; giữ backup trên D. Ở lần thành công mới, chính cơ chế chuyển của Docker đã chuyển source sangD; đã kiểm VHD active và dữ liệu sau chuyển, không chạy bước dọn nguồn riêng.

## Dữ liệu đo trên máy

| Mục | Giá trị |
|---|---|
| Ổ C trống | 0byte tại thời điểm phát hiện lỗi |
| Ổ D trống | 76.957.159.424byte, khoảng71,67GiB |
| Disk dữ liệu | `C:\Users\Acer\AppData\Local\Docker\wsl\disk\docker_data.vhdx` |
| Kích thước file disk | 10.972.299.264byte, khoảng10,22GiB |
| Disk bootstrap | `C:\Users\Acer\AppData\Local\Docker\wsl\main\ext4.vhdx`,100.663.296byte |
| Cấu hình Desktop | `C:\Users\Acer\AppData\Roaming\Docker\settings-store.json` |
| Đích đề xuất | **D:\DockerData**, ngoài repo |
| Backup đề xuất | **D:\DockerBackup\before-m2-20261114**, ngoài repo |

D còn đủ cho một bản backup khoảng10,32GiB, dữ liệu chạy khoảng10,32GiB và phần dư cho build CI. Dung lượng sau chuyển cần đo lại; không cam kết kích thước data disk không tăng khi build. Docker có thể giữ bootstrap/cài đặt chương trình trên C; mục tiêu là chuyển data disk chứa image/container/volume.

## Các bước thực hiện sau khi được duyệt

1. Ghi snapshot container/volume/network, trạng thái ứng dụng và Jenkins khi daemon còn đọc được. Hiện scanner gặp lỗi I/O và Jenkins không truy cập được; ghi đúng lỗi, không coi inventory thiếu là dữ liệu đã mất.
2. Dừng Docker Desktop theo CLI/app chính thức, chờ engine và distro docker-desktop dừng, xác nhận VHDX không còn bị giữ mở. Không tắt/xóa các distro Ubuntu khác.
3. Copy data disk, bootstrap disk và settings vào thư mục backup mới trên D. Không ghi đè backup đã có. Tính SHA256 khi source đã ngừng ghi; so byte count/hash source với backup. Nếu copy/hash lỗi thì dừng chuyển.
4. Nếu C cần chỗ để Docker ghi settings, bảo toàn log Docker cũ vào backup trên D khi Desktop đã dừng, chỉ xử lý đúng thư mục log Docker được kiểm tra; không dọn Downloads, cache ứng dụng khác hoặc dữ liệu người dùng.
5. Mở Docker Desktop, vào **Settings → Resources → Advanced → Disk image location**, chọn **D:\DockerData\active**, Apply. Dùng cơ chế chuyển dữ liệu do Docker hỗ trợ; không tự sửa registry WSL, không unregister distro, không reset/factory reset.
6. Xác nhận Desktop sử dụng đường dẫn mới; VHDX trên D có dữ liệu, daemon đọc được volume cũ. Chạy lại clinic-dev từ image hiện có, xác nhận migration/seed exit0 và7service healthy. Kiểm tra API/publisher/worker health/ready/metrics, website, Mailpit và Jenkins cũ.
7. Kiểm tra một luồng đặt/hủy lịch synthetic và email; không suy container healthy thành cổng host hoạt động. Nếu image scanner bị ghi dở, chỉ tải lại đúng image/cache do Mốc2 tạo, không prune toàn hệ thống.
8. Lưu bằng chứng đường dẫn/dung lượng, hash backup, trạng thái trước/sau và các lỗi. **Giữ backup** sau khi kiểm chứng; việc xóa backup là quyết định riêng sau này.

## Quay lại nếu chuyển không thành công

- Dừng Desktop trước mọi thao tác với VHDX. Giữ cả nguồn/backup, không ghi đè file đang mount.
- Dùng vị trí cũ qua Settings khi còn khả dụng, hoặc phục hồi đúng settings/data disk từ backup đã kiểm hash theo quy trình hỗ trợ của Docker. Kiểm tra đủ dung lượng C trước khi phục hồi; không copy mù vào ổ đầy.
- Nếu Desktop không cho đổi location trong trạng thái lỗi hiện tại, dừng ở backup đã kiểm chứng và báo blocker để chọn cách di chuyển được hỗ trợ; không thử unregister/factory reset hoặc di chuyển distro khác.

Giới hạn: chuyển vị trí không chứng minh mọi image/cache đều không lỗi hoặc stack từ source mới đã đạt. Phạm vi đã kiểm là active disk D, giữ nguyên inventory, Jenkins có xác thực và luồng nghiệp vụ trên image dev cũ. Không suy thành CI build, image release, Kubernetes hoặc monitoring đã chạy. Ổ D còn khoảng7,55GiB sau khi giữ các backup; cần tính lại dung lượng trước build lớn. Không xóa backup trong phiên này.

Nguồn chính thức: [Docker Desktop WSL2 – nơi lưu dữ liệu và đổi location](https://docs.docker.com/desktop/features/wsl/), [Desktop settings](https://docs.docker.com/desktop/settings-and-maintenance/settings/). Phiên bản máy: Desktop4.99.0, engine29.9.3.


Khôi phục sớm15/11/2026 (trước lần chuyển thành công): Docker engine đã chạy lại nhưng probe thực vẫn thấy VHD C bị giữ mở, bản D cũ mở độc quyền được, D:\DockerData\active chưa tồn tại. Có bản sao tại `D:\CODE\OOPs\Do_An\.ci-local\recovery-backups\before-recovery-20261115T005310\disk\docker_data.vhdx` và manifest trong evidence CI recovery, SHA256/bytes đã đối chiếu khi source giữ read-only độc quyền. Bản sao này tiếp tục được giữ; xem trạng thái mới ở đầu tài liệu.


Cập nhật dung lượng sau CI15/11: người dùng đã duyệt xóa riêng `D:\DockerData\DockerDesktopWSL`. Cả2VHD đã kiểm lại SHA256 với `D:\DockerBackup\before-m2-20261114`, mở độc quyền được và không phải active disk; kiểm backend/path/reparse trước xóa bằng Remove-Item đúng đường dẫn cố định. Đã lấy lại10,31GiB, D tăng từ~3 lên~13,31GiB trước build tiếp. Mọi backup thật và `D:\DockerData\active` giữ nguyên. [Manifest duyệt/thực thi](../evidence/ci-agent-20261115T064424Z/duplicate-copy-cleanup-executed.json); mọi phát biểu giữ bản tạmD cũ phía trên là lịch sử trước lần duyệt mới.
