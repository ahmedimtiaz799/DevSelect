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
  const [isPaused, setIsPaused] = useState(false)

  useEffect(() => {
    if (isPaused) {
      const timeout = setTimeout(() => {
        setIsPaused(false)
        setIsDeleting(true)
      }, pauseTime)
      return () => clearTimeout(timeout)
    }

    const current = texts[textIndex]

    if (!isDeleting) {
      if (charIndex < current.length) {
        const timeout = setTimeout(() => {
          setDisplayText(current.slice(0, charIndex + 1))
          setCharIndex((prev) => prev + 1)
        }, typingSpeed)
        return () => clearTimeout(timeout)
      } else {
        setIsPaused(true)
      }
    } else {
      if (charIndex > 0) {
        const timeout = setTimeout(() => {
          setDisplayText(current.slice(0, charIndex - 1))
          setCharIndex((prev) => prev - 1)
        }, deletingSpeed)
        return () => clearTimeout(timeout)
      } else {
        setIsDeleting(false)
        setTextIndex((prev) => (prev + 1) % texts.length)
      }
    }
  }, [charIndex, isDeleting, isPaused, textIndex, texts, typingSpeed, deletingSpeed, pauseTime])

  return (
    <span>
      {displayText}
      <span className="animate-pulse">|</span>
    </span>
  )
}