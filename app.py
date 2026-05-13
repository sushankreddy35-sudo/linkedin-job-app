# ============================================================
# app.py - Main Flask Backend - FIXED with JSearch API
# ============================================================

from flask import Flask, render_template, request, jsonify, session
import smtplib
import os
import re
import time
import requests
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.base import MIMEBase
from email import encoders
from werkzeug.utils import secure_filename

# -------------------------
# App Configuration
# -------------------------
app = Flask(__name__)
app.secret_key = "linkedin_automation_secret_2024"

UPLOAD_FOLDER = "uploads"
ALLOWED_EXTENSIONS = {"pdf", "doc", "docx"}
app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

# ============================================
# PASTE YOUR RAPIDAPI KEY BELOW (from jsearch)
# Get it free at: https://rapidapi.com/letscrape-6bRBa3QguO5/api/jsearch
RAPIDAPI_KEY = "58b9863658mshe4eaf337b9873f1p1bcf6ejsn44cc1c67289c"
# ============================================


# -------------------------
# Helper Functions
# -------------------------

def allowed_file(filename):
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS


def extract_emails_from_text(text):
    """Extract real email addresses from text using regex."""
    if not text:
        return []
    pattern = r"[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}"
    emails = re.findall(pattern, text)
    # Remove image/file false matches
    bad_endings = ('.png','.jpg','.jpeg','.gif','.svg','.ico','.css','.js','.webp')
    return list(set(e for e in emails if not e.lower().endswith(bad_endings)))


def guess_company_email(company_name):
    """
    Generate a likely HR email from company name.
    Example: 'Infosys Limited' -> 'hr@infosyslimited.com'
    This is a best-guess — not always correct, but useful.
    """
    if not company_name:
        return None
    clean = re.sub(r"[^a-zA-Z0-9]", "", company_name.lower())
    if len(clean) < 2:
        return None
    return f"hr@{clean}.com"


def search_jsearch(keyword, job_type):
    """
    Search jobs using JSearch API on RapidAPI.
    - Free: 200 requests/month
    - No credit card required
    - Returns real jobs from Google for Jobs
    """
    if RAPIDAPI_KEY == "YOUR_RAPIDAPI_KEY_HERE":
        print("JSearch API key not set — skipping")
        return []

    results = []
    try:
        url = "https://jsearch.p.rapidapi.com/search"
        # Build query: keyword + job type + India for local results
        query = f"{keyword} {job_type} India"
        headers = {
            "X-RapidAPI-Key":  RAPIDAPI_KEY,
            "X-RapidAPI-Host": "jsearch.p.rapidapi.com"
        }
        params = {
            "query":        query,
            "page":         "1",
            "num_pages":    "1",
            "date_posted":  "month"   # Only recent jobs
        }
        response = requests.get(url, headers=headers, params=params, timeout=15)
        print(f"JSearch status: {response.status_code}")

        if response.status_code == 200:
            data = response.json()
            jobs = data.get("data", [])
            print(f"JSearch returned {len(jobs)} jobs")

            for job in jobs[:10]:
                company     = job.get("employer_name", "Unknown Company")
                title       = job.get("job_title", keyword)
                description = job.get("job_description", "")
                location    = job.get("job_city", "") or job.get("job_country", "")
                apply_link  = job.get("job_apply_link", "")
                is_remote   = job.get("job_is_remote", False)
                job_type_r  = job.get("job_employment_type", job_type)
                publisher   = job.get("job_publisher", "Google for Jobs")

                # Extract real emails from description
                emails_found = extract_emails_from_text(description)

                # Also check apply link for email
                if not emails_found and apply_link and "mailto:" in apply_link:
                    mail = apply_link.replace("mailto:", "").split("?")[0].strip()
                    if "@" in mail:
                        emails_found = [mail]

                # Guess email from company name if none found
                if not emails_found:
                    guessed = guess_company_email(company)
                    if guessed:
                        emails_found = [guessed]

                # Build tags
                tags = []
                if is_remote:
                    tags.append("Remote")
                if location:
                    tags.append(location)
                if job_type_r:
                    tags.append(job_type_r)

                results.append({
                    "title":       title,
                    "company":     company,
                    "location":    location or ("Remote" if is_remote else "India"),
                    "url":         apply_link,
                    "description": description[:400] + "..." if len(description) > 400 else description,
                    "emails":      emails_found,
                    "tags":        tags[:5],
                    "source":      f"via {publisher}"
                })
        else:
            print(f"JSearch error body: {response.text[:300]}")

    except Exception as e:
        print(f"JSearch exception: {e}")

    return results


