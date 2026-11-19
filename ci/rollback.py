import argparse

from ci.cluster import context
from ci.common import read_json
from ci.deploy import restore_snapshot


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("namespace", choices=["staging", "production"])
    parser.add_argument("snapshot")
    parser.add_argument("--ack-production", action="store_true")
    args = parser.parse_args()
    if args.namespace == "production" and not args.ack_production:
        parser.error("Production rollback requires an explicit --ack-production")
    context(args.namespace)
    from pathlib import Path

    restore_snapshot(args.namespace, read_json(Path(args.snapshot)))


if __name__ == "__main__":
    main()
