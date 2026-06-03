import { router, useLocalSearchParams } from "expo-router";
import React, { useEffect, useState } from "react";
import {
  ActivityIndicator,
  Linking,
  Pressable,
  StyleSheet,
  Text,
  View,
} from "react-native";
import { SafeAreaView } from "react-native-safe-area-context";
import { fetchLegalMarkdown, type LegalDoc } from "@/api/client";
import { LegalMarkdown } from "@/components/LegalMarkdown";
import { PRIVACY_POLICY_URL } from "@/constants/config";
import { useColors } from "@/theme/ThemeContext";

const TITLES: Record<LegalDoc, string> = {
  privacy: "Política de Privacidade",
  terms: "Termos de Uso",
  refund: "Política de Reembolso",
};

function normalizeDoc(raw: string | string[] | undefined): LegalDoc {
  const d = Array.isArray(raw) ? raw[0] : raw;
  if (d === "terms" || d === "refund" || d === "privacy") return d;
  return "privacy";
}

export default function LegalScreen() {
  const colors = useColors();
  const params = useLocalSearchParams<{ doc?: string }>();
  const doc = normalizeDoc(params.doc);
  const [markdown, setMarkdown] = useState("");
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    (async () => {
      setLoading(true);
      setError(null);
      try {
        setMarkdown(await fetchLegalMarkdown(doc));
      } catch (e) {
        setError(e instanceof Error ? e.message : "Não foi possível carregar.");
      } finally {
        setLoading(false);
      }
    })();
  }, [doc]);

  const openPublicUrl = () => {
    if (PRIVACY_POLICY_URL && doc === "privacy") {
      Linking.openURL(PRIVACY_POLICY_URL);
    }
  };

  return (
    <SafeAreaView style={[styles.fill, { backgroundColor: colors.bg }]}>
      <View style={[styles.header, { borderBottomColor: colors.border }]}>
        <Pressable onPress={() => router.back()} hitSlop={12}>
          <Text style={[styles.back, { color: colors.primaryLight }]}>← Voltar</Text>
        </Pressable>
        <Text style={[styles.title, { color: colors.text }]}>{TITLES[doc]}</Text>
        {PRIVACY_POLICY_URL && doc === "privacy" ? (
          <Pressable onPress={openPublicUrl}>
            <Text style={[styles.link, { color: colors.primaryLight }]}>Abrir no browser</Text>
          </Pressable>
        ) : null}
      </View>
      {loading ? (
        <ActivityIndicator color={colors.primary} style={{ marginTop: 40 }} />
      ) : error ? (
        <Text style={[styles.error, { color: colors.danger }]}>{error}</Text>
      ) : (
        <LegalMarkdown markdown={markdown} colors={colors} />
      )}
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  fill: { flex: 1 },
  header: {
    paddingHorizontal: 16,
    paddingVertical: 12,
    borderBottomWidth: StyleSheet.hairlineWidth,
  },
  back: { fontSize: 16, fontWeight: "600", marginBottom: 8 },
  title: { fontSize: 20, fontWeight: "800" },
  link: { fontSize: 14, marginTop: 8, fontWeight: "600" },
  error: { padding: 20, fontSize: 15 },
});
