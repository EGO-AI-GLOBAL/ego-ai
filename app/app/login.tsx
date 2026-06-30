import { Link, Redirect, router, useLocalSearchParams } from "expo-router";
import { LinearGradient } from "expo-linear-gradient";
import React, { useEffect, useState } from "react";
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
import { AppGradientBackground } from "@/components/AppGradientBackground";
import { AuthTextInput } from "@/components/AuthTextInput";
import { EgoLogo } from "@/components/EgoLogo";
import { PasswordField } from "@/components/PasswordField";
import { loadLastLoginEmail } from "@/api/client";
import { useAuth } from "@/context/AuthContext";
import { useKeyboardHeight } from "@/hooks/useKeyboardHeight";
import { useColors } from "@/theme/ThemeContext";
import { validateEmail, validatePassword } from "@/utils/validation";

export default function LoginScreen() {
  const colors = useColors();
  const { session, loading, signIn } = useAuth();
  const { bottomInset } = useKeyboardHeight();
  const params = useLocalSearchParams<{ email?: string }>();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const raw = params.email;
    const fromLink = (Array.isArray(raw) ? raw[0] : raw) || "";
    if (fromLink.trim()) {
      setEmail(fromLink.trim());
      return;
    }
    void loadLastLoginEmail().then((saved) => {
      if (saved) setEmail(saved);
    });
  }, [params.email]);

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
    <AppGradientBackground variant="auth">
      <SafeAreaView style={styles.fill}>
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
          <Text style={[styles.heroTitle, { color: colors.text }]}>EGO-AI</Text>
          <Text style={[styles.heroSub, { color: colors.textMuted }]}>
            Seu companheiro com voz e rosto
          </Text>

          <View
            style={[
              styles.form,
              {
                backgroundColor: colors.glassBg,
                borderColor: colors.glassBorder,
              },
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
            <Text style={[styles.sessionHint, { color: colors.textMuted }]}>
              A sessão fica guardada neste telefone. A senha pode ser preenchida pelo
              gestor de senhas do Android.
            </Text>
            <Link
              href={{ pathname: "/forgot-password", params: { email: email.trim() } }}
              asChild
            >
              <Pressable style={styles.forgotWrap} hitSlop={8}>
                <Text style={[styles.forgot, { color: colors.primaryLight }]}>
                  Esqueci a senha?
                </Text>
              </Pressable>
            </Link>
            {error ? (
              <>
                <Text style={[styles.error, { color: colors.danger }]}>{error}</Text>
                {/incorretos/i.test(error) ? (
                  <Text style={[styles.errorHint, { color: colors.textMuted }]}>
                    Se o cadastro falhou antes (telefone ou e-mail em vermelho), a conta pode não
                    existir.
                  </Text>
                ) : null}
                {/não encontramos conta|criar conta/i.test(error) ? (
                  <Link href="/signup" asChild>
                    <Pressable style={styles.errorAction}>
                      <Text style={[styles.errorActionText, { color: colors.primary }]}>
                        Criar conta agora
                      </Text>
                    </Pressable>
                  </Link>
                ) : /incorretos/i.test(error) ? (
                  <View style={styles.errorActions}>
                    <Link href="/signup" asChild>
                      <Pressable style={styles.errorAction}>
                        <Text style={[styles.errorActionText, { color: colors.primary }]}>
                          Criar conta
                        </Text>
                      </Pressable>
                    </Link>
                    <Link
                      href={{ pathname: "/forgot-password", params: { email: email.trim() } }}
                      asChild
                    >
                      <Pressable style={styles.errorAction}>
                        <Text style={[styles.errorActionText, { color: colors.primaryLight }]}>
                          Esqueci a senha
                        </Text>
                      </Pressable>
                    </Link>
                  </View>
                ) : null}
              </>
            ) : null}
            <Pressable
              style={[styles.btnWrap, busy && styles.btnDisabled]}
              onPress={onSubmit}
              disabled={busy}
            >
              <LinearGradient
                colors={[colors.primary, colors.primaryLight]}
                start={{ x: 0, y: 0 }}
                end={{ x: 1, y: 1 }}
                style={styles.btn}
              >
                {busy ? (
                  <ActivityIndicator color="#fff" />
                ) : (
                  <Text style={styles.btnText}>Entrar</Text>
                )}
              </LinearGradient>
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
    </AppGradientBackground>
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
    marginBottom: 8,
  },
  heroTitle: {
    fontSize: 26,
    fontWeight: "900",
    textAlign: "center",
    letterSpacing: 0.5,
  },
  heroSub: {
    fontSize: 14,
    textAlign: "center",
    marginBottom: 20,
    lineHeight: 20,
  },
  form: {
    borderRadius: 22,
    padding: 20,
    borderWidth: 1,
    shadowColor: "#7C3AED",
    shadowOffset: { width: 0, height: 8 },
    shadowOpacity: 0.12,
    shadowRadius: 24,
    elevation: 6,
  },
  passwordWrap: { marginTop: 4 },
  sessionHint: { marginTop: 10, fontSize: 12, lineHeight: 17 },
  forgotWrap: { alignSelf: "flex-end", marginTop: 8 },
  forgot: { fontSize: 14, fontWeight: "600" },
  error: { marginTop: 12, fontSize: 14 },
  errorHint: { marginTop: 8, fontSize: 13, lineHeight: 18, textAlign: "center" },
  errorActions: {
    flexDirection: "row",
    flexWrap: "wrap",
    gap: 16,
    marginTop: 10,
    justifyContent: "center",
  },
  errorAction: { paddingVertical: 6, paddingHorizontal: 4 },
  errorActionText: { fontSize: 14, fontWeight: "700" },
  btnWrap: {
    marginTop: 20,
    borderRadius: 14,
    overflow: "hidden",
    shadowColor: "#7C3AED",
    shadowOffset: { width: 0, height: 4 },
    shadowOpacity: 0.35,
    shadowRadius: 10,
    elevation: 4,
  },
  btn: { paddingVertical: 14, alignItems: "center" },
  btnDisabled: { opacity: 0.7 },
  btnText: { color: "#fff", fontSize: 16, fontWeight: "700" },
  linkWrap: { marginTop: 16, alignItems: "center" },
  link: { fontSize: 15, fontWeight: "600" },
  legal: { fontSize: 13 },
});
