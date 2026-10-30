import unittest
from fastapi import HTTPException
from app.routers.applications import import_legacy_application
from app.schemas import LegacyImportIn

class ConsentRegression(unittest.TestCase):
    def test_missing_consent_is_rejected_before_customer_write(self):
        body = LegacyImportIn(full_name="Demo Borrower", phone="9999999999", pan_last4="1234",
            requested_amount=10000, purpose="education", consent=False)
        with self.assertRaises(HTTPException) as raised:
            import_legacy_application(body, db=object())
        self.assertEqual(raised.exception.status_code, 400)

if __name__ == "__main__":
    unittest.main()
