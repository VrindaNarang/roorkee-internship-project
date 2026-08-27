import { API_ORIGIN } from './client'

export interface CopilotHistoryTurn {
  role: 'user' | 'assistant'
  content: string
}

interface CopilotChatPayload {
  question: string
  history: CopilotHistoryTurn[]
}

// The Copilot streams plain-text chunks over a single POST response body —
// axios isn't a great fit for reading a streaming fetch body in the browser,
// so this bypasses the shared `apiClient` and uses `fetch` directly.
const COPILOT_CHAT_URL = `${API_ORIGIN}/api/v1/copilot/chat`

export async function streamCopilotChat(
  payload: CopilotChatPayload,
  onChunk: (text: string) => void,
  signal?: AbortSignal,
): Promise<void> {
  const response = await fetch(COPILOT_CHAT_URL, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload),
    signal,
  })

  if (!response.ok || !response.body) {
    throw new Error(`Copilot request failed with status ${response.status}`)
  }

  const reader = response.body.getReader()
  const decoder = new TextDecoder()

  for (;;) {
    const { done, value } = await reader.read()
    if (done) break
    onChunk(decoder.decode(value, { stream: true }))
  }
}
