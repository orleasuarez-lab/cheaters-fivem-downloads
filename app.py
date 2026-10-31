import os
import re
import json
import html
import hmac
import base64
import secrets
import uuid
import time
import urllib.parse
import urllib.request
import urllib.error
from datetime import datetime, timezone
from functools import wraps

from flask import Flask, request, session, redirect, url_for, jsonify, render_template_string, abort
from jinja2 import select_autoescape

app = Flask(__name__)
app.config.update(
    SECRET_KEY=os.environ.get("SECRET_KEY", "change-this-secret-before-production"),
    SESSION_COOKIE_HTTPONLY=True,
    SESSION_COOKIE_SECURE=True,
    SESSION_COOKIE_SAMESITE="Lax",
    PERMANENT_SESSION_LIFETIME=60 * 60 * 12,
    MAX_CONTENT_LENGTH=30 * 1024 * 1024,
)

ADMIN_PASSWORD = os.environ.get("ADMIN_PASSWORD", "").strip()
GITHUB_TOKEN = os.environ.get("GITHUB_TOKEN", "").strip()
GITHUB_REPOSITORY = os.environ.get("GITHUB_REPOSITORY", "orleasuarez-lab/cheaters-fivem-downloads").strip()
GITHUB_BRANCH = os.environ.get("GITHUB_BRANCH", "main").strip()
GITHUB_DATA_PATH = os.environ.get("GITHUB_DATA_PATH", "links.json").strip()
GITHUB_UPLOADS_PATH = os.environ.get("GITHUB_UPLOADS_PATH", "uploads").strip().strip("/")

