"use client"

import { Component, type ErrorInfo, type ReactNode } from "react"

interface Props {
  children: ReactNode
  onDismiss: () => void
}

interface State {
  hasError: boolean
}

export class PanelErrorBoundary extends Component<Props, State> {
  constructor(props: Props) {
    super(props)
    this.state = { hasError: false }
  }

  static getDerivedStateFromError(): State {
    return { hasError: true }
  }

  componentDidCatch(error: Error, errorInfo: ErrorInfo) {
    console.error("AssetPanel render error:", error, errorInfo)
  }

  render() {
    if (this.state.hasError) {
      return (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50">
          <div className="bg-bg-elevated border border-border-primary rounded-lg p-8 max-w-md text-center">
            <p className="text-sm font-medium text-text-primary mb-1">
              Unable to display details
            </p>
            <p className="text-xs text-text-secondary mb-4">
              Something went wrong rendering the analysis panel.
            </p>
            <button
              type="button"
              className="text-xs text-accent hover:text-accent/80 underline underline-offset-2"
              onClick={() => {
                this.setState({ hasError: false })
                this.props.onDismiss()
              }}
            >
              Dismiss
            </button>
          </div>
        </div>
      )
    }

    return this.props.children
  }
}
