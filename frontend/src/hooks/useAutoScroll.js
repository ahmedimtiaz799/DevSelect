import { useEffect, useRef } from 'react'

export function useAutoScroll(messages, layoutKey = '') {
  const containerRef = useRef(null)
  const shouldAutoScrollRef = useRef(true)
  const frameRef = useRef(null)

  useEffect(() => {
    const container = containerRef.current
    if (!container) return

    function isNearBottom() {
      return (
        container.scrollHeight -
          container.scrollTop -
          container.clientHeight <
        120
      )
    }

    function handleScroll() {
      shouldAutoScrollRef.current = isNearBottom()
    }

    container.addEventListener('scroll', handleScroll)
    shouldAutoScrollRef.current = isNearBottom()

    return () => {
      container.removeEventListener('scroll', handleScroll)
      if (frameRef.current) {
        cancelAnimationFrame(frameRef.current)
      }
    }
  }, [])

  useEffect(() => {
    const container = containerRef.current
    if (!container || !shouldAutoScrollRef.current) return

    if (frameRef.current) {
      cancelAnimationFrame(frameRef.current)
    }

    frameRef.current = requestAnimationFrame(() => {
      container.scrollTop = container.scrollHeight
    })
  }, [messages, layoutKey])

  return containerRef
}
