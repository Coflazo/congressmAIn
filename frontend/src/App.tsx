import { FormEvent, ReactNode, Suspense, lazy, useEffect, useMemo, useRef, useState } from "react";
import { QueryClient, QueryClientProvider, useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useTranslation } from "react-i18next";
import { BrowserRouter, Link, Navigate, Route, Routes, useParams } from "react-router-dom";

import "./i18n";
import "./styles/index.css";
import { API_BASE, ApiError, api } from "./lib/api";
import type {
  AdminMeeting,
  AdminMetrics,
  AdminSubscriber,
  ChatResponse,
  MeetingDetail,
  MeetingListItem,
  Segment,
  SpeakerSummary,
} from "./lib/types";
import { Layout } from "./components/Layout";
import { useUiStore } from "./store/useUiStore";

const queryClient = new QueryClient({
  defaultOptions: { queries: { staleTime: 30_000, retry: 1 } },
});

const PdfPanel = lazy(() => import("./components/PdfPanel"));

// ── Design constants ─────────────────────────────────────────────────────────
const ALL_TOPICS = [
  "housing", "climate", "infrastructure", "social-affairs",
  "education", "finance", "culture", "digital-affairs", "healthcare",
] as const;
type Topic = typeof ALL_TOPICS[number];

const STATUS_STYLES: Record<string, string> = {
  ready: "bg-tertiary/10 text-tertiary border-tertiary/20",
  processing: "bg-secondary/10 text-secondary border-secondary/20",
  pending: "bg-outline-variant/30 text-on-surface-variant border-outline-variant/40",
  failed: "bg-primary/10 text-primary border-primary/20",
};

// ── Shared micro-components ──────────────────────────────────────────────────

function Spinner({ size = "md" }: { size?: "sm" | "md" | "lg" }) {
  const dims = size === "sm" ? "h-4 w-4" : size === "lg" ? "h-10 w-10" : "h-6 w-6";
  return (
    <div className={`${dims} animate-spin rounded-full border-2 border-outline-variant border-t-primary`} />
  );
}

function PageLoader() {
  return (
    <div className="flex min-h-[240px] items-center justify-center">
      <Spinner size="lg" />
    </div>
  );
}

function PanelMessage({ children, variant = "default" }: { children: ReactNode; variant?: "default" | "error" }) {
  return (
    <div
      className={`rounded-lg border p-6 text-sm ${
        variant === "error"
          ? "border-primary/20 bg-primary/5 text-primary"
          : "border-outline-variant/40 bg-surface-low text-on-surface-variant"
      }`}
    >
      {children}
    </div>
  );
}

function StatusBadge({ status }: { status: string }) {
  const { t } = useTranslation();
  const style = STATUS_STYLES[status] ?? STATUS_STYLES.pending;
  const label = t(`meetings.status.${status}`, { defaultValue: status });
  return (
    <span className={`inline-flex items-center rounded-full border px-2 py-0.5 text-xs font-mono uppercase tracking-wide ${style}`}>
      {label}
    </span>
  );
}

function TopicChip({ topic }: { topic: string }) {
  const { t } = useTranslation();
  return (
    <span className="rounded-full bg-secondary-container px-2 py-0.5 text-xs text-secondary">
      {t(`topics.${topic}`, { defaultValue: topic })}
    </span>
  );
}

function StatCard({ label, value, detail }: { label: string; value: string; detail?: string }) {
  return (
    <div className="rounded-lg border border-outline-variant/40 bg-surface-low p-5">
      <div className="text-xs font-mono uppercase tracking-wide text-on-surface-variant">{label}</div>
      <div className="mt-2 text-3xl font-mono font-medium text-primary">{value}</div>
      {detail ? <div className="mt-1.5 text-xs text-on-surface-variant">{detail}</div> : null}
    </div>
  );
}

// ── Meetings List ────────────────────────────────────────────────────────────

