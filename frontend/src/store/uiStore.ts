/**
 * Zustand store for global UI state.
 */
import { create } from "zustand";

interface UIState {
  sidebarOpen: boolean;
  mobileMenuOpen: boolean;
  darkMode: boolean;
  toggleSidebar: () => void;
  setMobileMenu: (open: boolean) => void;
  toggleDarkMode: () => void;
}

export const useUIStore = create<UIState>((set) => ({
  sidebarOpen: true,
  mobileMenuOpen: false,
  darkMode: true,
  toggleSidebar: () => set((s) => ({ sidebarOpen: !s.sidebarOpen })),
  setMobileMenu: (open) => set({ mobileMenuOpen: open }),
  toggleDarkMode: () => set((s) => ({ darkMode: !s.darkMode })),
}));
