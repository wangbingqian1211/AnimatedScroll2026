import unittest
from backend.video_budget import charge
class FailureAllowanceTests(unittest.TestCase):
 def test_failed_and_unknown_are_free_locally(self):
  for state in ('failed','submission_unknown','cancelled','cost_unknown'):
   self.assertEqual(charge(dict(status=state,budgetReservationCny=5)),(0,0,'released'))
 def test_running_stays_reserved(self):
  self.assertEqual(charge(dict(status='running',budgetReservationCny=5)),(5,1,'held'))
 def test_success_counts(self):
  self.assertEqual(charge(dict(status='succeeded',budgetReservationCny=5)),(5,1,'spent'))
