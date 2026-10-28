import re
import os
import subprocess
import shutil
from copy import deepcopy
from collections import Counter, namedtuple

import matplotlib.pyplot as plt
import pandas as pd

from pypdf import PdfReader, PdfWriter, Transformation
from pypdf.papersizes import Dimensions

from cliargs import parse_args, prepare_dirs

################################################################################
# Global Utility Constants 
################################################################################

# Constants for photo roster pdf
N_ROWS_PER_PAGE = 4
N_COLS_PER_PAGE = 6
N_TOTAL_PER_PAGE = N_ROWS_PER_PAGE * N_COLS_PER_PAGE

# 8.5x11 converted into pixels at 72dpi (1 inch is equal to 72 pixels)
LETTERSIZE = Dimensions(8.5*72, 11*72)

HEADER_HEIGHT = 0.2 * LETTERSIZE.height # Top 20% of page is header
FOOTER_HEIGHT = 0.05 * LETTERSIZE.height # Bottom 5% of apge is footer
BODY_HEIGHT = LETTERSIZE.height - HEADER_HEIGHT - FOOTER_HEIGHT
PHOTO_WIDTH = LETTERSIZE.width / N_COLS_PER_PAGE 
PHOTO_HEIGHT = BODY_HEIGHT / N_ROWS_PER_PAGE

# Escaped backslash
B = '\\'

################################################################################
# Utility Functions
################################################################################

def setup_pandas():
    pd.set_option('display.max_rows',    1000)
    pd.set_option('display.max_columns', 1000)
    pd.set_option('display.width',       1500)

def prompt_yes_no(prompt):
    print(prompt)
    while True:
        res = input('Enter [Y]es or [N]o: ').lower()
        if res not in 'yn':
            continue
        elif res[0] == 'y':
            return True
        else: # entered no
            return False
            
def is_extension_student(studentid):
    '''
    A student is an extension student if their ID starts with 0 or X, OR if they
    have only 7 numbers
    '''
    idstr = str(studentid)
    return idstr[0] in ('0', 'X') or len(idstr) == 7

def to_inches(pixel):
    '''
    Assume that we use 72dpi (1 inch = 72 pixels)
    '''
    return pixel / 72.0
    
################################################################################
# Check for unordered names
################################################################################

def check_unordered_names(roster):
    '''
    Check for unordered names 
    '''
    lastnames = Counter(roster['Name'].apply(lambda x : x.split(',')[0]))
    for name,count in sorted(lastnames.items(), key=lambda x : x[0]):
        if count > 1:
            print(f' - {name} ({count})')

    res = prompt_yes_no('Did you check that the order of these names?')
    if not res:
        print('... exiting')
        exit()
        
################################################################################
# Main Functions - Extract Photos
################################################################################

def get_page_row_col(idx):
    '''Get page, row, and column where student name should appear'''
    ipage,idx = divmod(idx, N_TOTAL_PER_PAGE)
    irow,icol = divmod(idx, N_COLS_PER_PAGE)
    return ipage, irow, icol

def get_photo_from_index(photos, ipage, irow, icol):
    '''Make a cropbox for the photo, and its translation to get to (0,0)'''
    # Make a cropbox for that page/row/col
    photo = deepcopy(photos.pages[ipage])
    photo.cropbox.left = icol * PHOTO_WIDTH
    photo.cropbox.right = (icol+1) * PHOTO_WIDTH
    photo.cropbox.bottom = (N_ROWS_PER_PAGE-1 - irow) * PHOTO_HEIGHT + FOOTER_HEIGHT
    photo.cropbox.top = (N_ROWS_PER_PAGE - irow) * PHOTO_HEIGHT + FOOTER_HEIGHT
    
    # Also return the transformation that needs to be applied to the image
    # to get it to (0,0)
    trans = Transformation().translate(
        -icol * PHOTO_WIDTH,
        (irow-N_ROWS_PER_PAGE+1) * PHOTO_HEIGHT - FOOTER_HEIGHT)
    
    return photo, trans

def get_fphoto_from_name(photos_dir, name):
    return f"{photos_dir}/photo-{name.replace(', ','_')}.pdf"

def dump_photo(fname, photo, trans):
    '''Save the photo into a pdf by itself'''
    writer = PdfWriter()
    page = writer.add_blank_page(width=PHOTO_WIDTH, height=PHOTO_HEIGHT)
    page.merge_transformed_page(photo, trans)
    with open(fname, 'wb') as fp:
        writer.write(fp)

def extract_photos(roster, photos, photos_dir):
    for idx,r in roster.iterrows():
        if is_extension_student(r['ID']): # No photo exists, so make something up
            fphoto = get_fphoto_from_name(photos_dir, r['Name'])
            _fig, ax = plt.subplots(1,1, figsize=(to_inches(PHOTO_WIDTH), to_inches(PHOTO_HEIGHT)))
            ax.text(0.1,0.5, '\n'.join(r['Name'].split(',')))
            ax.get_xaxis().set_visible(False)
            ax.get_yaxis().set_visible(False)
            plt.axis('off')
            plt.savefig(fphoto, bbox_inches='tight')
        else: # Otherwise, find the photo and dump it
            ipage, irow, icol = get_page_row_col(idx)
            photo, trans = get_photo_from_index(photos, ipage, irow, icol)
            fphoto = get_fphoto_from_name(photos_dir, r['Name'])
            dump_photo(fphoto, photo, trans)

