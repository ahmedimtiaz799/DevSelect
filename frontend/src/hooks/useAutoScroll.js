import { useEffect, useRef, useState } from 'react'

export function useAutoScroll(messages) {
  const containerRef = useRef(null)
  const [shouldAutoScroll, setShouldAutoScroll] = useState(true)

  useEffect(() => {
    const container = containerRef.current
    if (!container) return

    function handleScroll() {
      const distanceFromBottom =
        container.scrollHeight - container.scrollTop - container.clientHeight

      if (distanceFromBottom < 100) {
        setShouldAutoScroll(true)
      } else {
        setShouldAutoScroll(false)
      }
    }

    container.addEventListener('scroll', handleScroll)
    return () => container.removeEventListener('scroll', handleScroll)
  }, [])

  useEffect(() => {
    if (!shouldAutoScroll) return
    const container = containerRef.current
    if (!container) return

    container.scrollTo({
      top: container.scrollHeight,
      behavior: 'smooth',
    })
  }, [messages, shouldAutoScroll])

  return containerRef
}