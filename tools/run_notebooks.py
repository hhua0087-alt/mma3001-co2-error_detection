"""Execute the three notebooks sequentially in fresh real Jupyter kernels."""
import argparse
import os
from pathlib import Path

import nbformat
from nbclient import NotebookClient


def main():
    """Read command-line settings and retain executed copies only under results."""
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--kernel',default='co2-project',help='Registered kernel from the project environment')
    parser.add_argument('--only',nargs='+',choices=['01','02','03'],help='Run selected stages, preserving their dependency order')
    args=parser.parse_args()
    root=Path(__file__).resolve().parents[1]
    output=root/'results/executed'
    output.mkdir(parents=True,exist_ok=True)
    os.environ.setdefault('MPLBACKEND','module://matplotlib_inline.backend_inline')
    for number in ['01','02','03']:
        if args.only and number not in args.only:continue
        path=next((root/'notebooks').glob(number+'_*.ipynb'))
        notebook=nbformat.read(path,as_version=4)
        progress_state={'code':0}
        def progress(cell,cell_index,**kwargs):
            if cell.cell_type=='code':
                progress_state['code']+=1
                print(f'{path.name}: code cell {progress_state["code"]}',flush=True)
        client=NotebookClient(notebook,timeout=300,kernel_name=args.kernel,
            resources={'metadata':{'path':str(root/'notebooks')}},allow_errors=False,on_cell_start=progress)
        try:
            client.execute()
        except Exception:
            nbformat.write(notebook,output/('failed_'+path.name))
            raise
        nbformat.write(notebook,output/('executed_'+path.name))
        print('Completed:',path.name,flush=True)


if __name__=='__main__':main()