################################################################################
# Main Functions - Make photo seating pdf
################################################################################

def pdf_template(content):
    return f'''
{B}documentclass{{article}}
{B}usepackage[left=0.5in,right=0.5in,top=0.5in,bottom=0.5in]{{geometry}}
{B}usepackage{{graphicx}}

{B}title{{}}
{B}author{{}}
{B}date{{}}

{B}begin{{document}}

{content}
    
{B}end{{document}}
'''

def create_pdf(fname, content, pdflatex):
    latex = pdf_template(content)
    with open('tmp.tex', 'w') as f:
        f.write(latex)

    args = [pdflatex, f'tmp.tex']
    subprocess.call(args, shell=False, timeout=200)
    
    shutil.move('./tmp.pdf', fname)

    # Remove other files
    os.remove('./tmp.tex')
    os.remove('./tmp.aux')
    os.remove('./tmp.log')
    
def page_header(row, args):
    header = f'''
{{ {B}Large
{B}noindent UCI {args.course_name} {args.exam_name} Photo Roster {B}{B}
{args.exam_date} {B}hfill {{Row {row}}}
}}
'''
    return header

def n_at_a_time(it, n):
    '''
    Yields n values of it at a time
    '''
    it = iter(it)
    while True:
        l = []
        for _ in range(n):
            try:
                l.append(next(it))
            except StopIteration: 
                if l:
                    yield l
                return
        yield l
        
def make_table_row(fmt, it, n):
    '''
    Make a row of a table
    '''
    it = list(it) # need this to be a list
    assert len(it) <= n, 'Error: too many items in list'
    return ' & '.join(fmt(i) for i in it) + f'{"&"*(n-len(it)-1)} {B}{B}\n'

def make_seating_latex(row, group, args, nrow=4, ncol=4):
    if args.debug:
        nrow,ncol = 3,3

    header = page_header(row, args)

    # Place all seating assignments in a tabular environment
    content = f'''
{header}

{B}begin{{tabular}}{{{'l'*ncol}}}
'''
    
    # Flag for whether a new table should be started
    start_new_table = False

    for i,it in enumerate(n_at_a_time((r for _,r in group.iterrows()), ncol)):
        
        # End previous table and start a new table on new page
        if start_new_table:
            start_new_table = False
            content += f'''\
{B}end{{tabular}}

{B}newpage

{header}

{B}begin{{tabular}}{{{'l'*ncol}}}
'''
        
        # Add photo row
        content += make_table_row(
                lambda x : f'{B}fbox{{{B}includegraphics{{{x}}}}}',
                [get_fphoto_from_name(args.photos_dir, r['Name']) for r in it],
                ncol)
    
        # Add seat row
        content += make_table_row(
                lambda x : f'Seat: {x}',
                [r['Seat'] for r in it],
                ncol)

        # Debug rows; comment if not needed
        if args.debug:
            content += make_table_row(
                    lambda x : f'{x.split(",")[0]}',
                    [r['Name'] for r in it],
                    ncol)
            
            # Debug rows; comment if not needed
            content += make_table_row(
                    lambda x : f'{x.split(",")[1]}',
                    [r['Name'] for r in it],
                    ncol)

        # if page is overfilled, then set flag to start new table on next iter
        if i > 0 and (i+1) % nrow == 0:
            start_new_table = True

    
    # End table
    content += f'''\
{B}end{{tabular}}

{B}newpage
'''
    
    return content
        
def make_photo_seating(roster, args):
    content = ''
    for row,group in sorted(roster.groupby(['Row', 'Group'])):
        group.sort_values('Num', inplace=True)

        annot = row[0] if row[1] == '' else f'{row[0]} ({row[1]})'
        content += make_seating_latex(annot, group, args)

    create_pdf(args.output, content, args.pdflatex)


def main(args):
    roster = pd.read_excel(args.f_roster, header=None, 
                           names=['ID', 'Name', '_'])
    photos = PdfReader(args.f_photo_roster)
    seats  = pd.read_excel(args.f_seats, header=None, 
                           names=['Name', 'Seat'])
    
    # Drop seats that are DSC
    seats = seats[seats['Seat'] != 'DSC']
    
    # Merge roster and seating 
    roster = roster.merge(seats, on='Name', how='left')
    roster = roster[~roster['Seat'].isna()]
    roster['Row'] = roster['Seat'].apply(lambda x : x[0])

    # Seat number, sorted
    pat = re.compile(r'\w-(\d+).*')
    roster['Num'] = roster['Seat'].apply(
        lambda x : int(re.match(pat, x).group(1)))
    
    # Set the group number as the first seat partition function returning True
    roster['Group'] = roster['Num'].apply(
        lambda x : next(filter(lambda v : \
            v[0], ((pf.func(x),pf.name) for pf in args.seats_partition)))[1])

    # Run
    print('Checking unordered names: ')
    check_unordered_names(roster)

    print('Extracting photos...')
    extract_photos(roster, photos, args.photos_dir)

    print('Generating photo roster...')
    make_photo_seating(roster, args)

if __name__ == '__main__':

    args = prepare_dirs(parse_args())

    setup_pandas()

    main(args)

    print('Done')
    