def search_remotive(keyword):
    """
    Search remote jobs using Remotive API.
    100% FREE — no key needed — works from any server.
    """
    results = []
    try:
        url = f"https://remotive.com/api/remote-jobs?search={requests.utils.quote(keyword)}&limit=8"
        response = requests.get(url, timeout=15, headers={"User-Agent": "LinkedApply/1.0"})
        print(f"Remotive status: {response.status_code}")

        if response.status_code == 200:
            data = response.json()
            jobs = data.get("jobs", [])
            print(f"Remotive returned {len(jobs)} jobs")

            for job in jobs:
                company   = job.get("company_name", "Unknown")
                title     = job.get("title", keyword)
                desc_html = job.get("description", "")
                url_job   = job.get("url", "")
                tags      = job.get("tags", [])
                location  = job.get("candidate_required_location", "Remote")

                # Strip HTML tags
                desc_clean = re.sub(r"<[^>]+>", " ", desc_html)
                desc_clean = re.sub(r"\s+", " ", desc_clean).strip()

                emails_found = extract_emails_from_text(desc_clean)
                if not emails_found:
                    guessed = guess_company_email(company)
                    if guessed:
                        emails_found = [guessed]

                results.append({
                    "title":       title,
                    "company":     company,
                    "location":    location,
                    "url":         url_job,
                    "description": desc_clean[:400] + "..." if len(desc_clean) > 400 else desc_clean,
                    "emails":      emails_found,
                    "tags":        (tags[:3] if tags else []) + ["Remote"],
                    "source":      "Remotive"
                })
    except Exception as e:
        print(f"Remotive exception: {e}")

    return results


def generate_demo_jobs(keyword, job_type):
    """
    Realistic Indian company demo jobs.
    Used ONLY when all APIs fail (e.g. no internet on server).
    """
    companies = [
        ("Infosys",           "careers@infosys.com",        "Bangalore"),
        ("TCS",               "hr@tcs.com",                 "Mumbai"),
        ("Wipro",             "recruitment@wipro.com",      "Hyderabad"),
        ("HCL Technologies",  "talent@hcltech.com",         "Noida"),
        ("Tech Mahindra",     "hiring@techmahindra.com",    "Pune"),
        ("Capgemini India",   "hr.india@capgemini.com",     "Chennai"),
        ("Accenture India",   "careers@accenture.com",      "Bangalore"),
        ("Cognizant",         "recruitment@cognizant.com",  "Hyderabad"),
    ]
    roles = ["Developer", "Engineer", "Analyst", "Specialist"]
    jobs = []
    for i, (company, email, city) in enumerate(companies):
        role = roles[i % len(roles)]
        jobs.append({
            "title":       f"{keyword} {role}",
            "company":     company,
            "location":    city,
            "url":         f"https://linkedin.com/jobs/view/{9000000 + i}",
            "description": (
                f"We are hiring a skilled {keyword} {role} ({job_type}) to join {company} in {city}. "
                f"Competitive salary, excellent benefits, strong growth path. "
                f"Send your resume to {email}. "
                "Requirements: 1-3 years experience preferred. Good communication skills."
            ),
            "emails":      [email],
            "tags":        [keyword, job_type, city, "India"],
            "source":      "Demo Data (set API key for real jobs)"
        })
    return jobs


def search_jobs_on_web(keyword, job_type):
    """
    Main search function.
    Priority: JSearch (real) → Remotive (free) → Demo (fallback)
    """
    results = []

    # 1. JSearch — best results (requires free RapidAPI key)
    print(f"\n--- Searching for: {keyword} ({job_type}) ---")
    jsearch_results = search_jsearch(keyword, job_type)
    results.extend(jsearch_results)

    # 2. Remotive — free, no key needed
    if len(results) < 5:
        remotive_results = search_remotive(keyword)
        results.extend(remotive_results)

    # 3. Demo fallback
    if not results:
        print("All APIs failed — using demo data")
        results = generate_demo_jobs(keyword, job_type)

    # Remove duplicates
    seen = set()
    unique = []
    for job in results:
        key = (job["title"].lower().strip(), job["company"].lower().strip())
        if key not in seen:
            seen.add(key)
            unique.append(job)

    print(f"Total unique jobs found: {len(unique)}")
    return unique[:10]


# -------------------------
# Email Sending
# -------------------------

