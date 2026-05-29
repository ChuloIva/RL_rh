"""fal.ai client helpers. Sync run + async concurrent fan-out."""

from __future__ import annotations

import asyncio
import os
import ssl
import time
from pathlib import Path
from typing import Any, Awaitable, Callable

import certifi
import fal_client
import httpx


def _ensure_key() -> None:
    if os.environ.get("FAL_KEY"):
        return
    for alt in ("FAL_AI_API_KEY", "FAL_API_KEY"):
        v = os.environ.get(alt)
        if v:
            os.environ["FAL_KEY"] = v
            return
    raise RuntimeError("FAL_KEY (or FAL_AI_API_KEY / FAL_API_KEY) not set")


def upload(path: str | Path) -> str:
    _ensure_key()
    return fal_client.upload_file(str(path))


def run(model: str, arguments: dict[str, Any], with_logs: bool = False) -> dict[str, Any]:
    """Subscribe-style call: blocks until the result is ready."""
    _ensure_key()
    return fal_client.subscribe(
        model,
        arguments=arguments,
        with_logs=with_logs,
    )


def submit(model: str, arguments: dict[str, Any]):
    _ensure_key()
    return fal_client.submit(model, arguments=arguments)


def _ssl_ctx() -> ssl.SSLContext:
    return ssl.create_default_context(cafile=certifi.where())


def download(url: str, dest: str | Path) -> Path:
    dest = Path(dest)
    dest.parent.mkdir(parents=True, exist_ok=True)
    with httpx.Client(verify=_ssl_ctx(), timeout=120.0, follow_redirects=True) as c:
        r = c.get(url)
        r.raise_for_status()
        dest.write_bytes(r.content)
    return dest


def run_with_retry(
    model: str,
    arguments: dict[str, Any],
    attempts: int = 3,
    backoff: float = 5.0,
) -> dict[str, Any]:
    last: Exception | None = None
    for i in range(attempts):
        try:
            return run(model, arguments)
        except Exception as e:  # noqa: BLE001
            last = e
            if i == attempts - 1:
                break
            time.sleep(backoff * (i + 1))
    raise RuntimeError(f"fal run failed after {attempts} attempts: {last}") from last


# ---------- Async / concurrent ----------

async def _arun_one(
    model: str,
    arguments: dict[str, Any],
    attempts: int = 3,
    backoff: float = 5.0,
) -> dict[str, Any]:
    last: Exception | None = None
    for i in range(attempts):
        try:
            return await fal_client.subscribe_async(model, arguments=arguments)
        except Exception as e:  # noqa: BLE001
            last = e
            if i == attempts - 1:
                break
            await asyncio.sleep(backoff * (i + 1))
    raise RuntimeError(f"fal run failed after {attempts} attempts: {last}") from last


async def _aupload(path: str | Path) -> str:
    return await fal_client.upload_file_async(str(path))


async def arun_many(
    jobs: list[dict[str, Any]],
    concurrency: int = 8,
    on_done: Callable[[int, dict[str, Any]], Awaitable[None] | None] | None = None,
) -> list[dict[str, Any]]:
    """Run many fal jobs concurrently, capped at `concurrency` in flight.

    Each `jobs[i]` is {"model": str, "arguments": dict, "label": str (optional)}.
    Returns results in the same order as `jobs`.

    If `on_done` is provided, it's called as each job completes with (index, result)
    so callers can persist progress to disk without waiting for all jobs.
    """
    _ensure_key()
    sem = asyncio.Semaphore(concurrency)
    results: list[dict[str, Any] | None] = [None] * len(jobs)

    async def _one(idx: int) -> None:
        async with sem:
            label = jobs[idx].get("label") or f"job-{idx}"
            print(f"[fal] start {label}")
            t0 = time.time()
            res = await _arun_one(jobs[idx]["model"], jobs[idx]["arguments"])
            print(f"[fal] done  {label} ({time.time()-t0:.1f}s)")
            results[idx] = res
            if on_done is not None:
                maybe = on_done(idx, res)
                if asyncio.iscoroutine(maybe):
                    await maybe

    await asyncio.gather(*[_one(i) for i in range(len(jobs))])
    return [r for r in results if r is not None]  # type: ignore[return-value]


async def aupload_many(paths: list[str | Path],
                       concurrency: int = 8) -> list[str]:
    """Upload many files concurrently, return URLs in input order."""
    _ensure_key()
    sem = asyncio.Semaphore(concurrency)

    async def _one(p):
        async with sem:
            return await _aupload(p)

    return await asyncio.gather(*[_one(p) for p in paths])
