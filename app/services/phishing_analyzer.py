from dataclasses import dataclass


@dataclass
class PhishingFinding:
    indicator: str
    severity: str
    explanation: str


class PhishingAnalyzer:
    """Rule-based phishing analysis engine used as the AI integration foundation."""

    URGENCY_TERMS = {
        "urgent",
        "immediately",
        "immediate",
        "as soon as possible",
        "within 24 hours",
        "account suspension",
        "act now",
    }

    CREDENTIAL_TERMS = {
        "password",
        "login",
        "verify your account",
        "confirm your account",
        "credentials",
        "sign in",
    }

    FINANCIAL_TERMS = {
        "payment",
        "invoice",
        "bank",
        "credit card",
        "refund",
        "transaction",
        "payment details",
    }

    def analyze(self, content: str) -> dict:
        text = content.lower()
        findings = []

        if self._contains_any(text, self.URGENCY_TERMS):
            findings.append(
                PhishingFinding(
                    indicator="Urgency or pressure",
                    severity="high",
                    explanation=(
                        "The message creates pressure to act quickly, "
                        "which is commonly used to reduce careful verification."
                    ),
                )
            )

        if self._contains_any(text, self.CREDENTIAL_TERMS):
            findings.append(
                PhishingFinding(
                    indicator="Credential request",
                    severity="high",
                    explanation=(
                        "The message references account credentials or "
                        "authentication activity."
                    ),
                )
            )

        if self._contains_any(text, self.FINANCIAL_TERMS):
            findings.append(
                PhishingFinding(
                    indicator="Financial request",
                    severity="high",
                    explanation=(
                        "The message references financial information, "
                        "transactions, or payment activity."
                    ),
                )
            )

        if not findings:
            findings.append(
                PhishingFinding(
                    indicator="No obvious phishing indicators detected",
                    severity="low",
                    explanation=(
                        "No predefined high-risk indicators were identified "
                        "by the current analysis rules."
                    ),
                )
            )

        risk_score = self._calculate_risk(findings)

        return {
            "risk_score": risk_score,
            "risk_level": self._risk_level(risk_score),
            "findings": [
                {
                    "indicator": finding.indicator,
                    "severity": finding.severity,
                    "explanation": finding.explanation,
                }
                for finding in findings
            ],
        }

    @staticmethod
    def _contains_any(text: str, terms: set[str]) -> bool:
        return any(term in text for term in terms)

    @staticmethod
    def _calculate_risk(findings: list[PhishingFinding]) -> int:
        score = 0

        for finding in findings:
            if finding.severity == "high":
                score += 35
            elif finding.severity == "medium":
                score += 20
            else:
                score += 5

        return min(score, 100)

    @staticmethod
    def _risk_level(score: int) -> str:
        if score >= 35:
            return "high"
        if score >= 20:
            return "medium"
        return "low"
