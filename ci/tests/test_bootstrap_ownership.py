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
