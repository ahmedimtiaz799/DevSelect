import unittest

from app.routers.evaluation import _candidate_meta
from app.utils.candidate_domain import (
    NON_TECHNICAL,
    SEMI_TECHNICAL,
    SKIP_NON_TECHNICAL,
    TECHNICAL,
    classify_candidate_domain,
    github_review_policy,
    resolve_candidate_display_role,
)


FINANCE_ROLE = "Entry-Level Banking & Finance Candidate"


def amber_like_finance_candidate():
    return {
        "full_name": "Syeda Amber Fatima Rizvi",
        "current_title": "Volunteer Trainer",
        "summary": "BBA Banking and Finance graduate targeting banking and financial sector roles.",
        "skills": [
            "Financial analysis",
            "Digital banking",
            "Financial inclusion",
            "Risk assessment",
            "Spreadsheet modeling",
        ],
        "education": [
            {
                "degree": "BBA Banking and Finance",
                "institution": "University",
            }
        ],
        "work_experience": [
            {
                "title": "Volunteer Trainer",
                "description": "Short volunteer trainer experience.",
            }
        ],
    }


class CandidateRoleResolverTests(unittest.TestCase):
    def test_finance_evidence_overrides_short_volunteer_trainer_role(self):
        candidate = amber_like_finance_candidate()
        raw_cv_text = (
            "BBA Banking and Finance. Banking and financial sector. "
            "Financial analysis, digital banking, financial inclusion, "
            "risk assessment, spreadsheet modeling. Volunteer Trainer."
        )

        display_role = resolve_candidate_display_role(candidate, raw_cv_text)
        domain, source = classify_candidate_domain(candidate, raw_cv_text)

        self.assertEqual(display_role, FINANCE_ROLE)
        self.assertNotEqual(display_role, "Volunteer Trainer")
        self.assertEqual(domain, NON_TECHNICAL)
        self.assertNotIn("training", source)

    def test_true_volunteer_trainer_role_is_preserved(self):
        candidate = {
            "current_title": "Volunteer Trainer",
            "summary": "Volunteer trainer focused on classroom education and youth coaching.",
            "skills": ["Training", "Curriculum delivery", "Lesson facilitation"],
            "work_experience": [
                {
                    "title": "Volunteer Trainer",
                    "description": "Delivered training sessions and classroom activities.",
                }
            ],
        }

        display_role = resolve_candidate_display_role(
            candidate,
            "teaching training education classroom curriculum lesson facilitation",
        )

        self.assertEqual(display_role, "Volunteer Trainer")
        self.assertNotEqual(display_role, FINANCE_ROLE)

    def test_technical_role_is_preserved(self):
        candidate = {
            "current_title": "Full Stack AI Engineer",
            "summary": "Full Stack AI Engineer building React, FastAPI, LangGraph and RAG systems.",
            "skills": ["React", "FastAPI", "LangGraph", "RAG"],
        }

        display_role = resolve_candidate_display_role(
            candidate,
            "Full Stack AI Engineer React FastAPI LangGraph RAG GitHub",
        )
        domain, _source = classify_candidate_domain(candidate, "React FastAPI LangGraph RAG")

        self.assertEqual(display_role, "Full Stack AI Engineer")
        self.assertEqual(domain, TECHNICAL)
        self.assertIsNone(github_review_policy(domain))

    def test_business_analyst_role_is_preserved(self):
        candidate = {
            "current_title": "Business Analyst",
            "summary": "Business Analyst focused on requirements gathering and stakeholder communication.",
            "skills": [
                "Requirements gathering",
                "Stakeholder communication",
                "Process mapping",
                "Dashboards",
                "Documentation",
            ],
        }

        display_role = resolve_candidate_display_role(candidate, "requirements stakeholder process dashboards")
        domain, _source = classify_candidate_domain(candidate, "requirements stakeholder process dashboards")

        self.assertEqual(display_role, "Business Analyst")
        self.assertEqual(domain, SEMI_TECHNICAL)
        self.assertIsNone(github_review_policy(domain))

    def test_product_manager_role_is_preserved(self):
        candidate = {
            "current_title": "Product Manager",
            "summary": "Product Manager focused on product roadmap and stakeholder alignment.",
            "skills": ["Product roadmap", "User stories", "Backlog", "Stakeholder alignment"],
        }

        display_role = resolve_candidate_display_role(candidate, "product roadmap user stories backlog")
        domain, _source = classify_candidate_domain(candidate, "product roadmap user stories backlog")

        self.assertEqual(display_role, "Product Manager")
        self.assertEqual(domain, SEMI_TECHNICAL)
        self.assertIsNone(github_review_policy(domain))

    def test_unknown_broad_cv_does_not_pick_random_specific_role(self):
        candidate = {
            "current_title": None,
            "summary": "Motivated candidate with varied interests and mixed general skills.",
            "skills": ["Communication", "MS Office", "Teamwork", "Research"],
            "work_experience": [],
            "education": [],
        }

        display_role = resolve_candidate_display_role(candidate, "general skills teamwork research")

        self.assertIn(display_role, {None, "Role focus needs clarification"})
        self.assertNotIn(display_role, {FINANCE_ROLE, "Volunteer Trainer", "Full Stack AI Engineer"})
        self.assertNotEqual(display_role, "Role unclear for code-based evaluation")

    def test_router_meta_uses_shared_display_role(self):
        candidate = amber_like_finance_candidate()
        raw_cv_text = (
            "BBA Banking and Finance. Banking and financial sector. "
            "Financial analysis, digital banking, financial inclusion, "
            "risk assessment, spreadsheet modeling. Volunteer Trainer."
        )

        meta = _candidate_meta(
            {
                "candidate": candidate,
                "raw_cv_text": raw_cv_text,
            }
        )

        self.assertEqual(meta["candidate_name"], "Syeda Amber Fatima Rizvi")
        self.assertEqual(meta["role"], FINANCE_ROLE)
        self.assertNotEqual(meta["role"], "Volunteer Trainer")

    def test_github_policy_skips_non_technical_but_not_technical(self):
        finance_candidate = amber_like_finance_candidate()
        finance_domain, _source = classify_candidate_domain(
            finance_candidate,
            "banking financial sector digital banking risk assessment",
        )
        technical_candidate = {
            "current_title": "Full Stack AI Engineer",
            "summary": "Full Stack AI Engineer building React and FastAPI systems.",
            "skills": ["React", "FastAPI"],
        }
        technical_domain, _source = classify_candidate_domain(
            technical_candidate,
            "React FastAPI GitHub",
        )

        self.assertEqual(finance_domain, NON_TECHNICAL)
        self.assertEqual(github_review_policy(finance_domain), SKIP_NON_TECHNICAL)
        self.assertEqual(technical_domain, TECHNICAL)
        self.assertIsNone(github_review_policy(technical_domain))


if __name__ == "__main__":
    unittest.main()
