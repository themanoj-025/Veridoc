"use client";

import { Component, type ReactNode } from "react";

interface ErrorBoundaryProps {
  children: ReactNode;
  fallback?: ReactNode;
  name?: string;
}

interface ErrorBoundaryState {
  hasError: boolean;
  error: Error | null;
}

/**
 * Catches JavaScript errors anywhere in its child component tree and
 * renders a fallback UI instead of crashing the whole page.
 *
 * Usage:
 *   <ErrorBoundary name="ChatPanel">
 *     <ChatPanel ... />
 *   </ErrorBoundary>
 */
export class ErrorBoundary extends Component<ErrorBoundaryProps, ErrorBoundaryState> {
  constructor(props: ErrorBoundaryProps) {
    super(props);
    this.state = { hasError: false, error: null };
  }

  static getDerivedStateFromError(error: Error): ErrorBoundaryState {
    return { hasError: true, error };
  }

  componentDidCatch(error: Error, errorInfo: React.ErrorInfo) {
    console.error(`[ErrorBoundary:${this.props.name || "unknown"}]`, error, errorInfo);
  }

  handleRetry = () => {
    this.setState({ hasError: false, error: null });
  };

  render() {
    if (this.state.hasError) {
      if (this.props.fallback) {
        return this.props.fallback;
      }

      return (
        <div className="h-full flex items-center justify-center p-6">
          <div className="text-center max-w-sm">
            <div className="w-12 h-12 rounded-2xl bg-red-100 mx-auto mb-3 flex items-center justify-center">
              <svg className="w-6 h-6 text-red-500" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2}
                  d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-2.5L13.732 4c-.77-.833-1.964-.833-2.732 0L4.082 16.5c-.77.833.192 2.5 1.732 2.5z" />
              </svg>
            </div>
            <h3 className="text-sm font-semibold text-foreground mb-1">
              {this.props.name || "Section"} crashed
            </h3>
            <p className="text-xs text-muted-foreground mb-3">
              {this.state.error?.message || "An unexpected error occurred"}
            </p>
            <button
              onClick={this.handleRetry}
              className="px-3 py-1.5 rounded-lg bg-veridoc-500 text-white text-xs font-medium
                         hover:bg-veridoc-600 transition-colors focus:outline-none focus:ring-2 focus:ring-veridoc-500/20"
            >
              Retry
            </button>
          </div>
        </div>
      );
    }

    return this.props.children;
  }
}
