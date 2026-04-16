import { Viewer, Worker } from "@react-pdf-viewer/core";

import type { Segment } from "../lib/types";
import { API_BASE } from "../lib/api";

type PdfPanelProps = {
  meetingId: number;
  segments: Segment[];
};

export function PdfPanel({ meetingId, segments }: PdfPanelProps) {
  return (
    <div className="grid gap-6 lg:grid-cols-[minmax(0,1fr)_280px]">
      <div className="min-h-[560px] overflow-hidden rounded-lg border border-outline-variant/50 bg-surface-lowest">
        <Worker workerUrl="https://unpkg.com/pdfjs-dist@3.11.174/build/pdf.worker.min.js">
          <Viewer fileUrl={`${API_BASE}/api/meetings/${meetingId}/pdf`} />
        </Worker>
      </div>
      <aside className="rounded-lg border border-outline-variant/50 bg-surface-low p-4">
        <h3 className="mb-3 font-serif text-xl">Highlights</h3>
        <div className="space-y-3 text-sm">
          {segments.length === 0 ? (
            <p className="text-on-surface-variant">Kies een spreker of citaat om gemarkeerde passages te zien.</p>
          ) : (
            segments.map((segment) => (
              <div key={segment.id} className="rounded border border-outline-variant/40 bg-surface-lowest p-3">
                <div className="mb-1 text-xs font-mono uppercase text-primary">
                  pagina {segment.page ?? "?"} · segment {segment.id}
                </div>
                <div className="font-medium">{segment.speaker ?? "Onbekend"}</div>
                <div className="mt-2 text-on-surface-variant">{segment.text}</div>
              </div>
            ))
          )}
        </div>
      </aside>
    </div>
  );
}
