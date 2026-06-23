import React, { useEffect, useState } from "react";
import {
  ActivityIndicator,
  Alert,
  Pressable,
  StyleSheet,
  Text,
  TextInput,
  View,
} from "react-native";
import { updateProfilePhone } from "@/api/client";
import type { AppColors } from "@/theme/colors";
import { formatPhoneBrInput, formatPhoneBrDisplay } from "@/utils/phoneBr";
import { validatePhone } from "@/utils/validation";

type Props = {
  colors: AppColors;
  phone?: string | null;
  onSaved: () => Promise<void>;
};

export function ProfilePhoneCard({ colors, phone, onSaved }: Props) {
  const stored = (phone || "").trim();
  const [value, setValue] = useState(stored ? formatPhoneBrDisplay(stored) : "");
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    setValue(stored ? formatPhoneBrDisplay(stored) : "");
  }, [stored]);

  const onSave = async () => {
    const err = validatePhone(value, true);
    if (err) {
      Alert.alert("Telefone", err);
      return;
    }
    setBusy(true);
    try {
      await updateProfilePhone(value.trim());
      await onSaved();
      Alert.alert(
        "Telefone guardado",
        "Convites do Entre Nós por telefone passam a funcionar com este número."
      );
    } catch (e) {
      Alert.alert("Telefone", e instanceof Error ? e.message : "Não foi possível guardar.");
    } finally {
      setBusy(false);
    }
  };

  return (
    <View style={[styles.card, { borderColor: colors.border, backgroundColor: colors.bgCard }]}>
      <Text style={[styles.title, { color: colors.text }]}>Telefone (WhatsApp)</Text>
      <Text style={[styles.hint, { color: colors.textMuted }]}>
        {stored
          ? "Usado para convites do Entre Nós baterem com o seu cadastro."
          : "Falta no seu cadastro — adicione para receber convites por telefone."}
      </Text>
      <TextInput
        value={value}
        onChangeText={(t) => setValue(formatPhoneBrInput(t))}
        placeholder="(11) 99999-9999"
        placeholderTextColor={colors.textMuted}
        keyboardType="phone-pad"
        editable={!busy}
        style={[
          styles.input,
          { color: colors.text, borderColor: colors.border, backgroundColor: colors.bg },
        ]}
      />
      <Pressable
        onPress={() => void onSave()}
        disabled={busy}
        style={[styles.btn, { backgroundColor: colors.primary, opacity: busy ? 0.7 : 1 }]}
      >
        {busy ? (
          <ActivityIndicator color="#fff" />
        ) : (
          <Text style={styles.btnText}>{stored ? "Atualizar telefone" : "Guardar telefone"}</Text>
        )}
      </Pressable>
    </View>
  );
}

const styles = StyleSheet.create({
  card: {
    borderWidth: 1,
    borderRadius: 16,
    padding: 16,
    marginBottom: 16,
  },
  title: { fontSize: 16, fontWeight: "700" },
  hint: { fontSize: 13, lineHeight: 18, marginTop: 6, marginBottom: 12 },
  input: {
    borderWidth: 1,
    borderRadius: 12,
    paddingHorizontal: 14,
    paddingVertical: 12,
    fontSize: 16,
  },
  btn: {
    marginTop: 12,
    borderRadius: 12,
    paddingVertical: 12,
    alignItems: "center",
  },
  btnText: { color: "#fff", fontWeight: "700", fontSize: 15 },
});
