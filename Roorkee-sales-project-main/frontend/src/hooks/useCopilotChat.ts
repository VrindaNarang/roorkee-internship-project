import { useCallback, useRef, useState } from 'react'
import { streamCopilotChat } from '../api/copilot'

export interface CopilotMessage {
  role: 'user' | 'assistant'
  content: string
}

// Owns the Copilot panel's conversation state — kept client-side only (not
// persisted server-side): the backend is stateless per request and receives
// the full history with each turn, matching Milestone 10's brief (no new
// chat-session tables, no RAG store).
export function useCopilotChat() {
  const [messages, setMessages] = useState<CopilotMessage[]>([])
  const [isStreaming, setIsStreaming] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const abortRef = useRef<AbortController | null>(null)

  const sendMessage = useCallback(
    async (question: string) => {
      const trimmed = question.trim()
      if (!trimmed || isStreaming) return

      setError(null)
      const history = messages.map((m) => ({ role: m.role, content: m.content }))
      setMessages((prev) => [...prev, { role: 'user', content: trimmed }, { role: 'assistant', content: '' }])
      setIsStreaming(true)

      const controller = new AbortController()
      abortRef.current = controller

      try {
        await streamCopilotChat(
          { question: trimmed, history },
          (chunk) => {
            setMessages((prev) => {
              const next = [...prev]
              const last = next[next.length - 1]
              next[next.length - 1] = { ...last, content: last.content + chunk }
              return next
            })
          },
          controller.signal,
        )
      } catch (err) {
        if ((err as Error).name !== 'AbortError') {
          setError(
            'The Sales Copilot is unreachable right now — check that the backend is running and an LLM provider is configured.',
          )
        }
      } finally {
        setIsStreaming(false)
        abortRef.current = null
      }
    },
    [messages, isStreaming],
  )

  const clear = useCallback(() => {
    abortRef.current?.abort()
    setMessages([])
    setError(null)
  }, [])

  return { messages, isStreaming, error, sendMessage, clear }
}
