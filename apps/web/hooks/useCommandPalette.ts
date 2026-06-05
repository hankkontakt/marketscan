"use client";

import { create } from "zustand";

interface CommandPaletteStore {
  isOpen: boolean;
  open: () => void;
  close: () => void;
  toggle: () => void;
}

// Zustand isn't in deps yet — use a simple event-based approach
let _listeners: Array<(open: boolean) => void> = [];
let _state = false;

function emit(val: boolean) {
  _state = val;
  _listeners.forEach((fn) => fn(val));
}

export function useCommandPalette() {
  return {
    open: () => emit(true),
    close: () => emit(false),
    toggle: () => emit(!_state),
    subscribe: (fn: (open: boolean) => void) => {
      _listeners.push(fn);
      return () => { _listeners = _listeners.filter((l) => l !== fn); };
    },
  };
}
