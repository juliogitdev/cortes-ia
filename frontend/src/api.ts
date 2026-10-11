import type { Analysis, ClipEditorial, ClipMediaVersions, ClipSubtitles, SubtitleSettings, SubtitleWord, EditorialProfile, Feedback, Job, Project, Revision, Publication, PublicationRecord, MetricSnapshot, TikTokAccount, TikTokAppStatus, TikTokVideo, TikTokCreatorInfo, TikTokPublishAttempt } from "./types";

export async function api<T>(
  path: string,
  options: RequestInit = {},
): Promise<T> {
  const headers = new Headers(options.headers);
  if (options.body && !(options.body instanceof FormData))
    headers.set("Content-Type", "application/json");
  const response = await fetch(path, { ...options, headers });
  if (!response.ok) {
    let message = `Erro ${response.status}`;
    try {
      const payload = await response.json();
      message = typeof payload.detail === "string" ? payload.detail : message;
    } catch {
      /* empty body */
    }
    throw new Error(message);
  }
  if (response.status === 204) return undefined as T;
  return response.json() as Promise<T>;
}

export const endpoints = {
  profiles: () => api<EditorialProfile[]>("/profiles"),
  createProfile: (name: string, platforms: EditorialProfile["platforms"], account_open_id: string | null) => api<EditorialProfile>("/profiles", { method: "POST", body: JSON.stringify({ name, platforms, account_open_id }) }),
  updateProfile: (id: string, name: string, platforms: EditorialProfile["platforms"], account_open_id: string | null) => api<EditorialProfile>(`/profiles/${id}`, { method: "PUT", body: JSON.stringify({ name, platforms, account_open_id }) }),
  saveProfileBranding: (id: string, tiktok_url: string, brand_name: string) => api<EditorialProfile>(`/profiles/${id}/branding`, { method: "PUT", body: JSON.stringify({ tiktok_url, brand_name }) }),
  uploadProfileAvatar: async (id: string, file: File): Promise<EditorialProfile> => {
    const response = await fetch(`/profiles/${id}/avatar`, { method: "PUT", headers: { "Content-Type": file.type }, body: file });
    if (!response.ok) throw new Error((await response.json()).detail || `Erro ${response.status}`);
    return response.json() as Promise<EditorialProfile>;
  },
  deleteProfile: (id: string) => api<{ status: string }>(`/profiles/${id}`, { method: "DELETE" }),
  assignProjectProfile: (projectId: string, profileId: string | null) => api<Project>(`/projects/${projectId}/profile`, { method: "PATCH", body: JSON.stringify({ profile_id: profileId }) }),
  clipEditorial: (analysisId: string, candidateId: string) => api<ClipEditorial>(`/analyses/${analysisId}/candidates/${candidateId}/editorial`),
  clipSubtitles: (analysisId: string, candidateId: string) => api<ClipSubtitles>(`/analyses/${analysisId}/candidates/${candidateId}/subtitles`),
  mediaVersions: (projectId: string) => api<ClipMediaVersions[]>(`/projects/${projectId}/media-versions`),
  selectMediaVersion: (analysisId: string, candidateId: string, exportId: string) => api<ClipMediaVersions>(`/analyses/${analysisId}/candidates/${candidateId}/media-selection`, { method: "PUT", body: JSON.stringify({ export_id: exportId }) }),
  deleteMediaVersion: (analysisId: string, candidateId: string, exportId: string) => api<ClipMediaVersions>(`/analyses/${analysisId}/candidates/${candidateId}/media-versions/${encodeURIComponent(exportId)}`, { method: "DELETE" }),
  saveClipSubtitles: (analysisId: string, candidateId: string, words: SubtitleWord[], settings: SubtitleSettings) => api<Job>(`/analyses/${analysisId}/candidates/${candidateId}/subtitles`, { method: "PUT", body: JSON.stringify({ words, settings }) }),
  saveClipEditorial: (value: ClipEditorial) => api<ClipEditorial>(`/analyses/${value.analysis_id}/candidates/${value.candidate_id}/editorial`, { method: "PUT", body: JSON.stringify(value) }),
  tiktokVideos: (openId: string, cursor?: number | null) => api<{ videos: TikTokVideo[]; cursor: number | null; has_more: boolean }>(`/integrations/tiktok/accounts/${encodeURIComponent(openId)}/videos/list`, {
    method: "POST", body: JSON.stringify({ cursor: cursor ?? null }),
  }),
  tiktokCreatorInfo: (openId: string) => api<TikTokCreatorInfo>(`/integrations/tiktok/accounts/${encodeURIComponent(openId)}/creator-info/query`, { method: "POST" }),
  tiktokPosts: () => api<TikTokPublishAttempt[]>("/tiktok-posts"),
  createTikTokPost: (payload: Record<string, unknown>) => api<TikTokPublishAttempt>("/tiktok-posts", { method: "POST", body: JSON.stringify(payload) }),
  scheduleTikTokPosts: (payload: Record<string, unknown>) => api<TikTokPublishAttempt[]>("/tiktok-posts/schedule", { method: "POST", body: JSON.stringify(payload) }),
  cancelTikTokPost: (id: string) => api<TikTokPublishAttempt>(`/tiktok-posts/${encodeURIComponent(id)}/cancel`, { method: "POST" }),
  refreshTikTokPost: (id: string) => api<TikTokPublishAttempt>(`/tiktok-posts/${encodeURIComponent(id)}/refresh`, { method: "POST" }),
  tiktokApp: () => api<TikTokAppStatus>("/integrations/tiktok/app"),
  saveTikTokApp: (payload: Record<string, unknown>) => api<TikTokAppStatus>("/integrations/tiktok/app", {
    method: "PUT", body: JSON.stringify(payload),
  }),
  tiktokAccounts: () => api<TikTokAccount[]>("/integrations/tiktok/accounts"),
  authorizeTikTok: () => api<{ url: string }>("/integrations/tiktok/authorize"),
  disconnectTikTok: (openId: string) => api<void>(`/integrations/tiktok/accounts/${encodeURIComponent(openId)}`, { method: "DELETE" }),
  linkTikTokPublication: (id: string, openId: string) => api<Publication>(`/publications/${id}/account`, {
    method: "PATCH", body: JSON.stringify({ account_open_id: openId }),
  }),
  tiktokStatus: () => api<{ connected: boolean; reason: string | null }>("/integrations/tiktok"),
  collectSession: (requestId: string, trigger: "explicit_user_action" | "authorized_session_start" = "authorized_session_start", profileId: string | null = null) =>
    api<unknown[]>("/publications/collect-session", {
      method: "POST", body: JSON.stringify({ request_id: requestId, trigger, profile_id: profileId }),
    }),
  publications: () => api<Publication[]>("/publications"),
  publication: (id: string) => api<PublicationRecord>(`/publications/${id}`),
  createPublication: (payload: Record<string, unknown>) =>
    api<Publication>("/publications", { method: "POST", body: JSON.stringify(payload) }),
  addMetric: (id: string, metric_name: string, value: number) =>
    api<MetricSnapshot>(`/publications/${id}/metrics`, {
      method: "POST", body: JSON.stringify({ metric_name, value, reviewer: "Administrador local" }),
    }),
  projects: () => api<Project[]>("/projects"),
  createProject: (name: string, profileId: string | null = null) =>
    api<Project>("/projects", {
      method: "POST",
      body: JSON.stringify({ name, profile_id: profileId }),
    }),
  renameProject: (id: string, name: string) =>
    api<Project>(`/projects/${id}`, {
      method: "PATCH",
      body: JSON.stringify({ name }),
    }),
  assignProjectAccount: (id: string, openId: string | null) =>
    api<Project>(`/projects/${encodeURIComponent(id)}/tiktok-account`, {
      method: "PATCH", body: JSON.stringify({ account_open_id: openId }),
    }),
  deleteProject: (id: string) => api<{ status: string; scope: string }>(`/projects/${encodeURIComponent(id)}`, { method: "DELETE" }),
  jobs: (id: string) => api<Job[]>(`/projects/${id}/jobs`),
  job: (id: string) => api<Job>(`/jobs/${id}`),
  cancelJob: (id: string) => api<Job>(`/jobs/${id}/cancel`, { method: "POST" }),
  analysis: (id: string) => api<Analysis>(`/analyses/${id}/candidates`),
  discarded: (id: string) => api<string[]>(`/analyses/${id}/discarded`),
  ensureExports: (id: string) =>
    api<Job[]>(`/analyses/${id}/exports`, { method: "POST" }),
  upload: (id: string, file: File) => {
    const body = new FormData();
    body.append("file", file);
    return api(`/projects/${id}/upload`, { method: "POST", body });
  },
  download: (id: string, url: string, settings: Record<string, unknown>) =>
    api<Job>(`/projects/${id}/downloads`, {
      method: "POST",
      headers: { "Idempotency-Key": crypto.randomUUID() },
      body: JSON.stringify({ url, settings }),
    }),
  analyze: (id: string, payload: Record<string, unknown>) =>
    api<Job>(`/projects/${id}/analyses`, {
      method: "POST",
      headers: { "Idempotency-Key": crypto.randomUUID() },
      body: JSON.stringify(payload),
    }),
  feedback: (analysis: string, candidate: string) =>
    api<Feedback[]>(`/analyses/${analysis}/candidates/${candidate}/feedback`),
  sendFeedback: (
    analysis: string,
    candidate: string,
    rating: "useful" | "not_useful",
    note: string,
  ) =>
    api<Feedback>(`/analyses/${analysis}/candidates/${candidate}/feedback`, {
      method: "POST",
      body: JSON.stringify({ rating, note }),
    }),
  discard: (analysis: string, candidate: string) =>
    api(`/analyses/${analysis}/candidates/${candidate}`, { method: "DELETE" }),
  revision: (
    analysis: string,
    candidate: string,
    start_s: number,
    end_s: number,
    parent_revision_id: string | null,
  ) =>
    api<Revision>(`/candidates/${candidate}/revisions`, {
      method: "POST",
      body: JSON.stringify({
        analysis_id: analysis,
        start_s,
        end_s,
        parent_revision_id,
        editor_changes: ["Limites ajustados no estúdio"],
      }),
    }),
  exportRevision: (id: string) =>
    api<Job>(`/revisions/${id}/exports`, {
      method: "POST",
      headers: { "Idempotency-Key": `export-${id}` },
    }),
};
