import os
import re
import json
import hmac
import hashlib
import secrets
import sqlite3
import uuid
import shutil
import time
import urllib.request
import urllib.error
from datetime import datetime, timezone
from functools import wraps
from pathlib import Path

from flask import Flask, request, session, redirect, url_for, jsonify, send_file, render_template_string, abort
from werkzeug.utils import secure_filename

app = Flask(__name__)
app.config.update(
    SECRET_KEY=os.environ.get("SECRET_KEY", "development-only-change-this"),
    MAX_CONTENT_LENGTH=12 * 1024 * 1024,
    SESSION_COOKIE_HTTPONLY=True,
    SESSION_COOKIE_SECURE=True,
    SESSION_COOKIE_SAMESITE="Lax",
)
ADMIN_EMAIL = os.environ.get("ADMIN_EMAIL", "orleasuarez@gmail.com").strip().lower()
DATA_DIR = Path(os.environ.get("DATA_DIR", "./data")).resolve()
FILES_DIR = DATA_DIR / "files"
TEMP_DIR = DATA_DIR / "temporary"
PERSISTENT_STORAGE = os.environ.get("PERSISTENT_STORAGE", "no").lower() == "yes"
MAX_FILE_SIZE = int(os.environ.get("MAX_FILE_SIZE", str(50 * 1024 * 1024 * 1024)))
CHUNK_SIZE = 6 * 1024 * 1024
for folder in (DATA_DIR, FILES_DIR, TEMP_DIR):
    folder.mkdir(parents=True, exist_ok=True)

def db():
    con = sqlite3.connect(DATA_DIR / "cheaters.db", timeout=30)
    con.row_factory = sqlite3.Row
    return con

def init_db():
    with db() as con:
        con.execute("""CREATE TABLE IF NOT EXISTS files (
            id TEXT PRIMARY KEY, original_name TEXT NOT NULL, storage_name TEXT NOT NULL,
            description TEXT NOT NULL DEFAULT '', size INTEGER NOT NULL, created_at TEXT NOT NULL
        )""")
        con.execute("""CREATE TABLE IF NOT EXISTS login_codes (
            email TEXT PRIMARY KEY, code_hash TEXT NOT NULL, expires_at INTEGER NOT NULL,
            attempts INTEGER NOT NULL DEFAULT 0, last_sent INTEGER NOT NULL
        )""")
init_db()

def csrf_token():
    if "csrf" not in session:
        session["csrf"] = secrets.token_urlsafe(24)
    return session["csrf"]

@app.before_request
def security_headers():
    pass

@app.after_request
def add_security_headers(response):
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    response.headers["Cache-Control"] = "no-store" if request.path.startswith("/admin") else "public, max-age=60"
    response.headers["Content-Security-Policy"] = "default-src 'self'; style-src 'self' 'unsafe-inline'; script-src 'self' 'unsafe-inline'; img-src 'self' data:; connect-src 'self'; base-uri 'self'; frame-ancestors 'none'"
    return response

def admin_required(fn):
    @wraps(fn)
    def wrapped(*args, **kwargs):
        if session.get("admin_email") != ADMIN_EMAIL:
            if request.path.startswith("/api/"):
                return jsonify(error="Sessão administrativa necessária."), 401
            return redirect(url_for("admin_login"))
        return fn(*args, **kwargs)
    return wrapped

def check_csrf():
    supplied = request.headers.get("X-CSRF-Token") or request.form.get("csrf")
    return bool(supplied and session.get("csrf") and hmac.compare_digest(supplied, session["csrf"]))

