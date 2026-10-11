"""Painel local: comunica com a API; não carrega modelos."""
import os
import re
import uuid
from html import escape
from collections import Counter
import httpx
import streamlit as st

API = os.environ.get('CLIP_API_URL', 'http://127.0.0.1:8000').rstrip('/')
st.set_page_config(page_title='Cortes IA', layout='wide')
st.markdown('''<style>
  .stApp {background: #f5f7fb; color: #18243a;}
  [data-testid="stSidebar"] {background: #10213a;}
  [data-testid="stSidebar"] * {color: #f4f7ff !important;}
  [data-testid="stSidebar"] input {color: #18243a !important;}
  .block-container {padding-top: 1.5rem; max-width: 1440px;}
  [data-testid="stMetric"] {background: white; border: 1px solid #e3e9f3; border-radius: 14px; padding: 1rem;}
  [data-testid="stVerticalBlockBorderWrapper"] {background: white; border-radius: 16px;}
  .workspace-hero {background: linear-gradient(115deg,#112746,#29446e); color: white;
      border-radius: 20px; padding: 1.5rem 1.8rem; margin-bottom: 1.5rem;}
  .workspace-hero h1 {font-size: 2rem; margin: .25rem 0; color: white;}
  .workspace-hero p {margin: .25rem 0; color: #d4e1f5;}
  .eyebrow {font-size: .78rem; letter-spacing: .12em; font-weight: 700; text-transform: uppercase;}
  div.stButton > button[kind="primary"] {border-radius: 10px; background: #1464d2;}
</style>''', unsafe_allow_html=True)


def clock_time(seconds):
    value = int(seconds)
    return f'{value // 3600:02d}:{value // 60 % 60:02d}:{value % 60:02d}'


def short_description(candidate, result):
    pieces = [item['observation'].strip() for item in result['evidence']['transcript']
              if item['evidence_id'] in candidate['evidence_ids']]
    raw = re.sub(r'\s+', ' ', ' '.join(pieces)).strip()
    words = re.findall(r'\w+', raw.lower())
    if not raw and candidate['features'].get('visual_changes', 0):
        return 'Mudança visual observada; revise o vídeo para identificar o acontecimento.'
    if not raw or len(words) >= 12 and Counter(words).most_common(1)[0][1] / len(words) > .45:
        return 'Trecho com fala; a transcrição não permite um resumo confiável.'
    return ('Fala: ' + raw[:145].rstrip() + ('…' if len(raw) > 145 else ''))


@st.dialog('Detalhes do corte', width='large')
def show_details(analysis_id, candidate, result, description):
    cid = candidate['candidate_id']
    st.write(description)
    st.write(f"**No original:** {clock_time(candidate['start_s'])}–{clock_time(candidate['end_s'])}")
    st.write(f"**Duração sugerida:** {candidate['end_s'] - candidate['start_s']:.1f} s")
    st.write(f"**Prioridade interna:** {candidate['rank_score']:.3f}")
    st.caption('Esta pontuação só ordena candidatos; não é probabilidade de viralizar.')
    st.subheader('Por que foi escolhido')
    for reason in candidate['reasons']:
        st.write('• ' + reason)
    st.subheader('Evidências observadas')
    for item in (result['evidence']['transcript'] + result['evidence']['visual_events'] +
                 result['evidence']['audio_events']):
        if item['evidence_id'] in candidate['evidence_ids']:
            st.write(f"{clock_time(item['start_s'])}–{clock_time(item['end_s'])}: {item['observation']}")
    if candidate['limitations']:
        st.subheader('Limitações')
        for limitation in candidate['limitations']:
            st.caption(limitation)
    st.caption('Modelo: ' + candidate['versions']['model_version'] +
               ' • Regras: ' + candidate['versions']['rules_version'])
    previous = call('GET', f'/analyses/{analysis_id}/candidates/{cid}/feedback')
    if previous is not None and previous.json():
        st.caption(f"Avaliações registradas: {len(previous.json())} • última: " +
                   ('útil' if previous.json()[-1]['rating'] == 'useful' else 'não útil'))
    with st.form('feedback-' + analysis_id + '-' + cid):
        rating = st.radio('Sua avaliação', ['Útil', 'Não útil'], horizontal=True)
        note = st.text_area('Comentário opcional', max_chars=1000)
        if st.form_submit_button('Salvar feedback'):
            response = call('POST', f'/analyses/{analysis_id}/candidates/{cid}/feedback',
                            json={'rating': 'useful' if rating == 'Útil' else 'not_useful', 'note': note})
            if response is not None:
                st.success('Feedback registrado. Isso não inicia treinamento automático.')
    if st.button('Fechar detalhes'):
        st.session_state.pop('details_candidate', None)
        st.rerun()


