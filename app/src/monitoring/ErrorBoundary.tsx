import Constants from "expo-constants";
import React, { Component, type ErrorInfo, type ReactNode } from "react";
import { Pressable, StyleSheet, Text, View } from "react-native";
import { captureException } from "./errorReporter";

type Props = { children: ReactNode };
type State = { error: Error | null };

export class ErrorBoundary extends Component<Props, State> {
  state: State = { error: null };

  static getDerivedStateFromError(error: Error): State {
    return { error };
  }

  componentDidCatch(error: Error, info: ErrorInfo): void {
    captureException(error, { componentStack: info.componentStack || "" });
  }

  render(): ReactNode {
    if (this.state.error) {
      const version = Constants.expoConfig?.version || "?";
      const build =
        Constants.expoConfig?.ios?.buildNumber ||
        String(Constants.expoConfig?.android?.versionCode || "");
      return (
        <View style={styles.wrap}>
          <Text style={styles.title}>Algo deu errado</Text>
          <Text style={styles.msg}>
            O erro foi enviado automaticamente. Feche e abra o app, ou tente de novo.
          </Text>
          <Text style={styles.version}>
            Versão {version}
            {build ? ` (${build})` : ""}
          </Text>
          <Pressable
            style={styles.btn}
            onPress={() => this.setState({ error: null })}
          >
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
  msg: { color: "#aaa", fontSize: 15, lineHeight: 22, marginBottom: 12 },
  version: { color: "#666", fontSize: 12, marginBottom: 24 },
  btn: {
    backgroundColor: "#6c5ce7",
    paddingVertical: 14,
    borderRadius: 12,
    alignItems: "center",
  },
  btnText: { color: "#fff", fontWeight: "600", fontSize: 16 },
});