def send_login_code(code):
    api_key = os.environ.get("RESEND_API_KEY", "").strip()
    mail_from = os.environ.get("MAIL_FROM", "").strip()
    if not api_key or not mail_from:
        raise RuntimeError("Falta configurar RESEND_API_KEY e MAIL_FROM no Render.")
    payload = json.dumps({
        "from": mail_from,
        "to": [ADMIN_EMAIL],
        "subject": "Seu código de acesso — Cheaters FiveM",
        "html": "<div style='font-family:Arial,sans-serif;color:#171717'><h2>Cheaters FiveM</h2><p>Seu código de acesso:</p><p style='font-size:30px;font-weight:700;letter-spacing:8px'>" + code + "</p><p>Ele expira em 10 minutos. Se você não solicitou, ignore este e-mail.</p></div>"
    }).encode("utf-8")
    req = urllib.request.Request(
        "https://api.resend.com/emails", data=payload,
        headers={"Authorization": "Bearer " + api_key, "Content-Type": "application/json"},
        method="POST"
    )
    try:
        with urllib.request.urlopen(req, timeout=15) as response:
            if response.status not in (200, 201):
                raise RuntimeError("O provedor de e-mail não aceitou o envio.")
    except urllib.error.HTTPError as exc:
        raise RuntimeError("Falha no envio do e-mail (HTTP " + str(exc.code) + ").") from exc

BASE_STYLE = """
:root{color-scheme:dark;--bg:#090b10;--panel:#11151e;--panel2:#171d29;--line:#252d3c;--text:#f2f5fa;--muted:#9aa5b5;--accent:#7c5cff;--accent2:#9a83ff;--red:#ff647c;--green:#49d49d}
*{box-sizing:border-box}body{margin:0;background:radial-gradient(ellipse at 50% -30%,#1c2040 0%,#090b10 55%);color:var(--text);font:15px/1.5 Inter,ui-sans-serif,system-ui,-apple-system,Segoe UI,sans-serif;min-height:100vh}
a{color:inherit;text-decoration:none}.wrap{width:min(1080px,calc(100% - 36px));margin:auto}
header{height:76px;border-bottom:1px solid #ffffff12;background:#090b10c9;backdrop-filter:blur(14px);display:flex;align-items:center}
.nav{display:flex;align-items:center;justify-content:space-between;gap:16px}.brand{font-weight:850;letter-spacing:.2px;font-size:18px}.brand span{color:var(--accent2)}
.nav a,.quiet{color:var(--muted);font-size:13px}.hero{padding:72px 0 36px}.eyebrow{color:var(--accent2);font-size:11px;font-weight:800;letter-spacing:2px;text-transform:uppercase}
h1{font-size:clamp(34px,6vw,54px);line-height:1.08;letter-spacing:-1.7px;margin:12px 0}.lead{color:var(--muted);max-width:600px;font-size:16px}
.toolbar{display:flex;justify-content:space-between;align-items:center;gap:12px;margin:34px 0 16px}.toolbar h2{font-size:17px;margin:0}
.grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(260px,1fr));gap:14px;padding-bottom:70px}
.file,.panel{background:linear-gradient(145deg,#151b27,#10141d);border:1px solid var(--line);border-radius:16px;padding:20px;box-shadow:0 12px 32px #0002}
.file-icon{width:42px;height:42px;border-radius:12px;background:#7c5cff20;display:grid;place-items:center;color:#b8aaff;font-size:20px;margin-bottom:16px}
.file h3{font-size:16px;margin:0 0 7px;overflow-wrap:anywhere}.desc{font-size:13px;color:var(--muted);min-height:38px;white-space:pre-wrap;overflow-wrap:anywhere}
.meta{display:flex;gap:10px;color:#8d99ac;font-size:11px;margin:14px 0 16px}
.btn{border:0;border-radius:10px;background:var(--accent);color:white;font-weight:750;padding:11px 15px;cursor:pointer;display:inline-flex;align-items:center;justify-content:center;gap:8px;font-size:13px}
.btn:hover{background:var(--accent2)}.btn:disabled{opacity:.5;cursor:not-allowed}.btn.secondary{background:#222a39;color:#dbe2ed}.btn.danger{background:#47202a;color:#ffb5c0}
.empty{grid-column:1/-1;padding:36px;text-align:center;color:var(--muted);border:1px dashed var(--line);border-radius:16px}
footer{border-top:1px solid #ffffff12;padding:22px 0;color:#657184;font-size:12px}
.admin-head{padding:40px 0 20px}.panel{margin:16px 0}.panel h2{margin:0 0 16px;font-size:18px}
label{display:block;color:#aab4c3;font-size:12px;margin:12px 0 6px}
input,textarea{width:100%;background:#0b0f17;border:1px solid #30394a;border-radius:9px;padding:12px;color:var(--text);outline:none;font:inherit}
input:focus,textarea:focus{border-color:var(--accent)}textarea{min-height:84px;resize:vertical}
.formrow{display:grid;grid-template-columns:1fr 1fr;gap:12px}.hint{color:var(--muted);font-size:12px}.notice{border:1px solid #624e23;background:#332a16;color:#f0d89e;border-radius:11px;padding:13px 15px;font-size:13px;margin:14px 0}
.status{font-size:12px;color:var(--muted);margin-top:10px}.admin-file{display:flex;justify-content:space-between;gap:15px;align-items:center;border-top:1px solid var(--line);padding:14px 0}.admin-file:first-child{border:0}.actions{display:flex;gap:7px;flex-wrap:wrap}.actions .btn{padding:8px 10px;font-size:11px}
.center{min-height:calc(100vh - 77px);display:grid;place-items:center;padding:32px 0}.login{width:min(420px,100%)}.login h1{font-size:30px;letter-spacing:-.5px}
@media(max-width:600px){.hero{padding-top:50px}.formrow{grid-template-columns:1fr}.admin-file{align-items:flex-start;flex-direction:column}.toolbar{align-items:flex-start;flex-direction:column}}
"""

