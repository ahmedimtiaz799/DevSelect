import inspect
import unittest

from app.agents.follow_up import FOLLOW_UP_SYSTEM_PROMPT, answer_follow_up_question


class FollowUpPromptTests(unittest.TestCase):
    def setUp(self):
        self.prompt = FOLLOW_UP_SYSTEM_PROMPT.lower()

    def test_supports_scoped_counterfactuals_and_excludes_sources(self):
        self.assertIn("evidence-scope questions are valid counterfactual analysis", self.prompt)
        self.assertIn("ignore the selected github profile", self.prompt)
        self.assertIn("judge only the cv", self.prompt)
        self.assertIn("fully exclude that source", self.prompt)
        self.assertIn("never cite or rely on excluded evidence", self.prompt)

    def test_scoped_recommendation_can_differ_without_replacing_report(self):
        self.assertIn("may differ from the saved report's official recommendation", self.prompt)
        self.assertIn("does not replace the original persisted report", self.prompt)
        self.assertIn("must not keep or justify no hire", self.prompt)
        self.assertIn("this answer is limited by the saved final report context", self.prompt)

    def test_github_name_mismatch_is_calibrated(self):
        self.assertIn("not an automatic no hire signal", self.prompt)
        self.assertIn("treat a name-only mismatch as a verification note", self.prompt)
        self.assertIn("wrong or famous-person profile", self.prompt)
        self.assertIn("unrelated repositories, languages, projects, or activity", self.prompt)
        self.assertIn("matching repositories, languages, and projects can reduce concern", self.prompt)

    def test_follow_up_keeps_report_only_architecture(self):
        parameters = list(inspect.signature(answer_follow_up_question).parameters)
        self.assertEqual(parameters, ["report_context", "question", "chat_id"])
        self.assertIn("using only the completed evaluation report", self.prompt)
        self.assertIn("do not rerun the evaluation", self.prompt)
        self.assertIn("do not invent missing cv or github details", self.prompt)
        self.assertNotIn("reload the original cv", self.prompt)
        self.assertNotIn("reload langgraph checkpoint", self.prompt)


if __name__ == "__main__":
    unittest.main()
