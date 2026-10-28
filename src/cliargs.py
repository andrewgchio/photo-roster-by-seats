# src/cliargs.py

import argparse
import os
import shutil
import sys
from collections import namedtuple
from pathlib import Path

################################################################################
# Constants
################################################################################

# Project root (parent of src/); data-{QUARTER} directories live here
PROJECT_ROOT = Path(__file__).resolve().parent.parent

EXAMS = ('me1', 'me2', 'me', 'fe')

# Used for the output title when --exam-name is not given
DEFAULT_EXAM_NAMES = {
    'me1' : 'Midterm 1',
    'me2' : 'Midterm 2',
    'me'  : 'Midterm',
    'fe'  : 'Final',
}

# Used when pdflatex is not on the PATH
DEFAULT_PDFLATEX_PATH = '/Library/TeX/texbin/pdflatex' 

################################################################################
# Seat Partitions
################################################################################

# Set based on the lecture hall. Most are one or the other. Format (Name, Func)
PartitionFunc = namedtuple('PartitionFunc', ['name', 'func'])
numeric = PartitionFunc('', lambda _x : True) # 1,2,3 order
over100 = PartitionFunc('$>$100', lambda x : x >= 100) # > 100
odd_under100 = PartitionFunc('odd', lambda x : x % 2 == 1 and not over100.func(x)) # odd & < 100
even_under100 = PartitionFunc('even', lambda x : x % 2 == 0 and not over100.func(x)) # even & < 100

SEATS_PARTITIONS = {
    'numeric'  : [numeric],
    'odd-even' : [odd_under100, even_under100, over100],
}

################################################################################
# Command Line Arguments
################################################################################

def parse_args(argv=None):
    '''
    Parse the command line options. --seats-partition is converted from its
    name into its list of PartitionFuncs.
    '''
    parser = argparse.ArgumentParser(
        description='Create a photo roster ordered by exam seat assignment.')

    parser.add_argument('--course-name', required=True,
                        help='course name, e.g., "ICS XXX Lec A"')
    parser.add_argument('--exam', required=True, choices=EXAMS,
                        help='short exam name; used to select the roster-, '
                             'photo-roster-, and seating- input files')
    parser.add_argument('--exam-name',
                        help='exam name shown in the output')
    parser.add_argument('--exam-date', required=True,
                        help='exam date, e.g., "Jan 1, 2024"')

    data = parser.add_mutually_exclusive_group(required=True)
    data.add_argument('--quarter',
                      help='quarter (and optional lecture), e.g., f19, s24b; '
                           'uses data-{QUARTER} in the project root')
    data.add_argument('--data-dir', type=Path,
                      help='data directory to use instead of data-{QUARTER}')

    parser.add_argument('--seats-partition', required=True, choices=SEATS_PARTITIONS,
                        help='how the lecture hall partitions seats')

    parser.add_argument('-o', '--output', type=Path,
                        help='output pdf (default: "{DATA_DIR}/{COURSE_NAME} '
                             '{EXAM_NAME} Photo Roster (Seating).pdf")')
    parser.add_argument('--pdflatex',
                        default=shutil.which('pdflatex') or DEFAULT_PDFLATEX_PATH,
                        help='path to pdflatex (default: %(default)s)')

    parser.add_argument('--debug', type=str.lower, choices=('true', 'false'),
                        default='false',
                        help='print names under photos to check roster order '
                             '(default: %(default)s)')

    args = parser.parse_args(argv)

    if args.exam_name is None:
        args.exam_name = DEFAULT_EXAM_NAMES[args.exam]
    args.seats_partition = SEATS_PARTITIONS[args.seats_partition]
    args.debug = args.debug == 'true'

    return args

def prepare_dirs(args):
    '''
    Resolve the data directory and the files in it, and check that the inputs
    and pdflatex exist before any work is done. Creates the photos and output
    directories if needed. Exits with an error message if anything is missing.
    '''
    data_dir = args.data_dir or PROJECT_ROOT / f'data-{args.quarter}'
    if not data_dir.is_dir():
        sys.exit(f'Error: data directory not found: {data_dir}')
    args.data_dir = data_dir

    args.f_roster = data_dir / f'roster-{args.exam}.xlsx'
    args.f_photo_roster = data_dir / f'photo-roster-{args.exam}.pdf'
    args.f_seats = data_dir / f'seating-{args.exam}.xlsx'

    missing = [f for f in (args.f_roster, args.f_photo_roster, args.f_seats)
               if not f.is_file()]
    if missing:
        sys.exit('Error: missing input files:\n'
                 + '\n'.join(f' - {f}' for f in missing))

    if not (os.path.isfile(args.pdflatex) and os.access(args.pdflatex, os.X_OK)):
        sys.exit(f'Error: pdflatex not found or not executable: {args.pdflatex}\n'
                 'Set its path with --pdflatex (obtained with `which pdflatex`)')

    # Extracted photos are written here
    args.photos_dir = data_dir / 'photos'
    args.photos_dir.mkdir(exist_ok=True)

    if args.output is None:
        args.output = data_dir / f'{args.course_name} {args.exam_name} Photo Roster (Seating).pdf'
    args.output.parent.mkdir(parents=True, exist_ok=True)

    return args
