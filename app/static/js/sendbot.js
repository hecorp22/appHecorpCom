// Usamos siempre el mismo origen donde se cargó la página
const API_BASE = window.location.origin.replace(/\/+$/, "");

document.getElementById("telegramForm").addEventListener("submit", async function (e) {
  e.preventDefault();

  const target = e.submitter?.getAttribute("data-target") || "bot";
  const form = e.target;
  const formData = new FormData(form);
  const responseDiv = document.getElementById("response");

  responseDiv.innerHTML = "Enviando...";

  try {
    const controller = new AbortController();
    const timeoutId = setTimeout(() => controller.abort(), 10000);

    let res;
    let url;

    // 👉 payload único (sirve para TODO)
    const payload = {
      title: formData.get("title") || "",
      comment: formData.get("comment") || "",
      link: formData.get("link") || ""
    };

    // =========================
    // 👉 TELEGRAM
    // =========================
    if (target === "bot" || target === "group") {
      url = `${API_BASE}/api/telegram/send/${target}`;
    }

    // =========================
    // 👉 FACEBOOK 🔥
    // =========================
    else if (target === "facebook") {
      url = `${API_BASE}/api/facebook/post`;
    }

    console.log("POST:", url, payload);

    res = await fetch(url, {
      method: "POST",
      headers: {
        "Content-Type": "application/json"
      },
      credentials: "include", // 🔥 necesario para cookie auth
      body: JSON.stringify(payload),
      signal: controller.signal
    });

    clearTimeout(timeoutId);

    if (!res.ok) {
      const errText = await res.text().catch(() => "");
      console.error("HTTP error:", res.status, errText);
      throw new Error(`Error HTTP: ${res.status}`);
    }

    const data = await res.json().catch(() => ({}));
    console.log("Respuesta:", data);

    responseDiv.innerHTML = `<pre>${JSON.stringify(data, null, 2)}</pre>`;

  } catch (err) {
    console.error("Error:", err);

    if (err.name === "AbortError") {
      responseDiv.innerHTML = `<span class="text-warning">Timeout</span>`;
    } else {
      responseDiv.innerHTML = `<span class="text-danger">${err.message}</span>`;
    }
  }
});