BASE_STYLE = """
:root{color-scheme:dark;--bg:#080a10;--panel:#111722;--panel2:#161f2d;--line:#253247;--text:#f4f6fb;--muted:#9ba8bc;--purple:#8b72ff;--cyan:#57d6df;--green:#62d6a2;--red:#ff7187}
*{box-sizing:border-box}html{scroll-behavior:smooth}body{margin:0;background:radial-gradient(ellipse at 50% -25%,#25204b 0,#0a0d16 48%,#080a10 100%);color:var(--text);font:15px/1.55 Inter,system-ui,-apple-system,Segoe UI,sans-serif;min-height:100vh}
a{color:inherit;text-decoration:none}.wrap{width:min(1100px,calc(100% - 36px));margin:auto}
header{height:74px;border-bottom:1px solid #ffffff12;background:#080a10d9;backdrop-filter:blur(14px);position:sticky;top:0;z-index:5}
.nav{height:100%;display:flex;align-items:center;justify-content:space-between;gap:16px}.brand{font-size:18px;font-weight:900;letter-spacing:.5px}.brand b{color:var(--purple)}
.navlink{color:var(--muted);font-size:13px}.navlink:hover{color:white}
.hero{padding:76px 0 44px}.tag{display:inline-flex;align-items:center;gap:8px;color:#c2b8ff;background:#8b72ff1c;border:1px solid #8b72ff45;border-radius:999px;padding:6px 11px;font-size:11px;font-weight:800;letter-spacing:1.3px;text-transform:uppercase}
h1{font-size:clamp(38px,7vw,66px);line-height:1.02;letter-spacing:-2.5px;margin:20px 0 15px}.hero h1 span{color:var(--purple)}.lead{max-width:620px;color:var(--muted);font-size:16px;margin:0}
.stats{display:flex;gap:12px;flex-wrap:wrap;margin-top:28px}.stat{border:1px solid var(--line);background:#101522a8;padding:9px 13px;border-radius:11px;color:var(--muted);font-size:12px}.stat strong{color:white}
.catalog-head{display:flex;justify-content:space-between;align-items:end;gap:15px;margin:12px 0 18px}.catalog-head h2{margin:0;font-size:20px;letter-spacing:-.4px}.catalog-head p{margin:3px 0 0;color:var(--muted);font-size:12px}
.tools{display:flex;gap:10px;align-items:center;margin-bottom:18px}.search{flex:1;min-width:0;background:#101622;border:1px solid var(--line);border-radius:11px;padding:12px 14px;color:white;font:inherit;outline:none}.search:focus,input:focus,textarea:focus{border-color:var(--purple)}
.grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(260px,1fr));gap:15px;padding-bottom:76px}
.card,.panel{background:linear-gradient(145deg,#151d2b,#101520);border:1px solid var(--line);border-radius:17px;padding:20px;box-shadow:0 14px 34px #0002}
.card{display:flex;flex-direction:column;min-height:225px;transition:transform .18s,border-color .18s}.card:hover{transform:translateY(-3px);border-color:#6556ae}
.cardtop{display:flex;justify-content:space-between;align-items:center;gap:12px}.symbol{height:42px;width:42px;border-radius:12px;background:#8b72ff20;color:#c6baff;display:grid;place-items:center;font-size:20px}
.category{font-size:10px;font-weight:800;letter-spacing:1px;color:#aebbd0;text-transform:uppercase;background:#ffffff0a;padding:6px 9px;border-radius:999px}
.card h3{font-size:17px;line-height:1.3;margin:17px 0 6px;overflow-wrap:anywhere}.description{font-size:13px;color:var(--muted);white-space:pre-wrap;overflow-wrap:anywhere;flex:1}
.cardbottom{display:flex;justify-content:space-between;align-items:center;gap:12px;margin-top:18px}.added{font-size:11px;color:#75839a}
.btn{border:0;border-radius:10px;background:var(--purple);color:#fff;font-weight:800;padding:11px 15px;cursor:pointer;display:inline-flex;align-items:center;justify-content:center;gap:8px;font-size:12px}.btn:hover{filter:brightness(1.12)}.btn:disabled{opacity:.45;cursor:not-allowed}.btn.secondary{background:#263246;color:#dce5f2}.btn.danger{background:#492532;color:#ffb7c5}
.empty{grid-column:1/-1;text-align:center;padding:42px 22px;border:1px dashed #354056;border-radius:16px;color:var(--muted)}.empty strong{display:block;color:#eef2fa;margin-bottom:5px}
footer{border-top:1px solid #ffffff12;padding:24px 0;color:#728097;font-size:12px}.foot{display:flex;justify-content:space-between;gap:12px;flex-wrap:wrap}
.adminhead{padding:42px 0 18px}.adminhead h1{font-size:36px;letter-spacing:-1px;margin:10px 0}
.panel{margin:15px 0}.panel h2{font-size:18px;margin:0 0 6px}.muted{color:var(--muted);font-size:12px}
label{display:block;color:#b8c2d2;font-size:12px;margin:14px 0 6px}
input,textarea,select{width:100%;background:#0b101a;border:1px solid #344157;border-radius:9px;padding:12px;color:white;outline:none;font:inherit}
textarea{min-height:85px;resize:vertical}.formgrid{display:grid;grid-template-columns:1fr 1fr;gap:12px}.actions{display:flex;gap:8px;flex-wrap:wrap;margin-top:16px}
.rowitem{display:flex;justify-content:space-between;align-items:center;gap:14px;border-top:1px solid var(--line);padding:15px 0}.rowitem:first-child{border-top:0}.rowtitle{font-weight:800;overflow-wrap:anywhere}.rowdesc{font-size:12px;color:var(--muted);overflow-wrap:anywhere}.rowactions{display:flex;gap:7px;flex-shrink:0}.rowactions .btn{padding:8px 10px;font-size:11px}
.notice{background:#352c18;border:1px solid #66552a;color:#f0dca8;border-radius:12px;padding:13px 15px;font-size:13px;margin:12px 0}.success{background:#123125;border-color:#285d47;color:#b8f2d6}
.center{min-height:calc(100vh - 75px);display:grid;place-items:center;padding:36px 0}.login{width:min(420px,100%)}.login h1{font-size:29px;letter-spacing:-.5px;margin:12px 0}
@media(max-width:650px){.hero{padding:53px 0 35px}.catalog-head{align-items:flex-start;flex-direction:column}.formgrid{grid-template-columns:1fr}.rowitem{align-items:flex-start;flex-direction:column}.rowactions{width:100%}.rowactions .btn{flex:1}}
"""

