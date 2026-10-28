# Photo Seat Roster Generation

This is a utility script used to create a pdf of a photo roster to match a seat assignment for an exam at UCI. This script works by extracting student photos from a given photo roster, and compiling the photos together to match row-wise seat assignments.

## Installation and Dependencies

To download the GitHub repository, run
```
git clone git@github.com:andrewgchio/photo-roster-by-seats.git
```

Then, install the following (required) external libraries: 

- pandas (version >= 1.3.4)
- matplotlib (version >= 3.7.1)
- pypdf (version >= 4.2.0)
- pylatex (version >= 1.4.1)
- openpyxl (version >= 3.0.10)
- pdflatex (pdfTeX version >= 3.141592653-2.6-1.40.25, TeX Live 2023)

Most of these requirements can be installed easily using an [Anaconda](https://www.anaconda.com) environment. After installing Anaconda, open the Anaconda command line and execute:

```
conda create --name photoroster
conda activate photoroster
conda install pandas matplotlib openpyxl
pip3 install --break-system-packages pypdf pylatex
``` 

`pdflatex` is a compiler for LaTeX. It needs to be installed for your system, e.g., using [MikTeX](https://miktex.org/) for Windows and [MacTeX](https://tug.org/mactex/mactex-download.html) for Mac.

To check that pdflatex is installed correctly, open the command line and try:

```
which pdflatex
```

This should return the path to running pdflatex. The script uses this pdflatex by default; if it is not on your `PATH`, pass its path with `--pdflatex` (see [Options](#options)).

## Setup

### File Organization

Your file directory should be organized as shown below. A different data directory and output file can be given with `--data-dir` and `--output` (see [Options](#options)).

```	
PhotoRosterBySeatAssignment
├── README.md
├── data-{QUARTER}
│  ├── roster-{EXAM}.xlsx
│  ├── photo-roster-{EXAM}.pdf
│  ├── seating-{EXAM}.xlsx
│  ├── photos (created automatically)
│  └── {COURSE_NAME} {EXAM_NAME} Photo Roster (Seating).pdf (the output)
└── src
   ├── main.py
   └── cliargs.py
```
1. `data-{QUARTER}` is the directory that should contain all input and output files for a particular quarter `{QUARTER}`.

2. `roster-{EXAM}.xlsx` is the student roster for your class for the exam `{EXAM}`, which can be obtained by copying the output of WebRoster into an Excel spreadsheet.

	This file should be formatted as follows: 
	- Must be an Excel spreadsheet (i.e., a .xlsx file)
	- Should only have 3 columns: (StudentID, StudentName, Email)
	- Should list all extension students at the **end** of this file.
	- No header lines, e.g., cell A1 should contain the first student ID number

3. `photo-roster-{EXAM}.pdf` is the photo roster for your class for the exam `{EXAM}`, which can be obtained by downloading the PDF Photo Roster from WebRoster. You should not make any changes to this file. However, it is recommended that this copy includes each student's photo, name, and ID.

4. `seating-{EXAM}.xlsx` is the seating assignment for the exam `{EXAM}`. 

	This file should be formatted as follows: 
	- Must be an Excel spreadsheet (i.e., a .xlsx file)
	- Should only have 2 columns: (StudentName, SeatAssignment)
	- No header lines, e.g., cell A1 should contain the first student ID number
	- The StudentName column must exactly match the name in `roster.xlsx`,
	  including any capitalization and spacing
	- The SeatAssignment column must contain seats in one of the formats:
		- `{ROW}-{SEATNUM}`, e.g., A-1, B-3, C-22
		- `{ROW}-{SEATNUM}(L)`, e.g., A-19(L), F-23(L)
			
	Other notes: 
	- Order of students in this file does not matter

5. `photos` holds each student's photo, extracted from the photo roster. It is created automatically if it does not exist.

6. `main.py` contains the source code for generating the ordered photo rosters, and `cliargs.py` defines its command-line options (see [Options](#options)).

### Defining Seat Partitions<a id="defining-seat-partitions"></a>

Most lecture halls on campus partition seats in one of two ways: 

1. *numerically* (all rows in the lecture hall increase numerically in one direction, e.g., left to right).

2. *odds, evens, and center*: the lecture hall is divided into 3 sections: odd number seats under 100, even number seats under 100, and seats > 100.
   
To group students based on the seat numbers in the lecture hall correctly, the `--seats-partition` option should be set as follows:

- If (1), then use `--seats-partition numeric`.
- If (2), then use `--seats-partition odd-even`.

## Order of the roster and photos

This script generates the sorted seating assignment by assuming that the index of where the student is located on the roster corresponds directly with the location of the student in the photo roster, i.e., the student roster and the photo roster are in the same order.

In general, **THIS IS NOT TRUE BY DEFAULT**: there are some inconsistencies that appear between the orders presented in the student roster and photo roster. Thus, some corrections need to be made for this order. Specifically, the photo roster seems to order based only on the LAST name, so if two students have the same last name, then their order in the photo roster seems to be random.

The first time you run the script, students with the same last name will be identified and printed. You should manually examine these names and reorder the student roster accordingly. *If this is not done correctly, then the resulting photo roster may be incorrect for these students!!*

## Running

The python script should be able to be run from the project root using, e.g.: 

```
conda activate photoroster # if you have not yet activated it
python src/main.py --course-name "CS143A Lec A" --quarter f26 --exam me1 --exam-date "Oct 30, 2026" --seats-partition numeric --debug false
python src/main.py --course-name "CS143A Lec A" --quarter sample --exam me1 --exam-date "Oct 30, 2026" --seats-partition numeric --debug false
```

If successful, "Done" is printed at the end. 

### Options<a id="options"></a>

Run `python src/main.py --help` to list these options.

| Option | Description |
|---|---|
| `--course-name` (required) | the course name, e.g., *ICS XXX Lec A* |
| `--exam` (required) | a shortened exam name: one of *me1*, *me2*, *me*, *fe*. This selects the `roster-{EXAM}.xlsx`, `photo-roster-{EXAM}.pdf`, and `seating-{EXAM}.xlsx` input files |
| `--exam-date` (required) | the date of the exam, e.g., *Jan 1, 2024* |
| `--seats-partition` (required) | the partitions of seats in the lecture hall: `numeric` or `odd-even`. See [Defining Seat Partitions](#defining-seat-partitions) |
| `--quarter` | the current quarter (and optional lecture), e.g., *f19*, *s24b*. Uses the `data-{QUARTER}` directory in the project root |
| `--data-dir` | the data directory to use instead of `data-{QUARTER}`. Exactly one of `--quarter` or `--data-dir` must be given |
| `--exam-name` | the name of the exam shown in the output, e.g., *Midterm 1*. Defaults to *Midterm 1*, *Midterm 2*, *Midterm*, or *Final* based on `--exam` |
| `-o`, `--output` | the filename for the output ordered photo roster. Defaults to `{DATA_DIR}/{COURSE_NAME} {EXAM_NAME} Photo Roster (Seating).pdf` |
| `--pdflatex` | the path for the pdflatex executable. Defaults to the one returned by `which pdflatex` |
| `--debug` | `true` or `false` (default `false`). If `true`, print both photos and names. This can be used to check that the ordering of the roster is correct |

## Odds and Ends

- For each exam, you should obtain the latest version of the student roster and photo roster, to ensure that students who have since added or dropped do not cause a "one-off" problem.
- For ease in checking photos during the exam, you may want to move anyone that does not have a photo in the photo roster to the front row. This mainly consists of students in the roster with an anteater photo and extension students. 
- Again, please check that student photos and the roster are in the same order. You can check everyone in a verbose way using --debug true
  
