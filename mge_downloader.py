"""
 29.08.2020
 Christopher Schuster
 Uploads files to and results from MEFinder
 https://cge.cbs.dtu.dk/services/MobileElementFinder/

"""

__version__ = "0.1.0"
__author__ = "Christopher Schuster"

# standard library imports
import argparse
import asyncio
from collections import defaultdict
import datetime
import json
import os
import pathlib
import sys
from typing import Union

# external imports
from selenium import webdriver
from selenium.webdriver.common.by import By

#############################################################################
# CONFIG
ACCESS_URL = 'https://cge.cbs.dtu.dk/services/MobileElementFinder/'
RESULT_FILENAME = "status.json"
FILTERED_RESULTS_FILENAME = "filtered_results.tsv"
URL_FILENAME = "urls.txt"
WAIT_TIME_LOAD_GRACE = 10  # seconds
WAIT_TIME_PAGE_CHANGE = 30  # seconds
MIN_WAIT_TIME = 5  # minutes
MIN_FETCH_TIME = 5  # minutes
#############################################################################

#############################################################################
# GLOBAL VARS TO HOLD INTERMEDIATE RESULTS
RESULTS = defaultdict(list)
FILTERED_RESULTS = []
URLS = []
#############################################################################


def update_urls(url: str, base_dir: pathlib.Path, fasta_file: str):
    """
    Retrieves an URL, adds it to the URL list and writes out into
    a txt file (only URLs) or an HTML file (with FASTA names)

    :param url: str URL to results
    :param base_dir: base dir where all results are stored
    :param fasta_file: complete file path of the fasta file

    :return: bool, success or not
    """

    base_filename = f"{os.path.basename(fasta_file)}"
    URLS.append([url, base_filename])

    try:
        with open(base_dir / URL_FILENAME, "w") as f_out:
            f_out.write("".join([url[0] for url in URLS]))
    except Exception as e:
        print(f"Error saving text file of urls: {url}: {e}", file=sys.stderr)
        return False

    try:
        with open(base_dir / f"{URL_FILENAME}.html", "w") as f_out:
            f_out.write("<html>\n<body>\n<h1>Results</h1>\n<br><table>")
            f_out.write("\n".join([f"<tr><td>{url[1]}</td>"
                                   f"<td><a href=\"{url[0]}\">{url[0]}</a></td></tr>"
                                   for url in URLS]))
            f_out.write("\n</table>\n</body>\n</html>")
    except Exception as e:
        print(f"Error saving HTML file of urls: {url}: {e}", file=sys.stderr)
        return False

    return True


def update_json(run_id: int, base_dir: pathlib.Path, msg: str):
    """
    Retrieves a run_id and a msg to be appended to the results dict,
    This is then exported to a json file
    Returns bool

    :param run_id: int. internal id
    :param base_dir: base directory to save files
    :param msg: message to be logged
    :return: bool. Success
    """
    try:
        RESULTS[run_id].append(f"{datetime.datetime.now()}: {msg}")
        with open(base_dir / RESULT_FILENAME, "w") as f_out:
            f_out.write(json.dumps(RESULTS, indent=2))
    except Exception as e:
        print(f"{run_id}: Error saving JSON file: {e}", file=sys.stderr)
        return False

    return True


'''
# Future proofing
def sanitize_search_string(search_str: str):
    return''.join([c if c.isalnum() else '' for c in search_str])


def filter_results_table_regex(search_str: str, result_table: str):
    # search_str="(.*(?:ctx|inc).*)"
    return '____\t'.join(re.findall(f"{search_str}", result_table, re.IGNORECASE + re.MULTILINE))
'''


def filter_results_table(search_str: str, result_table: str) -> str:
    """
    Uses search_str to locate interesting elements in the lines of the results table
    Expected format of results table: Result1\nResult2\n

    :param search_str: str: text to be present
    :param result_table: str: results extracted from table
    :return: str. Tab concatenated lines that matched
    """
    return "____\t".join([line for line in result_table.split("\n") if line.lower().find(search_str.lower()) >= 1])


def update_and_save_filtered_file(run_id: int, base_dir: pathlib.Path, fasta_filename: str,
                                  search_filter: str, result_table: str) -> bool:
    """Extracts data from current result, updates extracted results table an saves in a file

    :param run_id: int: id of run
    :param base_dir: path: directory where all results are saved
    :param fasta_filename: str: current fasta file name
    :param search_filter: str: string
    :param result_table: str: extracted table with results
    :return: bool: success
    """
    try:
        filtered_data = filter_results_table(search_filter, result_table)
    except Exception as e:
        print(f"{run_id}: Error filtering table: {e}", file=sys.stderr)
        return False

    try:
        FILTERED_RESULTS.append("\t".join([str(run_id), fasta_filename, filtered_data]))
        with open(base_dir / FILTERED_RESULTS_FILENAME, "w") as f_out:
            f_out.write("\n".join(FILTERED_RESULTS))
    except Exception as e:
        print(f"{run_id}: Error saving filtered table: {e}", file=sys.stderr)
        return False

    return True