@st.dialog('Excluir este corte?')
def confirm_delete(analysis_id, candidate_id):
    st.write('O MP4 automático será removido e o corte sairá da galeria. A gravação original, '
             'a análise e o histórico de feedback serão preservados.')
    if st.button('Excluir corte e arquivo', type='primary'):
        response = call('DELETE', f'/analyses/{analysis_id}/candidates/{candidate_id}')
        if response is not None:
            st.session_state.pop('pending_delete', None)
            st.rerun()
    if st.button('Cancelar exclusão'):
        st.session_state.pop('pending_delete', None)
        st.rerun()


def call(method, path, **kwargs):
    try:
        response = httpx.request(method, API + path, timeout=120, **kwargs)
        response.raise_for_status()
        return response
    except httpx.HTTPStatusError as exc:
        try:
            detail = exc.response.json().get('detail', 'Falha na API')
        except ValueError:
            detail = 'Falha na API'
        st.error(str(detail))
    except httpx.RequestError:
        st.error('API indisponível. Inicie a API local conforme as instruções de execução.')
    return None


with st.sidebar:
    st.markdown('## ◼ Cortes IA')
    st.caption('Workspace local de edição')
    page = st.radio('Navegação', ['Estúdio', 'Visão geral', 'Projetos', 'Configurações'],
                    label_visibility='collapsed')
    st.divider()
    st.header('Projetos')
    with st.form('new-project'):
        name = st.text_input('Nome do projeto', value='Minha gravação')
        if st.form_submit_button('Criar projeto'):
            response = call('POST', '/projects', json={'name': name})
            if response is not None:
                st.session_state['active_project'] = response.json()['project_id']
                st.rerun()
    response = call('GET', '/projects')
    projects = response.json() if response is not None else []
    if not projects:
        st.info('Crie um projeto para começar.')
        st.stop()
    ids = [p['project_id'] for p in projects]
    names = {p['project_id']: p['name'] for p in projects}
    active = st.session_state.get('active_project', ids[0])
    project_id = st.selectbox('Projeto', ids, index=ids.index(active) if active in ids else 0,
                              format_func=lambda key: names[key])
    project = next(p for p in projects if p['project_id'] == project_id)

st.markdown('<div class="workspace-hero"><div class="eyebrow">' + escape(page) + '</div><h1>' +
            escape(project['name']) + '</h1><p>Da gravação aos cortes prontos para revisar.</p></div>',
            unsafe_allow_html=True)

if page == 'Visão geral':
    all_jobs = []
    for item in projects:
        response = call('GET', f"/projects/{item['project_id']}/jobs")
        if response is not None:
            all_jobs.extend(response.json())
    counts = {'analysis': 0, 'export': 0, 'download': 0}
    for item in all_jobs:
        if item['status'] == 'completed':
            counts[item['kind']] += 1
    metric_columns = st.columns(4)
    for column, title, value in zip(metric_columns,
                                    ['Projetos', 'Análises concluídas', 'Cortes gerados', 'Downloads'],
                                    [len(projects), counts['analysis'], counts['export'], counts['download']]):
        column.metric(title, value)
    st.subheader('Atividade recente')
    if all_jobs:
        st.dataframe([{'Projeto': names.get(item['project_id'], item['project_id']),
                       'Tipo': item['kind'], 'Estado': item['status'],
                       'Etapa': item['stage'], 'Criado': item['created_at'][:19]}
                      for item in sorted(all_jobs, key=lambda row: row['created_at'], reverse=True)[:20]],
                     hide_index=True, use_container_width=True)
    else:
        st.info('Crie um projeto para começar sua primeira análise.')
    st.stop()

