#!/usr/bin/env python3
"""Package ONLY the public reader assets for GitHub Pages deployment."""
from pathlib import Path
import shutil


def build(root, output):
    if output.exists():
        shutil.rmtree(output)
    output.mkdir(parents=True)
    for relative in ('index.html', 'manifest.webmanifest', 'service-worker.js', 'assets/icon.svg',
                     'data/current.json', 'data/archive/index.json'):
        source = root / relative
        if not source.is_file():
            raise FileNotFoundError(relative)
        target = output / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, target)
    for source in (root / 'data' / 'archive').glob('????-??-??.json'):
        shutil.copy2(source, output / 'data' / 'archive' / source.name)
    print('公開用サイトを生成しました: ' + str(output))
    return output


if __name__ == '__main__':
    home = Path(__file__).resolve().parent
    build(home, home / '_site')
