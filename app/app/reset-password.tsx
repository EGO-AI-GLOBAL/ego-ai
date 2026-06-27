import { Link, Redirect, router } from "expo-router";
import React, { useEffect, useState } from "react";
import {
  ActivityIndicator,
  KeyboardAvoidingView,
  Platform,
  Pressable,
  StyleSheet,
  Text,
  View,
} from "react-native";
import { SafeAreaView } from "react-native-safe-area-context";
import { completePasswordReset } from "@/api/client";
import { PasswordField } from "@/components/PasswordField";
import { useAuth } from "@/context/AuthContext";
import {
  clearPasswordRecoveryTokens,
  loadPasswordRecoveryTokens,
} from "@/storage/passwordRecovery";
import { useColors } from "@/theme/ThemeContext";
import { validatePasswordConfirm } from "@/utils/validation";

export default function ResetPasswordScreen() {
  const colors = useColors();
  const { session, loading, applySession } = useAuth();
  const [ready, setReady] = useState(false);
  const [hasTokens, setHasTokens] = useState(false);
  const [password, setPassword] = useState("");
  const [passwordConfirm, setPasswordConfirm] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [done, setDone] = useState(false);

  useEffect(() => {
    void (async () => {
      const tokens = await loadPasswordRecoveryTokens();
      setHasTokens(Boolean(tokens?.access_token && tokens?.refresh_token));
      setReady(true);
    })();
  }, []);

  if (!loading && session && !done) {
    return <Redirect href="/" />;
  }

  if (!ready) {
    return (
      <SafeAreaView style={[styles.fill, styles.center, { backgroundColor: colors.bg }]}>
        <ActivityIndicator color={colors.primary} />
      </SafeAreaView>
    );
  }

  if (!hasTokens) {
    return (
      <SafeAreaView style={[styles.fill, { backgroundColor: colors.bg }]}>
        <View style={styles.inner}>
          <Text style={[styles.logo, { color: colors.text }]}>Link inválido</Text>
          <Text style={[styles.sub, { color: colors.textMuted }]}>
            Peça um novo e-mail em Esqueci a senha. O link expira após algum tempo.
          </Text>
          <Link href="/forgot-password" asChild>
            <Pressable style={[styles.btn, { backgroundColor: colors.primary }]}>
              <Text style={styles.btnText}>Pedir novo link</Text>
            </Pressable>
          </Link>
          <Link href="/login" asChild>
            <Pressable style={styles.linkWrap}>
              <Text style={[styles.link, { color: colors.textMuted }]}>Voltar ao login</Text>
            </Pressable>
          </Link>
        </View>
      </SafeAreaView>
    );
  }

  const onSubmit = async () => {
    setError(null);
    const passErr = validatePasswordConfirm(password, passwordConfirm);
    if (passErr) {
      setError(passErr);
      return;
    }
    setBusy(true);
    try {
      const tokens = await loadPasswordRecoveryTokens();
      if (!tokens) {
        setError("Link expirado. Peça um novo e-mail.");
        setHasTokens(false);
        return;
      }
      const newSession = await completePasswordReset(
        tokens.access_token,
        tokens.refresh_token,
        password
      );
      await clearPasswordRecoveryTokens();
      await applySession(newSession);
      setDone(true);
      router.replace("/");
    } catch (e) {
      setError(e instanceof Error ? e.message : "Não foi possível alterar a senha.");
    } finally {
      setBusy(false);
    }
  };

  return (
    <SafeAreaView style={[styles.fill, { backgroundColor: colors.bg }]}>
      <KeyboardAvoidingView
        style={styles.fill}
        behavior={Platform.OS === "ios" ? "padding" : undefined}
      >
        <View style={styles.inner}>
          <Text style={[styles.logo, { color: colors.text }]}>Nova senha</Text>
          <Text style={[styles.sub, { color: colors.textMuted }]}>
            Escolha uma senha com pelo menos 6 caracteres.
          </Text>

          <View
            style={[
              styles.form,
              { backgroundColor: colors.bgCard, borderColor: colors.border },
            ]}
          >
            <PasswordField
              label="Nova senha"
              value={password}
              onChangeText={setPassword}
              kind="new"
            />
            <PasswordField
              label="Confirmar senha"
              value={passwordConfirm}
              onChangeText={setPasswordConfirm}
              kind="new"
            />
            {error ? <Text style={[styles.error, { color: colors.danger }]}>{error}</Text> : null}
            <Pressable
              style={[styles.btn, { backgroundColor: colors.primary }, busy && styles.btnDisabled]}
              onPress={onSubmit}
              disabled={busy}
            >
              {busy ? (
                <ActivityIndicator color="#fff" />
              ) : (
                <Text style={styles.btnText}>Guardar senha</Text>
              )}
            </Pressable>
          </View>

          <Pressable onPress={() => router.back()} style={styles.linkWrap}>
            <Text style={[styles.link, { color: colors.primaryLight }]}>Cancelar</Text>
          </Pressable>
        </View>
      </KeyboardAvoidingView>
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  fill: { flex: 1 },
  center: { justifyContent: "center", alignItems: "center" },
  inner: { flex: 1, justifyContent: "center", paddingHorizontal: 24 },
  logo: { fontSize: 28, fontWeight: "800", textAlign: "center" },
  sub: { textAlign: "center", marginTop: 10, marginBottom: 24, fontSize: 14, lineHeight: 20 },
  form: { borderRadius: 20, padding: 20, borderWidth: 1 },
  error: { marginTop: 12, fontSize: 14 },
  btn: { marginTop: 20, borderRadius: 14, paddingVertical: 14, alignItems: "center" },
  btnDisabled: { opacity: 0.7 },
  btnText: { color: "#fff", fontSize: 16, fontWeight: "700" },
  linkWrap: { marginTop: 16, alignItems: "center" },
  link: { fontSize: 15, fontWeight: "600" },
});
