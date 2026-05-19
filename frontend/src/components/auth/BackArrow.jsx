import { useNavigate } from 'react-router-dom'

export function BackArrow() {
  const navigate = useNavigate()

  return (
    <button
      onClick={() => navigate('/')}
      className="absolute top-6 left-6 flex items-center gap-2 text-brand-dark hover:opacity-70 transition-opacity"
    >
      <svg
        xmlns="http://www.w3.org/2000/svg"
        width="20"
        height="20"
        fill="none"
        viewBox="0 0 24 24"
        stroke="currentColor"
        strokeWidth={2}
      >
        <path strokeLinecap="round" strokeLinejoin="round" d="M10 19l-7-7m0 0l7-7m-7 7h18" />
      </svg>
      <span className="text-sm font-medium">Back to home</span>
    </button>
  )
}