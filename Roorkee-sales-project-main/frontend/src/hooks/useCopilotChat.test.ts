import { act, renderHook, waitFor } from '@testing-library/react'
import { describe, expect, it, vi } from 'vitest'
import { useCopilotChat } from './useCopilotChat'
import { streamCopilotChat } from '../api/copilot'

vi.mock('../api/copilot', () => ({
  streamCopilotChat: vi.fn(),
}))

const mockedStream = vi.mocked(streamCopilotChat)

describe('useCopilotChat', () => {
  it('appends a user message and a streamed assistant message', async () => {
    mockedStream.mockImplementation(async (_payload, onChunk) => {
      onChunk('Business Insight: ')
      onChunk('revenue is up.')
    })

    const { result } = renderHook(() => useCopilotChat())

    await act(async () => {
      await result.current.sendMessage('Why did sales increase?')
    })

    expect(result.current.messages).toEqual([
      { role: 'user', content: 'Why did sales increase?' },
      { role: 'assistant', content: 'Business Insight: revenue is up.' },
    ])
    expect(result.current.isStreaming).toBe(false)
    expect(result.current.error).toBeNull()
  })

  it('sets an error message when the stream fails', async () => {
    mockedStream.mockRejectedValue(new Error('network down'))

    const { result } = renderHook(() => useCopilotChat())

    await act(async () => {
      await result.current.sendMessage('Which customers are at risk?')
    })

    await waitFor(() => expect(result.current.error).not.toBeNull())
    expect(result.current.isStreaming).toBe(false)
  })

  it('ignores blank questions', async () => {
    mockedStream.mockClear()
    const { result } = renderHook(() => useCopilotChat())

    await act(async () => {
      await result.current.sendMessage('   ')
    })

    expect(mockedStream).not.toHaveBeenCalled()
    expect(result.current.messages).toEqual([])
  })

  it('clear() resets messages and error state', async () => {
    mockedStream.mockImplementation(async (_payload, onChunk) => {
      onChunk('some answer')
    })
    const { result } = renderHook(() => useCopilotChat())

    await act(async () => {
      await result.current.sendMessage('Summarize sales')
    })
    expect(result.current.messages.length).toBeGreaterThan(0)

    act(() => {
      result.current.clear()
    })

    expect(result.current.messages).toEqual([])
    expect(result.current.error).toBeNull()
  })
})
