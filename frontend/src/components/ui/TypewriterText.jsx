import { useState, useEffect } from 'react'

function TypewriterAnimation({ text, typingSpeed, className }) {
  const [displayed, setDisplayed] = useState('')
  const [done, setDone] = useState(false)

  useEffect(() => {
    let index = 0

    const interval = setInterval(() => {
      index++
      setDisplayed(text.slice(0, index))

      if (index === text.length) {
        clearInterval(interval)
        setDone(true)
      }
    }, typingSpeed)

    return () => clearInterval(interval)
  }, [text, typingSpeed])

  return (
    <span className={className}>
      {displayed}
      {!done && (
        <span className="inline-block w-[2px] h-[1em] bg-brand-dark ml-[1px] align-middle animate-pulse" />
      )}
    </span>
  )
}

function TypewriterText({ text, typingSpeed = 40, className = '' }) {
  return (
    <TypewriterAnimation
      key={`${text}:${typingSpeed}`}
      text={text}
      typingSpeed={typingSpeed}
      className={className}
    />
  )
}

export default TypewriterText
