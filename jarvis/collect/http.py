from __future__ import annotations

import time
import requests

UA = "Mozilla/5.0 (compatible; jarvis-digest/0.1; +https://github.com)"


def get(url: str, *, params=None, headers=None, timeout=30, retries=3, sleep=2.0) -> requests.Response:
    h = {"User-Agent": UA}
    if headers:
        h.update(headers)
    last: Exception | None = None
    for i in range(retries):
        try:
            r = requests.get(url, params=params, headers=h, timeout=timeout)
            if r.status_code in (429, 502, 503):
                time.sleep(sleep * (i + 1))
                continue
            return r
        except requests.RequestException as e:  # noqa: PERF203
            last = e
            time.sleep(sleep * (i + 1))
    if last:
        raise last
    return r  # type: ignore[return-value]
