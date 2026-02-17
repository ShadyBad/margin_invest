import { describe, it, expect, vi, beforeEach } from "vitest"
import { render } from "@testing-library/react"

// Mock matchMedia for desktop viewport (>= 768px)
beforeEach(() => {
  Object.defineProperty(window, "matchMedia", {
    writable: true,
    value: vi.fn().mockImplementation((query: string) => ({
      matches: query === "(min-width: 768px)",
      media: query,
      onchange: null,
      addEventListener: vi.fn(),
      removeEventListener: vi.fn(),
      dispatchEvent: vi.fn(),
      addListener: vi.fn(),
      removeListener: vi.fn(),
    })),
  })
})

// Mock Three.js / R3F — jsdom can't do WebGL
vi.mock("@react-three/fiber", () => ({
  Canvas: ({ children }: any) => <div data-testid="r3f-canvas">{children}</div>,
  useFrame: vi.fn(),
  useThree: () => ({ size: { width: 1920, height: 1080 } }),
}))

vi.mock("three", () => {
  class MockVector2 {
    x = 0
    y = 0
    constructor(_x?: number, _y?: number) {
      this.x = _x ?? 0
      this.y = _y ?? 0
    }
    set = vi.fn()
    copy = vi.fn()
  }
  class MockColor {
    r = 0
    g = 0
    b = 0
    set = vi.fn()
  }
  return {
    ShaderMaterial: class {},
    PlaneGeometry: class {},
    Vector2: MockVector2,
    Vector3: class {
      x = 0
      y = 0
      z = 0
    },
    Color: MockColor,
  }
})

import { FluidShader } from "../fluid-shader"

describe("FluidShader", () => {
  it("renders without crashing", () => {
    const { getByTestId } = render(<FluidShader />)
    expect(getByTestId("r3f-canvas")).toBeDefined()
  })

  it("accepts DNA color props", () => {
    const { getByTestId } = render(
      <FluidShader
        baseColor="#1A3A5C"
        midColor="#0E4F4F"
        accentColor="#1A7A5A"
        tempo={0.85}
        density={0.6}
      />,
    )
    expect(getByTestId("r3f-canvas")).toBeDefined()
  })

  it("accepts scrollProgress prop", () => {
    const { getByTestId } = render(<FluidShader scrollProgress={0.5} />)
    expect(getByTestId("r3f-canvas")).toBeDefined()
  })

  it("does not render on mobile viewports", () => {
    Object.defineProperty(window, "matchMedia", {
      writable: true,
      value: vi.fn().mockImplementation((query: string) => ({
        matches: false,
        media: query,
        onchange: null,
        addEventListener: vi.fn(),
        removeEventListener: vi.fn(),
        dispatchEvent: vi.fn(),
        addListener: vi.fn(),
        removeListener: vi.fn(),
      })),
    })

    const { container } = render(<FluidShader />)
    expect(container.querySelector("[data-testid='r3f-canvas']")).toBeNull()
  })
})
