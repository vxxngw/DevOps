# Ngân sách tài nguyên – thiết kế, chưa đo workload

Host khảo sát Windows11Home RAM16,87GB; WSL khoảng8GiB, D khoảng49GiB ở đầuM3. KVM có nhưng user chưa có quyền, libvirt/QEMU chưa cài. Preflight thực tại evidenceM3, không coi các giá trị dưới là benchmark.

Profile duy nhất trong infra/lab-budget.json được Terraform/preflight cùng đọc:

| VM | RAM | vCPU | Diskảo | Trách nhiệm |
|---|---|---|---|---|
| Jenkins | 6GiB |2|32GiB|Controller/agent/rootlessengine, compose.ci.vm hardlimit5GiB+OSreserve|
| k3sserver |4GiB|2|48GiB|Controlplane/workloads và backup ngoàiDBnode|
| k3sagent |8GiB|4|48GiB|StoragePVC+workloads|

VMtổng18GiB/8vCPU/128GiBdisk. Dự trù host32GiB RAM,160GiBdisktrống (VMcapacity+base/cache/backupreserve), cần đo lại; không phải requirementphầncứng PDF. Máy hiện tại chưa đủ. Sparseqcow2 không chứng minh đủ capacity khi data/cache tăng. DB labPVC2GiB/namespace; Rabbit2GiB/namespace; backupretention7ngày phải đo kíchthước và freecapacity server, xuất offVM trước teardown.

Ứng dụng2 namespace theo requests hiện tại: khoảng2,75GiB ở API2/worker1; khoảng4,5GiB ở API5/worker5. Dự phòng Mốc 4 khoảng3GiB requests cho EFK/Prometheus/Grafana/Alertmanager/exporters, cộng K3sOS/operator và rolloutsurge. Đây là dự trù, chưa chọn/bật đầy đủM4. Limits có overcommit, không hứa tất cảpod đạt limit đồng thời; requestsfit không chứng minh HPA/KEDAmax hoạt động. Phải đo memory/CPU/allocatable/pending/OOM và điều chỉnh trước nghiệm thu, không bỏ EFK/monitoring khỏi ngân sách để báo đủ.

1server+1agent và DB/broker1 replica khôngHA. Demo xóaAPIpod không tương đương chịu lỗi controlplane/node/storage. Chưa có load/p95/scale hoặc peakM4 để công bố.


## Profile monitoring/EFK Mốc 4 đã chọn – vẫn là thiết kế

Requests RAM: Prometheus384MiB, Grafana256MiB, Alertmanager64 MiB, KSM96MiB, PostgreSQL exporter2×64 MiB, Elasticsearch1024MiB, Kibana512MiB, Fluentd2×128MiB = **2720MiB, khoảng2,66GiB**. Cộng profile app2,75GiB nền/4,5GiB max thành khoảng5,41GiB/7,16GiB requests, chưa gồm OS/k3s/operator/rollout surge. Limits tổng có overcommit; không cam kết workload cùng chạm limit hoặc scale tối đa đủ tài nguyên.

PVC M4: Prometheus4GiB, Grafana1GiB, Alertmanager1GiB, Elasticsearch6GiB =12GiB, cộng8GiB app DB/broker hai môi trường. Buffer Fluentd≤64 MiB/node, log/TSDB retention7ngày cần đo tốc độ sinh thực; image layers và backup/cache còn dùng disk riêng. Agent48GiB là thiết kế cần kiểm free sau pull ảnh; không nghiệm thu chỉ từ PVC nhỏ. VM/host vẫn thiếu tài nguyên trên máy hiện tại. Không deploy/scan ảnh lớn vào ổ C gần đầy trong phiên chuẩn bị.
