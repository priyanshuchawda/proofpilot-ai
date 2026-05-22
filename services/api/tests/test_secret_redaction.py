from app.ingestion.redaction import redact_secrets


def test_redacts_common_secret_formats() -> None:
    source = """
    GOOGLE_API_KEY=AIzaSyD-example-secret-value-123456789
    Authorization: Bearer secret-token-value
    eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.payload.signature
    -----BEGIN PRIVATE KEY-----
    abc123
    -----END PRIVATE KEY-----
    """

    redacted = redact_secrets(source)

    assert "AIzaSyD-example-secret-value" not in redacted.text
    assert "secret-token-value" not in redacted.text
    assert "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9" not in redacted.text
    assert "BEGIN PRIVATE KEY" not in redacted.text
    assert redacted.redaction_count == 4
    assert redacted.status == "redacted"
