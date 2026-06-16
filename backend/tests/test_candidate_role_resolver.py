import unittest

from app.routers.evaluation import _candidate_meta
from app.utils.candidate_domain import (
    NON_TECHNICAL,
    SEMI_TECHNICAL,
    SKIP_NON_TECHNICAL,
    SKIP_UNCLEAR,
    TECHNICAL,
    UNCLEAR,
    classify_candidate_domain,
    get_interview_track_for_role_family,
    github_review_policy,
    resolve_candidate_display_role,
    resolve_candidate_role_resolution,
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
    def assert_github_not_required(self, domain):
        self.assertNotEqual(domain, TECHNICAL)
        self.assertIn(github_review_policy(domain), {None, SKIP_NON_TECHNICAL})

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

        self.assertEqual(display_role, "Role focus needs clarification")
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

    def test_ui_ux_designer_role_is_semi_technical(self):
        candidate = {
            "current_title": "UI/UX Designer",
            "summary": "UI/UX Designer focused on user flows, usability testing, and design systems.",
            "skills": ["Figma", "Wireframes", "User flows", "Usability testing", "Design systems"],
        }

        display_role = resolve_candidate_display_role(candidate, "figma wireframes user flows usability testing")
        domain, _source = classify_candidate_domain(candidate, "figma wireframes design systems")

        self.assertEqual(display_role, "UI/UX Designer")
        self.assertEqual(domain, SEMI_TECHNICAL)
        self.assertIsNone(github_review_policy(domain))

    def test_data_analyst_role_is_not_software_or_unclear(self):
        candidate = {
            "current_title": "Data Analyst",
            "summary": "Data Analyst focused on SQL, Excel, Power BI dashboards and reporting.",
            "skills": ["SQL", "Excel", "Power BI", "Dashboards", "Reporting", "Data cleaning"],
        }

        display_role = resolve_candidate_display_role(candidate, "sql excel power bi dashboards reporting")
        domain, _source = classify_candidate_domain(candidate, "sql excel power bi dashboards reporting")

        self.assertEqual(display_role, "Data Analyst")
        self.assertNotEqual(display_role, "Software Engineering Candidate")
        self.assertNotEqual(domain, TECHNICAL)
        self.assertNotEqual(domain, "unclear")
        self.assert_github_not_required(domain)

    def test_scrum_master_role_is_semi_technical(self):
        candidate = {
            "current_title": "Scrum Master",
            "summary": "Scrum Master coordinating sprint planning, standups, retrospectives and Jira boards.",
            "skills": ["Sprint planning", "Standups", "Retrospectives", "Jira", "Agile ceremonies"],
        }

        display_role = resolve_candidate_display_role(candidate, "scrum master agile ceremonies jira sprint planning")
        domain, _source = classify_candidate_domain(candidate, "agile ceremonies jira retrospectives")

        self.assertEqual(display_role, "Scrum Master")
        self.assertEqual(domain, SEMI_TECHNICAL)
        self.assertIsNone(github_review_policy(domain))

    def test_hr_admin_role_is_non_technical_and_skips_github(self):
        candidate = {
            "current_title": "HR Officer",
            "summary": "HR Officer managing recruitment coordination, onboarding and employee records.",
            "skills": ["Recruitment coordination", "Onboarding", "Payroll support", "Employee records"],
        }

        display_role = resolve_candidate_display_role(candidate, "recruitment onboarding payroll employee records")
        domain, _source = classify_candidate_domain(candidate, "recruitment onboarding payroll employee records")

        self.assertEqual(display_role, "HR Officer")
        self.assertEqual(domain, NON_TECHNICAL)
        self.assertEqual(github_review_policy(domain), SKIP_NON_TECHNICAL)

    def test_sales_marketing_role_is_non_technical_and_skips_github(self):
        candidate = {
            "current_title": "Sales Executive",
            "summary": "Sales Executive handling leads, campaigns, CRM updates and client communication.",
            "skills": ["Leads", "Campaigns", "CRM", "Client communication", "Conversion tracking"],
        }

        display_role = resolve_candidate_display_role(candidate, "sales leads campaigns crm conversion tracking")
        domain, _source = classify_candidate_domain(candidate, "sales campaigns crm client communication")

        self.assertEqual(display_role, "Sales Executive")
        self.assertEqual(domain, NON_TECHNICAL)
        self.assertEqual(github_review_policy(domain), SKIP_NON_TECHNICAL)

    def test_operations_supply_chain_role_is_non_technical_and_skips_github(self):
        candidate = {
            "current_title": "Supply Chain Coordinator",
            "summary": "Supply Chain Coordinator supporting inventory, procurement and logistics.",
            "skills": ["Inventory", "Procurement", "Vendor coordination", "Logistics", "Stock reports"],
        }

        display_role = resolve_candidate_display_role(candidate, "inventory procurement vendor logistics stock reports")
        domain, _source = classify_candidate_domain(candidate, "operations supply chain inventory procurement logistics")

        self.assertEqual(display_role, "Supply Chain Coordinator")
        self.assertEqual(domain, NON_TECHNICAL)
        self.assertEqual(github_review_policy(domain), SKIP_NON_TECHNICAL)

    def test_accounting_audit_role_is_non_technical_and_not_generic_finance(self):
        candidate = {
            "current_title": "Audit Assistant",
            "summary": "Audit Assistant working on ledger review, reconciliation, tax and invoices.",
            "skills": ["Ledger", "Reconciliation", "Tax", "Invoices", "Financial statements"],
        }

        display_role = resolve_candidate_display_role(candidate, "audit ledger reconciliation tax invoices")
        domain, _source = classify_candidate_domain(candidate, "audit ledger reconciliation tax invoices")

        self.assertEqual(display_role, "Audit Assistant")
        self.assertNotEqual(display_role, FINANCE_ROLE)
        self.assertEqual(domain, NON_TECHNICAL)
        self.assertEqual(github_review_policy(domain), SKIP_NON_TECHNICAL)

    def test_healthcare_role_is_non_technical_and_skips_github(self):
        candidate = {
            "current_title": "Lab Technician",
            "summary": "Lab Technician maintaining clinical records and supporting lab tests.",
            "skills": ["Patient care", "Clinical records", "Lab tests", "Healthcare setting"],
        }

        display_role = resolve_candidate_display_role(candidate, "clinical records lab tests healthcare")
        domain, _source = classify_candidate_domain(candidate, "patient care clinical records lab tests")

        self.assertEqual(display_role, "Lab Technician")
        self.assertEqual(domain, NON_TECHNICAL)
        self.assertEqual(github_review_policy(domain), SKIP_NON_TECHNICAL)

    def test_customer_support_role_is_non_technical_and_skips_github(self):
        candidate = {
            "current_title": "Customer Support Representative",
            "summary": "Customer Support Representative resolving tickets, complaints and CRM cases.",
            "skills": ["Tickets", "Complaints", "CRM", "Customer communication", "Issue resolution"],
        }

        display_role = resolve_candidate_display_role(candidate, "tickets complaints crm issue resolution")
        domain, _source = classify_candidate_domain(candidate, "customer support tickets complaints crm")

        self.assertEqual(display_role, "Customer Support Representative")
        self.assertEqual(domain, NON_TECHNICAL)
        self.assertEqual(github_review_policy(domain), SKIP_NON_TECHNICAL)

    def test_stronger_sales_marketing_evidence_overrides_volunteer_trainer_title(self):
        candidate = {
            "current_title": "Volunteer Trainer",
            "summary": "Sales and marketing candidate focused on lead generation and CRM campaigns.",
            "skills": ["Lead generation", "CRM", "Campaigns", "Client communication", "Conversion tracking"],
            "education": [{"degree": "BBA Marketing", "institution": "University"}],
            "work_experience": [{"title": "Volunteer Trainer", "description": "Short volunteer training activity."}],
        }

        display_role = resolve_candidate_display_role(
            candidate,
            "sales marketing lead generation crm campaigns conversion tracking",
        )
        domain, _source = classify_candidate_domain(
            candidate,
            "sales marketing lead generation crm campaigns conversion tracking",
        )

        self.assertEqual(display_role, "Sales / Marketing Candidate")
        self.assertNotEqual(display_role, "Volunteer Trainer")
        self.assertEqual(domain, NON_TECHNICAL)
        self.assertEqual(github_review_policy(domain), SKIP_NON_TECHNICAL)

    def test_interview_track_for_full_stack_ai_engineer_is_technical(self):
        candidate = {
            "current_title": "Full Stack AI Engineer",
            "summary": "Full Stack AI Engineer building React, FastAPI, LangGraph and RAG systems.",
            "skills": ["React", "FastAPI", "LangGraph", "RAG"],
        }

        resolution = resolve_candidate_role_resolution(candidate, "React FastAPI LangGraph RAG GitHub")
        track = get_interview_track_for_role_family(resolution.role_family, resolution.domain)

        self.assertEqual(track, "technical interview")

    def test_interview_track_for_business_analyst_is_business_focused(self):
        candidate = {
            "current_title": "Business Analyst",
            "summary": "Business Analyst focused on requirements gathering and stakeholder communication.",
            "skills": ["Requirements gathering", "Stakeholder communication", "Process mapping"],
        }

        resolution = resolve_candidate_role_resolution(candidate, "requirements stakeholder process mapping")
        track = get_interview_track_for_role_family(resolution.role_family, resolution.domain)

        self.assertEqual(track, "business analysis interview")

    def test_interview_track_for_ui_ux_designer_is_design_focused(self):
        candidate = {
            "current_title": "UI/UX Designer",
            "summary": "UI/UX Designer focused on Figma, wireframes, and user flows.",
            "skills": ["Figma", "Wireframes", "User flows", "Usability testing"],
        }

        resolution = resolve_candidate_role_resolution(candidate, "figma wireframes user flows usability testing")
        track = get_interview_track_for_role_family(resolution.role_family, resolution.domain)

        self.assertEqual(track, "design/portfolio interview")

    def test_interview_track_for_banking_finance_uses_domain_track(self):
        candidate = amber_like_finance_candidate()

        resolution = resolve_candidate_role_resolution(
            candidate,
            "BBA Banking and Finance financial analysis digital banking risk assessment",
        )
        track = get_interview_track_for_role_family(resolution.role_family, resolution.domain)

        self.assertEqual(track, "banking/finance interview")

    def test_interview_track_for_sales_marketing_uses_domain_track(self):
        candidate = {
            "current_title": "Sales Executive",
            "summary": "Sales Executive handling leads, campaigns, CRM updates and client communication.",
            "skills": ["Leads", "Campaigns", "CRM", "Client communication", "Conversion tracking"],
        }

        resolution = resolve_candidate_role_resolution(candidate, "sales leads campaigns crm conversion tracking")
        track = get_interview_track_for_role_family(resolution.role_family, resolution.domain)

        self.assertEqual(track, "sales/marketing interview")

    def test_interview_track_for_unknown_role_is_general_not_technical(self):
        candidate = {
            "current_title": None,
            "summary": "Motivated candidate with varied interests and mixed general skills.",
            "skills": ["Communication", "MS Office", "Teamwork", "Research"],
        }

        resolution = resolve_candidate_role_resolution(candidate, "general skills teamwork research")
        track = get_interview_track_for_role_family(resolution.role_family, resolution.domain)

        self.assertEqual(resolution.domain, UNCLEAR)
        self.assertEqual(track, "general screening interview")
        self.assertNotIn("technical", track)
        self.assertNotIn("code", track)

    def test_agent3_report_guidance_uses_resolved_family_not_detected_role_keywords(self):
        from app.agents.agent3_lead_evaluator import _report_structure_guidance

        candidate = amber_like_finance_candidate()
        resolution = resolve_candidate_role_resolution(
            candidate,
            "BBA Banking and Finance financial analysis digital banking risk assessment Volunteer Trainer",
        )

        guidance = _report_structure_guidance(
            NON_TECHNICAL,
            SKIP_NON_TECHNICAL,
            "Volunteer Trainer",
            resolution.role_family,
        )

        self.assertIn("banking/finance interview", guidance)
        self.assertNotIn("teaching/classroom interview", guidance)


if __name__ == "__main__":
    unittest.main()
