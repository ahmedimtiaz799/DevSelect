import { useState, useEffect } from 'react'

function TypewriterText({ text, typingSpeed = 40, className = '' }) {
  const [displayed, setDisplayed] = useState('')
  const [done, setDone] = useState(false)

  useEffect(() => {
    setDisplayed('')
    setDone(false)

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

export default TypewriterText