import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import {
  Activity,
  BarChart3,
  ChevronRight,
  CircleHelp,
  FolderClosed,
  House,
  Menu,
  Plus,
  RefreshCw,
  Scissors,
  Settings2,
  Trash2,
  Users,
  X,
} from "lucide-react";
import { endpoints } from "./api";
import { PublicationsPage } from "./PublicationsPage";
import { TikTokConnections } from "./TikTokConnections";
import type { Analysis, Candidate, ClipMediaVersions, EditorialProfile, Job, Project, TikTokAccount } from "./types";
import {
  AnalysisModal,
  ClipCard,
  DetailDrawer,
  JobProgress,
  Empty,
  ProjectModal,
  RenameProjectModal,
  SourceForm,
  StatusPill,
} from "./components";
import { dateLabel, timeLabel } from "./format";
import "./App.css";

type Page = "accounts" | "overview" | "studio" | "projects" | "results" | "settings";
type Quality = "best" | "up_to_height";
type LiveClip = {
  analysisId: string;
  analysis: Analysis;
  candidate: Candidate;
  exportJob?: Job;
};

function ProfileBranding({ profile, action, busy }: { profile: EditorialProfile; action: (key: string, task: () => Promise<unknown>, success: string) => Promise<void>; busy: string }) {
  const [url, setUrl] = useState(profile.tiktok_url || "");
  const [name, setName] = useState(profile.brand_name || "");
  return <form className="panel profile-branding" onSubmit={(event) => { event.preventDefault(); void action("profile-branding", () => endpoints.saveProfileBranding(profile.profile_id, url, name), "Identidade do vídeo salva."); }}>
    <div><strong>Identidade dos vídeos</strong><small>O cabeçalho branco usa estes dados por padrão. Você pode mudar o nome e a chamada ao criar cada análise ou revisar cada corte.</small></div>
    <div className="profile-branding-fields">
      <label>Link do seu perfil TikTok<input type="url" placeholder="https://www.tiktok.com/@seuperfil" value={url} onChange={(event) => setUrl(event.target.value)} /></label>
      <label>Nome exibido<input maxLength={60} placeholder="Preenchido pelo @ do link se vazio" value={name} onChange={(event) => setName(event.target.value)} /></label>
      <label>Foto do perfil<input type="file" accept="image/png,image/jpeg,image/webp" onChange={(event) => { const file = event.target.files?.[0]; if (file) void action("profile-avatar", () => endpoints.uploadProfileAvatar(profile.profile_id, file), "Foto do perfil salva."); }} /><small>O link público sugere o nome; envie a foto aqui para usar no vídeo.</small></label>
      {profile.avatar_version > 0 && <img className="profile-branding-avatar" src={`/profiles/${profile.profile_id}/avatar?v=${profile.avatar_version}`} alt="Foto usada no cabeçalho" />}
    </div>
    <button className="button outline" type="submit" disabled={busy !== ""}>Salvar identidade</button>
  </form>;
}
const sections = [
  { id: "accounts" as Page, label: "Perfis", icon: Users },
  { id: "projects" as Page, label: "Lives", icon: FolderClosed },
  { id: "studio" as Page, label: "Estúdio de cortes", icon: Scissors },
  { id: "results" as Page, label: "Publicar e resultados", icon: BarChart3 },
  { id: "overview" as Page, label: "Visão geral", icon: House },
  { id: "settings" as Page, label: "Configurações", icon: Settings2 },
];

