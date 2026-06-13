import { useNavigate } from 'react-router-dom'
import Navbar from '../components/layout/Navbar'
import { Footer } from '../components/layout/Footer'
import Button from '../components/ui/Button'
import { CheckCircle } from 'lucide-react'

export function Pricing() {
  const navigate = useNavigate()

  const features = [
    'AI CV evaluation',
    'GitHub repository analysis',
    'Structured Hire / No-Hire recommendation',
    'Saved chat history',
    'Secure PDF upload',
    'Fair-use beta access',
  ]

  return (
    <div className="min-h-screen bg-ds-bg">
      <Navbar />

      <main className="flex flex-col items-center px-6 py-14 md:py-20">
        <section className="w-full max-w-4xl text-center mb-10 md:mb-12">
          <h1 className="text-3xl sm:text-4xl font-extrabold text-ds-text-strong mb-5">
            Start evaluating candidates for free during beta
          </h1>

          <p className="text-base md:text-body text-ds-text-secondary max-w-3xl mx-auto">
            Upload a CV and GitHub profile to generate an AI-assisted hiring
            report. Fair-use limits apply while DevSelect is in beta.
          </p>
        </section>

        <section className="w-full max-w-lg">
          <div className="bg-ds-surface border border-ds-border rounded-2xl shadow-card px-6 py-7 sm:px-8 sm:py-8">
            <p className="inline-flex items-center rounded-pill border border-brand-dark/15 bg-ds-surface-subtle px-3 py-1 text-badge text-ds-text-muted uppercase mb-5 select-none">
              Beta Access
            </p>

            <div className="mb-6">
              <h2 className="text-2xl font-extrabold text-ds-text-strong mb-3">
                Free during beta
              </h2>

              <div className="flex items-end gap-2 mb-4">
                <p className="text-price font-black text-ds-text-strong select-none">
                  $0
                </p>
                <p className="text-sm text-ds-text-muted pb-1">
                  / month
                </p>
              </div>

              <p className="text-ui text-ds-text-secondary leading-6">
                For early users testing AI-assisted candidate evaluation before
                public launch.
              </p>
            </div>

            <ul className="grid gap-4 mb-8">
              {features.map((feature) => (
                <li
                  key={feature}
                  className="flex items-start gap-3 text-ui text-ds-text-strong"
                >
                  <CheckCircle
                    size={18}
                    className="text-ds-text-strong shrink-0 mt-0.5"
                  />
                  <span>{feature}</span>
                </li>
              ))}
            </ul>

            <Button
              variant="primary"
              size="md"
              onClick={() => navigate('/signup')}
              className="w-full"
            >
              Start Free Evaluation
            </Button>

            <p className="text-center text-sm text-ds-text-muted mt-4">
              No credit card required
            </p>
          </div>

          <p className="text-center text-sm text-ds-text-muted leading-6 mt-5">
            DevSelect is currently in beta. Usage may be limited to keep
            evaluations fast, reliable, and cost-controlled.
          </p>
        </section>
      </main>

      <Footer />
    </div>
  )
}