if page == 'Projetos':
    st.subheader('Biblioteca de projetos')
    st.dataframe([{'Projeto': item['name'], 'Gravação': 'Disponível' if item.get('asset_id') else 'Aguardando mídia',
                   'Criado': item['created_at'][:19], 'ID': item['project_id']} for item in projects],
                 hide_index=True, use_container_width=True)
    with st.form('rename-' + project_id):
        new_name = st.text_input('Nome do projeto selecionado', value=project['name'])
        if st.form_submit_button('Renomear projeto'):
            response = call('PATCH', f'/projects/{project_id}', json={'name': new_name})
            if response is not None:
                st.success('Projeto renomeado.')
                st.rerun()
    st.caption('Crie um projeto pela barra lateral; selecione-o e abra o Estúdio para trabalhar nele.')
    st.stop()

if page == 'Configurações':
    st.subheader('Preferências de processamento')
    quality = st.selectbox('Qualidade para novos downloads', ['Melhor disponível', 'Limitar altura'],
                           key='download_quality_preference')
    if quality == 'Limitar altura':
        st.number_input('Altura máxima (pixels)', min_value=144, max_value=4320, value=1080,
                        key='download_height_preference')
    st.info('A preferência vale para novos downloads nesta sessão do painel. O modelo de fala e o '
            'dispositivo são escolhidos ao iniciar o worker local. Alterar o modelo exige reiniciar o worker.')
    st.caption('Jobs em andamento mantêm suas configurações. Conta e assinatura ainda não fazem parte da versão local.')
    st.stop()

st.subheader('Fonte e análise')
with st.expander('Adicionar gravação local', expanded=not bool(project.get('asset_id'))):
    with st.form('upload-' + project_id):
        uploaded = st.file_uploader('Gravação com imagem e áudio', type=['mp4', 'mkv', 'mov', 'webm'])
        if st.form_submit_button('Enviar gravação') and uploaded is not None:
            with st.spinner('Validando a gravação…'):
                response = call('POST', f'/projects/{project_id}/upload',
                                files={'file': (uploaded.name, uploaded.getvalue(), uploaded.type)})
            if response is not None:
                st.session_state.pop('analysis-' + project_id, None)
                st.success(f"Gravação validada: {response.json()['duration_s']:.1f} segundos")
                st.rerun()

if not project.get('asset_id'):
    with st.form('download-form-' + project_id):
        url = st.text_input('Link da gravação (YouTube, Vimeo, Twitch, Dailymotion ou TikTok)')
        st.caption('Melhor qualidade disponível de vídeo e áudio. Uma gravação por projeto.')
        if st.form_submit_button('Baixar vídeo') and url:
            settings = ({'quality': 'up_to_height',
                         'max_height': st.session_state.get('download_height_preference', 1080)}
                        if st.session_state.get('download_quality_preference') == 'Limitar altura'
                        else {'quality': 'best'})
            response = call('POST', f'/projects/{project_id}/downloads',
                            json={'url': url, 'settings': settings},
                            headers={'Idempotency-Key': uuid.uuid4().hex})
            if response is not None:
                st.session_state['download-job-' + project_id] = response.json()['job_id']
                st.rerun()
    download_job_id = st.session_state.get('download-job-' + project_id)
    jobs_response = call('GET', f'/projects/{project_id}/jobs')
    downloads = [item for item in jobs_response.json() if item['kind'] == 'download'] if jobs_response is not None else []
    if downloads and not download_job_id:
        download_job_id = downloads[0]['job_id']
    if download_job_id:
        response = call('GET', f'/jobs/{download_job_id}')
        if response is not None:
            download_job = response.json()
            st.write(f"Download: {download_job['status']} • etapa: {download_job['stage']}")
            if download_job['status'] == 'completed':
                st.success('Vídeo baixado. Atualize a página para iniciar a análise.')
            elif download_job['status'] == 'failed':
                st.error(download_job.get('error') or 'Download falhou.')
            elif download_job['status'] in ('queued', 'running'):
                if st.button('Atualizar download'):
                    st.rerun()
                if st.button('Cancelar download'):
                    call('POST', f'/jobs/{download_job_id}/cancel')
                    st.rerun()
    st.stop()

