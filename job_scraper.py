import time
import random

import pandas as pd
import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin
import json
import re
from datetime import datetime
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed

# --- CONFIG ---
KEYWORDS = ['backend', 'back-end', 'back end', 'software', 'full-stack', 'fullstack', 'full stack', 'java', 'front-end',
            'front end', 'frontend', 'developer', 'infrastructure', 'ui', 'devops', 'programmer', 'spring',
            'api', 'cloud', 'co-op', 'user interface', 'application' , 'junior' , 'ai' , 'artificial Intelligence']

NO_KEYWORDS = ['manager', 'staff', 'senior', 'director', "embedded", 'c++', 'machine', 'principal', 'lead',
               'recruit', 'vice president', 'talent']

# --- Error logging ---
error_messages = []

def log_error(company, message):
    error_messages.append(f"[ERROR] {company}: {message}")

# --- Load input file ---
# companies_df = pd.read_csv('companies.csv')
# Link to the file -- please add more companies to this as you find them
# https://drive.google.com/file/d/1oPIqvsKTcXw7zS2gtlrSsFl3bmjbxg17/view?usp=sharing

# file_id = '1oPIqvsKTcXw7zS2gtlrSsFl3bmjbxg17'
# url = f'https://drive.google.com/uc?export=download&id={file_id}'

companies_df = pd.read_csv('companies.csv')

results = []


def keyword_match(title):
    title_lower = title.lower()
    has_positive = any(k in title_lower for k in KEYWORDS)
    has_negative = any(nk in title_lower for nk in NO_KEYWORDS)
    return has_positive and not has_negative


def is_us_location(location):
    if not location:
        return True
    location_lower = location.lower()
    # print(location_lower)

    us_keywords = [
        'united states', 'usa', 'us', 'remote - us', 'remote usa', 'remote (us)'
    ]

    # Full state names
    us_states_full = [
        'alabama', 'alaska', 'arizona', 'arkansas', 'california', 'colorado', 'connecticut', 'delaware',
        'florida', 'georgia', 'hawaii', 'idaho', 'illinois', 'indiana', 'iowa', 'kansas', 'kentucky',
        'louisiana', 'maine', 'maryland', 'massachusetts', 'michigan', 'minnesota', 'mississippi',
        'missouri', 'montana', 'nebraska', 'nevada', 'new hampshire', 'new jersey', 'new mexico',
        'new york', 'north carolina', 'north dakota', 'ohio', 'oklahoma', 'oregon', 'pennsylvania',
        'rhode island', 'south carolina', 'south dakota', 'tennessee', 'texas', 'utah', 'vermont',
        'virginia', 'washington', 'west virginia', 'wisconsin', 'wyoming'
    ]

    # State abbreviations
    us_states_abbr = [
        'al', 'ak', 'az', 'ar', 'ca', 'co', 'ct', 'de', 'fl', 'ga', 'hi', 'id', 'il', 'in', 'ia', 'ks', 'ky',
        'la', 'me', 'md', 'ma', 'mi', 'mn', 'ms', 'mo', 'mt', 'ne', 'nv', 'nh', 'nj', 'nm', 'ny', 'nc', 'nd',
        'oh', 'ok', 'or', 'pa', 'ri', 'sc', 'sd', 'tn', 'tx', 'ut', 'vt', 'va', 'wa', 'wv', 'wi', 'wy'
    ]

    return (
            any(keyword in location_lower for keyword in us_keywords)
            or any(state in location_lower for state in us_states_full)
            or any(re.search(r'\b' + abbr + r'\b', location_lower) for abbr in us_states_abbr)
            or re.search(r',\s*us$', location_lower)
            or re.search(r',\s*usa$', location_lower)
    )


