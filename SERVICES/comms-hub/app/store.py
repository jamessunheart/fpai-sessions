from __future__ import annotations

import json
import os
import time
from contextlib import contextmanager
from pathlib import Path
from typing import Any, Iterator

from .dedupe import dedupe_key
from .models import DeliveryAttempt, MessageInput, MessageRecord, now_iso
from .security import redact_obj


class StoreError(RuntimeError):
    pass


class JsonlStore:
    def __init__(self, var_dir: Path):
        self.var_dir = Path(var_dir)
        self.inbox_path = self.var_dir / "inbox.jsonl"
        self.outbox_path = self.var_dir / "outbox.jsonl"
        self.delivery_log_path = self.var_dir / "delivery_log.jsonl"
        self.state_path = self.var_dir / "state.json"
        self.locks_dir = self.var_dir / "locks"
        self.tmp_dir = self.var_dir / "tmp"
        self.ensure()

    def ensure(self) -> None:
        self.var_dir.mkdir(parents=True, exist_ok=True)
        self.locks_dir.mkdir(parents=True, exist_ok=True)
        self.tmp_dir.mkdir(parents=True, exist_ok=True)
        for path in [self.inbox_path, self.outbox_path, self.delivery_log_path]:
            path.touch(exist_ok=True)
        if not self.state_path.exists():
            self.save_state({"dedupe": {}, "runtime_paused": False})

    def load_state(self) -> dict[str, Any]:
        try:
            return json.loads(self.state_path.read_text())
        except (json.JSONDecodeError, FileNotFoundError):
            return {"dedupe": {}, "runtime_paused": False}

    def save_state(self, state: dict[str, Any]) -> None:
        self.state_path.write_text(json.dumps(state, indent=2, sort_keys=True) + "\n")

    def runtime_paused(self) -> bool:
        return bool(self.load_state().get("runtime_paused", False))

    def set_runtime_paused(self, paused: bool) -> None:
        state = self.load_state()
        state["runtime_paused"] = paused
        self.save_state(state)

    @contextmanager
    def lock(self, name: str) -> Iterator[None]:
        lock_path = self.locks_dir / f"{name}.lock"
        try:
            fd = os.open(lock_path, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
        except FileExistsError as exc:
            raise StoreError(f"lock already held: {name}") from exc
        try:
            os.write(fd, str(os.getpid()).encode("utf-8"))
            yield
        finally:
            os.close(fd)
            try:
                lock_path.unlink()
            except FileNotFoundError:
                pass

    def _append(self, path: Path, record: dict[str, Any]) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(redact_obj(record), sort_keys=True) + "\n")

    def _read(self, path: Path) -> list[dict[str, Any]]:
        records: list[dict[str, Any]] = []
        if not path.exists():
            return records
        with path.open("r", encoding="utf-8") as handle:
            for line_no, line in enumerate(handle, start=1):
                if not line.strip():
                    continue
                try:
                    records.append(json.loads(line))
                except json.JSONDecodeError as exc:
                    raise StoreError(f"malformed jsonl in {path}:{line_no}") from exc
        return records

    def dedupe_seen(self, key: str, ttl_seconds: int = 86400) -> bool:
        state = self.load_state()
        dedupe = state.setdefault("dedupe", {})
        now = time.time()
        for old_key, created in list(dedupe.items()):
            if now - float(created) > ttl_seconds:
                dedupe.pop(old_key, None)
        if key in dedupe:
            self.save_state(state)
            return True
        dedupe[key] = now
        self.save_state(state)
        return False

    def next_message_id(self) -> str:
        return "msg_" + now_iso().replace("-", "").replace(":", "").replace(".", "_")

    def create_record(self, message: MessageInput, status: str = "queued") -> MessageRecord:
        key = dedupe_key(message)
        return MessageRecord(
            **message.model_dump(),
            id=self.next_message_id(),
            status=status,
            dedupe_key=key,
        )

    def append_outbox(self, message: MessageInput) -> MessageRecord:
        record = self.create_record(message)
        self._append(self.outbox_path, record.model_dump())
        return record

    def append_inbox(self, message: MessageInput) -> MessageRecord:
        record = self.create_record(message)
        self._append(self.inbox_path, record.model_dump())
        state = self.load_state()
        state["last_inbox_at"] = record.created_at
        self.save_state(state)
        return record

    def append_delivery(self, attempt: DeliveryAttempt) -> None:
        self._append(self.delivery_log_path, attempt.model_dump())
        state = self.load_state()
        state["last_outbox_drain_at"] = attempt.created_at
        self.save_state(state)

    def outbox(self) -> list[MessageRecord]:
        return [MessageRecord(**item) for item in self._read(self.outbox_path)]

    def inbox(self) -> list[MessageRecord]:
        return [MessageRecord(**item) for item in self._read(self.inbox_path)]

    def delivery_log(self) -> list[dict[str, Any]]:
        return self._read(self.delivery_log_path)

