# Giữ hàng đợi CI khi Windows gần hết dung lượng

Áp dụng cho Jenkins riêng của An Uyên tại `http://localhost:18090`, folder `an-uyen`, job `clinic-pipeline`. Jenkins cũ cổng8080 không thuộc phạm vi. [Bằng chứng 16/11/2026](../evidence/ci-queue-hold-20261115T210140Z/README.md) ghi lần thực hiện thật; runbook không xác nhận CI của head mới đã đạt.

## Khi nào giữ build

Nếu ổ hệ điều hành gần đầy, giữ việc cấp executor trước khi push vì webhook push tự xếp build. Docker data ở D vẫn cần dung lượng cho Windows/log/pagefile trên C. Ngưỡng mở lại **C≥5GiB, D≥3GiB** là giới hạn vận hành nhóm chọn, không phải mức phần cứng của PDF và không chứng minh đủ tài nguyên cho 3 VM.

Jenkins có API [quietDown/cancelQuietDown](https://javadoc.jenkins.io/jenkins/model/Jenkins.html#doQuietDown(boolean,int,java.lang.String,boolean)) để giữ việc bắt đầu build mới. Không gọi shutdown/safeRestart, không disable job, không xóa queue hoặc bỏ security gate. Banner/queue có thể hiện `Jenkins is about to shut down`; trong lần thực hiện này chỉ đặt quiet-down, không gửi lệnh tắt dịch vụ.

Trước khi giữ: đọc root jobs, kiểm controller chỉ có folder dự án, job có ownership marker của bootstrap, không có build đang chạy, không có quiet-down của người khác. Thao tác thực tế: POST `/quietDown` với `block=false`, `timeout=0`, `safeRestart=false` và reason dưới đây; đọc lại `quietingDown=true` cùng reason. Không in credential hay gọi bootstrap `init/configure` để thay cài đặt trong lúc xử lý dung lượng.

Reason của lần giữ này:

```text
An Uyen: low Windows C disk; hold validation for codex/team-four-handoff until C has >=5 GiB free. Build gates remain pending.
```

Đọc lại `quietingDown` và reason ngay trước mỗi push, kể cả sau khởi động lại controller; không giả định hold vẫn còn hiệu lực. Sau push, kiểm remote SHA, webhook HTTP202 và queue có đúng `SOURCE_REF`/`SOURCE_BRANCH`. Queue chờ không phải build đạt. `PUBLISH_IMAGES=false`, `DEPLOY=false` của nhánh tài liệu vẫn phải giữ; GHCR credential chưa có không ngăn lượt validation này nhưng vẫn chặn publish image.

## Mở lại sau khi dung lượng đã đủ

Đo C/D thực tế, không coi câu trả lời “sẽ giải phóng” là đã đủ. Không tự xóa dữ liệu cá nhân, backup Docker, state hoặc volume. Nếu reason đã đổi, controller có job ngoài dự án, agent offline hoặc queue có nhánh/publish/deploy ngoài phạm vi, dừng và xác minh người vận hành.

Đoạn sau chạy từ repo root bằng Python của Windows; chỉ mở lại lượt giữ đúng reason và build validation của nhánh này. Nó đọc credential cục bộ qua bootstrap, không in giá trị. **Chưa chạy bước mở lại ở thời điểm viết runbook**, vì dung lượng chưa đạt.

```powershell
@'
import importlib.util
import shutil
from pathlib import Path

root = Path.cwd().resolve()
assert (root / "Jenkinsfile").is_file() and (root / "pyproject.toml").is_file()
assert shutil.disk_usage("C:/").free >= 5 * 1024**3, "C needs >=5GiB free"
assert shutil.disk_usage("D:/").free >= 3 * 1024**3, "D needs >=3GiB free"
spec = importlib.util.spec_from_file_location("bootstrap_ci", root / "scripts/ci/bootstrap-ci.py")
bootstrap = importlib.util.module_from_spec(spec)
spec.loader.exec_module(bootstrap)
controller = bootstrap.Controller()
state = controller.request("GET", "/api/json", params={"tree": "quietingDown,quietDownReason,jobs[name]"}).json()
assert [job["name"] for job in state["jobs"]] == ["an-uyen"]
assert state["quietingDown"] is True
expected = "An Uyen: low Windows C disk; hold validation for codex/team-four-handoff until C has >=5 GiB free. Build gates remain pending."
assert state["quietDownReason"] == expected, "Another operator owns this hold"
assert bootstrap.OWNER in controller.request("GET", "/job/an-uyen/job/clinic-pipeline/config.xml").text
agent = controller.request("GET", "/computer/clinic-ci-linux/api/json", params={"tree": "offline"}).json()
assert agent["offline"] is False
queue = controller.request("GET", "/queue/api/json", params={"tree": "items[task[name],actions[parameters[name,value]]]"}).json()
for item in queue.get("items", []):
    values = {p["name"]: p.get("value") for a in item.get("actions", []) for p in a.get("parameters", [])}
    assert item["task"]["name"] == "clinic-pipeline"
    assert values.get("SOURCE_BRANCH") == "codex/team-four-handoff"
    assert values.get("PUBLISH_IMAGES") in (False, "false")
    assert values.get("DEPLOY") in (False, "false")
controller.request("POST", "/cancelQuietDown")
after = controller.request("GET", "/api/json", params={"tree": "quietingDown"}).json()
assert after["quietingDown"] is False
print("Scheduling resumed; validation results are still pending")
'@ | .\.venv\Scripts\python.exe -
```

Sau mở lại, theo dõi queue → build number → đúng commit → kết quả từng stage/JUnit/security report. Giữ trạng thái pending/failure nếu chưa đạt; không lấy Jenkins14 của commit cũ làm kết quả cho head hiện tại. Ghi receipt mới trước khi nâng ma trận hoặc chốt Mốc2. Nhánh main vẫn cần bảo vệ, PR/review và semver thật theo [quy trình nhóm](../guides/team-workflow.md).
