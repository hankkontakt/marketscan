"use client";

import { useEffect, useState } from "react";

type Theme = "dark" | "light";

export function useTheme() {
  const [theme, setTheme] = useState<Theme>("dark");

  useEffect(() => {
    const stored = localStorage.getItem("ms-theme") as Theme | null;
    if (stored) apply(stored);
  }, []);

  function apply(t: Theme) {
    setTheme(t);
    document.documentElement.setAttribute("data-theme", t);
    localStorage.setItem("ms-theme", t);
  }

  return { theme, toggle: () => apply(theme === "dark" ? "light" : "dark") };
}
