import React, { createContext, useContext, useMemo } from "react";
import { useColorScheme } from "react-native";
import { darkColors, lightColors, type AppColors } from "./colors";

const ThemeContext = createContext<AppColors>(lightColors);

export function ThemeProvider({ children }: { children: React.ReactNode }) {
  const scheme = useColorScheme();
  const colors = useMemo(
    () => (scheme === "dark" ? darkColors : lightColors),
    [scheme]
  );
  return <ThemeContext.Provider value={colors}>{children}</ThemeContext.Provider>;
}

export function useColors(): AppColors {
  return useContext(ThemeContext);
}

export { lightColors, darkColors };
