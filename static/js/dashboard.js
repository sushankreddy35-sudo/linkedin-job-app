// dashboard.js — Full Dashboard Logic for LinkedApply

var jobResults = [];
var selectedEmails = [];
var resumeUploaded = false;

function showToast(message, type) {
  var toast = document.getElementById("toast");
  var toastMsg = document.getElementById("toast-msg");
  var toastIcon = document.getElementById("toast-icon");
  toastMsg.textContent = message;
  toast.className = "toast";
  if (type === "success") { toast.classList.add("success"); toastIcon.className = "fas fa-check-circle"; }
  else if (type === "error") { toast.classList.add("error"); toastIcon.className = "fas fa-times-circle"; }
  else if (type === "warning") { toast.classList.add("warning"); toastIcon.className = "fas fa-exclamation-triangle"; }
  else { toastIcon.className = "fas fa-info-circle"; }
  toast.classList.add("show");
  setTimeout(function () { toast.classList.remove("show"); }, 3500);
}

function showLoading(text) {
  document.getElementById("loading-text").textContent = text || "Loading...";
  document.getElementById("loading-overlay").style.display = "flex";
}

function hideLoading() { document.getElementById("loading-overlay").style.display = "none"; }

function togglePassword() {
  var pwField = document.getElementById("sender-password");
  var pwIcon = document.getElementById("pw-icon");
  if (pwField.type === "password") { pwField.type = "text"; pwIcon.className = "fas fa-eye-slash"; }
  else { pwField.type = "password"; pwIcon.className = "fas fa-eye"; }
}

function toggleExtractor() {
  var body = document.getElementById("extractor-body");
  var chevron = document.getElementById("extractor-chevron");
  if (body.style.display === "none") { body.style.display = "flex"; chevron.style.transform = "rotate(180deg)"; }
  else { body.style.display = "none"; chevron.style.transform = "rotate(0deg)"; }
}

function copyToClipboard(text) {
  navigator.clipboard.writeText(text).then(function () { showToast("Email copied!", "success"); });
}

function updateSelectedCount() {
  document.getElementById("selected-count").textContent = selectedEmails.length + " selected";
  var sendPanel = document.getElementById("panel-send");
  if (selectedEmails.length > 0) { sendPanel.style.display = "block"; updateSendSummary(); }
  else { sendPanel.style.display = "none"; }
}

function updateSendSummary() {
  var summary = document.getElementById("send-summary");
  var name = document.getElementById("applicant-name").value || "Your Name";
  var email = document.getElementById("sender-email").value || "your@gmail.com";
  summary.innerHTML =
    "

Sending as: " + name + " (" + email + ")

" +
    "

Applications to send: " + selectedEmails.length + " emails

" +
    "

Resume: " + (resumeUploaded ? document.getElementById("upload-filename").textContent : "Not uploaded yet") + "

";
}

function removeResume() {
  resumeUploaded = false;
  document.getElementById("upload-status").style.display = "none";
  document.getElementById("upload-zone").style.display = "block";
  document.getElementById("resume-file").value = "";
  showToast("Resume removed.", "warning");
}

document.addEventListener("DOMContentLoaded", function () {
  var uploadZone = document.getElementById("upload-zone");
  uploadZone.addEventListener("dragover", function (e) { e.preventDefault(); uploadZone.classList.add("drag-over"); });
  uploadZone.addEventListener("dragleave", function () { uploadZone.classList.remove("drag-over"); });
  uploadZone.addEventListener("drop", function (e) {
    e.preventDefault(); uploadZone.classList.remove("drag-over");
    var files = e.dataTransfer.files;
    if (files.length > 0) { document.getElementById("resume-file").files = files; uploadResume(); }
  });
  uploadZone.addEventListener("click", function () { document.getElementById("resume-file").click(); });
  document.getElementById("resume-file").addEventListener("change", function () { if (this.files.length > 0) { uploadResume(); } });
  setTimeout(function () { showToast("Welcome! Fill Steps 1-5 to start applying.", ""); }, 800);
});

