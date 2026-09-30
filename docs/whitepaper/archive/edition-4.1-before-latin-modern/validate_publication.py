"""Validate figure references, artwork provenance and the generated publication.

Offline; never opens the production databases. Add --pdf for PyMuPDF checks.
Writes publication-validation.json. Numerical checks live in validate_paper.py.
"""
from __future__ import annotations
import argparse
import hashlib
import json
import re
from datetime import UTC, datetime
from pathlib import Path

HERE = Path(__file__).resolve().parent

def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()

def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--pdf', action='store_true')
    args = parser.parse_args()
    source = (HERE / 'eon-whitepaper.md').read_text()
    build = json.loads((HERE / 'document-build.json').read_text())
    art = json.loads((HERE / 'figures/art/manifest.json').read_text())
    checks = {}
    captions = [int(n) for n in re.findall(r'^\*Figure (\d+)\.', source, re.M)]
    assert captions == list(range(1, 18)), captions
    references = {int(n) for n in re.findall(r'Figure (\d+)', source)}
    assert references == set(captions)
    assert [f['number'] for f in build['figures']] == captions
    checks['numbered_figures'] = len(captions)
    # All image paths exist, with useful descriptions; generated art is explicit.
    images = re.findall(r'!\[([^\]]+)\]\(([^)]+)\)([^\n]*)', source)
    assert len(images) == 22
    art_paths = set()
    for alt, path, attrs in images:
        assert len(alt) > 30 and (HERE / path).is_file(), path
        if '/art/' in path:
            assert '.illustration' in attrs
            art_paths.add(path)
        else:
            assert (HERE / Path(path).with_suffix('.pdf')).is_file()
    assert len(art_paths) == 5
    assert len(art['assets']) == 6
    for asset in art['assets']:
        assert sha(HERE / asset['asset']) == asset['sha256'], asset['asset']
        assert asset['prompt'] and asset['native_pixels']
    assert art_paths | {'figures/art/art-cover.png'} == {a['asset'] for a in art['assets']}
    assert {a['asset'] for a in build['illustrations']} == art_paths
    for asset in build['illustrations'] + [build['cover']]:
        assert sha(HERE / asset['asset']) == asset['sha256']
    checks['illustrations'] = {'cover': 1, 'interior': 5, 'hashes': 'matched'}
    for key, path in [('markdown_sha256','eon-whitepaper.md'),('latex_sha256','eon-whitepaper.tex'),('preamble_sha256','paper-preamble.tex'),('generator_sha256','build_paper.py')]:
        assert build[key] == sha(HERE / path), path
    checks['build_matches_source'] = True
    assert source.count('*Illustration — ') == 5
    assert 'SIX_' not in source and '\ufffd' not in source
    if args.pdf:
        import pymupdf
        doc = pymupdf.open(HERE / 'eon-whitepaper.pdf')
        page_text = [p.get_text() for p in doc]
        text = '\n'.join(page_text)
        numbers = [int(n) for n in re.findall(r'^Figure\s+(\d+):', text, re.M)]
        assert numbers == captions, numbers
        assert len(re.findall(r'Illustration\s*[—–-]', text)) == 5
        tables = [int(n) for n in re.findall(r'^Table\s+(\d+):', text, re.M)]
        assert tables == [1, 2, 3], tables
        checks['numbered_tables'] = tables
        assert 'List of Figures' in text and 'Publication details' in text
        assert 'p = 0.094' in page_text[4]
        assert 'Tomorrow' in page_text[0] and 'Gabriel George' in page_text[0]
        for page in doc:
            assert page.get_text().strip(), f'Blank page {page.number+1}'
            for x0,y0,x1,y1,*_ in page.get_text('words'):
                assert x0 >= -1 and y0 >= -1 and x1 <= page.rect.width+1 and y1 <= page.rect.height+1, (page.number+1,x0,y0,x1,y1)
        links = [link for page in doc for link in page.get_links() if link.get('kind') in (pymupdf.LINK_GOTO, pymupdf.LINK_NAMED)]
        assert len(links) >= 17
        assert all(0 <= link.get('page', -1) < len(doc) for link in links)
        figure_destinations = {link['nameddest'] for link in links if link.get('nameddest', '').startswith('figure.')}
        assert len(figure_destinations) == 17
        checks['internal_pdf_links'] = len(links)
        checks['pdf'] = {'pages':len(doc), 'caption_order':'1–17', 'text_in_page_bounds':True, 'bytes':(HERE/'eon-whitepaper.pdf').stat().st_size}
        log = (HERE/'eon-whitepaper.log').read_text(errors='replace') if (HERE/'eon-whitepaper.log').exists() else ''
        assert not re.search(r'Overfull \\[hv]box|Missing character:',log)
    report = {'timestamp':datetime.now(UTC).isoformat(),'status':'passed','checks':checks,'inputs':{f:sha(HERE/f) for f in ['eon-whitepaper.md','eon-whitepaper.pdf','document-build.json','figures/art/manifest.json','validate_publication.py']}}
    (HERE/'publication-validation.json').write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps(checks,indent=2))

if __name__ == '__main__':
    main()
