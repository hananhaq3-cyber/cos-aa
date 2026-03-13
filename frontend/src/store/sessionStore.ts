/**
 * Zustand store for session and chat state management.
 */
import { create } from "zustand";
import type { CycleResult, Message, Session } from "../types";

interface SessionState {
  currentSession: Session | null;
  sessions: Session[];
  messages: Message[];
  currentPhase: string;
  isProcessing: boolean;
  cycleResults: CycleResult[];

  setSession: (session: Session | null) => void;
  setSessions: (sessions: Session[]) => void;
  loadSession: (session: Session) => void;
  addMessage: (message: Message) => void;
  setMessages: (messages: Message[]) => void;
  setPhase: (phase: string) => void;
  setProcessing: (processing: boolean) => void;
  addCycleResult: (result: CycleResult) => void;
  reset: () => void;
}

export const useSessionStore = create<SessionState>((set) => ({
  currentSession: null,
  sessions: [],
  messages: [],
  currentPhase: "IDLE",
  isProcessing: false,
  cycleResults: [],

  setSession: (session) => set({ currentSession: session }),
  setSessions: (sessions) => set({ sessions }),
  loadSession: (session) =>
    set({
      currentSession: session,
      messages: [],
      currentPhase: "IDLE",
      isProcessing: false,
      cycleResults: [],
    }),
  addMessage: (message) =>
    set((state) => ({ messages: [...state.messages, message] })),
  setMessages: (messages) => set({ messages }),
  setPhase: (phase) => set({ currentPhase: phase }),
  setProcessing: (processing) => set({ isProcessing: processing }),
  addCycleResult: (result) =>
    set((state) => ({ cycleResults: [...state.cycleResults, result] })),
  reset: () =>
    set({
      currentSession: null,
      sessions: [],
      messages: [],
      currentPhase: "IDLE",
      isProcessing: false,
      cycleResults: [],
    }),
}));
