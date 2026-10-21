"""Real-mode proxy app: defends with ModSecDefender at the configured paranoia level."""

import os

from proxy.app import create_app
from wafarena.defenders.modsec_defender import ModSecDefender

DEFAULT_PARANOIA_LEVEL = 1

app = create_app(
    ModSecDefender(int(os.environ.get("PROXY_PARANOIA_LEVEL", DEFAULT_PARANOIA_LEVEL)))
)
