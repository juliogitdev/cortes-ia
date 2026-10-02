"""Painel local: comunica com a API; não carrega modelos."""
import os
import uuid
import httpx
import streamlit as st

API = os.environ.get('CLIP_API_URL', 'http://127.0.0.1:8000').rstrip('/')
st.set_page_config(page_title='Cortes IA', layout='wide')
st.title('Cortes IA')
st.caption('Baseline de fala • processamento local • score ordena sugestões e não prevê viralização')


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

st.subheader(project['name'])
with st.form('upload-' + project_id):
    uploaded = st.file_uploader('Gravação local com imagem e áudio', type=['mp4', 'mkv', 'mov', 'webm'])
    if st.form_submit_button('Enviar gravação') and uploaded is not None:
        with st.spinner('Validando a gravação…'):
            response = call('POST', f'/projects/{project_id}/upload',
                            files={'file': (uploaded.name, uploaded.getvalue(), uploaded.type)})
        if response is not None:
            st.session_state.pop('analysis-' + project_id, None)
            st.success(f"Gravação validada: {response.json()['duration_s']:.1f} segundos")
            st.rerun()

if not project.get('asset_id'):
    st.stop()

with st.form('analyze-' + project_id):
    mode = st.radio('Duração dos cortes', ['Exata', 'Faixa'], horizontal=True)
    target = st.number_input('Duração exata (s)', min_value=1., value=30.)
    minimum = st.number_input('Mínimo (s)', min_value=1., value=20.)
    maximum = st.number_input('Máximo (s)', min_value=1., value=60.)
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
    st.info('O worker precisa estar executando em um terminal separado. CPU pode levar mais tempo.')
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
for limitation in result['limitations'] + result['evidence']['quality']:
    st.warning(limitation)
for index, candidate in enumerate(result['candidates'], 1):
    cid = candidate['candidate_id']
    with st.container(border=True):
        st.subheader(f"Sugestão {index} • {candidate['start_s']:.1f}s a {candidate['end_s']:.1f}s")
        st.video(API + f"/assets/{result['asset']['asset_id']}/media", start_time=candidate['start_s'], end_time=candidate['end_s'])
        st.write('Motivos: ' + '; '.join(candidate['reasons']))
        st.caption(f"Score de ordenação: {candidate['rank_score']:.3f}")
        for limitation in candidate['limitations']:
            st.caption(limitation)
        with st.expander('Evidências da seleção'):
            for evidence in result['evidence']['transcript']:
                if evidence['evidence_id'] in candidate['evidence_ids']:
                    st.write(f"{evidence['start_s']:.1f}s–{evidence['end_s']:.1f}s: {evidence['observation']}")
        revision_key = 'revision-' + analysis_id + '-' + cid
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
            export_job_id = st.session_state.get(export_key)
            if export_job_id:
                response = call('GET', f'/jobs/{export_job_id}')
                if response is not None:
                    export_job = response.json()
                    st.write('Exportação: ' + export_job['status'])
                    if export_job['status'] == 'completed':
                        exported = export_job['result']
                        response = call('GET', f"/exports/{exported['export_id']}/download")
                        if response is not None:
                            st.download_button('Baixar corte', response.content, file_name=f"corte-{exported['export_id']}.mp4", mime='video/mp4', key='download-' + exported['export_id'])
                    elif export_job['status'] == 'failed':
                        st.error(export_job.get('error'))
                    elif st.button('Atualizar exportação', key='refresh-' + revision['revision_id']):
                        st.rerun()
