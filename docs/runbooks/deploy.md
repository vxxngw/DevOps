# Deploy – cấu hình đã chuẩn bị, runtime chưa chạy

DevCompose giữ README; Mốc 3 theo [infra-lab](infra-lab.md). Điều kiện: clusterbootstrap,4namespaceSecrets, registrydigest đã scan/push, DNS/trustedCA và syntheticfixture. Phiên này chưa có cluster/kubeconfig/release thật.

JenkinsDEPLOY mặc địnhfalse; chỉ currentmain/PUBLISH_IMAGES=true và khôngPR. Kubeconfig phải đúng namespace và CLINIC_EXPECTED_CLUSTER_SERVER. CAfile qua clinic-lab-ca, URL qua STAGING_URL/PRODUCTION_URL; không bỏ TLSverify.

ci.deploy dùng cùng release-manifest cho staging/production:

1. Context/digestrepository/schema/policy/Secretmetadata preflight, không in secretvalues.
2. Render ConfigMap có hash/Services/SA, applyfoundation PostgreSQL/RabbitMQ/Mailpit và đợirollout.
3. MigrationJob riêng theo commit/confighash, Alembicupgradehead, đợiComplete trướcAPI. Không mọi replica tự migrate, không productionseed.
4. Applyapp/HPA/KEDA/Ingress/Certificate, đợirollout/CertificateReady.
5. SmokeHTTPS login → slotcòn trống → booking → SENT → Job tìm đúngemail trong Mailpit → hủy lịchsynthetic. SENT một mình chưa đủ; Mailpitkhông chứng minh mailboxngoài.
6. Chỉ sau smoke lưu release/configsnapshot và receipt vào artifact/ConfigMapclinic-release-state. Stagingevidence archive trước input, người được cấu hình duyệt trong15phút; productiondùngđúngdigest, không buildlại.

Bootstrapaccount là thao tácoperator riêng sau migration/initialpod, không phải releaseđạt: dùng admin kubeconfig và `kubectl -n staging exec -it deployment/api -- python -m clinic.manage_user --email admin@example.test --role admin` (đổi namespacecho production). Mật khẩu nhập tương tác, không argv/log. CLIchỉ tạo .testuser rõ ràng, không reset/elevate usercũ. Tạo patientsmoke riêng, bác sĩ và slottươnglai quaadminUI. DBtrống chưa fixture sẽ failbusinesssmoke; không bỏgate báo xanh. Sau bootstrap chạy lại pipeline và giữ approvalproduction.

Đối chiếu podcontainerStatuses.imageID với release; kiểm namespace/RBAC/PVC/health/metrics/2API+frontendReady và inbox. Chạy requestloop trongrollout để đo lỗi/p95; chưa chứng minh không gián đoạn. Coldmiddleware rebuild/baseupgrade cần maintenance/đo DBrestart.

Rollout/smokefail dừngpipeline; khi có previoussnapshot thành công thì thử khôi phục image/config và smoke, giữ FAILURE của deploygốc. Lầnđầu chưa snapshot phải sửa nguyên nhân, không tạo receiptgiả. Xem [rollback](rollback.md).
