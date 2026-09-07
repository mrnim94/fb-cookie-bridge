"""Minimal cookie management UI and upload endpoint."""
from __future__ import annotations

import json
import logging
import os
from pathlib import Path

LOG = logging.getLogger(__name__)

UPLOAD_HTML = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>FB Cookie Bridge — Upload Cookie</title>
<style>
  :root { --bg: #0d1117; --panel: #161b22; --border: #30363d; --accent: #58a6ff; --text: #c9d1d9; --muted: #8b949e; --green: #3fb950; --red: #f85149; }
  * { box-sizing: border-box; margin: 0; padding: 0; }
  body { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Helvetica, Arial, sans-serif; background: var(--bg); color: var(--text); display: flex; justify-content: center; align-items: center; min-height: 100vh; padding: 20px; }
  .card { background: var(--panel); border: 1px solid var(--border); border-radius: 12px; padding: 32px; max-width: 520px; width: 100%; }
  h1 { font-size: 20px; margin-bottom: 6px; }
  .sub { color: var(--muted); font-size: 14px; margin-bottom: 24px; }
  .drop-zone { border: 2px dashed var(--border); border-radius: 8px; padding: 40px 20px; text-align: center; cursor: pointer; transition: border-color 0.2s, background 0.2s; margin-bottom: 16px; }
  .drop-zone.over { border-color: var(--accent); background: rgba(88,166,255,0.06); }
  .drop-zone p { color: var(--muted); font-size: 14px; }
  .drop-zone .icon { font-size: 36px; margin-bottom: 8px; }
  .file-name { color: var(--accent); font-size: 14px; margin-bottom: 16px; min-height: 20px; }
  input[type=file] { display: none; }
  button { background: var(--accent); color: #fff; border: none; border-radius: 6px; padding: 10px 24px; font-size: 15px; cursor: pointer; width: 100%; transition: opacity 0.2s; }
  button:disabled { opacity: 0.4; cursor: not-allowed; }
  .result { margin-top: 16px; padding: 12px; border-radius: 6px; font-size: 14px; display: none; }
  .result.ok { background: rgba(63,185,80,0.1); border: 1px solid var(--green); color: var(--green); display: block; }
  .result.err { background: rgba(248,81,73,0.1); border: 1px solid var(--red); color: var(--red); display: block; }
  .status { margin-top: 16px; padding: 12px; border-radius: 6px; font-size: 13px; background: rgba(88,166,255,0.06); border: 1px solid var(--border); }
  .status .label { color: var(--muted); }
  .status .val { color: var(--text); font-weight: 600; }
</style>
</head>
<body>
<div class="card">
  <h1>🍪 Upload Facebook Cookie</h1>
  <p class="sub">Upload J2TEAM cookie export JSON. Overwrites current cookie file on disk.</p>

  <div class="drop-zone" id="dropZone">
    <div class="icon">📂</div>
    <p>Drop <code>.json</code> file here or click to browse</p>
  </div>
  <input type="file" id="fileInput" accept=".json,application/json">
  <div class="file-name" id="fileName"></div>
  <button id="uploadBtn" disabled>Upload Cookie</button>
  <div class="result" id="result"></div>

  <div class="status" id="status">
    <span class="label">Cookie status:</span> <span class="val" id="cookieStatus">checking…</span>
  </div>
</div>

<script>
const dropZone = document.getElementById('dropZone');
const fileInput = document.getElementById('fileInput');
const uploadBtn = document.getElementById('uploadBtn');
const result = document.getElementById('result');
const fileName = document.getElementById('fileName');
let selectedFile = null;

dropZone.addEventListener('click', () => fileInput.click());
dropZone.addEventListener('dragover', e => { e.preventDefault(); dropZone.classList.add('over'); });
dropZone.addEventListener('dragleave', () => dropZone.classList.remove('over'));
dropZone.addEventListener('drop', e => {
  e.preventDefault(); dropZone.classList.remove('over');
  if (e.dataTransfer.files.length) selectFile(e.dataTransfer.files[0]);
});
fileInput.addEventListener('change', () => { if (fileInput.files.length) selectFile(fileInput.files[0]); });

function selectFile(f) {
  selectedFile = f;
  fileName.textContent = f.name + ' (' + (f.size / 1024).toFixed(1) + ' KB)';
  uploadBtn.disabled = false;
  result.className = 'result'; result.textContent = '';
}

uploadBtn.addEventListener('click', async () => {
  if (!selectedFile) return;
  uploadBtn.disabled = true;
  result.className = 'result'; result.textContent = '';
  try {
    const text = await selectedFile.text();
    const resp = await fetch('/v1/cookie/upload', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: text
    });
    const data = await resp.json();
    if (resp.ok) {
      result.className = 'result ok';
      result.textContent = '✅ ' + (data.message || 'Cookie saved.');
      checkStatus();
    } else {
      result.className = 'result err';
      result.textContent = '❌ ' + (data.error || 'Upload failed.');
    }
  } catch (e) {
    result.className = 'result err';
    result.textContent = '❌ Network error: ' + e.message;
  }
  uploadBtn.disabled = false;
});

async function checkStatus() {
  const el = document.getElementById('cookieStatus');
  try {
    const resp = await fetch('/v1/cookie/status');
    const data = await resp.json();
    if (data.valid) {
      el.textContent = '✅ Loaded — ' + data.cookie_count + ' cookies';
      el.style.color = 'var(--green)';
    } else {
      el.textContent = '❌ ' + (data.error || 'No valid cookie');
      el.style.color = 'var(--red)';
    }
  } catch (e) {
    el.textContent = '⚠️ Cannot check';
    el.style.color = 'var(--muted)';
  }
}
checkStatus();
</script>
</body>
</html>"""


def cookie_upload_ui() -> bytes:
    """Return the upload page HTML."""
    return UPLOAD_HTML.encode("utf-8")


def handle_cookie_upload(body: bytes, cookie_file: Path) -> tuple[int, dict]:
    """Validate and save uploaded cookie JSON. Returns (status_code, response_dict)."""
    try:
        raw = json.loads(body)
    except json.JSONDecodeError:
        return 400, {"error": "invalid_json", "message": "File is not valid JSON."}

    # Accept J2TEAM format (list of cookie objects) or wrapped {"cookies": [...]}
    cookies = raw
    if isinstance(raw, dict):
        cookies = raw.get("cookies", raw)
    if not isinstance(cookies, list):
        return 400, {"error": "invalid_format", "message": "Expected a JSON array of cookie objects or {\"cookies\": [...]}"}
    if len(cookies) == 0:
        return 400, {"error": "empty_cookies", "message": "Cookie list is empty."}

    valid = [c for c in cookies if isinstance(c, dict) and c.get("name") and "value" in c]
    if len(valid) == 0:
        return 400, {"error": "no_valid_cookies", "message": "No cookie objects with 'name' and 'value' found."}

    # Ensure parent directory exists
    cookie_file.parent.mkdir(parents=True, exist_ok=True)

    # Atomic write: write to temp then rename
    tmp_path = cookie_file.with_suffix(".tmp")
    try:
        tmp_path.write_text(json.dumps(cookies, ensure_ascii=False, indent=2), encoding="utf-8")
        tmp_path.replace(cookie_file)
    except OSError as exc:
        LOG.exception("cookie_write_failed")
        return 500, {"error": "write_failed", "message": f"Cannot write cookie file: {exc}"}

    LOG.info("cookie_uploaded count=%d path=%s", len(valid), cookie_file)
    return 200, {"status": "ok", "message": f"Saved {len(valid)} cookies.", "cookie_count": len(valid)}


def handle_cookie_status(cookie_file: Path) -> tuple[int, dict]:
    """Check if cookie file exists and is loadable."""
    if not cookie_file.exists():
        return 200, {"valid": False, "error": "cookie_file_missing"}
    try:
        raw = json.loads(cookie_file.read_text(encoding="utf-8"))
        cookies = raw.get("cookies", raw) if isinstance(raw, dict) else raw
        if not isinstance(cookies, list):
            return 200, {"valid": False, "error": "invalid_format"}
        valid = [c for c in cookies if isinstance(c, dict) and c.get("name") and "value" in c]
        return 200, {"valid": True, "cookie_count": len(valid)}
    except Exception as exc:
        return 200, {"valid": False, "error": str(exc)}
