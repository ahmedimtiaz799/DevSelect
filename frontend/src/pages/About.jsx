import Navbar from '../components/layout/Navbar'

export function About() {
  return (
    <div className="min-h-screen bg-white">
      <Navbar />

      <div className="flex flex-col items-center px-6 py-16 md:py-20">

        <h1 className="text-display font-extrabold text-brand-dark mb-8 text-center">
          About
        </h1>

        <p className="text-body text-brand-secondary max-w-subtitle text-left mx-auto">
          I am Ahmed Imtiaz, a software Engineer who built DevSelect as a portfolio project. The idea came from thinking about how much time hiring managers spend reviewing CVs and GitHub profiles manually before even scheduling an interview. DevSelect tries to make that first filter faster and more informed. It scans a candidate's CV, looks through their GitHub activity, and gives you a straightforward answer on whether they are worth interviewing. This is not a funded startup. It is a real working product I built to demonstrate what I can do as a developer. If you are a hiring manager who finds it useful, that genuinely makes me happy.
        </p>

      </div>
    </div>
  )
}