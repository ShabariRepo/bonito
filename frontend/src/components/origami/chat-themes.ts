/**
 * Chat-window themes for Origami. Each theme overrides ONLY the chat
 * surface — scroller background, message bubbles, composer input, font.
 * The rest of the app (sidebar, page header, resources grid, etc.) stays
 * on the Bonito design tokens.
 *
 * Themes are stored client-side per user via localStorage; the user can
 * swap them at any time from the palette dropdown in the chat header.
 */

export type ChatThemeId =
  | "default"
  | "oregon"
  | "hacker"
  | "candy"
  | "japanese"
  | "dracula"
  | "lofi";

export interface ChatTheme {
  id: ChatThemeId;
  label: string;
  /** Small color row shown in the picker swatch */
  swatch: string[];
  /** Background of the scrolling chat body */
  scrollBg: string;
  /** Background tint of the chat header / composer area */
  surfaceBg: string;
  /** User message bubble classes */
  userBubble: string;
  /** Assistant message bubble classes */
  assistantBubble: string;
  /** Plan card wrapper override (null = use default) */
  planCardClass?: string;
  /** Composer container classes */
  composerBg: string;
  /** Input element classes — concatenated with the shadcn Input default */
  inputClass: string;
  /** Send button override classes — replaces default if set */
  sendBtnClass?: string;
  /** Font family class applied to every chat text element */
  font: string;
  /** Color class for the streaming-cursor caret */
  cursorClass: string;
  /** Color class for empty-state and placeholder text */
  mutedTextClass: string;
  /** Border tone used for separators inside the chat surface */
  separatorClass: string;
  /** Watermark crane fill — a single CSS color tuned for this theme */
  watermarkColor: string;
  /** Watermark crane opacity (0-1) tuned so foreground text stays sharp */
  watermarkOpacity: number;
}

