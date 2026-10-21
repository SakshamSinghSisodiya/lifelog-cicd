/* Capture bar and progressive enhancement. Vanilla JS, no dependencies. */
(function () {
  var form = document.getElementById("capture");
  var input = document.getElementById("cap-input");
  var previewBox = document.getElementById("cap-preview");
  var suggestBox = document.getElementById("cap-suggest");
  var hint = document.getElementById("cap-hint");
  var toast = document.getElementById("toast");
  var timer = null, seq = 0, toastTimer = null;

  function store(key, value) {
    try { if (value === undefined) { return localStorage.getItem(key); } localStorage.setItem(key, value); } catch (e) { return null; }
  }

  function post(url, body) {
    return fetch(url, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(body) })
      .then(function (r) { return r.json(); });
  }

  function chip(label, cls, attrs) {
    var b = document.createElement("button");
    b.type = "button"; b.className = "chip " + (cls || ""); b.textContent = label;
    Object.keys(attrs).forEach(function (k) { b.dataset[k] = attrs[k]; });
    return b;
  }

  function render(data) {
    var ok = ["set", "add", "money", "undo"].indexOf(data.status) !== -1;
    var text = data.preview || data.message || "";
    previewBox.textContent = text;
    previewBox.className = "cap-preview " + (ok && data.preview ? "ok" : text ? "bad" : "");
    suggestBox.textContent = "";
    (data.suggestions || []).forEach(function (s) { suggestBox.appendChild(chip(s.label, "", { fill: s.text })); });
    if (data.create) {
      suggestBox.appendChild(chip(data.create.label, "primary", { create: JSON.stringify(data.create) }));
    }
    hint.hidden = !!input.value.trim();
  }

  function preview() {
    var text = input.value.trim(), mine = ++seq;
    if (!text) { render({ status: "empty" }); return; }
    post("/api/capture/preview", { text: text }).then(function (d) { if (mine === seq) { render(d); } }).catch(function () {});
  }

  function showToast(message) {
    toast.textContent = message; toast.classList.add("show");
    clearTimeout(toastTimer); toastTimer = setTimeout(function () { toast.classList.remove("show"); }, 3200);
  }

  function refreshMain() {
    return fetch(location.href, { credentials: "same-origin" }).then(function (r) { return r.text(); }).then(function (html) {
      var doc = new DOMParser().parseFromString(html, "text/html");
      var fresh = doc.querySelector("main");
      if (fresh) { document.querySelector("main").replaceWith(fresh); }
    });
  }

  function submit(create) {
    var text = input.value.trim();
    if (!text) { return; }
    var body = { text: text };
    if (create) { body.create = create; }
    post("/api/capture", body).then(function (d) {
      if (d.ok) {
        store("lifelog:last", text);
        input.value = ""; render({ status: "empty" }); showToast(d.message); refreshMain();
      } else {
        render(d);
      }
    }).catch(function () { showToast("Could not reach the server."); });
  }

  if (form) {
    form.addEventListener("submit", function (e) { e.preventDefault(); submit(null); });
    input.addEventListener("input", function () { clearTimeout(timer); timer = setTimeout(preview, 120); });
    input.addEventListener("keydown", function (e) {
      if (e.key === "Escape") { input.value = ""; render({ status: "empty" }); input.blur(); }
      if (e.key === "ArrowUp" && !input.value) { var last = store("lifelog:last"); if (last) { input.value = last; preview(); e.preventDefault(); } }
    });
    form.addEventListener("click", function (e) {
      var target = e.target.closest("button[data-fill], button[data-create]");
      if (!target) { return; }
      if (target.dataset.create) { submit(JSON.parse(target.dataset.create)); return; }
      input.value = target.dataset.fill; input.focus(); preview();
    });
  }

  document.addEventListener("keydown", function (e) {
    var tag = (e.target.tagName || "").toLowerCase();
    var typing = tag === "input" || tag === "textarea" || tag === "select" || e.target.isContentEditable;
    if (e.key === "/" && !typing && !e.metaKey && !e.ctrlKey && !e.altKey) { e.preventDefault(); input.focus(); input.select(); }
  });

  // Inline controls: submit in the background, then swap in the fresh page body
  document.addEventListener("submit", function (e) {
    var f = e.target;
    if (!f.matches || !f.matches("form[data-ajax]")) { return; }
    e.preventDefault();
    var data = e.submitter ? new FormData(f, e.submitter) : new FormData(f);
    fetch(f.action, { method: "POST", body: data, credentials: "same-origin" }).then(refreshMain)
      .catch(function () { f.submit(); });
  });
})();
