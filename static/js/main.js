// main.js — Landing Page JavaScript
document.addEventListener("DOMContentLoaded", function () {
  document.querySelectorAll('a[href^="#"]').forEach(function (anchor) {
    anchor.addEventListener("click", function (e) {
      e.preventDefault();
      var target = document.querySelector(this.getAttribute("href"));
      if (target) { target.scrollIntoView({ behavior: "smooth", block: "start" }); }
    });
  });

  var observer = new IntersectionObserver(function (entries) {
    entries.forEach(function (entry) {
      if (entry.isIntersecting) { entry.target.style.opacity = "1"; entry.target.style.transform = "translateY(0)"; }
    });
  }, { threshold: 0.1 });

  document.querySelectorAll(".feature-card, .step").forEach(function (el) {
    el.style.opacity = "0"; el.style.transform = "translateY(20px)"; el.style.transition = "opacity 0.5s ease, transform 0.5s ease";
    observer.observe(el);
  });

  window.addEventListener("scroll", function () {
    var navbar = document.querySelector(".navbar");
    if (navbar) { navbar.style.background = window.scrollY > 50 ? "rgba(6,14,31,0.98)" : "rgba(6,14,31,0.85)"; }
  });
});
