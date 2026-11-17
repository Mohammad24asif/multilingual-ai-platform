import io
import json
import logging
import unittest

from app.core.errors import InvalidInputError, QueueFullError
from app.core.logging import JsonFormatter, log_event, redact_fields, request_id_var


class ErrorTests(unittest.TestCase):
    def test_problem_details_shape(self):
        err = QueueFullError("busy", extra={"retry_after": 2})
        body = err.to_problem("req-1")
        self.assertEqual(body["status"], 503)
        self.assertEqual(body["code"], "server_busy")
        self.assertEqual(body["type"], "urn:mlai:error:server_busy")
        self.assertEqual(body["request_id"], "req-1")
        self.assertEqual(body["retry_after"], 2)

    def test_default_detail_and_code_override(self):
        err = InvalidInputError(code="empty_text")
        self.assertEqual(err.code, "empty_text")
        self.assertEqual(err.detail, "Invalid input")


class LoggingTests(unittest.TestCase):
    def _logger(self):
        stream = io.StringIO()
        handler = logging.StreamHandler(stream)
        handler.setFormatter(JsonFormatter())
        logger = logging.getLogger("test.privacy." + str(id(stream)))
        logger.handlers[:] = [handler]
        logger.setLevel(logging.INFO)
        logger.propagate = False
        return logger, stream

    def test_content_fields_are_redacted(self):
        fields = redact_fields({"text": "secret words", "model_id": "m", "meta": {"source_text": "abc"}, "n_text": "x", "chars": 5})
        self.assertEqual(fields["text"], "<redacted len=12>")
        self.assertEqual(fields["meta"]["source_text"], "<redacted len=3>")
        self.assertEqual(fields["n_text"], "<redacted len=1>")
        self.assertEqual(fields["model_id"], "m")
        self.assertEqual(fields["chars"], 5)

    def test_json_line_has_request_id_and_never_the_text(self):
        logger, stream = self._logger()
        token = request_id_var.set("rid-9")
        try:
            log_event(logger, logging.INFO, "translate.done", text="ప్రైవేట్ సమాచారం", chars=15, duration_ms=12)
        finally:
            request_id_var.reset(token)
        line = stream.getvalue()
        record = json.loads(line)
        self.assertEqual(record["request_id"], "rid-9")
        self.assertEqual(record["chars"], 15)
        self.assertNotIn("ప్రైవేట్", line)

    def test_exceptions_log_type_and_frames_but_not_the_message(self):
        logger, stream = self._logger()
        try:
            raise ValueError("user said: my password is hunter2")
        except ValueError:
            logger.exception("boom")
        line = stream.getvalue()
        record = json.loads(line)
        self.assertEqual(record["exc_type"], "ValueError")
        self.assertTrue(record["frames"])
        self.assertNotIn("hunter2", line)


if __name__ == "__main__":
    unittest.main()
