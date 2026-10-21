"""Build all PDFs: report, recording script, study guide, screenshot checklist.

Usage: python scripts/make_docs.py   (needs the `markdown` package and Google Chrome)
Screenshots live in docs/screenshots/<name>.png; missing ones show as labelled slots."""
import base64
import os
import re
import subprocess
import sys
import tempfile

import markdown

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from diagrams import DIAGRAMS  # noqa: E402
from shots import SHOTS  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CHROME = "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"
EXTS = (".png", ".jpg", ".jpeg", ".webp")
CSS = """
body{font-family:-apple-system,Helvetica,Arial,sans-serif;font-size:10.3pt;line-height:1.5;color:#1b2430}
h1{font-size:23pt;margin:0 0 4px;letter-spacing:-0.01em}
h2{font-size:15pt;margin:1.5em 0 .4em;padding-bottom:3px;border-bottom:2px solid #2f6f5e;break-after:avoid}
h3{font-size:11.6pt;margin:1.1em 0 .3em;color:#2f6f5e;break-after:avoid}
p{margin:.45em 0}
table{border-collapse:collapse;width:100%;margin:8px 0;font-size:9.3pt;break-inside:auto}
tr{break-inside:avoid}
th{background:#e6f0ec;text-align:left}
th,td{border:1px solid #b8c4bf;padding:4px 7px;vertical-align:top}
code{font-family:Menlo,monospace;font-size:8.6pt;background:#f0efe9;padding:0 3px;border-radius:3px}
pre{background:#f0efe9;border:1px solid #d9d6c9;border-radius:6px;padding:7px 9px;font-size:8.4pt;line-height:1.35;white-space:pre-wrap;word-break:break-word;break-inside:avoid}
pre code{background:none;padding:0;font-size:8.4pt}
blockquote{margin:.6em 0;padding:6px 12px;background:#eaf5f0;border-left:4px solid #2f6f5e;border-radius:0 6px 6px 0;break-inside:avoid}
blockquote p{margin:.25em 0}
figure{margin:10px 0;text-align:center;break-inside:avoid}
figure img{max-width:100%;max-height:150mm;border:1px solid #c9d1cc;border-radius:4px;object-fit:contain}
figure.diagram{border:1px solid #d9d6c9;border-radius:8px;padding:8px;background:#fffdf8}
figcaption{font-size:8.8pt;color:#52606d;margin-top:3px}
.slot{border:2px dashed #9aa5b1;border-radius:8px;height:70px;display:flex;align-items:center;justify-content:center;color:#52606d;font-size:9.5pt;margin:8px 0;background:#fafaf7;text-align:center;padding:0 10px}
.meta{color:#52606d;font-size:9.5pt;margin:0 0 10px}
hr{border:0;border-top:1px solid #d9d6c9;margin:1.2em 0}
@page{size:A4;margin:15mm 15mm 16mm}
"""


def find_image(base_dir, src):
    stem, _ = os.path.splitext(os.path.join(base_dir, src))
    for ext in EXTS:
        if os.path.exists(stem + ext):
            return stem + ext
    return None


def embed(html, base_dir):
    def repl(m):
        alt, src = m.group(1), m.group(2)
        path = find_image(base_dir, src)
        name = os.path.basename(src)
        if not path:
            return f'<div class="slot">SCREENSHOT NEEDED: {alt}<br>save as {name}</div>'
        mime = "image/" + ("jpeg" if path.lower().endswith(("jpg", "jpeg")) else os.path.splitext(path)[1][1:])
        data = base64.b64encode(open(path, "rb").read()).decode()
        return f'<figure><img alt="{alt}" src="data:{mime};base64,{data}"><figcaption>{alt}</figcaption></figure>'

    return re.sub(r'<img alt="([^"]*)" src="([^"]+)"\s*/?>', repl, html)


