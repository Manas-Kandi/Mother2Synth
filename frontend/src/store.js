import { create } from "zustand";

export const useGlobalStore = create((set) => ({
  selectedFile: null,
  graphData: {},
  setGraphData: (data) => set({ graphData: data }),
  setSelectedFile: (file) => set({ selectedFile: file }),
}));
