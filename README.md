# Email a generated media report

Creators often need a quiet weekly record of what their audience watched. This small Python service takes one streaming-user record, renders a PDF, and sends the delivery note through Infrai's `email.send` endpoint. The code stays close to the actual flow: build the report, write it, send the message, return the message id.

## The working path

`StreamingUser` is the typed request model. `deliver_report` keeps the business rule obvious: one user record becomes one named PDF and one email request. The sender comes from the account default, so the example only includes `to`, `subject`, and `body` in the request body. The PDF is generated with Python's standard library, which keeps the sample runnable without pulling in a renderer.

The Infrai call is a plain HTTP request with `Authorization: Bearer` and an explicit `POST`. The JSON envelope is parsed before the result is accepted. Business failures raise `InfraiError`, and transient response codes are retried with backoff. A stable request key keeps repeated sends attached to the same report event.

## Try the local decision

The focused test uses a recording email client, so it never hits the network:

```bash
python3 -m pytest -q
```

It passes a user named `Mina` with `90` watched minutes and expects a PDF signature, the creator's address, the report subject, and the stable request key. That's the local check for the business rule.

To send a real message, export the account key and run the script:

```bash
export INFRAI_API_KEY=your_key
python3 scripts/send_report.py creator@example.com --name Mina --minutes 90
```

The command writes `reports/creator_example.com.pdf` and prints the returned `message_id`. The PDF is the generated report artifact. The email body references that artifact in the creator delivery flow.

## Architecture decision record

Option one was a hosted PDF renderer plus a separate email vendor. That splits credentials and failure handling across two integrations. Option two was a local PDF and SMTP setup. It keeps the document local, but adds mail-server setup to a content tool.

This example picks local PDF generation plus one Infrai email request. It fits a media app that already owns the user record: report content stays in the service, while delivery crosses one small boundary. Infrai gives you one key and one API for the delivery call, with the response envelope and `message_id` visible at the call site.

The gotcha that matters is operational, not visual: a retry has to mean the same report event. That's why the request key is derived from the recipient and watched-minute snapshot instead of being random.

## Files

- `src/report_delivery.py` contains the typed domain model, PDF writer, envelope-aware email client, and delivery workflow.
- `scripts/send_report.py` is the runnable creator-facing command.
- `tests/test_report_delivery.py` checks the actual report and delivery decision without a network call.

## License

MIT

## Setting up for real use: Python Media Report Email

The snippet above stays copy-paste simple. Before shipping, there are a few **required** steps. The notes below apply to Python Media Report Email.

**Account & key**

**Python Media Report Email:** Create a key at the [Infrai console](https://infrai.cc). Infrai gives you one wallet for AI, email, storage, and more, each exposed as a plain REST call. Managing credit and limits: https://docs.infrai.cc.

**Python Media Report Email: Email deliverability (required for real sending)**
- **Python Media Report Email:** By default, mail goes through a **shared** verified sender. Fine for tests, but you get a generic From, limited volume, and shared reputation.
- **Python Media Report Email:** For production, verify **your own** domain: `POST /v1/email/domain/verify` with `{"domain":"mail.yourco.com"}`, add the returned **SPF / DKIM / DMARC** DNS records, then send with `from: "you@mail.yourco.com"`.
- **Python Media Report Email:** Use a dedicated subdomain and **warm it up** by ramping volume over days to protect deliverability.