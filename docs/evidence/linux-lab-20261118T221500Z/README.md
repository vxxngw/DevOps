# Bằng chứng Bài 3 – Linux trên VM VirtualBox (18/11/2026, UTC)

Môi trường: VM `anuyen-lab` tạo bằng `scripts/infra/vbox-lab.py` (VirtualBox 7.2.22 chạy qua Hyper-V/NEM), Ubuntu 24.04.5 LTS, 1 vCPU / 4 GB RAM / 20 GB, host-only `192.168.56.10`. Cấu hình bằng `infra/ansible/linux-lab.yml` từ WSL; quy trình ở [runbook](../../runbooks/linux-lab.md).

| Yêu cầu Bài 3 | Kết quả | File |
|---|---|---|
| User riêng | `uid=1000(clinicops)`, nhóm `sudo`; mật khẩu `clinicops` và `root` đều khoá (`L`) | [verify.txt](verify.txt) |
| SSH bằng key | Đăng nhập bằng key thành công; chỉ dùng mật khẩu → `Permission denied (publickey)`; `sshd -T`: `passwordauthentication no`, `kbdinteractiveauthentication no`, `pubkeyauthentication yes` | [ssh-negative.txt](ssh-negative.txt), [verify.txt](verify.txt) |
| Tắt đăng nhập root | `ssh root@…` với key hợp lệ → `Permission denied (publickey)`; `permitrootlogin no` | [ssh-negative.txt](ssh-negative.txt), [verify.txt](verify.txt) |
| Bật UFW | `Status: active`, `deny (incoming)`; 22/tcp chỉ từ `192.168.56.1`, 9100 từ mạng nội bộ | [verify.txt](verify.txt) |
| Kiểm tra sức khỏe theo lịch | `clinic-host-health.timer` (15 phút) tự chạy 21:30 và 22:00 → `healthy:true`; chạy khi đang build image → `healthy:false` (load 2.10 ≥ 2 × 1 CPU), unit failed đúng thiết kế | [verify.txt](verify.txt) |
| Backup CSDL theo lịch | `clinic-backup@dev.timer` **tự kích hoạt đúng lịch lúc 22:04:33** nhưng lỗi `203/EXEC` (script commit từ Windows thiếu bit thực thi). Sửa ở PR #20 (`414c4c6`), áp lại bằng lần chạy Ansible thứ 4; cùng unit đó chạy thành công 22:09:44 và 22:10:30: dump 25 660 byte, `sha256sum -c` OK, 9 bảng dữ liệu, metric `clinic_backup_last_run_success 1` | [verify.txt](verify.txt), [backup.txt](backup.txt) |
| Idempotent (Ansible) | Lần 1 `changed=25`; lần 2 `changed=2` (revision mới + seed bù); **lần 3 `changed=0`**; lần 4 `changed=1` (chỉ checkout revision sửa lỗi) | [ansible-run1.log](ansible-run1.log) … [ansible-run4.log](ansible-run4.log) |
| Tạo VM | cloud-init nhận `meta-data`, `user-data`, `vendor-data` qua SMBIOS/HTTP | [vbox-create.log](vbox-create.log) |

Giới hạn: chưa ghi lại lần **timer** chạy backup thành công sau bản sửa (VM được tắt lúc 22:55 để giải phóng RAM, trước lần chạy 23:00). Muốn bổ sung: bật VM ≥ 1 giờ rồi `sudo journalctl -u clinic-backup@dev.service`. Backup staging/production trong k3s thuộc Bài 9. IP trong file là mạng host-only riêng, không có key hay mật khẩu.
