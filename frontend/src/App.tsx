import { FormEvent, useMemo, useState } from "react";
import { QueryClient, QueryClientProvider, useMutation, useQuery } from "@tanstack/react-query";
import { useTranslation } from "react-i18next";
import { BrowserRouter, Navigate, Route, Routes, useParams } from "react-router-dom";

import "./i18n";
import "./styles/index.css";
import { api } from "./lib/api";
import type { ChatResponse, MeetingDetail, MeetingListItem, Segment, SpeakerSummary } from "./lib/types";
import { Layout } from "./components/Layout";
import { PdfPanel } from "./components/PdfPanel";
import { useUiStore } from "./store/useUiStore";

const queryClient = new QueryClient();

function MeetingsPage() {
  const { t } = useTranslation();
  const { data, isLoading, error } = useQuery({
    queryKey: ["meetings"],
    queryFn: () => api<MeetingListItem[]>("/api/meetings/"),
  });

  if (isLoading) return <p>{t("common.loading")}</p>;
  if (error) return <p>{t("common.error")}</p>;

  return (
    <section className="space-y-6">
      <div>
        <h1 className="font-serif text-5xl text-primary">{t("meetings.title")}</h1>
        <p className="mt-2 max-w-2xl text-on-surface-variant">{t("meetings.search")}</p>
      </div>
      <div className="space-y-4">
        {data?.length ? (
          data.map((meeting) => (
            <a
              key={meeting.id}
              href={`/meetings/${meeting.id}`}
              className="block border-l-4 border-primary bg-surface-lowest p-6 transition hover:bg-surface-low"
            >
              <div className="text-xs font-mono uppercase text-on-surface-variant">{meeting.date}</div>
              <h2 className="mt-2 font-serif text-3xl">{meeting.title}</h2>
              <p className="mt-3 text-sm text-on-surface-variant">{meeting.municipality}</p>
              <div className="mt-3 flex flex-wrap gap-2">
                {meeting.topics?.map((topic) => (
                  <span key={topic} className="rounded-sm bg-secondary-container px-2 py-1 text-xs text-secondary">
                    {topic}
                  </span>
                ))}
              </div>
            </a>
          ))
        ) : (
          <div className="rounded-lg border border-outline-variant/50 bg-surface-low p-8 text-on-surface-variant">
            {t("meetings.empty")}
          </div>
        )}
      </div>
    </section>
  );
}

