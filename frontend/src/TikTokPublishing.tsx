import { useCallback, useEffect, useRef, useState } from "react";
import { Send, RefreshCw } from "lucide-react";
import { endpoints } from "./api";
import type { ClipMediaVersions, Job, MediaVariant, TikTokAccount, TikTokCreatorInfo, TikTokPublishAttempt } from "./types";

const privacyNames: Record<string, string> = {
  PUBLIC_TO_EVERYONE: "Público", MUTUAL_FOLLOW_FRIENDS: "Amigos",
  FOLLOWER_OF_CREATOR: "Seguidores", SELF_ONLY: "Somente eu",
};
const statusNames: Record<TikTokPublishAttempt["status"], string> = {
  scheduled: "Agendado", cancelled: "Cancelado",
  requested: "Preparando envio", uploading: "Enviando vídeo", processing: "Processando no TikTok",
  completed: "Publicado e vinculado automaticamente", failed: "Falha no envio ou processamento",
};
const errorNames: Record<string, string> = {
  scope_not_authorized: "A conta precisa autorizar a permissão video.publish.",
  unaudited_client_can_only_post_to_private_accounts: "O TikTok restringiu esta publicação porque o aplicativo ainda não foi auditado.",
  privacy_level_option_mismatch: "A visibilidade escolhida não está disponível para esta conta.",
  video_too_long_for_account: "O corte excede a duração permitida para esta conta.",
  spam_risk_too_many_posts: "O limite de publicações da conta foi atingido.",
  upload_failed: "O envio do arquivo ao TikTok falhou.",
  tiktok_request_failed: "Não foi possível comunicar com o TikTok.",
};
function errorText(cause: unknown, fallback: string) {
  const code = cause instanceof Error ? cause.message : "";
  return errorNames[code] || code || fallback;
}