def safe_text(value, limit):
    return str(value or "").strip()[:limit]

def escape(value):
    return html.escape(str(value or ""), quote=True)

def github_api(method, path, payload=None):
    if not GITHUB_TOKEN:
        raise RuntimeError("Falta configurar GITHUB_TOKEN no Render para salvar o catálogo.")
    url = "https://api.github.com" + path
    data = json.dumps(payload).encode("utf-8") if payload is not None else None
    req = urllib.request.Request(url, data=data, method=method)
    req.add_header("Authorization", "Bearer " + GITHUB_TOKEN)
    req.add_header("Accept", "application/vnd.github+json")
    req.add_header("X-GitHub-Api-Version", "2022-11-28")
    req.add_header("Content-Type", "application/json")
    try:
        with urllib.request.urlopen(req, timeout=18) as response:
            raw = response.read()
            return json.loads(raw.decode("utf-8")) if raw else {}
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", "replace")[:500]
        if exc.code == 404:
            return None
        if exc.code in (409, 422):
            raise RuntimeError("O catálogo mudou ao mesmo tempo. Tente novamente.") from exc
        if exc.code == 401:
            raise RuntimeError("GitHub não aceitou o token (401). Ele pode estar incorreto, revogado ou expirado. Confira GITHUB_TOKEN no Render.") from exc
        if exc.code == 403:
            try:
                api_message = json.loads(detail).get("message", "")
            except (ValueError, AttributeError):
                api_message = ""
            extra = (" Detalhe do GitHub: " + api_message) if api_message else ""
            raise RuntimeError("GitHub bloqueou a operação (403). Confira se o token tem acesso ao repositório e permissão Contents: Read and write." + extra) from exc
        raise RuntimeError("Falha ao acessar o GitHub (" + str(exc.code) + ").") from exc
    except (urllib.error.URLError, TimeoutError) as exc:
        raise RuntimeError("Não foi possível conectar ao GitHub agora.") from exc

def repo_file_path():
    encoded = urllib.parse.quote(GITHUB_DATA_PATH, safe="/")
    return "/repos/" + GITHUB_REPOSITORY + "/contents/" + encoded

def read_catalog():
    if not GITHUB_TOKEN:
        return []
    item = github_api("GET", repo_file_path() + "?ref=" + urllib.parse.quote(GITHUB_BRANCH))
    if item is None:
        return []
    try:
        content = base64.b64decode(item.get("content", "")).decode("utf-8")
        data = json.loads(content)
        return data if isinstance(data, list) else []
    except (ValueError, TypeError, UnicodeDecodeError):
        raise RuntimeError("O arquivo links.json no GitHub está inválido.")

def write_catalog(items):
    path = repo_file_path()
    current = github_api("GET", path + "?ref=" + urllib.parse.quote(GITHUB_BRANCH))
    payload = {
        "message": "Atualiza catálogo Cheaters FiveM",
        "content": base64.b64encode(json.dumps(items, ensure_ascii=False, indent=2).encode("utf-8")).decode("ascii"),
        "branch": GITHUB_BRANCH,
    }
    if current is not None:
        payload["sha"] = current["sha"]
    github_api("PUT", path, payload)

def store_uploaded_file(filename, file_bytes):
    safe_path = GITHUB_UPLOADS_PATH + "/" + filename
    encoded_path = urllib.parse.quote(safe_path, safe="/")
    payload = {
        "message": "Adiciona arquivo ao catálogo Cheaters FiveM",
        "content": base64.b64encode(file_bytes).decode("ascii"),
        "branch": GITHUB_BRANCH,
    }
    result = github_api("PUT", "/repos/" + GITHUB_REPOSITORY + "/contents/" + encoded_path, payload)
    raw_url = "https://raw.githubusercontent.com/" + GITHUB_REPOSITORY + "/" + urllib.parse.quote(GITHUB_BRANCH, safe="") + "/" + urllib.parse.quote(safe_path, safe="/")
    return raw_url, result.get("content", {}).get("sha", "")

