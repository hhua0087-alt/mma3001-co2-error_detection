"""Check portable, English, output-free source notebooks and local API links."""
import ast
import json
import re
from html.parser import HTMLParser
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]


def test_notebook_sources_are_english_output_free_and_portable():
    files=sorted((ROOT/'notebooks').glob('*.ipynb'))
    assert [p.name[:2] for p in files]==['01','02','03']
    for path in files:
        notebook=json.loads(path.read_text(encoding='utf-8'))
        for cell in notebook['cells']:
            source=''.join(cell['source'])
            assert not re.search('[\u4e00-\u9fff]',source)
            assert not re.search(r'[CE]:[\\/]',source)
            if cell['cell_type']=='code':
                ast.parse(source)
                assert cell.get('outputs',[])==[] and cell.get('execution_count') is None


def test_shared_source_compiles_without_personal_paths():
    for path in (ROOT/'src/co2_project').glob('*.py'):
        source=path.read_text(encoding='utf-8')
        ast.parse(source)
        assert not re.search('[\u4e00-\u9fff]',source)
        assert not re.search(r'[CE]:[\\/]',source)


def test_generated_api_links_are_local_and_valid():
    class Links(HTMLParser):
        def __init__(self):super().__init__();self.hrefs=[]
        def handle_starttag(self,tag,attrs):
            if tag=='a':self.hrefs += [v for k,v in attrs if k=='href']
    pages=list((ROOT/'docs/api').glob('*.html'))
    assert len(pages)>=7
    for path in pages:
        parser=Links();parser.feed(path.read_text(encoding='utf-8'))
        for href in parser.hrefs:
            assert (path.parent/href.split('#')[0]).is_file()
