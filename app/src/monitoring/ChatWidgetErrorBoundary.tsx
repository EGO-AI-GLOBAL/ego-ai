import React, { Component, type ErrorInfo, type ReactNode } from "react";
import { captureException } from "./errorReporter";

type Props = {
  name: string;
  children: ReactNode;
};

type State = { failed: boolean };

/** Isola cartões opcionais do chat — falha num widget não derruba o login. */
export class ChatWidgetErrorBoundary extends Component<Props, State> {
  state: State = { failed: false };

  static getDerivedStateFromError(): State {
    return { failed: true };
  }

  componentDidCatch(error: Error, info: ErrorInfo): void {
    captureException(error, {
      widget: this.props.name,
      componentStack: info.componentStack || "",
    });
  }

  render(): ReactNode {
    if (this.state.failed) return null;
    return this.props.children;
  }
}