def mutate_catalog(change):
    last_error = None
    for _ in range(3):
        try:
            items = read_catalog()
            result = change(items)
            write_catalog(items)
            return result
        except RuntimeError as exc:
            last_error = exc
            if "mudou ao mesmo tempo" not in str(exc):
                raise
    raise last_error or RuntimeError("Não foi possível salvar o catálogo.")

def csrf_token():
    if "csrf" not in session:
        session["csrf"] = secrets.token_urlsafe(24)
    return session["csrf"]

def check_csrf():
    supplied = request.headers.get("X-CSRF-Token") or request.form.get("csrf")
    expected = session.get("csrf", "")
    return bool(supplied and expected and hmac.compare_digest(supplied, expected))

def admin_required(fn):
    @wraps(fn)
    def wrapped(*args, **kwargs):
        if session.get("is_admin") is not True:
            return jsonify(error="Entre no painel administrativo novamente."), 401
        return fn(*args, **kwargs)
    return wrapped

def page(title, body, scripts=""):
    return render_template_string(
        """<!doctype html><html lang="pt-br"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><meta name="theme-color" content="#080a10"><meta name="description" content="Central de downloads Cheaters FiveM"><title>{{title}} · Cheaters FiveM</title><style>{{style}}</style></head><body>{{body|safe}}{{scripts|safe}}</body></html>""",
        title=title, style=BASE_STYLE, body=body, scripts=scripts
    )

@app.after_request
def security_headers(response):
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    response.headers["Content-Security-Policy"] = "default-src 'self'; style-src 'self' 'unsafe-inline'; script-src 'self' 'unsafe-inline'; base-uri 'self'; frame-ancestors 'none'"
    response.headers["Cache-Control"] = "no-store" if request.path.startswith("/admin") or request.path.startswith("/api") else "public, max-age=30"
    return response

@app.get("/")
def home():
    error = ""
    try:
        items = read_catalog()
    except RuntimeError:
        items = []
        error = "O catálogo está temporariamente indisponível. Tente novamente mais tarde."
    items = sorted(items, key=lambda x: x.get("created_at", ""), reverse=True)
    cards = []
    for item in items:
        name = escape(item.get("name"))
        description = escape(item.get("description") or "Link disponibilizado pela equipe.")
        category = escape(item.get("category") or "Geral")
        link = escape(item.get("url"))
        created = escape((item.get("created_at") or "")[:10])
        cards.append(
            '<article class="card" data-search="' + escape((item.get("name", "") + " " + item.get("description", "") + " " + item.get("category", "")).lower()) + '">' +
            '<div class="cardtop"><div class="symbol">↗</div><span class="category">' + category + '</span></div>' +
            '<h3>' + name + '</h3><div class="description">' + description + '</div>' +
            '<div class="cardbottom"><span class="added">' + (created or "Disponível") + '</span>' +
            '<a class="btn" href="' + link + '" target="_blank" rel="noopener noreferrer">Acessar download ↗</a></div></article>'
        )
    listing = "".join(cards) or '<div class="empty"><strong>Nenhum download publicado ainda.</strong>Os novos links aparecerão aqui quando forem adicionados no painel.</div>'
    warning = '<div class="notice">' + escape(error) + '</div>' if error else ""
    body = (
        '<header><div class="wrap nav"><a class="brand" href="/">CHEATERS <b>FIVEM</b></a><a class="navlink" href="/admin">Painel administrativo ↗</a></div></header>' +
        '<main class="wrap"><section class="hero"><div class="tag">● Central oficial de downloads</div><h1>SEUS DOWNLOADS.<br><span>SEM COMPLICAÇÃO.</span></h1>' +
        '<p class="lead">Encontre os links e arquivos publicados pela equipe Cheaters FiveM em um só lugar.</p>' +
        '<div class="stats"><div class="stat"><strong>' + str(len(items)) + '</strong> itens publicados</div><div class="stat">Acesso público e gratuito</div></div></section>' +
        warning + '<section><div class="catalog-head"><div><h2>Biblioteca de downloads</h2><p>Escolha um item para abrir o link externo.</p></div></div>' +
        '<div class="tools"><input class="search" id="search" type="search" placeholder="Buscar por nome, descrição ou categoria..." aria-label="Buscar downloads"></div>' +
        '<div class="grid" id="catalog">' + listing + '</div></section></main>' +
        '<footer><div class="wrap foot"><span>© Cheaters FiveM</span><span>Baixe somente arquivos de fontes em que você confia.</span></div></footer>'
    )
    scripts = """<script>
const search=document.getElementById('search');
search.addEventListener('input',()=>{const q=search.value.toLowerCase().trim();document.querySelectorAll('.card').forEach(card=>{card.hidden=!card.dataset.search.includes(q)});});
</script>"""
    return page("Downloads", body, scripts)

