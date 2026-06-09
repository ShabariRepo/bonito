"use client";

import { useCallback, useEffect, useState } from "react";
import { CHAT_THEMES, type ChatTheme, type ChatThemeId } from "./chat-themes";

const STORAGE_KEY = "bonito.origami.chat-theme";

function readStored(): ChatThemeId {
  if (typeof window === "undefined") return "default";
  try {
    const v = window.localStorage.getItem(STORAGE_KEY);
    if (v && v in CHAT_THEMES) return v as ChatThemeId;
  } catch {
    /* localStorage might be unavailable */
  }
  return "default";
}

export function useOrigamiChatTheme() {
  const [themeId, setThemeIdState] = useState<ChatThemeId>("default");

  // Lazy-read on mount so SSR doesn't disagree with client
  useEffect(() => {
    setThemeIdState(readStored());
  }, []);

  const setThemeId = useCallback((id: ChatThemeId) => {
    setThemeIdState(id);
    try {
      window.localStorage.setItem(STORAGE_KEY, id);
    } catch {
      /* ignore */
    }
  }, []);

  const theme: ChatTheme = CHAT_THEMES[themeId];
  return { theme, themeId, setThemeId };
}