def scrape_greenhouse_json(url, company):
    # print(f"Scraping Greenhouse for {company}")
    try:
        # Extract org name from URL
        match = re.search(r'greenhouse.io/([^/]+)', url)
        if not match:
            log_error(company, "Could not extract Greenhouse company name")
            return

        org = match.group(1)
        api_url = f"https://boards-api.greenhouse.io/v1/boards/{org}/jobs"
        r = requests.get(api_url)
        if r.status_code != 200:
            log_error(company, f"Greenhouse API failed: {r.status_code}")
            return
        jobs = r.json().get('jobs', [])
        for job in jobs:
            title = job['title']
            location = job.get('location', {}).get('name', 'N/A')
            link = job['absolute_url']
            postedOn = job['first_published']
            updatedOn = job['updated_at']
            if keyword_match(title) and link not in old_links and is_us_location(location):
                results.append(
                    {'company': company, 'title': title, 'location': location, 'link': link, 'postedOn': postedOn,
                     'updatedOn': updatedOn})
                old_links.add(link)
    except Exception as e:
        log_error(company, f"Greenhouse error: {e}")


def scrape_lever_json(url, company):
    # print(f"Scraping Lever for {company}")
    try:
        # Extract org name from URL
        match = re.search(r'lever.co/([^/]+)', url)
        if not match:
            log_error(company, "Could not extract Lever company name")
            return

        org = match.group(1)
        if re.search(r'eu.lever.co/([^/]+)', url):
            api_url = f"https://api.eu.lever.co/v0/postings/{org}?mode=json"
        else:
            api_url = f"https://api.lever.co/v0/postings/{org}?mode=json"
        r = requests.get(api_url)
        if r.status_code != 200:
            log_error(company, f"Lever API failed: {api_url} - {r.status_code}")
            return
        jobs = r.json()
        for job in jobs:
            title = job['text']
            location = job.get('categories', {}).get('location', 'N/A')
            created_at_raw = job.get('createdAt')
            postedOn = (
                datetime.utcfromtimestamp(created_at_raw / 1000).strftime('%Y-%m-%d %H:%M:%S')
                if created_at_raw else 'N/A'
            )
            updated_at_raw = job.get('updatedAt')
            updatedOn = (
                datetime.utcfromtimestamp(updated_at_raw / 1000).strftime('%Y-%m-%d %H:%M:%S')
                if updated_at_raw else 'N/A'
            )
            link = job['hostedUrl']
            if keyword_match(title) and link not in old_links and is_us_location(location):
                results.append(
                    {'company': company, 'title': title, 'location': location, 'link': link, 'postedOn': postedOn,
                     'updatedOn': updatedOn})
                old_links.add(link)
    except Exception as e:
        log_error(company, f"Lever error: {e}")


def scrape_ashby(url, company):
    # Not tested
    # print(f"Scraping Ashby for {company}")
    try:
        r = requests.get(url)
        match = re.search(r'careers\.([\w\-]+)\.com', url)
        if not match:
            log_error(company, f"Invalid Ashby URL: {url}")
            return
        domain = match.group(1)
        api_url = f"https://careers.{domain}.com/api/jobs"
        r = requests.get(api_url)
        if r.status_code != 200:
            log_error(company, f"Ashby API failed: {r.status_code}")
            return
        for job in r.json().get('jobs', []):
            title = job.get('title', '')
            location = job.get('location', 'N/A')
            link = f"https://careers.{domain}.com/jobs/{job['id']}"
            if keyword_match(title) and link not in old_links and is_us_location(location):
                results.append({'company': company, 'title': title, 'location': location, 'link': link})
                old_links.add(link)
    except Exception as e:
        log_error(company, f"Ashby scraping failed: {e}")


