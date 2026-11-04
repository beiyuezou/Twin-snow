"""A miniature Meta Model API, served on localhost, so the Muse route is testable with no key.

It answers on a socket rather than as a stub because the bugs worth finding live in
the transport: the ``Authorization: Bearer`` header, the ``/v1/chat/completions``
path, a 401 that must never be asked twice, a 429 that names the wait it wants, and
a reply that arrives as something that is not JSON at all.
"""

from __future__ import annotations

import json
import socket
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

MODEL = "muse-spark-1.3"
CHAT_PATH = "/v1/chat/completions"


class Reply:
    """One scripted answer: a status, a body, optional headers, or no answer at all."""

    def __init__(self, status: int = 200, payload: dict | None = None, text: str | None = None,
                 headers: dict | None = None, drop: bool = False) -> None:
        self.status = status
        self.payload = payload
        self.text = text
        self.headers = headers or {}
        self.drop = drop

    @property
    def content_type(self) -> str:
        return "application/json" if self.text is None else "text/html"

    @property
    def body(self) -> bytes:
        if self.text is not None:
            return self.text.encode()
        return json.dumps(self.payload if self.payload is not None else {}).encode()


def _chat(*, content: str = "", tool_calls: list | None = None) -> dict:
    message: dict = {"role": "assistant", "content": content}
    if tool_calls:
        message["tool_calls"] = tool_calls
    return {"id": "gen-1", "model": MODEL, "choices": [{"index": 0, "message": message, "finish_reason": "stop"}]}


def _tool_call(name: str, args: dict) -> dict:
    return {"id": "call-1", "type": "function", "function": {"name": name, "arguments": json.dumps(args)}}


def _error(message: str) -> dict:
    return {"error": {"message": message, "type": "invalid_request_error"}}


class FakeMuse:
    key: str = "muse-key"

    def __init__(self, key: str = "muse-key", model: str = MODEL) -> None:
        self.key = key
        self.model = model
        self.replies: list[Reply] = []
        self.paths: list[str] = []
        self.bodies: list[dict] = []
        self.headers: list[dict] = []
        self.rejected: list[str] = []
        self._server: ThreadingHTTPServer | None = None
        self._thread: threading.Thread | None = None

    # ------------------------------------------------------------------ serving

    def start(self) -> str:
        self._server = ThreadingHTTPServer(("127.0.0.1", 0), _make_handler(self))
        # A short poll interval so teardown notices promptly: eighteen fixtures' worth
        # of the default half-second is longer than every assertion in this file.
        self._thread = threading.Thread(target=self._server.serve_forever, kwargs={"poll_interval": 0.05}, daemon=True)
        self._thread.start()
        return self.url

    def stop(self) -> None:
        if self._server is not None:
            self._server.shutdown()
            self._server.server_close()
            self._server = None

    @property
    def url(self) -> str:
        """A base URL in the shape ``ModelConfig`` expects: it appends /chat/completions."""
        assert self._server is not None
        return f"http://127.0.0.1:{self._server.server_address[1]}/v1"

    @property
    def host(self) -> str:
        assert self._server is not None
        return f"127.0.0.1:{self._server.server_address[1]}"

    @property
    def calls(self) -> int:
        return len(self.paths)

    @property
    def last_body(self) -> dict:
        return self.bodies[-1]

    @property
    def tools_asked_for(self) -> set[str]:
        return {t["function"]["name"] for t in self.last_body.get("tools", [])}

    # ---------------------------------------------------------------- scripting

    def tool(self, name: str, args: dict) -> None:
        self.replies.append(Reply(payload=_chat(tool_calls=[_tool_call(name, args)])))

    def narration(self, said: str) -> None:
        self.replies.append(Reply(payload=_chat(content=said)))

    def refuse(self, status: int = 429, *, detail: str = "slow down", retry_after: str | None = None,
               times: int = 1) -> None:
        headers = {"Retry-After": retry_after} if retry_after is not None else {}
        self.replies.extend(Reply(status, payload=_error(detail), headers=headers) for _ in range(times))

    def gibberish(self, status: int = 200, text: str = "<html>502 Bad Gateway</html>") -> None:
        self.replies.append(Reply(status, text=text))

    def silence(self) -> None:
        """Do the work, then hang up: the reply never arrives."""
        self.replies.append(Reply(drop=True))

    # ---------------------------------------------------------------- endpoints

    def respond(self, method: str, path: str, headers: dict, body: bytes) -> Reply:
        self.paths.append(f"{method} {path}")
        if method != "POST":
            return Reply(405, payload=_error("this endpoint only takes POST"))
        if path != CHAT_PATH:
            return Reply(404, payload=_error(f"no such path: {path}"))
        bearer = headers.get("authorization", "")
        if bearer != f"Bearer {self.key}":
            self.rejected.append(bearer)
            return Reply(401, payload=_error("Invalid API key provided"))
        parsed = json.loads(body or b"{}")
        self.bodies.append(parsed)
        self.headers.append(headers)
        if parsed.get("model") != self.model:
            return Reply(404, payload=_error(f"Model '{parsed.get('model')}' is not available"))
        if not self.replies:
            return Reply(500, payload=_error("FakeMuse has nothing scripted for this call"))
        return self.replies.pop(0)


def _make_handler(app: FakeMuse):
    class Handler(BaseHTTPRequestHandler):
        protocol_version = "HTTP/1.1"

        def do_POST(self):  # noqa: N802 - required by BaseHTTPRequestHandler
            length = int(self.headers.get("Content-Length") or 0)
            body = self.rfile.read(length) if length else b""
            headers = {k.lower(): v for k, v in self.headers.items()}
            reply = app.respond(self.command, self.path, headers, body)
            if reply.drop:
                # The turn was generated and the answer is gone. A real gateway does
                # this on a timeout, and the client must not read it as a fresh ask.
                self.close_connection = True
                try:
                    self.connection.shutdown(socket.SHUT_RDWR)
                except OSError:
                    pass
                return
            raw = reply.body
            self.send_response(reply.status)
            self.send_header("Content-Type", reply.content_type)
            for key, value in reply.headers.items():
                self.send_header(key, value)
            self.send_header("Content-Length", str(len(raw)))
            self.end_headers()
            self.wfile.write(raw)

        def log_message(self, *args):
            pass

    return Handler
