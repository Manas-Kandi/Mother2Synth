import { create } from "zustand";

export const useGlobalStore = create((set) => ({
  selectedFile: null,
  graphData: {},
  projectSlug: "",
  setGraphData: (data) => set({ graphData: data }),
  setSelectedFile: (file) => set({ selectedFile: file }),
  setProjectSlug: (slug) => set({ projectSlug: slug }),
}));
