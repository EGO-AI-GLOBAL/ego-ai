import { MaterialCommunityIcons } from "@expo/vector-icons";
import React, { useState } from "react";
import {
  Platform,
  Pressable,
  StyleSheet,
  Text,
  TextInput,
  View,
  type TextInputProps,
  type ViewStyle,
} from "react-native";
import { useColors } from "@/theme/ThemeContext";

type PasswordKind = "login" | "new";

type Props = {
  label: string;
  value: string;
  onChangeText: (text: string) => void;
  placeholder?: string;
  kind?: PasswordKind;
  containerStyle?: ViewStyle;
} & Pick<TextInputProps, "onSubmitEditing" | "returnKeyType" | "editable">;

export function PasswordField({
  label,
  value,
  onChangeText,
  placeholder = "••••••••",
  kind = "login",
  containerStyle,
  onSubmitEditing,
  returnKeyType,
  editable = true,
}: Props) {
  const colors = useColors();
  const [visible, setVisible] = useState(false);

  const textContentType = kind === "new" ? "newPassword" : "password";
  const autoComplete =
    kind === "new" ? ("password-new" as const) : ("password" as const);

  return (
    <View style={containerStyle}>
      <Text style={[styles.label, { color: colors.textMuted }]}>{label}</Text>
      <View
        style={[
          styles.field,
          {
            backgroundColor: colors.bgCard,
            borderColor: colors.border,
          },
        ]}
      >
        <TextInput
          style={[styles.input, { color: colors.text }]}
          value={value}
          onChangeText={onChangeText}
          placeholder={placeholder}
          placeholderTextColor={colors.textMuted}
          secureTextEntry={!visible}
          autoCapitalize="none"
          autoCorrect={false}
          textContentType={textContentType}
          autoComplete={autoComplete}
          importantForAutofill="yes"
          onSubmitEditing={onSubmitEditing}
          returnKeyType={returnKeyType}
          editable={editable}
          selectionColor={colors.primary}
          underlineColorAndroid="transparent"
        />
        <Pressable
          onPress={() => setVisible((v) => !v)}
          style={({ pressed }) => [
            styles.toggle,
            pressed && { opacity: 0.65 },
          ]}
          hitSlop={10}
          accessibilityRole="button"
          accessibilityLabel={visible ? "Ocultar senha" : "Mostrar senha"}
          accessibilityHint={
            visible
              ? "A senha deixa de ser visível"
              : "A senha fica visível enquanto digita"
          }
        >
          <MaterialCommunityIcons
            name={visible ? "eye-off-outline" : "eye-outline"}
            size={24}
            color={visible ? colors.primary : colors.textMuted}
          />
        </Pressable>
      </View>
    </View>
  );
}

const styles = StyleSheet.create({
  label: { fontSize: 12, marginBottom: 6, marginTop: 8 },
  field: {
    flexDirection: "row",
    alignItems: "center",
    borderRadius: 24,
    borderWidth: StyleSheet.hairlineWidth,
    minHeight: 48,
    paddingLeft: 4,
    ...(Platform.OS === "web" ? ({ touchAction: "manipulation" } as object) : {}),
  },
  input: {
    flex: 1,
    fontSize: 16,
    paddingHorizontal: 14,
    paddingVertical: Platform.OS === "ios" ? 12 : 10,
  },
  toggle: {
    justifyContent: "center",
    alignItems: "center",
    width: 44,
    height: 44,
    marginRight: 2,
  },
});