function MeetingsPage() {
  const { t } = useTranslation();
  const { data, isLoading, error, refetch } = useQuery({
    queryKey: ["meetings"],
    queryFn: () => api<MeetingListItem[]>("/api/meetings/"),
  });

  if (isLoading) return <PageLoader />;

  if (error) {
    return (
      <div className="space-y-4">
        <PanelMessage variant="error">{t("common.error")}</PanelMessage>
        <button onClick={() => void refetch()} className="text-sm text-primary underline">
          {t("common.retry")}
        </button>
      </div>
    );
  }

  return (
    <section className="space-y-8">
      <div className="space-y-2">
        <h1 className="font-serif text-5xl text-primary">{t("meetings.title")}</h1>
        <p className="text-on-surface-variant">{t("meetings.search")}</p>
      </div>

      <div className="space-y-3">
        {data?.length ? (
          data.map((meeting) => (
            <Link
              key={meeting.id}
              to={`/meetings/${meeting.id}`}
              className="group block overflow-hidden rounded-lg border border-outline-variant/40 bg-surface-lowest shadow-[var(--shadow-card)] transition hover:border-primary/30 hover:shadow-[var(--shadow-elevated)]"
            >
              <div className="flex items-stretch">
                <div className="w-1 shrink-0 bg-primary opacity-70 transition group-hover:opacity-100" />
                <div className="flex flex-1 flex-col gap-3 p-5">
                  <div className="flex flex-wrap items-start justify-between gap-2">
                    <div className="text-xs font-mono text-on-surface-variant">
                      {meeting.date ?? "—"} · {meeting.municipality ?? "Amsterdam"}
                    </div>
                    <StatusBadge status={meeting.status} />
                  </div>
                  <h2 className="font-serif text-2xl leading-tight transition group-hover:text-primary">
                    {meeting.title}
                  </h2>
                  {meeting.agenda_item_count > 0 && (
                    <p className="text-sm text-on-surface-variant">
                      {meeting.agenda_item_count} {t("meetings.agendaItems")}
                    </p>
                  )}
                  {meeting.topics && meeting.topics.length > 0 && (
                    <div className="flex flex-wrap gap-1.5">
                      {meeting.topics.map((topic) => (
                        <TopicChip key={topic} topic={topic} />
                      ))}
                    </div>
                  )}
                </div>
              </div>
            </Link>
          ))
        ) : (
          <div className="rounded-lg border border-outline-variant/40 bg-surface-low p-10 text-center">
            <div className="text-4xl">📋</div>
            <p className="mt-3 font-medium text-on-surface-variant">{t("meetings.empty")}</p>
            <p className="mt-1 text-sm text-on-surface-variant/60">{t("meetings.emptyHint")}</p>
          </div>
        )}
      </div>
    </section>
  );
}

// ── Meeting Detail ────────────────────────────────────────────────────────────

type Tab = "summary" | "pdf" | "speakers" | "decisions" | "ask";

type ChatEntry = { question: string; response: ChatResponse };

