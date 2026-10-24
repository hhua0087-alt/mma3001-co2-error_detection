"""Remove saved outputs from the three submission notebooks before committing."""
from pathlib import Path
import nbformat


def main():
    """Clear output and execution counters without changing code or explanations."""
    root=Path(__file__).resolve().parents[1]
    for path in sorted((root/'notebooks').glob('*.ipynb')):
        notebook=nbformat.read(path,as_version=4)
        for cell in notebook.cells:
            if cell.cell_type=='code':cell.outputs=[];cell.execution_count=None
        nbformat.write(notebook,path)
        print('Cleared:',path.name)


if __name__=='__main__':main()
