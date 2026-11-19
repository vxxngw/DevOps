#!/usr/bin/env bash
set -euo pipefail
python3 - <<'PY'
import json, os, shutil
memory = dict(line.split(':', 1) for line in open('/proc/meminfo'))
available = int(memory['MemAvailable'].split()[0]) * 1024
disk = shutil.disk_usage('/')
load = os.getloadavg()[0]
healthy = available >= 256 * 1024**2 and disk.free >= 2 * 1024**3 and load < (os.cpu_count() or 1) * 2
print(json.dumps({'scope':'Linux host only; not application health', 'memory_available_bytes':available, 'root_disk_free_bytes':disk.free, 'load1':load, 'healthy':healthy}))
raise SystemExit(0 if healthy else 1)
PY