function uploadResume() {
  var fileInput = document.getElementById("resume-file");
  var file = fileInput.files[0];
  if (!file) { showToast("Please select a file first.", "warning"); return; }
  if (file.size > 5 * 1024 * 1024) { showToast("File too large. Max 5MB.", "error"); return; }

  var formData = new FormData();
  formData.append("resume", file);

  var btn = document.getElementById("btn-upload");
  btn.disabled = true;
  btn.innerHTML = ' Uploading...';

  fetch("/api/upload-resume", { method: "POST", body: formData })
    .then(function (r) { return r.json(); })
    .then(function (data) {
      btn.disabled = false;
      btn.innerHTML = ' Upload Resume';
      if (data.success) {
        resumeUploaded = true;
        document.getElementById("upload-zone").style.display = "none";
        document.getElementById("upload-status").style.display = "flex";
        document.getElementById("upload-filename").textContent = data.filename;
        showToast(data.message, "success");
      } else { showToast(data.message, "error"); }
    })
    .catch(function () {
      btn.disabled = false;
      btn.innerHTML = ' Upload Resume';
      showToast("Upload failed. Is the server running?", "error");
    });
}

function searchJobs() {
  var keyword = document.getElementById("job-keyword").value.trim();
  var jobType = document.getElementById("job-type").value;
  if (!keyword) { showToast("Please enter a job keyword.", "warning"); return; }

  showLoading("Searching job listings and extracting recruiter emails...");
  var btn = document.getElementById("btn-search");
  btn.disabled = true;

  fetch("/api/search-jobs", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ keyword: keyword, job_type: jobType })
  })
    .then(function (r) { return r.json(); })
    .then(function (data) {
      hideLoading(); btn.disabled = false;
      if (data.success) { jobResults = data.jobs; selectedEmails = []; renderJobResults(data); showToast(data.message, "success"); }
      else { showToast(data.message, "error"); }
    })
    .catch(function () { hideLoading(); btn.disabled = false; showToast("Search failed. Check server.", "error"); });
}

