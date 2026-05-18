#
# Copyright (c) 2026 CESNET z.s.p.o.
#
# oarepo-related-resources is free software; you can redistribute it and/or modify it
# under the terms of the MIT License; see LICENSE file for more details.
#
"""HTTP session helpers with retry and throttling support."""

from __future__ import annotations

import time
from typing import Any

import requests
from flask import current_app
from invenio_vocabularies.contrib.common.utils import invenio_user_agent  # type: ignore[import-not-found]
from requests.adapters import HTTPAdapter
from urllib3 import Retry


class ThrottledSession(requests.Session):
    """Requests session with throttling to limit request rate."""

    def __init__(self, min_interval: float = 0.0):
        """Initialize with ``min_interval`` minimum seconds between requests."""
        super().__init__()
        self.min_interval = min_interval
        self._last_request_ts = 0.0

    def request(self, *args: Any, **kwargs: Any) -> requests.Response:
        """Sleep until ``min_interval`` has elapsed since the last call, then dispatch the request."""
        now = time.monotonic()
        elapsed = now - self._last_request_ts

        if elapsed < self.min_interval:
            time.sleep(self.min_interval - elapsed)

        self._last_request_ts = time.monotonic()

        return super().request(*args, **kwargs)


def create_session_with_retries(
    total_retries: int = 4,
    status_forcelist: list[int] | None = None,
    backoff_factor: float = 0.3,
    respect_retry_after_header: bool = True,
    throttle_sleep: float = 0.0,
    **kwargs: Any,
) -> requests.Session:
    """Create a ThrottledSession wired with a urllib3 Retry strategy.

    :param total_retries: maximum number of retry attempts.
    :param status_forcelist: HTTP status codes that trigger a retry; defaults
        to ``[413, 429, 500, 502, 503]``.
    :param backoff_factor: backoff factor applied between retries.
    :param respect_retry_after_header: whether to honor the ``Retry-After`` header.
    :param throttle_sleep: minimum interval (seconds) between requests on the session.
    :param kwargs: forwarded to ``urllib3.Retry``.
    :return: a configured ``ThrottledSession``.
    """
    if status_forcelist is None:
        status_forcelist = [413, 429, 500, 502, 503]

    retry_strategy = Retry(
        total=total_retries,
        status_forcelist=status_forcelist,
        backoff_factor=backoff_factor,
        redirect=3,
        respect_retry_after_header=respect_retry_after_header,
        **kwargs,
    )
    adapter = HTTPAdapter(max_retries=retry_strategy)
    session = ThrottledSession(min_interval=throttle_sleep)
    session.mount("https://", adapter)
    session.mount("http://", adapter)
    # be polite and set User-Agent and From headers so that we can be contacted if needed
    session.headers.update(
        {"User-Agent": invenio_user_agent(), "From": current_app.config["APP_RDM_ADMIN_EMAIL_RECIPIENT"]}
    )
    return session
