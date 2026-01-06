import os
import json
import re
import time
import requests
import boto3
from datetime import datetime, timezone
from dotenv import load_dotenv

load_dotenv()

API_KEY = os.getenv("API_KEY")
API_ID = os.getenv("API_ID")

BUCKET = "reed-jobs-data"

COUNTRY = "gb"
CITIES = ["manchester", "london", "birmingham"]
KEYWORDS = ["data analyst", "business analyst", "financial analyst", "health data analyst", "bi analyst"]

RESULTS_PER_PAGE = 50
MAX_PAGES = 10  
SLEEP_SECONDS = 3 

def slugify(text: str) -> str:
    text = (text or "").strip().lower()
    text = re.sub(r"\s+", "_", text)
    text = re.sub(r"[^a-z0-9_]+", "", text)
    text = re.sub(r"_+", "_", text).strip("_")
    return text or "unknown"


def extract_job(country: str, job_title: str, location: str, page: int) -> dict:
    url = f"https://api.adzuna.com/v1/api/jobs/{country}/search/{page}"
    params = {
        "app_id": API_ID,
        "app_key": API_KEY,
        "results_per_page": RESULTS_PER_PAGE,
        "what": job_title,
        "where": location,
        "sort_by": "date",
    }

    r = requests.get(url, params=params, timeout=30)
    r.raise_for_status()
    return r.json()


def wrap_with_metadata(payload: dict, *, country: str, job_title: str, location: str, page: int, run_date: str) -> dict:
    return {
        "meta": {
            "run_date": run_date,
            "country": country,
            "city": location,
            "keyword": job_title,
            "page": page,
            "results_per_page": RESULTS_PER_PAGE,
        },
        "data": payload,
    }


def build_s3_key(*, run_date: str, location: str, job_title: str, page: int) -> str:
    city_slug = slugify(location)
    keyword_slug = slugify(job_title)
    page_str = str(page).zfill(3)

    return (
        f"raw/adzuna/jobs/"
        f"run_date={run_date}/"
        f"city={city_slug}/"
        f"keyword={keyword_slug}/"
        f"page={page_str}.json"
    )


def save_json(obj: dict, file_path: str) -> str:
    with open(file_path, "w", encoding="utf-8") as f:
        json.dump(obj, f, ensure_ascii=False, indent=2)
    return file_path


def upload_file_to_s3(file_path: str, bucket: str, key: str) -> None:
    s3 = boto3.client("s3")
    s3.upload_file(file_path, bucket, key)


def main():
    if not API_ID or not API_KEY:
        raise ValueError("missing API_ID or API_KEY. please Check your .env file.")

    run_date = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    print(f"Run date (UTC): {run_date}")
    print(f"Bucket: {BUCKET}")
    print(f"Cities: {CITIES}")
    print(f"Keywords: {KEYWORDS}")
    print(f"Plan: {RESULTS_PER_PAGE} results/page × {MAX_PAGES} pages = cap {RESULTS_PER_PAGE * MAX_PAGES} per combo\n")

    total_pages_uploaded = 0
    total_combos = 0

    for city in CITIES:
        for keyword in KEYWORDS:
            total_combos += 1
            print(f"=== {city.upper()} | {keyword.upper()} ===")

            for page in range(1, MAX_PAGES + 1):
                try:
                    payload = extract_job(COUNTRY, keyword, city, page)
                except requests.HTTPError as e:
                    print(f"[ERROR] HTTP error for city={city}, keyword={keyword}, page={page}: {e}")
                    raise
                except requests.RequestException as e:
                    print(f"[ERROR] Request error for city={city}, keyword={keyword}, page={page}: {e}")
                    raise

                results = payload.get("results", [])
                count = payload.get("count")
                print(f"page {str(page).zfill(2)}: returned {len(results)} (total found: {count})")

                if not results:
                    print("no results returned on this page. Stopping early for this (city, keyword).\n")
                    break

                wrapped = wrap_with_metadata(
                    payload,
                    country=COUNTRY,
                    job_title=keyword,
                    location=city,
                    page=page,
                    run_date=run_date,
                )

                s3_key = build_s3_key(run_date=run_date, location=city, job_title=keyword, page=page)

                #local temp file per page
                local_file = f"tmp_{slugify(city)}_{slugify(keyword)}_p{str(page).zfill(3)}.json"
                save_json(wrapped, local_file)
                upload_file_to_s3(local_file, BUCKET, s3_key)

                total_pages_uploaded += 1
                print(f"Uploaded: s3://{BUCKET}/{s3_key}")

                try:
                    os.remove(local_file)
                except OSError:
                    pass

                #rate limits
                time.sleep(SLEEP_SECONDS)

            print("")

    print(f"done. Combos processed: {total_combos}, pages uploaded: {total_pages_uploaded}")


if __name__ == "__main__":
    main()