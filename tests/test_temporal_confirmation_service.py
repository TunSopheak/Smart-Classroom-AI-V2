import unittest

from app.services.temporal_confirmation_service import evaluate_temporal_confirmation


def frame(label, confidence=0.55):
    return {"label": label, "confidence": confidence}


class TemporalConfirmationServiceTests(unittest.TestCase):
    def test_no_frames_never_confirms(self):
        result = evaluate_temporal_confirmation([])

        self.assertEqual(result["status"], "no_frames")
        self.assertFalse(result["confirmed_for_review"])
        self.assertFalse(result["should_show_dashboard_alert"])
        self.assertFalse(result["should_save_evidence"])
        self.assertEqual(result["generated_behavior_labels"], [])

    def test_needs_more_frames(self):
        result = evaluate_temporal_confirmation(
            [frame("possible_head_low_candidate"), frame("possible_head_low_candidate")]
        )

        self.assertEqual(result["status"], "needs_more_frames")
        self.assertEqual(result["target_matches"], 2)
        self.assertFalse(result["confirmed_for_review"])

    def test_repeated_candidate_confirms_for_review_only(self):
        result = evaluate_temporal_confirmation(
            [
                frame("possible_head_low_candidate", 0.55),
                frame("normal_upright_candidate", 0.60),
                frame("possible_head_low_candidate", 0.57),
                frame("possible_head_low_candidate", 0.56),
            ]
        )

        self.assertEqual(result["status"], "confirmed_for_review")
        self.assertTrue(result["confirmed_for_review"])
        self.assertFalse(result["should_show_dashboard_alert"])
        self.assertFalse(result["should_save_evidence"])
        self.assertFalse(result["should_update_database"])
        self.assertEqual(result["generated_behavior_labels"], [])

    def test_unstable_candidate_does_not_confirm(self):
        result = evaluate_temporal_confirmation(
            [
                frame("possible_head_low_candidate", 0.55),
                frame("normal_upright_candidate", 0.60),
                frame("normal_upright_candidate", 0.60),
                frame("possible_head_low_candidate", 0.49),
            ]
        )

        self.assertEqual(result["status"], "unstable_candidate")
        self.assertFalse(result["confirmed_for_review"])
        self.assertEqual(result["target_matches"], 1)

    def test_insufficient_pose_quality_status(self):
        result = evaluate_temporal_confirmation(
            [
                frame("insufficient_pose_quality", 0.0),
                frame("insufficient_pose_quality", 0.0),
                frame("normal_upright_candidate", 0.60),
            ]
        )

        self.assertEqual(result["status"], "insufficient_pose_quality")
        self.assertFalse(result["confirmed_for_review"])


if __name__ == "__main__":
    unittest.main()
