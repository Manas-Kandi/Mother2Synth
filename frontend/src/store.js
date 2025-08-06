import { create } from "zustand";

export const useGlobalStore = create((set) => ({
  selectedFile: null,
  graphData: {},
  error: null,
  projectSlug: "",
  setGraphData: (data) => set({ graphData: data }),
  setSelectedFile: (file) => set({ selectedFile: file }),
  setError: (msg) => set({ error: msg }),
  setProjectSlug: (slug) => set({ projectSlug: slug }),
}));