export function TikTokPublishing({ jobs, projectId, accounts, folderAccountId, onChanged }: {
  jobs: Job[]; projectId: string; accounts: TikTokAccount[]; folderAccountId: string; onChanged: () => void;
}) {
  const openId = folderAccountId;
  const [exportId, setExportId] = useState("");
  const [candidateKey, setCandidateKey] = useState("");
  const [versions, setVersions] = useState<ClipMediaVersions[]>([]);
  const [bulkVersions, setBulkVersions] = useState<Record<string, string>>({});
  const [bulk, setBulk] = useState(false);
  const [selectedIds, setSelectedIds] = useState<string[]>([]);
  const [timing, setTiming] = useState<"now" | "individual" | "interval">("now");
  const [startAt, setStartAt] = useState("");
  const [intervalHours, setIntervalHours] = useState(2);
  const [itemCaptions, setItemCaptions] = useState<Record<string, string>>({});
  const [itemTimes, setItemTimes] = useState<Record<string, string>>({});
  const [itemPrivacy, setItemPrivacy] = useState<Record<string, string>>({});
  const [caption, setCaption] = useState("");
  const [creator, setCreator] = useState<TikTokCreatorInfo | null>(null);
  const [preparedAccountId, setPreparedAccountId] = useState("");
  const [privacy, setPrivacy] = useState("");
  const [disableComment, setDisableComment] = useState(false);
  const [disableDuet, setDisableDuet] = useState(false);
  const [disableStitch, setDisableStitch] = useState(false);
  const [consent, setConsent] = useState(false);
  const [posts, setPosts] = useState<TikTokPublishAttempt[]>([]);
  const [busy, setBusy] = useState("");
  const [error, setError] = useState("");
  const reported = useRef(new Set<string>());
  const exports = jobs.filter((job) => job.kind === "export" && job.status === "completed" && job.result?.export_id);
  const completedExportIds = exports.map((job) => job.job_id).join("|");
  useEffect(() => {
    if (!projectId) return;
    let mounted = true;
    void endpoints.mediaVersions(projectId).then((items) => { if (mounted) setVersions(items); }).catch(() => {});
    return () => { mounted = false; };
  }, [projectId, completedExportIds]);
  const clipKey = (item: ClipMediaVersions) => `${item.analysis_id}:${item.candidate_id}`;
  const availableGroups = versions.filter((item) => item.variants.some((variant) => variant.available));
  const versionName = (item: ClipMediaVersions, variant: MediaVariant) => variant.kind === "original" ? "Original sem legenda" : `Legenda ${item.variants.slice(0, item.variants.findIndex((entry) => entry.export_id === variant.export_id) + 1).filter((entry) => entry.kind === "captioned").length}`;
  const singleGroup = availableGroups.find((item) => clipKey(item) === candidateKey);
  const variantChoice = (item: ClipMediaVersions, id: string) => item.variants.find((variant) => variant.export_id === id && variant.available);
  const chosen = bulk ? selectedIds.flatMap((key) => {
    const group = availableGroups.find((item) => clipKey(item) === key);
    const variant = group && variantChoice(group, bulkVersions[key] || "");
    return group && variant ? [{ group, variant }] : [];
  }) : singleGroup && variantChoice(singleGroup, exportId) ? [{ group: singleGroup, variant: variantChoice(singleGroup, exportId)! }] : [];
  const publishers = accounts.filter((item) => item.open_id === folderAccountId && item.scopes.includes("video.publish"));
  const readyCreator = preparedAccountId === openId ? creator : null;
  const ownRevisions = new Set(exports.map((job) => String(job.result?.revision_id)));
  const visiblePosts = posts.filter((item) => item.account_open_id === folderAccountId && ownRevisions.has(item.revision_id));
  const displayGroup = (group: ClipMediaVersions) => `Corte ${group.candidate_id.slice(0, 18)} · análise ${group.analysis_id.slice(0, 8)}`;

  const reload = useCallback(async () => {
    const items = await endpoints.tiktokPosts();
    setPosts(items);
    for (const item of items) {
      if (item.status === "completed" && !reported.current.has(item.attempt_id)) {
        reported.current.add(item.attempt_id);
        onChanged();
      }
    }
  }, [onChanged]);
  useEffect(() => { void reload().catch(() => {}); }, [reload]);
  useEffect(() => {
    if (!posts.some((item) => ["scheduled", "requested", "uploading", "processing"].includes(item.status))) return;
    const timer = window.setInterval(() => void reload().catch(() => {}), 5000);
    return () => window.clearInterval(timer);
  }, [posts, reload]);

  async function prepare() {
    setBusy("prepare"); setError("");
    try {
      const info = await endpoints.tiktokCreatorInfo(openId);
      setCreator(info); setPreparedAccountId(openId); setPrivacy(info.privacy_level_options[0] || "");
      setDisableComment(info.comment_disabled); setDisableDuet(info.duet_disabled);
      setDisableStitch(info.stitch_disabled);
    } catch (cause) { setError(errorText(cause, "Não foi possível obter as opções da conta.")); }
    finally { setBusy(""); }
  }

  async function publish(event: React.FormEvent) {
    event.preventDefault(); setBusy("publish"); setError("");
    const selected = chosen[0];
    if (!selected || (bulk && chosen.length !== selectedIds.length) || !consent) { setError("Escolha uma versão para cada corte e confirme o envio."); setBusy(""); return; }
    try {
      if (timing === "now" && !bulk) {
        await endpoints.createTikTokPost({ request_id: crypto.randomUUID(),
          revision_id: selected.variant.revision_id, export_id: selected.variant.export_id, account_open_id: openId,
          caption: itemCaptions[exportId] ?? caption, privacy_level: itemPrivacy[exportId] ?? privacy,
          disable_comment: disableComment, disable_duet: disableDuet, disable_stitch: disableStitch, consent: true });
      } else {
        const items = chosen.map(({ variant }) => {
          const id = variant.export_id;
          const when = itemTimes[id];
          if (timing === "individual" && (!when || Number.isNaN(new Date(when).getTime()))) throw new Error("Informe data e hora de cada vídeo.");
          return { revision_id: variant.revision_id, export_id: id,
            caption: itemCaptions[id] ?? caption, privacy_level: itemPrivacy[id] ?? privacy,
            disable_comment: disableComment, disable_duet: disableDuet, disable_stitch: disableStitch,
            ...(timing === "individual" ? { scheduled_at: new Date(when).toISOString() } : {}) };
        });
        if (timing === "interval" && (!startAt || Number.isNaN(new Date(startAt).getTime()))) throw new Error("Informe a data inicial.");
        await endpoints.scheduleTikTokPosts({ batch_id: crypto.randomUUID(), account_open_id: openId,
          mode: timing, items,
          ...(timing === "interval" ? { start_at: new Date(startAt).toISOString(), interval_hours: intervalHours } : {}),
          consent: true });
      }
      setConsent(false); await reload();
    } catch (cause) { setError(errorText(cause, "Falha ao iniciar publicação.")); }
    finally { setBusy(""); }
  }

  async function verify(id: string) {
    setBusy(id); setError("");
    try { await endpoints.refreshTikTokPost(id); await reload(); }
    catch (cause) { setError(errorText(cause, "Consulta de status indisponível.")); }
    finally { setBusy(""); }
  }

  async function cancel(id: string) {
    setBusy(id); setError("");
    try { await endpoints.cancelTikTokPost(id); await reload(); }
    catch (cause) { setError(errorText(cause, "Não foi possível cancelar o agendamento.")); }
    finally { setBusy(""); }
  }

  return <section className="panel tiktok-publishing">
    <div className="section-kicker"><Send size={17}/> PUBLICAR PELO PAINEL</div>
    <h2>Publicação com vínculo automático</h2>
    <p>Escolha um corte exportado e a conta de destino. O vínculo nasce do envio feito por esta plataforma e acompanha o processamento no TikTok.</p>
    {error && <div className="notice error" role="alert">{error}</div>}
    {!publishers.length && <div className="feature-lock"><strong>Publicação disponível após vincular a conta da pasta</strong><small>{!folderAccountId ? "Adicione uma conta TikTok à pasta desta live para liberar o envio." : "A conta desta pasta precisa autorizar video.publish no TikTok."}</small><div className="locked-actions"><button className="button outline" disabled>Publicar vídeo</button><button className="button outline" disabled>Agendar vídeo</button><button className="button outline" disabled>Publicar em lote</button></div></div>}
    {publishers.length > 0 && <form className="tiktok-publish-form" onSubmit={(event) => void publish(event)}>
      <div className="results-form-row">
        <label>Conta de destino<select required value={openId} disabled><option value={folderAccountId}>{publishers[0].display_name}</option></select></label>
        {!bulk && <><label>Corte<select required value={candidateKey} onChange={(event) => { setCandidateKey(event.target.value); setExportId(""); }}><option value="">Selecione o corte</option>{availableGroups.map((group) => <option key={clipKey(group)} value={clipKey(group)}>{displayGroup(group)}</option>)}</select></label><label>Versão para publicar<select required value={exportId} onChange={(event) => setExportId(event.target.value)}><option value="">Escolha original ou legenda</option>{singleGroup?.variants.filter((variant) => variant.available).map((variant) => <option key={variant.export_id} value={variant.export_id}>{versionName(singleGroup, variant)}{variant.selected ? " · Em uso" : ""}</option>)}</select></label></>}
      </div>
      <label className="tiktok-consent"><input type="checkbox" checked={bulk} onChange={(event) => { setBulk(event.target.checked); setTiming(event.target.checked ? "interval" : "now"); }} /> Agendar vários vídeos</label>
      {bulk && <div className="tiktok-bulk-list"><strong>Selecione os cortes na ordem e escolha uma versão de cada um</strong>{availableGroups.map((group) => { const key = clipKey(group); return <div className="tiktok-version-choice" key={key}><label><input type="checkbox" checked={selectedIds.includes(key)} onChange={(event) => setSelectedIds((current) => event.target.checked ? [...current, key] : current.filter((value) => value !== key))} /> {displayGroup(group)}</label>{selectedIds.includes(key) && <select aria-label={`Versão para ${displayGroup(group)}`} required value={bulkVersions[key] || ""} onChange={(event) => setBulkVersions((current) => ({ ...current, [key]: event.target.value }))}><option value="">Escolha original ou legenda</option>{group.variants.filter((variant) => variant.available).map((variant) => <option key={variant.export_id} value={variant.export_id}>{versionName(group, variant)}{variant.selected ? " · Em uso" : ""}</option>)}</select>}</div>; })}</div>}
      <button className="button outline" type="button" disabled={!openId || busy !== ""} onClick={() => void prepare()}>Consultar opções da conta</button>
      {readyCreator && <>
        <div className="tiktok-creator-summary"><strong>Destino: {readyCreator.creator_nickname || readyCreator.creator_username}</strong><small>@{readyCreator.creator_username} · Limite de vídeo: {readyCreator.max_video_post_duration_sec ?? "indisponível"} s</small></div>
        <label>Legenda padrão<textarea maxLength={2200} value={caption} onChange={(event) => setCaption(event.target.value)} placeholder="Escreva a legenda e as hashtags" /></label>
        <label>Quem pode assistir<select required value={privacy} onChange={(event) => setPrivacy(event.target.value)}>{readyCreator.privacy_level_options.map((option) => <option key={option} value={option}>{privacyNames[option] || option}</option>)}</select></label>
        <div className="tiktok-publish-options">
          <label><input type="checkbox" checked={disableComment} disabled={readyCreator.comment_disabled} onChange={(event) => setDisableComment(event.target.checked)} /> Desativar comentários</label>
          <label><input type="checkbox" checked={disableDuet} disabled={readyCreator.duet_disabled} onChange={(event) => setDisableDuet(event.target.checked)} /> Desativar duetos</label>
          <label><input type="checkbox" checked={disableStitch} disabled={readyCreator.stitch_disabled} onChange={(event) => setDisableStitch(event.target.checked)} /> Desativar costuras</label>
        </div>
        <label>Quando publicar<select value={timing} onChange={(event) => setTiming(event.target.value as typeof timing)}>
          {!bulk && <option value="now">Agora</option>}<option value="individual">Data e hora por vídeo</option><option value="interval">Intervalo de horas</option>
        </select></label>
        {timing === "interval" && <div className="results-form-row">
          <label>Começar em<input type="datetime-local" required value={startAt} onChange={(event) => setStartAt(event.target.value)} /></label>
          <label>Intervalo (horas)<input type="number" min="0.1" max="168" step="0.1" required value={intervalHours} onChange={(event) => setIntervalHours(Number(event.target.value))} /></label>
        </div>}
        {chosen.length > 0 && <div className="tiktok-bulk-list"><strong>Configuração de cada vídeo</strong>{chosen.map(({ group, variant }, index) => {
          const id = variant.export_id;
          const projected = timing === "interval" && startAt && !Number.isNaN(new Date(startAt).getTime()) ? new Date(new Date(startAt).getTime() + index * intervalHours * 3600000).toLocaleString("pt-BR") : "";
          return <div className="tiktok-schedule-item" key={id}>
            <strong>{index + 1}. {displayGroup(group)} · {versionName(group, variant)}</strong>
            <label>Legenda<textarea maxLength={2200} value={itemCaptions[id] ?? caption} onChange={(event) => setItemCaptions((current) => ({ ...current, [id]: event.target.value }))} /></label>
            <label>Visibilidade<select value={itemPrivacy[id] ?? privacy} onChange={(event) => setItemPrivacy((current) => ({ ...current, [id]: event.target.value }))}>{readyCreator.privacy_level_options.map((option) => <option key={option} value={option}>{privacyNames[option] || option}</option>)}</select></label>
            {timing === "individual" && <label>Data e hora<input type="datetime-local" required value={itemTimes[id] ?? ""} onChange={(event) => setItemTimes((current) => ({ ...current, [id]: event.target.value }))} /></label>}
            {projected && <small>Previsto: {projected}</small>}
          </div>;
        })}</div>}
        <label className="tiktok-consent"><input type="checkbox" checked={consent} onChange={(event) => setConsent(event.target.checked)} /> Confirmo o envio dos vídeos selecionados, com as legendas, horários e visibilidade exibidos.</label>
        <small>Os horários usam o fuso deste dispositivo. O computador precisa permanecer ligado e com o agendador ativo. O TikTok pode limitar contas e aplicativos ainda não auditados.</small>
        <button className="button primary" type="submit" disabled={!consent || !privacy || !chosen.length || (bulk && chosen.length !== selectedIds.length) || busy !== ""}>{timing === "now" && !bulk ? "Publicar no TikTok" : `Agendar ${chosen.length} vídeo${chosen.length === 1 ? "" : "s"}`}</button>
      </>}
    </form>}
    <div className="tiktok-post-history"><h3>Envios pelo painel</h3>
      {!visiblePosts.length && <small>Nenhum envio desta live iniciado.</small>}
      {visiblePosts.map((item) => <div className="tiktok-post-row" key={item.attempt_id}>
        <div><strong>{item.account_name} · {statusNames[item.status]}</strong><small>Corte {item.revision_id.slice(0, 18)} · {item.scheduled_at ? `Previsto: ${new Date(item.scheduled_at).toLocaleString("pt-BR")}` : new Date(item.requested_at).toLocaleString("pt-BR")}</small><small>Legenda: {item.caption || "(sem legenda)"}</small>{item.error_code && <small>Motivo: {errorNames[item.error_code] || item.error_code} Confira a conta no TikTok antes de tentar novamente.</small>}{item.status === "completed" && !item.external_video_id && <small>Vínculo automático salvo; ID público ainda indisponível.</small>}</div>
        {item.status === "scheduled" && <button className="button subtle" type="button" disabled={busy !== ""} onClick={() => void cancel(item.attempt_id)}>Cancelar</button>}
        {item.publish_id && (item.status !== "completed" || !item.external_video_id) && <button className="button subtle" disabled={busy !== ""} onClick={() => void verify(item.attempt_id)}><RefreshCw size={15}/> Verificar status</button>}
      </div>)}
    </div>
  </section>;
}
