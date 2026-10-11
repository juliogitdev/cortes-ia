import { useEffect, useState } from "react";
import {
  ArrowDownToLine,
  ArrowRight,
  Check,
  ChevronRight,
  Clock3,
  Copy,
  CloudUpload,
  Film,
  FolderPlus,
  Info,
  Link2,
  Play,
  Plus,
  Scissors,
  Sparkles,
  ThumbsDown,
  ThumbsUp,
  Trash2,
  X,
} from "lucide-react";
import { endpoints } from "./api";
import type { Analysis, Candidate, ClipMediaVersions, ClipSubtitles, EditorialProfile, Feedback, Job, SubtitleSettings, SubtitleWord } from "./types";
import { description, statusLabel, timeLabel } from "./format";

type Action = (
  key: string,
  task: () => Promise<unknown>,
  success: string,
) => Promise<void>;

const defaultSubtitleSettings: SubtitleSettings = {
  enabled: true, style: "yellow_pop", position: "bottom", max_words_per_line: 3,
  font_scale: 1, text_color: "#FFFFFF", highlight_color: "#FFFF00",
  outline_color: "#000000", outline_width: 5,
};

function SubtitleAppearance({ settings, change, compact = false, sample, previewImage }: {
  settings: SubtitleSettings;
  change: (value: SubtitleSettings) => void;
  compact?: boolean;
  sample?: string;
  previewImage?: string;
}) {
  const update = <K extends keyof SubtitleSettings>(key: K, value: SubtitleSettings[K]) => change({ ...settings, [key]: value });
  const words = (sample?.trim() || "ISSO É INCRÍVEL").split(/\s+/).slice(0, settings.max_words_per_line);
  const active = words.length - 1;
  const stroke = settings.outline_width * .45;
  const shadow = stroke ? `${stroke}px ${stroke}px 0 ${settings.outline_color}, ${-stroke}px ${stroke}px 0 ${settings.outline_color}, ${stroke}px ${-stroke}px 0 ${settings.outline_color}, ${-stroke}px ${-stroke}px 0 ${settings.outline_color}, 0 ${stroke + 1}px ${stroke + 2}px #0009` : "none";
  return <div className={compact ? "subtitle-appearance compact" : "subtitle-appearance"}>
    <div className="subtitle-preview-wrap">
      <div className={`subtitle-preview${previewImage ? " with-image" : ""}`} aria-label="Prévia da aparência da legenda" style={previewImage ? { backgroundImage: `linear-gradient(#0002, #0005), url("${previewImage}")` } : undefined}>
        <span className={`subtitle-preview-text ${settings.position}`} style={{ fontSize: `${Math.round(19 * settings.font_scale)}px`, textShadow: shadow }}>
          {words.map((word, index) => <span key={index} className={index === active ? "active-word" : ""} style={{ color: index === active ? settings.highlight_color : settings.text_color }}>{word}{index < active ? " " : ""}</span>)}
        </span>
        <span className="subtitle-preview-label">Prévia do estilo</span>
      </div>
      <small>A prévia mostra cor, tamanho, contorno e posição. O tempo da animação é aplicado ao gerar o vídeo.</small>
    </div>
    <div className="field-row">
      <div className="field"><label>Cor do texto<input aria-label="Cor do texto da legenda" type="color" value={settings.text_color} onChange={(event) => update("text_color", event.target.value.toUpperCase())} /></label></div>
      <div className="field"><label>Cor da palavra ativa<input aria-label="Cor da palavra ativa" type="color" value={settings.highlight_color} onChange={(event) => update("highlight_color", event.target.value.toUpperCase())} /></label></div>
      <div className="field"><label>Cor do contorno<input aria-label="Cor do contorno" type="color" value={settings.outline_color} onChange={(event) => update("outline_color", event.target.value.toUpperCase())} /></label></div>
    </div>
    <div className="field-row">
      <div className="field"><label>Posição<select aria-label="Posição da legenda" value={settings.position} onChange={(event) => update("position", event.target.value as SubtitleSettings["position"])}><option value="bottom">Inferior</option><option value="middle">Centro</option></select></label></div>
      <div className="field"><label>Palavras por linha<input aria-label="Palavras por linha" type="number" min="2" max="6" value={settings.max_words_per_line} onChange={(event) => update("max_words_per_line", Number(event.target.value))} /></label></div>
    </div>
    <div className="field"><label>Tamanho do texto: {Math.round(settings.font_scale * 100)}%<input aria-label="Tamanho do texto" type="range" min="0.7" max="1.5" step="0.1" value={settings.font_scale} onChange={(event) => update("font_scale", Number(event.target.value))} /></label></div>
    <div className="field"><label>Espessura do contorno: {settings.outline_width}<input aria-label="Espessura do contorno" type="range" min="0" max="8" step="1" value={settings.outline_width} onChange={(event) => update("outline_width", Number(event.target.value))} /></label></div>
  </div>;
}

export function StatusPill({ status }: { status: Job["status"] }) {
  return (
    <span className={`status-pill ${status}`}>
      <i /> {statusLabel[status]}
    </span>
  );
}
export function JobProgress({ job }: { job: Job }) {
  const progress = job.status === "completed" ? 1 : job.progress;
  const percent = progress === null ? null : Math.round(progress * 100);
  const etaMinutes = job.eta_s === null ? null : Math.max(1, Math.ceil(job.eta_s / 60));
  const lastUpdate = new Date(job.updated_at).toLocaleTimeString("pt-BR", { hour: "2-digit", minute: "2-digit" });
  return <div className="job-progress" aria-label={`Progresso da tarefa ${job.kind}`}>
    <div className="job-progress-head"><strong>{job.stage === "queued" ? "Aguardando a vez" : job.stage}</strong><b>{percent === null ? "Calculando" : `${percent}%`}</b></div>
    <div className="job-progress-bar" role="progressbar" aria-valuemin={0} aria-valuemax={100} aria-valuenow={percent ?? undefined} aria-label="Progresso total"><span style={{ width: `${percent ?? 0}%` }} /></div>
    <div className="job-progress-foot"><span>{job.status === "queued" ? "O prazo será calculado quando começar" : job.stage_progress !== null ? `${Math.round(job.stage_progress * 100)}% desta etapa` : "Medindo esta etapa"}</span><span>{job.status === "running" ? etaMinutes === null ? "Estimando tempo restante" : `≈ ${etaMinutes} min restantes` : job.status === "completed" ? "Concluída" : ""}</span></div>
    {job.status === "running" && <small>Último sinal do worker às {lastUpdate} · estimativa aproximada, atualizada com o avanço real</small>}
  </div>;
}
export function Empty({
  title,
  detail,
  action,
}: {
  title: string;
  detail: string;
  action?: React.ReactNode;
}) {
  return (
    <div className="empty-state">
      <span>
        <Film size={27} />
      </span>
      <h3>{title}</h3>
      <p>{detail}</p>
      {action}
    </div>
  );
}

