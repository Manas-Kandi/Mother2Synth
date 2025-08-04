import { create } from "zustand";

export const useGlobalStore = create((set) => ({
  selectedFile: null,
  graphData: {},
  projectSlug: "",
  setProjectSlug: (slug) => set({ projectSlug: slug }),
  setGraphData: (data) => set({ graphData: data }),
  setSelectedFile: (file) => set({ selectedFile: file }),
}));
