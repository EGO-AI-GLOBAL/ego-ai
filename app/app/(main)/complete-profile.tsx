import { router } from "expo-router";
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
import { updateProfilePhone } from "@/api/client";
import { useDashboard } from "@/hooks/useDashboard";
import { useKeyboardHeight } from "@/hooks/useKeyboardHeight";
import { useColors } from "@/theme/ThemeContext";
import { formatPhoneBrInput } from "@/utils/phoneBr";
import { validatePhone } from "@/utils/validation";

export default function CompleteProfileScreen() {
  const colors = useColors();
  const { refresh } = useDashboard();
  const { bottomInset } = useKeyboardHeight();
  const [phone, setPhone] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const onSubmit = async () => {
    setError(null);
    const phoneErr = validatePhone(phone, true);
    if (phoneErr) {
      setError(phoneErr);
      return;
    }
    setBusy(true);
    try {
      await updateProfilePhone(phone.trim());
      await refresh();
      router.replace("/(main)/chat");
    } catch (e) {
      setError(e instanceof Error ? e.message : "Não foi possível guardar o telefone.");
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
          <EgoLogo width={220} style={styles.logo} />
          <Text style={[styles.title, { color: colors.text }]}>Complete seu cadastro</Text>
          <Text style={[styles.sub, { color: colors.textMuted }]}>
            Falta o seu telefone (WhatsApp). É necessário para convites do Entre Nós e para
            ligar a sua conta quando alguém o convida.
          </Text>

          <View
            style={[
              styles.form,
              { backgroundColor: colors.bgCard, borderColor: colors.border },
            ]}
          >
            <AuthTextInput
              label="Telefone (WhatsApp)"
              value={phone}
              onChangeText={(t) => setPhone(formatPhoneBrInput(t))}
              placeholder="(11) 99999-9999"
              keyboardType="phone-pad"
              editable={!busy}
            />
            {error ? <Text style={[styles.error, { color: colors.danger }]}>{error}</Text> : null}
            <Pressable
              style={[styles.btn, { backgroundColor: colors.primary }, busy && styles.btnDisabled]}
              onPress={() => void onSubmit()}
              disabled={busy}
            >
              {busy ? (
                <ActivityIndicator color="#fff" />
              ) : (
                <Text style={styles.btnText}>Continuar</Text>
              )}
            </Pressable>
          </View>

          <Text style={[styles.note, { color: colors.textMuted }]}>
            Use o mesmo número que a pessoa usou ao convidar você, se for o caso.
          </Text>
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
    paddingTop: 24,
    paddingBottom: 32,
    justifyContent: "center",
  },
  logo: { alignSelf: "center", marginBottom: 16 },
  title: { fontSize: 22, fontWeight: "800", textAlign: "center", marginBottom: 8 },
  sub: { fontSize: 14, lineHeight: 20, textAlign: "center", marginBottom: 20 },
  form: { borderRadius: 20, padding: 20, borderWidth: 1 },
  error: { marginTop: 12, fontSize: 14 },
  btn: { marginTop: 20, borderRadius: 14, paddingVertical: 14, alignItems: "center" },
  btnDisabled: { opacity: 0.7 },
  btnText: { color: "#fff", fontSize: 16, fontWeight: "700" },
  note: { marginTop: 16, fontSize: 12, lineHeight: 17, textAlign: "center" },
});
