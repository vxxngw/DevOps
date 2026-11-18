# Kiểm tra Linux sau refactor – 15/11/2026

[Metadata](metadata.json) ghi source chính xác `0bd3fb303f50999a54d08648f2c7d9a83edc6188`. Source được xuất bằng Git archive, giữ SHA256/size, rồi đưa vào thư mục riêng **có khoảng trắng** trên Jenkins agent Linux đang rảnh. Chạy với UID 1000, dùng Python/pytest đã cài sẵn; không cài package hay build/pull image mới, không thay workspace của Jenkins.

- [18 test liên quan](unit-targeted.log), [JUnit](junit.xml): tất cả đạt trên Linux, gồm bảo vệ restore, path Ansible, Bash và các dạng cast schema. Đây là test riêng cho thay đổi, không thay full suite 110/8 skip trên Windows hoặc integration 33 case của baseline Jenkins trước đó.
- [Đối chiếu source thực](actual-source-paths.log): **7 source Ansible** có thật, **6 file Bash** đều parse thành công bằng `/usr/bin/bash`, mỗi file một lệnh. Không dùng mock ở lượt kiểm source thực này.

Đây là lệnh kiểm tra trực tiếp trong container agent hiện có, **không phải Jenkins build**. Không tạo DB/VM/cluster, không chạy timer, không kiểm Ansible convergence/idempotency hay push GHCR. Source snapshot nhỏ được giữ ở đường dẫn riêng trong metadata, không chứa env, credential hoặc dump DB.
