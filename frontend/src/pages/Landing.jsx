import { useNavigate } from 'react-router-dom'
import { ChevronRight } from 'lucide-react'
import Navbar from '../components/layout/Navbar'
import { Footer } from '../components/layout/Footer'
import Button from '../components/ui/Button'

const flowSteps = [
  {
    number: '01',
    title: 'CV reviewed',
    text: 'Skills, projects, education, certifications, and role fit are reviewed from the uploaded CV.',
  },
  {
    number: '02',
    title: 'GitHub reviewed',
    text: 'Repositories, commits, languages, README coverage, and project activity are checked as supporting evidence.',
  },
  {
    number: '03',
    title: 'Report generated',
    text: 'The final report summarizes strengths, risks, skill match, and a clear interview recommendation.',
  },
]

const reportChecks = [
  {
    title: 'CV evidence',
    text: 'Skills, experience, projects, education, and certifications from the uploaded CV.',
  },
  {
    title: 'GitHub evidence',
    text: 'Repositories, commits, languages, README coverage, and recent development activity.',
  },
  {
    title: 'Project quality',
    text: 'Complexity, documentation habits, consistency, and ownership signals across projects.',
  },
  {
    title: 'Recommendation',
    text: 'Strengths, risks, skill match, and suggested next steps before the interview.',
  },
]

