from pathlib import Path

from src.report_delivery import ReportDelivery, StreamingUser, deliver_report


class RecordingEmail:
    def __init__(self) -> None:
        self.payload = None

    def send(self, payload, idempotency_key):
        self.payload = (payload, idempotency_key)
        return {"message_id": "msg_test_1"}


def test_creator_gets_a_pdf_and_a_single_delivery_request(tmp_path: Path) -> None:
    email = RecordingEmail()
    result = deliver_report(StreamingUser("creator@example.com", "Mina", 90), tmp_path, email)

    assert isinstance(result, ReportDelivery)
    assert result.report_path.read_bytes().startswith(b"%PDF-1.4")
    assert email.payload[0]["to"] == "creator@example.com"
    assert email.payload[0]["subject"] == "Your media viewing report"
    assert email.payload[1] == "media-report:creator@example.com:90"