def page(title, body, scripts=""):
    return render_template_string("""<!doctype html><html lang="pt-br"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><meta name="theme-color" content="#090b10"><title>{{title}} · Cheaters FiveM</title><style>{{style}}</style></head><body>{{body|safe}}{{scripts|safe}}</body></html>""", title=title, style=BASE_STYLE, body=body, scripts=scripts)

def fmt_size(size):
    units = ["B", "KB", "MB", "GB", "TB"]
    value = float(size)
    for unit in units:
        if value < 1024 or unit == "TB":
            return (str(int(value)) if unit == "B" else f"{value:.1f}") + " " + unit
        value /= 1024
    return str(size) + " B"

@app.get("/")
def home():
    with db() as con:
        rows = con.execute("SELECT id,original_name,description,size,created_at FROM files ORDER BY created_at DESC").fetchall()
    cards = "".join(
        '<article class="file"><div class="file-icon">⇩</div><h3>' + html_escape(r["original_name"]) +
        '</h3><div class="desc">' + html_escape(r["description"] or "Arquivo disponibilizado para download.") +
        '</div><div class="meta"><span>' + fmt_size(r["size"]) + '</span><span>·</span><span>' +
        r["created_at"][:10] + '</span></div><a class="btn" href="/download/' + r["id"] + '">↓ Baixar arquivo</a></article>'
        for r in rows
    )
    if not cards:
        cards = '<div class="empty">Nenhum arquivo publicado ainda.<br><span class="hint">Os novos downloads aparecerão aqui.</span></div>'
    body = """<header><div class="wrap nav"><a class="brand" href="/">CHEATERS <span>FIVEM</span></a><a href="/admin">Administração ↗</a></div></header>
    <main class="wrap"><section class="hero"><div class="eyebrow">Central de downloads</div><h1>Arquivos e atualizações<br>em um só lugar.</h1><p class="lead">Baixe os arquivos disponibilizados pela equipe Cheaters FiveM com praticidade.</p></section>
    <div class="toolbar"><h2>Arquivos disponíveis</h2><span class="quiet">""" + str(len(rows)) + """ arquivo(s)</span></div><section class="grid">""" + cards + """</section></main>
    <footer><div class="wrap">Cheaters FiveM · Central de downloads</div></footer>"""
    return page("Downloads", body)

def html_escape(value):
    import html
    return html.escape(str(value or ""))

@app.get("/download/<file_id>")
def download(file_id):
    with db() as con:
        row = con.execute("SELECT * FROM files WHERE id=?", (file_id,)).fetchone()
    if not row:
        abort(404)
    path = FILES_DIR / row["storage_name"]
    if not path.is_file():
        abort(404)
    return send_file(path, as_attachment=True, download_name=row["original_name"], conditional=True)

