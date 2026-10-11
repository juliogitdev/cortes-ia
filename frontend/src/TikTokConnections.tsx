import { useCallback, useEffect, useState } from "react";
import { Link2, ShieldCheck, Trash2 } from "lucide-react";
import { endpoints } from "./api";
import type { TikTokAccount, TikTokAppStatus } from "./types";

const emptyApp: TikTokAppStatus = {
  configured: false, client_key: "", redirect_uri: "", secret_saved: false,
  request_publish_scope: false,
};

export function TikTokConnections({ onAccounts }: { onAccounts: (items: TikTokAccount[]) => void }) {
  const [app, setApp] = useState<TikTokAppStatus>(emptyApp);
  const [secret, setSecret] = useState("");
  const [accounts, setAccounts] = useState<TikTokAccount[]>([]);
  const [error, setError] = useState("");
  const [message, setMessage] = useState("");
  const [busy, setBusy] = useState(false);
  const [callback] = useState(() => new URLSearchParams(window.location.search).get("tiktok"));

  const reload = useCallback(async () => {
    const [config, linked] = await Promise.all([endpoints.tiktokApp(), endpoints.tiktokAccounts()]);
    setApp({ ...config, redirect_uri: config.redirect_uri || `${window.location.origin}/integrations/tiktok/callback` });
    setAccounts(linked);
    onAccounts(linked);
  }, [onAccounts]);
  useEffect(() => {
    void reload().catch((cause) => setError(String(cause)));
    if (callback) window.history.replaceState({}, "", window.location.pathname);
  }, [reload, callback]);

  async function save(event: React.FormEvent) {
    event.preventDefault(); setBusy(true); setError(""); setMessage("");
    try {
      const updated = await endpoints.saveTikTokApp({ client_key: app.client_key.trim(),
        client_secret: secret, redirect_uri: app.redirect_uri.trim(),
        request_publish_scope: app.request_publish_scope });
      setApp(updated); setSecret(""); setMessage("Configuração salva neste computador.");
    } catch (cause) { setError(cause instanceof Error ? cause.message : "Falha ao salvar configuração."); }
    finally { setBusy(false); }
  }

  async function connect() {
    setBusy(true); setError("");
    try {
      const result = await endpoints.authorizeTikTok();
      window.location.assign(result.url);
    } catch (cause) { setError(cause instanceof Error ? cause.message : "Não foi possível iniciar a autorização."); setBusy(false); }
  }

  async function remove(openId: string) {
    if (!window.confirm("Desvincular esta conta deste computador? As publicações e métricas já registradas serão preservadas.")) return;
    setBusy(true); setError("");
    try { await endpoints.disconnectTikTok(openId); await reload(); setMessage("Conta desvinculada."); }
    catch (cause) { setError(cause instanceof Error ? cause.message : "Não foi possível desvincular a conta."); }
    finally { setBusy(false); }
  }

  return <section className="panel tiktok-connections">
    <div className="section-kicker"><Link2 size={17}/> INTEGRAÇÃO TIKTOK</div>
    <h2>Contas conectadas</h2>
    <p>Configure seu aplicativo do TikTok for Developers e autorize cada perfil pelo próprio TikTok. As credenciais ficam no servidor deste computador.</p>
    {callback === "connected" && <div className="notice success">Conta TikTok vinculada. Confira as permissões abaixo.</div>}
    {callback === "failed" && <div className="notice error">O TikTok não concluiu a vinculação. Confira o domínio, a chave e as permissões aprovadas.</div>}
    {callback === "denied" && <div className="notice error">A autorização foi cancelada no TikTok.</div>}
    {error && <div className="notice error" role="alert">{error}</div>}
    {message && <div className="notice success">{message}</div>}
    <form className="tiktok-config-form" onSubmit={(event) => void save(event)}>
      <div className="results-form-row">
        <label>Chave do aplicativo<input required autoComplete="off" value={app.client_key} onChange={(event) => setApp({ ...app, client_key: event.target.value })} placeholder="Client key" /></label>
        <label>Segredo do aplicativo<input type="password" autoComplete="new-password" required={!app.secret_saved} value={secret} onChange={(event) => setSecret(event.target.value)} placeholder={app.secret_saved ? "Salvo · deixe vazio para manter" : "Client secret"} /></label>
      </div>
      <label>URL de retorno HTTPS<input required type="url" value={app.redirect_uri} onChange={(event) => setApp({ ...app, redirect_uri: event.target.value })} /></label>
      <small>Cadastre exatamente essa URL no Login Kit. Use um domínio HTTPS fixo; o endereço do túnel temporário muda quando ele reinicia.</small>
      <label className="tiktok-scope-option"><input type="checkbox" checked={app.request_publish_scope} onChange={(event) => setApp({ ...app, request_publish_scope: event.target.checked })} /> Pedir também permissão de publicação (`video.publish`) quando seu aplicativo for aprovado</label>
      <div className="tiktok-actions"><button className="button primary" disabled={busy} type="submit">Salvar configuração</button><button className="button outline" disabled={busy || !app.configured} type="button" onClick={() => void connect()}><Link2 size={15}/> Vincular conta do TikTok</button></div>
    </form>
    <div className="tiktok-account-list">
      {!accounts.length && <div className="results-empty">Nenhuma conta autorizada ainda.</div>}
      {accounts.map((item) => <div className="tiktok-account" key={item.open_id}>
        <div><strong>{item.display_name}</strong><small>ID: {item.open_id}</small><small>{item.scopes.includes("video.list") ? "Métricas autorizadas" : "Sem permissão de métricas"} · {item.scopes.includes("video.publish") ? "Publicação autorizada" : "Publicação ainda não autorizada"}</small></div>
        <button className="button subtle" type="button" disabled={busy} onClick={() => void remove(item.open_id)} aria-label={`Desvincular ${item.display_name}`}><Trash2 size={16}/></button>
      </div>)}
    </div>
    <p className="tiktok-security-note"><ShieldCheck size={15}/> O segredo e os tokens não aparecem novamente no painel. Vincular uma conta não publica vídeos.</p>
  </section>;
}
