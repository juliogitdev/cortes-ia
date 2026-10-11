export type Project = {
  project_id: string;
  name: string;
  created_at: string;
  asset_id: string | null;
  account_open_id: string | null;
  profile_id: string | null;
};
export type EditorialProfile = {
  profile_id: string;
  name: string;
  platforms: ("tiktok" | "instagram")[];
  account_open_id: string | null;
  created_at: string;
  tiktok_url: string;
  brand_name: string;
  avatar_version: number;
};
export type ClipEditorial = {
  analysis_id: string;
  candidate_id: string;
  caption: string;
  hashtags: string;
  headline: string;
  status: "draft" | "review" | "approved";
};
export type SubtitleWord = { start_s: number; end_s: number; text: string };
export type SubtitleSettings = {
  enabled: boolean;
  style: "yellow_pop";
  position: "bottom" | "middle";
  max_words_per_line: number;
  font_scale: number;
  text_color: string;
  highlight_color: string;
  outline_color: string;
  outline_width: number;
};
export type ClipSubtitles = {
  revision_id: string;
  enabled: boolean;
  words: SubtitleWord[];
  version: string | null;
  settings?: SubtitleSettings | null;
  suppressed_ranges?: { start_s: number; end_s: number }[];
};
export type MediaVariant = {
  export_id: string;
  revision_id: string;
  kind: "original" | "captioned";
  created_at: string;
  selected: boolean;
  available: boolean;
  duration_s: number;
};
export type ClipMediaVersions = {
  analysis_id: string;
  candidate_id: string;
  selected_export_id: string | null;
  variants: MediaVariant[];
};
export type Job = {
  job_id: string;
  project_id: string;
  kind: "analysis" | "export" | "download";
  status: "queued" | "running" | "completed" | "failed" | "cancelled";
  stage: string;
  payload: Record<string, unknown>;
  result: Record<string, unknown> | null;
  error: string | null;
  created_at: string;
  updated_at: string;
  progress: number | null;
  stage_progress: number | null;
  eta_s: number | null;
  progress_at: string | null;
};
export type Evidence = {
  evidence_id: string;
  start_s: number;
  end_s: number;
  observation: string;
};
export type Candidate = {
  candidate_id: string;
  start_s: number;
  end_s: number;
  rank_score: number;
  reasons: string[];
  limitations: string[];
  evidence_ids: string[];
  features: Record<string, number>;
  versions: { model_version: string; rules_version: string };
};
export type Analysis = {
  asset: { asset_id: string; duration_s: number; source_uri: string };
  request: {
    duration_mode: string;
    min_s?: number;
    max_s?: number;
    target_s?: number;
    top_k: number;
    niche: string;
  };
  candidates: Candidate[];
  evidence: {
    transcript: Evidence[];
    visual_events: Evidence[];
    audio_events: Evidence[];
    quality: string[];
  };
  limitations: string[];
};
export type Revision = {
  revision_id: string;
  candidate_id: string;
  boundaries: { start_s: number; end_s: number };
  editor_changes: string[];
  parent_revision_id: string | null;
};
export type Feedback = {
  feedback_id: string;
  rating: "useful" | "not_useful";
  note: string;
  created_at: string;
};
export type Publication = {
  publication_id: string;
  revision_id: string;
  platform: string;
  account: string;
  account_open_id: string | null;
  posted_at: string;
  publication_url: string | null;
  external_video_id: string | null;
  link_type: "manual" | "automatic";
  publish_id: string | null;
};
export type TikTokVideo = {
  id: string;
  title: string;
  description: string;
  create_time: number | null;
  duration: number | null;
  cover_image_url: string | null;
  share_url: string | null;
};
export type TikTokCreatorInfo = {
  creator_username: string;
  creator_nickname: string;
  privacy_level_options: string[];
  comment_disabled: boolean;
  duet_disabled: boolean;
  stitch_disabled: boolean;
  max_video_post_duration_sec: number | null;
};
export type TikTokPublishAttempt = {
  attempt_id: string;
  revision_id: string;
  export_id: string;
  account_open_id: string;
  account_name: string;
  caption: string;
  privacy_level: string;
  requested_at: string;
  updated_at: string;
  status: "requested" | "scheduled" | "uploading" | "processing" | "completed" | "failed" | "cancelled";
  scheduled_at: string | null;
  batch_id: string | null;
  publish_id: string | null;
  external_video_id: string | null;
  publication_id: string | null;
  error_code: string | null;
};
export type TikTokAccount = {
  open_id: string;
  display_name: string;
  scopes: string[];
  connected_at: string;
};
export type TikTokAppStatus = {
  configured: boolean;
  client_key: string;
  redirect_uri: string;
  secret_saved: boolean;
  request_publish_scope: boolean;
};
export type MetricSnapshot = {
  snapshot_id: string;
  metric_name: string;
  value: number;
  observed_at: string;
  age_hours: number;
};
export type PublicationRecord = {
  publication: Publication;
  snapshots: MetricSnapshot[];
  collections: Array<{
    collection_id: string;
    status: "requested" | "collecting" | "completed" | "partial" | "failed";
    error_code: string | null;
    requested_at: string;
    finished_at: string | null;
  }>;
};
