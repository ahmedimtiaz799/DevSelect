import { useEffect, useState } from 'react'

export function CyclingTypewriter({
  texts,
  typingSpeed = 35,
  deletingSpeed = 20,
  pauseTime = 1500,
}) {
  const [displayText, setDisplayText] = useState('')
  const [textIndex, setTextIndex] = useState(0)
  const [charIndex, setCharIndex] = useState(0)
  const [isDeleting, setIsDeleting] = useState(false)

  useEffect(() => {
    const current = texts[textIndex]
    let delay

    if (!isDeleting) {
      if (charIndex < current.length) {
        delay = typingSpeed
      } else {
        delay = pauseTime
      }
    } else {
      delay = charIndex > 0 ? deletingSpeed : 0
    }

    const timeout = setTimeout(() => {
      if (!isDeleting) {
        if (charIndex < current.length) {
          setDisplayText(current.slice(0, charIndex + 1))
          setCharIndex((prev) => prev + 1)
        } else {
          setIsDeleting(true)
        }
      } else if (charIndex > 0) {
          setDisplayText(current.slice(0, charIndex - 1))
          setCharIndex((prev) => prev - 1)
      } else {
        setIsDeleting(false)
        setTextIndex((prev) => (prev + 1) % texts.length)
      }
    }, delay)

    return () => clearTimeout(timeout)
  }, [charIndex, isDeleting, textIndex, texts, typingSpeed, deletingSpeed, pauseTime])

  return (
    <span>
      {displayText}
      <span className="animate-pulse">|</span>
    </span>
  )
}
