import { useEffect, useRef, useState } from "react";
import { Dimensions, Keyboard, Platform, type KeyboardEvent } from "react-native";

type KeyboardLayout = {
  /** Altura reportada do teclado (0 quando fechado). */
  height: number;
  /**
   * Espaço extra na base para manter o compositor visível.
   * Zero quando o SO já redimensionou a janela (adjustResize).
   */
  bottomInset: number;
};

/** Teclado virtual — altura e inset manual para Android quando resize falha. */
export function useKeyboardHeight(): KeyboardLayout {
  const [height, setHeight] = useState(0);
  const [bottomInset, setBottomInset] = useState(0);
  const windowHeightRef = useRef(Dimensions.get("window").height);
  const keyboardOpenRef = useRef(false);

  useEffect(() => {
    if (Platform.OS === "web") return;

    const measureInset = (kbHeight: number) => {
      if (Platform.OS === "ios") {
        setBottomInset(0);
        return;
      }
      const winH = Dimensions.get("window").height;
      const shrink = windowHeightRef.current - winH;
      const osHandled = kbHeight > 0 && shrink > kbHeight * 0.35;
      setBottomInset(osHandled ? 0 : kbHeight);
    };

    const onShow = (e: KeyboardEvent) => {
      keyboardOpenRef.current = true;
      const kbHeight = e.endCoordinates.height;
      setHeight(kbHeight);
      requestAnimationFrame(() => measureInset(kbHeight));
      setTimeout(() => measureInset(kbHeight), 60);
      setTimeout(() => measureInset(kbHeight), 180);
    };

    const onHide = () => {
      keyboardOpenRef.current = false;
      setHeight(0);
      setBottomInset(0);
      windowHeightRef.current = Dimensions.get("window").height;
    };

    const onDimChange = ({ window }: { window: { height: number } }) => {
      if (!keyboardOpenRef.current) {
        windowHeightRef.current = window.height;
      }
    };

    const showEvent =
      Platform.OS === "ios" ? "keyboardWillShow" : "keyboardDidShow";
    const hideEvent =
      Platform.OS === "ios" ? "keyboardWillHide" : "keyboardDidHide";

    const subShow = Keyboard.addListener(showEvent, onShow);
    const subHide = Keyboard.addListener(hideEvent, onHide);
    const subDim = Dimensions.addEventListener("change", onDimChange);

    return () => {
      subShow.remove();
      subHide.remove();
      subDim?.remove();
    };
  }, []);

  return { height, bottomInset };
}