export function SourceForm({
  projectId,
  quality,
  height,
  action,
  busy,
}: {
  projectId: string;
  quality: "best" | "up_to_height";
  height: number;
  action: Action;
  busy: string;
}) {
  const [url, setUrl] = useState("");
  const [file, setFile] = useState<File | null>(null);
  return (
    <section className="source-forms">
      <div className="section-top">
        <div>
          <h2>Adicione sua gravação</h2>
          <p>Importe por link ou envie um vídeo do computador.</p>
        </div>
      </div>
      <div className="source-form-grid">
        <form
          className="panel source-form"
          onSubmit={(event) => {
            event.preventDefault();
            if (url.trim())
              void action(
                "download",
                async () => {
                  await endpoints.download(
                    projectId,
                    url.trim(),
                    quality === "best"
                      ? { quality: "best" }
                      : { quality: "up_to_height", max_height: height },
                  );
                  setUrl("");
                },
                "Download adicionado à fila.",
              );
          }}
        >
          <span className="form-symbol">
            <Link2 size={22} />
          </span>
          <h3>Importar por link</h3>
          <p>YouTube, Vimeo, Twitch, Dailymotion ou TikTok.</p>
          <div className="field">
            <label htmlFor="source-url">URL da gravação</label>
            <input
              id="source-url"
              type="url"
              placeholder="Cole o link aqui"
              value={url}
              onChange={(event) => setUrl(event.target.value)}
              required
            />
          </div>
          <button
            type="submit"
            className="button primary"
            disabled={busy === "download"}
          >
            Importar vídeo <ArrowRight size={16} />
          </button>
        </form>
        <form
          className="panel source-form"
          onSubmit={(event) => {
            event.preventDefault();
            if (file)
              void action(
                "upload",
                async () => {
                  await endpoints.upload(projectId, file);
                  setFile(null);
                },
                "Gravação enviada.",
              );
          }}
        >
          <span className="form-symbol violet">
            <CloudUpload size={22} />
          </span>
          <h3>Enviar arquivo</h3>
          <p>MP4, MKV, MOV ou WebM do seu computador.</p>
          <label className="file-zone">
            <CloudUpload size={25} />
            <strong>{file?.name || "Escolher arquivo de vídeo"}</strong>
            <small>
              {file
                ? `${(file.size / 1024 ** 2).toFixed(1)} MB`
                : "Clique para selecionar"}
            </small>
            <input
              type="file"
              accept="video/mp4,video/x-matroska,video/quicktime,video/webm"
              onChange={(event) => setFile(event.target.files?.[0] || null)}
            />
          </label>
          <button
            type="submit"
            className="button outline"
            disabled={!file || busy === "upload"}
          >
            Enviar gravação
          </button>
        </form>
      </div>
    </section>
  );
}

export function ClipCard({
  candidate,
  analysis,
  analysisId,
  exportJob,
  mediaVersions,
  index,
  open,
  remove,
}: {
  candidate: Candidate;
  analysis: Analysis;
  analysisId: string;
  exportJob?: Job;
  mediaVersions?: ClipMediaVersions;
  index: number;
  open: () => void;
  remove: () => void;
}) {
  const id = mediaVersions?.variants.find((variant) => variant.export_id === mediaVersions.selected_export_id && variant.available)?.export_id || exportJob?.result?.export_id as string | undefined;
  const [postCaption, setPostCaption] = useState("");
  const [postHashtags, setPostHashtags] = useState("");
  const [copyState, setCopyState] = useState("");
  useEffect(() => {
    let active = true;
    void endpoints.clipEditorial(analysisId, candidate.candidate_id).then((item) => {
      if (active) { setPostCaption(item.caption); setPostHashtags(item.hashtags || ""); }
    }).catch(() => {});
    const updated = (event: Event) => {
      const value = (event as CustomEvent<{ analysisId: string; candidateId: string; caption: string; hashtags: string }>).detail;
      if (value.analysisId === analysisId && value.candidateId === candidate.candidate_id) { setPostCaption(value.caption); setPostHashtags(value.hashtags); }
    };
    window.addEventListener("clip-editorial-updated", updated);
    return () => { active = false; window.removeEventListener("clip-editorial-updated", updated); };
  }, [analysisId, candidate.candidate_id]);
  async function copyCaption(includeHashtags = false) {
    try { await navigator.clipboard.writeText(postCaption + (includeHashtags && postHashtags ? `\n\n${postHashtags}` : "")); setCopyState(includeHashtags ? "Post copiado!" : "Legenda copiada!"); }
    catch { setCopyState("Não foi possível copiar. Abra os detalhes para selecionar o texto."); }
  }
  return (
    <article className="clip-card">
      <div className="clip-media">
        {id ? (
          <video
            controls
            preload="metadata"
            poster={`/exports/${id}/thumbnail`}
            src={`/exports/${id}/media`}
            aria-label={`Reproduzir corte ${index + 1}`}
          />
        ) : (
          <div className="clip-placeholder">
            <Play size={28} />
            <span>
              {exportJob?.status === "failed"
                ? "Falha ao gerar vídeo"
                : "Preparando vídeo"}
            </span>
          </div>
        )}
        <span className="clip-index">
          CORTE {String(index + 1).padStart(2, "0")}
        </span>
        <span className="duration-label">
          {Math.round(candidate.end_s - candidate.start_s)}s
        </span>
      </div>
      <div className="clip-body">
        <div className="clip-meta">
          <span>
            <Clock3 size={14} /> {timeLabel(candidate.start_s)} –{" "}
            {timeLabel(candidate.end_s)}
          </span>
          <span>#{index + 1} sugestão</span>
        </div>
        <h3>{description(candidate, analysis)}</h3>
        <div className="signal-tags">
          {candidate.features.boundary_signals > 0 && (
            <span>
              <Check size={13} /> Fim de fala
            </span>
          )}
          {candidate.features.visual_changes > 0 && (
            <span>
              <Film size={13} /> Sinal visual
            </span>
          )}
          {candidate.features.continuation_suggested > 0 && (
            <span>
              <Info size={13} /> Continuação
            </span>
          )}
        </div>
        <div className="clip-post-caption">
          <div><strong>Legenda para o post</strong><button type="button" className="button subtle" disabled={!postCaption} onClick={() => void copyCaption()}><Copy size={14} /> Copiar legenda</button></div>
          <p>{postCaption || "Preparando sugestão de legenda…"}</p>
          <small>Sugestão automática baseada na transcrição. Revise antes de publicar.</small>
          {postHashtags && <div className="clip-post-hashtags"><span>{postHashtags}</span><button type="button" className="button subtle" disabled={!postCaption} onClick={() => void copyCaption(true)}>Copiar tudo</button></div>}
          {copyState && <small role="status">{copyState}</small>}
        </div>
        <div className="clip-buttons">
          <button className="button outline" onClick={open}>
            Ver detalhes <ChevronRight size={16} />
          </button>
          <div>
            <a
              className={`icon-button ${id ? "" : "disabled"}`}
              title="Baixar MP4"
              aria-label={`Baixar corte ${index + 1}`}
              href={id ? `/exports/${id}/download` : undefined}
            >
              <ArrowDownToLine size={18} />
            </a>
            <button
              className="icon-button"
              title="Excluir corte"
              aria-label={`Excluir corte ${index + 1}`}
              onClick={remove}
            >
              <Trash2 size={17} />
            </button>
          </div>
        </div>
      </div>
    </article>
  );
}