def scrape_ashbyhq_hosted(url, company):
    # print(f"Scraping Ashby REST API for {company}")
    try:
        match = re.search(r'ashbyhq\.com/([\w\-]+)', url)
        if not match:
            log_error(company, f"Invalid AshbyHQ URL: {url}")
            return
        org = match.group(1)

        api_url = f"https://api.ashbyhq.com/posting-api/job-board/{org}"
        response = requests.get(api_url)
        if response.status_code != 200:
            log_error(company, f"Ashby API failed - HTTP {response.status_code}: {response.text}")
            return

        data = response.json()
        for job in data.get('jobs', []):
            title = job.get('title', '')
            location = job.get('location', 'N/A')
            link = job.get('jobUrl', '')
            posted_raw = job.get('publishedAt')
            # posted_date = (
            #     datetime.fromisoformat(posted_raw.rstrip("Z")).strftime('%Y-%m-%d')
            #     if posted_raw else 'N/A'
            # )

            if keyword_match(title) and link not in old_links and is_us_location(location):
                results.append({
                    'company': company,
                    'title': title,
                    'location': location,
                    'link': link,
                    'postedOn': posted_raw
                })
                old_links.add(link)
    except Exception as e:
        log_error(company, f"Ashby REST API scraping failed: {e}")


def scrape_breezy(url, company):
    # print(f"Scraping Breezy for {company}")
    try:
        match = re.search(r'https?://([\w\-]+)\.breezy\.hr', url)
        if not match:
            log_error(company, f"Invalid Breezy URL: {url}")
            return
        org = match.group(1)
        api_url = f"https://{org}.breezy.hr/json"
        r = requests.get(api_url)
        if r.status_code != 200:
            log_error(company, f"Breezy API failed: {r.status_code}")
            return
        for job in r.json():
            title = job.get('name')
            location = job.get('location', 'N/A').get('name', 'N/A')
            postedOn = job.get('published_date', '')
            link = job.get('url')
            if keyword_match(title) and link not in old_links and is_us_location(location):
                results.append(
                    {'company': company, 'title': title, 'location': location, 'link': link, 'postedOn': postedOn})
                old_links.add(link)
    except Exception as e:
        log_error(company, f"Breezy: {e}")


def scrape_smartrecruiters(url, company):
    # print(f"Scraping SmartRecruiters for {company}")
    try:
        # match = re.search(r'company/([^/]+)', url)
        # org = match.group(1)
        api_url = f"https://api.smartrecruiters.com/v1/companies/{company}/postings"
        r = requests.get(api_url)
        if r.status_code != 200:
            log_error(company, f"SmartRecruiters API failed: {r.status_code}")
            return
        for job in r.json().get('content', []):
            title = job.get('name')
            location = job.get('location', {}).get('city', 'N/A')
            postedOn = job.get('releasedDate')
            link = f"https://www.smartrecruiters.com/{company}/{job.get('id')}"
            if keyword_match(title) and link not in old_links and is_us_location(location):
                results.append(
                    {'company': company, 'title': title, 'location': location, 'link': link, 'postedOn': postedOn})
                old_links.add(link)
    except Exception as e:
        log_error(company, f"SmartRecruiters: {e}")


def scrape_recruiterbox(url, company):
    # No tested
    # print(f"Scraping Recruiterbox for {company}")
    try:
        r = requests.get(url)
        if r.status_code != 200:
            log_error(company, f"Recruiterbox API failed: {r.status_code}")
            return
        soup = BeautifulSoup(r.text, 'html.parser')
        for job in soup.select('li a[href]'):
            title = job.text.strip()
            link = job['href']
            if not link.startswith("http"):
                link = url.rstrip("/") + "/" + link.lstrip("/")
            if keyword_match(title) and link not in old_links:  # and is_us_location(location):
                results.append({'company': company, 'title': title, 'location': 'N/A', 'link': link})
                old_links.add(link)
    except Exception as e:
        log_error(company, f"Recruiterbox: {e}")