@app.get("/admin")
def admin():
    if session.get("admin_email") != ADMIN_EMAIL:
        return redirect(url_for("admin_login"))
    token = csrf_token()
    with db() as con:
        rows = con.execute("SELECT * FROM files ORDER BY created_at DESC").fetchall()
    notice = "" if PERSISTENT_STORAGE else '<div class="notice">O disco persistente ainda não está ativado. Por segurança, os uploads estão bloqueados para evitar perda de arquivos após reinicializações. Será necessário conectar um Render Disk em /var/data e habilitar PERSISTENT_STORAGE=yes.</div>'
    items = "".join(
        '<div class="admin-file"><div><strong>' + html_escape(r["original_name"]) + '</strong><div class="hint">' +
        fmt_size(r["size"]) + ' · ' + html_escape(r["description"]) + '</div></div><div class="actions"><button class="btn secondary" onclick="editFile(\'' +
        r["id"] + '\',\'' + html_escape(r["original_name"]).replace("&#x27;","\\'") + '\',\'' +
        html_escape(r["description"]).replace("&#x27;","\\'") + '\')">Editar</button><button class="btn danger" onclick="deleteFile(\'' +
        r["id"] + '\')">Excluir</button></div></div>' for r in rows
    ) or '<div class="hint">Nenhum arquivo publicado.</div>'
    body = """<header><div class="wrap nav"><a class="brand" href="/">CHEATERS <span>FIVEM</span></a><a href="/">Ver site ↗</a></div></header>
    <main class="wrap"><section class="admin-head"><div class="eyebrow">Área restrita</div><h1 style="font-size:34px">Administração</h1><p class="quiet">Conectado como """ + html_escape(ADMIN_EMAIL) + """ · <a href="/admin/logout">Sair</a></p></section>
    """ + notice + """
    <section class="panel"><h2>Adicionar arquivo</h2><p class="hint">Os arquivos são enviados em partes de 6 MB. Não feche esta página até o envio terminar.</p>
    <form id="uploadForm"><label>Arquivo</label><input type="file" id="file" required><label>Descrição</label><textarea id="description" placeholder="Explique o que é este arquivo (opcional)"></textarea>
    <div style="margin-top:16px"><button class="btn" id="uploadButton" type="submit" """ + ("" if PERSISTENT_STORAGE else "disabled") + """>Enviar arquivo</button></div><div id="uploadStatus" class="status"></div></form></section>
    <section class="panel"><h2>Arquivos publicados</h2><div id="fileList">""" + items + """</div></section></main><footer><div class="wrap">Cheaters FiveM · Administração</div></footer>"""
    scripts = """<script>
const CSRF=""" + json.dumps(token) + """;
async function api(url,opts={}){opts.headers={...(opts.headers||{}),'X-CSRF-Token':CSRF};const r=await fetch(url,opts);let d={};try{d=await r.json()}catch{}if(!r.ok)throw Error(d.error||'Falha na solicitação.');return d}
document.getElementById('uploadForm').addEventListener('submit',async e=>{e.preventDefault();const f=document.getElementById('file').files[0];if(!f)return;const btn=document.getElementById('uploadButton'),s=document.getElementById('uploadStatus');btn.disabled=true;try{const id=crypto.randomUUID(),desc=document.getElementById('description').value;let offset=0;while(offset<f.size){const end=Math.min(offset+6*1024*1024,f.size),chunk=f.slice(offset,end);const form=new FormData();form.append('chunk',chunk);form.append('upload_id',id);form.append('filename',f.name);form.append('description',desc);form.append('total_size',String(f.size));form.append('offset',String(offset));await api('/api/admin/upload-chunk',{method:'POST',body:form});offset=end;s.textContent='Enviando: '+Math.floor(offset/f.size*100)+'%';}s.textContent='Arquivo publicado com sucesso!';location.reload()}catch(err){s.textContent=err.message;btn.disabled=false}});
async function deleteFile(id){if(!confirm('Excluir este arquivo?'))return;try{await api('/api/admin/files/'+id,{method:'DELETE'});location.reload()}catch(e){alert(e.message)}}
async function editFile(id,name,desc){const next=prompt('Nome do arquivo:',name);if(next===null)return;const d=prompt('Descrição:',desc);if(d===null)return;try{await api('/api/admin/files/'+id,{method:'PATCH',headers:{'Content-Type':'application/json'},body:JSON.stringify({name:next,description:d})});location.reload()}catch(e){alert(e.message)}}
</script>"""
    return page("Administração", body, scripts)

