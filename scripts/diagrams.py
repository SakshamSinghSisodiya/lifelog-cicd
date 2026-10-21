"""Small inline-SVG diagrams for the PDFs. Fixed light colours so they print well."""
INK, LINE = "#1f2933", "#52606d"
FILLS = {"a": "#dff3ea", "b": "#fde8d8", "c": "#dcebf7", "d": "#f8efc2", "e": "#e9e3f3", "n": "#f3f1ea"}


def _text(x, y, s, size=13, weight=400, anchor="middle", fill=INK):
    return f'<text x="{x}" y="{y}" font-size="{size}" font-weight="{weight}" text-anchor="{anchor}" fill="{fill}" font-family="Helvetica, Arial, sans-serif">{s}</text>'


def box(x, y, w, h, title, sub=(), fill="n", dashed=False):
    d = ' stroke-dasharray="6 4"' if dashed else ""
    out = [f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="8" fill="{FILLS[fill]}" stroke="{LINE}" stroke-width="1.5"{d}/>']
    lines = [title] + list(sub)
    top = y + h / 2 - (len(lines) - 1) * 9 + 4
    for i, line in enumerate(lines):
        out.append(_text(x + w / 2, top + i * 18, line, 13 if i == 0 else 11.5, 700 if i == 0 else 400))
    return "".join(out)


def arrow(x1, y1, x2, y2, label="", dy=-6):
    out = [f'<line x1="{x1}" y1="{y1}" x2="{x2}" y2="{y2}" stroke="{LINE}" stroke-width="1.8" marker-end="url(#ah)"/>']
    if label:
        out.append(_text((x1 + x2) / 2, (y1 + y2) / 2 + dy, label, 11, 400, fill=LINE))
    return "".join(out)


def svg(w, h, body, title):
    defs = f'<defs><marker id="ah" markerWidth="9" markerHeight="9" refX="8" refY="4.5" orient="auto"><path d="M0,0 L9,4.5 L0,9 z" fill="{LINE}"/></marker></defs>'
    return f'<svg viewBox="0 0 {w} {h}" width="100%" role="img" aria-label="{title}" xmlns="http://www.w3.org/2000/svg">{defs}{body}</svg>'


def flow():
    names = [("Developer", ["Mac", "git push"], "a"), ("GitHub", ["main", "v2-goals"], "c"), ("Jenkins", ["on EC2", ":8080"], "b"),
             ("Docker Hub", ["backend", "frontend"], "d"), ("Minikube", ["on EC2", "k8s cluster"], "e"), ("Browser", ["you", ":30080"], "a")]
    body, x, w, gap = [], 5, 125, 33
    for i, (t, sub, f) in enumerate(names):
        body.append(box(x + i * (w + gap), 20, w, 74, t, sub, f))
        if i:
            body.append(arrow(x + i * (w + gap) - gap + 2, 57, x + i * (w + gap) - 2, 57))
    labels = ["push", "poll / webhook", "push images", "kubectl apply", "HTTP"]
    for i, lab in enumerate(labels):
        body.append(_text(x + (i + 1) * (w + gap) - gap / 2 - 1, 112, lab, 10.5, 400, fill=LINE))
    stages = ["Checkout", "Build & Test", "Docker Build", "Push Image", "Deploy", "Verify"]
    sx, sw = 5, 140
    body.append(_text(460, 150, "Inside the Jenkins pipeline", 12, 700, fill=LINE))
    for i, s in enumerate(stages):
        body.append(box(sx + i * (sw + 15), 162, sw, 44, s, (), "b"))
        if i:
            body.append(arrow(sx + i * (sw + 15) - 13, 184, sx + i * (sw + 15) - 1, 184))
    body.append(_text(460, 240, "A failure in any stage stops the pipeline; the Verify stage curls /health and fails the build unless it returns 200.", 11.5, 400, fill=LINE))
    return svg(920, 256, "".join(body), "Developer to browser flow")


def topology():
    b = [box(5, 120, 110, 70, "Browser", ["http://EC2-IP", ":30080"], "a")]
    b.append('<rect x="165" y="8" width="750" height="364" rx="12" fill="none" stroke="#9aa5b1" stroke-width="1.5" stroke-dasharray="7 5"/>')
    b.append(_text(540, 30, "EC2 instance  /  Minikube (docker driver)  /  Kubernetes", 12, 700, fill=LINE))
    b.append(box(185, 120, 130, 70, "Service lifelog", ["NodePort 30080", "port 80"], "d"))
    b.append(box(365, 60, 150, 70, "frontend pod 1", ["nginx :8080", "static + proxy"], "c"))
    b.append(box(365, 180, 150, 70, "frontend pod 2", ["nginx :8080", "static + proxy"], "c"))
    b.append(box(565, 120, 130, 70, "Service backend", ["ClusterIP :5000"], "d"))
    b.append(box(745, 120, 150, 70, "backend pod", ["gunicorn + Flask", "SQLite file"], "b"))
    b += [arrow(115, 155, 185, 155, "port-forward", -8), arrow(315, 140, 365, 100), arrow(315, 170, 365, 215),
          arrow(515, 100, 565, 140), arrow(515, 215, 565, 170), arrow(695, 155, 745, 155)]
    b.append(_text(540, 300, "Probes: frontend /nginx-health on 8080, backend /health on 5000. Backend is 1 replica because SQLite is a file inside the pod.", 11.5, 400, fill=LINE))
    b.append(_text(540, 322, "Docker Hub images are pulled by the cluster: lifelog-frontend:BUILD and lifelog-backend:BUILD.", 11.5, 400, fill=LINE))
    b.append(box(185, 335, 400, 30, "Minikube IP 192.168.49.2 is only reachable from the EC2 host", (), "n", True))
    return svg(920, 380, "".join(b), "Runtime topology")


def capture():
    b = [box(5, 20, 140, 64, "Capture bar", ["you type: wat 3"], "a"), box(200, 20, 150, 64, "/api/capture/preview", ["debounced 120 ms"], "c"),
         box(405, 20, 150, 64, "capture.py", ["pure parser", "text to Intent"], "b"), box(610, 20, 150, 64, "service.describe", ["reads today's value", "builds the sentence"], "d"),
         box(810, 20, 105, 64, "Preview", ["Water +3 ->", "6/8 today"], "a")]
    b += [arrow(145, 52, 200, 52), arrow(350, 52, 405, 52), arrow(555, 52, 610, 52), arrow(760, 52, 810, 52)]
    b += [box(5, 140, 140, 64, "Press Enter", [], "a"), box(200, 140, 150, 64, "/api/capture", ["same parser"], "c"),
          box(405, 140, 150, 64, "apply_intent", ["write entry", "log the action"], "b"), box(610, 140, 150, 64, "SQLite", ["entries + actions", "tables"], "d"),
          box(810, 140, 105, 64, "Page refresh", ["swap page body"], "a")]
    b += [arrow(145, 172, 200, 172), arrow(350, 172, 405, 172), arrow(555, 172, 610, 172), arrow(760, 172, 810, 172)]
    b.append(_text(460, 245, "'undo' reads the newest un-undone row in the actions table and reverses it (restores the old value, deletes the money entry, or removes the tracker).", 11.5, 400, fill=LINE))
    return svg(920, 262, "".join(b), "Capture bar flow")


DIAGRAMS = {"flow": flow, "topology": topology, "capture": capture}
