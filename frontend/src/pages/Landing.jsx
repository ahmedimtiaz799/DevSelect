import { useNavigate } from 'react-router-dom'
import Navbar from '../components/layout/Navbar'
import Button from '../components/ui/Button'
import TypewriterText from '../components/ui/TypewriterText'

export function Landing() {
  const navigate = useNavigate()

  return (
    <div className="min-h-screen bg-white">
      <Navbar />
      <div className="flex flex-col items-center justify-center text-center px-6 py-16 md:py-24 lg:py-32">
        <h1 className="text-3xl sm:text-4xl md:text-display lg:text-hero font-extrabold text-brand-dark max-w-hero leading-tight mb-6">
          Know Who to Hire Before the Interview
        </h1>
        <p className="text-base md:text-body text-brand-secondary max-w-subtitle mb-10 min-h-[40px]">
          <TypewriterText
            text="DevSelect looks at every candidates CV and GitHub activity and gives you a straight answer on whether they are worth hiring."
            typingSpeed={30}
          />
        </p>
        <Button
          variant="primary"
          size="lg"
          onClick={() => navigate('/signup')}
        >
          Get Started
        </Button>
      </div>
    </div>
  )
}