import Navbar from '../components/layout/Navbar'
import { Footer } from '../components/layout/Footer'

export function About() {
  return (
    <div className="min-h-screen bg-white">
      <Navbar />

      <div className="flex flex-col items-center px-6 py-16 md:py-20">

        <h1 className="text-display font-extrabold text-brand-dark mb-8 text-center">
          About DevSelect
        </h1>

        <div className="text-body text-brand-secondary max-w-subtitle text-left mx-auto flex flex-col gap-5">
          <p>
            DevSelect is an AI-assisted hiring evaluation tool built by Ahmed
            Imtiaz, a Software Engineer focused on full-stack AI systems.
          </p>

          <p>
            The idea came from a simple problem: hiring teams spend too much
            time manually reviewing CVs and GitHub profiles before deciding who
            is worth interviewing.
          </p>

          <p>
            DevSelect helps with that first filter. It analyzes a candidate's
            CV, reviews their GitHub activity, and generates a structured hiring
            report with a clear recommendation.
          </p>

          <p>
            This is an independent portfolio project built to demonstrate
            production-style AI engineering, including CV parsing, GitHub
            analysis, multi-agent workflows, authentication, streaming
            responses, and saved chat history.
          </p>
        </div>

      </div>

      <Footer />
    </div>
  )
}
