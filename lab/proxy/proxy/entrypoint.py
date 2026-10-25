"""Real-mode proxy app.

Defends with ModSecDefender at PROXY_PARANOIA_LEVEL by default. When PROXY_DEFENDER_CHECKPOINT is
set (a checkpoint directory or a reference id under checkpoints/refs/, e.g. DEF-REF-1), it serves
that trained defender instead, through DefenderDriver (the `proxy-learned` service, F3-T10).
"""

import os

from proxy.app import create_app
from wafarena.defenders.modsec_defender import ModSecDefender

DEFAULT_PARANOIA_LEVEL = 1


def _policy():
    checkpoint = os.environ.get("PROXY_DEFENDER_CHECKPOINT")
    if checkpoint:
        from wafarena.envs.resolve import resolve_defender

        return resolve_defender({"type": "checkpoint", "path": checkpoint})
    return ModSecDefender(int(os.environ.get("PROXY_PARANOIA_LEVEL", DEFAULT_PARANOIA_LEVEL)))


app = create_app(_policy())
