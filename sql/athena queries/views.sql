CREATE OR REPLACE VIEW v_clean_jobs AS
SELECT
    LOWER(TRIM(title))              AS title,
    TRIM(company_name)              AS company_name,
    LOWER(TRIM(city))               AS city,
    CAST(salary_min AS DOUBLE)      AS salary_min,
    CAST(salary_max AS DOUBLE)      AS salary_max,
    LOWER(TRIM(keyword))            AS keyword,
    DATE(posted_date)               AS posted_date
FROM raw_job_postings
WHERE city IS NOT NULL
  AND salary_min IS NOT NULL;


-- total jobs kpi
CREATE OR REPLACE VIEW v_total_jobs AS
SELECT
    COUNT(*) AS total_jobs
FROM v_clean_jobs;


-- average Minimum Salary KPI
CREATE OR REPLACE VIEW v_avg_min_salary AS
SELECT
    ROUND(AVG(salary_min), 0) AS avg_min_salary
FROM v_clean_jobs;


-- analyst Job Demand by Role chart
CREATE OR REPLACE VIEW v_jobs_by_role AS
SELECT
    keyword,
    COUNT(*) AS job_count
FROM v_clean_jobs
GROUP BY keyword
ORDER BY job_count DESC;


-- Job Demand by City
CREATE OR REPLACE VIEW v_jobs_by_city AS
SELECT
    city,
    COUNT(*) AS job_count
FROM v_clean_jobs
GROUP BY city
ORDER BY job_count DESC;


-- Top Hiring Companies
CREATE OR REPLACE VIEW v_top_hiring_companies AS
SELECT
    company_name,
    COUNT(*) AS job_count
FROM v_clean_jobs
GROUP BY company_name
ORDER BY job_count DESC
LIMIT 10;

-- Average Salary by Role
CREATE OR REPLACE VIEW v_salary_by_role AS
SELECT
    keyword,
    ROUND(AVG(salary_min), 0) AS avg_min_salary
FROM v_clean_jobs
GROUP BY keyword
ORDER BY avg_min_salary DESC;
