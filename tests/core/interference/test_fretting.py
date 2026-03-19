import unittest


def make_context() -> dict:
    return {
        "length_ratio_l_over_d": 0.40,
        "modulus_ratio": 0.01,
        "has_bending": False,
        "torque_sf": 2.2,
        "combined_sf": 1.9,
        "p_min_mpa": 24.0,
        "torque_design_nm": 120.0,
        "torque_capacity_min_nm": 264.0,
    }


class FrettingAssessmentTests(unittest.TestCase):
    def test_fretting_assessment_returns_structured_result_for_applicable_case(self) -> None:
        from core.interference.fretting import assess_fretting_risk

        result = assess_fretting_risk(
            {
                "mode": "on",
                "load_spectrum": "pulsating",
                "duty_severity": "medium",
                "surface_condition": "dry",
                "importance_level": "important",
            },
            make_context(),
        )

        self.assertTrue(result["enabled"])
        self.assertTrue(result["applicable"])
        self.assertIn(result["risk_level"], {"low", "medium", "high"})
        self.assertIsInstance(result["drivers"], list)
        self.assertIsInstance(result["recommendations"], list)
        self.assertIn(result["confidence"], {"low", "medium", "high"})

    def test_fretting_assessment_returns_not_applicable_when_length_ratio_is_too_small(self) -> None:
        from core.interference.fretting import assess_fretting_risk

        context = make_context()
        context["length_ratio_l_over_d"] = 0.20

        result = assess_fretting_risk(
            {
                "mode": "on",
                "load_spectrum": "steady",
                "duty_severity": "light",
                "surface_condition": "coated",
                "importance_level": "general",
            },
            context,
        )

        self.assertTrue(result["enabled"])
        self.assertFalse(result["applicable"])
        self.assertEqual(result["risk_level"], "not_applicable")
        self.assertTrue(result["notes"])

    def test_fretting_risk_rises_for_harsher_operating_conditions(self) -> None:
        from core.interference.fretting import assess_fretting_risk

        low = assess_fretting_risk(
            {
                "mode": "on",
                "load_spectrum": "steady",
                "duty_severity": "light",
                "surface_condition": "coated",
                "importance_level": "general",
            },
            make_context(),
        )
        high_context = make_context()
        high_context["torque_sf"] = 1.15
        high_context["combined_sf"] = 1.05
        high = assess_fretting_risk(
            {
                "mode": "on",
                "load_spectrum": "reversing",
                "duty_severity": "heavy",
                "surface_condition": "dry",
                "importance_level": "critical",
            },
            high_context,
        )

        self.assertGreater(high["risk_score"], low["risk_score"])
        levels = {"low": 1, "medium": 2, "high": 3}
        self.assertGreaterEqual(levels[high["risk_level"]], levels[low["risk_level"]])


if __name__ == "__main__":
    unittest.main()
