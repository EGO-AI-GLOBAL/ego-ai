import { Link, Redirect, router } from "expo-router";
import React, { useState } from "react";
import {
  ActivityIndicator,
  KeyboardAvoidingView,
  Platform,
  Pressable,
  ScrollView,
  StyleSheet,
  Text,
  View,
} from "react-native";
import { SafeAreaView } from "react-native-safe-area-context";
import { AuthTextInput } from "@/components/AuthTextInput";
import { EgoLogo } from "@/components/EgoLogo";
import { PasswordField } from "@/components/PasswordField";
import { useAuth } from "@/context/AuthContext";
import { useKeyboardHeight } from "@/hooks/useKeyboardHeight";
import { useColors } from "@/theme/ThemeContext";
import { validateEmail, validatePassword } from "@/utils/validation";

export default function LoginScreen() {
  const colors = useColors();
  const { session, loading, signIn } = useAuth();
  const { bottomInset } = useKeyboardHeight();
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
        behavior={Platform.OS === "ios" ? "padding" : "height"}
        keyboardVerticalOffset={Platform.OS === "ios" ? 8 : 0}
      >
        <ScrollView
          contentContainerStyle={[
            styles.scroll,
            bottomInset > 0 ? { paddingBottom: bottomInset + 16 } : null,
          ]}
          keyboardShouldPersistTaps="handled"
          showsVerticalScrollIndicator={false}
        >
          <EgoLogo width={280} style={styles.logoImage} />

          <View
            style={[
              styles.form,
              { backgroundColor: colors.bgCard, borderColor: colors.border },
            ]}
          >
            <AuthTextInput
              label="E-mail"
              value={email}
              onChangeText={setEmail}
              placeholder="nome@exemplo.com"
              keyboardType="email-address"
              autoComplete="email"
              textContentType="emailAddress"
              returnKeyType="next"
              editable={!busy}
            />
            <PasswordField
              label="Senha"
              value={password}
              onChangeText={setPassword}
              kind="login"
              returnKeyType="done"
              onSubmitEditing={() => void onSubmit()}
              editable={!busy}
              containerStyle={styles.passwordWrap}
            />
            <Link href="/forgot-password" asChild>
              <Pressable style={styles.forgotWrap} hitSlop={8}>
                <Text style={[styles.forgot, { color: colors.primaryLight }]}>
                  Esqueci a senha?
                </Text>
              </Pressable>
            </Link>
            {error ? (
              <Text style={[styles.error, { color: colors.danger }]}>{error}</Text>
            ) : null}
            <Pressable
              style={[
                styles.btn,
                { backgroundColor: colors.primary },
                busy && styles.btnDisabled,
              ]}
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
        </ScrollView>
      </KeyboardAvoidingView>
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  fill: { flex: 1 },
  scroll: {
    flexGrow: 1,
    justifyContent: "center",
    paddingHorizontal: 24,
    paddingVertical: 24,
  },
  logoImage: {
    alignSelf: "center",
    marginBottom: 24,
  },
  form: { borderRadius: 20, padding: 20, borderWidth: 1 },
  passwordWrap: { marginTop: 4 },
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
