# Bàn giao kỹ thuật Kubernetes, HPA/KEDA, TLS/RBAC và Rollout/Rollback

**Người phụ trách:** TV4 – Nguyễn Thành Thiện (Thien)  
**Người review:** TV2 – Vương (Vuong)  
**Tài liệu tham chiếu:** [deploy/k8s/](../../deploy/k8s/), [ci/deploy.py](../../ci/deploy.py), [ci/rollback.py](../../ci/rollback.py), [docs/compliance-matrix.md](../compliance-matrix.md)

---

## 1. Tổng quan phạm vi phụ trách (TV4)

Theo bảng phân công của nhóm, TV4 phụ trách các hạng mục cốt lõi thuộc:
- **Bài 9 (Kubernetes):** Kustomize packaging, 2 namespace (`staging`, `production`), Pod liveness/readiness probes, requests/limits, HPA co giãn theo CPU, StatefulSet DB/Queue, và Rolling Update / Rollback.
- **Bài 11 (Bảo mật cụm K8s):** HTTPS Ingress qua cert-manager, ServiceAccount tối thiểu quyền (không gán cluster-admin, không token API thừa), RBAC Role/RoleBinding, và NetworkPolicy giới hạn luồng mạng nội bộ.
- **Thử thách đề tài 8 (Event-driven Autoscale):** KEDA `ScaledObject` theo dõi độ sâu hàng đợi RabbitMQ để tự động scale số lượng worker email.

---

## 2. Cấu trúc và Chi tiết Cấu hình K8s Hiện có

Toàn bộ manifest K8s được tổ chức theo chuẩn **Kustomize** tại thư mục `deploy/k8s/`:

```
deploy/k8s/
├── base/                          # Cấu hình gốc dùng chung
│   ├── account.yaml               # ServiceAccount clinic-app-sa
│   ├── autoscaling.yaml           # HPA (API) + KEDA ScaledObject (Worker)
│   ├── deployments.yaml           # Deployment: api, publisher, worker, frontend
│   ├── ingress.yaml               # Ingress routing + TLS cert-manager
│   ├── kustomization.yaml         # Base kustomization
│   ├── migration.yaml             # K8s Job chạy alembic upgrade head
│   ├── networkpolicy.yaml         # Giới hạn ingress/egress giữa các pod
│   ├── nginx.conf                 # ConfigMap cấu hình Nginx frontend
│   ├── services.yaml              # ClusterIP services cho các component
│   └── statefulsets.yaml          # StatefulSet lưu trữ cho postgres & rabbitmq
├── bootstrap/                     # Khởi tạo cụm ban đầu
│   ├── local-ca.yaml              # cert-manager ClusterIssuer & self-signed CA
│   └── namespaces-rbac.yaml       # Namespace clinic-staging, clinic-prod & RBAC
└── overlays/                      # Tách biệt 2 môi trường theo đề bài
    ├── staging/                   # 1 replica API, tài nguyên tối thiểu để test
    └── production/                # >= 2 replica API, HPA min 2 max 5, PVC riêng
```

### Chi tiết các thành phần chính:

1. **Liveness & Readiness Probes:**
   - `api`: `/health` (liveness) và `/ready` (readiness) qua HTTP cổng 8000.
   - `publisher`: HTTP check `/health` cổng 8001.
   - `worker`: HTTP check `/health` cổng 8002.
2. **Resource Requests & Limits:**
   - Mỗi pod đều khai báo rõ ràng `cpu` và `memory` requests/limits nhằm đảm bảo QoS và giúp HPA tính toán chính xác ngưỡng tải.
3. **Autoscaling:**
   - **HPA (Horizontal Pod Autoscaler):** Scale `clinic-api` từ 2 đến 5 pod khi CPU trung bình vượt ngưỡng 60%.
   - **KEDA ScaledObject:** Kích hoạt bởi trigger `rabbitmq`, theo dõi queue `clinic.dev.email` (hoặc prefix theo env). Khi queue depth > 20 messages, KEDA tự động tăng `clinic-worker` từ 1 lên tối đa 5 pod để giải tỏa backlog; khi hết task tự scale down về 1.
