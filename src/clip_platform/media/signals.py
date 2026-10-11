"""Observable audio energy and frame changes; no semantic event claims."""
import subprocess
import wave
from pathlib import Path

import numpy as np

from clip_platform.media.tools import AV_DEMUXERS, MediaError, find_tool
from clip_platform.shared.contracts import Evidence, MediaAsset, Provenance


def audio_events(asset: MediaAsset, wav_path: Path, window_s=1.0):
    with wave.open(str(wav_path), 'rb') as reader:
        rate = reader.getframerate()
        if reader.getnchannels() != 1 or reader.getsampwidth() != 2 or rate <= 0:
            raise MediaError('Áudio PCM mono de 16 bits esperado para análise de energia.')
        frames_per_window = max(1, int(rate * window_s))
        levels = []
        while data := reader.readframes(frames_per_window):
            samples = np.frombuffer(data, dtype='<i2').astype(np.float32) / 32768
            levels.append(float(np.sqrt(np.mean(samples * samples))))
    if not levels:
        return [], None
    median = float(np.median(levels))
    threshold = max(.08, median * 2.5)
    provenance = Provenance(run_id='audio_energy_v1', source_uri=str(wav_path),
                            artifact_hash=asset.content_hash, original_offset_s=0,
                            settings={'window_s': window_s, 'metric': 'RMS normalized',
                                      'threshold': threshold, 'sample_rate': rate})
    events = []
    for index, level in enumerate(levels):
        if level < threshold:
            continue
        start = index * window_s
        end = min(asset.duration_s, (index + 1) * window_s)
        if end <= start:
            continue
        events.append(Evidence(evidence_id=f'audio_{index:06d}', asset_id=asset.asset_id,
                               start_s=start, end_s=end,
                               observation=f'Energia sonora elevada na janela (RMS {level:.3f}).',
                               provenance=provenance))
    return events, provenance


def visual_events(asset: MediaAsset, sample_s=5., width=32, height=18, device='cpu'):
    source = Path(asset.local_path).resolve(strict=True)
    command = [find_tool('ffmpeg'), '-hide_banner', '-loglevel', 'error', '-nostdin',
               '-protocol_whitelist', 'file,pipe', '-format_whitelist', AV_DEMUXERS]
    if device == 'cuda':
        # Decode keyframes on the GPU, then let fps hold them at regular sample
        # times. This avoids decoding every frame of a multi-hour recording.
        command += ['-hwaccel', 'cuda', '-skip_frame', 'nokey']
    command += [
               '-i', str(source), '-map', '0:v:0', '-vf', f'fps=1/{sample_s},scale={width}:{height}',
               '-f', 'rawvideo', '-pix_fmt', 'gray', '-']
    try:
        completed = subprocess.run(command, capture_output=True, timeout=max(120, asset.duration_s * 2))
    except subprocess.TimeoutExpired as exc:
        raise MediaError('Amostragem visual excedeu o tempo disponível.') from exc
    if completed.returncode:
        raise MediaError('Amostragem visual falhou: ' + completed.stderr.decode('utf-8', 'replace')[-500:])
    frame_size = width * height
    if len(completed.stdout) % frame_size:
        raise MediaError('Quadro visual incompleto.')
    provenance = Provenance(run_id='frame_change_v1', source_uri=str(source),
                            artifact_hash=asset.content_hash, original_offset_s=0,
                            settings={'sample_s': sample_s, 'size': [width, height],
                                      'frame_policy': 'keyframes_held' if device == 'cuda' else 'decoded_frames',
                                      'decoder': device,
                                      'metric': 'mean absolute grayscale difference', 'threshold': .18})
    events = []
    previous = None
    for index in range(len(completed.stdout) // frame_size):
        frame = np.frombuffer(completed.stdout, dtype=np.uint8,
                              count=frame_size, offset=index * frame_size).astype(np.int16)
        if previous is not None:
            change = float(np.mean(np.abs(frame - previous)) / 255.)
            if change >= .18:
                start = index * sample_s
                end = min(asset.duration_s, start + sample_s)
                if end > start:
                    events.append(Evidence(evidence_id=f'visual_{index:06d}', asset_id=asset.asset_id,
                                           start_s=start, end_s=end,
                                           observation=f'Mudança visual entre quadros amostrados ({change:.3f}).',
                                           provenance=provenance))
        previous = frame
    return events, provenance
