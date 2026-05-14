function Button({ children, variant = 'primary', size = 'md', onClick, disabled, type = 'button', className = '' }) {

  const base = 'inline-flex items-center justify-center rounded-btn font-semibold transition-all duration-200 disabled:opacity-50 disabled:cursor-not-allowed'

  const variants = {
    primary: 'bg-brand-dark text-white hover:bg-opacity-90 hover:scale-[1.02]',
    secondary: 'border-2 border-brand-dark text-brand-dark bg-transparent hover:bg-brand-dark hover:text-white',
    ghost: 'text-brand-dark bg-transparent hover:text-brand-muted',
  }

  const sizes = {
    lg: 'text-btn-lg px-8 py-3',
    md: 'text-btn-md px-6 py-2.5',
    sm: 'text-btn-sm px-4 py-2',
  }

  return (
    <button
      type={type}
      onClick={onClick}
      disabled={disabled}
      aria-disabled={disabled}
      className={`${base} ${variants[variant]} ${sizes[size]} ${className}`}
    >
      {children}
    </button>
  )
}

export default Button