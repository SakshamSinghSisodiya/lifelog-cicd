"""Render README.md to docs/report.pdf (needs `markdown` and Google Chrome)."""
import os
import subprocess
import sys
import tempfile

import markdown

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CHROME = "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"
SHOTS = ["Jenkins dashboard with the pipeline job", "Pipeline stage view (all green)",
         "Console Output of a successful run", "Docker Hub repository with tags",
         "kubectl get pods,deploy,svc", "App in the browser (build 1)", "App after the second run (Goals page, new build and pod)"]
CSS = """body{font-family:-apple-system,Helvetica,Arial,sans-serif;font-size:11pt;line-height:1.45;color:#111}
h1{font-size:21pt}h2{font-size:15pt;margin-top:1.3em;border-bottom:1px solid #999}
table{border-collapse:collapse;width:100%;font-size:9.5pt}th,td{border:1px solid #888;padding:4px 6px;text-align:left;vertical-align:top}
pre{border:1px solid #bbb;padding:6px;font-size:9pt;white-space:pre-wrap}code{font-family:Menlo,monospace;font-size:9pt}
.shot{border:2px dashed #888;height:120px;margin:10px 0;display:flex;align-items:center;justify-content:center;color:#555}
@page{size:A4;margin:16mm}"""


def main():
    text = open(os.path.join(ROOT, "README.md")).read()
    html = markdown.markdown(text, extensions=["tables", "fenced_code"])
    slots = "".join(f'<div class="shot">[Screenshot {i}: {s}]</div>' for i, s in enumerate(SHOTS, 1))
    html = html.replace("<p>See <code>docs/report.pdf</code> for labelled screenshot slots.</p>", slots)
    page = f"<html><head><meta charset='utf-8'><style>{CSS}</style></head><body>{html}</body></html>"
    with tempfile.NamedTemporaryFile("w", suffix=".html", delete=False) as f:
        f.write(page)
    out = os.path.join(ROOT, "docs", "report.pdf")
    subprocess.run([CHROME, "--headless", "--disable-gpu", "--no-pdf-header-footer",
                    f"--print-to-pdf={out}", "file://" + f.name], check=True, capture_output=True)
    os.unlink(f.name)
    print("wrote", out)


if __name__ == "__main__":
    sys.exit(main())