function MeetingDetailPage() {
  const { id } = useParams();
  const meetingId = Number(id);
  const { t, i18n } = useTranslation();
  const [tab, setTab] = useState<"summary" | "pdf" | "speakers" | "decisions" | "ask">("summary");
  const [question, setQuestion] = useState("");
  const activeSpeakerId = useUiStore((state) => state.activeSpeakerId);
  const highlightedSegmentIds = useUiStore((state) => state.highlightedSegmentIds);
  const setActiveSpeaker = useUiStore((state) => state.setActiveSpeaker);
  const setHighlightedSegments = useUiStore((state) => state.setHighlightedSegments);

  const detailQuery = useQuery({
    queryKey: ["meeting", meetingId],
    queryFn: () => api<MeetingDetail>(`/api/meetings/${meetingId}`),
  });
  const summaryQuery = useQuery({
    queryKey: ["summary", meetingId, i18n.language],
    queryFn: () => api<{ lang: string; summary: MeetingDetail["summary_nl"] }>(`/api/meetings/${meetingId}/summary/${i18n.language}`),
  });
  const segmentsQuery = useQuery({
    queryKey: ["segments", meetingId],
    queryFn: () => api<Segment[]>(`/api/meetings/${meetingId}/segments`),
  });
  const speakersQuery = useQuery({
    queryKey: ["speakers", meetingId],
    queryFn: () => api<SpeakerSummary[]>(`/api/meetings/${meetingId}/speakers`),
  });
  const chatMutation = useMutation({
    mutationFn: () =>
      api<ChatResponse>(`/api/meetings/${meetingId}/chat`, {
        method: "POST",
        body: JSON.stringify({ question, language: i18n.language }),
      }),
  });

  const selectedSegments = useMemo(() => {
    const all = segmentsQuery.data ?? [];
    if (highlightedSegmentIds.length) {
      return all.filter((segment) => highlightedSegmentIds.includes(segment.id));
    }
    if (!activeSpeakerId) {
      return [];
    }
    return all.filter((segment) => `${segment.speaker}|${segment.party ?? ""}|${segment.role ?? ""}` === activeSpeakerId);
  }, [segmentsQuery.data, highlightedSegmentIds, activeSpeakerId]);

  if (detailQuery.isLoading || summaryQuery.isLoading) return <p>{t("common.loading")}</p>;
  if (detailQuery.error || !detailQuery.data) return <p>{t("common.error")}</p>;

  const summary = summaryQuery.data?.summary ?? detailQuery.data.summary_nl;

  const handleAsk = async (event: FormEvent) => {
    event.preventDefault();
    await chatMutation.mutateAsync();
  };

  return (
    <section className="space-y-8">
      <header className="space-y-3 border-b border-outline-variant/40 pb-6">
        <div className="text-xs font-mono uppercase text-on-surface-variant">
          {detailQuery.data.date} · {detailQuery.data.start_time} - {detailQuery.data.end_time}
        </div>
        <h1 className="font-serif text-5xl">{detailQuery.data.title}</h1>
        <div className="flex flex-wrap gap-2">
          {["pdf", "summary", "speakers", "decisions", "ask"].map((item) => (
            <button
              key={item}
              onClick={() => setTab(item as typeof tab)}
              className={`rounded-sm border px-4 py-2 text-sm ${
                tab === item ? "border-primary bg-primary text-white" : "border-outline-variant bg-surface-lowest"
              }`}
            >
              {t(`detail.${item}`)}
            </button>
          ))}
        </div>
      </header>

      {tab === "summary" && (
        <div className="space-y-6">
          {summary?.agenda_items?.length ? (
            summary.agenda_items.map((item) => (
              <article key={`${item.number}-${item.title}`} className="rounded-lg bg-surface-low p-6">
                <div className="text-xs font-mono uppercase text-primary">Agenda {item.number}</div>
                <h2 className="mt-2 font-serif text-3xl">{item.title}</h2>
                <p className="mt-3 text-lg">{item.topic_summary}</p>
                <p className="mt-3 text-on-surface-variant">{item.decision_detail}</p>
                {item.resident_impact && (
                  <p className="mt-4 border-l-4 border-primary pl-4"><strong>Voor bewoners:</strong> {item.resident_impact}</p>
                )}
              </article>
            ))
          ) : (
            <p>{t("detail.noSummary")}</p>
          )}
        </div>
      )}

      {tab === "pdf" && <PdfPanel meetingId={meetingId} segments={selectedSegments} />}

      {tab === "speakers" && (
        <div className="grid gap-6 lg:grid-cols-[280px_minmax(0,1fr)]">
          <aside className="space-y-2 rounded-lg bg-surface-low p-4">
            {(speakersQuery.data ?? []).map((speaker) => (
              <button
                key={speaker.id}
                onClick={() => {
                  setActiveSpeaker(speaker.id);
                  setTab("pdf");
                }}
                className={`w-full rounded-sm border px-3 py-3 text-left ${
                  activeSpeakerId === speaker.id ? "border-primary bg-secondary-container" : "border-outline-variant bg-surface-lowest"
                }`}
              >
                <div className="font-medium">{speaker.speaker}</div>
                <div className="text-xs text-on-surface-variant">{speaker.party ?? speaker.role ?? ""}</div>
              </button>
            ))}
          </aside>
          <div className="space-y-3">
            {selectedSegments.length ? (
              selectedSegments.map((segment) => (
                <div key={segment.id} className="rounded-lg border border-outline-variant/40 bg-surface-lowest p-4">
                  <div className="text-xs font-mono uppercase text-primary">pagina {segment.page} · {segment.intent}</div>
                  <p className="mt-2">{segment.text}</p>
                </div>
              ))
            ) : (
              <p>{t("detail.noSegments")}</p>
            )}
          </div>
        </div>
      )}

      {tab === "decisions" && (
        <div className="grid gap-4 md:grid-cols-2">
          {summary?.agenda_items?.map((item) => (
            <div key={`${item.number}-${item.title}`} className="rounded-lg border border-outline-variant/40 bg-surface-low p-5">
              <h3 className="font-serif text-2xl">{item.title}</h3>
              <div className="mt-2 text-sm uppercase tracking-wide text-primary">{item.decision}</div>
              <p className="mt-3 text-on-surface-variant">{item.decision_detail}</p>
              {item.votes && (
                <div className="mt-4 text-sm">
                  Voor: {item.votes.for ?? "-"} · Tegen: {item.votes.against ?? "-"} · Onthoudingen: {item.votes.abstentions ?? "-"}
                </div>
              )}
            </div>
          ))}
        </div>
      )}

      {tab === "ask" && (
        <div className="space-y-4 rounded-lg bg-surface-low p-6">
          <form onSubmit={handleAsk} className="space-y-4">
            <textarea
              value={question}
              onChange={(event) => setQuestion(event.target.value)}
              placeholder={t("detail.askPlaceholder")}
              className="min-h-32 w-full rounded-lg border border-outline-variant bg-surface-lowest p-4"
            />
            <button className="rounded-sm bg-primary px-4 py-2 text-white">{t("detail.send")}</button>
          </form>
          {chatMutation.data && (
            <div className="space-y-4">
              <div className="rounded-lg bg-surface-lowest p-4">{chatMutation.data.answer}</div>
              <div className="flex flex-wrap gap-2">
                {chatMutation.data.citations.map((citation) => (
                  <button
                    key={citation.segment_id}
                    onClick={() => {
                      setHighlightedSegments([citation.segment_id]);
                      setTab("pdf");
                    }}
                    className="rounded-full bg-secondary-container px-3 py-2 text-xs font-mono text-secondary"
                  >
                    segment {citation.segment_id}
                  </button>
                ))}
              </div>
            </div>
          )}
        </div>
      )}
    </section>
  );
}

