import { Link } from 'react-router-dom'

const productLinks = [
  ['Home', '/'],
  ['Pricing', '/pricing'],
  ['About', '/about'],
  ['Get Started', '/signup'],
]

const evaluationItems = [
  'CV review',
  'GitHub analysis',
  'Hiring report',
  'Saved chat history',
]

const trustItems = [
  'Secure PDF upload',
  'Authenticated access',
  'Beta fair-use limits',
  'No credit card required',
]

const externalLinks = [
  ['GitHub', 'https://github.com/ahmedimtiaz799'],
  ['LinkedIn', 'https://www.linkedin.com/in/ahmed-imtiaz-769ba7342'],
]

function FooterHeading({ children }) {
  return (
    <h2 className="text-[11px] font-bold uppercase tracking-widest text-white/55">
      {children}
    </h2>
  )
}

function FooterLink({ children, to }) {
  return (
    <Link
      to={to}
      className="text-sm text-white/75 transition-colors hover:text-white focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-white/60 rounded-sm"
    >
      {children}
    </Link>
  )
}

function ExternalLink({ children, href }) {
  return (
    <a
      href={href}
      target="_blank"
      rel="noopener noreferrer"
      className="text-sm text-white/75 transition-colors hover:text-white focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-white/60 rounded-sm"
    >
      {children}
    </a>
  )
}

export function Footer() {
  return (
    <footer className="bg-brand-dark text-white">
      <div className="mx-auto max-w-7xl px-6 py-16 md:px-8 md:py-[72px]">
        <div className="grid gap-x-10 gap-y-11 sm:grid-cols-2 lg:grid-cols-[1.75fr_repeat(5,minmax(0,1fr))]">
          <div>
            <Link
              to="/"
              className="inline-flex text-lg font-extrabold tracking-wide text-white transition-colors hover:text-white/85 focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-white/60 rounded-sm"
            >
              DevSelect
            </Link>

            <p className="mt-4 max-w-sm text-sm leading-6 text-white/60">
              AI-assisted candidate evaluation from CV and GitHub evidence.
              Built as an independent full-stack AI engineering project.
            </p>

            <p className="mt-4 text-xs font-semibold tracking-wide text-white/45">
              Currently in beta &middot; Fair-use limits apply
            </p>
          </div>

          <div>
            <FooterHeading>Product</FooterHeading>
            <nav className="mt-4 flex flex-col gap-3">
              {productLinks.map(([label, to]) => (
                <FooterLink key={label} to={to}>
                  {label}
                </FooterLink>
              ))}
            </nav>
          </div>

          <div>
            <FooterHeading>Evaluation</FooterHeading>
            <ul className="mt-4 flex flex-col gap-3">
              {evaluationItems.map((item) => (
                <li key={item} className="text-sm text-white/70">
                  {item}
                </li>
              ))}
            </ul>
          </div>

          <div>
            <FooterHeading>Trust</FooterHeading>
            <ul className="mt-4 flex flex-col gap-3">
              {trustItems.map((item) => (
                <li key={item} className="text-sm text-white/70">
                  {item}
                </li>
              ))}
            </ul>
          </div>

          <div>
            <FooterHeading>Legal</FooterHeading>
            <nav className="mt-4 flex flex-col gap-3">
              <FooterLink to="/terms">Terms</FooterLink>
              <FooterLink to="/privacy">Privacy Policy</FooterLink>
            </nav>
          </div>

          <div>
            <FooterHeading>Connect</FooterHeading>
            <div className="mt-4 flex flex-col gap-3">
              {externalLinks.map(([label, href]) => (
                <ExternalLink key={label} href={href}>
                  {label}
                </ExternalLink>
              ))}
              <a
                href="mailto:ahmed.awan9839@gmail.com"
                className="text-sm text-white/75 transition-colors hover:text-white focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-white/60 rounded-sm"
              >
                <span className="sm:hidden">Email</span>
                <span className="hidden sm:inline">ahmed.awan9839@gmail.com</span>
              </a>
            </div>
          </div>
        </div>

        <div className="mt-12 border-t border-white/10 pt-6">
          <p className="text-xs text-white/45">
            &copy; 2026 DevSelect. Built by Ahmed Imtiaz.
          </p>
        </div>
      </div>
    </footer>
  )
}
