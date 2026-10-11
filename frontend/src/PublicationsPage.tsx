import { useCallback, useEffect, useMemo, useState } from "react";
import { ArrowUpRight, BarChart3, Plus, RefreshCw } from "lucide-react";
import { endpoints } from "./api";
import { TikTokPublishing } from "./TikTokPublishing";
import type { Job, Project, Publication, PublicationRecord, TikTokAccount, TikTokVideo } from "./types";

const metricNames: Record<string, string> = {
  views: "Visualizações", likes: "Curtidas", comments: "Comentários", shares: "Compartilhamentos",
};
const collectionErrors: Record<string, string> = {
  not_connected: "Conta TikTok não conectada.",
  token_expired: "Autorização do TikTok expirada.",
  token_refresh_failed: "Não foi possível renovar a autorização do TikTok.",
  video_not_accessible: "O vídeo não está acessível para esta conta TikTok.",
  tiktok_api_error: "O TikTok recusou a consulta.",
  tiktok_request_failed: "Falha de conexão com o TikTok.",
  metrics_unavailable: "O TikTok não forneceu métricas para este vídeo.",
};

export function PublicationsPage({ jobs, project, profileId, onAccounts }: { jobs: Job[]; project?: Project; profileId: string; onAccounts: (items: TikTokAccount[]) => void }) {
  const [items, setItems] = useState<Publication[]>([]);
  const [records, setRecords] = useState<Record<string, PublicationRecord>>({});
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);
  const [revisionId, setRevisionId] = useState("");
  const [platform, setPlatform] = useState("tiktok");
  const [account, setAccount] = useState("");
  const [selectedVideoId, setSelectedVideoId] = useState("");
  const [videos, setVideos] = useState<TikTokVideo[]>([]);
  const [videoCursor, setVideoCursor] = useState<number | null>(null);
  const [hasMoreVideos, setHasMoreVideos] = useState(false);
  const [videosBusy, setVideosBusy] = useState(false);
  const [linkedAccounts, setLinkedAccounts] = useState<TikTokAccount[]>([]);
  const [url, setUrl] = useState("");
  const [postedAt, setPostedAt] = useState("");
  const [connected, setConnected] = useState(false);
  const handleAccounts = useCallback((linked: TikTokAccount[]) => {
    setLinkedAccounts(linked);
    setConnected(linked.some((item) => item.scopes.includes("video.list")));
    onAccounts(linked);
  }, [onAccounts]);
  const exports = jobs.filter((job) => job.kind === "export" && job.status === "completed" && job.result?.revision_id);
  const accountOpenId = project?.account_open_id || "";
  const folderAccount = linkedAccounts.find((item) => item.open_id === accountOpenId);
  const canCollect = Boolean(folderAccount?.scopes.includes("video.list"));
  const revisionKey = useMemo(() => jobs.filter((job) => job.kind === "export" && job.status === "completed")
    .map((job) => String(job.result?.revision_id)).sort().join("|"), [jobs]);

  const reload = useCallback(async () => {
    const ownRevisionIds = new Set(revisionKey.split("|"));
    const publications = (await endpoints.publications()).filter((item) => ownRevisionIds.has(item.revision_id));
    setItems(publications);
    const entries = await Promise.all(publications.map(async (item) => [item.publication_id, await endpoints.publication(item.publication_id)] as const));
    setRecords(Object.fromEntries(entries));
  }, [revisionKey]);
  const handlePublicationChanged = useCallback(() => {
    void reload().catch(() => {});
  }, [reload]);
  useEffect(() => {
    void reload().catch((cause) => setError(String(cause)));
    void endpoints.tiktokStatus().then((status) => setConnected(status.connected)).catch(() => {});
    void endpoints.tiktokAccounts().then(handleAccounts).catch(() => {});
  }, [reload, handleAccounts]);
  useEffect(() => {
    if (!Object.values(records).some((record) => record.collections.some((run) => run.status === "collecting"))) return;
    const timer = window.setInterval(() => void reload().catch(() => {}), 5000);
    return () => window.clearInterval(timer);
  }, [records, reload]);

  async function collectNow() {
    setBusy(true); setError("");
    try { await endpoints.collectSession(crypto.randomUUID(), "explicit_user_action", profileId); await reload(); }
    catch (cause) { setError(cause instanceof Error ? cause.message : "Falha ao iniciar consulta."); }
    finally { setBusy(false); }
  }

  async function savePublication(event: React.FormEvent) {
    event.preventDefault();
    setError(""); setBusy(true);
    try {
      await endpoints.createPublication({ revision_id: revisionId, platform,
        account: platform === "tiktok" ? folderAccount?.display_name || account.trim() : account.trim(),
        account_open_id: platform === "tiktok" ? accountOpenId : null,
        external_video_id: selectedVideoId || null,
        publication_url: url.trim(), posted_at: postedAt ? new Date(postedAt).toISOString() : null });
      setRevisionId(""); setUrl(""); setPostedAt(""); setSelectedVideoId(""); await reload();
    } catch (cause) { setError(cause instanceof Error ? cause.message : "Falha ao registrar publicação."); }
    finally { setBusy(false); }
  }

  async function linkExisting(publicationId: string) {
    const openId = accountOpenId;
    if (!openId) return;
    setBusy(true); setError("");
    try { await endpoints.linkTikTokPublication(publicationId, openId); await reload(); }
    catch (cause) { setError(cause instanceof Error ? cause.message : "Não foi possível associar a conta."); }
    finally { setBusy(false); }
  }

  async function findVideos(more = false) {
    if (!accountOpenId) return;
    setVideosBusy(true); setError("");
    try {
      const result = await endpoints.tiktokVideos(accountOpenId, more ? videoCursor : null);
      setVideos(more ? [...videos, ...result.videos] : result.videos);
      setVideoCursor(result.cursor); setHasMoreVideos(result.has_more);
    } catch (cause) { setError(cause instanceof Error ? cause.message : "Não foi possível listar os vídeos da conta."); }
    finally { setVideosBusy(false); }
  }

  function selectVideo(video: TikTokVideo) {
    setSelectedVideoId(video.id);
    setUrl(video.share_url || "");
    if (video.create_time) {
      const date = new Date(video.create_time * 1000);
      const part = (value: number) => String(value).padStart(2, "0");
      setPostedAt(`${date.getFullYear()}-${part(date.getMonth() + 1)}-${part(date.getDate())}T${part(date.getHours())}:${part(date.getMinutes())}`);
    } else setPostedAt("");
  }

  return <div className="publications-page">
    <div className="page-title"><div><span className="eyebrow">{project?.name || "ESCOLHA UMA LIVE"}</span><h1>Publicar e acompanhar</h1><p>Envie cortes, vincule posts existentes e acompanhe as métricas coletadas do TikTok.</p></div></div>
    <div className="panel publication-folder-account"><div><strong>Conta TikTok desta live</strong><small>{project ? "Esta página mostra somente os cortes e resultados da live aberta neste perfil." : "Abra uma live deste perfil para publicar e acompanhar seus cortes."}</small></div><strong>{folderAccount?.display_name || "Nenhuma conta vinculada ao perfil"}</strong></div>
    <div className={`integration-notice ${connected ? "connected" : ""}`}>
      <div><strong>{canCollect ? `${folderAccount?.display_name}: métricas automáticas` : "Métricas aguardando conta TikTok"}</strong><p>{canCollect ? "Ao vincular um corte ao link do post, esta live consulta curtidas, comentários, compartilhamentos e visualizações. Uma nova consulta também acontece ao entrar no painel." : "Adicione uma conta com permissão video.list a esta pasta. Sem essa autorização, o TikTok não libera as métricas dos seus vídeos."}</p></div>
      {canCollect && <button className="button outline" disabled={busy} onClick={() => void collectNow()}><RefreshCw size={15}/> Atualizar agora</button>}
    </div>
    <TikTokPublishing jobs={jobs} projectId={project?.project_id || ""} accounts={linkedAccounts} folderAccountId={accountOpenId} onChanged={handlePublicationChanged} />
    {error && <div className="notice error" role="alert">{error}</div>}
    <div className="results-layout">
      <section className="panel results-form"><div className="section-kicker"><Plus size={17}/> VÍNCULO MANUAL</div><h2>Vincular um corte publicado</h2><p>Escolha o corte e cole o link do post. As métricas são consultadas após salvar o vínculo.</p>
        {!canCollect && <div className="feature-lock"><strong>Vinculação com métricas automáticas bloqueada</strong><small>{!project ? "Abra uma live primeiro." : !accountOpenId ? "Adicione uma conta TikTok à pasta desta live." : "A conta desta pasta precisa autorizar video.list."}</small></div>}
        <form onSubmit={(event) => void savePublication(event)}>
          <label>Corte exportado<select required value={revisionId} onChange={(event) => setRevisionId(event.target.value)}><option value="">Selecione um corte</option>{exports.map((job) => <option key={job.job_id} value={String(job.result?.revision_id)}>{String(job.payload.candidate_id || job.result?.revision_id).slice(0, 18)} · {new Date(job.created_at).toLocaleDateString("pt-BR")}</option>)}</select></label>
          <div className="results-form-row"><label>Plataforma<select value={platform} onChange={(event) => setPlatform(event.target.value)}><option value="tiktok">TikTok</option><option value="youtube">YouTube</option><option value="instagram">Instagram</option><option value="facebook">Facebook</option><option value="outro">Outra</option></select></label>{platform === "tiktok" ? <label>Conta desta live<input readOnly value={folderAccount?.display_name || "Nenhuma conta vinculada à pasta"} /></label> : <label>Perfil<input required maxLength={100} value={account} onChange={(event) => setAccount(event.target.value)} placeholder="@seu_perfil" /></label>}</div>
          {platform === "tiktok" && accountOpenId && <div className="tiktok-video-picker"><button className="button outline" type="button" disabled={videosBusy || !linkedAccounts.find((item) => item.open_id === accountOpenId)?.scopes.includes("video.list")} onClick={() => void findVideos()}>Buscar vídeos públicos desta conta</button>{videos.length > 0 && <div className="tiktok-video-list">{videos.map((video) => <div className={`tiktok-video-row ${selectedVideoId === video.id ? "selected" : ""}`} key={video.id}>{video.cover_image_url && <img src={video.cover_image_url} alt="Capa do vídeo no TikTok" loading="lazy" />}<div><strong>{video.title || video.description || `Vídeo ${video.id}`}</strong><small>{video.create_time ? new Date(video.create_time * 1000).toLocaleString("pt-BR") : "Data indisponível"}{video.duration ? ` · ${video.duration} s` : ""}</small></div><button type="button" className="button subtle" onClick={() => selectVideo(video)}>Escolher</button></div>)}{hasMoreVideos && <button type="button" className="button subtle" disabled={videosBusy} onClick={() => void findVideos(true)}>Carregar mais</button>}</div>}<small>Escolher um vídeo preenche os dados; confirme a correspondência com o corte antes de salvar.</small></div>}
          <label>Link da publicação<input required type="url" value={url} onChange={(event) => { setUrl(event.target.value); setSelectedVideoId(""); }} placeholder="https://..." /></label>
          <label>Data e hora da postagem {platform === "tiktok" ? "(opcional)" : ""}<input required={platform !== "tiktok"} type="datetime-local" value={postedAt} onChange={(event) => setPostedAt(event.target.value)} /></label>
          {platform === "tiktok" && <small>Se deixar vazio, a aplicação consulta a data real no TikTok ao salvar o vínculo.</small>}
          <button className="button primary" disabled={busy || !exports.length || (platform === "tiktok" && !canCollect)} type="submit">Vincular e consultar métricas</button>
        </form>
      </section>
      <section className="panel results-history"><div className="section-kicker"><BarChart3 size={17}/> Histórico</div><h2>{items.length} publicação(ões)</h2><p>Métricas ficam registradas por postagem e horário de observação.</p>
        {!items.length && <div className="results-empty">Nenhuma publicação registrada ainda. Exporte um corte e vincule o link aqui.</div>}
        {items.map((item) => <article className="publication-row" key={item.publication_id}><div className="publication-head"><div><strong>{item.platform.toUpperCase()} · {item.account}</strong><small>{new Date(item.posted_at).toLocaleString("pt-BR")} · <b className={`link-type ${item.link_type}`}>Vínculo {item.link_type === "automatic" ? "automático" : "manual"}</b></small></div>{item.publication_url && <a href={item.publication_url} target="_blank" rel="noreferrer" aria-label="Abrir publicação"><ArrowUpRight size={18}/></a>}</div>
          {item.link_type === "automatic" && !item.external_video_id && <small className="collection-status">Envio vinculado ao corte; o TikTok ainda não forneceu um ID público para consultar métricas.</small>}
          {item.platform.toLowerCase() === "tiktok" && item.link_type === "manual" && <div className="tiktok-publication-link"><small>{item.account_open_id ? `Conta vinculada: ${linkedAccounts.find((linked) => linked.open_id === item.account_open_id)?.display_name || "conta indisponível"}.` : "Publicação antiga sem conta associada."}</small>{item.account_open_id !== accountOpenId && canCollect && <button className="button outline" disabled={busy} onClick={() => void linkExisting(item.publication_id)}>Associar à conta desta live e consultar</button>}</div>}
          {(() => { const last = records[item.publication_id]?.collections.at(-1); return last && <small className="collection-status">{last.status === "collecting" ? "Consultando TikTok…" : last.status === "failed" ? collectionErrors[last.error_code || ""] || "Consulta indisponível." : `Última consulta: ${new Date(last.finished_at || last.requested_at).toLocaleString("pt-BR")}${last.status === "partial" ? " · dados parciais" : ""}`}</small>; })()}
          <div className="publication-metrics">{Object.keys(metricNames).map((name) => { const latest = records[item.publication_id]?.snapshots.filter((entry) => entry.metric_name === name).at(-1); return <span key={name}><small>{metricNames[name]}</small><strong>{latest ? latest.value.toLocaleString("pt-BR") : "—"}</strong></span>; })}</div>
          {records[item.publication_id]?.snapshots.length ? <div className="metric-entry"><small>Histórico de métricas coletadas</small>{records[item.publication_id].snapshots.slice().reverse().map((snapshot) => <div className="metric-history" key={snapshot.snapshot_id}>{metricNames[snapshot.metric_name]}: {snapshot.value.toLocaleString("pt-BR")} · {new Date(snapshot.observed_at).toLocaleString("pt-BR")}</div>)}</div> : null}
        </article>)}
      </section>
    </div>
  </div>;
}
