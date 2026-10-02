"""Download deliberado de modelo pequeno, separado da execução do worker."""
import argparse
import json
from pathlib import Path
from datetime import datetime, timezone

def main():
    from huggingface_hub import HfApi, snapshot_download
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--repo', default='Systran/faster-whisper-tiny')
    parser.add_argument('--destination', type=Path, default=Path('models/whisper-tiny'))
    parser.add_argument('--revision')
    args = parser.parse_args()
    manifest = args.destination / 'download-manifest.json'
    if manifest.exists():
        previous = json.loads(manifest.read_text(encoding='utf-8'))
        if previous['repo'] != args.repo or (args.revision and previous['revision'] != args.revision):
            raise ValueError('Modelo existente diferente; escolha outro diretório para preservá-lo.')
        if (args.destination / 'model.bin').is_file():
            print('Modelo local já preparado: ' + str(args.destination))
            return
    elif args.destination.exists() and any(args.destination.iterdir()):
        raise ValueError('Destino não vazio sem manifesto; escolha outro diretório.')
    info = HfApi().model_info(args.repo, revision=args.revision)
    revision = info.sha
    print(f'Download explícito: {args.repo}@{revision}', flush=True)
    snapshot_download(repo_id=args.repo, revision=revision, local_dir=str(args.destination),
                      allow_patterns=['*.json', '*.bin', '*.txt'])
    manifest.write_text(json.dumps({'repo': args.repo, 'revision': revision,
        'source': 'https://huggingface.co/' + args.repo, 'observed_at': datetime.now(timezone.utc).isoformat()},
        indent=2), encoding='utf-8')
    print('Modelo preparado: ' + str(args.destination), flush=True)

if __name__ == '__main__':
    main()
