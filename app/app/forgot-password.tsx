import { Link, router } from "expo-router";
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
import { requestPasswordReset } from "@/api/client";
import { useColors } from "@/theme/ThemeContext";
import { validateEmail } from "@/utils/validation";

export default function ForgotPasswordScreen() {
  const colors = useColors();
  const [email, setEmail] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [info, setInfo] = useState<string | null>(null);

  const onSubmit = async () => {
    setError(null);
    setInfo(null);
    const emailErr = validateEmail(email);
    if (emailErr) {
      setError(emailErr);
      return;
    }
    setBusy(true);
    try {
      const msg = await requestPasswordReset(email.trim());
      setInfo(msg);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Não foi possível enviar o e-mail.");
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
          <Text style={[styles.logo, { color: colors.text }]}>Recuperar senha</Text>
          <Text style={[styles.sub, { color: colors.textMuted }]}>
            Enviaremos um link para o seu e-mail. Abra o link no telemóvel, crie a nova senha e
            entre no app.
          </Text>

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
            {error ? <Text style={[styles.error, { color: colors.danger }]}>{error}</Text> : null}
            {info ? <Text style={[styles.info, { color: colors.success }]}>{info}</Text> : null}
            <Pressable
              style={[styles.btn, { backgroundColor: colors.primary }, busy && styles.btnDisabled]}
              onPress={onSubmit}
              disabled={busy}
            >
              {busy ? (
                <ActivityIndicator color="#fff" />
              ) : (
                <Text style={styles.btnText}>Enviar link</Text>
              )}
            </Pressable>
          </View>

          <Pressable onPress={() => router.back()} style={styles.linkWrap}>
            <Text style={[styles.link, { color: colors.primaryLight }]}>Voltar ao login</Text>
          </Pressable>
          <Link href="/login" asChild>
            <Pressable style={styles.linkWrap}>
              <Text style={[styles.link, { color: colors.textMuted }]}>Entrar</Text>
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
  logo: { fontSize: 28, fontWeight: "800", textAlign: "center" },
  sub: { textAlign: "center", marginTop: 10, marginBottom: 24, fontSize: 14, lineHeight: 20 },
  form: { borderRadius: 20, padding: 20, borderWidth: 1 },
  label: { fontSize: 12, marginBottom: 6, marginTop: 8 },
  input: {
    borderRadius: 12,
    paddingHorizontal: 14,
    paddingVertical: 12,
    fontSize: 16,
    borderWidth: 1,
  },
  error: { marginTop: 12, fontSize: 14 },
  info: { marginTop: 12, fontSize: 14, lineHeight: 20 },
  btn: { marginTop: 20, borderRadius: 14, paddingVertical: 14, alignItems: "center" },
  btnDisabled: { opacity: 0.7 },
  btnText: { color: "#fff", fontSize: 16, fontWeight: "700" },
  linkWrap: { marginTop: 16, alignItems: "center" },
  link: { fontSize: 15, fontWeight: "600" },
});