def send_application_email(sender_email, sender_password, recipient_email,
                            applicant_name, job_title, company_name, resume_path):
    """Send professional application email via Gmail SMTP."""
    try:
        msg = MIMEMultipart()
        msg["From"]    = f"{applicant_name} <{sender_email}>"
        msg["To"]      = recipient_email
        msg["Subject"] = f"Application for {job_title} – {applicant_name}"

        body = f"""Dear Hiring Team at {company_name},

I hope this message finds you well. I am writing to express my sincere interest in the {job_title} position at {company_name}.

I am confident that my skills and dedication make me a strong fit for this role. Please find my resume attached for your review. I would welcome the opportunity to discuss how I can contribute to your team.

Thank you for your time and consideration. I look forward to hearing from you.

Best regards,
{applicant_name}
{sender_email}
"""
        msg.attach(MIMEText(body, "plain"))

        if resume_path and os.path.exists(resume_path):
            with open(resume_path, "rb") as f:
                part = MIMEBase("application", "octet-stream")
                part.set_payload(f.read())
            encoders.encode_base64(part)
            part.add_header("Content-Disposition",
                            f"attachment; filename={os.path.basename(resume_path)}")
            msg.attach(part)

        server = smtplib.SMTP("smtp.gmail.com", 587)
        server.starttls()
        server.login(sender_email, sender_password)
        server.sendmail(sender_email, recipient_email, msg.as_string())
        server.quit()
        return {"success": True, "message": f"Sent to {recipient_email}"}

    except smtplib.SMTPAuthenticationError:
        return {"success": False,
                "message": "Gmail auth failed. Use App Password, not your Gmail password."}
    except smtplib.SMTPRecipientsRefused:
        return {"success": False,
                "message": f"{recipient_email} refused. May be an invalid address."}
    except Exception as e:
        return {"success": False, "message": f"Error: {str(e)}"}


# -------------------------
# Flask Routes
# -------------------------

@app.route("/")
def index():
    return render_template("index.html")


@app.route("/dashboard")
def dashboard():
    return render_template("dashboard.html")


@app.route("/api/search-jobs", methods=["POST"])
def search_jobs():
    data     = request.get_json()
    keyword  = data.get("keyword", "").strip()
    job_type = data.get("job_type", "full-time").strip()

    if not keyword:
        return jsonify({"success": False, "message": "Please enter a job keyword."})

    session["keyword"]  = keyword
    session["job_type"] = job_type

    try:
        jobs         = search_jobs_on_web(keyword, job_type)
        total_emails = sum(len(job["emails"]) for job in jobs)
        return jsonify({
            "success":      True,
            "jobs":         jobs,
            "total_jobs":   len(jobs),
            "total_emails": total_emails,
            "message":      f"Found {len(jobs)} jobs with {total_emails} contact emails."
        })
    except Exception as e:
        return jsonify({"success": False, "message": f"Search error: {str(e)}"})


@app.route("/api/upload-resume", methods=["POST"])
def upload_resume():
    if "resume" not in request.files:
        return jsonify({"success": False, "message": "No file provided."})
    file = request.files["resume"]
    if file.filename == "":
        return jsonify({"success": False, "message": "No file selected."})
    if not allowed_file(file.filename):
        return jsonify({"success": False, "message": "Only PDF, DOC, DOCX allowed."})

    filename = secure_filename(file.filename)
    filepath = os.path.join(app.config["UPLOAD_FOLDER"], filename)
    file.save(filepath)
    session["resume_path"] = filepath
    session["resume_name"] = filename
    return jsonify({"success": True,
                    "message": f"'{filename}' uploaded!",
                    "filename": filename})


@app.route("/api/send-emails", methods=["POST"])
def send_emails():
    data            = request.get_json()
    sender_email    = data.get("email", "").strip()
    sender_password = data.get("password", "").strip()
    applicant_name  = data.get("name", "").strip()
    selected_emails = data.get("selected_emails", [])

    if not sender_email or not sender_password:
        return jsonify({"success": False, "message": "Email and password required."})
    if not applicant_name:
        return jsonify({"success": False, "message": "Your name is required."})
    if not selected_emails:
        return jsonify({"success": False, "message": "Select at least one email."})

    resume_path = session.get("resume_path")
    if not resume_path or not os.path.exists(resume_path):
        return jsonify({"success": False, "message": "Please upload your resume first."})

    results, success_count, fail_count = [], 0, 0
    for item in selected_emails:
        result = send_application_email(
            sender_email    = sender_email,
            sender_password = sender_password,
            recipient_email = item.get("email"),
            applicant_name  = applicant_name,
            job_title       = item.get("job_title", "the position"),
            company_name    = item.get("company", "your company"),
            resume_path     = resume_path
        )
        results.append({"email": item.get("email"),
                         "company": item.get("company"), **result})
        success_count += 1 if result["success"] else 0
        fail_count    += 0 if result["success"] else 1
        time.sleep(1)

    return jsonify({"success": True, "results": results,
                    "success_count": success_count, "fail_count": fail_count,
                    "message": f"{success_count} sent, {fail_count} failed."})


@app.route("/api/extract-emails", methods=["POST"])
def extract_emails():
    text   = request.get_json().get("text", "")
    emails = extract_emails_from_text(text)
    return jsonify({"success": True, "emails": emails,
                    "count": len(emails),
                    "message": f"Found {len(emails)} email(s)."})


@app.route("/health")
def health():
    return jsonify({"status": "ok", "message": "LinkedApply running!"})


if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=5000)
