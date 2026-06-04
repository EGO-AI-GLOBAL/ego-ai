import { Link, Redirect, router, useLocalSearchParams } from "expo-router";
import React, { useEffect, useState } from "react";
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
import { validateReferralCode } from "@/api/client";
import { useAuth } from "@/context/AuthContext";
import { useColors } from "@/theme/ThemeContext";
import {
  validateEmail,
  validatePassword,
  validatePasswordConfirm,
} from "@/utils/validation";

export default function SignupScreen() {
  const colors = useColors();
  const params = useLocalSearchParams<{ ref?: string }>();
  const { session, loading, signUp } = useAuth();
  const [firstName, setFirstName] = useState("");
  const [lastName, setLastName] = useState("");
  const [preferredName, setPreferredName] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [passwordConfirm, setPasswordConfirm] = useState("");
  const [acceptedTerms, setAcceptedTerms] = useState(false);
  const [referralCode, setReferralCode] = useState("");
  const [referralOpen, setReferralOpen] = useState(false);
  const [referralHint, setReferralHint] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [info, setInfo] = useState<string | null>(null);

  useEffect(() => {
    const raw = params.ref;
    const fromLink = (Array.isArray(raw) ? raw[0] : raw) || "";
    if (fromLink.trim()) {
      setReferralCode(fromLink.trim().toUpperCase());
      setReferralOpen(true);
    }
  }, [params.ref]);

  useEffect(() => {
    const code = referralCode.trim();
    if (code.length < 3) {
      setReferralHint(null);
      return;
    }
    const t = setTimeout(() => {
      void validateReferralCode(code)
        .then((r) => {
          if (r.valid && r.display_name) {
            setReferralHint(`Código válido — parceiro: ${r.display_name}. 10% na 1ª compra.`);
          } else if (r.valid) {
            setReferralHint("Código válido. Você ganha 10% de desconto na primeira compra.");
          } else {
            setReferralHint("Código não encontrado.");
          }
        })
        .catch(() => setReferralHint(null));
    }, 400);
    return () => clearTimeout(t);
  }, [referralCode]);

  if (!loading && session) {
    return <Redirect href="/" />;
  }

  const onSubmit = async () => {
    setError(null);
    setInfo(null);
    const emailErr = validateEmail(email);
    const passErr = validatePasswordConfirm(password, passwordConfirm);
    if (emailErr || passErr) {
      setError(emailErr || passErr);
      return;
    }
    if (!firstName.trim() || !lastName.trim()) {
      setError("Informe seu nome e sobrenome.");
      return;
    }
    if (!preferredName.trim()) {
      setError("Informe como gostaria de ser chamado.");
      return;
    }
    if (!acceptedTerms) {
      setError("Aceite os Termos de Uso e a Política de Privacidade.");
      return;
    }
    setBusy(true);
    try {
      const display = preferredName.trim();
      const { needsEmailConfirm } = await signUp(
        email.trim(),
        password,
        display,
        referralCode.trim() || undefined
      );
      if (needsEmailConfirm) {
        setInfo(
          "Conta criada. Se o Supabase pedir confirmação por e-mail, confirme e depois use Entrar."
        );
        return;
      }
      router.replace("/(main)/choose-avatar");
    } catch (e) {
      setError(e instanceof Error ? e.message : "Não foi possível criar a conta.");
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
          <EgoLogo width={280} style={styles.logoImage} />
          <Text style={[styles.logoSub, { color: colors.textMuted }]}>Criar conta</Text>

          <View
            style={[
              styles.form,
              { backgroundColor: colors.bgCard, borderColor: colors.border },
            ]}
          >
            <Text style={[styles.label, { color: colors.textMuted }]}>Nome</Text>
            <TextInput
              style={[
                styles.input,
                {
                  backgroundColor: colors.bgElevated,
                  borderColor: colors.border,
                  color: colors.text,
                },
              ]}
              value={firstName}
              onChangeText={setFirstName}
              placeholder="Seu nome"
              placeholderTextColor={colors.textMuted}
            />
            <Text style={[styles.label, { color: colors.textMuted }]}>Sobrenome</Text>
            <TextInput
              style={[
                styles.input,
                {
                  backgroundColor: colors.bgElevated,
                  borderColor: colors.border,
                  color: colors.text,
                },
              ]}
              value={lastName}
              onChangeText={setLastName}
              placeholder="Seu sobrenome"
              placeholderTextColor={colors.textMuted}
            />
            <Text style={[styles.label, { color: colors.textMuted }]}>
              Como gostaria de ser chamado
            </Text>
            <TextInput
              style={[
                styles.input,
                {
                  backgroundColor: colors.bgElevated,
                  borderColor: colors.border,
                  color: colors.text,
                },
              ]}
              value={preferredName}
              onChangeText={setPreferredName}
              placeholder="Ex.: Reida"
              placeholderTextColor={colors.textMuted}
            />
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
              placeholder="seu@email.com"
              placeholderTextColor={colors.textMuted}
            />
            <PasswordField
              label="Senha"
              value={password}
              onChangeText={setPassword}
              placeholder="mín. 6 caracteres"
              kind="new"
            />
            <PasswordField
              label="Confirmar senha"
              value={passwordConfirm}
              onChangeText={setPasswordConfirm}
              placeholder="Repita a senha"
              kind="new"
            />
            {referralOpen ? (
              <View style={styles.referralBlock}>
                <View style={styles.referralHeader}>
                  <Text style={[styles.label, { color: colors.textMuted, marginTop: 0 }]}>
                    Código de indicação
                  </Text>
                  <Pressable
                    onPress={() => {
                      setReferralOpen(false);
                      setReferralCode("");
                      setReferralHint(null);
                    }}
                    hitSlop={8}
                  >
                    <Text style={[styles.referralClose, { color: colors.textMuted }]}>
                      Fechar
                    </Text>
                  </Pressable>
                </View>
                <TextInput
                  style={[
                    styles.input,
                    {
                      backgroundColor: colors.bgElevated,
                      borderColor: colors.border,
                      color: colors.text,
                    },
                  ]}
                  autoCapitalize="characters"
                  value={referralCode}
                  onChangeText={(t) => setReferralCode(t.toUpperCase())}
                  placeholder="Ex.: MARIA10"
                  placeholderTextColor={colors.textMuted}
                />
                {referralHint ? (
                  <Text
                    style={[
                      styles.referralHint,
                      {
                        color: referralHint.includes("não encontrado")
                          ? colors.danger
                          : colors.success,
                      },
                    ]}
                  >
                    {referralHint}
                  </Text>
                ) : (
                  <Text style={[styles.referralHint, { color: colors.textMuted }]}>
                    10% de desconto na primeira compra, se o código for válido.
                  </Text>
                )}
              </View>
            ) : (
              <Pressable
                style={styles.referralToggle}
                onPress={() => setReferralOpen(true)}
                hitSlop={8}
              >
                <Text style={[styles.referralToggleText, { color: colors.primaryLight }]}>
                  Tem código de indicação?
                </Text>
              </Pressable>
            )}

            <Pressable
              style={styles.termsRow}
              onPress={() => setAcceptedTerms((v) => !v)}
              accessibilityRole="checkbox"
              accessibilityState={{ checked: acceptedTerms }}
            >
              <View
                style={[
                  styles.checkbox,
                  {
                    borderColor: colors.border,
                    backgroundColor: acceptedTerms ? colors.primary : colors.bgElevated,
                  },
                ]}
              >
                {acceptedTerms ? <Text style={styles.checkMark}>✓</Text> : null}
              </View>
              <Text style={[styles.termsText, { color: colors.textMuted }]}>
                Li e aceito os{" "}
                <Text
                  style={{ color: colors.primaryLight }}
                  onPress={() => router.push("/legal/terms")}
                >
                  Termos
                </Text>{" "}
                e a{" "}
                <Text
                  style={{ color: colors.primaryLight }}
                  onPress={() => router.push("/legal/privacy")}
                >
                  Política de Privacidade
                </Text>
              </Text>
            </Pressable>

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
                <Text style={styles.btnText}>Criar conta</Text>
              )}
            </Pressable>
          </View>

          <Link href="/login" asChild>
            <Pressable style={styles.linkWrap}>
              <Text style={[styles.link, { color: colors.primaryLight }]}>
                Já tenho conta — Entrar
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
  logoImage: { alignSelf: "center", marginBottom: 8 },
  logoSub: { fontSize: 16, fontWeight: "600", textAlign: "center", marginBottom: 20 },
  form: { borderRadius: 20, padding: 20, borderWidth: 1 },
  label: { fontSize: 12, marginBottom: 6, marginTop: 8 },
  input: {
    borderRadius: 12,
    paddingHorizontal: 14,
    paddingVertical: 12,
    fontSize: 16,
    borderWidth: 1,
  },
  termsRow: { flexDirection: "row", alignItems: "flex-start", marginTop: 14, gap: 10 },
  checkbox: {
    width: 22,
    height: 22,
    borderRadius: 6,
    borderWidth: 1,
    alignItems: "center",
    justifyContent: "center",
    marginTop: 2,
  },
  checkMark: { color: "#fff", fontWeight: "800", fontSize: 14 },
  termsText: { flex: 1, fontSize: 13, lineHeight: 18 },
  error: { marginTop: 12, fontSize: 14 },
  referralToggle: { marginTop: 12, alignSelf: "flex-start" },
  referralToggleText: { fontSize: 14, fontWeight: "600" },
  referralBlock: { marginTop: 12 },
  referralHeader: {
    flexDirection: "row",
    alignItems: "center",
    justifyContent: "space-between",
    marginBottom: 6,
  },
  referralClose: { fontSize: 13, fontWeight: "600" },
  referralHint: { marginTop: 6, fontSize: 12, lineHeight: 16 },
  info: { marginTop: 12, fontSize: 14, lineHeight: 20 },
  btn: { marginTop: 20, borderRadius: 14, paddingVertical: 14, alignItems: "center" },
  btnDisabled: { opacity: 0.7 },
  btnText: { color: "#fff", fontSize: 16, fontWeight: "700" },
  linkWrap: { marginTop: 20, alignItems: "center" },
  link: { fontSize: 15, fontWeight: "600" },
});