def scrape_workable(url, company):
    # print(f"Scraping Workable for {company}")
    try:
        match = re.search(r'workable\.com/([^/]+)/?', url)
        if not match:
            log_error(company, f"Invalid Workable URL: {url}")
            return
        org = match.group(1)

        headers = {
            "Accept": "application/json",
            "Content-Type": "application/json"
        }

        # Try v3 with POST
        v3_url = f"https://apply.workable.com/api/v3/accounts/{org}/jobs"
        payload = {
            "query": "",
            # "limit": 100,
            # "offset": 0
        }

        r = requests.post(v3_url, headers=headers, json=payload)
        if r.status_code == 200:
            jobs = r.json().get('results', [])
            for job in jobs:
                title = job.get('title', '')
                location_data = job.get('location', {})
                city = location_data.get('city', 'N/A')
                region = location_data.get('region', '')
                location = f"{city}, {region}".strip(', ')
                shortcode = job.get('shortcode')
                link = f"https://apply.workable.com/{org}/j/{shortcode}/"

                # Extract and format posted date
                published_raw = job.get('published')
                # posted_date = (
                #     datetime.fromisoformat(published_raw.rstrip("Z")).strftime('%Y-%m-%d')
                #     if published_raw else 'N/A'
                # )

                if keyword_match(title) and link not in old_links and is_us_location(location):
                    results.append({
                        'company': company,
                        'title': title,
                        'location': location,
                        'link': link,
                        'postedOn': published_raw
                    })
                    old_links.add(link)
            return  # success with v3 POST

        # fallback to v1 GET
        v1_url = f"https://apply.workable.com/api/v1/accounts/{org}/jobs"
        r = requests.get(v1_url, headers=headers)
        if r.status_code != 200:
            log_error(company, f"Workable API failed (v3 & v1): {r.status_code}")
            return

        jobs = r.json()
        for job in jobs:
            title = job.get('title', '')
            location = job.get('location', 'N/A')
            shortcode = job.get('shortcode')
            link = f"https://apply.workable.com/{org}/j/{shortcode}/"

            published_raw = job.get('published')
            # posted_date = (
            #     datetime.fromisoformat(published_raw.rstrip("Z")).strftime('%Y-%m-%d')
            #     if published_raw else 'N/A'
            # )

            if keyword_match(title) and link not in old_links and is_us_location(location):
                results.append({
                    'company': company,
                    'title': title,
                    'location': location,
                    'link': link,
                    'postedOn': published_raw
                })
                old_links.add(link)

    except Exception as e:
        log_error(company, f"Workable scraping failed: {e}")


def scrape_workday(url, company):
    # print(f"Scraping Workday for {company}")
    try:
        # Match pattern: https://{sub}.wdX.myworkdayjobs.com/.../{site_id}
        match = re.search(r'https://([\w\-]+)\.(wd\d+)\.myworkdayjobs\.com/(?:[\w\-]+/)?([\w\-]+)', url)
        if not match:
            log_error(company, f"Invalid Workday URL")
            return

        subdomain, wd_instance, site_id = match.group(1), match.group(2), match.group(3)
        api_url = f"https://{subdomain}.{wd_instance}.myworkdayjobs.com/wday/cxs/{subdomain}/{site_id}/jobs"

        offset = 0
        page_size = 20
        total_jobs = 1000

        headers = {
            'Content-Type': 'application/json',
            'Accept': 'application/json'
        }

        while offset < total_jobs:
            payload = {
                "appliedFacets": {},
                "limit": page_size,
                "offset": offset,
                "searchText": ""
            }

            response = requests.post(api_url, json=payload, headers=headers)
            if response.status_code != 200:
                log_error(company, f"Workday API failed: HTTP {response.status_code} - {response.text}")
                return

            data = response.json()
            # total_jobs = data.get('total', 0)
            postings = data.get('jobPostings', [])
            offset += page_size

            for job in postings:
                title = job.get('title', '')
                location = job.get('locationsText', 'N/A')
                external_path = job.get('externalPath', '')
                postedOn = job.get('postedOn', '')
                link = f"https://{subdomain}.{wd_instance}.myworkdayjobs.com/en-US/{site_id}{external_path}"

                if keyword_match(title) and link not in old_links and is_us_location(location):
                    results.append({
                        'company': company,
                        'title': title,
                        'location': location,
                        'postedOn': postedOn,
                        'link': link
                    })
                    old_links.add(link)

    except Exception as e:
        log_error(company, f"Workday scraping failed: {e}")