function MeetingDetailPage() {
  const { id } = useParams();
  const meetingId = Number(id);
  const { t, i18n } = useTranslation();
  const [tab, setTab] = useState<Tab>("summary");
  const [question, setQuestion] = useState("");
  const [chatHistory, setChatHistory] = useState<ChatEntry[]>([]);
  const chatEndRef = useRef<HTMLDivElement>(null);

  const activeSpeakerId = useUiStore((s) => s.activeSpeakerId);
  const highlightedSegmentIds = useUiStore((s) => s.highlightedSegmentIds);
  const setActiveSpeaker = useUiStore((s) => s.setActiveSpeaker);
  const setHighlightedSegments = useUiStore((s) => s.setHighlightedSegments);
  const clearSelection = useUiStore((s) => s.clearSelection);

  const detailQuery = useQuery({
    queryKey: ["meeting", meetingId],
    queryFn: () => api<MeetingDetail>(`/api/meetings/${meetingId}`),
    enabled: Number.isFinite(meetingId),
  });
  const summaryQuery = useQuery({
    queryKey: ["summary", meetingId, i18n.language],
    queryFn: async () => {
      try {
        return await api<{ lang: string; summary: MeetingDetail["summary_nl"] }>(
          `/api/meetings/${meetingId}/summary/${i18n.language}`,
        );
      } catch (err) {
        if (err instanceof ApiError && err.status === 404) return null;
        throw err;
      }
    },
    enabled: Number.isFinite(meetingId),
    retry: false,
  });
  const segmentsQuery = useQuery({
    queryKey: ["segments", meetingId],
    queryFn: () => api<Segment[]>(`/api/meetings/${meetingId}/segments`),
    enabled: Number.isFinite(meetingId),
  });
  const speakersQuery = useQuery({
    queryKey: ["speakers", meetingId],
    queryFn: () => api<SpeakerSummary[]>(`/api/meetings/${meetingId}/speakers`),
    enabled: Number.isFinite(meetingId),
  });

  const chatMutation = useMutation({
    mutationFn: (q: string) =>
      api<ChatResponse>(`/api/meetings/${meetingId}/chat`, {
        method: "POST",
        body: JSON.stringify({ question: q, language: i18n.language }),
      }),
    onSuccess: (data, q) => {
      setChatHistory((prev) => [...prev, { question: q, response: data }]);
      setQuestion("");
    },
  });

  const selectedSegments = useMemo(() => {
    const all = segmentsQuery.data ?? [];
    if (highlightedSegmentIds.length) {
      return all.filter((s) => highlightedSegmentIds.includes(s.id));
    }
    if (!activeSpeakerId) return [];
    return all.filter(
      (s) => `${s.speaker}|${s.party ?? ""}|${s.role ?? ""}` === activeSpeakerId,
    );
  }, [segmentsQuery.data, highlightedSegmentIds, activeSpeakerId]);

  useEffect(() => {
    clearSelection();
    setChatHistory([]);
  }, [clearSelection, meetingId]);

  useEffect(() => {
    chatEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [chatHistory]);

  if (!Number.isFinite(meetingId)) {
    return <PanelMessage variant="error">{t("detail.invalidMeeting")}</PanelMessage>;
  }
  if (detailQuery.isLoading || summaryQuery.isLoading) return <PageLoader />;
  if (detailQuery.error || !detailQuery.data) {
    return <PanelMessage variant="error">{t("common.error")}</PanelMessage>;
  }

  const meeting = detailQuery.data;
  const summary = summaryQuery.data?.summary ?? meeting.summary_nl;

  const TAB_LIST: { key: Tab; label: string }[] = [
    { key: "summary", label: t("detail.summary") },
    { key: "pdf", label: t("detail.pdf") },
    { key: "speakers", label: t("detail.speakers") },
    { key: "decisions", label: t("detail.decisions") },
    { key: "ask", label: t("detail.ask") },
  ];

  const submitQuestion = () => {
    if (!question.trim() || chatMutation.isPending) return;
    void chatMutation.mutateAsync(question);
  };

  const handleAsk = (event: FormEvent) => {
    event.preventDefault();
    submitQuestion();
  };

  return (
    <section className="space-y-6">
      {/* Header */}
      <header className="space-y-3 border-b border-outline-variant/40 pb-6">
        <div className="flex flex-wrap items-center gap-2">
          <Link
            to="/meetings"
            className="text-xs font-mono text-on-surface-variant hover:text-primary"
          >
            ← {t("common.backToMeetings")}
          </Link>
          {meeting.municipality && (
            <>
              <span className="text-outline-variant/60">·</span>
              <span className="text-xs font-mono text-on-surface-variant">{meeting.municipality}</span>
            </>
          )}
          <StatusBadge status={meeting.status} />
        </div>
        <div className="text-xs font-mono text-on-surface-variant">
          {meeting.date}
          {meeting.start_time ? ` · ${meeting.start_time}` : ""}
          {meeting.end_time ? ` – ${meeting.end_time}` : ""}
        </div>
        <h1 className="font-serif text-4xl leading-tight md:text-5xl">{meeting.title}</h1>
        {meeting.topics && meeting.topics.length > 0 && (
          <div className="flex flex-wrap gap-1.5">
            {meeting.topics.map((topic) => (
              <TopicChip key={topic} topic={topic} />
            ))}
          </div>
        )}

        {/* Tab bar */}
        <div className="flex gap-1 overflow-x-auto pb-px pt-2">
          {TAB_LIST.map(({ key, label }) => (
            <button
              key={key}
              onClick={() => setTab(key)}
              className={`shrink-0 rounded-t border-b-2 px-4 py-2 text-sm font-medium transition ${
                tab === key
                  ? "border-primary text-primary"
                  : "border-transparent text-on-surface-variant hover:text-on-surface"
              }`}
            >
              {label}
            </button>
          ))}
        </div>
      </header>

      {/* ── Summary tab ──────────────────────────────────────────────── */}
      {tab === "summary" && (
        <div className="space-y-4">
          {summary?.agenda_items?.length ? (
            summary.agenda_items.map((item) => (
              <article
                key={`${item.number}-${item.title}`}
                className="overflow-hidden rounded-lg border border-outline-variant/40 bg-surface-low shadow-[var(--shadow-card)]"
              >
                <div className="border-b border-outline-variant/30 bg-surface-container px-6 py-3">
                  <span className="text-xs font-mono uppercase text-primary">
                    {t("detail.agenda")} {item.number}
                  </span>
                  <h2 className="mt-1 font-serif text-2xl leading-snug">{item.title}</h2>
                </div>
                <div className="space-y-4 px-6 py-4">
                  {item.topic_summary && (
                    <p className="text-base leading-relaxed">{item.topic_summary}</p>
                  )}
                  {item.decision_detail && item.decision_detail !== item.topic_summary && (
                    <p className="text-sm text-on-surface-variant">{item.decision_detail}</p>
                  )}
                  {item.resident_impact && (
                    <div className="flex gap-3 rounded-lg bg-primary/5 p-4 text-sm">
                      <span className="mt-0.5 shrink-0 text-primary">●</span>
                      <div>
                        <span className="font-semibold text-primary">{t("detail.residentImpact")}: </span>
                        {item.resident_impact}
                      </div>
                    </div>
                  )}
                  {item.votes && (
                    <div className="flex flex-wrap gap-2 text-xs font-mono">
                      {item.votes.for != null && (
                        <span className="rounded-full bg-tertiary/10 px-3 py-1 text-tertiary">
                          {t("detail.votes.for")} {item.votes.for}
                        </span>
                      )}
                      {item.votes.against != null && (
                        <span className="rounded-full bg-primary/10 px-3 py-1 text-primary">
                          {t("detail.votes.against")} {item.votes.against}
                        </span>
                      )}
                      {item.votes.abstentions != null && item.votes.abstentions > 0 && (
                        <span className="rounded-full bg-surface-high px-3 py-1 text-on-surface-variant">
                          {t("detail.votes.abstentions")} {item.votes.abstentions}
                        </span>
                      )}
                      {item.votes.unanimous && (
                        <span className="rounded-full bg-tertiary/10 px-3 py-1 text-tertiary">✓ unanim</span>
                      )}
                    </div>
                  )}
                </div>
              </article>
            ))
          ) : (
            <PanelMessage>{t("detail.noSummary")}</PanelMessage>
          )}
        </div>
      )}

      {/* ── PDF tab ───────────────────────────────────────────────────── */}
      {tab === "pdf" && (
        <Suspense fallback={<PageLoader />}>
          <PdfPanel meetingId={meetingId} segments={selectedSegments} />
        </Suspense>
      )}

      {/* ── Speakers tab ──────────────────────────────────────────────── */}
      {tab === "speakers" && (
        <div className="grid gap-4 lg:grid-cols-[260px_minmax(0,1fr)]">
          {/* Speaker list */}
          <aside className="space-y-1.5 rounded-lg border border-outline-variant/40 bg-surface-low p-3">
            {speakersQuery.isLoading && (
              <div className="flex justify-center py-4">
                <Spinner />
              </div>
            )}
            {(speakersQuery.data ?? []).map((speaker) => {
              const isActive = activeSpeakerId === speaker.id;
              const initials = speaker.speaker
                .split(" ")
                .map((w) => w[0])
                .join("")
                .slice(0, 2)
                .toUpperCase();
              return (
                <button
                  key={speaker.id}
                  onClick={() => setActiveSpeaker(speaker.id)}
                  className={`w-full rounded-lg border px-3 py-3 text-left transition ${
                    isActive
                      ? "border-primary/30 bg-primary/5 text-primary"
                      : "border-transparent bg-surface-lowest hover:border-outline-variant/40"
                  }`}
                >
                  <div className="flex items-center gap-3">
                    <div
                      className={`flex h-8 w-8 shrink-0 items-center justify-center rounded-full text-xs font-bold ${
                        isActive ? "bg-primary text-white" : "bg-secondary-container text-secondary"
                      }`}
                    >
                      {initials}
                    </div>
                    <div className="min-w-0">
                      <div className="truncate font-medium text-sm">{speaker.speaker}</div>
                      <div className="truncate text-xs text-on-surface-variant">
                        {speaker.party ?? speaker.role ?? ""}
                      </div>
                    </div>
                    <div className="ml-auto shrink-0 text-xs font-mono text-on-surface-variant">
                      {speaker.segment_count}
                    </div>
                  </div>
                </button>
              );
            })}
          </aside>

          {/* Segments */}
          <div className="space-y-3">
            {activeSpeakerId && selectedSegments.length > 0 ? (
              <>
                <div className="flex items-center justify-between">
                  <span className="text-sm text-on-surface-variant">
                    {selectedSegments.length} {t("detail.segmentCount")}
                  </span>
                  <button
                    onClick={() => {
                      setTab("pdf");
                    }}
                    className="text-xs text-primary underline"
                  >
                    {t("detail.viewInPdf")}
                  </button>
                </div>
                {selectedSegments.map((segment) => (
                  <div
                    key={segment.id}
                    className="rounded-lg border border-outline-variant/40 bg-surface-lowest p-4"
                  >
                    <div className="mb-2 text-xs font-mono uppercase text-on-surface-variant">
                      {t("detail.page")} {segment.page ?? "?"} · {segment.intent}
                    </div>
                    <p className="text-sm leading-relaxed">{segment.text}</p>
                  </div>
                ))}
              </>
            ) : (
              <div className="flex min-h-[200px] items-center justify-center rounded-lg border border-outline-variant/40 bg-surface-low">
                <p className="text-sm text-on-surface-variant">{t("detail.selectSpeaker")}</p>
              </div>
            )}
          </div>
        </div>
      )}

      {/* ── Decisions tab ─────────────────────────────────────────────── */}
      {tab === "decisions" && (
        summary?.agenda_items?.length ? (
          <div className="grid gap-4 md:grid-cols-2">
            {summary.agenda_items.map((item) => (
              <div
                key={`${item.number}-${item.title}`}
                className="rounded-lg border border-outline-variant/40 bg-surface-low p-5 shadow-[var(--shadow-card)]"
              >
                <div className="mb-1 text-xs font-mono uppercase text-on-surface-variant">
                  {t("detail.agenda")} {item.number}
                </div>
                <h3 className="font-serif text-xl leading-snug">{item.title}</h3>
                {item.decision && (
                  <div className="mt-2 text-sm font-semibold uppercase tracking-wide text-primary">
                    {item.decision}
                  </div>
                )}
                {item.decision_detail && (
                  <p className="mt-2 text-sm text-on-surface-variant">{item.decision_detail}</p>
                )}
                {item.votes && (
                  <div className="mt-3 flex flex-wrap gap-2 text-xs font-mono">
                    {item.votes.for != null && (
                      <span className="rounded-full bg-tertiary/10 px-2.5 py-1 text-tertiary">
                        {t("detail.votes.for")} {item.votes.for}
                      </span>
                    )}
                    {item.votes.against != null && (
                      <span className="rounded-full bg-primary/10 px-2.5 py-1 text-primary">
                        {t("detail.votes.against")} {item.votes.against}
                      </span>
                    )}
                    {item.votes.abstentions != null && item.votes.abstentions > 0 && (
                      <span className="rounded-full bg-surface-high px-2.5 py-1 text-on-surface-variant">
                        {t("detail.votes.abstentions")} {item.votes.abstentions}
                      </span>
                    )}
                  </div>
                )}
              </div>
            ))}
          </div>
        ) : (
          <PanelMessage>{t("detail.noDecisions")}</PanelMessage>
        )
      )}

      {/* ── Ask AI tab ────────────────────────────────────────────────── */}
      {tab === "ask" && (
        <div className="space-y-4">
          {/* Conversation history */}
          {chatHistory.length > 0 && (
            <div className="space-y-4">
              {chatHistory.map((entry, idx) => (
                <div key={idx} className="space-y-2">
                  {/* Question bubble */}
                  <div className="flex justify-end">
                    <div className="max-w-[80%] rounded-2xl rounded-tr-sm bg-primary px-4 py-3 text-sm text-white">
                      {entry.question}
                    </div>
                  </div>
                  {/* Answer bubble */}
                  <div className="flex justify-start">
                    <div className="max-w-[80%] rounded-2xl rounded-tl-sm bg-surface-low px-4 py-3 text-sm">
                      <p className="leading-relaxed">{entry.response.answer}</p>
                      {entry.response.citations.length > 0 && (
                        <div className="mt-3 flex flex-wrap gap-1.5">
                          {entry.response.citations.map((citation) => (
                            <button
                              key={citation.segment_id}
                              onClick={() => {
                                setHighlightedSegments([citation.segment_id]);
                                setTab("pdf");
                              }}
                              className="rounded-full border border-secondary/30 bg-secondary-container px-2.5 py-1 text-xs font-mono text-secondary transition hover:bg-secondary hover:text-white"
                              title={citation.text_excerpt}
                            >
                              #{citation.segment_id}
                              {citation.speaker ? ` · ${citation.speaker}` : ""}
                            </button>
                          ))}
                        </div>
                      )}
                    </div>
                  </div>
                </div>
              ))}
              <div ref={chatEndRef} />
            </div>
          )}

          {/* Input form */}
          <div className="rounded-lg border border-outline-variant/40 bg-surface-low p-4">
            <form onSubmit={handleAsk} className="flex gap-3">
              <textarea
                value={question}
                onChange={(e) => setQuestion(e.target.value)}
                onKeyDown={(e) => {
                  if (e.key === "Enter" && !e.shiftKey) {
                    e.preventDefault();
                    void handleAsk(e as unknown as FormEvent);
                  }
                }}
                placeholder={t("detail.askPlaceholder")}
                rows={2}
                className="flex-1 resize-none rounded-lg border border-outline-variant bg-surface-lowest px-3 py-2 text-sm focus:border-primary focus:outline-none"
              />
              <div className="flex flex-col gap-2">
                <button
                  type="submit"
                  disabled={!question.trim() || chatMutation.isPending}
                  className="flex items-center gap-2 rounded-lg bg-primary px-4 py-2 text-sm text-white disabled:cursor-not-allowed disabled:opacity-50"
                >
                  {chatMutation.isPending ? <Spinner size="sm" /> : null}
                  {chatMutation.isPending ? t("detail.sending") : t("detail.send")}
                </button>
                {chatHistory.length > 0 && (
                  <button
                    type="button"
                    onClick={() => setChatHistory([])}
                    className="rounded-lg border border-outline-variant px-3 py-2 text-xs text-on-surface-variant hover:bg-surface-high"
                  >
                    {t("detail.chatClear")}
                  </button>
                )}
              </div>
            </form>
            {chatMutation.error && (
              <p className="mt-2 text-xs text-primary">{t("detail.chatError")}</p>
            )}
          </div>
        </div>
      )}
    </section>
  );
}

// ── Subscriptions ────────────────────────────────────────────────────────────

function SubscriptionsPage() {
  const { t, i18n } = useTranslation();
  const [email, setEmail] = useState("");
  const [selectedTopics, setSelectedTopics] = useState<Topic[]>([]);

  const toggleTopic = (topic: Topic) => {
    setSelectedTopics((prev) =>
      prev.includes(topic) ? prev.filter((t) => t !== topic) : [...prev, topic],
    );
  };

  const mutation = useMutation({
    mutationFn: () =>
      api("/api/subscribers/", {
        method: "POST",
        body: JSON.stringify({
          email,
          language: i18n.language,
          topics: selectedTopics,
          frequency: "immediate",
        }),
      }),
    onSuccess: () => {
      setEmail("");
      setSelectedTopics([]);
    },
  });

  return (
    <section className="grid gap-8 lg:grid-cols-[1.2fr_0.8fr]">
      <div className="space-y-6">
        <div>
          <h1 className="font-serif text-5xl text-primary">{t("subscriptions.title")}</h1>
          <p className="mt-2 text-on-surface-variant">{t("subscriptions.lead")}</p>
        </div>

        <div className="space-y-1">
          <label className="text-xs font-mono uppercase text-on-surface-variant">
            {t("subscriptions.email")}
          </label>
          <input
            type="email"
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            placeholder="you@example.com"
            className="w-full rounded-lg border border-outline-variant bg-surface-lowest px-4 py-3 text-base focus:border-primary focus:outline-none"
          />
        </div>

        <div className="space-y-2">
          <label className="text-xs font-mono uppercase text-on-surface-variant">
            {t("subscriptions.topicsLabel")}
          </label>
          <p className="text-xs text-on-surface-variant/70">{t("subscriptions.topicsHint")}</p>
          <div className="flex flex-wrap gap-2">
            {ALL_TOPICS.map((topic) => (
              <button
                key={topic}
                onClick={() => toggleTopic(topic)}
                className={`rounded-full border px-3 py-1.5 text-sm transition ${
                  selectedTopics.includes(topic)
                    ? "border-primary bg-primary text-white"
                    : "border-outline-variant bg-surface-lowest text-on-surface-variant hover:border-primary/50 hover:text-on-surface"
                }`}
              >
                {t(`topics.${topic}`)}
              </button>
            ))}
          </div>
        </div>

        <button
          onClick={() => mutation.mutate()}
          disabled={!email.trim() || mutation.isPending}
          className="flex items-center gap-2 rounded-lg bg-primary px-6 py-3 text-white disabled:cursor-not-allowed disabled:opacity-50"
        >
          {mutation.isPending && <Spinner size="sm" />}
          {mutation.isPending ? t("subscriptions.saving") : t("subscriptions.save")}
        </button>

        {mutation.isSuccess && (
          <div className="flex items-center gap-2 rounded-lg border border-tertiary/30 bg-tertiary/5 px-4 py-3 text-sm text-tertiary">
            <span>✓</span> {t("subscriptions.saved")}
          </div>
        )}
        {mutation.error && <PanelMessage variant="error">{t("subscriptions.error")}</PanelMessage>}
      </div>

      {/* Preview card */}
      <div className="rounded-xl border border-outline-variant/40 bg-surface-low p-6">
        <div className="text-xs font-mono uppercase text-on-surface-variant">Preview</div>
        <div className="mt-4 rounded-xl border border-outline-variant/30 bg-surface-lowest p-5">
          <div className="text-xs font-mono text-on-surface-variant">congressmAIn · Amsterdam</div>
          <h2 className="mt-2 font-serif text-2xl">Raadsvergadering — congressmAIn</h2>
          <p className="mt-3 text-sm text-on-surface-variant leading-relaxed">
            {t("subscriptions.preview.body")}
          </p>
          <div className="mt-4 flex gap-2">
            <div className="h-1.5 flex-1 rounded-full bg-primary/20" />
            <div className="h-1.5 flex-1 rounded-full bg-primary/10" />
            <div className="h-1.5 w-8 rounded-full bg-primary/10" />
          </div>
        </div>
      </div>
    </section>
  );
}

// ── About ────────────────────────────────────────────────────────────────────

const ABOUT_STEPS = [
  { key: "step1", icon: "📄" },
  { key: "step2", icon: "⚙️" },
  { key: "step3", icon: "🤖" },
  { key: "step4", icon: "🏘️" },
] as const;

function AboutPage() {
  const { t } = useTranslation();
  return (
    <section className="space-y-12">
      <div className="max-w-3xl space-y-4">
        <h1 className="font-serif text-6xl text-primary">{t("about.title")}</h1>
        <p className="text-xl leading-relaxed text-on-surface-variant">{t("about.lead")}</p>
      </div>

      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
        {ABOUT_STEPS.map(({ key, icon }, index) => (
          <div
            key={key}
            className="group rounded-xl border border-outline-variant/40 bg-surface-low p-6 transition hover:border-primary/30 hover:shadow-[var(--shadow-elevated)]"
          >
            <div className="flex items-center gap-3">
              <span className="text-2xl">{icon}</span>
              <span className="text-xs font-mono text-on-surface-variant">0{index + 1}</span>
            </div>
            <h2 className="mt-4 font-serif text-2xl">{t(`about.${key}.title`)}</h2>
            <p className="mt-2 text-sm leading-relaxed text-on-surface-variant">
              {t(`about.${key}.desc`)}
            </p>
          </div>
        ))}
      </div>

      {/* Tech stack note */}
      <div className="rounded-xl border border-outline-variant/40 bg-surface-low p-6">
        <div className="text-xs font-mono uppercase text-on-surface-variant">Stack</div>
        <div className="mt-3 flex flex-wrap gap-2">
          {["FastAPI", "GPT-4o", "LibreTranslate", "React", "TailwindCSS", "SQLite / Postgres"].map(
            (tech) => (
              <span
                key={tech}
                className="rounded-full border border-outline-variant/40 bg-surface-lowest px-3 py-1 text-xs font-mono"
              >
                {tech}
              </span>
            ),
          )}
        </div>
      </div>
    </section>
  );
}

// ── Admin ─────────────────────────────────────────────────────────────────────

function AdminPage() {
  const { t } = useTranslation();
  const qc = useQueryClient();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [token, setToken] = useState<string | null>(localStorage.getItem("congressmain-admin-token"));
  const [authError, setAuthError] = useState<string | null>(null);

  const login = useMutation({
    mutationFn: async () => {
      const response = await fetch(`${API_BASE}/api/admin/token`, {
        method: "POST",
        headers: { "Content-Type": "application/x-www-form-urlencoded" },
        body: new URLSearchParams({ username: email, password }),
      });
      const payload = (await response.json().catch(() => ({}))) as {
        access_token?: string;
        detail?: string;
      };
      if (!response.ok || !payload.access_token) {
        throw new Error(payload.detail ?? "Authentication failed");
      }
      return payload;
    },
    onMutate: () => setAuthError(null),
    onSuccess: (data: { access_token?: string }) => {
      if (data.access_token) {
        localStorage.setItem("congressmain-admin-token", data.access_token);
        setToken(data.access_token);
        setPassword("");
      }
    },
    onError: (err: Error) => setAuthError(err.message),
  });

  const authHeaders = token ? { Authorization: `Bearer ${token}` } : undefined;

  const metricsQuery = useQuery({
    queryKey: ["admin-metrics", token],
    enabled: Boolean(token),
    queryFn: () => api<AdminMetrics>("/api/admin/metrics", { headers: authHeaders }),
    retry: false,
  });
  const meetingsQuery = useQuery({
    queryKey: ["admin-meetings", token],
    enabled: Boolean(token),
    queryFn: () => api<AdminMeeting[]>("/api/admin/meetings", { headers: authHeaders }),
    retry: false,
  });
  const subscribersQuery = useQuery({
    queryKey: ["admin-subscribers", token],
    enabled: Boolean(token),
    queryFn: () => api<AdminSubscriber[]>("/api/admin/subscribers", { headers: authHeaders }),
    retry: false,
  });

  const reprocessMutation = useMutation({
    mutationFn: (meetingId: number) =>
      api(`/api/meetings/${meetingId}/reprocess`, {
        method: "POST",
        headers: authHeaders,
      }),
    onSuccess: () => void qc.invalidateQueries({ queryKey: ["admin-meetings"] }),
  });

  useEffect(() => {
    const err = metricsQuery.error ?? meetingsQuery.error ?? subscribersQuery.error;
    if (!err) return;
    if (/401|403|credentials/i.test((err as Error).message)) {
      localStorage.removeItem("congressmain-admin-token");
      setToken(null);
      setAuthError(t("admin.sessionExpired"));
    }
  }, [metricsQuery.error, meetingsQuery.error, subscribersQuery.error, t]);

  const handleRefresh = () => {
    void qc.invalidateQueries({ queryKey: ["admin-metrics"] });
    void qc.invalidateQueries({ queryKey: ["admin-meetings"] });
    void qc.invalidateQueries({ queryKey: ["admin-subscribers"] });
  };

  if (!token) {
    return (
      <section className="max-w-md space-y-4">
        <h1 className="font-serif text-5xl">{t("admin.title")}</h1>
        <input
          value={email}
          onChange={(e) => setEmail(e.target.value)}
          placeholder={t("admin.email")}
          type="email"
          className="w-full rounded-lg border border-outline-variant bg-surface-lowest px-4 py-3 focus:border-primary focus:outline-none"
        />
        <input
          value={password}
          onChange={(e) => setPassword(e.target.value)}
          placeholder={t("admin.password")}
          type="password"
          onKeyDown={(e) => e.key === "Enter" && login.mutate()}
          className="w-full rounded-lg border border-outline-variant bg-surface-lowest px-4 py-3 focus:border-primary focus:outline-none"
        />
        <button
          onClick={() => login.mutate()}
          disabled={!email.trim() || !password.trim() || login.isPending}
          className="flex w-full items-center justify-center gap-2 rounded-lg bg-primary py-3 text-white disabled:opacity-50"
        >
          {login.isPending && <Spinner size="sm" />}
          {login.isPending ? t("admin.loggingIn") : t("admin.login")}
        </button>
        {authError && <PanelMessage variant="error">{authError}</PanelMessage>}
      </section>
    );
  }

  return (
    <section className="space-y-6">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <h1 className="font-serif text-5xl">{t("admin.title")}</h1>
        <div className="flex gap-2">
          <button
            onClick={handleRefresh}
            className="rounded-lg border border-outline-variant bg-surface-lowest px-4 py-2 text-sm hover:bg-surface-low"
          >
            {t("admin.refresh")}
          </button>
          <button
            onClick={() => {
              localStorage.removeItem("congressmain-admin-token");
              setToken(null);
            }}
            className="rounded-lg border border-outline-variant bg-surface-lowest px-4 py-2 text-sm hover:bg-surface-low"
          >
            {t("admin.logout")}
          </button>
        </div>
      </div>

      {/* Metrics */}
      {metricsQuery.isLoading ? (
        <PageLoader />
      ) : metricsQuery.data ? (
        <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-4">
          <StatCard label={t("admin.metrics.processed")} value={String(metricsQuery.data.meetings_processed)} />
          <StatCard label={t("admin.metrics.processing")} value={String(metricsQuery.data.meetings_processing)} />
          <StatCard label={t("admin.metrics.failed")} value={String(metricsQuery.data.meetings_failed)} />
          <StatCard
            label={t("admin.metrics.processingTime")}
            value={`${metricsQuery.data.avg_processing_time_seconds}s`}
          />
          <StatCard
            label={t("admin.metrics.cacheHit")}
            value={`${metricsQuery.data.translation_cache_hit_rate}%`}
          />
          <StatCard
            label={t("admin.metrics.deliverySuccess")}
            value={`${metricsQuery.data.digest_delivery_success}%`}
          />
          <StatCard
            label={t("admin.metrics.subscribers")}
            value={String(metricsQuery.data.active_subscribers)}
          />
          <StatCard
            label={t("admin.metrics.topTopic")}
            value={metricsQuery.data.top_topics[0]?.topic ?? "—"}
            detail={
              metricsQuery.data.top_topics[0]
                ? `${metricsQuery.data.top_topics[0].count} ${t("admin.metrics.meetingsUnit")}`
                : t("admin.metrics.noTopics")
            }
          />
        </div>
      ) : null}

      {/* Tables */}
      <div className="grid gap-6 xl:grid-cols-[1.3fr_0.7fr]">
        {/* Meetings table */}
        <div className="space-y-2">
          <div className="flex items-center justify-between">
            <h2 className="font-serif text-2xl">{t("admin.meetings")}</h2>
            <span className="text-xs font-mono text-on-surface-variant">
              {meetingsQuery.data?.length ?? 0}
            </span>
          </div>
          <div className="overflow-hidden rounded-xl border border-outline-variant/40 bg-surface-low">
            {meetingsQuery.isLoading ? (
              <div className="flex justify-center p-6">
                <Spinner />
              </div>
            ) : meetingsQuery.data?.length ? (
              <div className="divide-y divide-outline-variant/20">
                {meetingsQuery.data.map((m) => (
                  <div
                    key={m.id}
                    className="flex flex-wrap items-center gap-3 px-4 py-3"
                  >
                    <div className="min-w-0 flex-1">
                      <div className="truncate font-medium text-sm">{m.title}</div>
                      <div className="text-xs text-on-surface-variant">{m.date ?? "—"}</div>
                      {m.error_message && (
                        <div className="mt-1 text-xs text-primary truncate">{m.error_message}</div>
                      )}
                    </div>
                    <StatusBadge status={m.status} />
                    <div className="flex gap-2">
                      <Link
                        to={`/meetings/${m.id}`}
                        className="rounded border border-outline-variant px-3 py-1 text-xs hover:bg-surface-high"
                      >
                        {t("admin.openMeeting")}
                      </Link>
                      {m.status === "failed" && (
                        <button
                          onClick={() => reprocessMutation.mutate(m.id)}
                          disabled={reprocessMutation.isPending}
                          className="rounded border border-primary/30 bg-primary/5 px-3 py-1 text-xs text-primary hover:bg-primary/10 disabled:opacity-50"
                        >
                          {t("admin.reprocess")}
                        </button>
                      )}
                    </div>
                  </div>
                ))}
              </div>
            ) : (
              <div className="p-6 text-sm text-on-surface-variant">{t("admin.noMeetings")}</div>
            )}
          </div>
        </div>

        {/* Subscribers table */}
        <div className="space-y-2">
          <div className="flex items-center justify-between">
            <h2 className="font-serif text-2xl">{t("admin.subscribers")}</h2>
            <span className="text-xs font-mono text-on-surface-variant">
              {subscribersQuery.data?.length ?? 0}
            </span>
          </div>
          <div className="overflow-hidden rounded-xl border border-outline-variant/40 bg-surface-low">
            {subscribersQuery.isLoading ? (
              <div className="flex justify-center p-6">
                <Spinner />
              </div>
            ) : subscribersQuery.data?.length ? (
              <div className="divide-y divide-outline-variant/20">
                {subscribersQuery.data.map((s: AdminSubscriber) => (
                  <div key={s.id} className="px-4 py-3">
                    <div className="flex items-center justify-between gap-2">
                      <span className="truncate text-sm font-medium">{s.email}</span>
                      <span
                        className={`shrink-0 rounded-full px-2 py-0.5 text-xs ${
                          s.is_active
                            ? "bg-tertiary/10 text-tertiary"
                            : "bg-surface-high text-on-surface-variant"
                        }`}
                      >
                        {s.is_active ? t("admin.active") : t("admin.inactive")}
                      </span>
                    </div>
                    <div className="mt-0.5 text-xs font-mono text-on-surface-variant">
                      {s.language.toUpperCase()} · {s.created_at.split("T")[0]}
                    </div>
                  </div>
                ))}
              </div>
            ) : (
              <div className="p-6 text-sm text-on-surface-variant">{t("admin.noSubscribers")}</div>
            )}
          </div>
        </div>
      </div>
    </section>
  );
}

// ── App shell ─────────────────────────────────────────────────────────────────

function AppShell() {
  return (
    <BrowserRouter>
      <QueryClientProvider client={queryClient}>
        <Layout>
          <Routes>
            <Route path="/" element={<Navigate to="/meetings" replace />} />
            <Route path="/meetings" element={<MeetingsPage />} />
            <Route path="/meetings/:id" element={<MeetingDetailPage />} />
            <Route path="/subscriptions" element={<SubscriptionsPage />} />
            <Route path="/about" element={<AboutPage />} />
            <Route path="/admin" element={<AdminPage />} />
          </Routes>
        </Layout>
      </QueryClientProvider>
    </BrowserRouter>
  );
}

export default AppShell;