LOGIN_HTML = """
<header><div class="wrap nav"><a class="brand" href="/">CHEATERS <span>FIVEM</span></a><a href="/">Voltar ao site</a></div></header>
<main class="wrap center"><section class="panel login"><div class="eyebrow">Acesso administrativo</div><h1>Entrar no painel</h1>
<p class="hint">Enviaremos um código de verificação para o e-mail autorizado.</p>
{% if error %}<div class="notice">{{error}}</div>{% endif %}
<form method="post" action="/admin/send-code"><input type="hidden" name="csrf" value="{{csrf}}"><button class="btn" type="submit" style="width:100%">Enviar código por e-mail</button></form>
{% if sent %}<form method="post" action="/admin/verify"><input type="hidden" name="csrf" value="{{csrf}}"><label>Código de 6 dígitos</label><input name="code" inputmode="numeric" pattern="[0-9]{6}" maxlength="6" required placeholder="000000"><button class="btn" style="width:100%;margin-top:14px">Confirmar código</button></form>{% endif %}
</section></main>"""

@app.get("/admin/login")
def admin_login():
    if session.get("admin_email") == ADMIN_EMAIL:
        return redirect(url_for("admin"))
    return page("Entrar", render_template_string(LOGIN_HTML, csrf=csrf_token(), error=request.args.get("error",""), sent=request.args.get("sent")=="1"))

@app.post("/admin/send-code")
def send_code():
    if not check_csrf():
        abort(400)
    now = int(time.time())
    with db() as con:
        old = con.execute("SELECT last_sent FROM login_codes WHERE email=?", (ADMIN_EMAIL,)).fetchone()
        if old and now - old["last_sent"] < 60:
            return redirect(url_for("admin_login", error="Aguarde 1 minuto antes de pedir outro código."))
        code = f"{secrets.randbelow(1000000):06d}"
        digest = hmac.new(app.config["SECRET_KEY"].encode(), code.encode(), hashlib.sha256).hexdigest()
        con.execute("INSERT OR REPLACE INTO login_codes(email,code_hash,expires_at,attempts,last_sent) VALUES(?,?,?,?,?)",
                    (ADMIN_EMAIL, digest, now + 600, 0, now))
    try:
        send_login_code(code)
    except Exception as exc:
        app.logger.error("Falha ao enviar código de login: %s", str(exc))
        return redirect(url_for("admin_login", error="O envio de e-mail ainda não está configurado no Render."))
    return redirect(url_for("admin_login", sent="1"))

@app.post("/admin/verify")
def verify_code():
    if not check_csrf():
        abort(400)
    code = re.sub(r"\D", "", request.form.get("code", ""))
    if len(code) != 6:
        return redirect(url_for("admin_login", sent="1", error="Código inválido."))
    now = int(time.time())
    digest = hmac.new(app.config["SECRET_KEY"].encode(), code.encode(), hashlib.sha256).hexdigest()
    with db() as con:
        row = con.execute("SELECT * FROM login_codes WHERE email=?", (ADMIN_EMAIL,)).fetchone()
        if not row or row["expires_at"] < now or row["attempts"] >= 5:
            con.execute("DELETE FROM login_codes WHERE email=?", (ADMIN_EMAIL,))
            return redirect(url_for("admin_login", error="Código expirado. Solicite outro."))
        if not hmac.compare_digest(row["code_hash"], digest):
            con.execute("UPDATE login_codes SET attempts=attempts+1 WHERE email=?", (ADMIN_EMAIL,))
            return redirect(url_for("admin_login", sent="1", error="Código incorreto."))
        con.execute("DELETE FROM login_codes WHERE email=?", (ADMIN_EMAIL,))
    session.clear()
    session["admin_email"] = ADMIN_EMAIL
    session["csrf"] = secrets.token_urlsafe(24)
    session.permanent = True
    app.permanent_session_lifetime = 12 * 60 * 60
    return redirect(url_for("admin"))