# def scrape_jobvite(url, company):
#     print(f"Scraping Jobvite for {company}")
#     try:
#         match = re.search(r'jobvite\.com/([^/]+)', url)
#         if not match:
#             print(f"[ERROR] Invalid Jobvite URL for {company}: {url}")
#             return
#         org = match.group(1)
#         api_url = f"https://jobs.jobvite.com/api/v1/company/{org}/jobs"
#
#         r = requests.get(api_url)
#         if r.status_code != 200:
#             print(f"[ERROR] Jobvite API failed for {company}: HTTP {r.status_code} - {r.text}")
#             return
#
#         print(r.text)
        # for job in r.json():
        #     title = job.get('title', '')
        #     location = job.get('location', {}).get('city', 'N/A') + ', ' + job.get('location', {}).get('state', '')
        #     link = job.get('jobUrl')
        #     if keyword_match(title) and is_us_location(location) and link not in old_links:
        #         results.append({
        #             'company': company,
        #             'title': title,
        #             'location': location,
        #             'link': link,
        #             'postedOn': 'N/A'
        #         })

    # except Exception as e:
    #     print(f"[ERROR] Jobvite scraping failed for {company}: {e}")


def scrape_generic(url, company):
    # print(f"Scraping generic site for {company}")
    try:
        r = requests.get(url)
        soup = BeautifulSoup(r.text, 'html.parser')
        for a in soup.find_all('a', href=True):
            title = a.text.strip()
            link = urljoin(url, a['href'])
            if keyword_match(title) and link not in old_links:
                results.append({'company': company, 'title': title, 'location': 'N/A', 'link': link})
                old_links.add(link)
    except Exception as e:
        log_error(company, f"Generic scraping failed: {e}")


def scrape_company(row):
    company = row['company']
    url = row['careers_url']
    platform = row['platform'].lower()
    scraper = dispatch_map.get(platform)
    if scraper:
        try:
            if platform == "workday":
                # Sleep to respect Workday rate limits
                time.sleep(random.uniform(2.5, 4.0))  # 2.5–4 sec delay
            scraper(url, company)
        except Exception as e:
            log_error(company, f"Exception in scraping {platform}: {e}")
    else:
        log_error(company, f"Unsupported platform '{platform}'")


# Dispatcher
dispatch_map = {
    'greenhouse': scrape_greenhouse_json,
    'lever': scrape_lever_json,
    'ashby': scrape_ashby,
    'ashbyhq_hosted': scrape_ashbyhq_hosted,
    'workable': scrape_workable,
    'workday': scrape_workday,
    'generic': scrape_generic,
    'breezy': scrape_breezy,
    'smartrecruiters': scrape_smartrecruiters,
    'recruiterbox': scrape_recruiterbox,
    # 'jobvite': scrape_jobvite
}

old_results_path = Path('output_old.csv')
old_links = set()

if old_results_path.exists():
    old_df = pd.read_csv(old_results_path)
    old_links = set(old_df['link'].dropna().unique())

# print(old_links)
MAX_WORKERS = 10

with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
    futures = [executor.submit(scrape_company, row) for _, row in companies_df.iterrows()]
    for future in as_completed(futures):
        pass


# --- Save results ---
output_df = pd.DataFrame(results)
output_df.to_csv('output.csv', index=False)
print(f"\n✅ Scraped {len(output_df)} new jobs. Output saved to 'output.csv'.")

# --- Append to old archive ---
if not output_df.empty:
    if old_results_path.exists():
        expected_cols = ['company', 'title', 'location', 'link', 'postedOn', 'updatedOn']
        output_df = output_df.reindex(columns=expected_cols)
        output_df.to_csv(old_results_path, mode='a', index=False, header=False)
    else:
        output_df.to_csv(old_results_path, index=False)

    print(f"📦 Appended {len(output_df)} jobs to 'output_old.csv'")

# --- Print new jobs for Telegram notification ---
if not output_df.empty:
    print("NEW_JOBS_START")
    print(output_df.to_json(orient='records'))
    print("NEW_JOBS_END")

# --- Print errors for Telegram notification ---
if error_messages:
    print("ERRORS_START")
    for err in error_messages:
        print(err)
    print("ERRORS_END")
