import { useNavigate } from 'react-router-dom'
import Navbar from '../components/layout/Navbar'
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
    <div className="min-h-screen bg-white">
      <Navbar />

      <main className="flex flex-col items-center px-6 py-14 md:py-20">
        <section className="w-full max-w-4xl text-center mb-10 md:mb-12">
          <h1 className="text-3xl sm:text-4xl md:text-display font-extrabold text-brand-dark mb-5">
            Start evaluating candidates for free during beta
          </h1>

          <p className="text-base md:text-body text-brand-secondary max-w-3xl mx-auto">
            Upload a CV and GitHub profile to generate an AI-assisted hiring
            report. Fair-use limits apply while DevSelect is in beta.
          </p>
        </section>

        <section className="w-full max-w-lg">
          <div className="bg-white border border-gray-200 rounded-2xl shadow-card px-6 py-7 sm:px-8 sm:py-8">
            <p className="inline-flex items-center rounded-pill border border-brand-dark/15 bg-brand-surfaceSubtle px-3 py-1 text-badge text-brand-muted uppercase mb-5 select-none">
              Beta Access
            </p>

            <div className="mb-6">
              <h2 className="text-2xl font-extrabold text-brand-dark mb-3">
                Free during beta
              </h2>

              <div className="flex items-end gap-2 mb-4">
                <p className="text-price font-black text-brand-dark select-none">
                  $0
                </p>
                <p className="text-sm text-brand-muted pb-1">
                  / month
                </p>
              </div>

              <p className="text-ui text-brand-secondary leading-6">
                For early users testing AI-assisted candidate evaluation before
                public launch.
              </p>
            </div>

            <ul className="grid gap-4 mb-8">
              {features.map((feature) => (
                <li
                  key={feature}
                  className="flex items-start gap-3 text-ui text-brand-dark"
                >
                  <CheckCircle
                    size={18}
                    className="text-brand-dark shrink-0 mt-0.5"
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

            <p className="text-center text-sm text-brand-muted mt-4">
              No credit card required
            </p>
          </div>

          <p className="text-center text-sm text-brand-muted leading-6 mt-5">
            DevSelect is currently in beta. Usage may be limited to keep
            evaluations fast, reliable, and cost-controlled.
          </p>
        </section>
      </main>
    </div>
  )
}
