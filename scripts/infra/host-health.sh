#!/usr/bin/env bash
# Linux host health only (memory, root disk, load); exit 1 when any threshold fails.
set -euo pipefail
min_memory=$((256 * 1024 * 1024))
min_disk=$((2 * 1024 * 1024 * 1024))
# MemAvailable needs Linux >= 3.14; fall back to the stricter MemFree (e.g. Git Bash tests).
memory=$(( $(awk '/^MemAvailable:/ {a = $2} /^MemFree:/ {f = $2} END {print (a != "" ? a : f)}' /proc/meminfo) * 1024 ))
disk=$(( $(df -Pk / | awk 'NR == 2 {print $4}') * 1024 ))
read -r load _ < /proc/loadavg
cpus="$(nproc)"
healthy=true
(( memory >= min_memory && disk >= min_disk )) || healthy=false
# Bash has no float math; awk compares the 1-minute load against 2x CPU count.
awk -v l="$load" -v c="$cpus" 'BEGIN { exit !(l < c * 2) }' || healthy=false
printf '{"scope":"Linux host only; not application health","memory_available_bytes":%d,"root_disk_free_bytes":%d,"load1":%s,"cpus":%d,"healthy":%s}\n' \
  "$memory" "$disk" "$load" "$cpus" "$healthy"
[[ "$healthy" == true ]]
