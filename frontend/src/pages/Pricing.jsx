import { useNavigate } from 'react-router-dom'
import Navbar from '../components/layout/Navbar'
import Button from '../components/ui/Button'
import { CheckCircle } from 'lucide-react'

function Pricing() {
  const navigate = useNavigate()

  const features = [
    'Unlimited CV scans',
    'GitHub repository analysis',
    'Hire or no hire recommendations',
    'Chat history saved',
    'Free during beta',
  ]

  return (
    <div className="min-h-screen bg-white">
      <Navbar />

      <div className="flex flex-col items-center justify-center px-6 py-16 md:py-20">

        <h1 className="text-display font-extrabold text-brand-dark mb-12">
          Pricing
        </h1>

        <div className="bg-gray-50 rounded-card shadow-card px-10 py-10 w-full max-w-xs">

          <p className="text-badge text-brand-muted tracking-widest uppercase mb-3 select-none">
            Beta Access
          </p>

          <p className="text-price font-black text-brand-dark mb-8 select-none">
            $0
          </p>

          <ul className="flex flex-col gap-4 mb-10">
            {features.map((feature) => (
              <li key={feature} className="flex items-center gap-3 text-ui text-brand-dark">
                <CheckCircle size={18} className="text-brand-dark shrink-0" />
                {feature}
              </li>
            ))}
          </ul>

          <Button
            variant="primary"
            size="md"
            onClick={() => navigate('/signup')}
            className="w-full"
          >
            Get Started
          </Button>

        </div>

      </div>
    </div>
  )
}

export default Pricing