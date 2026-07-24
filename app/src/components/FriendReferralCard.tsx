import React, { useCallback, useEffect, useState } from "react";
import {
  ActivityIndicator,
  Alert,
  Linking,
  Pressable,
  StyleSheet,
  Text,
  TextInput,
  View,
} from "react-native";
import {
  createFriendReferralInvite,
  fetchFriendReferralStatus,
  type FriendReferralStatus,
} from "@/api/client";
import type { AppColors } from "@/theme/colors";
import { formatPhoneBrInput } from "@/utils/phoneBr";
import { validateEmail, validatePhone } from "@/utils/validation";
import { shareWhatsAppText } from "@/utils/whatsappShare";

type Props = {
  colors: AppColors;
};

function phoneToWaDigits(phone: string): string {
  let d = phone.replace(/\D/g, "");
  if (d.startsWith("55") && d.length >= 12) return d;
  if (d.length === 10 || d.length === 11) return `55${d}`;
  return d;
}

function buildInviteMessage(opts: {
  shareUrl: string;
  stripeUrl?: string | null;
  code?: string;
}): string {
  return [
    "Oi! Indiquei-te no EGO-AI.",
    "Cria a conta com este e-mail/telefone e assina o Premium no Stripe (não App Store/Play):",
    opts.stripeUrl || opts.shareUrl,
    opts.shareUrl && opts.stripeUrl ? `Cadastro: ${opts.shareUrl}` : "",
    opts.code ? `Código: ${opts.code}` : "",
  ]
    .filter(Boolean)
    .join("\n");
}

async function openWhatsApp(phone: string, message: string): Promise<void> {
  const digits = phoneToWaDigits(phone);
  const encoded = encodeURIComponent(message);
  if (digits) {
    const url = `https://wa.me/${digits}?text=${encoded}`;
    try {
      await Linking.openURL(url);
      return;
    } catch {
      /* fallback */
    }
  }
  await shareWhatsAppText(message);
}

export function FriendReferralCard({ colors }: Props) {
  const [status, setStatus] = useState<FriendReferralStatus | null>(null);
  const [email, setEmail] = useState("");
  const [phone, setPhone] = useState("");
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState(false);

  const load = useCallback(async () => {
    try {
      const s = await fetchFriendReferralStatus();
      setStatus(s);
    } catch {
      setStatus(null);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    void load();
  }, [load]);

  const onInvite = async () => {
    const emailErr = validateEmail(email);
    if (emailErr) {
      Alert.alert("E-mail", emailErr);
      return;
    }
    const phoneErr = validatePhone(phone, true);
    if (phoneErr) {
      Alert.alert("Telefone", phoneErr);
      return;
    }
    const phoneForWa = phone.trim();
    setBusy(true);
    try {
      const res = await createFriendReferralInvite(email.trim(), phoneForWa);
      setEmail("");
      setPhone("");
      await load();
      const message = buildInviteMessage({
        shareUrl: res.share_url,
        stripeUrl: res.stripe_checkout_url,
        code: res.code,
      });
      await openWhatsApp(phoneForWa, message);
    } catch (e) {
      Alert.alert(
        "Não foi possível indicar",
        e instanceof Error
          ? e.message
          : "Esta pessoa já pode ter e-mail ou telefone cadastrado."
      );
    } finally {
      setBusy(false);
    }
  };

  const onShareExisting = () => {
    if (!status?.share_url && !status?.stripe_checkout_url) return;
    const message = buildInviteMessage({
      shareUrl: status.share_url || "",
      stripeUrl: status.stripe_checkout_url,
      code: status.code,
    });
    void shareWhatsAppText(message);
  };

  return (
    <View style={[styles.card, { borderColor: colors.border, backgroundColor: colors.bgCard }]}>
      <Text style={[styles.title, { color: colors.text }]}>Indique um amigo</Text>
      <Text style={[styles.hint, { color: colors.textMuted }]}>
        {status?.tagline ||
          "Coloca o e-mail e o telefone do amigo. Enviamos o link Stripe pelo WhatsApp. Se ele assinar o Premium, você ganha 1 mês grátis. Só quem ainda não tem conta no EGO."}
      </Text>

      {loading ? (
        <ActivityIndicator color={colors.primary} style={{ marginVertical: 12 }} />
      ) : (
        <>
          {status?.code ? (
            <Text style={[styles.code, { color: colors.text }]}>
              O teu código: {status.code}
            </Text>
          ) : null}
          {status?.rewards_earned ? (
            <Text style={[styles.meta, { color: colors.textMuted }]}>
              Meses ganhos: {status.rewards_earned}
            </Text>
          ) : null}
          {status?.referral_bonus_until ? (
            <Text style={[styles.meta, { color: colors.textMuted }]}>
              Bónus até: {String(status.referral_bonus_until).slice(0, 10)}
            </Text>
          ) : null}

          <TextInput
            value={email}
            onChangeText={setEmail}
            placeholder="E-mail do amigo"
            placeholderTextColor={colors.textMuted}
            keyboardType="email-address"
            autoCapitalize="none"
            autoCorrect={false}
            editable={!busy}
            style={[
              styles.input,
              { color: colors.text, borderColor: colors.border, backgroundColor: colors.bg },
            ]}
          />
          <TextInput
            value={phone}
            onChangeText={(t) => setPhone(formatPhoneBrInput(t))}
            placeholder="Telefone com DDD (WhatsApp)"
            placeholderTextColor={colors.textMuted}
            keyboardType="phone-pad"
            editable={!busy}
            style={[
              styles.input,
              {
                color: colors.text,
                borderColor: colors.border,
                backgroundColor: colors.bg,
                marginTop: 10,
              },
            ]}
          />

          <Pressable
            onPress={() => void onInvite()}
            disabled={busy}
            style={[styles.btn, { backgroundColor: "#128C7E", opacity: busy ? 0.7 : 1 }]}
          >
            {busy ? (
              <ActivityIndicator color="#fff" />
            ) : (
              <Text style={styles.btnText}>Enviar no WhatsApp</Text>
            )}
          </Pressable>

          {status?.share_url || status?.stripe_checkout_url ? (
            <Pressable
              onPress={onShareExisting}
              style={({ pressed }) => [
                styles.secondary,
                { borderColor: colors.border, opacity: pressed ? 0.75 : 1 },
              ]}
            >
              <Text style={[styles.secondaryText, { color: colors.primary }]}>
                Partilhar o meu link no WhatsApp
              </Text>
            </Pressable>
          ) : null}
        </>
      )}
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
  code: { fontSize: 14, fontWeight: "700", marginBottom: 6 },
  meta: { fontSize: 12, marginBottom: 4 },
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
  secondary: {
    marginTop: 10,
    borderWidth: 1,
    borderRadius: 12,
    paddingVertical: 12,
    alignItems: "center",
  },
  secondaryText: { fontWeight: "700", fontSize: 14 },
});