export function ProjectModal({
  close,
  submit,
  busy,
}: {
  close: () => void;
  submit: (name: string) => void;
  busy: boolean;
}) {
  const [name, setName] = useState("");
  return (
    <div
      className="modal-backdrop"
      onMouseDown={(event) => {
        if (event.target === event.currentTarget) close();
      }}
    >
      <form
        className="modal"
        role="dialog"
        aria-modal="true"
        aria-labelledby="project-title"
        onSubmit={(event) => {
          event.preventDefault();
          if (name.trim()) submit(name.trim());
        }}
      >
        <button
          type="button"
          className="icon-button close-modal"
          aria-label="Fechar"
          onClick={close}
        >
          <X size={19} />
        </button>
        <span className="modal-symbol">
          <FolderPlus size={23} />
        </span>
        <h2 id="project-title">Novo projeto</h2>
        <p>Organize uma gravação e todos os seus cortes.</p>
        <div className="field">
          <label htmlFor="project-name">Nome do projeto</label>
          <input
            id="project-name"
            autoFocus
            placeholder="Ex.: Podcast de sexta-feira"
            maxLength={200}
            value={name}
            onChange={(event) => setName(event.target.value)}
            required
          />
        </div>
        <div className="modal-actions">
          <button type="button" className="button outline" onClick={close}>
            Cancelar
          </button>
          <button type="submit" className="button primary" disabled={busy}>
            Criar projeto
          </button>
        </div>
      </form>
    </div>
  );
}

export function RenameProjectModal({
  name,
  close,
  submit,
  busy,
}: {
  name: string;
  close: () => void;
  submit: (name: string) => void;
  busy: boolean;
}) {
  const [value, setValue] = useState(name);
  return (
    <div
      className="modal-backdrop"
      onMouseDown={(event) => {
        if (event.target === event.currentTarget) close();
      }}
    >
      <form
        className="modal"
        role="dialog"
        aria-modal="true"
        aria-labelledby="rename-title"
        onSubmit={(event) => {
          event.preventDefault();
          if (value.trim()) submit(value.trim());
        }}
      >
        <button
          type="button"
          className="icon-button close-modal"
          aria-label="Fechar"
          onClick={close}
        >
          <X size={19} />
        </button>
        <span className="modal-symbol">
          <FolderPlus size={23} />
        </span>
        <h2 id="rename-title">Renomear projeto</h2>
        <p>
          O histórico, a gravação e os cortes permanecem vinculados ao projeto.
        </p>
        <div className="field">
          <label htmlFor="rename-name">Novo nome</label>
          <input
            id="rename-name"
            autoFocus
            maxLength={200}
            value={value}
            onChange={(event) => setValue(event.target.value)}
            required
          />
        </div>
        <div className="modal-actions">
          <button type="button" className="button outline" onClick={close}>
            Cancelar
          </button>
          <button type="submit" className="button primary" disabled={busy}>
            Salvar nome
          </button>
        </div>
      </form>
    </div>
  );
}