@app.get("/admin")
def admin():
    if session.get("is_admin") is not True:
        return redirect(url_for("admin_login"))
    try:
        items = sorted(read_catalog(), key=lambda x: x.get("created_at", ""), reverse=True)
        error = ""
    except RuntimeError as exc:
        items = []
        error = str(exc)
    rows = []
    for item in items:
        rows.append(
            '<div class="rowitem"><div><div class="rowtitle">' + escape(item.get("name")) + '</div>' +
            '<div class="rowdesc">' + escape(item.get("category") or "Arquivo") + ' · ' + escape(item.get("file_name") or "Link externo") + '</div></div>' +
            '<div class="rowactions"><button class="btn danger" onclick="deleteItem(' + json.dumps(item.get("id", "")) + ')">Excluir</button></div></div>'
        )
    items_html = "".join(rows) or '<p class="muted">Ainda não há links cadastrados.</p>'
    warning = '<div class="notice">' + escape(error) + '</div>' if error else ""
    if not GITHUB_TOKEN:
        warning += '<div class="notice">Falta conectar o armazenamento gratuito do catálogo. O painel abre, mas não consegue salvar links até configurar GITHUB_TOKEN nas variáveis do Render.</div>'
    body = (
        '<header><div class="wrap nav"><a class="brand" href="/">CHEATERS <b>FIVEM</b></a><a class="navlink" href="/">Ver site ↗</a></div></header>' +
        '<main class="wrap"><section class="adminhead"><div class="tag">Área protegida</div><h1>Painel administrativo</h1>' +
        '<p class="muted">Envie arquivos para a biblioteca. <a href="/admin/logout">Sair</a></p></section>' +
        warning + '<section class="panel"><h2>Adicionar arquivo</h2><p class="muted">Escolha um arquivo no celular ou computador e toque em adicionar.</p>' +
        '<form id="fileForm"><label for="productName">Nome do produto</label><input id="productName" maxlength="100" required placeholder="Ex.: Pack de veículos">' +
        '<label for="productDescription">Descrição do produto</label><textarea id="productDescription" maxlength="500" placeholder="Descreva o conteúdo do arquivo"></textarea>' +
        '<label for="uploadFile">Selecionar arquivo</label><input id="uploadFile" name="file" type="file" required accept=".zip,.rar,.7z,.dll,.asi,.lua,.ytd,.yft,.ymap,.ymf,.meta,.ini,.cfg,.json,.txt,.png,.jpg,.jpeg">' +
        '<div class="actions"><button class="btn" id="addFileButton" type="submit">Adicionar arquivo</button></div><div class="muted" id="status" role="status"></div></form>' +
        '<p class="muted">Limite: 25 MB por arquivo. Formatos permitidos: ZIP, RAR, 7Z, DLL, ASI e arquivos comuns de recursos FiveM.</p></section>' +
        '<section class="panel"><h2>Arquivos publicados</h2>' + items_html + '</section></main>' +
        '<footer><div class="wrap foot"><span>Cheaters FiveM · Administração</span><span>Não compartilhe sua senha.</span></div></footer>'
    )
    scripts = """<script>
const CSRF=""" + json.dumps(csrf_token()) + """;
const form=document.getElementById('fileForm'),input=document.getElementById('uploadFile'),button=document.getElementById('addFileButton'),status=document.getElementById('status');
form.addEventListener('submit',async e=>{e.preventDefault();if(!input.files.length)return;const data=new FormData();data.append('file',input.files[0]);data.append('name',document.getElementById('productName').value);data.append('description',document.getElementById('productDescription').value);button.disabled=true;status.textContent='Enviando arquivo...';try{const response=await fetch('/api/admin/files',{method:'POST',headers:{'X-CSRF-Token':CSRF},body:data});let result={};try{result=await response.json()}catch{}if(!response.ok)throw new Error(result.error||'Não foi possível enviar o arquivo.');status.textContent='Arquivo adicionado!';location.reload()}catch(err){status.textContent=err.message;button.disabled=false}});
async function deleteItem(id){if(!confirm('Excluir este item da biblioteca?'))return;try{const response=await fetch('/api/admin/links/'+id,{method:'DELETE',headers:{'X-CSRF-Token':CSRF}});let result={};try{result=await response.json()}catch{}if(!response.ok)throw new Error(result.error||'Não foi possível excluir.');location.reload()}catch(err){alert(err.message)}}
</script>"""

    return page("Administração", body, scripts)

