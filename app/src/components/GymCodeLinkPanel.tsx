import React, { useState } from "react";
import {
  ActivityIndicator,
  Alert,
  Pressable,
  StyleSheet,
  Text,
  TextInput,
  View,
} from "react-native";
import { saveMyGymCode } from "@/api/client";
import { useAuth } from "@/context/AuthContext";
import { useGymPartner } from "@/context/GymPartnerContext";
import type { AppColors } from "@/theme/colors";

/**
 * Vincular parceiro → profiles.gym_code (API interna permanente).
 * Com código de parceiro → planos só Stripe Connect (IAP escondido).
 * Parceiro = academia, clínica, médico, empresa, etc. — mesmo modelo.
 */
export function GymCodeLinkPanel({ colors }: { colors: AppColors }) {
  const { session } = useAuth();
  const { partner, gymCode, refreshGymPartner } = useGymPartner();
  const [code, setCode] = useState("");
  const [busy, setBusy] = useState(false);

  if (!session?.access_token) {
    return (
      <View style={[styles.card, { backgroundColor: colors.bgCard, borderColor: colors.border }]}>
        <Text style={[styles.title, { color: colors.text }]}>Parceiro</Text>
        <Text style={[styles.hint, { color: colors.textMuted }]}>
          Entra na conta para vincular o código do parceiro.
        </Text>
      </View>
    );
  }

  async function onLink() {
    const trimmed = code.trim().toUpperCase();
    if (!trimmed) {
      Alert.alert("Código", "Digite o código do parceiro.");
      return;
    }
    setBusy(true);
    try {
      const p = await saveMyGymCode(trimmed);
      await refreshGymPartner();
      setCode("");
      const nome = (p?.name || "").trim();
      Alert.alert(
        "Vinculado",
        nome
          ? `${nome} ligado ao teu perfil.\n\nCanal parceiro: Premium EGO só via Stripe Connect (sem loja/IAP). Outros produtos do parceiro (ex. Shape30) pagam-se à parte se quiseres — checkouts separados; o parceiro recebe ≈30% em cada.`
          : "Código guardado. Canal parceiro = só Stripe no EGO (sem IAP)."
      );
    } catch (e) {
      Alert.alert("Código", e instanceof Error ? e.message : "Não foi possível vincular.");
    } finally {
      setBusy(false);
    }
  }

  if (partner && gymCode) {
    return (
      <View
        style={[
          styles.card,
          { backgroundColor: colors.bgCard, borderColor: colors.primary },
        ]}
      >
        <Text style={[styles.eyebrow, { color: colors.primary }]}>Parceiro vinculado</Text>
        <Text style={[styles.linkedName, { color: colors.text }]}>{partner.name}</Text>
        <Text style={[styles.linkedCode, { color: colors.textMuted }]}>
          Código: {gymCode} · canal parceiro = só Stripe (sem IAP) · 30%
        </Text>
        <Text style={[styles.lockHint, { color: colors.textMuted }]}>
          Vínculo permanente. Só excluir a conta zera o vínculo.
        </Text>
      </View>
    );
  }

  if (gymCode) {
    return (
      <View style={[styles.card, { backgroundColor: colors.bgCard, borderColor: colors.border }]}>
        <Text style={[styles.eyebrow, { color: colors.primary }]}>Parceiro vinculado</Text>
        <Text style={[styles.linkedName, { color: colors.text }]}>Código: {gymCode}</Text>
        <Text style={[styles.lockHint, { color: colors.textMuted }]}>
          Premium desta conta: só Stripe Connect — sem App Store / Play.
        </Text>
      </View>
    );
  }

  return (
    <View style={[styles.card, { backgroundColor: colors.bgCard, borderColor: colors.border }]}>
      <Text style={[styles.eyebrow, { color: colors.primary }]}>EGO + Parceiros</Text>
      <Text style={[styles.title, { color: colors.text }]}>Vincular parceiro</Text>
      <Text style={[styles.hint, { color: colors.textMuted }]}>
        Código do parceiro (academia, clínica, médico, empresa…). Neste app o
        canal parceiro é SÓ Stripe Connect (sem IAP/lojas). Outros produtos do
        parceiro, se existirem, são checkouts separados; ≈30% ao parceiro em cada.
        Sem código → IAP normal nas lojas.
      </Text>
      <Text style={[styles.label, { color: colors.text }]}>Código do parceiro</Text>
      <TextInput
        style={[
          styles.input,
          {
            backgroundColor: colors.bg,
            borderColor: colors.border,
            color: colors.text,
          },
        ]}
        value={code}
        onChangeText={setCode}
        autoCapitalize="characters"
        autoCorrect={false}
        placeholder="Ex: CORPOACAO"
        placeholderTextColor={colors.textMuted}
        editable={!busy}
        returnKeyType="done"
        onSubmitEditing={() => void onLink()}
      />
      <Pressable
        style={[styles.btn, { backgroundColor: colors.primary }, busy && styles.disabled]}
        disabled={busy}
        onPress={() => void onLink()}
      >
        {busy ? (
          <ActivityIndicator color="#fff" />
        ) : (
          <Text style={styles.btnText}>Vincular parceiro</Text>
        )}
      </Pressable>
    </View>
  );
}

const styles = StyleSheet.create({
  card: {
    borderRadius: 16,
    borderWidth: 1.5,
    padding: 16,
    marginBottom: 16,
  },
  eyebrow: {
    fontSize: 11,
    fontWeight: "800",
    textTransform: "uppercase",
    letterSpacing: 0.6,
    marginBottom: 6,
  },
  title: { fontSize: 18, fontWeight: "900", marginBottom: 8 },
  hint: { fontSize: 14, lineHeight: 20, marginBottom: 14 },
  lockHint: { fontSize: 13, lineHeight: 19, marginTop: 4 },
  label: { fontWeight: "700", fontSize: 13, marginBottom: 6 },
  input: {
    borderWidth: 1,
    borderRadius: 12,
    paddingHorizontal: 14,
    paddingVertical: 12,
    fontSize: 16,
    fontWeight: "700",
    letterSpacing: 1,
    marginBottom: 12,
  },
  btn: {
    borderRadius: 12,
    paddingVertical: 14,
    alignItems: "center",
  },
  btnText: { color: "#fff", fontWeight: "900", fontSize: 15 },
  disabled: { opacity: 0.6 },
  linkedName: { fontWeight: "900", fontSize: 16 },
  linkedCode: { fontSize: 13, marginTop: 2 },
});
