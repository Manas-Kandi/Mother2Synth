import { create } from "zustand";

export const useGlobalStore = create((set) => ({
  selectedFile: null,
  graphData: {},
  error: null,
  setGraphData: (data) => set({ graphData: data }),
  setSelectedFile: (file) => set({ selectedFile: file }),
  setError: (msg) => set({ error: msg }),
}));