LOGIN_HTML = """
<header><div class="wrap nav"><a class="brand" href="/">CHEATERS <b>FIVEM</b></a><a class="navlink" href="/">Voltar ao site</a></div></header>
<main class="wrap center"><section class="panel login"><div class="tag">Acesso restrito</div><h1>Entrar no painel</h1><p class="muted">Digite a senha de administrador.</p>
{% if error %}<div class="notice">{{error}}</div>{% endif %}
<form method="post" action="/admin/login"><input type="hidden" name="csrf" value="{{csrf}}"><label for="password">Senha</label><input id="password" type="password" name="password" autocomplete="current-password" required placeholder="Sua senha"><button class="btn" type="submit" style="width:100%;margin-top:15px">Entrar</button></form>
</section></main>
"""

@app.route("/admin/login", methods=["GET", "POST"])
def admin_login():
    if session.get("is_admin") is True:
        return redirect(url_for("admin"))
    error = ""
    if request.method == "POST":
        if not check_csrf():
            abort(400)
        now = int(time.time())
        if int(session.get("login_lock_until", 0)) > now:
            error = "Muitas tentativas. Aguarde alguns minutos."
        elif not ADMIN_PASSWORD:
            error = "A senha administrativa não está configurada no Render."
        elif hmac.compare_digest(request.form.get("password", ""), ADMIN_PASSWORD):
            session.clear()
            session["is_admin"] = True
            session["csrf"] = secrets.token_urlsafe(24)
            session.permanent = True
            return redirect(url_for("admin"))
        else:
            attempts = int(session.get("login_attempts", 0)) + 1
            session["login_attempts"] = attempts
            if attempts >= 5:
                session["login_lock_until"] = now + 600
                session["login_attempts"] = 0
            error = "Senha incorreta."
    return page("Entrar", render_template_string(LOGIN_HTML, csrf=csrf_token(), error=error))

@app.get("/admin/logout")
def logout():
    session.clear()
    return redirect(url_for("home"))

def validate_link(data):
    name = safe_text(data.get("name"), 100)
    category = safe_text(data.get("category"), 40) or "Geral"
    description = safe_text(data.get("description"), 500)
    url = safe_text(data.get("url"), 2048)
    parsed = urllib.parse.urlparse(url)
    if not name:
        raise ValueError("Informe o nome do download.")
    if parsed.scheme != "https" or not parsed.hostname or parsed.username or parsed.password:
        raise ValueError("Use um link HTTPS válido, começando com https://")
    if any(ord(ch) < 32 for ch in url):
        raise ValueError("O link contém caracteres inválidos.")
    return {"name": name, "category": category, "description": description, "url": url}

