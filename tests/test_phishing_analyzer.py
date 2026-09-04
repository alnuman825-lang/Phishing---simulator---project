from app.services.phishing_analyzer import PhishingAnalyzer


def test_analyzer_detects_urgency():
    result = PhishingAnalyzer().analyze(
        "URGENT: Your account will be suspended. Act now."
    )

    assert result["risk_level"] == "high"
    assert any(
        finding["indicator"] == "Urgency or pressure"
        for finding in result["findings"]
    )


def test_analyzer_detects_credential_request():
    result = PhishingAnalyzer().analyze(
        "Please verify your account and confirm your password."
    )

    assert any(
        finding["indicator"] == "Credential request"
        for finding in result["findings"]
    )


def test_analyzer_detects_financial_request():
    result = PhishingAnalyzer().analyze(
        "Please confirm your bank payment details."
    )

    assert any(
        finding["indicator"] == "Financial request"
        for finding in result["findings"]
    )


def test_analyzer_returns_low_risk_without_indicators():
    result = PhishingAnalyzer().analyze(
        "The library will close at 5 PM today."
    )

    assert result["risk_level"] == "low"
    assert result["risk_score"] == 5
