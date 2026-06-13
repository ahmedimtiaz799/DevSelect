import { BackArrow } from '../auth/BackArrow'

export function AuthLayout({ children }) {
  return (
    <div className="relative min-h-screen bg-ds-bg flex flex-col items-center justify-center">
      <BackArrow />
      <div className="w-full max-w-sm px-6 flex flex-col items-center mt-8">
        <span className="text-ds-text-strong font-bold text-sm tracking-wide mb-6">
          DevSelect
        </span>
        {children}
      </div>
    </div>
  )
}