function renderJobResults(data) {
  var container = document.getElementById("jobs-container");
  container.innerHTML = "";
  document.getElementById("badge-jobs").textContent = data.total_jobs + " Jobs";
  document.getElementById("badge-emails").textContent = data.total_emails + " Emails";
  document.getElementById("panel-results").style.display = "block";
  document.getElementById("panel-send").style.display = "none";

  if (!data.jobs || data.jobs.length === 0) {
    container.innerHTML = '

No jobs found. Try a different keyword.

';
    return;
  }

  data.jobs.forEach(function (job, index) {
    var card = document.createElement("div");
    card.className = "job-card";
    var initial = (job.company || "?").charAt(0).toUpperCase();
    var tagsHtml = "";
    if (job.tags && job.tags.length > 0) { job.tags.forEach(function (tag) { tagsHtml += '' + escapeHtml(tag) + ''; }); }
    var emailsHtml = "";
    if (job.emails && job.emails.length > 0) {
      job.emails.forEach(function (email) {
        var checkId = "email-" + index + "-" + email.replace(/[@.]/g, "-");
        emailsHtml += '
' +
          '' +
          '' + escapeHtml(email) + '' +
          '' +
          '
';
      });
    } else { emailsHtml = '

 No emails found in this listing.

'; }

    card.innerHTML =
      '
' +
      '
' + initial + '
' +
      '
' + escapeHtml(job.title) + '
' + escapeHtml(job.company) + '
' +
      '' + escapeHtml(job.source) + ' ' +
      '
' +
      '
' + escapeHtml(job.description) + '
' + tagsHtml + '
' +
      '
 Recruiter Emails (' + (job.emails ? job.emails.length : 0) + ')
' + emailsHtml + '
';
    container.appendChild(card);
  });
  document.getElementById("panel-results").scrollIntoView({ behavior: "smooth", block: "start" });
}

function getColor(index) {
  var colors = ["#0a66c2","#e74c3c","#2ecc71","#9b59b6","#f39c12","#1abc9c","#e67e22","#3498db"];
  return colors[index % colors.length];
}

function escapeHtml(text) {
  if (!text) return "";
  return String(text).replace(/&/g,"&").replace(//g,">").replace(/"/g,""").replace(/'/g,"'");
}

function toggleEmail(checkbox, email, jobTitle, company) {
  var itemEl = checkbox.closest(".email-item");
  if (checkbox.checked) { selectedEmails.push({ email: email, job_title: jobTitle, company: company }); itemEl.classList.add("selected"); }
  else { selectedEmails = selectedEmails.filter(function (item) { return item.email !== email; }); itemEl.classList.remove("selected"); }
  syncSelectAll(); updateSelectedCount();
}

function toggleSelectAll() {
  var isChecked = document.getElementById("select-all").checked;
  selectedEmails = [];
  document.querySelectorAll('.email-item input[type="checkbox"]').forEach(function (cb) {
    cb.checked = isChecked;
    var item = cb.closest(".email-item");
    if (isChecked) {
      item.classList.add("selected");
      var emailAddr = item.querySelector(".email-addr").textContent.trim();
      var card = item.closest(".job-card");
      var jobTitle = card ? card.querySelector(".job-title").textContent.trim() : "";
      var company = card ? card.querySelector(".job-company").textContent.trim() : "";
      selectedEmails.push({ email: emailAddr, job_title: jobTitle, company: company });
    } else { item.classList.remove("selected"); }
  });
  updateSelectedCount();
}

function clearSelection() {
  selectedEmails = [];
  document.querySelectorAll('.email-item input[type="checkbox"]').forEach(function (cb) { cb.checked = false; cb.closest(".email-item").classList.remove("selected"); });
  document.getElementById("select-all").checked = false;
  updateSelectedCount();
}

function syncSelectAll() {
  var all = document.querySelectorAll('.email-item input[type="checkbox"]');
  var checked = document.querySelectorAll('.email-item input[type="checkbox"]:checked');
  document.getElementById("select-all").checked = all.length > 0 && all.length === checked.length;
}

function extractEmails() {
  var text = document.getElementById("paste-text").value.trim();
  var resultDiv = document.getElementById("extracted-result");
  if (!text) { showToast("Please paste some text first.", "warning"); return; }
  fetch("/api/extract-emails", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ text: text }) })
    .then(function (r) { return r.json(); })
    .then(function (data) {
      if (data.count === 0) {
        resultDiv.innerHTML = '

 No emails found.

';
      } else {
        var html = '
 Found ' + data.count + ' email(s):
';
        data.emails.forEach(function (email) { html += '
' + escapeHtml(email) + '
'; });
        html += '
';
        resultDiv.innerHTML = html;
        showToast("Found " + data.count + " email(s)!", "success");
      }
    });
}

function sendApplications() {
  var name = document.getElementById("applicant-name").value.trim();
  var email = document.getElementById("sender-email").value.trim();
  var password = document.getElementById("sender-password").value.trim();
  if (!name) { showToast("Enter your name in Step 1.", "warning"); return; }
  if (!email) { showToast("Enter Gmail address in Step 1.", "warning"); return; }
  if (!password) { showToast("Enter App Password in Step 1.", "warning"); return; }
  if (!resumeUploaded) { showToast("Upload your resume in Step 2.", "warning"); return; }
  if (selectedEmails.length === 0) { showToast("Select at least one email.", "warning"); return; }

  var confirm = window.confirm("Send " + selectedEmails.length + " application email(s)?\nFrom: " + email + "\nName: " + name + "\n\nContinue?");
  if (!confirm) return;

  showLoading("Sending " + selectedEmails.length + " application email(s)...");
  var btn = document.getElementById("btn-send");
  btn.disabled = true;

  fetch("/api/send-emails", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ name: name, email: email, password: password, selected_emails: selectedEmails })
  })
    .then(function (r) { return r.json(); })
    .then(function (data) {
      hideLoading(); btn.disabled = false;
      renderSendResults(data);
      showToast(data.message, data.fail_count === 0 ? "success" : "warning");
    })
    .catch(function () { hideLoading(); btn.disabled = false; showToast("Sending failed.", "error"); });
}

function renderSendResults(data) {
  var panel = document.getElementById("panel-log");
  var log = document.getElementById("results-log");
  panel.style.display = "block";
  var summaryHtml = '
  ' + data.success_count + ' sent  |  ' + data.fail_count + ' failed
';
  var itemsHtml = "";
  data.results.forEach(function (result) {
    var icon = result.success ? '' : '';
    itemsHtml += '
' + icon + '
' + escapeHtml(result.email) + ' — ' + escapeHtml(result.company) + '
' + escapeHtml(result.message) + '
';
  });
  log.innerHTML = summaryHtml + itemsHtml;
  panel.scrollIntoView({ behavior: "smooth", block: "start" });
}