def checklist_md():
    you = [s for s in SHOTS if s[6] == "you"]
    out = ["# Screenshot checklist", "",
           "<p class='meta'>LifeLog CI/CD project. Everything you need to capture, in the order you will naturally meet it.</p>", "",
           "## How to capture and name them", "",
           "1. On the Mac press **Cmd+Shift+4** (drag a rectangle) or **Cmd+Shift+5**. Capture only the area that matters, but keep it readable.",
           "2. Save each file as **PNG** with the **exact file name** in the table, into `~/lifelog-cicd/docs/screenshots/`.",
           "3. Either rebuild the PDFs yourself with `~/mpft/.venv/bin/python scripts/make_docs.py`, or send the files to me and I will rebuild them.", "",
           "> **Never show secrets.** The Docker Hub token must not appear in any screenshot. Do not open the `dockerhub-creds` credential. Your EC2 public IP is fine to show.", "",
           f"You need **{sum(1 for s in you if s[5])} required** screenshots and {sum(1 for s in you if not s[5])} optional ones. "
           f"The {len(SHOTS) - len(you)} app screens (light and dark theme, capture bar, log, insights, trackers, goals, mobile) are already captured and included.", ""]
    groups = []
    for s in you:
        if s[1] not in groups:
            groups.append(s[1])
    n = 0
    for g in groups:
        out += [f"## {g}", "", "| # | File name (.png) | How to capture | Must be visible | Need |", "|---|---|---|---|---|"]
        for stem, grp, cap, how, show, req, _ in you:
            if grp == g:
                n += 1
                how_md = how.replace("|", "/")
                out.append(f"| {n} | `{stem}` | {how_md} | {show} | {'required' if req else 'optional'} |")
        out.append("")
    out += ["## Order of work", "",
            "1. Take the AWS, Jenkins, Docker Hub, GitHub and Kubernetes shots while the first successful run is on screen.",
            "2. Take **app-aws-01-before** and **jenkins-05-stage-view** *before* the second run.",
            "3. Do the second run (merge `v2-goals`, push, Build Now) and take **k8s-04-rolling-update** while it deploys.",
            "4. When it is green take **app-aws-02-after**, **jenkins-08-two-runs** and **github-02-commits**.", "",
            "## Already captured for you", "",
            "| File | What it shows |", "|---|---|"]
    out += [f"| `{s[0]}` | {s[2]} |" for s in SHOTS if s[6] == "auto"]
    return "\n".join(out) + "\n"


def report_appendix(base):
    out = ["## 8. Screenshots", ""]
    group = None
    for stem, grp, cap, _how, _show, _req, _who in SHOTS:
        if grp != group:
            out += [f"### {grp}", ""]
            group = grp
        out += [f"![{cap}]({base}/screenshots/{stem}.png)", ""]
    return "\n".join(out)


def render(md_text, base_dir, title):
    html = markdown.markdown(md_text, extensions=["tables", "fenced_code", "sane_lists"])
    for name, fn in DIAGRAMS.items():
        html = html.replace(f"<p>{{{{diagram:{name}}}}}</p>", f'<figure class="diagram">{fn()}</figure>')
    html = embed(html, base_dir)
    return f"<html><head><meta charset='utf-8'><title>{title}</title><style>{CSS}</style></head><body>{html}</body></html>"


def to_pdf(html, out_path):
    with tempfile.NamedTemporaryFile("w", suffix=".html", delete=False) as f:
        f.write(html)
    subprocess.run([CHROME, "--headless", "--disable-gpu", "--no-pdf-header-footer", f"--print-to-pdf={out_path}", "file://" + f.name],
                   check=True, capture_output=True)
    os.unlink(f.name)
    print("wrote", os.path.relpath(out_path, ROOT))


def main():
    docs = os.path.join(ROOT, "docs")
    with open(os.path.join(docs, "SCREENSHOT_CHECKLIST.md"), "w") as f:
        f.write(checklist_md())
    readme = open(os.path.join(ROOT, "README.md")).read()
    readme = re.sub(r"## 8\. Screenshots.*", lambda _m: report_appendix("docs"), readme, flags=re.S)
    to_pdf(render(readme, ROOT, "LifeLog CI/CD report"), os.path.join(docs, "report.pdf"))
    for name in ("SCREENSHOT_CHECKLIST", "RECORDING_SCRIPT", "STUDY_GUIDE", "CICD_GUIDE"):
        path = os.path.join(docs, name + ".md")
        if os.path.exists(path):
            to_pdf(render(open(path).read(), docs, name), os.path.join(docs, name + ".pdf"))


if __name__ == "__main__":
    main()
