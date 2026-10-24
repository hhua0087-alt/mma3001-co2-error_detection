"""Extract one sensor from an authorized course environmental CSV."""
import argparse
import sys
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'src'))
from co2_project.extraction import extract


def main():
    """Require an explicit raw input; write a new local extract without modifying it."""
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--input',type=Path,required=True,help='Authorized raw environmental CSV')
    parser.add_argument('--sensor',default='6012002000869')
    parser.add_argument('--variable',help='Exact channel; omit to retain all channels required by the study')
    parser.add_argument('--output',type=Path,default=ROOT/'data/input.csv')
    parser.add_argument('--progress-every',type=int,default=10000)
    parser.add_argument('--force',action='store_true',help='Explicitly replace an existing destination, never the raw source')
    args=parser.parse_args()
    if args.progress_every<1:parser.error('--progress-every must be positive')
    try:extract(args.input,args.output,args.sensor,args.variable,args.progress_every,args.force)
    except (FileNotFoundError,FileExistsError,ValueError) as exc:parser.exit(1,f'Error: {exc}\n')


if __name__=='__main__':main()
