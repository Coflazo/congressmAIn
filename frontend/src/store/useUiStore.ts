import { create } from "zustand";

type UiState = {
  activeSpeakerId: string | null;
  highlightedSegmentIds: number[];
  setActiveSpeaker: (speakerId: string | null) => void;
  setHighlightedSegments: (segmentIds: number[]) => void;
  clearSelection: () => void;
};

export const useUiStore = create<UiState>((set) => ({
  activeSpeakerId: null,
  highlightedSegmentIds: [],
  setActiveSpeaker: (activeSpeakerId) => set({ activeSpeakerId, highlightedSegmentIds: [] }),
  setHighlightedSegments: (highlightedSegmentIds) => set({ highlightedSegmentIds }),
  clearSelection: () => set({ activeSpeakerId: null, highlightedSegmentIds: [] }),
}));