async def upload(run_id: int, base_dir: pathlib.Path, fasta: str) -> Union[str, None]:
    """Upload FASTA file to mgefinder. Then wait for queued URL and return

    :param run_id: id of current run
    :param base_dir: path: directory where all results are saved
    :param fasta: str: current fasta file name
    :return: str: URL of where result can be fetched
    """

    print(f"{run_id}: STARTING UPLOAD")
    print(f"{run_id}: Creating driver")
    update_json(run_id, base_dir, "ACCESSING UPLOAD")
    driver = webdriver.Chrome()

    # Open page
    print(f"{run_id}: Opening url: {ACCESS_URL}")
    try:
        driver.get(ACCESS_URL)
    except Exception as err:
        driver.quit()
        print(f"{run_id}: ERROR: Cannot access upload page {ACCESS_URL}, {err}", file=sys.stderr)
        print(type(err))
        print(err)
        update_json(run_id, base_dir, f"ERROR, UPLOAD PAGE NOT ACCESSIBLE, {err}")
        return None
    print(f"{run_id}: Giving the page some time to load additional resources.")
    await asyncio.sleep(WAIT_TIME_LOAD_GRACE)

    # Submit File
    try:
        print(f"{run_id}: Switching to iframe")
        driver.switch_to.frame('myIframe')
        inp = driver.find_elements(By.XPATH, '//input')[0]
        print(f"{run_id}: Sending file path {fasta} for upload")
        inp.send_keys(fasta)
        await asyncio.sleep(2)
        update_json(run_id, base_dir, "SUBMITTING")
        print(f"{run_id}: Submitting job and waiting for upload to finish.")
        url_before_submission = driver.current_url
        driver.find_elements(By.XPATH, '//button')[1].click()
    except Exception as err:
        driver.quit()
        print(f"{run_id}: ERROR: Couldn't submit fasta file: {err}", file=sys.stderr)
        update_json(run_id, base_dir, "ERROR, FASTA COULD NOT BE UPLOADED")
        return None

    # Poll for result
    await asyncio.sleep(WAIT_TIME_PAGE_CHANGE)
    retries_left = 20
    while url_before_submission == driver.current_url:
        if retries_left < 1:
            print(f"{run_id}: WARNING: Oh oh... URL did not change but retries were exhausted!", file=sys.stderr)
            update_json(run_id, base_dir, "WARNING, RESULT URL COULD NOT BE RETRIEVED AFTER SUBMISSION")
            return None
        print(f"{run_id}: Waiting for page to reload... Retries left: {retries_left}")
        await asyncio.sleep(WAIT_TIME_PAGE_CHANGE)
        retries_left -= 1

    url = driver.current_url
    update_json(run_id, base_dir, "UPLOADED")
    update_json(run_id, base_dir, url)

    print(f"{run_id}: New url is {url}")
    driver.quit()
    return url