with st.expander('Nova análise', expanded=True):
    with st.form('analyze-' + project_id):
        mode = st.radio('Duração dos cortes', ['Faixa', 'Exata'], horizontal=True)
        if mode == 'Faixa':
            st.caption('O motor busca uma pausa ou fim de frase dentro da faixa. Se não encontrar, avisa nos detalhes.')
            minimum = st.number_input('Mínimo (s)', min_value=1., value=25.)
            maximum = st.number_input('Máximo (s)', min_value=1., value=65.)
            target = None
        else:
            st.caption('Duração fixa pode interromper uma fala no limite escolhido.')
            target = st.number_input('Duração exata (s)', min_value=1., value=30.)
            minimum = maximum = None
        top_k = st.number_input('Número de sugestões', min_value=1, max_value=20, value=5)
        niche = st.text_input('Nicho', value='conversa')
        instructions = st.text_area('Orientação editorial opcional')
        if st.form_submit_button('Analisar gravação'):
            payload = {'asset_id': project['asset_id'], 'duration_mode': 'exact' if mode == 'Exata' else 'range',
                       'target_s': target if mode == 'Exata' else None, 'min_s': minimum if mode == 'Faixa' else None,
                       'max_s': maximum if mode == 'Faixa' else None, 'top_k': top_k, 'niche': niche,
                       'instructions': instructions or None}
            response = call('POST', f'/projects/{project_id}/analyses', json=payload,
                            headers={'Idempotency-Key': uuid.uuid4().hex})
            if response is not None:
                st.session_state['analysis-' + project_id] = response.json()['job_id']

analysis_id = st.session_state.get('analysis-' + project_id)
response = call('GET', f'/projects/{project_id}/jobs')
history = [item for item in response.json() if item['kind'] == 'analysis'] if response is not None else []
if history:
    entries = {item['job_id']: item for item in history}
    options = [item['job_id'] for item in history]
    choice = st.selectbox('Histórico de análises', options,
        index=options.index(analysis_id) if analysis_id in options else 0,
        format_func=lambda key: f"{entries[key]['created_at'][:19]} • {entries[key]['status']}")
    if st.button('Abrir análise do histórico') or not analysis_id:
        analysis_id = choice
        st.session_state['analysis-' + project_id] = choice
if not analysis_id:
    with st.form('resume-' + project_id):
        identifier = st.text_input('ID de análise para retomar uma sessão anterior')
        if st.form_submit_button('Retomar análise') and identifier:
            response = call('GET', f'/jobs/{identifier}')
            if response is not None and response.json()['project_id'] == project_id:
                st.session_state['analysis-' + project_id] = identifier
                st.rerun()
    st.stop()

response = call('GET', f'/jobs/{analysis_id}')
if response is None:
    st.stop()
job = response.json()
st.write(f"Estado: {job['status']} • etapa: {job['stage']}")
if job['status'] in ('queued', 'running'):
    st.info('A análise usa o worker local. O tempo depende da duração da gravação e do dispositivo configurado.')
    if st.button('Atualizar andamento'):
        st.rerun()
    if st.button('Cancelar análise'):
        call('POST', f'/jobs/{analysis_id}/cancel')
        st.rerun()
    st.stop()
if job['status'] in ('failed', 'cancelled'):
    st.error(job.get('error') or 'Análise cancelada. Você pode criar uma nova análise.')
    st.stop()

response = call('GET', f'/analyses/{analysis_id}/candidates')
if response is None:
    st.stop()
result = response.json()
prepared = call('POST', f'/analyses/{analysis_id}/exports')
if prepared is None:
    st.stop()
auto_by_candidate = {item['payload']['candidate_id']: item['job_id'] for item in prepared.json()}
jobs_response = call('GET', f'/projects/{project_id}/jobs')
jobs_by_id = {item['job_id']: item for item in jobs_response.json()} if jobs_response is not None else {}
if any(jobs_by_id.get(jid, {}).get('status') in ('queued', 'running') for jid in auto_by_candidate.values()):
    st.info('Gerando os arquivos dos cortes. Cada vídeo aparecerá aqui quando terminar.')
    if st.button('Atualizar cortes'):
        st.rerun()
for limitation in result['limitations'] + result['evidence']['quality']:
    st.warning(limitation)
discarded_response = call('GET', f'/analyses/{analysis_id}/discarded')
if discarded_response is None:
    st.stop()
