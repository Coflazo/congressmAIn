/**
 * PDF viewer with bbox highlight overlays.
 * when you click a speaker in the "Wie zei wat" tab, their segments glow yellow in the PDF.
 * uses renderPage from @react-pdf-viewer/core to inject custom overlay divs per page.
 */
import { useEffect, useRef, useMemo } from "react";
import { useTranslation } from "react-i18next";
import pdfWorkerUrl from "pdfjs-dist/build/pdf.worker.min.js?url";
import { Viewer, Worker } from "@react-pdf-viewer/core";
import type { RenderPageProps } from "@react-pdf-viewer/core";

import type { Segment } from "../lib/types";
import { API_BASE } from "../lib/api";

type BBox = [number, number, number, number]; // [x0, y0, x1, y1] — all 0-1 normalized

type PdfPanelProps = {
  meetingId: number;
  segments: Segment[]; // highlighted segments — empty means no highlight active
};

// one yellow box for a single segment highlight
function HighlightBox({ bbox, label }: { bbox: BBox; label?: string }) {
  const [x0, y0, x1, y1] = bbox;
  return (
    <div
      title={label}
      style={{
        position: "absolute",
        left: `${x0 * 100}%`,
        top: `${y0 * 100}%`,
        width: `${(x1 - x0) * 100}%`,
        height: `${(y1 - y0) * 100}%`,
        backgroundColor: "#F0E4B8", // --highlight from tokens
        opacity: 0.55,
        mixBlendMode: "multiply",
        borderRadius: "2px",
        pointerEvents: "none",
      }}
    />
  );
}

export function PdfPanel({ meetingId, segments }: PdfPanelProps) {
  const containerRef = useRef<HTMLDivElement>(null);
  const { t } = useTranslation();

  // group segments by page so we can look them up quickly inside renderPage
  const segmentsByPage = useMemo(() => {
    const map = new Map<number, Segment[]>();
    for (const seg of segments) {
      if (seg.page == null || !Array.isArray(seg.bbox) || seg.bbox.length !== 4) continue;
      const existing = map.get(seg.page) ?? [];
      existing.push(seg);
      map.set(seg.page, existing);
    }
    return map;
  }, [segments]);

  // when highlighted segments change, scroll the viewer to the first highlighted page
  useEffect(() => {
    if (!segments.length || !containerRef.current) return;

    const pages = segments
      .map((s) => s.page)
      .filter((p): p is number => p != null);
    if (!pages.length) return;

    const firstPage = Math.min(...pages);

    // @react-pdf-viewer uses data-testid="core__page-layer-{0-indexed}" for each page
    // we try a few selectors in case the internals changed between versions
    const pageEl =
      containerRef.current.querySelector(
        `[data-testid="core__page-layer-${firstPage - 1}"]`
      ) ??
      containerRef.current.querySelector(
        `.rpv-core__page-layer:nth-child(${firstPage})`
      );

    if (pageEl) {
      pageEl.scrollIntoView({ behavior: "smooth", block: "start" });
    }
  }, [segments]);

  // inject highlight overlays on top of each rendered page
  const renderPage = (props: RenderPageProps) => {
    // @react-pdf-viewer uses 0-indexed pageIndex; our segments use 1-indexed page numbers
    const pageNumber = props.pageIndex + 1;
    const pageSegments = segmentsByPage.get(pageNumber) ?? [];

    return (
      <>
        {props.canvasLayer.children}
        {props.textLayer.children}
        {props.annotationLayer.children}
        {pageSegments.length > 0 && (
          // overlay container — sits on top of the page, pointer-events off so PDF is still scrollable
          <div
            style={{
              position: "absolute",
              inset: 0,
              overflow: "hidden",
              pointerEvents: "none",
            }}
          >
            {pageSegments.map((seg) => (
              <HighlightBox
                key={seg.id}
                bbox={seg.bbox as BBox}
                label={`${seg.speaker ?? ""}${seg.party ? ` (${seg.party})` : ""}`}
              />
            ))}
          </div>
        )}
      </>
    );
  };

  const hasHighlights = segments.length > 0;

  return (
    <div className="grid gap-4 lg:grid-cols-[minmax(0,1fr)_260px]">
      {/* PDF viewer — takes up most of the width */}
      <div
        ref={containerRef}
        className="min-h-[600px] overflow-hidden rounded-lg border border-outline-variant/50 bg-surface-lowest"
        style={{ height: "80vh" }}
      >
        <Worker workerUrl={pdfWorkerUrl}>
          <Viewer
            fileUrl={`${API_BASE}/api/meetings/${meetingId}/pdf`}
            renderPage={renderPage}
          />
        </Worker>
      </div>

      {/* Sidebar — shows highlighted segments with page jump links */}
      <aside className="rounded-lg border border-outline-variant/50 bg-surface-low p-4">
        <h3 className="mb-3 font-serif text-xl text-on-surface">
          {hasHighlights ? t("pdf.markedPassages") : t("pdf.help")}
        </h3>

        {hasHighlights ? (
          <div className="space-y-3">
            <p className="text-xs text-on-surface-variant">
              {segments.length} {t("pdf.markedPassages").toLowerCase()}
            </p>
            {segments.map((seg) => (
              <button
                key={seg.id}
                onClick={() => {
                  // scroll to the page for this segment using the DOM query
                  if (!containerRef.current || !seg.page) return;
                  const pageEl =
                    containerRef.current.querySelector(
                      `[data-testid="core__page-layer-${seg.page - 1}"]`
                    ) ??
                    containerRef.current.querySelector(
                      `.rpv-core__page-layer:nth-child(${seg.page})`
                    );
                  pageEl?.scrollIntoView({ behavior: "smooth", block: "start" });
                }}
                className="w-full rounded border border-outline-variant/40 bg-surface-lowest p-3 text-left transition hover:border-primary/30 hover:bg-primary/5"
              >
                <div className="mb-1 text-xs font-mono uppercase text-primary">
                  {t("detail.page")} {seg.page ?? "?"} · {seg.intent}
                </div>
                {seg.speaker && (
                  <div className="text-sm font-medium">
                    {seg.speaker}
                    {seg.party ? ` (${seg.party})` : ""}
                  </div>
                )}
                <div className="mt-1.5 line-clamp-3 text-xs text-on-surface-variant">
                  {seg.text}
                </div>
              </button>
            ))}
          </div>
        ) : (
          // shown when no speaker is selected
          <div className="space-y-3 text-sm text-on-surface-variant">
            <p>{t("pdf.selectSpeakerHint")}</p>
            <p className="text-xs">{t("pdf.chatHint")}</p>
          </div>
        )}
      </aside>
    </div>
  );
}

export default PdfPanel;
