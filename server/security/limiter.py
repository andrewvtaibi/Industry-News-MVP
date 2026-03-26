# server/security/limiter.py
# Rate limiter configuration using slowapi.
# Inputs:  RATE_LIMIT_PER_MINUTE env var (default 30)
# Outputs: configured Limiter instance imported by server/main.py

from __future__ import annotations

import os
from slowapi import Limiter
from slowapi.util import get_remote_address

_rate = os.environ.get("RATE_LIMIT_PER_MINUTE", "30")
_limit_string = f"{_rate}/minute"

limiter = Limiter(
    key_func=get_remote_address,
    default_limits=[_limit_string],
)
