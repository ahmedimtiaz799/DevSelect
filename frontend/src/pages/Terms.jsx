import Navbar from '../components/layout/Navbar'
import { Footer } from '../components/layout/Footer'

const termsSections = [
  {
    title: 'Using DevSelect',
    text: 'DevSelect helps review candidate CVs and GitHub activity to create an AI-assisted hiring report. The report is meant to support the first screening step, not replace human judgment.',
  },
  {
    title: 'Permission to upload documents',
    text: 'Only upload CVs, documents, or GitHub profiles that you are allowed to review. Do not upload private or sensitive documents unless you have permission to use them for candidate evaluation.',
  },
  {
    title: 'AI-assisted reports',
    text: 'DevSelect uses AI to generate reports. AI output can be incomplete or incorrect, so you should review the results before making any hiring or interview decision.',
  },
  {
    title: 'Beta access and fair use',
    text: 'DevSelect is in beta, so access may be limited, changed, paused, or updated as the product improves. Fair-use limits may apply to keep evaluations reliable and cost-controlled.',
  },
  {
    title: 'User responsibility',
    text: 'Do not misuse DevSelect, attempt to abuse the service, upload harmful files, or use the product for unlawful or discriminatory purposes.',
  },
  {
    title: 'Changes to the product',
    text: 'Features, limits, and availability may change during beta. DevSelect may update these terms as the product evolves.',
  },
]

export function Terms() {
  return (
    <div className="min-h-screen bg-white">
      <Navbar />

      <main className="px-6 py-16 md:py-24">
        <article className="mx-auto max-w-3xl">
          <p className="text-sm font-semibold text-brand-muted mb-4">
            Last updated: June 2026
          </p>

          <h1 className="text-3xl md:text-display font-extrabold text-brand-dark mb-6">
            Terms of Use
          </h1>

          <p className="text-base md:text-body text-brand-secondary mb-10">
            DevSelect is currently in beta. These terms explain how you should
            use the product while it is being developed and tested.
          </p>

          <div className="flex flex-col gap-8">
            {termsSections.map((section) => (
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
                Contact
              </h2>

              <p className="text-base md:text-body text-brand-secondary">
                If you have questions about these terms, contact:{' '}
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
