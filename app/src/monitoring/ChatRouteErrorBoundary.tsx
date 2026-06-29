import React, { Component, type ErrorInfo, type ReactNode } from "react";
import { Pressable, StyleSheet, Text, View } from "react-native";
import { captureException } from "./errorReporter";

type Props = { children: ReactNode };
type State = { failed: boolean };

/** Isola o ecrã de chat — evita «Algo deu errado» global após escolher avatar. */
export class ChatRouteErrorBoundary extends Component<Props, State> {
  state: State = { failed: false };

  static getDerivedStateFromError(): State {
    return { failed: true };
  }

  componentDidCatch(error: Error, info: ErrorInfo): void {
    captureException(error, {
      route: "chat",
      componentStack: info.componentStack || "",
    });
  }

  render(): ReactNode {
    if (this.state.failed) {
      return (
        <View style={styles.wrap}>
          <Text style={styles.title}>Chat indisponível</Text>
          <Text style={styles.msg}>
            Escolha o avatar outra vez ou toque abaixo para tentar de novo.
          </Text>
          <Pressable style={styles.btn} onPress={() => this.setState({ failed: false })}>
            <Text style={styles.btnText}>Tentar novamente</Text>
          </Pressable>
        </View>
      );
    }
    return this.props.children;
  }
}

const styles = StyleSheet.create({
  wrap: {
    flex: 1,
    justifyContent: "center",
    padding: 24,
    backgroundColor: "#0f0f12",
  },
  title: { color: "#fff", fontSize: 20, fontWeight: "700", marginBottom: 12 },
  msg: { color: "#aaa", fontSize: 15, lineHeight: 22, marginBottom: 24 },
  btn: {
    backgroundColor: "#6c5ce7",
    paddingVertical: 14,
    borderRadius: 12,
    alignItems: "center",
  },
  btnText: { color: "#fff", fontWeight: "600", fontSize: 16 },
});