export function AnalysisModal({
  close,
  submit,
  busy,
  assetId,
  profile,
}: {
  close: () => void;
  submit: (data: Record<string, unknown>) => void;
  busy: boolean;
  assetId: string;
  profile?: EditorialProfile;
}) {
  const [mode, setMode] = useState<"range" | "exact">("range");
  const [min, setMin] = useState(25),
    [max, setMax] = useState(65),
    [target, setTarget] = useState(30),
    [count, setCount] = useState(5);
  const [niche, setNiche] = useState("conversa"),
    [instructions, setInstructions] = useState("");
  const [section, setSection] = useState<"video" | "subtitles">("video");
  const [subtitleSettings, setSubtitleSettings] = useState<SubtitleSettings>(defaultSubtitleSettings);
  const [aspect, setAspect] = useState<"source" | "vertical" | "horizontal">("vertical");
  const [removeSilence, setRemoveSilence] = useState(true);
  const [watermarkText, setWatermarkText] = useState(profile?.tiktok_url ? `@${profile.tiktok_url.split('/@')[1]}` : "");
  const [watermarkPosition, setWatermarkPosition] = useState<"top_left" | "top_right" | "bottom_left" | "bottom_right">("bottom_right");
  const [headerEnabled, setHeaderEnabled] = useState(true);
  const [headerName, setHeaderName] = useState(profile?.brand_name || profile?.name || "");
  const [headerTitle, setHeaderTitle] = useState("");
  const valid = (mode === "exact" ? target > 0 : min > 0 && max >= min) && count >= 1 && count <= 20 && (!subtitleSettings.enabled || (subtitleSettings.max_words_per_line >= 2 && subtitleSettings.max_words_per_line <= 6));
  return (
    <div
      className="modal-backdrop"
      onMouseDown={(event) => {
        if (event.target === event.currentTarget) close();
      }}
    >
      <form
        className="modal analysis-modal"
        role="dialog"
        aria-modal="true"
        aria-labelledby="analysis-title"
        onSubmit={(event) => {
          event.preventDefault();
          if (valid)
            submit({
              duration_mode: mode,
              min_s: mode === "range" ? min : null,
              max_s: mode === "range" ? max : null,
              target_s: mode === "exact" ? target : null,
              top_k: count,
              niche,
              instructions: instructions || null,
              subtitle_settings: subtitleSettings,
              video_settings: { aspect, remove_silence: removeSilence, watermark_text: watermarkText.trim(), watermark_position: watermarkPosition, header_enabled: headerEnabled && aspect === "vertical", header_name: headerName.trim(), header_title: headerTitle.trim() },
            });
        }}
      >
        <button
          type="button"
          className="icon-button close-modal"
          aria-label="Fechar"
          onClick={close}
        >
          <X size={19} />
        </button>
        <span className="modal-symbol orange">
          <Sparkles size={23} />
        </span>
        <h2 id="analysis-title">Nova análise</h2>
        <p>Configure os cortes e a legenda que será aplicada ao vídeo exportado.</p>
        <div className="analysis-tabs" role="tablist" aria-label="Configurações da análise">
          <button type="button" role="tab" id="tab-video" aria-controls="panel-video" aria-selected={section === "video"} className={section === "video" ? "selected" : ""} onClick={() => setSection("video")}>Vídeo e seleção</button>
          <button type="button" role="tab" id="tab-subtitles" aria-controls="panel-subtitles" aria-selected={section === "subtitles"} className={section === "subtitles" ? "selected" : ""} onClick={() => setSection("subtitles")}>Legendas <span>{subtitleSettings.enabled ? "Ativas" : "Desligadas"}</span></button>
        </div>
        <div id="panel-video" role="tabpanel" aria-labelledby="tab-video" hidden={section !== "video"}>
        <div className="field">
          <label>Duração dos cortes</label>
          <div className="segmented">
            <button
              type="button"
              className={mode === "range" ? "selected" : ""}
              onClick={() => setMode("range")}
            >
              Faixa flexível
            </button>
            <button
              type="button"
              className={mode === "exact" ? "selected" : ""}
              onClick={() => setMode("exact")}
            >
              Duração exata
            </button>
          </div>
          <small>
            {mode === "range"
              ? "Busca um ponto de encerramento dentro da faixa."
              : "A duração fixa pode interromper uma fala."}
          </small>
        </div>
        {mode === "range" ? (
          <div className="field-row">
            <div className="field">
              <label htmlFor="min">Mínimo (s)</label>
              <input
                id="min"
                type="number"
                min="1"
                value={min}
                onChange={(event) => setMin(Number(event.target.value))}
              />
            </div>
            <div className="field">
              <label htmlFor="max">Máximo (s)</label>
              <input
                id="max"
                type="number"
                min={min}
                value={max}
                onChange={(event) => setMax(Number(event.target.value))}
              />
            </div>
          </div>
        ) : (
          <div className="field">
            <label htmlFor="target">Duração exata (s)</label>
            <input
              id="target"
              type="number"
              min="1"
              value={target}
              onChange={(event) => setTarget(Number(event.target.value))}
            />
          </div>
        )}
        <div className="field-row">
          <div className="field">
            <label htmlFor="count">Sugestões</label>
            <input
              id="count"
              type="number"
              min="1"
              max="20"
              value={count}
              onChange={(event) => setCount(Number(event.target.value))}
            />
          </div>
          <div className="field">
            <label htmlFor="niche">Nicho</label>
            <input
              id="niche"
              value={niche}
              onChange={(event) => setNiche(event.target.value)}
              required
            />
          </div>
        </div>
        <div className="field">
          <label htmlFor="instructions">
            Orientação editorial <small>opcional</small>
          </label>
          <textarea
            id="instructions"
            rows={3}
            placeholder="Ex.: prefira começo e conclusão claros"
            value={instructions}
            onChange={(event) => setInstructions(event.target.value)}
          />
        </div>
        <div className="field-row">
          <div className="field"><label htmlFor="video-aspect">Proporção do vídeo</label><select id="video-aspect" value={aspect} onChange={(event) => setAspect(event.target.value as typeof aspect)}><option value="vertical">Em pé · 9:16</option><option value="horizontal">Deitado · 16:9</option><option value="source">Original</option></select><small>No formato em pé, o enquadramento procura manter os rostos visíveis. Quando não há detecção segura, preserva a imagem inteira.</small></div>
          <div className="field"><label htmlFor="remove-silence">Pausas</label><label className="subtitle-toggle" htmlFor="remove-silence"><span><strong>Remover silêncios</strong><small>Remove pausas de pelo menos 0,8 s e ajusta os horários da legenda. O vídeo final pode ficar mais curto que a duração escolhida.</small></span><input id="remove-silence" type="checkbox" checked={removeSilence} onChange={(event) => setRemoveSilence(event.target.checked)} /></label></div>
        </div>
        <div className="field-row">
          <div className="field"><label htmlFor="watermark-text">Marca d’água em texto</label><input id="watermark-text" maxLength={80} placeholder="Ex.: @meuperfil" value={watermarkText} onChange={(event) => setWatermarkText(event.target.value)} /></div>
          <div className="field"><label htmlFor="watermark-position">Posição</label><select id="watermark-position" value={watermarkPosition} onChange={(event) => setWatermarkPosition(event.target.value as typeof watermarkPosition)}><option value="top_left">Superior esquerda</option><option value="top_right">Superior direita</option><option value="bottom_left">Inferior esquerda</option><option value="bottom_right">Inferior direita</option></select></div>
        </div>
        <div className="field"><label className="subtitle-toggle" htmlFor="header-enabled"><span><strong>Cabeçalho branco do perfil</strong><small>Foto, nome e chamada no alto do vídeo vertical. Desative para deixar somente o vídeo.</small></span><input id="header-enabled" type="checkbox" checked={headerEnabled} disabled={aspect !== "vertical"} onChange={(event) => setHeaderEnabled(event.target.checked)} /></label></div>
        {headerEnabled && aspect === "vertical" && <div className="field-row"><div className="field"><label htmlFor="header-name">Nome no vídeo</label><input id="header-name" maxLength={60} value={headerName} onChange={(event) => setHeaderName(event.target.value)} /></div><div className="field"><label htmlFor="header-title">Chamada para todos os cortes (opcional)</label><input id="header-title" maxLength={120} value={headerTitle} onChange={(event) => setHeaderTitle(event.target.value)} placeholder="Vazio: sugestão específica por corte" /></div></div>}
        {headerEnabled && aspect === "vertical" && <div className="header-preview" aria-label="Prévia do cabeçalho"><div className="header-preview-identity">{profile?.avatar_version ? <img src={`/profiles/${profile.profile_id}/avatar?v=${profile.avatar_version}`} alt="" /> : <span>@</span>}<strong>{headerName || "Nome do perfil"}</strong></div><b>{headerTitle || "Chamada sugerida para cada corte"}</b><small>A chamada automática usa a fala transcrita. Revise cada corte antes da publicação.</small></div>}
        </div>
        <div id="panel-subtitles" role="tabpanel" aria-labelledby="tab-subtitles" hidden={section !== "subtitles"} className="subtitle-settings">
          <label className="subtitle-toggle" htmlFor="subtitle-enabled"><span><strong>Legendas no vídeo</strong><small>Sincronizadas com a fala e incorporadas ao MP4.</small></span><input id="subtitle-enabled" type="checkbox" checked={subtitleSettings.enabled} onChange={(event) => setSubtitleSettings((current) => ({ ...current, enabled: event.target.checked }))} /></label>
          <div className={`subtitle-options${subtitleSettings.enabled ? "" : " disabled"}`} aria-disabled={!subtitleSettings.enabled}>
            <div className="subtitle-style-heading"><strong>Estilo</strong><small>Mais estilos poderão ser adicionados aqui.</small></div>
            <div className="subtitle-style-card" aria-label="Estilo selecionado: Amarelo em destaque"><span className="subtitle-style-swatch">OLHA <em>ISSO!</em></span><span><strong>Amarelo em destaque</strong><small>Palavras amarelas com animação no ritmo da fala.</small></span><Check size={18} /></div>
            <SubtitleAppearance settings={subtitleSettings} change={setSubtitleSettings} previewImage={`/assets/${assetId}/thumbnail`} />
          </div>
        </div>
        {!valid && (
          <small className="field-error">
            Informe um máximo maior ou igual ao mínimo.
          </small>
        )}
        <div className="modal-actions">
          <button type="button" className="button outline" onClick={close}>
            Cancelar
          </button>
          <button
            type="submit"
            className="button primary"
            disabled={!valid || busy}
          >
            <Sparkles size={16} /> Iniciar análise
          </button>
        </div>
      </form>
    </div>
  );
}

