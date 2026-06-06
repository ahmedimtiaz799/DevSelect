import Navbar from '../components/layout/Navbar'
import { Footer } from '../components/layout/Footer'

const privacySections = [
  {
    title: 'Information you provide',
    text: 'When you use DevSelect, you may provide account information such as your name, email address, and login provider. You may also upload CV files or provide GitHub profile information for evaluation.',
  },
  {
    title: 'CV and GitHub evaluation data',
    text: 'DevSelect processes uploaded CV content and GitHub activity to generate candidate evaluation reports. This may include skills, projects, education, repositories, commits, languages, README and documentation details.',
  },
  {
    title: 'Saved chat history and reports',
    text: 'DevSelect may save your chats, uploaded file references, generated reports, and final error messages so you can return to previous evaluations.',
  },
  {
    title: 'How the information is used',
    text: 'We use this information to run evaluations, generate reports, save chat history, improve reliability, protect accounts, and troubleshoot errors.',
  },
  {
    title: 'Services used to run DevSelect',
    text: 'DevSelect uses third-party services for authentication, database/storage, AI processing, GitHub review, and error monitoring. These services help the app work, but DevSelect does not sell your data.',
  },
  {
    title: 'Your responsibility',
    text: 'Please do not upload CVs or documents unless you have permission to process them. Avoid uploading unnecessary sensitive information.',
  },
  {
    title: 'Updates',
    text: 'This policy may be updated as DevSelect changes during beta.',
  },
]

export function Privacy() {
  return (
    <div className="min-h-screen bg-white">
      <Navbar />

      <main className="px-6 py-16 md:py-24">
        <article className="mx-auto max-w-3xl">
          <p className="text-sm font-semibold text-brand-muted mb-4">
            Last updated: June 2026
          </p>

          <h1 className="text-3xl md:text-display font-extrabold text-brand-dark mb-6">
            Privacy Policy
          </h1>

          <p className="text-base md:text-body text-brand-secondary mb-10">
            DevSelect is currently in beta. This page explains what information
            the app uses and why.
          </p>

          <div className="flex flex-col gap-8">
            {privacySections.map((section) => (
              <section key={section.title}>
                <h2 className="text-xl font-extrabold text-brand-dark mb-3">
                  {section.title}
                </h2>

                <p className="text-base md:text-body text-brand-secondary">
                  {section.text}
                </p>
              </section>
            ))}

            <section>
              <h2 className="text-xl font-extrabold text-brand-dark mb-3">
                Data requests
              </h2>

              <p className="text-base md:text-body text-brand-secondary">
                If you want help with your account data or want to request
                deletion, contact:{' '}
                <a
                  href="mailto:ahmed.awan9839@gmail.com"
                  className="font-semibold text-brand-dark underline underline-offset-4"
                >
                  ahmed.awan9839@gmail.com
                </a>
              </p>
            </section>
          </div>
        </article>
      </main>

      <Footer />
    </div>
  )
}
