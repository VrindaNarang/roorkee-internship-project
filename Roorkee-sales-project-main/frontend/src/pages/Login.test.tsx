import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { AxiosError } from 'axios'
import { MemoryRouter } from 'react-router-dom'
import { describe, expect, it, vi } from 'vitest'
import Login from './Login'
import { useAuth } from '../context/AuthContext'

vi.mock('../context/AuthContext', () => ({
  useAuth: vi.fn(),
}))

const mockedUseAuth = vi.mocked(useAuth)

function renderLogin() {
  return render(
    <MemoryRouter initialEntries={['/login']} future={{ v7_startTransition: true, v7_relativeSplatPath: true }}>
      <Login />
    </MemoryRouter>,
  )
}

describe('Login page', () => {
  it('fills in a demo account email/password when a demo account button is clicked', async () => {
    mockedUseAuth.mockReturnValue({ login: vi.fn(), logout: vi.fn(), user: null, status: 'unauthenticated' })
    renderLogin()

    await userEvent.click(screen.getByRole('button', { name: /Admin.*admin@salespilot\.example\.com/ }))

    expect(screen.getByRole('textbox', { name: 'Email address' })).toHaveValue('admin@salespilot.example.com')
  })

  it('calls login with the entered credentials on submit', async () => {
    const login = vi.fn().mockResolvedValue(undefined)
    mockedUseAuth.mockReturnValue({ login, logout: vi.fn(), user: null, status: 'unauthenticated' })
    renderLogin()

    await userEvent.type(screen.getByRole('textbox', { name: 'Email address' }), 'manager@salespilot.example.com')
    await userEvent.type(screen.getByLabelText('Password'), 'ChangeMe123!')
    await userEvent.click(screen.getByRole('button', { name: 'Sign In' }))

    expect(login).toHaveBeenCalledWith('manager@salespilot.example.com', 'ChangeMe123!')
  })

  it('shows "incorrect email or password" for a genuine 401 from the API', async () => {
    const unauthorized = new AxiosError('Request failed with status code 401', '401', undefined, undefined, {
      status: 401,
      data: { detail: 'Incorrect email or password' },
    } as never)
    const login = vi.fn().mockRejectedValue(unauthorized)
    mockedUseAuth.mockReturnValue({ login, logout: vi.fn(), user: null, status: 'unauthenticated' })
    renderLogin()

    await userEvent.type(screen.getByRole('textbox', { name: 'Email address' }), 'nobody@example.com')
    await userEvent.type(screen.getByLabelText('Password'), 'wrong-password')
    await userEvent.click(screen.getByRole('button', { name: 'Sign In' }))

    expect(await screen.findByText('Incorrect email or password.')).toBeInTheDocument()
  })

  it('shows a distinct "can\'t reach the server" message when the API is unreachable, not a credentials error', async () => {
    const networkError = new AxiosError('Network Error')
    const login = vi.fn().mockRejectedValue(networkError)
    mockedUseAuth.mockReturnValue({ login, logout: vi.fn(), user: null, status: 'unauthenticated' })
    renderLogin()

    await userEvent.type(screen.getByRole('textbox', { name: 'Email address' }), 'admin@salespilot.example.com')
    await userEvent.type(screen.getByLabelText('Password'), 'ChangeMe123!')
    await userEvent.click(screen.getByRole('button', { name: 'Sign In' }))

    expect(await screen.findByText(/Can't reach the server/i)).toBeInTheDocument()
    expect(screen.queryByText('Incorrect email or password.')).not.toBeInTheDocument()
  })

  it('toggles password visibility', async () => {
    mockedUseAuth.mockReturnValue({ login: vi.fn(), logout: vi.fn(), user: null, status: 'unauthenticated' })
    renderLogin()

    const passwordField = screen.getByLabelText('Password') as HTMLInputElement
    expect(passwordField.type).toBe('password')

    await userEvent.click(screen.getByRole('button', { name: 'Show password' }))
    expect(passwordField.type).toBe('text')
  })
})