@app.get("/admin/logout")
def logout():
    session.clear()
    return redirect(url_for("home"))

@app.post("/api/admin/upload-chunk")
@admin_required
def upload_chunk():
    if not check_csrf():
        return jsonify(error="Verificação de segurança falhou."), 400
    if not PERSISTENT_STORAGE:
        return jsonify(error="Uploads bloqueados: conecte um disco persistente no Render e habilite PERSISTENT_STORAGE=yes."), 503
    upload_id = request.form.get("upload_id", "")
    if not re.fullmatch(r"[a-fA-F0-9-]{32,36}", upload_id):
        return jsonify(error="Identificador de envio inválido."), 400
    try:
        total = int(request.form.get("total_size", "0"))
        offset = int(request.form.get("offset", "-1"))
    except ValueError:
        return jsonify(error="Tamanho inválido."), 400
    if total <= 0 or total > MAX_FILE_SIZE or offset < 0:
        return jsonify(error="Arquivo excede o limite configurado."), 413
    chunk = request.files.get("chunk")
    if not chunk:
        return jsonify(error="Parte do arquivo não recebida."), 400
    temp_path = TEMP_DIR / (upload_id + ".part")
    current = temp_path.stat().st_size if temp_path.exists() else 0
    if current != offset or offset + request.content_length > total + 1024 * 1024:
        return jsonify(error="Parte fora de ordem. Reinicie o envio."), 409
    chunk.save(temp_path, buffer_size=1024 * 1024)
    written = temp_path.stat().st_size
    if written > total:
        temp_path.unlink(missing_ok=True)
        return jsonify(error="Tamanho enviado inválido."), 400
    if written == total:
        original_name = secure_filename(request.form.get("filename", "")) or "arquivo"
        if len(original_name) > 180:
            original_name = original_name[-180:]
        description = request.form.get("description", "")[:1000]
        storage_name = upload_id + ".bin"
        final_path = FILES_DIR / storage_name
        os.replace(temp_path, final_path)
        with db() as con:
            con.execute("INSERT INTO files(id,original_name,storage_name,description,size,created_at) VALUES(?,?,?,?,?,?)",
                        (upload_id, original_name, storage_name, description, total, datetime.now(timezone.utc).isoformat()))
        return jsonify(done=True, id=upload_id)
    return jsonify(done=False, received=written)

@app.route("/api/admin/files/<file_id>", methods=["PATCH", "DELETE"])
@admin_required
def manage_file(file_id):
    if not check_csrf():
        return jsonify(error="Verificação de segurança falhou."), 400
    with db() as con:
        row = con.execute("SELECT * FROM files WHERE id=?", (file_id,)).fetchone()
        if not row:
            return jsonify(error="Arquivo não encontrado."), 404
        if request.method == "DELETE":
            (FILES_DIR / row["storage_name"]).unlink(missing_ok=True)
            con.execute("DELETE FROM files WHERE id=?", (file_id,))
            return jsonify(ok=True)
        data = request.get_json(silent=True) or {}
        name = secure_filename(str(data.get("name", row["original_name"]))) or row["original_name"]
        if len(name) > 180:
            name = name[-180:]
        description = str(data.get("description", row["description"]))[:1000]
        con.execute("UPDATE files SET original_name=?,description=? WHERE id=?", (name, description, file_id))
    return jsonify(ok=True)

@app.get("/health")
def health():
    return jsonify(status="ok", app="Cheaters FiveM")

@app.errorhandler(413)
def too_large(_):
    return jsonify(error="Parte enviada muito grande. Tente novamente."), 413

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", "10000")))