@app.post("/api/admin/links")
@admin_required
def create_link():
    if not check_csrf():
        return jsonify(error="Verificação de segurança falhou. Atualize a página."), 400
    try:
        data = validate_link(request.get_json(silent=True) or {})
        entry = {"id": str(uuid.uuid4()), **data, "created_at": datetime.now(timezone.utc).isoformat()}
        mutate_catalog(lambda items: items.insert(0, entry))
        return jsonify(ok=True, item=entry), 201
    except ValueError as exc:
        return jsonify(error=str(exc)), 400
    except RuntimeError as exc:
        return jsonify(error=str(exc)), 503

@app.post("/api/admin/files")
@admin_required
def upload_file():
    if not check_csrf():
        return jsonify(error="Atualize a página e tente novamente."), 400
    uploaded = request.files.get("file")
    if not uploaded or not uploaded.filename:
        return jsonify(error="Selecione um arquivo primeiro."), 400
    from werkzeug.utils import secure_filename
    original_name = secure_filename(uploaded.filename)
    extension = os.path.splitext(original_name)[1].lower()
    allowed = {".zip", ".rar", ".7z", ".dll", ".asi", ".lua", ".ytd", ".yft", ".ymap", ".ymf", ".meta", ".ini", ".cfg", ".json", ".txt", ".png", ".jpg", ".jpeg"}
    if not original_name or extension not in allowed:
        return jsonify(error="Esse tipo de arquivo não está permitido. Escolha um arquivo compatível com FiveM."), 400
    file_bytes = uploaded.read(25 * 1024 * 1024 + 1)
    if not file_bytes:
        return jsonify(error="O arquivo está vazio."), 400
    if len(file_bytes) > 25 * 1024 * 1024:
        return jsonify(error="O arquivo ultrapassa o limite de 25 MB."), 413
    product_name = request.form.get("name", "").strip()[:100]
    product_description = request.form.get("description", "").strip()[:500]
    if not product_name:
        return jsonify(error="Digite o nome do produto."), 400
    stored_name = uuid.uuid4().hex[:12] + "-" + original_name[:100]
    try:
        raw_url, file_sha = store_uploaded_file(stored_name, file_bytes)
        entry = {
            "id": str(uuid.uuid4()),
            "name": product_name,
            "file_name": original_name,
            "category": "Arquivo",
            "description": product_description or "Arquivo disponibilizado pela equipe Cheaters FiveM.",
            "url": raw_url,
            "file_path": GITHUB_UPLOADS_PATH + "/" + stored_name,
            "file_sha": file_sha,
            "created_at": datetime.now(timezone.utc).isoformat(),
        }
        mutate_catalog(lambda items: items.insert(0, entry))
        return jsonify(ok=True, item=entry), 201
    except RuntimeError as exc:
        return jsonify(error=str(exc)), 503

@app.route("/api/admin/links/<link_id>", methods=["PATCH", "DELETE"])
@admin_required
def update_link(link_id):
    if not check_csrf():
        return jsonify(error="Verificação de segurança falhou. Atualize a página."), 400
    try:
        def change(items):
            for index, item in enumerate(items):
                if item.get("id") == link_id:
                    if request.method == "DELETE":
                        removed = items.pop(index)
                        if removed.get("file_path") and removed.get("file_sha"):
                            encoded_path = urllib.parse.quote(removed["file_path"], safe="/")
                            github_api("DELETE", "/repos/" + GITHUB_REPOSITORY + "/contents/" + encoded_path, {
                                "message": "Remove arquivo do catálogo Cheaters FiveM",
                                "sha": removed["file_sha"],
                                "branch": GITHUB_BRANCH,
                            })
                        return True
                    updated = validate_link(request.get_json(silent=True) or {})
                    item.update(updated)
                    return True
            return False
        found = mutate_catalog(change)
        if not found:
            return jsonify(error="Link não encontrado."), 404
        return jsonify(ok=True)
    except ValueError as exc:
        return jsonify(error=str(exc)), 400
    except RuntimeError as exc:
        return jsonify(error=str(exc)), 503

@app.get("/health")
def health():
    return jsonify(status="ok", app="Cheaters FiveM", storage="github" if GITHUB_TOKEN else "not_configured")

@app.errorhandler(413)
def too_large(_):
    return jsonify(error="O envio ultrapassa o limite permitido de 15 MB."), 413

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", "10000")))