discarded_ids = set(discarded_response.json())
visible_candidates = [item for item in result['candidates'] if item['candidate_id'] not in discarded_ids]
st.subheader('Galeria de cortes')
st.caption(f'{len(visible_candidates)} corte(s) nesta análise • clique no vídeo para reproduzir')
columns = st.columns(3, gap='medium')
for index, candidate in enumerate(visible_candidates, 1):
    cid = candidate['candidate_id']
    with columns[(index - 1) % 3], st.container(border=True):
        requested_duration = candidate['end_s'] - candidate['start_s']
        st.markdown(f"**Corte {index}** · {requested_duration:.1f} s")
        auto_job = jobs_by_id.get(auto_by_candidate.get(cid))
        revision_key = 'revision-' + analysis_id + '-' + cid
        revision = st.session_state.get(revision_key)
        manual_job = None
        if revision:
            manual_job = jobs_by_id.get(st.session_state.get('export-' + revision['revision_id']))
        shown_job = manual_job if manual_job and manual_job['status'] == 'completed' else auto_job
        if shown_job and shown_job['status'] == 'completed':
            exported = shown_job['result']
            st.video(API + f"/exports/{exported['export_id']}/media")
        elif auto_job and auto_job['status'] == 'failed':
            st.error('Falha ao gerar corte: ' + str(auto_job.get('error') or 'erro desconhecido'))
        else:
            st.info('Corte na fila de exportação.')
        description = short_description(candidate, result)
        st.write(description)
        st.caption(f"Original: {clock_time(candidate['start_s'])}–{clock_time(candidate['end_s'])}")
        download_col, details_col, delete_col = st.columns([1, 1, 1])
        with download_col:
            if shown_job and shown_job['status'] == 'completed':
                st.link_button('Baixar', API + f"/exports/{shown_job['result']['export_id']}/download",
                               icon=':material/download:', help='Baixar apenas este MP4')
        with details_col:
            if st.button('Detalhes', key='details-' + analysis_id + cid, icon=':material/info:'):
                st.session_state['details_candidate'] = (analysis_id, cid)
                st.session_state.pop('pending_delete', None)
        with delete_col:
            if st.button('Excluir', key='delete-' + analysis_id + cid, icon=':material/delete:'):
                st.session_state['pending_delete'] = (analysis_id, cid)
                st.session_state.pop('details_candidate', None)
        with st.expander('Ajustar limites deste corte'):
            with st.form('bounds-' + analysis_id + '-' + cid):
                start = st.number_input('Início no original (s)', min_value=0., value=float(candidate['start_s']), key='start-' + analysis_id + cid)
                end = st.number_input('Fim no original (s)', min_value=0.1, value=float(candidate['end_s']), key='end-' + analysis_id + cid)
                if st.form_submit_button('Salvar revisão'):
                    old = st.session_state.get(revision_key)
                    response = call('POST', f'/candidates/{cid}/revisions', json={'analysis_id': analysis_id,
                        'start_s': start, 'end_s': end, 'editor_changes': ['Limites confirmados manualmente'],
                        'parent_revision_id': old['revision_id'] if old else None})
                    if response is not None:
                        st.session_state[revision_key] = response.json()
                        st.success('Nova revisão preservada. A justificativa original pode precisar de reavaliação.')
            revision = st.session_state.get(revision_key)
            if revision:
                export_key = 'export-' + revision['revision_id']
                if st.button('Gerar arquivo desta revisão', key='generate-' + revision['revision_id']):
                    response = call('POST', f"/revisions/{revision['revision_id']}/exports",
                                    headers={'Idempotency-Key': 'export-' + revision['revision_id']})
                    if response is not None:
                        st.session_state[export_key] = response.json()['job_id']
                export_job = jobs_by_id.get(st.session_state.get(export_key))
                if export_job and export_job['status'] in ('queued', 'running'):
                    st.info('Gerando revisão; o corte inicial continua disponível acima.')
                elif export_job and export_job['status'] == 'failed':
                    st.error(export_job.get('error') or 'Falha na exportação da revisão.')

candidate_by_id = {item['candidate_id']: item for item in visible_candidates}
pending_delete = st.session_state.get('pending_delete')
selected_details = st.session_state.get('details_candidate')
if pending_delete and pending_delete[0] == analysis_id and pending_delete[1] in candidate_by_id:
    confirm_delete(*pending_delete)
elif selected_details and selected_details[0] == analysis_id and selected_details[1] in candidate_by_id:
    selected_candidate = candidate_by_id[selected_details[1]]
    show_details(analysis_id, selected_candidate, result, short_description(selected_candidate, result))
