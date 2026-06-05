/** Reconhecimento de voz no browser (Chrome/Edge) — evita enviar áudio ao Gemini (muito mais rápido). */

type SpeechRecognitionCtor = new () => SpeechRecognition;

function getSpeechRecognitionCtor(): SpeechRecognitionCtor | null {
  if (typeof window === "undefined") return null;
  const w = window as Window & {
    SpeechRecognition?: SpeechRecognitionCtor;
    webkitSpeechRecognition?: SpeechRecognitionCtor;
  };
  return w.SpeechRecognition || w.webkitSpeechRecognition || null;
}

export function webSpeechToTextAvailable(): boolean {
  return Boolean(getSpeechRecognitionCtor());
}

export type WebSpeechSession = {
  recognition: SpeechRecognition;
  textPromise: Promise<string>;
  stop: () => void;
};

export function startWebSpeechSession(lang = "pt-BR"): WebSpeechSession {
  const Ctor = getSpeechRecognitionCtor();
  if (!Ctor) {
    throw new Error("Reconhecimento de voz do browser indisponível.");
  }

  const recognition = new Ctor();
  recognition.lang = lang;
  recognition.interimResults = false;
  recognition.continuous = false;
  recognition.maxAlternatives = 1;

  let settled = false;
  let resolveText!: (value: string) => void;
  let rejectText!: (reason: Error) => void;

  const textPromise = new Promise<string>((resolve, reject) => {
    resolveText = resolve;
    rejectText = (err) => reject(err);
  });

  const finish = (fn: () => void) => {
    if (settled) return;
    settled = true;
    fn();
  };

  const hardCap = window.setTimeout(() => {
    finish(() => {
      try {
        recognition.stop();
      } catch {
        /* ignore */
      }
      rejectText(new Error("Não ouvi a tempo. Fale 3 segundos e toque Enviar voz."));
    });
  }, 25_000);

  recognition.onresult = (event) => {
    finish(() => {
      window.clearTimeout(hardCap);
      const text = (event.results?.[0]?.[0]?.transcript || "").trim();
      if (!text) {
        rejectText(new Error("Não percebi o que disse. Fale outra vez, mais perto do microfone."));
        return;
      }
      resolveText(text);
    });
  };

  recognition.onerror = (event) => {
    finish(() => {
      window.clearTimeout(hardCap);
      const code = (event as SpeechRecognitionErrorEvent).error || "";
      if (code === "no-speech") {
        rejectText(new Error("Nenhuma voz detetada. Fale 3 segundos e tente outra vez."));
        return;
      }
      if (code === "not-allowed" || code === "service-not-allowed") {
        rejectText(new Error("Permissão do microfone negada no browser."));
        return;
      }
      if (code === "aborted") {
        rejectText(new Error("Gravação cancelada."));
        return;
      }
      rejectText(
        new Error("Reconhecimento de voz falhou. Escreva em texto ou use Chrome no PC.")
      );
    });
  };

  recognition.onend = () => {
    window.setTimeout(() => {
      finish(() => {
        window.clearTimeout(hardCap);
        rejectText(new Error("Não ouvi nada. Fale 3 segundos e tente Enviar voz."));
      });
    }, 400);
  };

  try {
    recognition.start();
  } catch (err) {
    window.clearTimeout(hardCap);
    throw err instanceof Error ? err : new Error(String(err));
  }

  return {
    recognition,
    textPromise,
    stop: () => {
      try {
        recognition.stop();
      } catch {
        /* ignore */
      }
    },
  };
}
