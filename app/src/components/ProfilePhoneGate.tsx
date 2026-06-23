import { Redirect, useSegments } from "expo-router";
import React, { useEffect, useState } from "react";
import { ActivityIndicator, View } from "react-native";
import { useAuth } from "@/context/AuthContext";
import { useDashboard } from "@/hooks/useDashboard";
import { getLocalProfilePhone } from "@/storage/profilePhoneLocal";
import { useColors } from "@/theme/ThemeContext";
import { isProfilePhoneMissing } from "@/utils/profileComplete";
import { resolveUserId } from "@/utils/resolveUserId";

type Props = {
  children: React.ReactNode;
};

/** Contas antigas sem telefone — obriga a completar antes do resto do app. */
export function ProfilePhoneGate({ children }: Props) {
  const colors = useColors();
  const { session } = useAuth();
  const { data, loading } = useDashboard();
  const segments = useSegments();
  const onCompleteProfile = segments.includes("complete-profile");
  const [localPhone, setLocalPhone] = useState<string | null>(null);
  const [localReady, setLocalReady] = useState(false);
  const uid = resolveUserId(session, data.me?.user_id);

  useEffect(() => {
    if (!uid) {
      setLocalPhone(null);
      setLocalReady(true);
      return;
    }
    let cancelled = false;
    setLocalReady(false);
    void getLocalProfilePhone(uid).then((ph) => {
      if (!cancelled) {
        setLocalPhone(ph);
        setLocalReady(true);
      }
    });
    return () => {
      cancelled = true;
    };
  }, [uid, onCompleteProfile]);

  if (!localReady || loading) {
    return (
      <View
        style={{
          flex: 1,
          justifyContent: "center",
          alignItems: "center",
          backgroundColor: colors.bg,
        }}
      >
        <ActivityIndicator size="large" color={colors.primary} />
      </View>
    );
  }

  const missing = isProfilePhoneMissing(data.me, localPhone);

  if (missing && !onCompleteProfile) {
    return <Redirect href="/(main)/complete-profile" />;
  }

  if (!missing && onCompleteProfile) {
    return <Redirect href="/(main)/chat" />;
  }

  return <>{children}</>;
}
