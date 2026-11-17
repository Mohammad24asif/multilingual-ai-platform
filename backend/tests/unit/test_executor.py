import asyncio
import threading
import time
import unittest

from app.core.errors import InferenceError, InferenceTimeoutError, JobCancelledError, QueueFullError
from app.inference.executor import InferenceExecutor


class ExecutorTests(unittest.TestCase):
    def setUp(self):
        self.executors: list[InferenceExecutor] = []

    def tearDown(self):
        for ex in self.executors:
            ex.shutdown()

    def make(self, **kwargs) -> InferenceExecutor:
        ex = InferenceExecutor(**kwargs)
        ex.start()
        self.executors.append(ex)
        return ex

    def test_all_jobs_run_on_one_worker_thread_in_fifo_order(self):
        ex = self.make(queue_size=20)
        seen: list[tuple[int, str]] = []
        futures = [ex.submit(lambda tok, n=n: seen.append((n, threading.current_thread().name)) or n)[0] for n in range(10)]
        self.assertEqual([f.result(timeout=2).value for f in futures], list(range(10)))
        self.assertEqual([n for n, _ in seen], list(range(10)))
        self.assertEqual(len({name for _, name in seen}), 1)
        self.assertNotEqual(seen[0][1], threading.current_thread().name)

    def test_queue_is_bounded_and_rejects_immediately_when_full(self):
        ex = self.make(queue_size=2)
        gate = threading.Event()
        started = threading.Event()

        def blocker(tok):
            started.set()
            gate.wait(5)
            return "done"

        running, _ = ex.submit(blocker)
        self.assertTrue(started.wait(2))
        queued = [ex.submit(lambda tok: "q")[0] for _ in range(2)]
        with self.assertRaises(QueueFullError) as ctx:
            ex.submit(lambda tok: "overflow")
        self.assertEqual(ctx.exception.status, 503)
        self.assertIn("retry_after", ctx.exception.extra)
        stats = ex.stats()
        self.assertEqual((stats.queue_depth, stats.queue_capacity, stats.rejected, stats.running), (2, 2, 1, True))
        gate.set()
        self.assertEqual(running.result(2).value, "done")
        self.assertEqual([f.result(2).value for f in queued], ["q", "q"])

    def test_exceptions_reach_the_caller_and_the_worker_survives(self):
        ex = self.make()
        bad, _ = ex.submit(lambda tok: (_ for _ in ()).throw(ValueError("boom")))
        with self.assertRaises(ValueError):
            bad.result(2)
        good, _ = ex.submit(lambda tok: 7)
        self.assertEqual(good.result(2).value, 7)
        self.assertEqual(ex.stats().failed, 1)

    def test_result_reports_queue_and_run_time(self):
        ex = self.make()
        future, _ = ex.submit(lambda tok: time.sleep(0.05))
        result = future.result(2)
        self.assertGreaterEqual(result.run_s, 0.04)
        self.assertGreaterEqual(result.queued_s, 0.0)

    def test_on_thread_start_runs_in_the_worker(self):
        names = []
        ex = self.make(on_thread_start=lambda: names.append(threading.current_thread().name))
        ex.submit(lambda tok: None)[0].result(2)
        self.assertEqual(names, ["inference-worker"])

    def test_submit_after_shutdown_and_pending_jobs_are_dropped(self):
        ex = InferenceExecutor(queue_size=5)
        ex.start()
        gate = threading.Event()
        started = threading.Event()
        ex.submit(lambda tok: (started.set(), gate.wait(5))[1])
        self.assertTrue(started.wait(2))
        pending, _ = ex.submit(lambda tok: "never")
        gate.set()
        ex.shutdown()
        self.assertTrue(pending.cancelled() or pending.done())
        with self.assertRaises(InferenceError):
            ex.submit(lambda tok: 1)
        self.assertFalse(ex.alive)

    def test_invalid_queue_size(self):
        with self.assertRaises(ValueError):
            InferenceExecutor(queue_size=0)

    def test_submit_before_start_raises(self):
        with self.assertRaises(InferenceError):
            InferenceExecutor().submit(lambda tok: 1)


class AsyncBridgeTests(unittest.TestCase):
    def test_run_returns_value_and_timings(self):
        async def scenario():
            ex = InferenceExecutor()
            ex.start()
            try:
                result = await ex.run(lambda tok: 41 + 1, timeout=2)
                self.assertEqual(result.value, 42)
            finally:
                ex.shutdown()

        asyncio.run(scenario())

    def test_timeout_cancels_a_running_job_cooperatively_and_the_worker_recovers(self):
        async def scenario():
            ex = InferenceExecutor()
            ex.start()
            progress = []

            def slow(tok):
                for step in range(50):
                    tok.raise_if_cancelled()
                    progress.append(step)
                    time.sleep(0.02)

            try:
                with self.assertRaises(InferenceTimeoutError):
                    await ex.run(slow, timeout=0.1)
                await asyncio.sleep(0.2)
                self.assertLess(len(progress), 20)  # stopped early instead of running all 50 steps
                self.assertEqual((await ex.run(lambda tok: "ok", timeout=2)).value, "ok")
            finally:
                ex.shutdown()

        asyncio.run(scenario())

    def test_a_job_that_times_out_while_queued_never_runs(self):
        async def scenario():
            ex = InferenceExecutor(queue_size=4)
            ex.start()
            gate = threading.Event()
            ran = []
            blocker = asyncio.create_task(ex.run(lambda tok: gate.wait(3), timeout=5))
            await asyncio.sleep(0.05)
            try:
                with self.assertRaises(InferenceTimeoutError):
                    await ex.run(lambda tok: ran.append(1), timeout=0.05)
                gate.set()
                await blocker
                await asyncio.sleep(0.1)
                self.assertEqual(ran, [])
                self.assertEqual(ex.stats().cancelled, 1)
            finally:
                ex.shutdown()

        asyncio.run(scenario())

    def test_cancelling_the_awaiting_task_cancels_the_job(self):
        async def scenario():
            ex = InferenceExecutor()
            ex.start()
            started = threading.Event()
            seen_cancel = []

            def job(tok):
                started.set()
                for _ in range(100):
                    if tok.cancelled:
                        seen_cancel.append(True)
                        raise JobCancelledError()
                    time.sleep(0.01)

            task = asyncio.create_task(ex.run(job, timeout=10))
            await asyncio.sleep(0.1)
            task.cancel()
            with self.assertRaises(asyncio.CancelledError):
                await task
            await asyncio.sleep(0.2)
            self.assertEqual(seen_cancel, [True])
            ex.shutdown()

        asyncio.run(scenario())


if __name__ == "__main__":
    unittest.main()