4. **Bảo mật RBAC & TLS (Bài 11):**
   - Pod chạy bằng ServiceAccount `clinic-app-sa` với quyền `automountServiceAccountToken: false` (ngăn pod đánh cắp K8s API token).
   - Role và RoleBinding trong `namespaces-rbac.yaml` chỉ cấp quyền tối thiểu trong namespace riêng, không dùng quyền `cluster-admin`.
   - Ingress sử dụng TLS với chứng chỉ sinh bởi cert-manager.

---

## 3. Điều kiện phụ thuộc để Triển khai Runtime

Để cụm Kubernetes có thể chạy thật (thoát khỏi trạng thái `IMPLEMENTED_NOT_RUN` sang `VERIFIED`), cần các điều kiện bàn giao từ các thành viên khác:

1. **Từ TV3 (Long - Host & IaC):** Cung cấp cụm k3s gồm 2 node (1 Server, 1 Agent) ở trạng thái `Ready` thông qua Ansible role `k3s`.
2. **Từ TV2 (Vuong - CI/Registry):** Cung cấp digest Docker images đã build và scan sạch CRITICAL lỗ hổng trên GHCR (`ghcr.io/vxxngw/...`), kèm secret `regcred` để pull image.
3. **Secret môi trường:** Chạy script `scripts/prepare-cluster-secrets.py` để sinh Secret DB, RabbitMQ, JWT riêng biệt cho từng namespace `staging` và `production`.

---

## 4. Các Lệnh Kiểm tra và Đánh giá (Verification Commands)

### 4.1. Kiểm tra tĩnh cú pháp Kustomize (Chạy ngay không cần cluster)

```bash
# Kiểm tra build manifest môi trường staging
kubectl kustomize deploy/k8s/overlays/staging

# Kiểm tra build manifest môi trường production
kubectl kustomize deploy/k8s/overlays/production
```

### 4.2. Lệnh kiểm tra trên Cụm K8s thực tế (Khi có cluster)

```bash
# 1. Khởi tạo namespace và RBAC
kubectl apply -f deploy/k8s/bootstrap/namespaces-rbac.yaml
kubectl apply -f deploy/k8s/bootstrap/local-ca.yaml

# 2. Triển khai staging
kubectl apply -k deploy/k8s/overlays/staging

# 3. Kiểm tra pod, service, ingress, probes
kubectl get pods,svc,ingress,hpa -n clinic-staging
kubectl describe pod -l app=clinic-api -n clinic-staging

# 4. Kiểm tra phân quyền tối thiểu (RBAC test)
kubectl auth can-i create pods --as=system:serviceaccount:clinic-staging:clinic-app-sa -n clinic-staging
# Kết quả mong đợi: 'no' (thỏa mãn nguyên tắc đặc quyền tối thiểu)

# 5. Diễn tập Rollback không gián đoạn
python ci/rollback.py --namespace clinic-staging --deployment clinic-api
```

---

## 5. Hiện trạng nghiệm thu & Phần việc tiếp theo

- **Đã đạt (Verified Local / Static):**
  - Cấu hình Kustomize đầy đủ 100% cho cả 2 môi trường.
  - Manifest đạt chuẩn bảo mật (non-root, probes, resource bounds, dropped capabilities).
  - KEDA ScaledObject và HPA đã hoàn thiện cú pháp và unit tests.
  - Script điều phối rollback [ci/rollback.py](../../ci/rollback.py) và runbook [docs/runbooks/rollback.md](../runbooks/rollback.md) đã sẵn sàng.
- **Phần việc tiếp theo (Runtime Lab):**
  - Nhận cụm k3s từ TV3 khi hoàn thành setup máy ảo.
  - Phối hợp cùng TV1 chạy script tạo tải `scripts/infra/load-http.py` và `load-queue.py` để ghi lại biểu đồ co giãn HPA và KEDA phục vụ báo cáo và video demo.
