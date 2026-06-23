import { Link, Redirect, router, useLocalSearchParams } from "expo-router";
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
import { AuthTextInput } from "@/components/AuthTextInput";
import { EgoLogo } from "@/components/EgoLogo";
import { PasswordField } from "@/components/PasswordField";
import { validateReferralCode } from "@/api/client";
import { useAuth } from "@/context/AuthContext";
import { useKeyboardHeight } from "@/hooks/useKeyboardHeight";
import { useColors } from "@/theme/ThemeContext";
import { formatPhoneBrInput } from "@/utils/phoneBr";
import {
  validateEmail,
  validatePassword,
  validatePasswordConfirm,
  validatePhone,
} from "@/utils/validation";
import { savePostLoginRoute } from "@/storage/postLoginRoute";

export default function SignupScreen() {
  const colors = useColors();
  const params = useLocalSearchParams<{ ref?: string; next?: string }>();
  const { session, loading, signUp } = useAuth();
  const { bottomInset } = useKeyboardHeight();
  const [firstName, setFirstName] = useState("");
  const [lastName, setLastName] = useState("");
  const [preferredName, setPreferredName] = useState("");
  const [phone, setPhone] = useState("");
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
    const raw = params.next;
    const next = (Array.isArray(raw) ? raw[0] : raw) || "";
    if (next.trim().toLowerCase() === "agenda") {
      void savePostLoginRoute("/(main)/agenda");
    }
  }, [params.next]);

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
    const phoneErr = validatePhone(phone, true);
    if (phoneErr) {
      setError(phoneErr);
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
        phone.trim(),
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
          <EgoLogo width={240} style={styles.logoImage} />
          <Text style={[styles.logoSub, { color: colors.textMuted }]}>Criar conta</Text>

          <View
            style={[
              styles.form,
              { backgroundColor: colors.bgCard, borderColor: colors.border },
            ]}
          >
            <AuthTextInput
              label="Nome"
              value={firstName}
              onChangeText={setFirstName}
              placeholder="Seu nome"
              autoCapitalize="words"
              editable={!busy}
            />
            <AuthTextInput
              label="Sobrenome"
              value={lastName}
              onChangeText={setLastName}
              placeholder="Seu sobrenome"
              autoCapitalize="words"
              editable={!busy}
            />
            <AuthTextInput
              label="Como gostaria de ser chamado"
              value={preferredName}
              onChangeText={setPreferredName}
              placeholder="Ex.: Reida"
              autoCapitalize="words"
              editable={!busy}
            />
            <AuthTextInput
              label="Telefone (WhatsApp)"
              value={phone}
              onChangeText={(t) => setPhone(formatPhoneBrInput(t))}
              placeholder="(11) 99999-9999"
              keyboardType="phone-pad"
              editable={!busy}
            />
            <AuthTextInput
              label="E-mail"
              value={email}
              onChangeText={setEmail}
              placeholder="seu@email.com"
              autoCapitalize="none"
              keyboardType="email-address"
              autoComplete="email"
              textContentType="emailAddress"
              editable={!busy}
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
                <AuthTextInput
                  value={referralCode}
                  onChangeText={(t) => setReferralCode(t.toUpperCase())}
                  placeholder="Ex.: MARIA10"
                  autoCapitalize="characters"
                  editable={!busy}
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
        </ScrollView>
      </KeyboardAvoidingView>
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  fill: { flex: 1 },
  scroll: {
    flexGrow: 1,
    paddingHorizontal: 24,
    paddingTop: 12,
    paddingBottom: 32,
  },
  logoImage: { alignSelf: "center", marginBottom: 8 },
  logoSub: { fontSize: 16, fontWeight: "600", textAlign: "center", marginBottom: 16 },
  form: { borderRadius: 20, padding: 20, borderWidth: 1 },
  label: { fontSize: 12, marginBottom: 6, marginTop: 8 },
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
