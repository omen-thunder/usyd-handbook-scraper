import argparse
import csv
from datetime import datetime
from itertools import zip_longest
import multiprocessing as mp
import re
import requests


base_url = 'https://www.sydney.edu.au'
current_year = datetime.now().year


def join_url(page_url, link):
    if link[:1] == '/':
        return base_url + link
    elif link[:7] == 'http://' or link[:8] == 'https://':
        return link
    else:
        return page_url + link


def get_faculties(year):
    # checks if the requested year is current or an archive
    if year == current_year:
        page_url = base_url + '/handbooks/'
    else:
        page_url =  base_url + '/handbooks/archive/' + str(year) + '/'

    html = requests.get(page_url).text
    # search the page for the requested handbooks table
    search = re.search(f'{year} Handbooks[\s\S]*{year - 1} Handbooks', html)
    # if the requested handbooks table isn't found,
    # use the whole page instead
    table = search[0] if search else html
    # find each cell in the table
    cells = re.findall('<td[\s\S]*?\/td>', table)
    # remove the cells that don't contain links
    cells = [cell for cell in cells if 'href' in cell]
    # regex for getting the href tag and it's contents
    faculty_links = [re.search('href\s*=\s*[\'\"].*?[\'\"]', cell)[0] for cell in cells]
    # regex for getting just the link
    faculty_links = [re.search('(?<=[\'\"]).*?(?=[\'\"])', link)[0] for link in faculty_links]
    faculty_urls = [join_url(page_url, link) for link in faculty_links]

    return faculty_urls


def faculty_name(url):
    if 'archive' in url:
        name = re.search('\d+\/\w+', url)[0]
        name = re.search('(?<=\/)\w+', name)[0]
        return name
    else:
        name = re.search('handbooks\/\w+', url)[0]
        name = re.search('(?<=\/)\w+', name)[0]
        return name


def good_link(link, page_url):
    if link[:7] == 'http://':
        return False
    if link[:8] == 'https://':
        return False
    if link[:3] == '../':
        return False
    if link[:1] == '/' and page_url not in base_url + link:
        return False
    if 'contacts' in link:
        return False
    if 'errata' in link:
        return False
    if 'rules' in link:
        return False
    if 'governance' in link:
        return False

    return True


# recursively search for units of study
def search(url):
    # regex for getting the current directory from the url
    page_url = re.search('.*\/', url)[0]
    
    html = requests.get(url).text
    # regex for getting the strong tags with unit codes
    units = re.findall('<\s*strong\s*>[A-Z]{4}\d{4}', html)
    # regex for getting just the unit codes
    units = [re.search('[A-Z]{4}\d{4}', unit)[0] for unit in units]

    # regex for getting the href tags and their contents
    links = re.findall('href\s*=\s*[\'\"].*?\.shtml.*?[\'\"]', html)
    # regex for getting just the links
    links = [re.search('(?<=[\'\"]).*?(?=[\'\"])', link)[0] for link in links]
    # removing links that are unlikely to lead to unit of study tables
    links = [link for link in links if good_link(link, page_url)]
    urls = [join_url(page_url, link) for link in links]
    urls = list(set(urls))

    return units, urls


def worker(unit_queue, start_url, max_depth):
    url_queue = [(start_url, 0)]
    searched = []
    units = set()
    while url_queue:
        url, depth = url_queue.pop(0)
        if depth > max_depth:
            break

        searched.append(url)
        new_units, new_urls = search(url)
        units.update(new_units)
        new_urls = [url for url in new_urls if url not in searched]
        new_urls = [(url, depth + 1) for url in new_urls]
        url_queue += new_urls

    unit_queue.put(units)
    print(f'{start_url} done')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='A tool for comparing USyd units of study between years.')
    parser.add_argument('years', type=int, nargs='+', help='The years for comparison, separated by spaces.')
    parser.add_argument('-d', '--depth', type=int, default=2, help='The search depth.')
    parser.add_argument('-f', '--faculty', action='store_true', help='If set, search by faculty.')
    parser.add_argument('-o', '--output', type=str, default='out.csv', help='The output path.')
    args = parser.parse_args()

    columns = []
    headers = [str(year) for year in args.years]
    for idx, year in enumerate(args.years):
        faculty_urls = get_faculties(year)
        if args.faculty:
            print('Enter the indices of faculties to search, separated by spaces:')
            print('E.g. 0 1 4\n')
            for i, url in enumerate(faculty_urls):
                print(f'[{i}]\t{year} {faculty_name(url)}')

            print()
            indices = input().split(' ')
            indices = [int(i) for i in indices]
            faculty_urls = [faculty_urls[i] for i in indices]
            for url in faculty_urls:
                headers[idx] = headers[idx] + f' {faculty_name(url)}'

        unit_queue = mp.Queue()
        processes = []
        for url in faculty_urls:
            process = mp.Process(target=worker, args=(unit_queue, url, args.depth))
            processes.append(process)
            process.start()

        units = set()
        for process in processes:
            units.update(unit_queue.get())

        columns.append(sorted(list(units)))

    if len(columns) == 2:
        headers.append(f'In {headers[0]} but not {headers[1]}')
        columns.append(sorted(list(set(columns[0]) - set(columns[1]))))
        headers.append(f'In {headers[1]} but not {headers[0]}')
        columns.append(sorted(list(set(columns[1]) - set(columns[0]))))

    for col in columns:
        col.append('')
        col.append(f'total: {len(col)}')

    with open(args.output, 'w') as f:
        writer = csv.writer(f)
        writer.writerow(headers)
        rows = zip_longest(*columns, fillvalue='')
        writer.writerows(rows)

