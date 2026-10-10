"""Allow overlapping Therapy Sessions; everything else stays standard healthcare."""
from healthcare.healthcare.doctype.therapy_session.therapy_session import TherapySession


class CustomTherapySession(TherapySession):
    def validate_duplicate(self):
        # Allow overlapping sessions for every Therapy Type.
        # Same client and same practitioner are allowed.
        # No execution quantity limit is enforced here.
        return
