# Ước tính chuyển lên cloud – tra giá, chưa thuê dịch vụ

[ĐỀ BÀI] PDF trang 3 yêu cầu bảng ước tính nếu chọn local. [THIẾT KẾ] phương án tham chiếu DigitalOcean, region SGP1/Singapore; không thay quyết định dùng lab libvirt, không tạo tài khoản/tài nguyên hay phát sinh chi phí. Giá USD tra ngày **14/11/2026**, chưa thuế, không dùng free trial/credit. [Bằng chứng nguồn và phép tính](evidence/cloud-cost-latest.json).

Giả định chạy cả 3 VM liên tục730 giờ/tháng và áp trần tháng của gói Basic Regular: Jenkins cần6GiB nên làm tròn8GiB; server4GiB; agent8GiB. Chưa benchmark cloud. [Bảng giá compute](https://www.digitalocean.com/pricing/droplets) và [catalog region](https://docs.digitalocean.com/products/droplets/details/availability/) xác nhận Basic có tại SGP1, chưa kiểm stock/quota tài khoản.

| Hạng mục | Cấu hình/giả định | Đơn giá | Thành tiền/tháng |
|---|---|---|---:|
| Jenkins VM | Ubuntu24.04,4vCPU/8GiB/160GiB SSD | $0.07143/giờ, trần$48/tháng | $48.00 |
| k3s server | Ubuntu24.04,2vCPU/4GiB/80GiB SSD | $0.03571/giờ, trần$24/tháng | $24.00 |
| k3s agent | Ubuntu24.04,4vCPU/8GiB/160GiB SSD | $0.07143/giờ, trần$48/tháng | $48.00 |
| Backup VM hằng tuần | Cả3 VM; không thay pg_dump ứng dụng | 20% × $120 | $24.00 |
| Volume dữ liệu | Standard100GiB riêng cho PVC; root SSD ở trên là OS/cache | $0.10/GiB/tháng | $10.00 |
| Regional HTTP LB | 1node, dự kiến80/443, cần thiết kế TLS khi chuyển | $12/node/tháng | $12.00 |
| Spaces Standard | Backup pg_dump/state đã mã hóa; ≤250GiB và≤1024GiB egress/tháng | Gói$5/tháng | $5.00 |
| IP/DNS | IP gắn tài nguyên, DNS zone; không giữ IPv4 rời | Không cộng thêm trong giả định | $0.00 |
| **Tổng hạ tầng DO trước thuế** | **$120 + $24 + $10 + $12 + $5** | | **$171.00** |

Nguồn đơn giá: [backup](https://docs.digitalocean.com/products/backups/details/pricing/), [volume](https://docs.digitalocean.com/products/volumes/details/pricing/), [LB](https://docs.digitalocean.com/products/networking/load-balancers/details/pricing/), [Spaces](https://docs.digitalocean.com/products/spaces/details/pricing/), [IP](https://docs.digitalocean.com/products/networking/reserved-ips/details/pricing/), [DNS](https://docs.digitalocean.com/products/networking/dns/details/pricing/). Daily VM backup30% thay weekly20% sẽ thêm$12/tháng. Dự phòng20% do nhóm tự chọn làm ngân sách khoảng$205.20, không phải đơn giá nhà cung cấp.

Egress Droplet giả định trong allowance gộp của các VM; phần vượt tính$0.01/GiB theo [billing](https://docs.digitalocean.com/platform/billing/bandwidth/). Spaces vượt250GiB tính$0.02/GiB/tháng, vượt transfer tính$0.01/GiB. Ước lượng backup7ngày cho2 môi trường phải đo dung lượng thực; bảng không cam kết dump luôn nhỏ. IPv4 reserved không gắn Droplet có thể bị tính$5/tháng, nên không tính nó là miễn phí vô điều kiện. Tắt nguồn Droplet vẫn không đồng nghĩa ngừng tính phí tài nguyên đã giữ.

**Ngoài tổng:** đăng ký domain (giả định đã sở hữu), SMTP ngoài, gói/quota GHCR/GitHub thực, thuế, excess usage và công vận hành. Chưa có thông tin tài khoản để tính các mục này; $171 là ước tính hạ tầng theo giả định, không phải hóa đơn trọn gói hay khẳng định cloud miễn phí.

Chuyển cloud còn cần provider Terraform DigitalOcean, VPC/firewall/SSH, DNS domain hợp lệ, certificate issuer phù hợp, thiết lập volume/StorageClass, backup offsite/restore và webhook/Jenkins ingress an toàn. Repo hiện chỉ có libvirt local; bảng giá không chứng minh các cấu hình cloud này tồn tại. Ba VM này vẫn có1 control plane và DB/broker1 replica, không HA. Đo allocatable/requests/limits/disk thực trước nghiệm thu; resource-budget.md là ước lượng.
