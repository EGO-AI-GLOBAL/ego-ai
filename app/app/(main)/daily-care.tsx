import { useFocusEffect } from "expo-router";
import React, { useCallback, useMemo, useState } from "react";
import {
  ActivityIndicator,
  RefreshControl,
  ScrollView,
  StyleSheet,
  Text,
  View,
} from "react-native";
import { DailyCareChallenge } from "@/components/DailyCareChallenge";
import {
  MoodMonsterStickyPet,
  type MonsterPetPlayRequest,
} from "@/components/moodMonsters/MoodMonsterStickyPet";
import { ScreenShell } from "@/components/ScreenShell";
import { TrialBanner } from "@/components/TrialBanner";
import { useAuth } from "@/context/AuthContext";
import { useDashboard } from "@/hooks/useDashboard";
import { useColors } from "@/theme/ThemeContext";

/** Monstrinhos do Humor — pet sticky no topo; scroll com humor + missões. */
export default function DailyCareScreen() {
  const colors = useColors();
  const { session } = useAuth();
  const { data, loading, refreshing, error, refresh, mergeDailyCare } = useDashboard();
  const userId = data.me?.user_id?.trim() ?? session?.user?.id?.trim() ?? "";

  const [previewMood, setPreviewMood] = useState<string | undefined>();
  const [playRequest, setPlayRequest] = useState<MonsterPetPlayRequest | null>(null);

  const stickyMood = useMemo(() => {
    if (previewMood) return previewMood;
    if (data.daily_care?.checked_today && data.daily_care.last_mood) {
      return data.daily_care.last_mood;
    }
    return undefined;
  }, [previewMood, data.daily_care?.checked_today, data.daily_care?.last_mood]);

  useFocusEffect(
    useCallback(() => {
      // Já tem pergunta do dia → não forçar spinner ao abrir (Finch: humor em <10s).
      if (data.daily_care?.question) return;
      void refresh();
    }, [refresh, data.daily_care?.question])
  );

  const showPet = Boolean(data.daily_care?.question) && (!loading || refreshing);

  return (
    <ScreenShell title="Monstrinhos do Humor" subtitle="1 toque por dia · ranking · Stories">
      <View style={styles.body}>
        {showPet ? (
          <MoodMonsterStickyPet
            colors={colors}
            moodKey={stickyMood}
            moods={data.daily_care?.moods}
            playRequest={playRequest}
            onPlayDone={() => setPlayRequest(null)}
          />
        ) : null}
        <ScrollView
          style={styles.scroll}
          contentContainerStyle={styles.scrollContent}
          refreshControl={
            <RefreshControl refreshing={refreshing} onRefresh={refresh} tintColor={colors.primary} />
          }
        >
          {loading && !refreshing ? (
            <ActivityIndicator color={colors.primary} style={{ marginTop: 24 }} />
          ) : null}
          {error ? (
            <Text style={[styles.error, { color: colors.danger }]}>{error}</Text>
          ) : null}
          {!loading || refreshing ? (
            <DailyCareChallenge
              colors={colors}
              care={data.daily_care}
              userId={userId}
              onUpdate={(care, journey) => mergeDailyCare(care, journey)}
              onPetMoodPreview={setPreviewMood}
              onPetPlay={setPlayRequest}
              afterMood={
                <>
                  <TrialBanner colors={colors} access={data.access} journey={data.wellness_journey} />
                  <Text style={[styles.lead, { color: colors.textMuted }]}>
                    Pet no topo — humor define a cor · missões fazem ele reagir.
                  </Text>
                </>
              }
            />
          ) : null}
        </ScrollView>
      </View>
    </ScreenShell>
  );
}

const styles = StyleSheet.create({
  body: { flex: 1 },
  scroll: { flex: 1 },
  scrollContent: { paddingHorizontal: 16, paddingBottom: 32 },
  lead: { fontSize: 14, lineHeight: 20, marginBottom: 12 },
  error: { marginBottom: 12, fontSize: 14 },
});
