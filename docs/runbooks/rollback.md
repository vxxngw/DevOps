# Rollback image/config – chưa diễn tập runtime

ci.deploy chỉ ghi currentreceipt sau businesssmoke; release sau lưu previoussnapshot vào artifactNAMESPACE-previous.json. Snapshot gồm digest và ConfigMap/spec liên quan, không secret/data. ConfigMaphashcũ được giữ, không prune.

Deployfail có previoussnapshot thì apply image/configcũ, bỏ mọi migrationJob, đợirollout và smoke. Không migrationdowngrade/pg_restore/secretrotation. Deploygốc vẫnFAILURE dù recoveryđạt. Schema phải tương thíchbảntrước; review/test migrationphá tươngthích trướcrelease.

Rollbackthủ công chỉ dùng snapshotCIđược tin cậy, đúng kubeconfig/CA/smokecredential:

```bash
export CLINIC_EXPECTED_CLUSTER_SERVER=https://192.168.150.11:6443
export CLINIC_SMOKE_URL=https://staging.anuyen.test
python -m ci.rollback staging ci-out/staging-previous.json
# Actual production URL/credentials/context required:
python -m ci.rollback production ci-out/production-previous.json --ack-production
```

Không sửa snapshot sang imagechưa scan. Nếu DB/broker/schema/secret không tương thích thì dừng, dùng phục hồi córeview; approllback không khôi phục dữ liệu. CIdeployer không sửa namespace/RBAC hoặc có clusteradmin.

Evidencephải có thời điểm lỗi/phát hiện/bắtđầukhôi phục/readiness/smoke, requestloop/tổnglỗi/p95 và image/configtrước/sau. rollback-result.seconds chỉ ghi khi thực sựchạy; đo mụctiêu≤120giây theo demo, không suy từtimeout. Hiện mới unit/schema/configchecks, chưa đoRTO/rollbackthật.
