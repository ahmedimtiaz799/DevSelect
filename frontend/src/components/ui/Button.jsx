function Button({ children, variant = 'primary', size = 'md', onClick, disabled, type = 'button', className = '' }) {

  const base = 'inline-flex items-center justify-center rounded-btn font-semibold transition-all duration-200 disabled:opacity-50 disabled:cursor-not-allowed'

  const variants = {
    primary: 'bg-ds-button-primary text-ds-button-primary-text hover:bg-ds-button-primary-hover hover:scale-[1.02]',
    secondary: 'border-2 border-ds-accent text-ds-accent bg-transparent hover:bg-ds-accent hover:text-ds-text-inverse',
    ghost: 'text-ds-text-strong bg-transparent hover:text-ds-text-muted',
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
