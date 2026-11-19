"""Business HTTP read load for API HPA; never health-route latency or an automatic pass."""

import argparse
import concurrent.futures
import json
import ssl
import time
import urllib.request
from datetime import UTC, datetime
from pathlib import Path
from urllib.parse import urlparse


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--url", required=True)
    parser.add_argument("--password-file", required=True)
    parser.add_argument("--ca-file", required=True)
    parser.add_argument("--email", default="smoke@example.test")
    parser.add_argument("--seconds", type=int, default=60)
    parser.add_argument("--concurrency", type=int, default=16)
    args = parser.parse_args()
    if (
        urlparse(args.url).scheme != "https"
        or urlparse(args.url).hostname != "staging.anuyen.test"
        or not args.email.endswith(".test")
    ):
        raise ValueError("This load generator is restricted to trusted HTTPS staging lab accounts")
    if not 5 <= args.seconds <= 600 or not 1 <= args.concurrency <= 64:
        raise ValueError("Use5–600seconds and1–64clients")
    context = ssl.create_default_context(cafile=args.ca_file)
    base = args.url.rstrip("/")
    body = json.dumps(
        {"email": args.email, "password": Path(args.password_file).read_text().strip()}
    ).encode()
    request = urllib.request.Request(
        base + "/api/auth/login", data=body, headers={"Content-Type": "application/json"}
    )
    with urllib.request.urlopen(request, context=context, timeout=10) as response:
        token = json.load(response)["access_token"]
    headers = {"Authorization": "Bearer " + token}
    with urllib.request.urlopen(
        urllib.request.Request(base + "/api/doctors", headers=headers), context=context, timeout=10
    ) as response:
        doctors = json.load(response)
    if not doctors:
        raise RuntimeError("Prepare synthetic doctor/slot fixtures before load")
    endpoint = base + "/api/doctors/" + doctors[0]["id"] + "/slots"
    started_at = datetime.now(UTC).isoformat()
    started_load = time.monotonic()
    deadline = started_load + args.seconds

    def worker(_):
        durations, errors = [], 0
        while time.monotonic() < deadline:
            started = time.monotonic()
            try:
                with urllib.request.urlopen(
                    urllib.request.Request(endpoint, headers=headers), context=context, timeout=10
                ) as response:
                    response.read()
                durations.append(time.monotonic() - started)
            except Exception:
                errors += 1
        return durations, errors

    with concurrent.futures.ThreadPoolExecutor(max_workers=args.concurrency) as pool:
        results = list(pool.map(worker, range(args.concurrency)))
    durations = sorted(duration for group, _ in results for duration in group)
    errors = sum(count for _, count in results)
    elapsed = time.monotonic() - started_load
    print(
        json.dumps(
            {
                "scope": "Business slots HTTP load only; verify API CPU/HPA separately",
                "started_at_utc": started_at,
                "ended_at_utc": datetime.now(UTC).isoformat(),
                "elapsed_seconds": elapsed,
                "concurrency": args.concurrency,
                "requests": len(durations) + errors,
                "requests_per_second": (len(durations) + errors) / elapsed,
                "successes": len(durations),
                "errors": errors,
                "latency_population": "successful_requests_only",
                "p95_seconds": durations[min(len(durations) - 1, int(len(durations) * 0.95))]
                if durations
                else None,
            }
        )
    )
    return 1 if errors or not durations else 0


if __name__ == "__main__":
    raise SystemExit(main())