export function Landing() {
  const navigate = useNavigate()

  return (
    <div className="min-h-screen bg-white">
      <Navbar />

      <main>
        <section className="flex flex-col items-center justify-center text-center px-6 py-16 md:py-24 lg:py-28">
          <h1 className="text-3xl sm:text-4xl md:text-display lg:text-hero font-extrabold text-brand-dark max-w-hero leading-tight mb-6">
            Know Who to Hire Before the Interview
          </h1>

          <p className="text-base md:text-body text-brand-secondary max-w-subtitle mb-10">
            DevSelect reviews a candidate's CV and GitHub activity, then
            generates a structured hiring report with a clear recommendation.
          </p>

          <Button
            variant="primary"
            size="lg"
            onClick={() => navigate('/signup')}
          >
            Get Started
          </Button>
        </section>

        <section className="px-6 py-14 md:py-20 bg-brand-surfaceSubtle">
          <div className="max-w-5xl mx-auto">
            <div className="text-center max-w-3xl mx-auto mb-10">
              <h2 className="text-3xl md:text-display font-extrabold text-brand-dark mb-4">
                A hiring report built from real candidate evidence
              </h2>

              <p className="text-base md:text-body text-brand-secondary">
                DevSelect combines CV details with GitHub activity, then
                summarizes the result in a clear report your team can review
                before the interview.
              </p>
            </div>

            <div className="mx-auto max-w-4xl overflow-hidden rounded-2xl border border-gray-200 bg-page-chat shadow-card">
              <div className="grid min-h-[560px] grid-cols-[48px_1fr] sm:grid-cols-[56px_1fr]">
                <div className="bg-brand-dark px-2 py-4 flex flex-col items-center gap-4">
                  <div className="h-8 w-8 rounded-md text-white/55 flex items-center justify-center">
                    <ChevronRight size={16} />
                  </div>
                  <div className="h-9 w-9 rounded-lg bg-white text-brand-dark text-lg font-semibold flex items-center justify-center">
                    +
                  </div>
                  <div className="mt-auto h-9 w-9 rounded-full bg-[#F4511E] text-white text-sm font-extrabold flex items-center justify-center">
                    A
                  </div>
                </div>

                <div className="min-w-0 flex flex-col bg-page-chat">
                  <div className="h-14 border-b border-gray-100 bg-white px-4 sm:px-6 flex items-center">
                    <h3 className="truncate text-logo-chat text-brand-dark font-extrabold">
                      Ali Hamza — Full Stack AI Engineer
                    </h3>
                  </div>

                  <div className="flex-1 px-4 py-5 sm:px-6 sm:py-6">
                    <div className="mx-auto flex max-w-2xl flex-col gap-5">
                      <div className="flex justify-end">
                        <div className="max-w-xs rounded-bubble bg-brand-userBubble px-2 py-2 text-brand-body">
                          <div className="flex items-center gap-2 min-w-0 rounded-lg border border-brand-dark/10 bg-white/70 px-2.5 py-2">
                            <span className="flex h-7 w-7 shrink-0 items-center justify-center rounded-md bg-brand-dark/10 text-brand-dark">
                              CV
                            </span>

                            <span className="min-w-0 text-left">
                              <span className="block truncate text-sm font-medium leading-5 text-brand-body">
                                ali_hamza_cv.pdf
                              </span>
                              <span className="block text-xs leading-4 text-brand-muted">
                                CV uploaded
                              </span>
                            </span>
                          </div>
                        </div>
                      </div>

                      <div className="min-w-0 px-1 py-2 sm:px-2 sm:py-3">
                        <div className="grid gap-5 text-left">
                          <section>
                            <h4 className="text-lg font-bold text-brand-dark mb-2">
                              Candidate Overview
                            </h4>
                            <div className="grid gap-1 text-msg text-brand-body">
                              <p>
                                <strong className="text-brand-dark font-semibold">
                                  Candidate Name:
                                </strong>{' '}
                                Ali Hamza
                              </p>
                              <p>
                                <strong className="text-brand-dark font-semibold">
                                  Detected Role:
                                </strong>{' '}
                                Full Stack AI Engineer
                              </p>
                              <p>
                                <strong className="text-brand-dark font-semibold">
                                  Seniority Level:
                                </strong>{' '}
                                Junior
                              </p>
                            </div>
                          </section>

                          <section>
                            <h4 className="text-lg font-bold text-brand-dark mb-2">
                              CV & Experience Review
                            </h4>
                            <p className="text-msg text-brand-body">
                              Strong evidence of full-stack AI work across
                              LangGraph, FastAPI, React, and RAG pipelines.
                            </p>
                          </section>

                          <section>
                            <h4 className="text-lg font-bold text-brand-dark mb-2">
                              GitHub Profile Review
                            </h4>
                            <p className="text-msg text-brand-body">
                              Verified repositories show consistent project work
                              across AI, backend, and frontend development.
                            </p>
                          </section>

                          <section>
                            <h4 className="text-lg font-bold text-brand-dark mb-2">
                              Skill Match Assessment
                            </h4>
                            <p className="text-msg text-brand-body">
                              Good alignment with Full Stack AI Engineer
                              requirements.
                            </p>
                          </section>

                          <section>
                            <h4 className="text-lg font-bold text-brand-dark mb-2">
                              Hiring Recommendation
                            </h4>
                            <p className="text-msg text-brand-body">
                              <strong className="text-brand-dark font-semibold">
                                Recommendation:
                              </strong>{' '}
                              Interview
                            </p>
                          </section>
                        </div>
                      </div>
                    </div>
                  </div>

                  <div className="border-t border-gray-100 bg-white px-4 py-3 sm:px-6">
                    <div className="mx-auto max-w-3xl rounded-input bg-brand-inputBg px-4 py-3 text-left text-sm text-brand-muted">
                      Ask a follow-up about this candidate...
                    </div>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </section>

        <section className="px-6 py-14 md:py-20">
          <div className="max-w-5xl mx-auto grid gap-10 lg:grid-cols-[0.9fr_1.1fr] lg:items-start">
            <div>
              <h2 className="text-3xl md:text-display font-extrabold text-brand-dark mb-5">
                The evaluation flow
              </h2>

              <p className="text-base md:text-body text-brand-secondary">
                DevSelect turns candidate evidence into a structured hiring
                report by reviewing the CV and GitHub activity before
                generating a recommendation.
              </p>
            </div>

            <ol className="border-l border-gray-200">
              {flowSteps.map((step) => (
                <li key={step.number} className="relative pl-6 pb-8 last:pb-0">
                  <span className="absolute -left-[17px] top-0 flex h-8 w-8 items-center justify-center rounded-full bg-brand-dark text-white text-xs font-bold">
                    {step.number}
                  </span>

                  <h3 className="text-xl font-extrabold text-brand-dark mb-2">
                    {step.title}
                  </h3>

                  <p className="text-ui text-brand-secondary leading-6">
                    {step.text}
                  </p>
                </li>
              ))}
            </ol>
          </div>
        </section>

        <section className="px-6 py-14 md:py-20 bg-brand-surfaceSubtle">
          <div className="max-w-5xl mx-auto">
            <div className="text-center max-w-3xl mx-auto mb-10">
              <h2 className="text-3xl md:text-display font-extrabold text-brand-dark mb-4">
                What the report checks
              </h2>

              <p className="text-base md:text-body text-brand-secondary">
                DevSelect focuses the first screening step on candidate
                evidence, not guesswork.
              </p>
            </div>

            <div className="bg-white border border-gray-200 rounded-2xl shadow-card overflow-hidden">
              {reportChecks.map((item, index) => (
                <div
                  key={item.title}
                  className={`grid gap-2 px-5 py-5 sm:grid-cols-[220px_1fr] sm:gap-6 sm:px-7 ${
                    index === reportChecks.length - 1
                      ? ''
                      : 'border-b border-gray-200'
                  }`}
                >
                  <h3 className="text-lg font-extrabold text-brand-dark">
                    {item.title}
                  </h3>

                  <p className="text-ui text-brand-secondary leading-6">
                    {item.text}
                  </p>
                </div>
              ))}
            </div>

            <div className="text-center mt-8">
              <Button
                variant="primary"
                size="md"
                onClick={() => navigate('/signup')}
              >
                Start with a free beta evaluation
              </Button>
            </div>
          </div>
        </section>
      </main>

      <Footer />
    </div>
  )
}