function SubscriptionsPage() {
  const { t, i18n } = useTranslation();
  const [email, setEmail] = useState("");
  const mutation = useMutation({
    mutationFn: () =>
      api("/api/subscribers/", {
        method: "POST",
        body: JSON.stringify({ email, language: i18n.language, topics: [], frequency: "immediate" }),
      }),
  });

  return (
    <section className="grid gap-8 lg:grid-cols-[1.2fr_0.8fr]">
      <div className="space-y-6">
        <h1 className="font-serif text-5xl text-primary">{t("subscriptions.title")}</h1>
        <input
          value={email}
          onChange={(event) => setEmail(event.target.value)}
          placeholder={t("subscriptions.email")}
          className="w-full border-0 border-b border-outline-variant bg-transparent px-0 py-3 text-lg"
        />
        <button
          onClick={() => mutation.mutate()}
          className="rounded-sm bg-primary px-4 py-2 text-white"
        >
          {t("subscriptions.save")}
        </button>
        {mutation.isSuccess && <p className="text-tertiary">{t("subscriptions.saved")}</p>}
      </div>
      <div className="rounded-lg bg-surface-low p-6">
        <div className="text-xs font-mono uppercase text-on-surface-variant">Preview</div>
        <div className="mt-4 rounded-lg bg-surface-lowest p-5">
          <h2 className="font-serif text-3xl">AI020 briefing</h2>
          <p className="mt-3 text-on-surface-variant">Nieuwe besluiten komen automatisch in uw inbox in uw gekozen taal.</p>
        </div>
      </div>
    </section>
  );
}

function AboutPage() {
  const { t } = useTranslation();
  return (
    <section className="space-y-8">
      <h1 className="font-serif text-6xl text-primary">{t("about.title")}</h1>
      <p className="max-w-3xl text-xl leading-relaxed text-on-surface-variant">{t("about.body")}</p>
      <div className="grid gap-4 md:grid-cols-4">
        {["PDF", "Email", "AI", "Readers"].map((step, index) => (
          <div key={step} className="rounded-lg bg-surface-low p-6">
            <div className="text-xs font-mono text-primary">0{index + 1}</div>
            <h2 className="mt-4 font-serif text-3xl">{step}</h2>
          </div>
        ))}
      </div>
    </section>
  );
}

function AdminPage() {
  const { t } = useTranslation();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [token, setToken] = useState<string | null>(localStorage.getItem("ai020-admin-token"));
  const login = useMutation({
    mutationFn: () =>
      fetch(`${import.meta.env.VITE_API_BASE_URL ?? "http://localhost:8000"}/api/admin/token`, {
        method: "POST",
        headers: { "Content-Type": "application/x-www-form-urlencoded" },
        body: new URLSearchParams({ username: email, password }),
      }).then((response) => response.json()),
    onSuccess: (data: { access_token?: string }) => {
      if (data.access_token) {
        localStorage.setItem("ai020-admin-token", data.access_token);
        setToken(data.access_token);
      }
    },
  });
  const metricsQuery = useQuery({
    queryKey: ["admin-metrics", token],
    enabled: Boolean(token),
    queryFn: () =>
      api<Record<string, unknown>>("/api/admin/metrics", {
        headers: { Authorization: `Bearer ${token}` },
      }),
  });

  if (!token) {
    return (
      <section className="max-w-lg space-y-4">
        <h1 className="font-serif text-5xl">{t("admin.title")}</h1>
        <input value={email} onChange={(event) => setEmail(event.target.value)} placeholder={t("admin.email")} className="w-full rounded border border-outline-variant bg-surface-lowest p-3" />
        <input value={password} onChange={(event) => setPassword(event.target.value)} placeholder={t("admin.password")} type="password" className="w-full rounded border border-outline-variant bg-surface-lowest p-3" />
        <button onClick={() => login.mutate()} className="rounded-sm bg-primary px-4 py-2 text-white">{t("admin.login")}</button>
      </section>
    );
  }

  return (
    <section className="space-y-6">
      <h1 className="font-serif text-5xl">{t("admin.title")}</h1>
      <div className="grid gap-4 md:grid-cols-3">
        {Object.entries(metricsQuery.data ?? {}).map(([key, value]) => (
          <div key={key} className="rounded-lg bg-surface-low p-5">
            <div className="text-xs font-mono uppercase text-on-surface-variant">{key}</div>
            <div className="mt-2 text-3xl font-mono text-primary">{typeof value === "object" ? JSON.stringify(value) : String(value)}</div>
          </div>
        ))}
      </div>
    </section>
  );
}

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
