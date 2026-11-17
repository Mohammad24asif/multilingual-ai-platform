"""A single-worker inference executor with a bounded queue, timeouts and cooperative cancellation.

Why this exists (ADR-004): model inference is CPU/GPU-heavy and blocking. Running it inside an async
request handler freezes the whole server, and running it in many threads or processes loads many copies
of the model into RAM. Instead exactly one worker thread owns all model work; the API awaits results.

* The queue is bounded: when it is full ``submit`` raises ``QueueFullError`` immediately (HTTP 503 with
  Retry-After) instead of letting latency grow without limit.
* A job that is still waiting when its request times out or the client disconnects is dropped, never run.
* A running job cannot be killed (Python threads), so jobs receive a ``CancelToken`` and check it between
  batches; the worst-case overrun is one batch.
"""

from __future__ import annotations

import asyncio
import queue
import threading
import time
from collections.abc import Callable
from concurrent.futures import Future
from dataclasses import dataclass
from typing import Generic, TypeVar

from ..core.errors import InferenceError, InferenceTimeoutError, JobCancelledError, QueueFullError

T = TypeVar("T")
_STOP = object()


class CancelToken:
    __slots__ = ("_event",)

    def __init__(self) -> None:
        self._event = threading.Event()

    def cancel(self) -> None:
        self._event.set()

    @property
    def cancelled(self) -> bool:
        return self._event.is_set()

    def raise_if_cancelled(self) -> None:
        if self._event.is_set():
            raise JobCancelledError("The request was cancelled before it finished.")


@dataclass(frozen=True, slots=True)
class JobResult(Generic[T]):
    value: T
    queued_s: float
    run_s: float


@dataclass(frozen=True, slots=True)
class ExecutorStats:
    queue_depth: int
    queue_capacity: int
    running: bool
    completed: int
    failed: int
    rejected: int
    cancelled: int


@dataclass(slots=True)
class _Job:
    fn: Callable[[CancelToken], object]
    token: CancelToken
    future: Future
    enqueued_at: float


class InferenceExecutor:
    def __init__(self, *, queue_size: int = 8, name: str = "inference-worker", on_thread_start: Callable[[], None] | None = None) -> None:
        if queue_size < 1:
            raise ValueError("queue_size must be >= 1")
        self._queue: queue.Queue[object] = queue.Queue(maxsize=queue_size)
        self._capacity = queue_size
        self._name = name
        self._on_thread_start = on_thread_start
        self._thread: threading.Thread | None = None
        self._lock = threading.Lock()
        self._closed = False
        self._running = False
        self._completed = self._failed = self._rejected = self._cancelled = 0

    # -- lifecycle ---------------------------------------------------------------------------
    def start(self) -> None:
        with self._lock:
            if self._thread is not None:
                return
            self._thread = threading.Thread(target=self._worker, name=self._name, daemon=True)
            self._thread.start()

    @property
    def alive(self) -> bool:
        return self._thread is not None and self._thread.is_alive() and not self._closed

    def shutdown(self, *, timeout: float = 5.0) -> None:
        with self._lock:
            if self._closed:
                return
            self._closed = True
        while True:  # drop everything still waiting
            try:
                item = self._queue.get_nowait()
            except queue.Empty:
                break
            if isinstance(item, _Job):
                item.token.cancel()
                item.future.cancel()
        self._queue.put_nowait(_STOP)
        if self._thread is not None:
            self._thread.join(timeout)

    # -- submission --------------------------------------------------------------------------
    def submit(self, fn: Callable[[CancelToken], T]) -> tuple[Future, CancelToken]:
        if self._thread is None or self._closed:
            raise InferenceError("The inference worker is not running.", code="executor_not_running")
        token = CancelToken()
        future: Future = Future()
        job = _Job(fn, token, future, time.monotonic())
        try:
            self._queue.put_nowait(job)
        except queue.Full:
            with self._lock:
                self._rejected += 1
            raise QueueFullError(
                "The server is busy translating other requests. Try again shortly.",
                extra={"retry_after": 5, "queue_capacity": self._capacity},
            ) from None
        return future, token

    async def run(self, fn: Callable[[CancelToken], T], *, timeout: float | None = None) -> JobResult[T]:
        future, token = self.submit(fn)
        try:
            return await asyncio.wait_for(asyncio.wrap_future(future), timeout)
        except TimeoutError:
            token.cancel()
            raise InferenceTimeoutError(
                f"Inference did not finish within {timeout:g} seconds.", extra={"timeout_s": timeout}
            ) from None
        except asyncio.CancelledError:
            token.cancel()
            raise

    def stats(self) -> ExecutorStats:
        with self._lock:
            return ExecutorStats(
                queue_depth=self._queue.qsize(),
                queue_capacity=self._capacity,
                running=self._running,
                completed=self._completed,
                failed=self._failed,
                rejected=self._rejected,
                cancelled=self._cancelled,
            )

    # -- worker ------------------------------------------------------------------------------
    def _worker(self) -> None:
        if self._on_thread_start is not None:
            self._on_thread_start()
        while True:
            job = self._queue.get()
            if job is _STOP:
                return
            assert isinstance(job, _Job)
            self._run_job(job)

    def _run_job(self, job: _Job) -> None:
        if not job.future.set_running_or_notify_cancel():
            with self._lock:
                self._cancelled += 1
            return
        if job.token.cancelled:
            job.future.set_exception(JobCancelledError("The request was cancelled before it started."))
            with self._lock:
                self._cancelled += 1
            return
        started = time.monotonic()
        with self._lock:
            self._running = True
        try:
            value = job.fn(job.token)
        except BaseException as exc:  # noqa: BLE001 - delivered to the awaiting caller
            job.future.set_exception(exc)
            with self._lock:
                self._failed += 1
        else:
            job.future.set_result(JobResult(value, started - job.enqueued_at, time.monotonic() - started))
            with self._lock:
                self._completed += 1
        finally:
            with self._lock:
                self._running = False
