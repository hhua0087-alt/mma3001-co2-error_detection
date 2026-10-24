"""Build a local HTML API reference directly from source signatures and docstrings."""
import ast
import html
import json
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'docs/api'
STYLE='''body{font:16px/1.55 system-ui,sans-serif;color:#18232c;background:#fff;max-width:1050px;margin:36px auto;padding:0 24px}
h1,h2,h3{color:#000;line-height:1.25}nav{margin:20px 0}nav a{margin-right:14px}a{color:#165d91}
pre{background:#f2f4f6;padding:16px;white-space:pre-wrap;overflow-wrap:anywhere}code{font-family:Consolas,monospace}
section{margin:32px 0}summary{cursor:pointer;color:#165d91}footer{margin:40px 0;color:#4a555f}'''


def page(title,content):
    """Return standalone UTF-8 HTML with no external assets or script dependencies."""
    return '<!doctype html><html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">'+f'<title>{html.escape(title)}</title><style>{STYLE}</style><body>{content}</body></html>'


def document_node(node,level=2):
    """Render an AST function/class and its documented methods."""
    name=node.name
    signature=name+'('+ast.unparse(node.args)+')' if isinstance(node,(ast.FunctionDef,ast.AsyncFunctionDef)) else name
    doc=ast.get_docstring(node) or 'See the source and experiment notebook for this component.'
    result=f'<section id="{html.escape(name)}"><h{level}><code>{html.escape(signature)}</code></h{level}><pre>{html.escape(doc)}</pre>'
    if isinstance(node,ast.ClassDef):
        for child in node.body:
            if isinstance(child,ast.FunctionDef) and (not child.name.startswith('_') or child.name=='__init__'):
                result+=document_node(child,3)
    return result+'</section>'


def main():
    """Build index and per-module pages from the final local Python sources."""
    OUT.mkdir(parents=True,exist_ok=True)
    modules=sorted((ROOT/'src/co2_project').glob('*.py'))
    modules=[p for p in modules if p.stem!='__init__']
    nav='<nav><a href="index.html">API home</a>'+''.join(f'<a href="{p.stem}.html">{p.stem}</a>' for p in modules)+'</nav>'
    rows=[]
    for path in modules:
        source=path.read_text(encoding='utf-8');tree=ast.parse(source)
        doc=ast.get_docstring(tree) or path.stem
        nodes=[n for n in tree.body if isinstance(n,(ast.FunctionDef,ast.ClassDef)) and not n.name.startswith('_')]
        content=nav+f'<h1>{html.escape(path.stem)} API</h1><p>{html.escape(doc)}</p>'
        content+=''.join(document_node(n) for n in nodes)
        content+='<details><summary>Inspect module source</summary><pre><code>'+html.escape(source)+'</code></pre></details>'
        (OUT/(path.stem+'.html')).write_text(page(path.stem+' API',content),encoding='utf-8')
        rows.append(f'<li><a href="{path.stem}.html">{path.stem}</a> — {html.escape(doc.splitlines()[0])}</li>')
    for path in sorted((ROOT/'notebooks').glob('*.ipynb')):
        notebook=json.loads(path.read_text(encoding='utf-8'))
        content=nav+f'<h1>{html.escape(path.stem)} notebook functions</h1>'
        content+='<p>Orchestration functions defined in the notebook. Read the notebook for the sequential experiment and the module pages for shared calculation.</p>'
        code_number=0
        for cell in notebook['cells']:
            if cell['cell_type']!='code':continue
            code_number+=1
            source=''.join(cell['source'])
            nodes=[n for n in ast.parse(source).body if isinstance(n,(ast.FunctionDef,ast.ClassDef))]
            if nodes:
                content+=f'<h2>Code cell {code_number}</h2>'
                content+=''.join(document_node(n,3) for n in nodes)
        name='notebook_'+path.stem+'.html'
        (OUT/name).write_text(page(path.stem+' notebook functions',content),encoding='utf-8')
        rows.append(f'<li><a href="{name}">{html.escape(path.stem)}</a> — notebook orchestration functions</li>')
    intro=nav+'<h1>CO2 fault detection API</h1><p>Shared functions used by the three experiment notebooks. Inputs, outputs, units and failure cases are documented below each signature. The source is included for inspection.</p><ul>'+''.join(rows)+'</ul>'
    intro+='<p>Study order: main experiment, controlled NN input comparison, then results analysis. CUSUM statistics are not additional CO2 predictions. Simulated faults and passing implementation checks do not establish real sensor health.</p>'
    intro+='<footer>Generated from the local source by tools/build_docs.py. No external hosting is required.</footer>'
    (OUT/'index.html').write_text(page('CO2 fault detection API',intro),encoding='utf-8')
    print('Generated HTML API pages:',len(modules)+4)


if __name__=='__main__':main()