export default function App() {
  const [page, setPage] = useState<Page>(
    sessionStorage.getItem("clip-active-profile") && !new URLSearchParams(window.location.search).has("tiktok") ? "projects" : "accounts",
  );
  const [linkedAccounts, setLinkedAccounts] = useState<TikTokAccount[]>([]);
  const [profiles, setProfiles] = useState<EditorialProfile[]>([]);
  const [profilesLoaded, setProfilesLoaded] = useState(false);
  const [selectedProfileId, setSelectedProfileId] = useState<string | null>(
    new URLSearchParams(window.location.search).has("tiktok") ? null : sessionStorage.getItem("clip-active-profile"),
  );
  const [profileName, setProfileName] = useState("");
  const [profilePlatforms, setProfilePlatforms] = useState<"tiktok" | "instagram" | "both">("tiktok");
  const [profileAccountId, setProfileAccountId] = useState("");
  const [moveTargets, setMoveTargets] = useState<Record<string, string>>({});
  const [projects, setProjects] = useState<Project[]>([]);
  const [activeId, setActiveId] = useState(
    localStorage.getItem("clip-active-project") || "",
  );
  const [jobs, setJobs] = useState<Job[]>([]);
  const [mediaVersions, setMediaVersions] = useState<ClipMediaVersions[]>([]);
  const [allJobs, setAllJobs] = useState<Job[]>([]);
  const [analysisId, setAnalysisId] = useState("");
  const [library, setLibrary] = useState<
    Record<string, { analysis: Analysis; discarded: string[] }>
  >({});
  const [selected, setSelected] = useState<LiveClip | null>(null);
  const [modal, setModal] = useState<"project" | "analysis" | null>(null);
  const [deleteCandidate, setDeleteCandidate] = useState<LiveClip | null>(null);
  const [deleteProject, setDeleteProject] = useState<Project | null>(null);
  const [deleteProfile, setDeleteProfile] = useState<EditorialProfile | null>(null);
  const [renameProject, setRenameProject] = useState<Project | null>(null);
  const [busy, setBusy] = useState("");
  const [message, setMessage] = useState<{
    type: "success" | "error";
    text: string;
  } | null>(null);
  const [search, setSearch] = useState("");
  const [filter, setFilter] = useState("all");
  const [quality, setQuality] = useState<Quality>(
    (localStorage.getItem("clip-quality") as Quality) || "best",
  );
  const [height, setHeight] = useState(
    Number(localStorage.getItem("clip-height")) || 1080,
  );
  const [menuOpen, setMenuOpen] = useState(false);
  const preparedAnalyses = useRef(new Set<string>());
  const folderProjects = useMemo(() => projects.filter((project) => selectedProfileId === "unassigned"
    ? !project.profile_id
    : selectedProfileId !== null && project.profile_id === selectedProfileId), [projects, selectedProfileId]);
  const scopedProjectIds = new Set(folderProjects.map((project) => project.project_id));
  const scopedJobs = allJobs.filter((job) => scopedProjectIds.has(job.project_id));
  const active = folderProjects.find((project) => project.project_id === activeId);
  const activeProjectId = active?.project_id;
  const selectedProfile = profiles.find((item) => item.profile_id === selectedProfileId);
  const currentFolderProject = active;
  const analyses = useMemo(
    () =>
      jobs
        .filter((job) => job.kind === "analysis")
        .sort((a, b) => b.created_at.localeCompare(a.created_at)),
    [jobs],
  );
  const current = analyses.find((job) => job.job_id === analysisId);
  const analysis = library[analysisId]?.analysis || null;
  const completedIds = analyses
    .filter((job) => job.status === "completed")
    .map((job) => job.job_id)
    .join("|");
  const completedExportIds = jobs.filter((job) => job.kind === "export" && job.status === "completed").map((job) => job.job_id).join("|");
  useEffect(() => {
    if (!activeProjectId) return;
    let mounted = true;
    void endpoints.mediaVersions(activeProjectId).then((items) => { if (mounted) setMediaVersions(items); }).catch(() => {});
    return () => { mounted = false; };
  }, [activeProjectId, completedExportIds]);
  const updateMediaVersion = (item: ClipMediaVersions) => setMediaVersions((items) => [...items.filter((current) => current.analysis_id !== item.analysis_id || current.candidate_id !== item.candidate_id), item]);
  const versionFor = (analysisId: string, candidateId: string) => mediaVersions.find((item) => item.analysis_id === analysisId && item.candidate_id === candidateId);
  const pending = jobs.filter(
    (job) => job.status === "running" || job.status === "queued",
  ).length;

  const loadProjects = useCallback(async () => {
    const items = await endpoints.projects();
    setProjects(items);
    const scoped = items.filter((item) => selectedProfileId === "unassigned"
      ? !item.profile_id
      : selectedProfileId !== null && item.profile_id === selectedProfileId);
    setActiveId((id) => scoped.some((item) => item.project_id === id)
      ? id : scoped[0]?.project_id || "");
    return items;
  }, [selectedProfileId]);
  const loadJobs = useCallback(
    async (id: string) => setJobs(await endpoints.jobs(id)),
    [],
  );
  const refresh = useCallback(async () => {
    try {
      const items = await loadProjects();
      setProfiles(await endpoints.profiles()); setProfilesLoaded(true);
      if (activeId && items.some((item) => item.project_id === activeId &&
        (selectedProfileId === "unassigned" ? !item.profile_id : item.profile_id === selectedProfileId))) await loadJobs(activeId);
      const scoped = items.filter((item) => selectedProfileId === "unassigned" ? !item.profile_id : item.profile_id === selectedProfileId);
      setAllJobs(
        (
          await Promise.all(
            scoped.map((item) => endpoints.jobs(item.project_id)),
          )
        ).flat(),
      );
    } catch (error) {
      setMessage({
        type: "error",
        text:
          error instanceof Error ? error.message : "Falha ao atualizar dados.",
      });
    }
  }, [activeId, loadJobs, loadProjects, selectedProfileId]);
  async function action(
    key: string,
    task: () => Promise<unknown>,
    success: string,
  ) {
    setBusy(key);
    setMessage(null);
    try {
      await task();
      setMessage({ type: "success", text: success });
      await refresh();
    } catch (error) {
      setMessage({
        type: "error",
        text: error instanceof Error ? error.message : "A operação falhou.",
      });
    } finally {
      setBusy("");
    }
  }
  function chooseProject(id: string) {
    const project = folderProjects.find((item) => item.project_id === id);
    if (!project) return;
    setActiveId(id);
    setAnalysisId("");
    setSelected(null);
    setPage("studio");
    setMenuOpen(false);
  }

  function chooseProfile(profile: EditorialProfile) {
    sessionStorage.setItem("clip-active-profile", profile.profile_id);
    setSelectedProfileId(profile.profile_id);
    setActiveId(projects.find((item) => item.profile_id === profile.profile_id)?.project_id || "");
    setPage("projects");
    setMenuOpen(false);
  }

  function chooseUnassigned() {
    sessionStorage.setItem("clip-active-profile", "unassigned");
    setSelectedProfileId("unassigned");
    setActiveId(projects.find((item) => !item.profile_id)?.project_id || "");
    setPage("projects");
    setMenuOpen(false);
  }

  function leaveProfile() {
    sessionStorage.removeItem("clip-active-profile");
    setSelectedProfileId(null);
    setActiveId(""); setJobs([]); setAllJobs([]); setLibrary({}); setSelected(null);
    setAnalysisId(""); setModal(null); setDeleteCandidate(null); setDeleteProject(null);
    setDeleteProfile(null); setRenameProject(null); setMessage(null);
    setPage("accounts"); setMenuOpen(false);
  }

  async function removeProject(project: Project) {
    setBusy("delete-project"); setMessage(null);
    try {
      await endpoints.deleteProject(project.project_id);
      setDeleteProject(null);
      setActiveId(""); setJobs([]); setLibrary({}); setSelected(null);
      setPage("projects");
      await loadProjects();
      setMessage({ type: "success", text: "Live e arquivos locais removidos. Publicações no TikTok permanecem intactas." });
    } catch (error) {
      setMessage({ type: "error", text: error instanceof Error ? error.message : "Falha ao excluir a live." });
    } finally { setBusy(""); }
  }

  useEffect(() => {
    void loadProjects().catch((error) =>
      setMessage({ type: "error", text: error.message }),
    );
  }, [loadProjects]);
  useEffect(() => {
    void endpoints.tiktokAccounts().then(setLinkedAccounts).catch(() => {});
    void endpoints.profiles().then((items) => { setProfiles(items); setProfilesLoaded(true); }).catch(() => {});
  }, []);
  useEffect(() => {
    if (profilesLoaded && selectedProfileId && selectedProfileId !== "unassigned" && !profiles.some((item) => item.profile_id === selectedProfileId)) leaveProfile();
  }, [profilesLoaded, profiles, selectedProfileId]);
  useEffect(() => {
    if (!selectedProfileId || window.location.protocol !== "https:") return;
    const sessionKey = `clip-tiktok-session-sync:${selectedProfileId}`;
    if (sessionStorage.getItem(sessionKey)) return;
    void endpoints.tiktokStatus().then((status) => {
      if (!status.connected) return;
      const requestId = crypto.randomUUID();
      sessionStorage.setItem(sessionKey, requestId);
      void endpoints.collectSession(requestId, "authorized_session_start", selectedProfileId).catch(() => {
        sessionStorage.removeItem(sessionKey);
      });
    }).catch(() => {});
  }, [selectedProfileId]);
  useEffect(() => {
    if (!activeProjectId) { setJobs([]); setLibrary({}); return; }
    localStorage.setItem("clip-active-project", activeId);
    setJobs([]);
    setLibrary({});
    void loadJobs(activeId).catch((error) =>
      setMessage({ type: "error", text: error.message }),
    );
    const timer = setInterval(
      () => void loadJobs(activeId).catch(() => {}),
      6000,
    );
    return () => clearInterval(timer);
  }, [activeId, activeProjectId, loadJobs]);
  useEffect(() => {
    if (!analyses.length) {
      setAnalysisId("");
      return;
    }
    if (!analyses.some((job) => job.job_id === analysisId))
      setAnalysisId(
        (analyses.find((job) => job.status === "completed") || analyses[0])
          .job_id,
      );
  }, [analyses, analysisId]);
  useEffect(() => {
    if (!completedIds) return;
    let mounted = true;
    const ids = completedIds.split("|");
    void Promise.all(
      ids.map(async (id) => {
        const [result, discarded] = await Promise.all([
          endpoints.analysis(id),
          endpoints.discarded(id),
        ]);
        if (!preparedAnalyses.current.has(id)) {
          preparedAnalyses.current.add(id);
          void endpoints
            .ensureExports(id)
            .then(() => {
              if (activeId) void loadJobs(activeId);
            })
            .catch(() => {});
        }
        return [id, { analysis: result, discarded }] as const;
      }),
    )
      .then((entries) => {
        if (mounted) setLibrary(Object.fromEntries(entries));
      })
      .catch((error) => setMessage({ type: "error", text: error.message }));
    return () => {
      mounted = false;
    };
  }, [completedIds, activeId, loadJobs]);
  useEffect(() => {
    if (page === "overview" || page === "projects" || page === "results")
      void Promise.all(folderProjects.map((item) => endpoints.jobs(item.project_id)))
        .then((items) => setAllJobs(items.flat()))
        .catch(() => {});
  }, [page, folderProjects]);

  const liveClips: LiveClip[] = Object.entries(library)
    .flatMap(([id, entry]) =>
      entry.analysis.candidates
        .filter(
          (candidate) => !entry.discarded.includes(candidate.candidate_id),
        )
        .map((candidate) => ({
          analysisId: id,
          analysis: entry.analysis,
          candidate,
          exportJob: (() => {
            const matching = jobs.filter((job) =>
              job.kind === "export" &&
              job.payload.auto === true &&
              job.payload.analysis_id === id &&
              job.payload.candidate_id === candidate.candidate_id,
            );
            return matching.find((job) => job.status === "completed") || matching[0];
          })(),
        })),
    )
    .sort(
      (a, b) =>
        a.candidate.start_s - b.candidate.start_s ||
        a.analysisId.localeCompare(b.analysisId),
    );
  const visible = liveClips
    .filter(
      (clip) =>
        filter === "all" ||
        (filter === "ready"
          ? clip.exportJob?.status === "completed"
          : clip.exportJob?.status !== "completed"),
    )
    .filter(
      (clip) =>
        !search ||
        clip.candidate.reasons
          .join(" ")
          .toLowerCase()
          .includes(search.toLowerCase()) ||
        timeLabel(clip.candidate.start_s).includes(search),
    );
  const completedExports = jobs.filter(
    (job) => job.kind === "export" && job.status === "completed",
  ).length;
  const completedAnalyses = analyses.filter(
    (job) => job.status === "completed",
  ).length;
  const currentTotal = liveClips.length;
  return (
    <div className="app-shell">
      <aside className={`sidebar ${menuOpen ? "open" : ""}`}>
        <div className="brand">
          <span className="brand-symbol">
            <Scissors size={20} />
          </span>
          <span>
            <strong>
              Cortes<span>IA</span>
            </strong>
            <small>Creative workspace</small>
          </span>
          <button
            className="icon-button mobile-only"
            aria-label="Fechar menu"
            onClick={() => setMenuOpen(false)}
          >
            <X size={18} />
          </button>
        </div>
        <div className="sidebar-label">{selectedProfileId ? "PERFIL ATIVO" : "ESCOLHA UM PERFIL"}</div>
        {selectedProfileId && <div className="sidebar-profile"><span className="account-folder-avatar">{(selectedProfile?.name || "Sem perfil").slice(0, 2).toUpperCase()}</span><span><strong>{selectedProfile?.name || "Lives sem perfil"}</strong><small>Espaço de trabalho atual</small></span></div>}
        {selectedProfileId && <nav aria-label="Navegação principal">
          {sections.filter((item) => item.id !== "accounts").map((item) => (
            <button
              key={item.id}
              className={`nav-link ${page === item.id ? "active" : ""}`}
              onClick={() => {
                setPage(item.id);
                setSearch("");
                setMenuOpen(false);
              }}
            >
              <item.icon size={18} />
              {item.label}
              {item.id === "studio" && pending > 0 && (
                <span className="nav-badge">{pending}</span>
              )}
            </button>
          ))}
        </nav>}
        {selectedProfileId && <button className="sidebar-switch" onClick={leaveProfile}><Users size={17}/> Trocar perfil</button>}
        {selectedProfileId && <div className="sidebar-separator" />}
        {selectedProfileId && <>
        <div className="sidebar-heading">
          <span>LIVES DESTE PERFIL</span>
          <button
            title="Criar projeto"
            aria-label="Criar projeto"
            onClick={() => setModal("project")}
          >
            <Plus size={16} />
          </button>
        </div>
        <div className="recent-projects">
          {folderProjects.slice(0, 5).map((project) => (
            <button
              key={project.project_id}
              onClick={() => chooseProject(project.project_id)}
              className={project.project_id === activeId ? "chosen" : ""}
            >
              <span>{project.name.slice(0, 1).toUpperCase()}</span>
              {project.name}
            </button>
          ))}
        </div>
        </>}
        <div className="sidebar-footer">
          <div className="local-state">
            <i /> Operando localmente
          </div>
          <div className="account">
            <span className="account-avatar">JC</span>
            <div>
              <strong>Meu espaço</strong>
              <small>Administrador local</small>
            </div>
          </div>
        </div>
      </aside>
      {menuOpen && (
        <button
          className="mobile-overlay"
          aria-label="Fechar menu"
          onClick={() => setMenuOpen(false)}
        />
      )}
      <div className="main-shell">
        <header className="topbar">
          <div className="breadcrumbs">
            <button
              className="icon-button mobile-only"
              aria-label="Abrir menu"
              onClick={() => setMenuOpen(true)}
            >
              <Menu size={21} />
            </button>
            {selectedProfileId ? <><button className="breadcrumb-link" onClick={() => setPage("projects")}>{selectedProfile?.name || "Lives sem perfil"}</button><ChevronRight size={15} /><strong>{sections.find((item) => item.id === page)?.label}</strong></> : <strong>Escolha seu perfil</strong>}
          </div>
          <div className="topbar-tools">
            {selectedProfileId && <button className="button outline topbar-switch" onClick={leaveProfile}><Users size={16}/> Trocar perfil</button>}
            <button
              className="icon-button"
              title="Documentação da API"
              onClick={() => window.open("/docs", "_blank")}
            >
              <CircleHelp size={19} />
            </button>
            <span className="top-avatar">JC</span>
          </div>
        </header>
        <main className="content">
          {message && (
            <div role="alert" className={`notice ${message.type}`}>
              {message.text}
              <button
                aria-label="Fechar aviso"
                onClick={() => setMessage(null)}
              >
                <X size={16} />
              </button>
            </div>
          )}
          {!selectedProfileId && page === "accounts" && <>
            <PageTitle eyebrow="ESPAÇOS DE TRABALHO" title="Escolha um perfil" description="Depois de entrar, o painel mostra somente as lives e atividades daquele perfil." />
            <div className="account-folder-grid">
              {profiles.map((profile) => <div className="account-folder-wrap" key={profile.profile_id}><button className="account-folder-card panel" onClick={() => chooseProfile(profile)}>
                <span className="account-folder-avatar">{profile.name.slice(0, 2).toUpperCase()}</span>
                <span><strong>{profile.name}</strong><small>{profile.platforms.join(" + ").toUpperCase()} · {projects.filter((project) => project.profile_id === profile.profile_id).length} live(s) · {profile.account_open_id ? "TikTok vinculado" : "Sem conta vinculada"}</small></span><ChevronRight size={19}/>
              </button><button className="icon-button account-folder-remove" title={`Excluir perfil ${profile.name}`} aria-label={`Excluir perfil ${profile.name}`} onClick={() => setDeleteProfile(profile)}><Trash2 size={17}/></button></div>)}
              <button className="account-folder-card panel" onClick={chooseUnassigned}><span className="account-folder-avatar muted"><FolderClosed size={23}/></span><span><strong>Lives sem perfil</strong><small>{projects.filter((project) => !project.profile_id).length} live(s) antigas para organizar</small></span><ChevronRight size={19}/></button>
            </div>
            {projects.some((project) => !project.profile_id) && profiles.length > 0 && <section className="panel profile-organize"><h2>Organizar lives antigas</h2><p>As lives sem perfil ficam separadas. Se quiser, mova uma delas para o perfil correto antes de entrar.</p>{projects.filter((project) => !project.profile_id).map((project) => <div className="profile-organize-row" key={project.project_id}><strong>{project.name}</strong><select aria-label={`Destino da live ${project.name}`} value={moveTargets[project.project_id] || ""} onChange={(event) => setMoveTargets((current) => ({ ...current, [project.project_id]: event.target.value }))}><option value="">Escolha o destino</option>{profiles.map((profile) => <option key={profile.profile_id} value={profile.profile_id}>{profile.name}</option>)}</select><button className="button outline" disabled={!moveTargets[project.project_id] || busy !== ""} onClick={() => void action("move-project", async () => { await endpoints.assignProjectProfile(project.project_id, moveTargets[project.project_id]); setMoveTargets((current) => { const next = { ...current }; delete next[project.project_id]; return next; }); }, "Live movida para o perfil.")}>Mover live</button></div>)}</section>}
            <form className="panel profile-create" onSubmit={(event) => { event.preventDefault(); void action("create-profile", async () => { await endpoints.createProfile(profileName.trim(), profilePlatforms === "both" ? ["tiktok", "instagram"] : [profilePlatforms], profilePlatforms === "instagram" ? null : profileAccountId || null); setProfileName(""); }, "Perfil criado."); }}>
              <h3>Criar perfil editorial</h3><p>Organize várias lives sob uma identidade. A conexão com Instagram ainda não está disponível.</p>
              <div className="profile-create-fields"><input aria-label="Nome do perfil" placeholder="Nome do perfil" value={profileName} onChange={(event) => setProfileName(event.target.value)} maxLength={200} required />
              <select aria-label="Plataformas do perfil" value={profilePlatforms} onChange={(event) => setProfilePlatforms(event.target.value as typeof profilePlatforms)}><option value="tiktok">TikTok</option><option value="instagram">Instagram</option><option value="both">TikTok + Instagram</option></select>
              {profilePlatforms !== "instagram" && <select aria-label="Conta TikTok vinculada" value={profileAccountId} onChange={(event) => setProfileAccountId(event.target.value)}><option value="">Vincular depois</option>{linkedAccounts.map((item) => <option key={item.open_id} value={item.open_id}>{item.display_name}</option>)}</select>}
              <button className="button primary" disabled={busy !== ""}><Plus size={16}/> Criar perfil</button></div>
            </form>
            <TikTokConnections onAccounts={setLinkedAccounts} />
          </>}
          {selectedProfileId && page === "results" && <PublicationsPage key={selectedProfileId + ':' + (currentFolderProject?.project_id || '')} jobs={currentFolderProject ? jobs : []} project={currentFolderProject} profileId={selectedProfileId} onAccounts={setLinkedAccounts} />}
          {selectedProfileId && page === "overview" && (
            <>
              <PageTitle
                eyebrow="SEU PAINEL"
                title="Visão geral"
                description="Acompanhe seus projetos e avance de onde parou."
                action={
                  <button
                    className="button primary"
                    onClick={() => setModal("project")}
                  >
                    <Plus size={17} /> Nova live
                  </button>
                }
              />
              <div className="metric-grid">
                <Metric
                  icon={FolderClosed}
                  label="Projetos"
                  count={folderProjects.length}
                  color="blue"
                />
                <Metric
                  icon={Scissors}
                  label="Cortes prontos"
                  count={
                    scopedJobs.filter(
                      (job) =>
                        job.kind === "export" && job.status === "completed",
                    ).length
                  }
                  color="orange"
                />
                <Metric
                  icon={Activity}
                  label="Análises"
                  count={
                    scopedJobs.filter(
                      (job) =>
                        job.kind === "analysis" && job.status === "completed",
                    ).length
                  }
                  color="violet"
                />
                <Metric
                  icon={RefreshCw}
                  label="Em andamento"
                  count={
                    scopedJobs.filter(
                      (job) =>
                        job.status === "running" || job.status === "queued",
                    ).length
                  }
                  color="green"
                />
              </div>
              <div className="dashboard-grid">
                <section className="panel">
                  <div className="section-top">
                    <div>
                      <h2>Seus projetos</h2>
                      <p>Escolha uma gravação para continuar.</p>
                    </div>
                    <button
                      className="text-link"
                      onClick={() => setPage("projects")}
                    >
                      Ver todos <ChevronRight size={16} />
                    </button>
                  </div>
                  {folderProjects.length ? (
                    folderProjects.slice(0, 4).map((project) => (
                      <button
                        className="project-row"
                        key={project.project_id}
                        onClick={() => chooseProject(project.project_id)}
                      >
                        <span className="row-icon">
                          <FolderClosed size={21} />
                        </span>
                        <span>
                          <strong>{project.name}</strong>
                          <small>
                            {project.asset_id
                              ? "Gravação disponível"
                              : "Aguardando gravação"}
                          </small>
                        </span>
                        <ChevronRight size={17} />
                      </button>
                    ))
                  ) : (
                    <Empty
                      title="Nenhum projeto ainda"
                      detail="Crie um projeto para organizar sua primeira gravação."
                    />
                  )}
                </section>
                <section className="next-card">
                  <span className="next-icon">
                    <Scissors size={24} />
                  </span>
                  <span className="eyebrow">PRÓXIMO PASSO</span>
                  <h2>
                    {active?.asset_id
                      ? "Transforme sua gravação em cortes"
                      : "Comece com uma gravação"}
                  </h2>
                  <p>
                    {active?.asset_id
                      ? "Abra o estúdio, configure a duração e revise cada sugestão em vídeo."
                      : "Adicione um link ou envie um vídeo para iniciar a análise."}
                  </p>
                  <button
                    className="button dark"
                    onClick={() => setPage("studio")}
                  >
                    Abrir estúdio <ChevronRight size={17} />
                  </button>
                  <Scissors className="next-art" size={128} strokeWidth={1} />
                </section>
              </div>
              <section className="panel activity-panel">
                <div className="section-top">
                  <div>
                    <h2>Atividade recente</h2>
                    <p>Últimas tarefas do seu workspace.</p>
                  </div>
                  <button
                    className="icon-button"
                    title="Atualizar"
                    onClick={() => void refresh()}
                  >
                    <RefreshCw size={17} />
                  </button>
                </div>
                {scopedJobs
                  .slice()
                  .sort((a, b) => b.created_at.localeCompare(a.created_at))
                  .slice(0, 6)
                  .map((job) => (
                    <div className="activity-row" key={job.job_id}>
                      <span className="row-icon">
                        <Activity size={18} />
                      </span>
                      <div>
                        <strong>
                          {job.kind === "analysis"
                            ? "Análise"
                            : job.kind === "export"
                              ? "Exportação de corte"
                              : "Download"}
                        </strong>
                        <small>
                          {
                            projects.find(
                              (item) => item.project_id === job.project_id,
                            )?.name
                          }{" "}
                          · {dateLabel(job.created_at)}
                        </small>
                        {(job.status === "queued" || job.status === "running") && <JobProgress job={job} />}
                      </div>
                      <StatusPill status={job.status} />
                      {(job.status === "queued" || job.status === "running") && <button className="button subtle" disabled={busy !== ""} onClick={() => void action(`cancel-${job.job_id}`, () => endpoints.cancelJob(job.job_id), "Tarefa cancelada.")}>Cancelar</button>}
                    </div>
                  ))}
                {!scopedJobs.length && (
                  <p className="muted">Nenhuma atividade registrada.</p>
                )}
              </section>
            </>
          )}
          {selectedProfileId && page === "projects" && (
            <>
              <PageTitle
                eyebrow="BIBLIOTECA"
                title={selectedProfile?.name || "Lives sem perfil"}
                description="Abra uma live para ver os cortes e configurar a publicação."
                action={
                  <button
                    className="button primary"
                    onClick={() => setModal("project")}
                  >
                    <Plus size={17} /> Novo projeto
                  </button>
                }
              />
              {selectedProfile && <div className="panel profile-connection"><div><strong>Contas do perfil</strong><small>{selectedProfile.platforms.map((item) => item === "tiktok" ? "TikTok" : "Instagram").join(" + ")}{selectedProfile.platforms.includes("instagram") ? " · conexão Instagram indisponível por enquanto" : ""}</small></div>{selectedProfile.platforms.includes("tiktok") && <select aria-label="Vincular TikTok ao perfil" value={selectedProfile.account_open_id || ""} onChange={(event) => { const openId = event.target.value; void action("profile-account", () => endpoints.updateProfile(selectedProfile.profile_id, selectedProfile.name, selectedProfile.platforms, openId || null), "Conta do perfil atualizada."); }}><option value="">TikTok não vinculado</option>{linkedAccounts.map((item) => <option value={item.open_id} key={item.open_id}>{item.display_name}</option>)}</select>}</div>}
              {selectedProfile && <ProfileBranding key={`${selectedProfile.profile_id}:${selectedProfile.tiktok_url}:${selectedProfile.brand_name}`} profile={selectedProfile} action={action} busy={busy} />}
              <div className="project-grid">
                {folderProjects.map((project) => (
                  <article className="project-card" key={project.project_id}>
                    <div className="project-cover">
                      {project.asset_id && <img src={`/assets/${project.asset_id}/thumbnail`} alt={`Capa da gravação ${project.name}`} loading="lazy" />}
                      <FolderClosed size={42} strokeWidth={1.2} />
                      <span>
                        {project.asset_id
                          ? "GRAVAÇÃO DISPONÍVEL"
                          : "SEM GRAVAÇÃO"}
                      </span>
                    </div>
                    <div className="project-card-body">
                      <h3>{project.name}</h3>
                      <p>Criado em {dateLabel(project.created_at)}</p>
                      <div className="project-stats">
                        <span>
                          <Scissors size={15} />{" "}
                          {
                            scopedJobs.filter(
                              (job) =>
                                job.project_id === project.project_id &&
                                job.kind === "export" &&
                                job.status === "completed",
                            ).length
                          }{" "}
                          cortes
                        </span>
                        <span>
                          <Activity size={15} />{" "}
                          {
                            scopedJobs.filter(
                              (job) =>
                                job.project_id === project.project_id &&
                                job.kind === "analysis",
                            ).length
                          }{" "}
                          análises
                        </span>
                      </div>
                      <div className="project-card-actions">
                        <small className="project-linked-account">{project.account_open_id ? `Conta TikTok: ${linkedAccounts.find((item) => item.open_id === project.account_open_id)?.display_name || "vinculada"}` : "Sem conta TikTok vinculada"}</small>
                        <button
                          className="button outline"
                          onClick={() => setRenameProject(project)}
                        >
                          Renomear
                        </button>
                        <button
                          className="button outline"
                          onClick={() => chooseProject(project.project_id)}
                        >
                          Abrir live <ChevronRight size={16} />
                        </button>
                        <button className="button danger" onClick={() => setDeleteProject(project)}><Trash2 size={16}/> Excluir live</button>
                      </div>
                    </div>
                  </article>
                ))}
                {!folderProjects.length && (
                  <Empty
                    title="Sua biblioteca começa aqui"
                    detail="Crie um projeto para adicionar uma gravação."
                  />
                )}
              </div>
            </>
          )}
          {selectedProfileId && page === "studio" && (
            <>
              <PageTitle
                eyebrow={`ESTÚDIO / ${active?.name || "PROJETO"}`}
                title={active?.name || "Escolha um projeto"}
                description="Da gravação aos cortes: analise, revise e exporte em um só lugar."
                action={
                  <div className="title-actions">
                    <button className="button outline" onClick={() => setPage("results")}><BarChart3 size={16}/> Publicar e resultados</button>
                    {active && <button className="button danger" onClick={() => setDeleteProject(active)}><Trash2 size={16}/> Excluir live</button>}
                    <button
                      className="button outline"
                      onClick={() => void refresh()}
                    >
                      <RefreshCw size={16} /> Atualizar
                    </button>
                    {active?.asset_id && (
                      <button
                        className="button primary"
                        onClick={() => setModal("analysis")}
                      >
                        <Plus size={17} /> Nova análise
                      </button>
                    )}
                  </div>
                }
              />
              {active ? (
                <>
                  {!active.account_open_id && <div className="notice">Esta live ainda não tem uma conta TikTok. Abra “Publicar e resultados” para ver as opções bloqueadas e vincule uma conta na pasta da live.</div>}
                  <div className="studio-summary">
                    <div className="source-summary panel">
                      <span className="row-icon large">
                        <FolderClosed size={26} />
                      </span>
                      <div>
                        <span className="eyebrow">GRAVAÇÃO DE ORIGEM</span>
                        <strong>
                          {active.asset_id
                            ? active.name
                            : "Nenhuma gravação adicionada"}
                        </strong>
                        <small>
                          {active.asset_id
                            ? `Pronta para análise${analysis ? ` · ${timeLabel(analysis.asset.duration_s)}` : ""}`
                            : "Adicione um link ou arquivo para começar"}
                        </small>
                      </div>
                      <span
                        className={`source-pill ${active.asset_id ? "ready" : ""}`}
                      >
                        {active.asset_id ? "Pronta" : "Pendente"}
                      </span>
                    </div>
                    <div className="summary-counts panel">
                      <div>
                        <strong>{analyses.length}</strong>
                        <small>análises</small>
                      </div>
                      <div>
                        <strong>{completedExports}</strong>
                        <small>arquivos no projeto</small>
                      </div>
                      <div>
                        <strong>{pending}</strong>
                        <small>em andamento ou na fila</small>
                      </div>
                    </div>
                  </div>
                  {!active.asset_id && (
                    <SourceForm
                      projectId={active.project_id}
                      quality={quality}
                      height={height}
                      action={action}
                      busy={busy}
                    />
                  )}
                  {jobs.some((job) => job.status === "queued" || job.status === "running") && <section className="panel job-monitor" aria-live="polite"><div className="section-top"><div><h2>Acompanhamento das tarefas</h2><p>Os tempos são aproximações calculadas a partir do avanço medido. A lista atualiza automaticamente.</p></div><button className="button outline" onClick={() => void refresh()}><RefreshCw size={16}/> Atualizar</button></div>{jobs.filter((job) => job.status === "queued" || job.status === "running").map((job) => <div className="job-monitor-row" key={job.job_id}><div className="job-monitor-main"><div className="job-monitor-title"><strong>{job.kind === "download" ? "Importação da gravação" : job.kind === "analysis" ? "Análise e seleção de cortes" : "Exportação de corte"}</strong><StatusPill status={job.status} /></div><JobProgress job={job} /></div><button className="button outline" disabled={busy !== ""} onClick={() => void action(`cancel-${job.job_id}`, () => endpoints.cancelJob(job.job_id), "Tarefa cancelada.")}>Cancelar</button></div>)}</section>}
                  {analyses.length > 0 && (
                    <div className="analysis-toolbar panel">
                      <span>
                        <Activity size={18} /> Biblioteca da live
                      </span>
                      <span>
                        {currentTotal} cortes · {completedAnalyses} análises
                        concluídas
                      </span>
                    </div>
                  )}
                  {current?.status === "failed" && (
                    <div className="notice error">
                      {current.error || "Análise falhou."}
                    </div>
                  )}
                  {Object.keys(library).length > 0 && (
                    <>
                      <div className="results-heading">
                        <div>
                          <span className="eyebrow">
                            TODOS OS CORTES DA LIVE
                          </span>
                          <h2>
                            Cortes da gravação <span>{currentTotal}</span>
                          </h2>
                          <p>
                            {visible.length === currentTotal
                              ? `Exibindo os ${currentTotal} cortes desta live. Role para ver todos.`
                              : `Exibindo ${visible.length} de ${currentTotal} cortes. Limpe a busca ou selecione Todos para ver os demais.`}
                          </p>
                        </div>
                        <div className="result-filters">
                          <input
                            aria-label="Buscar cortes"
                            placeholder="Buscar horário ou motivo"
                            value={search}
                            onChange={(event) => setSearch(event.target.value)}
                          />
                          <select
                            aria-label="Filtrar cortes"
                            value={filter}
                            onChange={(event) => setFilter(event.target.value)}
                          >
                            <option value="all">Todos</option>
                            <option value="ready">Prontos</option>
                            <option value="pending">Em processamento</option>
                          </select>
                        </div>
                      </div>
                      <div className="clip-grid">
                        {visible.map((clip, index) => (
                          <ClipCard
                            key={`${clip.analysisId}-${clip.candidate.candidate_id}`}
                            candidate={clip.candidate}
                            analysis={clip.analysis}
                            analysisId={clip.analysisId}
                            index={index}
                            exportJob={clip.exportJob}
                            mediaVersions={versionFor(clip.analysisId, clip.candidate.candidate_id)}
                            open={() => setSelected(clip)}
                            remove={() => setDeleteCandidate(clip)}
                          />
                        ))}
                        {!visible.length && (
                          <Empty
                            title="Nenhum corte neste filtro"
                            detail="Experimente outro termo ou selecione Todos."
                          />
                        )}
                      </div>
                    </>
                  )}
                  {active.asset_id && !analyses.length && (
                    <Empty
                      title="Gravação pronta para análise"
                      detail="Configure a duração e gere suas primeiras sugestões."
                      action={
                        <button
                          className="button primary"
                          onClick={() => setModal("analysis")}
                        >
                          Criar análise
                        </button>
                      }
                    />
                  )}
                </>
              ) : (
                <Empty
                  title="Escolha um projeto"
                  detail="Crie ou selecione um projeto para iniciar."
                />
              )}
            </>
          )}
          {selectedProfileId && page === "settings" && (
            <>
              <PageTitle
                eyebrow="PREFERÊNCIAS"
                title="Configurações"
                description="Controle como novos downloads são preparados no seu navegador."
              />
              <div className="settings-grid">
                <section className="panel settings-card">
                  <h2>Qualidade de download</h2>
                  <p>A preferência vale para novos downloads nesta sessão.</p>
                  <label
                    className={`quality-option ${quality === "best" ? "selected" : ""}`}
                  >
                    <input
                      type="radio"
                      name="quality"
                      checked={quality === "best"}
                      onChange={() => {
                        setQuality("best");
                        localStorage.setItem("clip-quality", "best");
                      }}
                    />
                    <span>
                      <strong>Melhor disponível</strong>
                      <small>
                        Vídeo e áudio na melhor qualidade oferecida pela fonte.
                      </small>
                    </span>
                  </label>
                  <label
                    className={`quality-option ${quality === "up_to_height" ? "selected" : ""}`}
                  >
                    <input
                      type="radio"
                      name="quality"
                      checked={quality === "up_to_height"}
                      onChange={() => {
                        setQuality("up_to_height");
                        localStorage.setItem("clip-quality", "up_to_height");
                      }}
                    />
                    <span>
                      <strong>Limitar resolução</strong>
                      <small>
                        Define a altura máxima dos próximos downloads.
                      </small>
                    </span>
                  </label>
                  {quality === "up_to_height" && (
                    <div className="field">
                      <label htmlFor="height">Altura máxima</label>
                      <select
                        id="height"
                        value={height}
                        onChange={(event) => {
                          setHeight(Number(event.target.value));
                          localStorage.setItem(
                            "clip-height",
                            event.target.value,
                          );
                        }}
                      >
                        <option value="720">720p</option>
                        <option value="1080">1080p</option>
                        <option value="1440">1440p</option>
                        <option value="2160">2160p</option>
                      </select>
                    </div>
                  )}
                </section>
                <section className="panel settings-card">
                  <h2>Processamento local</h2>
                  <p>Os modelos e os arquivos permanecem no seu computador.</p>
                  <div className="setting-row">
                    <span>Motor de seleção</span>
                    <strong>Fala + sinais observáveis</strong>
                  </div>
                  <div className="setting-row">
                    <span>Modelo de fala</span>
                    <strong>Definido no worker</strong>
                  </div>
                  <div className="setting-row">
                    <span>Assinatura</span>
                    <strong>Não necessária</strong>
                  </div>
                  <small>
                    Alterar o modelo ou dispositivo do worker exige reiniciar os
                    serviços.
                  </small>
                </section>
              </div>
            </>
          )}
        </main>
      </div>
      {selectedProfileId && modal === "project" && (
        <ProjectModal
          close={() => setModal(null)}
          submit={(name) =>
            void action(
              "project",
              async () => {
                const project = await endpoints.createProject(name, selectedProfileId === "unassigned" ? null : selectedProfileId);
                setActiveId(project.project_id);
                setPage("studio");
                setModal(null);
              },
              "Projeto criado.",
            )
          }
          busy={busy === "project"}
        />
      )}
      {renameProject && (
        <RenameProjectModal
          name={renameProject.name}
          close={() => setRenameProject(null)}
          submit={(name) =>
            void action(
              "rename",
              async () => {
                await endpoints.renameProject(renameProject.project_id, name);
                setRenameProject(null);
              },
              "Projeto renomeado.",
            )
          }
          busy={busy === "rename"}
        />
      )}
      {modal === "analysis" && active?.asset_id && (
        <AnalysisModal
          assetId={active.asset_id}
          profile={selectedProfile}
          close={() => setModal(null)}
          submit={(payload) =>
            void action(
              "analysis",
              async () => {
                const job = await endpoints.analyze(active.project_id, {
                  ...payload,
                  asset_id: active.asset_id,
                });
                setAnalysisId(job.job_id);
                setModal(null);
              },
              "Análise enviada para a fila.",
            )
          }
          busy={busy === "analysis"}
        />
      )}
      {selected && (
        <DetailDrawer
          candidate={selected.candidate}
          analysis={selected.analysis}
          analysisId={selected.analysisId}
          jobs={jobs}
          exportJob={liveClips.find((clip) => clip.analysisId === selected.analysisId &&
            clip.candidate.candidate_id === selected.candidate.candidate_id)?.exportJob || selected.exportJob}
          mediaVersions={versionFor(selected.analysisId, selected.candidate.candidate_id)}
          onMediaVersionChanged={updateMediaVersion}
          close={() => setSelected(null)}
          action={action}
          busy={busy}
        />
      )}
      {deleteCandidate && (
        <div className="modal-backdrop">
          <div role="dialog" aria-modal="true" className="modal confirm-modal">
            <h2>Excluir este corte?</h2>
            <p>
              O MP4 automático será removido. A gravação, a análise e o feedback
              permanecem salvos. Se você já publicou esse corte no TikTok, o vídeo
              publicado e suas métricas não serão apagados.
            </p>
            <div className="modal-actions">
              <button
                className="button outline"
                onClick={() => setDeleteCandidate(null)}
              >
                Cancelar
              </button>
              <button
                className="button danger"
                disabled={busy === "delete"}
                onClick={() =>
                  void action(
                    "delete",
                    async () => {
                      await endpoints.discard(
                        deleteCandidate.analysisId,
                        deleteCandidate.candidate.candidate_id,
                      );
                      const ids = await endpoints.discarded(
                        deleteCandidate.analysisId,
                      );
                      setLibrary((current) => ({
                        ...current,
                        [deleteCandidate.analysisId]: {
                          ...current[deleteCandidate.analysisId],
                          discarded: ids,
                        },
                      }));
                      setDeleteCandidate(null);
                    },
                    "Corte removido da galeria.",
                  )
                }
              >
                Excluir corte
              </button>
            </div>
          </div>
        </div>
      )}
      {deleteProject && <div className="modal-backdrop"><div role="dialog" aria-modal="true" className="modal confirm-modal" aria-labelledby="delete-project-title">
        <h2 id="delete-project-title">Excluir a live “{deleteProject.name}”?</h2>
        <p>O projeto desaparecerá do painel e os vídeos, cortes e arquivos de processamento locais desta live serão removidos. Publicações feitas no TikTok não serão apagadas; seus vínculos e métricas continuam guardados no histórico interno.</p>
        <p>Se houver tarefa local em andamento, cancele antes de excluir. Publicações agendadas precisam ser canceladas em “Publicar e resultados”.</p>
        <div className="modal-actions"><button className="button outline" disabled={busy !== ""} onClick={() => setDeleteProject(null)}>Voltar</button>{allJobs.some((job) => job.project_id === deleteProject.project_id && (job.status === "queued" || job.status === "running")) && <button className="button outline" disabled={busy !== ""} onClick={() => void action("cancel-project-jobs", async () => { for (const job of allJobs.filter((item) => item.project_id === deleteProject.project_id && (item.status === "queued" || item.status === "running"))) await endpoints.cancelJob(job.job_id); }, "Tarefas da live canceladas. Agora você pode excluí-la.")}>Cancelar tarefas desta live</button>}<button className="button danger" disabled={busy !== "" || allJobs.some((job) => job.project_id === deleteProject.project_id && (job.status === "queued" || job.status === "running"))} onClick={() => void removeProject(deleteProject)}>{busy === "delete-project" ? "Excluindo…" : "Excluir live e arquivos locais"}</button></div>
      </div></div>}
      {deleteProfile && <div className="modal-backdrop"><div role="dialog" aria-modal="true" className="modal confirm-modal" aria-labelledby="delete-profile-title"><h2 id="delete-profile-title">Excluir o perfil “{deleteProfile.name}”?</h2><p>Somente o perfil será removido. As lives, vídeos locais e publicações permanecem; as lives aparecerão sem perfil.</p><div className="modal-actions"><button className="button outline" disabled={busy !== ""} onClick={() => setDeleteProfile(null)}>Voltar</button><button className="button danger" disabled={busy !== ""} onClick={() => void action("delete-profile", async () => { await endpoints.deleteProfile(deleteProfile.profile_id); if (selectedProfileId === deleteProfile.profile_id) { setSelectedProfileId(null); setPage("accounts"); } setDeleteProfile(null); }, "Perfil excluído; lives preservadas.")}>Excluir perfil</button></div></div></div>}
    </div>
  );
}

function PageTitle({
  eyebrow,
  title,
  description,
  action,
}: {
  eyebrow: string;
  title: string;
  description: string;
  action?: React.ReactNode;
}) {
  return (
    <div className="page-title">
      <div>
        <span className="eyebrow">{eyebrow}</span>
        <h1>{title}</h1>
        <p>{description}</p>
      </div>
      {action}
    </div>
  );
}
function Metric({
  icon: Icon,
  label,
  count,
  color,
}: {
  icon: typeof House;
  label: string;
  count: number;
  color: string;
}) {
  return (
    <div className="metric panel">
      <span className={`metric-symbol ${color}`}>
        <Icon size={21} />
      </span>
      <div>
        <strong>{count}</strong>
        <small>{label}</small>
      </div>
    </div>
  );
}
