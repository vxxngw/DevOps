# Backup/restore – có script, chưa có artifact/drill runtime

PDFtrang6 yêu cầu runbookrestore. scripts/backup.sh, restore.sh, host-health.sh và Ansiblebackuprole/systemdtimer đã chuẩn bị; Bashsyntaxcheck không thay pg_dump/restorethật.

Timer trên k3sserver chạy daily, customdump vào /srv/clinic-backups/NAMESPACE ngoài DBpod/storageagent, mode0600/checksum. Retention7ngày chỉ filenameđúngprefix trongdirđãkiểm; lỗi phải nonzero. Nodeexportertextfile ghi lastsuccesstimestamp, Mốc 4cần alertage/failure. Hai namespace táchdir; kiểm timezoneVM/UTC của timertrước demo.

```bash
sudo systemctl start clinic-backup@staging.service
sudo journalctl -u clinic-backup@staging.service --no-pager
sudo systemctl list-timers 'clinic-backup@*'
sudo /usr/local/sbin/clinic-restore.sh staging /srv/clinic-backups/staging/FILE.dump clinic_restore_DRILL_ID
```

Restorechỉ staging, kiểmpath/checksum; createdb từ chối DBđã có, pg_restore --exit-on-error rồi kiểm Alembic/rowcount. Không drop/reset/livecutover. DBdrill giữ đểoperator kiểm constraint/migration/booking/SMTP bằng appisolated; rowcount không tự chứng minh mọi dữ liệu/luồng hoạtđộng.

Production: dừng ghi khi cần, chọn backupRPOphùhợp, copy/checksum và restore vào môi trườngriêng; smoke/review schema/data/secret rồi duyệt cutover. Script không restore đèproduction. Approllback khác restoredatabase.

Lưu timestamp/checksum/size/exitcode, thờigianrestore và kiểm tra; RPO từ backupcuối tới sự cố, RTO đến businesssmokephục hồi. Chưa có sốđo. Backup trênserver chưaoffsite/HA, cũng mất khi Terraformdestroyserver: xuất bản đãkiểm checksum ra ngoài3 VM trước teardown. Không xóa backupDocker trênD.