async def download(run_id: int, base_dir: pathlib.Path, fasta: str, url: str, search_filter: str) -> bool:
    """
    Download and then extract the results from an upload to mgefinder

    :param run_id: int: internal id
    :param base_dir: path: base directory
    :param fasta: str: file path to fasta file
    :param url: str: url of the result
    :param search_filter: str: what to filter on in results
    :return: bool: success
    """
    # Open URL to retrieve result
    print(f"{run_id}: Creating driver")
    driver = webdriver.Chrome()

    print(f"{run_id}: Fetching {url}")
    update_json(run_id, base_dir, f"REQUESTING URL {url}")
    try:
        driver.get(url)
    except Exception as err:
        driver.quit()
        print(f"{run_id}: ERROR: Cannot access page {url}. {err}", file=sys.stderr)
        update_json(run_id, base_dir, "ERROR FETCHING RESULT. {err}")
        return False

    print(f"{run_id}: Giving the page a few more seconds to load...")

    await asyncio.sleep(WAIT_TIME_LOAD_GRACE)
    base_filename = f"{os.path.basename(fasta)}"

    # Save page
    print(f"{run_id}: Attempting to save page {url} to {run_id}_{base_filename}.html...")
    curated_table = ''
    try:
        with open(base_dir / f"{run_id}_{base_filename}.html", 'w') as f_html:
            f_html.write(driver.page_source)
    except Exception as err:
        print(f"{run_id} ERROR: ----->Something went wrong when downloading page: {err}", file=sys.stderr)
        driver.quit()
        update_json(run_id, base_dir, f"DOWNLOAD ERROR. {err}")
        return False

    try:
        print(f"{run_id}: Locating results table")
        table = driver.find_element(By.XPATH, "//table[@id='summary-table']")
        update_json(run_id, base_dir, f"LOCATED TABLE")
    except Exception as err:
        print(f"{run_id} ERROR: Could not find results table in page. Possibly the wait to "
              f"fetch result is too short! Please extend wait time. Details: {err}", file=sys.stderr)
        driver.quit()
        update_json(run_id, base_dir, f"ERROR LOCATING RESULTS TABLE. {err}")
        return False

    try:
        print(f"{run_id}: Extracting content table")
        for row in table.find_elements_by_tag_name("tr"):
            line = '\t'.join([cell.text for cell in row.find_elements_by_tag_name("td")])+"\n"
            curated_table += line
        update_json(run_id, base_dir, f"EXTRACTED TABLE CONTENT")
    except Exception as err:
        print(f"{run_id} ERROR: Could not extract results from results table: {err}", file=sys.stderr)
        driver.quit()
        update_json(run_id, base_dir, f"ERROR EXTRACTING RESULTS FROM TABLE. {err}")
        return False

    try:
        print(f"{run_id}: Saving extracted table")
        with open(base_dir / f"{run_id}_{base_filename}.txt", 'w') as f_txt:
            f_txt.write(curated_table)
        driver.quit()
        update_json(run_id, base_dir, f"SAVED TABLE CONTENT TO FILE")
        print(f"{run_id}: Extracted table was saved")
    except Exception as err:
        print(f"{run_id} ERROR: Could not write results table to file: {err}", file=sys.stderr)
        driver.quit()
        update_json(run_id, base_dir, f"ERROR SAVING EXTRACTED RESULTS. {err}")
        return False

    if len(search_filter) > 0:
        print(f"{run_id}: Attempting to filter extracted data")
        update_and_save_filtered_file(run_id, base_dir, base_filename, search_filter, curated_table)
        update_json(run_id, base_dir, f"FILTERED DATA FROM TABLE")

    update_json(run_id, base_dir, "DOWNLOADED AND EXTRACTED DATA")
    print(f"{run_id}: Finished download and extraction of results.")

    return True


async def handle_upload_and_download(run_id: int, base_dir: pathlib.Path, fasta: str,
                                     wait_to_fetch: int, search_filter: str) -> bool:
    """
    Upload fasta files and then download result.

    :param run_id: int: internal id
    :param base_dir: path: base output directory
    :param fasta: str: path to fasta file
    :param wait_to_fetch: int: time to wait before fetching result
    :param search_filter: str: what to filter on in results
    :return: bool, success
    """
    print(datetime.datetime.now())
    print(f"Starting procedure for #{run_id} --> {fasta}")
    update_json(run_id, base_dir, fasta)
    url = await asyncio.shield(upload(run_id, base_dir, fasta))
    if not url:
        print(f"{run_id}: ERROR: no URL received to download from.", file=sys.stderr)
        return False
    update_urls(url, base_dir, fasta)
    await asyncio.sleep(60*wait_to_fetch)
    await download(run_id, base_dir, fasta, url, search_filter)
    return True


# Schedule tasks
async def scheduler(base_dir: pathlib.Path, files: list, time_to_next: int,
                    wait_to_fetch: int, search_filter: str) -> None:
    """
    Schedule all tasks one after the other

    :param base_dir: path: base output directory
    :param files: list: fasta file
    :param time_to_next: int: time to wait before submitting a new FASTA
    :param wait_to_fetch: int: time to wait before fetching result
    :param search_filter: str: what to filter on in results
    :return: None
    """

    for run_id, fasta in enumerate(files[:-1]):
        asyncio.create_task(handle_upload_and_download(run_id, base_dir, fasta, wait_to_fetch, search_filter))
        await asyncio.sleep(60*time_to_next)
    # Cheating to wait for all tasks
    await asyncio.shield(handle_upload_and_download(len(files)-1, base_dir, files[-1], wait_to_fetch, search_filter))

    print("Adding extra wait time to make sure all threads have finished."
          "If you are sure all threads are done, hit CTRL-C to stop execution.")
    await asyncio.sleep(60*wait_to_fetch)
    print("Thank you. Please come again.")