export const CHAT_THEMES: Record<ChatThemeId, ChatTheme> = {
  default: {
    id: "default",
    label: "Bonito",
    swatch: ["#7c3aed", "#a78bfa", "#1f1f1f", "#f5f0e8"],
    scrollBg: "bg-transparent",
    surfaceBg: "bg-transparent",
    userBubble: "bg-primary text-primary-foreground",
    assistantBubble: "bg-muted text-foreground border border-border",
    composerBg: "border-t border-border bg-transparent",
    inputClass: "",
    font: "font-sans",
    cursorClass: "bg-primary",
    mutedTextClass: "text-muted-foreground",
    separatorClass: "border-border",
    watermarkColor: "#ffffff",
    watermarkOpacity: 0.07,
  },

  oregon: {
    id: "oregon",
    label: "Oregon Trail",
    swatch: ["#3d2817", "#8b5a2b", "#d4a574", "#f5e6c8"],
    scrollBg:
      "bg-gradient-to-b from-[#f5e6c8] to-[#d4a574]/40 dark:from-[#2a1d10] dark:to-[#3d2817]",
    surfaceBg: "bg-[#d4a574]/30 backdrop-blur-sm",
    userBubble:
      "bg-[#8b5a2b] text-[#f5e6c8] border border-[#3d2817]/50 shadow-sm",
    assistantBubble:
      "bg-[#f5e6c8] text-[#3d2817] border-2 border-[#8b5a2b]/60 dark:bg-[#3d2817] dark:text-[#f5e6c8] dark:border-[#8b5a2b]/80",
    composerBg:
      "border-t-2 border-[#8b5a2b]/50 bg-[#f5e6c8]/80 dark:bg-[#2a1d10]/80",
    inputClass:
      "bg-[#f5e6c8] text-[#3d2817] placeholder:text-[#8b5a2b]/70 border-[#8b5a2b]/60 focus:border-[#3d2817] dark:bg-[#3d2817] dark:text-[#f5e6c8] caret-[#8b5a2b]",
    sendBtnClass: "bg-[#8b5a2b] text-[#f5e6c8] hover:bg-[#3d2817]",
    font: "font-serif",
    cursorClass: "bg-[#8b5a2b]",
    mutedTextClass: "text-[#8b5a2b]",
    separatorClass: "border-[#8b5a2b]/40",
    watermarkColor: "#ffffff",
    watermarkOpacity: 0.06,
  },

  hacker: {
    id: "hacker",
    label: "Hacker terminal",
    swatch: ["#000000", "#10b981", "#34d399", "#022c22"],
    scrollBg: "bg-black",
    surfaceBg: "bg-black",
    userBubble:
      "bg-emerald-900/40 text-emerald-300 border border-emerald-500/60 shadow-[0_0_12px_rgba(16,185,129,0.15)]",
    assistantBubble:
      "bg-zinc-950 text-emerald-400 border border-emerald-500/40 shadow-[0_0_8px_rgba(16,185,129,0.10)]",
    composerBg: "border-t border-emerald-500/30 bg-black",
    inputClass:
      "bg-black text-emerald-300 placeholder:text-emerald-700 border-emerald-500/40 focus:border-emerald-400 caret-emerald-400",
    sendBtnClass:
      "bg-emerald-500 text-black hover:bg-emerald-400 font-mono uppercase tracking-wider",
    font: "font-mono",
    cursorClass: "bg-emerald-400",
    mutedTextClass: "text-emerald-700",
    separatorClass: "border-emerald-500/30",
    watermarkColor: "#ffffff",
    watermarkOpacity: 0.10,
  },

  candy: {
    id: "candy",
    label: "Candy land",
    swatch: ["#fdf2f8", "#f472b6", "#fde047", "#a78bfa"],
    scrollBg: "bg-pink-50 dark:bg-pink-950/20",
    surfaceBg: "bg-pink-100/60 dark:bg-pink-950/40",
    userBubble:
      "bg-pink-400 text-white shadow-lg shadow-pink-200/50 dark:shadow-pink-900/30",
    assistantBubble:
      "bg-yellow-100 text-pink-900 border-2 border-pink-200 dark:bg-yellow-100/90 dark:text-pink-950",
    composerBg: "border-t-2 border-pink-200 bg-pink-50 dark:bg-pink-950/40",
    inputClass:
      "bg-white text-pink-900 placeholder:text-pink-300 border-pink-300 focus:border-pink-500 dark:bg-pink-50",
    sendBtnClass:
      "bg-pink-500 text-white hover:bg-pink-600 rounded-full shadow-md shadow-pink-300/50",
    font: "font-sans",
    cursorClass: "bg-pink-500",
    mutedTextClass: "text-pink-500",
    separatorClass: "border-pink-200",
    watermarkColor: "#ffffff",
    watermarkOpacity: 0.10,
  },

  japanese: {
    id: "japanese",
    label: "和風 Wafū",
    swatch: ["#faf3e0", "#9f1b0f", "#1a1a1a", "#8b7355"],
    scrollBg: "bg-[#faf3e0] dark:bg-[#2a2420]",
    surfaceBg: "bg-[#faf3e0] dark:bg-[#2a2420]",
    userBubble:
      "bg-[#9f1b0f] text-[#faf3e0] border border-[#7a140b]",
    assistantBubble:
      "bg-[#f5ead0] text-[#1a1a1a] border border-[#8b7355] dark:bg-[#3a322a] dark:text-[#faf3e0] dark:border-[#5a4a3a]",
    composerBg:
      "border-t border-[#8b7355]/40 bg-[#faf3e0] dark:bg-[#2a2420]",
    inputClass:
      "bg-[#fdf8eb] text-[#1a1a1a] placeholder:text-[#8b7355] border-[#8b7355] focus:border-[#9f1b0f] dark:bg-[#3a322a] dark:text-[#faf3e0]",
    sendBtnClass:
      "bg-[#9f1b0f] text-[#faf3e0] hover:bg-[#7a140b]",
    font: "font-serif tracking-wide",
    cursorClass: "bg-[#9f1b0f]",
    mutedTextClass: "text-[#8b7355]",
    separatorClass: "border-[#8b7355]/40",
    watermarkColor: "#ffffff",
    watermarkOpacity: 0.08,
  },

  dracula: {
    id: "dracula",
    label: "Dracula",
    swatch: ["#282a36", "#bd93f9", "#ff79c6", "#50fa7b"],
    scrollBg: "bg-[#282a36]",
    surfaceBg: "bg-[#21222c]",
    userBubble: "bg-[#bd93f9] text-[#282a36] font-medium",
    assistantBubble:
      "bg-[#44475a] text-[#f8f8f2] border border-[#6272a4]",
    composerBg: "border-t border-[#44475a] bg-[#21222c]",
    inputClass:
      "bg-[#282a36] text-[#f8f8f2] placeholder:text-[#6272a4] border-[#44475a] focus:border-[#bd93f9] caret-[#ff79c6]",
    sendBtnClass:
      "bg-[#ff79c6] text-[#282a36] hover:bg-[#ff9ed5] font-medium",
    font: "font-mono",
    cursorClass: "bg-[#ff79c6]",
    mutedTextClass: "text-[#6272a4]",
    separatorClass: "border-[#44475a]",
    watermarkColor: "#ffffff",
    watermarkOpacity: 0.12,
  },

  lofi: {
    id: "lofi",
    label: "Lofi",
    swatch: ["#fdf6ec", "#d4a574", "#a67c5b", "#5c4033"],
    scrollBg: "bg-[#fdf6ec] dark:bg-[#2a241e]",
    surfaceBg: "bg-[#fdf6ec] dark:bg-[#2a241e]",
    userBubble:
      "bg-[#d4a574] text-[#3a2818] dark:bg-[#a67c5b] dark:text-[#fdf6ec]",
    assistantBubble:
      "bg-[#f0e4d0] text-[#5c4033] border border-[#d4a574]/60 dark:bg-[#3a322a] dark:text-[#fdf6ec] dark:border-[#a67c5b]/60",
    composerBg:
      "border-t border-[#d4a574]/40 bg-[#fdf6ec] dark:bg-[#2a241e]",
    inputClass:
      "bg-[#fdf6ec] text-[#3a2818] placeholder:text-[#a67c5b] border-[#d4a574]/60 focus:border-[#a67c5b] dark:bg-[#3a322a] dark:text-[#fdf6ec]",
    sendBtnClass:
      "bg-[#a67c5b] text-[#fdf6ec] hover:bg-[#5c4033]",
    font: "font-serif",
    cursorClass: "bg-[#a67c5b]",
    mutedTextClass: "text-[#a67c5b]",
    separatorClass: "border-[#d4a574]/40",
    watermarkColor: "#ffffff",
    watermarkOpacity: 0.10,
  },
};

export const CHAT_THEME_LIST: ChatTheme[] = Object.values(CHAT_THEMES);
