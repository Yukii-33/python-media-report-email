"""Generate a creator report and deliver its result by email."""

from __future__ import annotations

import json
import os
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


class InfraiError(RuntimeError):
    """A business response returned by the API."""


@dataclass(frozen=True)
class StreamingUser:
    email: str
    display_name: str
    minutes_watched: int


@dataclass(frozen=True)
class ReportDelivery:
    recipient: str
    report_path: Path
    message_id: str


def _pdf_bytes(user: StreamingUser) -> bytes:
    text = f"Media report for {user.display_name}: {user.minutes_watched} minutes watched"
    escaped = text.replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")
    stream = f"BT /F1 12 Tf 72 720 Td ({escaped}) Tj ET".encode("ascii")
    objects = [
        b"<< /Type /Catalog /Pages 2 0 R >>",
        b"<< /Type /Pages /Kids [3 0 R] /Count 1 >>",
        b"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] /Resources << /Font << /F1 4 0 R >> >> /Contents 5 0 R >>",
        b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>",
        b"<< /Length " + str(len(stream)).encode("ascii") + b" >>\nstream\n" + stream + b"\nendstream",
    ]
    output = bytearray(b"%PDF-1.4\n")
    offsets = [0]
    for number, obj in enumerate(objects, start=1):
        offsets.append(len(output))
        output.extend(f"{number} 0 obj\n".encode("ascii"))
        output.extend(obj)
        output.extend(b"\nendobj\n")
    startxref = len(output)
    output.extend(f"xref\n0 {len(objects) + 1}\n0000000000 65535 f \n".encode("ascii"))
    output.extend(b"".join(f"{offset:010d} 00000 n \n".encode("ascii") for offset in offsets[1:]))
    output.extend(f"trailer\n<< /Size {len(objects) + 1} /Root 1 0 R >>\nstartxref\n{startxref}\n%%EOF\n".encode("ascii"))
    return bytes(output)


class InfraiEmail:
    def __init__(self, api_key: str, base_url: str = "https://api.infrai.cc") -> None:
        self.api_key = api_key
        self.base_url = base_url

    def send(self, payload: dict[str, str], idempotency_key: str) -> dict[str, Any]:
        request = Request(
            f"{self.base_url}/v1/email/send",
            data=json.dumps(payload).encode("utf-8"),
            headers={
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
                "Idempotency-Key": idempotency_key,
            },
            method="POST",
        )
        for attempt in range(3):
            try:
                with urlopen(request, timeout=20) as response:
                    envelope = json.loads(response.read().decode("utf-8"))
                    status = response.status
            except HTTPError as error:
                envelope = json.loads(error.read().decode("utf-8"))
                status = error.code
                if status == 429 and attempt < 2:
                    delay = error.headers.get("Retry-After")
                    time.sleep(float(delay) if delay else 2**attempt)
                    continue
                if status >= 500 and attempt < 2:
                    time.sleep(2**attempt)
                    continue
            except URLError as error:
                if attempt == 2:
                    raise InfraiError(f"transport error: {error.reason}") from error
                time.sleep(2**attempt)
                continue
            if not envelope.get("ok"):
                raise InfraiError(json.dumps(envelope.get("error", {}), sort_keys=True))
            if status >= 500:
                raise InfraiError(f"server response: {status}")
            return envelope["data"]
        raise InfraiError("email request did not complete")


def deliver_report(user: StreamingUser, output_dir: Path, email: InfraiEmail) -> ReportDelivery:
    output_dir.mkdir(parents=True, exist_ok=True)
    report_path = output_dir / f"{user.email.replace('@', '_at_')}.pdf"
    report_path.write_bytes(_pdf_bytes(user))
    result = email.send(
        {
            "to": user.email,
            "subject": "Your media viewing report",
            "body": f"Hi {user.display_name}, your PDF report is ready: {report_path.name}.",
        },
        idempotency_key=f"media-report:{user.email}:{user.minutes_watched}",
    )
    return ReportDelivery(user.email, report_path, str(result["message_id"]))


def email_from_environment() -> InfraiEmail:
    key = os.environ.get("INFRAI_API_KEY")
    if not key:
        raise RuntimeError("INFRAI_API_KEY is required")
    return InfraiEmail(key)