export function DetailDrawer({
  candidate,
  analysis,
  analysisId,
  jobs,
  exportJob,
  mediaVersions,
  onMediaVersionChanged,
  close,
  action,
  busy,
}: {
  candidate: Candidate;
  analysis: Analysis;
  analysisId: string;
  jobs: Job[];
  exportJob?: Job;
  mediaVersions?: ClipMediaVersions;
  onMediaVersionChanged: (item: ClipMediaVersions) => void;
  close: () => void;
  action: Action;
  busy: string;
}) {
  const [feedback, setFeedback] = useState<Feedback[]>([]);
  const [caption, setCaption] = useState("");
  const [hashtags, setHashtags] = useState("");
  const [headline, setHeadline] = useState("");
  const [captionCopyState, setCaptionCopyState] = useState("");
  const [editorialStatus, setEditorialStatus] = useState<"draft" | "review" | "approved">("draft");
  const [note, setNote] = useState("");
  const [subtitles, setSubtitles] = useState<ClipSubtitles | null>(null);
  const [subtitleWords, setSubtitleWords] = useState<SubtitleWord[]>([]);
  const [subtitleSettings, setSubtitleSettings] = useState<SubtitleSettings>(defaultSubtitleSettings);
  const [subtitleError, setSubtitleError] = useState("");
  const [subtitlesLoading, setSubtitlesLoading] = useState(true);
  const [start, setStart] = useState(candidate.start_s),
    [end, setEnd] = useState(candidate.end_s);
  useEffect(() => {
    void endpoints
      .feedback(analysisId, candidate.candidate_id)
      .then(setFeedback)
      .catch(() => {});
    void endpoints.clipEditorial(analysisId, candidate.candidate_id).then((item) => {
      setCaption(item.caption); setHashtags(item.hashtags || ""); setHeadline(item.headline || ""); setEditorialStatus(item.status);
    }).catch(() => {});
    let live = true;
    void endpoints.clipSubtitles(analysisId, candidate.candidate_id).then((item) => {
      if (!live) return;
      setSubtitles(item); setSubtitleWords(item.words.map((word) => ({ ...word })));
      setSubtitleSettings({ ...defaultSubtitleSettings, ...item.settings, enabled: true });
      setSubtitleError("");
    }).catch((error: unknown) => {
      if (live) setSubtitleError(error instanceof Error ? error.message : "Não foi possível carregar as legendas.");
    }).finally(() => { if (live) setSubtitlesLoading(false); });
    return () => { live = false; };
  }, [analysisId, candidate.candidate_id]);
  const subtitlesValid = subtitleSettings.max_words_per_line >= 2 && subtitleSettings.max_words_per_line <= 6 && subtitleWords.length > 0 && subtitleWords.every((word, index) =>
    word.text.trim().length > 0 && Number.isFinite(word.start_s) && Number.isFinite(word.end_s) &&
    word.start_s >= candidate.start_s && word.end_s <= candidate.end_s && word.end_s > word.start_s &&
    (index === 0 || word.start_s >= subtitleWords[index - 1].end_s),
  );
  function changeSubtitleWord(index: number, field: keyof SubtitleWord, value: string) {
    setSubtitleWords((items) => items.map((word, wordIndex) => wordIndex === index ? {
      ...word, [field]: field === "text" ? value : Number(value),
    } : word));
  }
  function addSubtitleWord(afterIndex: number) {
    setSubtitleWords((items) => {
      if (items.length === 0) {
        if (candidate.end_s - candidate.start_s < 0.02) return items;
        return [{ start_s: candidate.start_s, end_s: Math.min(candidate.end_s, Math.round((candidate.start_s + 0.6) * 100) / 100), text: "" }];
      }
      const current = items[afterIndex];
      const next = items[afterIndex + 1];
      const availableEnd = next?.start_s ?? candidate.end_s;
      let newStart = current.end_s;
      let newEnd = Math.min(availableEnd, Math.round((newStart + 0.6) * 100) / 100);
      const result = items.map((word) => ({ ...word }));
      if (newEnd - newStart < 0.02) {
        if (current.end_s - current.start_s < 0.04) return items;
        newStart = Math.round(((current.start_s + current.end_s) / 2) * 100) / 100;
        newEnd = current.end_s;
        result[afterIndex].end_s = newStart;
      }
      result.splice(afterIndex + 1, 0, { start_s: newStart, end_s: newEnd, text: "" });
      return result;
    });
  }
  const id = mediaVersions?.variants.find((variant) => variant.export_id === mediaVersions.selected_export_id && variant.available)?.export_id || exportJob?.result?.export_id as string | undefined;
  const [versionBusy, setVersionBusy] = useState("");
  const [versionError, setVersionError] = useState("");
  const originalVersion = mediaVersions?.variants.find((variant) => variant.kind === "original" && variant.available);
  async function selectVersion(exportId: string) {
    setVersionBusy(exportId); setVersionError("");
    try { onMediaVersionChanged(await endpoints.selectMediaVersion(analysisId, candidate.candidate_id, exportId)); }
    catch (error) { setVersionError(error instanceof Error ? error.message : "Não foi possível escolher a versão."); }
    finally { setVersionBusy(""); }
  }
  async function deleteVersion(exportId: string) {
    if (!window.confirm("Excluir somente este MP4 legendado da aplicação? O vídeo publicado no TikTok não será apagado.")) return;
    setVersionBusy(exportId); setVersionError("");
    try { onMediaVersionChanged(await endpoints.deleteMediaVersion(analysisId, candidate.candidate_id, exportId)); }
    catch (error) { setVersionError(error instanceof Error ? error.message : "Não foi possível remover esta versão."); }
    finally { setVersionBusy(""); }
  }
  const evidence = [
    ...analysis.evidence.transcript,
    ...analysis.evidence.visual_events,
    ...analysis.evidence.audio_events,
  ].filter((item) => candidate.evidence_ids.includes(item.evidence_id));
  const revisions = jobs.filter(
    (job) =>
      job.kind === "export" &&
      job.payload.revision_id &&
      !job.payload.auto &&
      job.payload.candidate_id === candidate.candidate_id,
  );
  return (
    <div
      className="drawer-backdrop"
      onMouseDown={(event) => {
        if (event.target === event.currentTarget) close();
      }}
    >
      <aside
        className="drawer"
        role="dialog"
        aria-modal="true"
        aria-labelledby="detail-title"
      >
        <div className="drawer-top">
          <div>
            <span className="eyebrow">DETALHES DO CORTE</span>
            <h2 id="detail-title">Revise esta sugestão</h2>
          </div>
          <button
            className="icon-button"
            aria-label="Fechar detalhes"
            onClick={close}
          >
            <X size={20} />
          </button>
        </div>
        <div className="drawer-scroll">
          <div className="drawer-video">
            {id ? (
              <video
                key={id}
                controls
                poster={`/exports/${id}/thumbnail`}
                src={`/exports/${id}/media`}
              />
            ) : (
              <span>Vídeo em processamento</span>
            )}
          </div>
          <div className="drawer-intro">
            <h3>{description(candidate, analysis)}</h3>
            <p>
              <Clock3 size={15} /> {timeLabel(candidate.start_s)} –{" "}
              {timeLabel(candidate.end_s)} ·{" "}
              {(candidate.end_s - candidate.start_s).toFixed(1)} s
            </p>
          </div>
          <section className="drawer-section">
            <h4>Preparação do clipe</h4>
            <label htmlFor="clip-headline">Chamada no cabeçalho do vídeo</label>
            <input id="clip-headline" aria-label="Chamada no cabeçalho do vídeo" maxLength={120} value={headline} onChange={(event) => setHeadline(event.target.value)} placeholder="Uma frase curta sobre este momento" />
            <small>Revise a sugestão antes de exportar. Após salvar, gere uma nova versão do vídeo para aplicar a mudança.</small>
            <p>Sugestão baseada na transcrição automática. Revise antes de postar: palavras reconhecidas podem estar erradas. Este texto acompanha o post e não é gravado sobre o vídeo.</p>
            <textarea aria-label="Legenda da publicação" rows={4} maxLength={2200} value={caption} onChange={(event) => setCaption(event.target.value)} placeholder="Legenda para publicar este corte" />
            <button className="button outline" type="button" disabled={!caption} onClick={() => void navigator.clipboard.writeText(caption).then(() => setCaptionCopyState("Legenda copiada!"), () => setCaptionCopyState("Não foi possível copiar; selecione o texto acima."))}><Copy size={15} /> Copiar legenda</button>
            <label htmlFor="clip-hashtags">Hashtags sugeridas</label>
            <input id="clip-hashtags" aria-label="Hashtags sugeridas" maxLength={300} value={hashtags} onChange={(event) => setHashtags(event.target.value)} placeholder="#Cortes #Criador #Assunto" />
            <button className="button outline" type="button" disabled={!caption && !hashtags} onClick={() => void navigator.clipboard.writeText([caption, hashtags].filter(Boolean).join("\n\n")).then(() => setCaptionCopyState("Legenda e hashtags copiadas!"), () => setCaptionCopyState("Não foi possível copiar; selecione os campos acima."))}><Copy size={15} /> Copiar post completo</button>
            {captionCopyState && <small role="status">{captionCopyState}</small>}
            <select aria-label="Estado do corte" value={editorialStatus} onChange={(event) => setEditorialStatus(event.target.value as typeof editorialStatus)}><option value="draft">Rascunho</option><option value="review">Em revisão</option><option value="approved">Aprovado</option></select>
            <button className="button primary" disabled={busy !== ""} onClick={() => void action("clip-editorial", async () => { const saved = await endpoints.saveClipEditorial({ analysis_id: analysisId, candidate_id: candidate.candidate_id, caption, hashtags, headline, status: editorialStatus }); window.dispatchEvent(new CustomEvent("clip-editorial-updated", { detail: { analysisId, candidateId: candidate.candidate_id, caption: saved.caption, hashtags: saved.hashtags } })); return saved; }, "Preparação do clipe salva.")}>Salvar preparação</button>
          </section>
          <section className="drawer-section subtitle-editor">
            <h4>Legendas no vídeo</h4>
            <p>O original fica guardado. Escolha uma versão para prévia, download e publicação. Corrigir as palavras gera outro MP4 sem substituir os anteriores. Para um som sem fala, remova a palavra sugerida ou escreva uma marcação como “(risos)” depois de conferir o vídeo.</p>
            {mediaVersions && mediaVersions.variants.length > 0 && <div className="subtitle-version-list">
              {mediaVersions.variants.map((variant, index) => <div className={`subtitle-version-row ${variant.export_id === mediaVersions.selected_export_id ? "active" : ""}`} key={variant.export_id}>
                <div><strong>{variant.kind === "original" ? "Original sem legenda" : `Legenda ${mediaVersions.variants.slice(0, index + 1).filter((item) => item.kind === "captioned").length}`}</strong><small>{variant.available ? new Date(variant.created_at).toLocaleString("pt-BR") : "Arquivo indisponível"}{variant.export_id === mediaVersions.selected_export_id ? " · Em uso" : ""}</small></div>
                <div className="subtitle-version-actions">
                  <button className="button outline" disabled={!variant.available || versionBusy !== "" || variant.export_id === mediaVersions.selected_export_id} onClick={() => void selectVersion(variant.export_id)}>{variant.export_id === mediaVersions.selected_export_id ? "Selecionado" : "Usar versão"}</button>
                  {variant.available && <a className="button outline" href={`/exports/${variant.export_id}/download`}>Baixar</a>}
                  {variant.kind === "captioned" && <button className="button subtle" disabled={versionBusy !== ""} onClick={() => void deleteVersion(variant.export_id)}>Excluir local</button>}
                </div>
              </div>)}
              {originalVersion && mediaVersions.selected_export_id !== originalVersion.export_id && <button className="button outline" disabled={versionBusy !== ""} onClick={() => void selectVersion(originalVersion.export_id)}>Voltar ao vídeo sem legenda</button>}
            </div>}
            {versionError && <p className="subtitle-editor-error" role="alert">{versionError}</p>}
            {subtitlesLoading && <small>Carregando palavras sincronizadas…</small>}
            {!subtitlesLoading && subtitleError && <p className="subtitle-editor-error">{subtitleError}</p>}
            {!subtitlesLoading && subtitles && (subtitles.suppressed_ranges?.length || 0) > 0 && <p className="subtitle-editor-error" role="status">Esta análise contém {subtitles.suppressed_ranges!.length} trecho(s) com texto repetitivo. Novas legendas automáticas omitem esses intervalos; versões antigas já gravadas continuam como estavam. Revise as palavras ou gere uma nova análise.</p>}
            {!subtitlesLoading && !subtitleError && subtitles && !subtitles.enabled && <p>Este corte ainda não tem legendas no vídeo. Revise as palavras abaixo e ative o estilo amarelo sem analisar a live novamente.</p>}
            {subtitles && !subtitleError && !subtitlesLoading && <>
              <SubtitleAppearance settings={subtitleSettings} change={setSubtitleSettings} compact sample={subtitleWords.slice(0, 4).map((word) => word.text).join(" ")} previewImage={id ? `/exports/${id}/thumbnail` : undefined} />
              {subtitleWords.length === 0 ? <div className="subtitle-empty"><small>Não há palavras sincronizadas disponíveis para este corte.</small><button className="button outline" onClick={() => addSubtitleWord(-1)}><Plus size={15} /> Adicionar primeira palavra</button></div> : <>
                <div className="subtitle-word-heading"><span>Palavra</span><span>Início (s)</span><span>Fim (s)</span><span>Ações</span></div>
                <div className="subtitle-word-list">{subtitleWords.map((word, index) => <div className="subtitle-word-row" key={index}><input aria-label={`Palavra ${index + 1}`} value={word.text} onChange={(event) => changeSubtitleWord(index, "text", event.target.value)} /><input aria-label={`Início da palavra ${index + 1} em segundos`} type="number" min={candidate.start_s} max={candidate.end_s} step="0.01" value={word.start_s} onChange={(event) => changeSubtitleWord(index, "start_s", event.target.value)} /><input aria-label={`Fim da palavra ${index + 1} em segundos`} type="number" min={candidate.start_s} max={candidate.end_s} step="0.01" value={word.end_s} onChange={(event) => changeSubtitleWord(index, "end_s", event.target.value)} /><div className="subtitle-word-actions"><button type="button" title="Adicionar palavra depois" aria-label={`Adicionar palavra após ${index + 1}`} onClick={() => addSubtitleWord(index)}><Plus size={15} /></button><button type="button" title="Remover palavra" aria-label={`Remover palavra ${index + 1}`} onClick={() => setSubtitleWords((items) => items.filter((_, wordIndex) => wordIndex !== index))}><Trash2 size={14} /></button></div></div>)}</div>
                {!subtitlesValid && <small className="subtitle-editor-error">Preencha todas as palavras e mantenha os tempos em ordem, sem sobreposição, dentro do corte.</small>}
                <button className="button primary" disabled={busy !== "" || !subtitlesValid} onClick={() => void action("subtitle-revision", async () => {
                  await endpoints.saveClipSubtitles(analysisId, candidate.candidate_id, subtitleWords.map((word) => ({ ...word, text: word.text.trim() })), subtitleSettings);
                  setSubtitles(await endpoints.clipSubtitles(analysisId, candidate.candidate_id));
                }, subtitles.enabled ? "Correções enviadas para gerar um novo MP4." : "Legendas ativadas. O novo MP4 está em processamento.")}>{subtitles.enabled ? "Aplicar correções e gerar vídeo" : "Ativar legendas neste corte"}</button>
              </>}
            </>}
          </section>
          <section className="drawer-section">
            <h4>
              <Sparkles size={17} /> Por que foi sugerido
            </h4>
            <ul>
              {candidate.reasons.map((reason, index) => (
                <li key={index}>{reason}</li>
              ))}
            </ul>
            <small>
              Prioridade interna: {candidate.rank_score.toFixed(2)}. Não é
              chance de viralizar.
            </small>
          </section>
          <section className="drawer-section">
            <h4>
              <Info size={17} /> Evidências com horário
            </h4>
            {evidence.slice(0, 12).map((item) => (
              <div className="evidence-row" key={item.evidence_id}>
                <span>{timeLabel(item.start_s)}</span>
                <p>{item.observation}</p>
              </div>
            ))}
            {evidence.length > 12 && (
              <small>Mais {evidence.length - 12} evidências registradas.</small>
            )}
          </section>
          {candidate.limitations.length > 0 && (
            <section className="drawer-section">
              <h4>
                <Info size={17} /> Pontos de atenção
              </h4>
              {candidate.limitations.map((item, index) => (
                <p className="limitation" key={index}>
                  {item}
                </p>
              ))}
            </section>
          )}
          <section className="drawer-section">
            <h4>
              <Scissors size={17} /> Ajustar limites
            </h4>
            <p>Horários no vídeo original. Uma revisão gera outro MP4.</p>
            <div className="field-row">
              <div className="field">
                <label htmlFor="start">Início (s)</label>
                <input
                  id="start"
                  type="number"
                  min="0"
                  step="0.01"
                  value={start}
                  onChange={(event) => setStart(Number(event.target.value))}
                />
              </div>
              <div className="field">
                <label htmlFor="end">Fim (s)</label>
                <input
                  id="end"
                  type="number"
                  min="0.01"
                  step="0.01"
                  value={end}
                  onChange={(event) => setEnd(Number(event.target.value))}
                />
              </div>
            </div>
            <button
              className="button outline"
              disabled={
                busy === "revision" ||
                end <= start ||
                end > analysis.asset.duration_s
              }
              onClick={() =>
                void action(
                  "revision",
                  async () => {
                    const revision = await endpoints.revision(
                      analysisId,
                      candidate.candidate_id,
                      start,
                      end,
                      null,
                    );
                    await endpoints.exportRevision(revision.revision_id);
                  },
                  "Revisão enviada para exportação.",
                )
              }
            >
              <Scissors size={16} /> Gerar revisão
            </button>
            {revisions.map((job) => (
              <p className="revision-item" key={job.job_id}>
                {statusLabel[job.status]}{" "}
                {Boolean(job.result?.export_id) && (
                  <a
                    href={`/exports/${String(job.result?.export_id)}/download`}
                  >
                    Baixar revisão
                  </a>
                )}
              </p>
            ))}
          </section>
          <section className="drawer-section">
            <h4>
              <ThumbsUp size={17} /> Sua avaliação
            </h4>
            <p>O feedback fica registrado e não inicia treinamento.</p>
            <textarea
              rows={2}
              maxLength={1000}
              value={note}
              onChange={(event) => setNote(event.target.value)}
              placeholder="O que funcionou ou precisa melhorar?"
            />
            <div className="feedback-buttons">
              <button
                className="button outline"
                disabled={busy === "feedback"}
                onClick={() =>
                  void action(
                    "feedback",
                    async () => {
                      await endpoints.sendFeedback(
                        analysisId,
                        candidate.candidate_id,
                        "useful",
                        note,
                      );
                      setFeedback(
                        await endpoints.feedback(
                          analysisId,
                          candidate.candidate_id,
                        ),
                      );
                      setNote("");
                    },
                    "Feedback registrado.",
                  )
                }
              >
                <ThumbsUp size={16} /> Útil
              </button>
              <button
                className="button outline"
                disabled={busy === "feedback"}
                onClick={() =>
                  void action(
                    "feedback",
                    async () => {
                      await endpoints.sendFeedback(
                        analysisId,
                        candidate.candidate_id,
                        "not_useful",
                        note,
                      );
                      setFeedback(
                        await endpoints.feedback(
                          analysisId,
                          candidate.candidate_id,
                        ),
                      );
                      setNote("");
                    },
                    "Feedback registrado.",
                  )
                }
              >
                <ThumbsDown size={16} /> Não útil
              </button>
            </div>
            {feedback.length > 0 && (
              <small>
                {feedback.length} avaliação(ões) · última:{" "}
                {feedback.at(-1)?.rating === "useful" ? "útil" : "não útil"}
              </small>
            )}
          </section>
          <small className="drawer-version">
            Modelo: {candidate.versions.model_version} · Regras:{" "}
            {candidate.versions.rules_version}
          </small>
        </div>
        <div className="drawer-bottom">
          {id ? (
            <a className="button primary" href={`/exports/${id}/download`}>
              <ArrowDownToLine size={16} /> Baixar MP4
            </a>
          ) : (
            <button className="button primary" disabled>
              Vídeo em processamento
            </button>
          )}
          <button className="button outline" onClick={close}>
            Fechar
          </button>
        </div>
      </aside>
    </div>
  );
}
