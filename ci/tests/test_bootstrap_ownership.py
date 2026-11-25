import importlib.util
from types import SimpleNamespace

import pytest

from ci.common import ROOT


def bootstrap():
    spec = importlib.util.spec_from_file_location(
        "bootstrap_ownership", ROOT / "scripts/ci/bootstrap-ci.py"
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_moved_bootstrap_can_update_existing_owned_item():
    module = bootstrap()
    controller = module.Controller.__new__(module.Controller)
    existing = "<description>Managed by scripts/bootstrap-ci.py for vxxngw/DevOps</description>"
    controller.client = SimpleNamespace(
        get=lambda path: SimpleNamespace(status_code=200, text=existing)
    )
    calls = []
    controller.request = lambda *args, **kwargs: calls.append((args, kwargs))
    controller.owned_item("/job/an-uyen/job/clinic-pipeline", b"<flow-definition/>")
    assert calls[0][0] == ("POST", "/job/an-uyen/job/clinic-pipeline/config.xml")


def test_moved_bootstrap_still_refuses_foreign_item():
    module = bootstrap()
    controller = module.Controller.__new__(module.Controller)
    controller.client = SimpleNamespace(
        get=lambda path: SimpleNamespace(
            status_code=200, text="<description>Another project</description>"
        )
    )
    with pytest.raises(RuntimeError, match="not owned"):
        controller.owned_item("/job/other", b"<flow-definition/>")


def test_webhook_reuses_previous_quick_tunnel_hook():
    managed_hook = bootstrap().managed_hook
    old = {"id": 1, "config": {"url": "https://old-name.trycloudflare.com/github"}}
    other = {"id": 2, "config": {"url": "https://ci.example.test/hook"}}
    new_endpoint = "https://new-name.trycloudflare.com/github"
    assert managed_hook([other, old], new_endpoint) is old
    same = {"id": 3, "config": {"url": new_endpoint}}
    assert managed_hook([old, same], new_endpoint) is same
    assert managed_hook([other], new_endpoint) is None
