# USYD Handbook Scraper
This tool catalogs and compares the University of Sydney's available units of study by year and faculty.
The units of study are scraped from the [USYD handbooks online website](https://www.sydney.edu.au/handbooks/).

## Usage
```commandline
usage: scaper.py [-h] [-d DEPTH] [-f] [-o OUTPUT] years [years ...]

A tool for comparing USyd units of study between years.

positional arguments:
  years                 The years for comparison, separated by spaces.

options:
  -h, --help            show this help message and exit
  -d DEPTH, --depth DEPTH
                        The search depth.
  -f, --faculty         If set, search by faculty.
  -o OUTPUT, --output OUTPUT
                        The output path.
```

### Examples
```commandline
python3 scraper.py 2022
python3 scraper.py -d 3 -f -o 2021-2022_arts.csv 2021 2022
```

### Output
The script outputs a CSV file with a column for each input year.
If exactly two input years are provided, the output file will contain two additional comparison columns.
