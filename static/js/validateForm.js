function validateForm() {
  const input = document.getElementById("stat_page").value;
  const substring = "https://www.hltv.org/stats/";
  const error = document.getElementById("error");

  try {
    const url = new URL(input);
    if (!url.href.includes(substring)) {
      error.textContent = "Not a valid stat page URL";
      return false;
    }

    error.textContent = "";
    return true;

  } catch (_) {
    error.textContent = "Not a valid stat page URL";
    return false;
  }
}