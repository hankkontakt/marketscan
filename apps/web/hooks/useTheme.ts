"use client";

import { useEffect, useState, useCallback } from "react";

export type Theme = "light" | "dark" | "auto";

function resolveTheme(pref: Theme): "light" | "dark" {
  if (pref === "auto") {
    if (typeof window === "undefined") return "light";
    return window.matchMedia("(prefers-color-scheme: dark)").matches ? "dark" : "light";
  }
  return pref;
}

export function useTheme() {
  const [theme, setThemeState] = useState<Theme>("light");
  const [resolved, setResolved] = useState<"light" | "dark">("light");

  const apply = useCallback((t: Theme) => {
    const effective = resolveTheme(t);
    setThemeState(t);
    setResolved(effective);
    document.documentElement.setAttribute("data-theme", effective);
    localStorage.setItem("ms-theme", t);
  }, []);

  // Init from localStorage on mount
  useEffect(() => {
    const stored = (localStorage.getItem("ms-theme") as Theme) ?? "light";
    apply(stored);
  }, [apply]);

  // Listen for system preference changes when in auto mode
  useEffect(() => {
    const mq = window.matchMedia("(prefers-color-scheme: dark)");
    const handler = () => {
      const current = localStorage.getItem("ms-theme") as Theme | null;
      if (current === "auto") {
        apply("auto");
      }
    };
    mq.addEventListener("change", handler);
    return () => mq.removeEventListener("change", handler);
  }, [apply]);

  const setTheme = useCallback((t: Theme) => apply(t), [apply]);

  const toggle = useCallback(() => {
    const current = localStorage.getItem("ms-theme") as Theme | null;
    if (current === "auto") {
      const r = resolveTheme("auto");
      apply(r === "dark" ? "light" : "dark");
    } else {
      apply(current === "dark" ? "light" : "dark");
    }
  }, [apply]);

  return { theme, resolved, setTheme, toggle };
}
