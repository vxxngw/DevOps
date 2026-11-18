"""Pin direct Jenkins plugin versions from the official update center; no credentials."""

import json
from datetime import UTC, datetime
from pathlib import Path

import httpx

ROOT = next(
    (
        p
        for p in Path(__file__).resolve().parents
        if (p / "Jenkinsfile").is_file() and (p / "pyproject.toml").is_file()
    ),
    Path.cwd(),
)
NAMES = (
    "workflow-aggregator",
    "git",
    "github",
    "credentials-binding",
    "cloudbees-folder",
    "junit",
    "ws-cleanup",
    "matrix-auth",
    "ssh-slaves",
)


def version_tuple(value):
    return tuple(int(part) for part in value.split(".") if part.isdigit())


def main():
    url = "https://updates.jenkins.io/update-center.actual.json"
    response = httpx.get(url, timeout=60, follow_redirects=True, trust_env=False)
    response.raise_for_status()
    data = response.json()
    controller = json.loads((ROOT / "ci/tools.json").read_text(encoding="utf-8"))["jenkins"]
    plugins = []
    history = None
    for name in NAMES:
        plugin = data["plugins"][name]
        if version_tuple(plugin["requiredCore"]) > version_tuple(controller):
            if history is None:
                previous = httpx.get(
                    "https://updates.jenkins.io/current/plugin-versions.json",
                    timeout=90,
                    follow_redirects=True,
                    trust_env=False,
                )
                previous.raise_for_status()
                history = previous.json()["plugins"]
            compatible = [
                dict(item, name=name, version=version)
                for version, item in history[name].items()
                if version_tuple(item.get("requiredCore", "9999")) <= version_tuple(controller)
            ]
            if not compatible:
                raise RuntimeError("No compatible plugin found: " + name)
            plugin = max(
                compatible, key=lambda item: item.get("releaseTimestamp", item.get("buildDate", ""))
            )
        plugins.append(plugin)
    target = ROOT / "ci/controller/plugins.txt"
    target.write_text(
        "\n".join(plugin["name"] + ":" + plugin["version"] for plugin in plugins) + "\n",
        encoding="utf-8",
    )
    metadata = {
        "at_utc": datetime.now(UTC).isoformat(),
        "source": url,
        "controller": controller,
        "plugins": [
            {key: plugin.get(key) for key in ["name", "version", "requiredCore", "sha256", "url"]}
            for plugin in plugins
        ],
    }
    (ROOT / "ci/controller/plugins-lock.json").write_text(
        json.dumps(metadata, indent=2) + "\n", encoding="utf-8"
    )
    print(
        "Pinned", len(plugins), "direct plugins; transitive versions resolved with --latest=false"
    )


if __name__ == "__main__":
    main()
