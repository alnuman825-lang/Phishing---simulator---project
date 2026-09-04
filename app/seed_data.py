"""
Seed data for phishing training scenarios.

Kept as a plain data structure (not embedded in seed.py) so tests or
an admin tool can import it later without executing the seeding
script. Every scenario here is fictional simulated training content:
no real people, no real organisations impersonated in a way that
could be mistaken for a real message, and no functional links.
"""

SCENARIOS = [
    {
        "title": "Fake University Account Suspension Notice",
        "sender_name": "IT Service Desk",
        "sender_email": "it-helpdesk@csu-portal-alerts.com",
        "subject": "URGENT: Your student account will be suspended in 24 hours",
        "body": (
            "Dear Student,\n\n"
            "Our system has detected unusual activity on your student portal account. "
            "To avoid suspension, you must verify your identity immediately by clicking "
            "the link below and confirming your login details.\n\n"
            "[Verify My Account Now]\n\n"
            "Failure to act within 24 hours will result in permanent loss of access to "
            "your enrolment, grades, and email.\n\n"
            "IT Service Desk"
        ),
        "context": (
            "This is a SIMULATED training email. It arrived outside of normal business "
            "hours and was not sent from the university's real domain."
        ),
        "explanation": (
            "This message uses urgency and fear (account suspension in 24 hours) to "
            "pressure quick action. The sender domain 'csu-portal-alerts.com' is not "
            "the university's real domain — always check the actual domain, not just "
            "the display name. Legitimate IT departments do not ask you to 'verify' "
            "your password via an emailed link. The correct action is to report it."
        ),
        "correct_response": "report",
        "difficulty": "beginner",
        "category": "fake_university_notification",
    },
    {
        "title": "Suspicious Password Reset Request",
        "sender_name": "Account Security",
        "sender_email": "no-reply@secure-passreset.net",
        "subject": "Password reset requested for your account",
        "body": (
            "We received a request to reset the password for your account. If you did "
            "not make this request, you can ignore this email and your password will "
            "remain unchanged.\n\n"
            "If you did request this, click below to set a new password:\n\n"
            "[Reset Password]\n\n"
            "This link will expire in 15 minutes."
        ),
        "context": (
            "This is a SIMULATED training email. The user did not request a password "
            "reset for this service."
        ),
        "explanation": (
            "A password reset email you did not request is a common phishing lure — "
            "clicking the link often leads to a fake login page designed to steal "
            "your real credentials. The generic sender domain and artificial urgency "
            "('expires in 15 minutes') are additional red flags. Since no reset was "
            "requested, the safest action is to report it rather than click or simply "
            "ignore it (ignoring alone doesn't alert others who may receive the same email)."
        ),
        "correct_response": "report",
        "difficulty": "beginner",
        "category": "suspicious_password_reset",
    },
    {
        "title": "Fake Parcel Delivery Notification",
        "sender_name": "Parcel Delivery Service",
        "sender_email": "tracking@parcel-updates-express.info",
        "subject": "Your parcel could not be delivered — action required",
        "body": (
            "We attempted to deliver your parcel today but were unable to complete "
            "delivery. A small redelivery fee of $2.99 is required to reschedule.\n\n"
            "Pay now and select a new delivery date:\n\n"
            "[Pay Redelivery Fee]\n\n"
            "If payment is not received within 3 days, the parcel will be returned "
            "to sender."
        ),
        "context": (
            "This is a SIMULATED training email. The recipient is not expecting any "
            "parcel deliveries."
        ),
        "explanation": (
            "Fake delivery notices are a very common phishing pattern — a small, "
            "'reasonable' fee makes people less suspicious than a large payment "
            "request would. The domain 'parcel-updates-express.info' does not match "
            "any real courier company, and legitimate couriers rarely charge a card "
            "fee by email link. Reporting it is correct — a single unexpected notice "
            "with a payment link, from an unrecognised domain, should not be clicked "
            "or paid."
        ),
        "correct_response": "report",
        "difficulty": "beginner",
        "category": "fake_parcel_delivery",
    },
    {
        "title": "Fake Invoice / Payment Request",
        "sender_name": "Accounts Payable",
        "sender_email": "billing@vendor-invoices-hub.com",
        "subject": "Invoice #INV-88213 overdue — immediate payment required",
        "body": (
            "This is a reminder that invoice #INV-88213 for $1,240.00 is now overdue. "
            "Please review the attached invoice and process payment within 48 hours "
            "to avoid service interruption.\n\n"
            "[View Invoice]\n\n"
            "Contact accounts payable with any questions."
        ),
        "context": (
            "This is a SIMULATED training email. The recipient's organisation has no "
            "record of any vendor relationship or outstanding invoice matching this number."
        ),
        "explanation": (
            "Fake invoice emails target the natural instinct to resolve financial "
            "matters quickly, especially with a 'service interruption' threat. Key "
            "indicators here: an unfamiliar vendor, a generic invoice number, and a "
            "payment link rather than a proper attached PDF from a known accounts "
            "system. The correct response is to report the message so finance/IT can "
            "verify it, not click through or quietly delete it."
        ),
        "correct_response": "report",
        "difficulty": "intermediate",
        "category": "fake_invoice_payment",
    },
    {
        "title": "Suspicious Microsoft-Style Account Alert",
        "sender_name": "Microsoft Account Team",
        "sender_email": "security-noreply@micros0ft-alerts.com",
        "subject": "Unusual sign-in activity detected on your account",
        "body": (
            "We detected a sign-in to your account from a new device in a location "
            "we don't recognise. If this was you, no action is needed.\n\n"
            "If this wasn't you, secure your account immediately:\n\n"
            "[Secure My Account]\n\n"
            "Microsoft Account Team"
        ),
        "context": (
            "This is a SIMULATED training email. Note the sender domain carefully."
        ),
        "explanation": (
            "The sender domain uses a zero ('micros0ft-alerts.com') instead of the "
            "letter 'o' — a classic typosquatting technique designed to look right at "
            "a glance. Real account-alert emails from major providers link to the "
            "provider's actual domain and are usually also visible by logging in "
            "directly (typed manually, not via the email link). This should be "
            "reported, and the account checked by navigating to the real site directly."
        ),
        "correct_response": "report",
        "difficulty": "intermediate",
        "category": "fake_microsoft_google_alert",
    },
    {
        "title": "Internal-Looking IT Survey (Low Risk Example)",
        "sender_name": "Student Services",
        "sender_email": "surveys@student-services.csu.edu.au",
        "subject": "Quick 2-minute feedback survey on library hours",
        "body": (
            "Hi there,\n\n"
            "We're reviewing library opening hours for next semester and would love "
            "your feedback. This short survey takes about 2 minutes.\n\n"
            "[Take the Survey]\n\n"
            "Thanks for helping us improve student services."
        ),
        "context": (
            "This is a SIMULATED training email included to test whether users "
            "over-report harmless messages. The domain matches the real university "
            "domain and no credentials or payment are requested."
        ),
        "explanation": (
            "Not every email with a link is phishing. This message comes from a "
            "domain matching the real university, makes no urgent threat, and asks "
            "for opinions rather than credentials, payment, or personal data. "
            "Reporting every single email as phishing creates alert fatigue for "
            "security teams. The appropriate response to a low-risk, plausible "
            "internal message like this is simply to ignore/delete it if you don't "
            "want to participate — not to report it as an attack."
        ),
        "correct_response": "ignore",
        "difficulty": "beginner",
        "category": "general",
    },
]
