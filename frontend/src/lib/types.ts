export type Votes = {
  for?: number;
  against?: number;
  abstentions?: number;
  unanimous?: boolean;
  by_party?: Array<{ party: string; vote: string }>;
};

export type AgendaItem = {
  number?: number;
  title: string;
  topic_summary?: string;
  decision?: string;
  decision_detail?: string;
  resident_impact?: string;
  cost?: string;
  votes?: Votes;
  amendments?: Array<{ description: string; decision: string }>;
  motions?: Array<{ description: string; decision: string }>;
};

export type MeetingDetail = {
  id: number;
  title: string;
  municipality?: string | null;
  date?: string | null;
  start_time?: string | null;
  end_time?: string | null;
  status: string;
  topics?: string[] | null;
  summary_nl?: {
    meeting?: Record<string, unknown>;
    agenda_items?: AgendaItem[];
    commitments?: Array<{ by?: string; description: string; deadline?: string }>;
  } | null;
  pdf_path?: string | null;
};

export type MeetingListItem = {
  id: number;
  title: string;
  municipality?: string | null;
  date?: string | null;
  status: string;
  topics?: string[] | null;
  agenda_item_count: number;
};

export type Segment = {
  id: number;
  order_idx: number;
  speaker?: string | null;
  party?: string | null;
  role?: string | null;
  text: string;
  page?: number | null;
  bbox?: number[] | null;
  intent?: string | null;
};

export type SpeakerSummary = {
  id: string;
  speaker: string;
  party?: string | null;
  role?: string | null;
  segment_count: number;
};

export type ChatResponse = {
  answer: string;
  answer_language: string;
  citations: Array<{ segment_id: number; speaker?: string | null; text_excerpt: string }>;
};
