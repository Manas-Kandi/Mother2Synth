import { create } from "zustand";

export const useGlobalStore = create((set) => ({
  selectedFile: null,
  graphData: null,
  setSelectedFile: (file) => set({ selectedFile: file }),
  setGraphData: (data) => set({ graphData: data }),
}));
