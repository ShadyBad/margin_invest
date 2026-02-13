import { describe, it, expect, vi } from 'vitest'
import { render, screen } from '@testing-library/react'
import Page from '../page'

// Mock next/image since it's not available in test environment
vi.mock('next/image', () => ({
  default: (props: React.ImgHTMLAttributes<HTMLImageElement>) => {
    // eslint-disable-next-line @next/next/no-img-element, jsx-a11y/alt-text
    return <img {...props} />
  },
}))

describe('Home Page', () => {
  it('renders without crashing', () => {
    render(<Page />)
    // Just verify the page renders
    expect(document.body).toBeTruthy()
  })

  it('renders the heading', () => {
    render(<Page />)
    expect(
      screen.getByRole('heading', { level: 1 })
    ).toBeInTheDocument()
  })
})
