let lang = "ko";

function toggleLang() {
  lang = lang === "ko" ? "en" : "ko";

  const toggle = document.getElementById("lang-toggle");
  toggle.textContent = lang === "ko" ? "English" : "한국어";

  // Hero subtitle
  document.getElementById("hero-sub-ko").classList.toggle("hidden", lang !== "ko");
  document.getElementById("hero-sub-en").classList.toggle("hidden", lang !== "en");

  // Open source description
  document.getElementById("oss-desc-ko").classList.toggle("hidden", lang !== "ko");
  document.getElementById("oss-desc-en").classList.toggle("hidden", lang !== "en");

  // Cloud title and description
  document.getElementById("cloud-title-ko").classList.toggle("hidden", lang !== "ko");
  document.getElementById("cloud-title-en").classList.toggle("hidden", lang !== "en");
  document.getElementById("cloud-desc-ko").classList.toggle("hidden", lang !== "ko");
  document.getElementById("cloud-desc-en").classList.toggle("hidden", lang !== "en");
}
