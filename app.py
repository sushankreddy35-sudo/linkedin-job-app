# ============================================================
# app.py - Main Flask Backend Application
# LinkedIn Job Application Automation Tool
# ============================================================

from flask import Flask, render_template, request, jsonify, session
import smtplib
import os
import re
import time
import json
import requests
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.base import MIMEBase
from email import encoders
from werkzeug.utils import secure_filename
from bs4 import BeautifulSoup

# -------------------------
# App Configuration
# -------------------------
app = Flask(__name__)
app.secret_key = "linkedin_automation_secret_2024"

UPLOAD_FOLDER = "uploads"
ALLOWED_EXTENSIONS = {"pdf", "doc", "docx"}
app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER
os.makedirs(UPLOAD_FOLDER, exist_ok=True)


# -------------------------
# Helper Functions
# -------------------------

def allowed_file(filename):
    """Check if the uploaded file has an allowed extension."""
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS


def extract_emails_from_text(text):
    """Use regex to find all email addresses in a block of text."""
    email_pattern = r"[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}"
    emails = re.findall(email_pattern, text)
    return list(set(emails))


def search_jobs_on_web(keyword, job_type):
    """Search for jobs using free public APIs. Falls back to demo data."""
    results = []

    try:
        headers = {
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/120.0.0.0 Safari/537.36"
            )
        }
        remoteok_url = f"https://remoteok.com/api?tag={requests.utils.quote(keyword)}"
        response = requests.get(remoteok_url, headers=headers, timeout=10)

        if response.status_code == 200:
            jobs_data = response.json()
            for job in jobs_data[1:11]:
                if isinstance(job, dict):
                    company = job.get("company", "Unknown Company")
                    position = job.get("position", keyword)
                    url = job.get("url", "")
                    description = job.get("description", "")
                    tags = job.get("tags", [])
                    emails_found = extract_emails_from_text(description)
                    results.append({
                        "title": position,
                        "company": company,
                        "url": url if url.startswith("http") else f"https://remoteok.com{url}",
                        "description": description[:300] + "..." if len(description) > 300 else description,
                        "emails": emails_found,
                        "tags": tags[:5] if tags else [],
                        "source": "RemoteOK"
                    })
    except Exception as e:
        print(f"RemoteOK API error: {e}")

    if len(results) < 3:
        try:
            headers = {"User-Agent": "Mozilla/5.0"}
            arbeitnow_url = f"https://www.arbeitnow.com/api/job-board-api?search={requests.utils.quote(keyword)}"
            response = requests.get(arbeitnow_url, headers=headers, timeout=10)
            if response.status_code == 200:
                data = response.json()
                for job in data.get("data", [])[:8]:
                    description = job.get("description", "")
                    emails_found = extract_emails_from_text(description)
                    results.append({
                        "title": job.get("title", keyword),
                        "company": job.get("company_name", "Unknown"),
                        "url": job.get("url", ""),
                        "description": description[:300] + "..." if len(description) > 300 else description,
                        "emails": emails_found,
                        "tags": job.get("tags", [])[:5],
                        "source": "Arbeitnow"
                    })
        except Exception as e:
            print(f"Arbeitnow API error: {e}")

    if not results:
        results = generate_demo_jobs(keyword, job_type)

    return results[:10]


def generate_demo_jobs(keyword, job_type):
    """Generate demo job data when APIs are unavailable."""
    companies = [
        ("TechCorp Solutions", "hr@techcorpsolutions.com"),
        ("InnovateTech Ltd", "careers@innovatetech.io"),
        ("Global Staffing Inc", "recruit@globalstaffing.com"),
        ("StartupHub", "jobs@startuphub.co"),
        ("DataDriven Co", "hiring@datadriven.com"),
        ("CloudSystems Pvt Ltd", "talent@cloudsystems.in"),
        ("NextGen Technologies", "hr.nextgen@gmail.com"),
        ("Future Works Ltd", "apply@futureworks.net"),
    ]
    demo_jobs = []
    for i, (company, email) in enumerate(companies):
        demo_jobs.append({
            "title": f"{keyword} {job_type}",
            "company": company,
            "url": f"https://linkedin.com/jobs/view/{1000000 + i}",
            "description": (
                f"We are looking for a talented {keyword} professional to join our team. "
                f"This is a {job_type} position offering competitive salary and benefits. "
                f"Contact us at {email} to apply. "
                "Requirements: 2+ years of experience, strong communication skills."
            ),
            "emails": [email],
            "tags": [keyword.lower(), job_type.lower(), "remote", "hiring"],
            "source": "Demo Data"
        })
    return demo_jobs


