#
# Copyright (c) 2025 CESNET z.s.p.o.
#
# oarepo-related-resources is free software; you can redistribute it and/or modify it
# under the terms of the MIT License; see LICENSE file for more details.
#

"""Utility functions for Related resources import module."""

from __future__ import annotations

import time
from typing import Any

import click
import requests
from bs4 import BeautifulSoup
from rapidfuzz import fuzz
from requests import Response
from requests.adapters import HTTPAdapter
from urllib3.util import Retry

HTTP_OK = 200
HTTP_FORBIDDEN = 403
HTTP_NOT_FOUND = 404
HTTP_GONE = 410

RETRY_STATUS_CODES = [413, 429, 500, 502, 503]


class ThrottledSession(requests.Session):
    """Requests session with throttling to limit request rate."""

    def __init__(self, min_interval: float = 0.0):
        """min_interval: minimum seconds between requests."""
        super().__init__()
        self.min_interval = min_interval
        self._last_request_ts = 0.0

    def request(self, *args: Any, **kwargs: Any) -> requests.Response:
        """Create the request."""
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
    """Create a requests session with retry strategy.

    :param total_retries: Maximum number of retry attempts
    :param status_forcelist: List of HTTP status codes to retry on
    :param backoff_factor: Backoff factor for retries (delay between retries)

    :return: Configured requests session with automatic retries
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
        {
            "User-Agent": "CESNET - NMA Harvesting module/1.0 nrp-repo_L3@eosc.cz",
            "From": "nrp-repo_L3@eosc.cz",
        }
    )
    return session


def extract_text_from_html(html_content: str) -> str:
    """Extract plain text from HTML content.

    :param html_content: HTML content as string

    :return: Extracted plain text
    """
    try:
        soup = BeautifulSoup(html_content, "html.parser")
        # Remove script and style elements
        for script in soup(["script", "style"]):
            script.decompose()

        # Get text and clean it up
        text = soup.get_text()
        # Break into lines and remove leading/trailing space on each
        lines = (line.strip() for line in text.splitlines())
        # Break multi-headlines into a line each
        chunks = (phrase.strip() for line in lines for phrase in line.split("  "))
        # Drop blank lines

        return " ".join(chunk for chunk in chunks if chunk)

    except Exception as e:  # noqa: BLE001
        return f"[Could not extract text: {e!s}]"


def is_title_in_content(
    title: str, content: str, token_threshold: int = 75, partial_threshold: int = 85
) -> tuple[bool, str, int]:
    """Check if title appears in content using hybrid matching approach.

    Uses three methods in order of speed:
    1. Exact substring match python built-in
    2. Token-based fuzzy matching
        - split string by words, sort words, and compare with Levenshtein
        - handles word reordering and extra/missing words
    3. Partial substring fuzzy matching (handles typos)
        - takes title and compares using Levenshtein

    :param title: The title to search for
    :param content: The content to search in
    :param token_threshold: Minimum score for token matching (0-100).
    Typically lower than partial_threshold. Score could be diluted by extra words.
    :param partial_threshold: Minimum score for partial matching (0-100)

    :return: tuple: (found, method, score) where:
            - found: True if title was found
            - method: 'exact', 'token', 'partial', or 'none'
            - score: Matching score (0-100)
    """
    if not title or not content:
        return False, "none", 0

    title_clean = title.lower().strip()
    content_clean = content.lower()

    # Method 1: Fast exact match (covers ~60% of cases)
    if title_clean in content_clean:
        return True, "exact", 100

    # Method 2: Token-based matching (handles word reordering and extra words)
    token_score = fuzz.token_sort_ratio(title_clean, content_clean)
    if token_score >= token_threshold:
        return True, "token", int(token_score)

    # Method 3: Partial matching (handles typos in substring)
    partial_score = fuzz.partial_ratio(title_clean, content_clean)
    if partial_score >= partial_threshold:
        return True, "partial", int(partial_score)

    # Not found - return best score for logging
    best_score = max(token_score, partial_score)
    return False, "none", int(best_score)


def _handle_status_code(status_code: int) -> tuple[str, str] | None:
    if status_code == HTTP_FORBIDDEN:
        return "not_accessible", "Access forbidden (HTTP 403)"
    if status_code == HTTP_NOT_FOUND:
        return "not_found", "Resource not found (HTTP 404)"
    if status_code == HTTP_GONE:
        return "not_accessible", "Resource gone (HTTP 410)"
    return None


def _handle_html_response(resp: Response, title_clean: str) -> tuple[str, str]:
    content_type = resp.headers.get("Content-Type", "").lower()

    if "text/html" not in content_type:
        return "success", f"URL is accessible ({content_type})"

    text_content = extract_text_from_html(resp.text)

    if not title_clean:
        return "success", "URL is accessible (no tombstone verification)"

    found, method, score = is_title_in_content(title_clean, text_content)

    if found:
        return "success", f"URL is accessible. Title found in content ({method} match, score: {score})"

    return (
        "warning",
        f"URL accessible but title not found in content."
        f" Possible tombstone/deleted record (best score: {score}). Manual verification recommended",
    )


def check_url_availability(
    url: str, timeout: int = 15, title: str = "", session: requests.Session | None = None
) -> tuple[int | None, str, str]:
    """Check if a URL is available and return its status.

    :param url: The URL to check
    :param timeout: Request timeout in seconds
    :param title: Optional title to verify in content (for tombstone detection)

    :return: tuple: (status_code, status_string, message) where:
            - status_code: HTTP status code or None if request failed
            - status_string is one of: 'success', 'warning', 'not_accessible', 'not_found' or 'error'
            - message is a human-readable description of the result
    """
    session = session or create_session_with_retries()
    status = "error"
    status_code = None
    message = ""

    title_clean = extract_text_from_html(f"<html><body>{title}</body></html>") if title else ""

    def _handle_error(msg_prefix: str, e: Exception) -> tuple[str, str]:
        """Handle request error."""
        click.secho(f"{msg_prefix} checking {url}: {e}", fg="red")
        return "error", f"{msg_prefix}: {e!s}"

    try:
        resp = session.get(url, allow_redirects=True, timeout=timeout)
        status_code = resp.status_code

        if status_code == HTTP_OK:
            status, message = _handle_html_response(resp, title_clean)
        else:
            result = _handle_status_code(status_code)
            if result:
                status, message = result

    except requests.exceptions.Timeout as e:
        status, message = _handle_error(f"Request timeout after {timeout}s", e)
    except requests.exceptions.ConnectionError as e:
        status, message = _handle_error("Connection error", e)
    except requests.exceptions.RequestException as e:
        status, message = _handle_error("Request error", e)
    except Exception as e:  # noqa: BLE001
        status, message = _handle_error("Unexpected error", e)

    return status_code, status, message