def return_arg_parser():
    """
    Uses argparse to provide cli interface
    :return: an argparse.parse_args() object
    """
    parser = argparse.ArgumentParser(description="Upload fasta file to mefinder and download results.",
                                     epilog="Examples:\n"
                                            "  Submit files fasta1.fna and my_fasta2.fna:\n"
                                            "    python mge_downloader.py --outdir dir1 my_fasta1.fna my_fasta2.fna\n"
                                            "  Submit all fasta files in current directory:\n"
                                            "    python mge_downloader.py --outdir dir2 *.fasta\n"
                                            "  Submit all .fna files in current directory and filter for bla:\n"
                                            "    python mge_downloader.py --outdir dir3 *.fna --filter bla",
                                     formatter_class=argparse.RawTextHelpFormatter)
    parser.add_argument("--outdir", required=True, metavar="directory", type=pathlib.Path,
                        help="directory that should be used to place the output.")
    parser.add_argument("--time-to-next", metavar="minutes", default=5, type=int,
                        help="Number of minutes to wait before sending next fasta file")
    parser.add_argument("--time-to-fetch-result", metavar="minutes", default=30, type=int,
                        help="Number of minutes to wait before fetching the result")
    parser.add_argument("--filter", metavar="filter_string", default='', type=str,
                        help="Filter a specific output from results table")
    parser.add_argument("files", metavar="fasta file(s)", type=pathlib.Path, nargs="+",
                        help="fastA files.")
    args = parser.parse_args()
    return args


def check_args(args):
    """
    Check parameters and adjust values as needed

    :param args: argparse args
    :return: returns the cleaned up parameters
    """
    if args.time_to_next < MIN_WAIT_TIME:
        print(f"WARNING: Wait time too short."
              f"Setting to the minimum, {MIN_WAIT_TIME} [min].", file=sys.stderr)
        args.time_to_next = MIN_WAIT_TIME

    if args.time_to_fetch_result < MIN_FETCH_TIME:
        print(f"WARNING: Fetch time after submission too short."
              f"Setting to the minimum, {MIN_FETCH_TIME} [min].", file=sys.stderr)
        args.time_to_fetch_result = MIN_FETCH_TIME

    if args.outdir.exists():
        if args.outdir.is_dir() and os.listdir(args.outdir) == []:
            print(f"WARNING: Directory '{args.outdir}' already exists. "
                  f"Using this directory anyway because it is empty.", file=sys.stderr)
        else:
            print(f"ERROR: Directory '{args.outdir}' already exists. Will not overwrite. "
                  f"Please change directory name or remove directory. Exiting now.", file=sys.stderr)
            return None
    else:
        os.mkdir(args.outdir)

    fasta_files = [str(fp.absolute()) for fp in args.files]

    # Parameters
    print("PARAMETERS")
    print(f"FASTAs: {', '.join(fasta_files)}")
    print(f"outdir: {args.outdir}")
    print(f"time_to_fetch_result: {args.time_to_fetch_result} min")
    print(f"time_to_next: {args.time_to_next} min")
    if len(args.filter) > 0:
        print(f"Filter: ON. Search for '{args.filter}'")
    else:
        print("Filter: OFF")
    print("=" * 50)

    return args


def estimate_completion(num_files: int, time_to_next: int, time_to_fetch_result: int):
    """
    Estimate when the up- and download will be finished and prints to console

    :param num_files: number of fasta files
    :param time_to_next: time until next upload
    :param time_to_fetch_result: time to wait until result is fetched
    :return: None
    """
    execution_time = num_files + (num_files-1) * time_to_next + time_to_fetch_result
    completed_by = datetime.datetime.now()+datetime.timedelta(minutes=execution_time)
    print(f"{num_files} file(s). Estimated execution time: {execution_time} min.")
    print(f"Now: {datetime.datetime.now():%x %X}. Estimated completion at: {completed_by:%x %X}")
    print("=" * 50)


def main():
    """
    Main logic. Fetch the parameters, do a sanity check and run program

    :return: int.
        ZERO=Ran (although errors might have been encountered)
        -1=did not run at all
    """
    print(f"================= mgefinder {__version__} =================")

    args = return_arg_parser()
    clean_args = check_args(args)
    if not clean_args:
        return -1
    fasta_files = [str(fp.absolute()) for fp in clean_args.files]
    base_dir = clean_args.outdir
    estimate_completion(len(fasta_files), clean_args.time_to_next,  clean_args.time_to_fetch_result)
    search_filter = args.filter

    asyncio.run(scheduler(base_dir, fasta_files, clean_args.time_to_next,
                          clean_args.time_to_fetch_result, search_filter))

    return 0


if __name__ == "__main__":
    main()