def send_application_email(sender_email, sender_password, recipient_email,
                            applicant_name, job_title, company_name, resume_path):
    """Send a professional application email with resume attached via Gmail SMTP."""
    try:
        msg = MIMEMultipart()
        msg["From"] = sender_email
        msg["To"] = recipient_email
        msg["Subject"] = f"Application for {job_title} Position - {applicant_name}"

        body = f"""Dear Hiring Manager at {company_name},

I hope this message finds you well. I am writing to express my strong interest in the {job_title} position at {company_name}.

I believe my skills and experience make me a strong candidate for this role. I have attached my resume for your review, and I would welcome the opportunity to discuss how I can contribute to your team.

I am enthusiastic about the work being done at {company_name} and am confident that my background aligns well with your requirements.

Thank you for taking the time to consider my application. I look forward to hearing from you.

Best regards,
{applicant_name}
{sender_email}
"""
        msg.attach(MIMEText(body, "plain"))

        if resume_path and os.path.exists(resume_path):
            with open(resume_path, "rb") as attachment:
                part = MIMEBase("application", "octet-stream")
                part.set_payload(attachment.read())
            encoders.encode_base64(part)
            filename = os.path.basename(resume_path)
            part.add_header("Content-Disposition", f"attachment; filename={filename}")
            msg.attach(part)

        server = smtplib.SMTP("smtp.gmail.com", 587)
        server.starttls()
        server.login(sender_email, sender_password)
        server.sendmail(sender_email, recipient_email, msg.as_string())
        server.quit()
        return {"success": True, "message": f"Email sent to {recipient_email}"}

    except smtplib.SMTPAuthenticationError:
        return {
            "success": False,
            "message": "Authentication failed. Use Gmail App Password, not your regular password."
        }
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
    data = request.get_json()
    keyword = data.get("keyword", "").strip()
    job_type = data.get("job_type", "").strip()

    if not keyword:
        return jsonify({"success": False, "message": "Please enter a job keyword."})

    session["keyword"] = keyword
    session["job_type"] = job_type

    jobs = search_jobs_on_web(keyword, job_type)
    total_emails = sum(len(job["emails"]) for job in jobs)

    return jsonify({
        "success": True,
        "jobs": jobs,
        "total_jobs": len(jobs),
        "total_emails": total_emails,
        "message": f"Found {len(jobs)} jobs with {total_emails} recruiter emails."
    })


@app.route("/api/upload-resume", methods=["POST"])
def upload_resume():
    if "resume" not in request.files:
        return jsonify({"success": False, "message": "No file provided."})

    file = request.files["resume"]
    if file.filename == "":
        return jsonify({"success": False, "message": "No file selected."})
    if not allowed_file(file.filename):
        return jsonify({"success": False, "message": "Only PDF, DOC, DOCX files allowed."})

    filename = secure_filename(file.filename)
    filepath = os.path.join(app.config["UPLOAD_FOLDER"], filename)
    file.save(filepath)
    session["resume_path"] = filepath
    session["resume_name"] = filename

    return jsonify({
        "success": True,
        "message": f"Resume '{filename}' uploaded successfully!",
        "filename": filename
    })


@app.route("/api/send-emails", methods=["POST"])
def send_emails():
    data = request.get_json()
    sender_email = data.get("email", "").strip()
    sender_password = data.get("password", "").strip()
    applicant_name = data.get("name", "").strip()
    selected_emails = data.get("selected_emails", [])

    if not sender_email or not sender_password:
        return jsonify({"success": False, "message": "Email and password are required."})
    if not applicant_name:
        return jsonify({"success": False, "message": "Your name is required."})
    if not selected_emails:
        return jsonify({"success": False, "message": "Select at least one recruiter email."})

    resume_path = session.get("resume_path", None)
    if not resume_path or not os.path.exists(resume_path):
        return jsonify({"success": False, "message": "Please upload your resume first."})

    results = []
    success_count = 0
    fail_count = 0

    for item in selected_emails:
        recipient_email = item.get("email")
        job_title = item.get("job_title", "the open position")
        company_name = item.get("company", "your company")

        result = send_application_email(
            sender_email=sender_email,
            sender_password=sender_password,
            recipient_email=recipient_email,
            applicant_name=applicant_name,
            job_title=job_title,
            company_name=company_name,
            resume_path=resume_path
        )
        results.append({"email": recipient_email, "company": company_name, **result})

        if result["success"]:
            success_count += 1
        else:
            fail_count += 1
        time.sleep(1)

    return jsonify({
        "success": True,
        "results": results,
        "success_count": success_count,
        "fail_count": fail_count,
        "message": f"Sent {success_count} emails. {fail_count} failed."
    })


@app.route("/api/extract-emails", methods=["POST"])
def extract_emails():
    data = request.get_json()
    text = data.get("text", "")
    emails = extract_emails_from_text(text)
    return jsonify({
        "success": True,
        "emails": emails,
        "count": len(emails),
        "message": f"Found {len(emails)} email(s)."
    })


@app.route("/health")
def health():
    """Health check endpoint for deployment platforms."""
    return jsonify({"status": "ok", "message": "LinkedApply is running!"})


if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=5000)
