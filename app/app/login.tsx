import { Link, Redirect, router } from "expo-router";
import React, { useState } from "react";
import {
  ActivityIndicator,
  KeyboardAvoidingView,
  Platform,
  Pressable,
  StyleSheet,
  Text,
  TextInput,
  View,
} from "react-native";
import { SafeAreaView } from "react-native-safe-area-context";
import { EgoLogo } from "@/components/EgoLogo";
import { PasswordField } from "@/components/PasswordField";
import { useAuth } from "@/context/AuthContext";
import { useColors } from "@/theme/ThemeContext";
import { validateEmail, validatePassword } from "@/utils/validation";

export default function LoginScreen() {
  const colors = useColors();
  const { session, loading, signIn } = useAuth();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  if (!loading && session) {
    return <Redirect href="/" />;
  }

  const onSubmit = async () => {
    setError(null);
    const emailErr = validateEmail(email);
    const passErr = validatePassword(password);
    if (emailErr || passErr) {
      setError(emailErr || passErr);
      return;
    }
    setBusy(true);
    try {
      await signIn(email.trim(), password);
      router.replace("/");
    } catch (e) {
      setError(e instanceof Error ? e.message : "Falha no login.");
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
          <EgoLogo width={300} style={styles.logoImage} />

          <View
            style={[
              styles.form,
              { backgroundColor: colors.bgCard, borderColor: colors.border },
            ]}
          >
            <Text style={[styles.label, { color: colors.textMuted }]}>E-mail</Text>
            <TextInput
              style={[
                styles.input,
                {
                  backgroundColor: colors.bgElevated,
                  borderColor: colors.border,
                  color: colors.text,
                },
              ]}
              autoCapitalize="none"
              keyboardType="email-address"
              value={email}
              onChangeText={setEmail}
              placeholder="nome@exemplo.com"
              placeholderTextColor={colors.textMuted}
            />
            <PasswordField
              label="Senha"
              value={password}
              onChangeText={setPassword}
              kind="login"
              returnKeyType="done"
              onSubmitEditing={() => void onSubmit()}
            />
            <Link href="/forgot-password" asChild>
              <Pressable style={styles.forgotWrap} hitSlop={8}>
                <Text style={[styles.forgot, { color: colors.primaryLight }]}>
                  Esqueci a senha?
                </Text>
              </Pressable>
            </Link>
            {error ? <Text style={[styles.error, { color: colors.danger }]}>{error}</Text> : null}
            <Pressable
              style={[styles.btn, { backgroundColor: colors.primary }, busy && styles.btnDisabled]}
              onPress={onSubmit}
              disabled={busy}
            >
              {busy ? (
                <ActivityIndicator color="#fff" />
              ) : (
                <Text style={styles.btnText}>Entrar</Text>
              )}
            </Pressable>
          </View>

          <Link href="/signup" asChild>
            <Pressable style={styles.linkWrap}>
              <Text style={[styles.link, { color: colors.primaryLight }]}>
                Não tenho conta — Criar conta
              </Text>
            </Pressable>
          </Link>

          <Link href="/legal/privacy" asChild>
            <Pressable style={styles.linkWrap}>
              <Text style={[styles.legal, { color: colors.textMuted }]}>
                Política de Privacidade
              </Text>
            </Pressable>
          </Link>
        </View>
      </KeyboardAvoidingView>
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  fill: { flex: 1 },
  inner: { flex: 1, justifyContent: "center", paddingHorizontal: 24 },
  logoImage: {
    alignSelf: "center",
    marginBottom: 28,
  },
  form: { borderRadius: 20, padding: 20, borderWidth: 1 },
  label: { fontSize: 12, marginBottom: 6, marginTop: 8 },
  input: {
    borderRadius: 12,
    paddingHorizontal: 14,
    paddingVertical: 12,
    fontSize: 16,
    borderWidth: 1,
  },
  forgotWrap: { alignSelf: "flex-end", marginTop: 8 },
  forgot: { fontSize: 14, fontWeight: "600" },
  error: { marginTop: 12, fontSize: 14 },
  btn: { marginTop: 20, borderRadius: 14, paddingVertical: 14, alignItems: "center" },
  btnDisabled: { opacity: 0.7 },
  btnText: { color: "#fff", fontSize: 16, fontWeight: "700" },
  linkWrap: { marginTop: 16, alignItems: "center" },
  link: { fontSize: 15, fontWeight: "600" },
  legal: { fontSize: 13 },
});
