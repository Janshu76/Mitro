import unittest
from app.services.provisioning import required_ecl, required_ecl_without_dlg

class DlgInvocationRegression(unittest.TestCase):
    def test_invocation_reduces_cover_before_recomputing_ecl(self):
        self.assertEqual(required_ecl(5000.0, 4000.0, 2000.0), 3000.0)

    def test_recompute_clamps_remaining_cover_at_zero(self):
        self.assertEqual(required_ecl(5000.0, 1000.0, 2000.0), 5000.0)

    def test_no_dlg_decoy_keeps_gross_ecl(self):
        self.assertEqual(required_ecl_without_dlg(5000.0), 5000.0)

if __name__ == "__main__":
    unittest.main()
