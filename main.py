from fastapi import FastAPI, Form, Request, Response
from fastapi.responses import HTMLResponse, RedirectResponse, FileResponse
from sqlalchemy import create_engine, text
from starlette.middleware.sessions import SessionMiddleware
from datetime import datetime, date
import json

app = FastAPI()
app.add_middleware(SessionMiddleware, secret_key="brahma_riacho_mall_2024")

DATABASE_URL = "postgresql://postgres:GNlZnHiuKAcFnpgXhwILfigqKCNkaHqx@interchange.proxy.rlwy.net:44559/railway"
engine = create_engine(DATABASE_URL, pool_pre_ping=True)

MENU_INICIAL = {
    "CHOPP": [("Caneca 350ml", 11.9), ("Descartável 500ml", 13.9), ("Tulipa 700ml", 17.9), ("Torre 2.5L", 84.9), ("Torre 3.5L", 99.9)],
    "CERVEJAS": [("Original 600ml", 12.9), ("Amstel 600ml", 12.0), ("Brahma Duplo Malte", 12.0), ("Heineken 600ml", 16.9), ("Spaten LN", 8.9), ("Corona LN", 10.0), ("Heineken LN", 10.0), ("Stella LN", 8.9), ("Heineken Zero", 10.0)],
    "PETISCOS": [("Fritas", 21.9), ("Fritas c/ Queijo", 25.9), ("Fritas Cheddar/Bacon", 27.9), ("Kibe 10un", 34.9), ("Kibe c/ Queijo", 37.9), ("Frango Passarinho", 28.9), ("Carne Sol c/ Fritas", 54.9), ("Calabresa Acebolada", 22.9), ("Tábua Frios", 34.9)],
    "BEBIDAS": [("Caipirinha", 14.9), ("Caipiroska Absolut", 16.9), ("Gin Tônica", 24.9), ("Gin Tropical", 26.9), ("Cozumel 600ml", 14.9), ("Refri Lata", 4.9), ("Soda Italiana", 13.9), ("Suco Lata", 5.9), ("Red Bull", 13.0), ("Água", 3.9)]
}

# --- CRIAÇÃO DAS TABELAS BÁSICAS + USUÁRIOS ---
with engine.begin() as conn:
    conn.execute(text("""
        CREATE TABLE IF NOT EXISTS clientes (id SERIAL PRIMARY KEY, nome_completo TEXT NOT NULL, cpf TEXT UNIQUE NOT NULL, data_nascimento DATE, contato TEXT, email TEXT);
        CREATE TABLE IF NOT EXISTS pulseiras (id SERIAL PRIMARY KEY, numero_pulseira TEXT NOT NULL, cliente_cpf TEXT REFERENCES clientes(cpf), total_conta DECIMAL(10,2) DEFAULT 7.00);
        CREATE TABLE IF NOT EXISTS vendas_itens (id SERIAL PRIMARY KEY, pulseira_num TEXT, item_nome TEXT, valor DECIMAL(10,2), data_venda DATE DEFAULT CURRENT_DATE, hora_venda TIME DEFAULT CURRENT_TIME);
        CREATE TABLE IF NOT EXISTS produtos (id SERIAL PRIMARY KEY, nome TEXT UNIQUE NOT NULL);
        CREATE TABLE IF NOT EXISTS fila_impressao (id SERIAL PRIMARY KEY, conteudo TEXT, status TEXT DEFAULT 'PENDENTE', data_criacao TIMESTAMP DEFAULT CURRENT_TIMESTAMP);
        CREATE TABLE IF NOT EXISTS historico_estoque (id SERIAL PRIMARY KEY, produto_nome TEXT, qtd_adicionada INT, data_entrada DATE DEFAULT CURRENT_DATE);
        CREATE TABLE IF NOT EXISTS usuarios (id SERIAL PRIMARY KEY, username TEXT UNIQUE NOT NULL, password TEXT NOT NULL, role TEXT NOT NULL);
    """))

MIGRACOES = [
    "ALTER TABLE pulseiras ADD COLUMN IF NOT EXISTS status TEXT DEFAULT 'ABERTA';",
    "ALTER TABLE vendas_itens ADD COLUMN IF NOT EXISTS status TEXT DEFAULT 'ABERTA';",
    "ALTER TABLE pulseiras DROP CONSTRAINT IF EXISTS pulseiras_numero_pulseira_key;",
    "ALTER TABLE produtos ADD COLUMN IF NOT EXISTS categoria TEXT DEFAULT 'OUTROS';",
    "ALTER TABLE produtos ADD COLUMN IF NOT EXISTS preco DECIMAL(10,2) DEFAULT 0.00;",
    "ALTER TABLE produtos ADD COLUMN IF NOT EXISTS estoque INT DEFAULT 0;",
    "ALTER TABLE vendas_itens ADD COLUMN IF NOT EXISTS garcom TEXT;",
    "ALTER TABLE pulseiras ADD COLUMN IF NOT EXISTS forma_pagamento TEXT;",
    "ALTER TABLE pulseiras ADD COLUMN IF NOT EXISTS data_fechamento TIMESTAMP;"
]
for mig in MIGRACOES:
    try:
        with engine.begin() as conn: conn.execute(text(mig))
    except Exception: pass

# POPULANDO BANCO INICIAL (PRODUTOS + USUÁRIO ADMIN PADRÃO)
try:
    with engine.begin() as conn:
        for cat, itens in MENU_INICIAL.items():
            for n, p in itens:
                conn.execute(text("INSERT INTO produtos (nome, categoria, preco, estoque) VALUES (:n, :c, :p, 100) ON CONFLICT (nome) DO NOTHING"), {"n": n, "c": cat, "p": p})
        conn.execute(text("INSERT INTO usuarios (username, password, role) VALUES ('admin', '1234', 'admin') ON CONFLICT (username) DO NOTHING"))
except Exception: pass

def formata_linha(esq, dir, width=32):
    dir_str = str(dir)
    esq_str = str(esq)[:width - len(dir_str) - 1]
    return esq_str + " " * (width - len(esq_str) - len(dir_str)) + dir_str

# --- CSS E DESIGN ---
CSS = """
<meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no">
<meta name="apple-mobile-web-app-capable" content="yes">
<meta name="apple-mobile-web-app-status-bar-style" content="black-translucent">
<meta name="apple-mobile-web-app-title" content="Brahma">
<link rel="apple-touch-icon" href="https://upload.wikimedia.org/wikipedia/commons/thumb/1/18/Brahma_Logo.svg/512px-Brahma_Logo.svg.png">
<style>
    * { box-sizing: border-box; font-family: 'Segoe UI', Tahoma, sans-serif; }
    body { margin: 0; background: #0a3a7a; color: white; height: 100vh; display: flex; flex-direction: column; overflow: hidden; }
    .layout-vendas { display: flex; flex: 1; height: 100vh; }
    .menu-lateral { width: 220px; padding: 20px; display: flex; flex-direction: column; gap: 10px; border-right: 1px solid rgba(255,255,255,0.1); background: #082d5e; overflow-y:auto; }
    .btn-menu { background: #0a3a7a; color: white; border: 1px solid #1352a3; padding: 15px; border-radius: 8px; text-align: left; font-weight: bold; font-size: 15px; cursor: pointer; text-decoration: none; display: flex; justify-content: space-between; }
    .btn-menu:hover, .btn-menu.ativo { background: #d31a21; border-color: white; }
    .main-area { flex: 1; padding: 20px; display: flex; flex-direction: column; overflow-y: auto; align-items: center; }
    .logo-central { width: 140px; margin-bottom: 20px; filter: drop-shadow(0px 4px 6px rgba(0,0,0,0.5)); }
    .logo-peq { width: 100px; margin-bottom: 10px; }
    .logo-css { background: #d31a21; color: white; border-radius: 50%; display: flex; flex-direction: column; align-items: center; justify-content: center; border: 4px solid white; box-shadow: 0 6px 12px rgba(0,0,0,0.5); font-weight: 900; line-height: 1.1; text-transform: uppercase; font-family: 'Arial Black', sans-serif; }
    .grid-produtos { display: grid; grid-template-columns: repeat(auto-fill, minmax(160px, 1fr)); gap: 15px; width: 100%; max-width: 900px; }
    .prod-card { border-radius: 10px; padding: 15px 10px; text-align: center; cursor: pointer; display: flex; flex-direction: column; justify-content: space-between; min-height: 120px; box-shadow: 0 4px 6px rgba(0,0,0,0.3); transition: 0.2s; color: white; border-width: 2px; border-style: solid; }
    .prod-card:hover { transform: scale(1.05); border-color: white; }
    .bg-green { background: linear-gradient(180deg, #28a745 0%, #1e7e34 100%); border-color: #145523; }
    .bg-red { background: linear-gradient(180deg, #d31a21 0%, #9e0b10 100%); border-color: #5a0407; opacity: 0.8; }
    .prod-card b { font-size: 14px; margin-bottom: 8px; text-shadow: 1px 1px 2px rgba(0,0,0,0.6); }
    .prod-card span { font-size: 16px; font-weight: bold; background: rgba(0,0,0,0.3); padding: 5px; border-radius: 5px; }
    .badge-estoque { font-size: 12px; margin-top: 8px; background: rgba(0,0,0,0.4); border-radius: 4px; padding: 3px; font-weight: bold; }
    .comanda-lateral { width: 340px; background: white; color: black; border-left: 5px solid #d31a21; display: flex; flex-direction: column; }
    .comanda-header { background: #d31a21; color: white; padding: 15px; font-weight: bold; text-align: center; font-size: 18px; }
    .comanda-body { flex: 1; overflow-y: auto; padding: 15px; background: #f9f9f9; }
    .secao-titulo { font-size: 12px; color: #666; text-transform: uppercase; font-weight: bold; border-bottom: 1px solid #ccc; margin-bottom: 10px; padding-bottom: 5px; }
    .item-linha { display: flex; justify-content: space-between; font-size: 14px; margin-bottom: 8px; border-bottom: 1px dashed #ddd; padding-bottom: 5px; }
    .comanda-footer { padding: 15px; background: white; border-top: 1px solid #ccc; }
    .btn-acao { display: block; width: 100%; padding: 15px; margin-bottom: 8px; border: none; border-radius: 5px; font-weight: bold; color: white; cursor: pointer; text-align: center; text-decoration: none; font-size: 14px; background: #062b5e; }
    .btn-acao:hover { background: #0d4b9c; }
    .container-center { display: flex; align-items: center; justify-content: center; height: 100vh; padding: 20px; overflow-y: auto; }
    .card-center { background: white; color: #333; padding: 30px; border-radius: 15px; width: 100%; max-width: 650px; text-align: center; box-shadow: 0 8px 20px rgba(0,0,0,0.4); margin: auto; }
    .input-padrao { width: 100%; padding: 12px; margin: 8px 0; border: 1px solid #ccc; border-radius: 5px; font-size: 16px; }
    table { width: 100%; border-collapse: collapse; margin-top: 15px; }
    th, td { padding: 8px; border-bottom: 1px solid #eee; text-align: left; vertical-align: middle; }
    @media (max-width: 768px) {
        body { height: auto; overflow: auto; }
        .layout-vendas { display: flex; flex-direction: column; height: auto; min-height: 100vh; }
        .menu-lateral { width: 100%; flex-direction: row; overflow-x: auto; padding: 10px; border-right: none; border-bottom: 2px solid rgba(255,255,255,0.1); display: flex; gap: 8px; flex-shrink: 0; white-space: nowrap; -webkit-overflow-scrolling: touch; }
        .btn-menu { padding: 10px 15px; font-size: 14px; text-align: center; flex: 0 0 auto; justify-content: center; }
        .main-area { display: flex; overflow: visible; padding: 15px; flex-shrink: 0; }
        .grid-produtos { grid-template-columns: repeat(auto-fill, minmax(130px, 1fr)); gap: 10px; }
        .prod-card { min-height: 110px; padding: 10px; }
        .prod-card b { font-size: 13px; }
        .prod-card span { font-size: 14px; }
        .comanda-lateral { width: 100%; display: flex; border-left: none; border-top: 5px solid #d31a21; flex-shrink: 0; }
        .card-center { width: 95%; padding: 20px; }
    }
</style>
"""

IMG_LOGO = """<div style='display:flex; justify-content:center; margin-bottom:20px;'><img src='https://upload.wikimedia.org/wikipedia/commons/thumb/1/18/Brahma_Logo.svg/512px-Brahma_Logo.svg.png' class='logo-central' style='margin:0;' onerror='this.style.display="none"; document.getElementById("fb-logo").style.display="flex";'><div id='fb-logo' class='logo-css' style='display:none; width:130px; height:130px;'><span style='font-size:18px; font-style:italic;'>CHOPP</span><span style='font-size:26px;'>BRAHMA</span></div></div>"""
IMG_LOGO_PEQ = """<div style='display:flex; justify-content:center; margin-bottom:15px;'><img src='https://upload.wikimedia.org/wikipedia/commons/thumb/1/18/Brahma_Logo.svg/512px-Brahma_Logo.svg.png' class='logo-peq' style='margin:0;' onerror='this.style.display="none"; document.getElementById("fb-logo-peq").style.display="flex";'><div id='fb-logo-peq' class='logo-css' style='display:none; width:90px; height:90px;'><span style='font-size:12px; font-style:italic;'>CHOPP</span><span style='font-size:16px;'>BRAHMA</span></div></div>"""

@app.get("/sw.js")
async def get_sw(): return Response(content="self.addEventListener('install', e => { self.skipWaiting(); }); self.addEventListener('activate', e => { e.waitUntil(clients.claim()); }); self.addEventListener('fetch', e => {});", media_type="application/javascript")

@app.get("/manifest.json")
async def get_manifest(): return {"name": "Quiosque Brahma", "short_name": "BrahmaApp", "start_url": "/", "display": "standalone", "background_color": "#0a3a7a", "theme_color": "#d31a21", "icons": [{"src": "https://upload.wikimedia.org/wikipedia/commons/thumb/1/18/Brahma_Logo.svg/512px-Brahma_Logo.svg.png", "sizes": "512x512", "type": "image/png", "purpose": "any maskable"}]}

@app.get("/", response_class=HTMLResponse)
async def login_page(): return f"""<html><head>{CSS}<link rel="manifest" href="/manifest.json"></head><body><div class='container-center'><div class='card-center'>{IMG_LOGO}<h2>Acesso ao Sistema</h2><form action='/login' method='post'><input class='input-padrao' name='user' placeholder='Usuário' required><input class='input-padrao' name='pw' type='password' placeholder='Senha' required><button class='btn-acao' style='padding:15px; font-size:18px;'>ENTRAR</button></form></div></div></body></html>"""

@app.post("/login")
async def login(request: Request):
    f = await request.form()
    
    # 🚀 A CORREÇÃO TÁ AQUI: Forçando a leitura em minúsculo e tirando espaços!
    u = f.get("user", "").strip().lower() 
    p = f.get("pw", "")
    
    with engine.connect() as conn:
        user = conn.execute(text("SELECT username, role FROM usuarios WHERE username = :u AND password = :p"), {"u": u, "p": p}).fetchone()
        if user:
            request.session["user"] = user.username
            request.session["role"] = user.role
            return RedirectResponse(url="/central", status_code=303)
            
    return HTMLResponse("<script>alert('Usuário ou Senha incorretos!'); window.location.href='/';</script>")

@app.get("/central", response_class=HTMLResponse)
async def central(request: Request):
    user = request.session.get("user")
    role = request.session.get("role")
    if not user: return RedirectResponse(url="/")
    
    botoes = ""
    # Portaria, Garçom, Caixa, Gerente, Admin tem acesso:
    if role in ["admin", "gerente", "garcom", "caixa", "portaria"]:
        botoes += f"<a href='/cadastro' class='btn-acao' style='background:#d31a21'>➕ NOVO CLIENTE</a><a href='/buscar' class='btn-acao'>🔍 BUSCAR / ABRIR NOVA PULSEIRA</a>"
    # Apenas Garçom, Caixa, Gerente, Admin tem acesso a vendas e fechamento:
    if role in ["admin", "gerente", "garcom", "caixa"]:
        botoes += f"<a href='/vendas' class='btn-acao' style='background:#28a745'>🛒 CAIXA / LANÇAR ITENS</a><a href='/fechar_conta' class='btn-acao' style='background:#333'>🔒 FECHAR CONTA</a>"
    # Apenas Gerente e Admin tem acesso a relatórios:
    if role in ["admin", "gerente"]:
        botoes += "<a href='/dashboard' class='btn-acao' style='background:#17a2b8'>📊 DEMONSTRATIVO GESTÃO</a><a href='/estoque' class='btn-acao' style='background:#e67e22'>📦 GESTÃO DE ESTOQUE</a><a href='#' class='btn-acao' style='background:#062b5e' onclick='abrirPopup()'>⚙️ CONECTAR IMPRESSORA</a>"
    # Apenas ADMIN tem acesso à criação de usuários:
    if role == "admin":
        botoes += "<a href='/usuarios' class='btn-acao' style='background:#9b59b6'>👥 GERENCIAR USUÁRIOS</a>"
        
    popup = """<div id="popup" style="display:none; position:fixed; top:0; left:0; width:100%; height:100%; background:rgba(0,0,0,0.8); z-index:999; align-items:center; justify-content:center; flex-direction:column; padding:20px;"><div style="background:white; color:black; padding:30px; border-radius:15px; max-width:400px; text-align:center; border-top: 8px solid #d31a21;"><h2 style="margin-top:0; color:#d31a21;">🖨️ Impressora</h2><p style="margin-bottom:20px;">Baixe nosso integrador para pedidos automáticos.</p><a href="/download_conector" class="btn-acao" style="background:#28a745; margin-bottom:15px;">⬇️ BAIXAR CONECTOR</a><button onclick="document.getElementById('popup').style.display='none'" style="background:transparent; border:none; color:#666; cursor:pointer; text-decoration:underline;">Fazer depois</button></div></div><script>function abrirPopup() { document.getElementById('popup').style.display = 'flex'; }</script>"""
    return f"<html><head>{CSS}</head><body>{popup if role in ['admin', 'gerente'] else ''}<div class='container-center'><div class='card-center'>{IMG_LOGO_PEQ}<p style='margin-top:0;'>Logado como: <b>{user.upper()}</b></p>{botoes}<br><a href='/logout' style='color:gray'>Sair do Sistema</a></div></div></body></html>"
@app.get("/usuarios", response_class=HTMLResponse)
async def tela_usuarios(request: Request):
    if request.session.get("role") != "admin": return RedirectResponse(url="/central")
    linhas = ""
    with engine.connect() as conn:
        users_db = conn.execute(text("SELECT id, username, role FROM usuarios ORDER BY role, username")).fetchall()
        for r in users_db:
            acoes = f"<form action='/excluir_usuario' method='post' style='margin:0;' onsubmit='return confirm(\"Excluir {r.username}?\");'><input type='hidden' name='id' value='{r.id}'><button class='btn-acao' style='background:#d31a21; margin:0; padding:8px; width:auto;'>🗑️</button></form>" if r.username != "admin" else ""
            linhas += f"<tr><td style='color:black; font-weight:bold;'>{r.username.upper()}</td><td style='color:#062b5e;'>{r.role.upper()}</td><td>{acoes}</td></tr>"
            
    add_form = f"""<div style='background:#f4f4f4; padding:20px; border-radius:10px; margin-bottom:20px; text-align:left; border:1px solid #ccc;'><h3 style='margin-top:0; color:#9b59b6;'>➕ NOVO USUÁRIO</h3><form action='/novo_usuario' method='post' style='display:flex; flex-wrap:wrap; gap:10px;'><input name='u' placeholder='Nome de Usuário (Login)' class='input-padrao' style='flex:1; min-width:180px;' required><input name='p' type='password' placeholder='Senha' class='input-padrao' style='flex:1; min-width:120px;' required><select name='r' class='input-padrao' style='flex:1; min-width:130px;' required><option value='gerente'>GERENTE (Acesso Total)</option><option value='caixa'>CAIXA (Vendas + Fechamento)</option><option value='garcom'>GARÇOM (Vendas + Fechamento)</option><option value='portaria'>PORTARIA (Apenas Cadastros)</option></select><button class='btn-acao' style='background:#9b59b6; margin:0; width:100%;'>CRIAR ACESSO</button></form></div>"""
    return f"""<html><head>{CSS}</head><body><div class='container-center'><div class='card-center'><h2>Gestão de Usuários</h2>{add_form}<div style='max-height:400px; overflow-y:auto; border:1px solid #ddd;'><table><tr><th style='color:black'>Login</th><th style='color:black'>Cargo</th><th style='color:black'>Ação</th></tr>{linhas}</table></div><br><a href='/central' style='color:gray'>Voltar</a></div></div></body></html>"""

@app.post("/novo_usuario")
async def novo_usuario(request: Request):
    if request.session.get("role") != "admin": return RedirectResponse(url="/central")
    f = await request.form()
    u, p, r = f.get("u", "").strip().lower(), f.get("p", ""), f.get("r", "garcom")
    try:
        with engine.begin() as conn: conn.execute(text("INSERT INTO usuarios (username, password, role) VALUES (:u, :p, :r) ON CONFLICT (username) DO NOTHING"), {"u": u, "p": p, "r": r})
    except: pass
    return RedirectResponse(url="/usuarios", status_code=303)

@app.post("/excluir_usuario")
async def excluir_usuario(request: Request):
    if request.session.get("role") != "admin": return RedirectResponse(url="/central")
    f = await request.form()
    try:
        with engine.begin() as conn: conn.execute(text("DELETE FROM usuarios WHERE id = :id AND username != 'admin'"), {"id": f.get("id")})
    except: pass
    return RedirectResponse(url="/usuarios", status_code=303)

# AS ROTAS ABAIXO FORAM PROTEGIDAS PELO NOVO SISTEMA DE HIERARQUIA
@app.get("/estoque", response_class=HTMLResponse)
async def tela_estoque(request: Request):
    if request.session.get("role") not in ["admin", "gerente"]: return RedirectResponse(url="/central")
    linhas, curr_cat = "", ""
    with engine.connect() as conn:
        prods_db = conn.execute(text("SELECT p.id, p.nome, p.categoria, p.preco, p.estoque, MAX(h.data_entrada) as ultima_compra FROM produtos p LEFT JOIN historico_estoque h ON p.nome = h.produto_nome GROUP BY p.id, p.nome, p.categoria, p.preco, p.estoque ORDER BY p.categoria, p.nome")).fetchall()
        for r in prods_db:
            cat_val, p_val, e_val = r.categoria or "OUTROS", float(r.preco or 0), int(r.estoque or 0)
            data_compra = r.ultima_compra.strftime("%d/%m/%Y") if r.ultima_compra else "Sem Registro"
            cod_formatado = f"{r.id:03d}"
            if cat_val != curr_cat:
                linhas += f"<tr><td colspan='5' style='background:#082d5e; color:white; font-weight:bold; text-align:center;'>{cat_val}</td></tr>"
                curr_cat = cat_val
            acoes = f"""<div style='display:flex; gap:5px; align-items:center;'><form action='/att_estoque' method='post' style='margin:0; display:flex; gap:5px;'><input type='hidden' name='i' value='{r.nome}'><input type='number' name='q' class='input-padrao' style='width:50px; margin:0; padding:5px;' required><button class='btn-acao' style='background:#28a745; margin:0; padding:8px; width:auto;'>➕</button></form><button class='btn-acao' style='background:#ffc107; color:black; margin:0; padding:8px; width:auto;' onclick='editarProd("{r.nome}", "{p_val:.2f}")'>✏️</button><form action='/excluir_produto' method='post' style='margin:0;' onsubmit='return confirm("Excluir {r.nome}?");'><input type='hidden' name='nome' value='{r.nome}'><button class='btn-acao' style='background:#d31a21; margin:0; padding:8px; width:auto;'>🗑️</button></form></div>"""
            linhas += f"<tr><td style='color:#d31a21; font-weight:bold;'>{cod_formatado}</td><td style='color:black; line-height:1.2;'>{r.nome} <br><small style='color:#666;'>R$ {p_val:.2f}</small></td><td style='color:#062b5e; font-size:12px;'>{data_compra}</td><td style='color:black; font-weight:bold; font-size:18px;'>{e_val}</td><td>{acoes}</td></tr>"
            
    add_form = f"""<div style='background:#f4f4f4; padding:20px; border-radius:10px; margin-bottom:20px; text-align:left; border:1px solid #ccc;'><h3 style='margin-top:0; color:#d31a21;'>➕ CADASTRAR NOVO PRODUTO</h3><form action='/novo_produto' method='post' style='display:flex; flex-wrap:wrap; gap:10px;'><input name='nome' placeholder='Nome do Produto' class='input-padrao' style='flex:1; min-width:180px;' required><select name='cat' class='input-padrao' style='flex:1; min-width:130px;' required><option value='CHOPP'>CHOPP</option><option value='CERVEJAS'>CERVEJAS</option><option value='PETISCOS'>PETISCOS</option><option value='BEBIDAS'>BEBIDAS</option><option value='OUTROS'>OUTROS</option></select><input name='preco' type='text' placeholder='Preço' class='input-padrao' style='flex:1; min-width:100px;' required><input name='qtd' type='number' placeholder='Qtd' class='input-padrao' style='flex:1; min-width:120px;' required><button class='btn-acao' style='background:#062b5e; margin:0; width:100%;'>SALVAR PRODUTO</button></form></div>"""
    return f"""<html><head>{CSS}<script>function editarProd(n_a, p_a) {{ let n_n = prompt("Novo Nome:", n_a); if(!n_n) return; let p = prompt("Novo Preço:", p_a); if(!p) return; let f = document.createElement("form"); f.method="POST"; f.action="/editar_produto"; let i1 = document.createElement("input"); i1.name="nome_antigo"; i1.value=n_a; f.appendChild(i1); let i2 = document.createElement("input"); i2.name="nome_novo"; i2.value=n_n; f.appendChild(i2); let i3 = document.createElement("input"); i3.name="preco"; i3.value=p; f.appendChild(i3); document.body.appendChild(f); f.submit(); }}</script></head><body><div class='container-center'><div class='card-center'><h2>Gestão de Estoque</h2>{add_form}<div style='max-height:400px; overflow-y:auto; border:1px solid #ddd;'><table><tr><th style='color:black'>Cód</th><th style='color:black'>Item</th><th style='color:black'>Últ. Compra</th><th style='color:black'>Qtd</th><th style='color:black'>Ação</th></tr>{linhas}</table></div><br><a href='/central' style='color:gray'>Voltar</a></div></div></body></html>"""

@app.post("/novo_produto")
async def novo_produto(request: Request):
    if request.session.get("role") not in ["admin", "gerente"]: return RedirectResponse(url="/central")
    f = await request.form()
    n, c, p, q = f.get("nome", "").strip(), f.get("cat", "OUTROS"), f.get("preco", "0").replace(",", "."), f.get("qtd", "0")
    if n:
        try:
            with engine.begin() as conn: 
                conn.execute(text("INSERT INTO produtos (nome, categoria, preco, estoque) VALUES (:n, :c, :p, :q) ON CONFLICT (nome) DO NOTHING"), {"n": n, "c": c, "p": float(p), "q": int(q)})
                conn.execute(text("INSERT INTO historico_estoque (produto_nome, qtd_adicionada) VALUES (:n, :q)"), {"n": n, "q": int(q)})
        except: pass
    return RedirectResponse(url="/estoque", status_code=303)

@app.post("/att_estoque")
async def att_estoque(request: Request):
    if request.session.get("role") not in ["admin", "gerente"]: return RedirectResponse(url="/central")
    f = await request.form()
    i, q = f.get("i", ""), int(f.get("q", "0"))
    try:
        with engine.begin() as conn: 
            conn.execute(text("UPDATE produtos SET estoque = COALESCE(estoque, 0) + :q WHERE nome = :i"), {"i": i, "q": q})
            conn.execute(text("INSERT INTO historico_estoque (produto_nome, qtd_adicionada) VALUES (:i, :q)"), {"i": i, "q": q})
    except: pass
    return RedirectResponse(url="/estoque", status_code=303)

@app.post("/editar_produto")
async def editar_produto(request: Request):
    if request.session.get("role") not in ["admin", "gerente"]: return RedirectResponse(url="/central")
    f = await request.form()
    na, nn, p = f.get("nome_antigo", ""), f.get("nome_novo", "").strip(), f.get("preco", "0").replace(",", ".")
    if na and nn:
        try:
            with engine.begin() as conn: 
                conn.execute(text("UPDATE produtos SET nome = :nn, preco = :p WHERE nome = :na"), {"nn": nn, "p": float(p), "na": na})
                conn.execute(text("UPDATE historico_estoque SET produto_nome = :nn WHERE produto_nome = :na"), {"nn": nn, "na": na})
        except: pass
    return RedirectResponse(url="/estoque", status_code=303)

@app.post("/excluir_produto")
async def excluir_produto(request: Request):
    if request.session.get("role") not in ["admin", "gerente"]: return RedirectResponse(url="/central")
    f = await request.form()
    try:
        with engine.begin() as conn: conn.execute(text("DELETE FROM produtos WHERE nome = :n"), {"n": f.get("nome", "")})
    except: pass
    return RedirectResponse(url="/estoque", status_code=303)

@app.get("/vendas", response_class=HTMLResponse)
async def vendas(request: Request, cat: str = "CHOPP", p: str = ""):
    if request.session.get("role") not in ["admin", "gerente", "garcom", "caixa"]: return RedirectResponse(url="/central")
    if p:
        with engine.connect() as conn:
            if not conn.execute(text("SELECT id FROM pulseiras WHERE numero_pulseira = :p AND status = 'ABERTA'"), {"p": p}).fetchone(): return HTMLResponse(f"<script>alert('A comanda {p} não está ativa ou não existe!'); window.location.href='/vendas?cat={cat}';</script>")
    prods, itens_html = "", ""
    with engine.connect() as conn:
        for n, v, e in conn.execute(text("SELECT nome, preco, estoque FROM produtos WHERE categoria = :c ORDER BY nome"), {"c": cat}).fetchall():
            v_val, e_val = float(v or 0), int(e or 0)
            cor = 'bg-green' if e_val > 0 else 'bg-red'
            prods += f"<div class='prod-card {cor}' onclick='add(\"{n}\", {v_val}, {e_val})'><b>{n}</b><span>R$ {v_val:.2f}</span><div class='badge-estoque'>Estoque: {e_val}</div></div>"
    if p:
        with engine.connect() as conn:
            for r in conn.execute(text("SELECT item_nome, COUNT(*) as qtd, SUM(valor) as tot FROM vendas_itens WHERE pulseira_num = :p AND status = 'ABERTA' GROUP BY item_nome"), {"p": p}).fetchall():
                itens_html += f"<div class='item-linha'><span>{r.qtd}x {r.item_nome}</span><span>R$ {float(r.tot or 0):.2f}</span></div>"
    comanda_display = f"""<div class='comanda-header' style='padding-bottom:15px;'><div style='font-size:13px; margin-bottom:8px; color:#ffdddd;'>NÚMERO DA PULSEIRA:</div><input type='number' id='input-pulseira' class='input-padrao' style='margin:0; font-weight:bold; text-align:center; color:black; padding:10px; font-size:20px;' value='{p}' placeholder='Ex: 15'><button class='btn-acao' style='background:white; color:#d31a21; margin-top:10px; padding:10px; font-size:15px;' onclick='acessarComanda()'>ACESSAR COMANDA</button></div><div class='comanda-body'><div class='secao-titulo'>Histórico de Consumo</div>{itens_html if p else "<div style='color:#999; text-align:center'>Nenhuma pulseira acessada</div>"}<br><div class='secao-titulo' style='color:#d31a21'>Novo Pedido</div><div id='novo-pedido'></div></div><div class='comanda-footer'><div style='display:flex; justify-content:space-between; font-size:18px; font-weight:bold; margin-bottom:10px;'><span>Subtotal Pedido:</span><span id='tot-pedido'>R$ 0.00</span></div><button class='btn-acao' style='background:#28a745; font-size:16px;' onclick='enviarPedido()'>🖨️ FINALIZAR PEDIDO</button><a href='/central' class='btn-acao' style='background:#333'>Voltar</a></div>"""
    return f"""<html><head>{CSS}<script>const p_num = new URLSearchParams(window.location.search).get('p') || ''; let cart = JSON.parse(sessionStorage.getItem('cart_' + p_num)) || []; function add(n, v, e) {{ if(!p_num) return alert('Acesse uma pulseira no campo acima primeiro!'); if (e <= 0 || cart.filter(x => x.n === n).length >= e) return alert('❌ Produto esgotado ou sem estoque!'); cart.push({{n, v}}); sessionStorage.setItem('cart_' + p_num, JSON.stringify(cart)); render(); }} function render() {{ let html = ''; let t = 0; if(!p_num) return; cart.forEach((i, idx) => {{ html += `<div class='item-linha' style='color:#d31a21; font-weight:bold;'><span>${{i.n}}</span><span>R$ ${{i.v.toFixed(2)}} <b onclick='rem(${{idx}})' style='cursor:pointer; color:black; font-size:16px; margin-left:8px; padding: 5px;'>X</b></span></div>`; t += i.v; }}); document.getElementById('novo-pedido').innerHTML = html; document.getElementById('tot-pedido').innerText = 'R$ ' + t.toFixed(2); }} function rem(idx) {{ cart.splice(idx, 1); sessionStorage.setItem('cart_' + p_num, JSON.stringify(cart)); render(); }} function enviarPedido() {{ if(!p_num || cart.length === 0) return alert('Adicione itens ao pedido antes de finalizar!'); let f = document.createElement('form'); f.method = 'POST'; f.action = '/lancar_pedido'; let i1 = document.createElement('input'); i1.name = 'p'; i1.value = p_num; f.appendChild(i1); let i2 = document.createElement('input'); i2.name = 'itens'; i2.value = JSON.stringify(cart); f.appendChild(i2); document.body.appendChild(f); sessionStorage.removeItem('cart_' + p_num); f.submit(); }} function acessarComanda() {{ let val = document.getElementById('input-pulseira').value; if(!val) return alert('Digite o número da pulseira!'); window.location.href=`/vendas?cat={cat}&p=${{val}}`; }} window.onload = render;</script></head><body><div class='layout-vendas'><div class='menu-lateral'><a href='/vendas?cat=CHOPP&p={p}' class='btn-menu {"ativo" if cat=="CHOPP" else ""}'>🍺 CHOPP</a><a href='/vendas?cat=CERVEJAS&p={p}' class='btn-menu {"ativo" if cat=="CERVEJAS" else ""}'>🍾 CERVEJAS</a><a href='/vendas?cat=PETISCOS&p={p}' class='btn-menu {"ativo" if cat=="PETISCOS" else ""}'>🍟 PETISCOS</a><a href='/vendas?cat=BEBIDAS&p={p}' class='btn-menu {"ativo" if cat=="BEBIDAS" else ""}'>🍹 BEBIDAS</a><a href='/vendas?cat=OUTROS&p={p}' class='btn-menu {"ativo" if cat=="OUTROS" else ""}'>📦 OUTROS</a></div><div class='main-area'>{IMG_LOGO}<h2 style='margin-bottom:20px; font-size:24px;'>CARDÁPIO - {cat}</h2><div class='grid-produtos'>{prods}</div></div><div class='comanda-lateral'>{comanda_display}</div></div></body></html>"""

@app.post("/lancar_pedido")
async def lancar_pedido(request: Request):
    if request.session.get("role") not in ["admin", "gerente", "garcom", "caixa"]: return RedirectResponse(url="/central")
    form = await request.form()
    p, itens, usuario = form.get("p", ""), form.get("itens", ""), request.session.get("user", "Desconhecido")
    if not p or not itens: return RedirectResponse(url="/vendas", status_code=303)
    lista = json.loads(itens)
    if not lista: return RedirectResponse(url="/vendas", status_code=303)
    tot = sum(i['v'] for i in lista)
    try:
        with engine.begin() as conn:
            if not conn.execute(text("SELECT id FROM pulseiras WHERE numero_pulseira = :p AND status = 'ABERTA'"), {"p": p}).fetchone(): return RedirectResponse(url="/vendas", status_code=303)
            conn.execute(text("UPDATE pulseiras SET total_conta = total_conta + :t WHERE numero_pulseira = :p AND status = 'ABERTA'"), {"t": tot, "p": p})
            for i in lista:
                conn.execute(text("INSERT INTO vendas_itens (pulseira_num, item_nome, valor, status, garcom) VALUES (:p, :n, :v, 'ABERTA', :g)"), {"p": p, "n": i['n'], "v": i['v'], "g": usuario})
                conn.execute(text("UPDATE produtos SET estoque = GREATEST(COALESCE(estoque, 0) - 1, 0) WHERE nome = :n"), {"n": i['n']})
            txt = "--------------------------------\n      QUIOSQUE CHOPP BRAHMA     \n   TICKET DE PREPARO DE BALCAO  \n--------------------------------\n"
            txt += f"PULSEIRA: {p}\nDATA: {datetime.now().strftime('%d/%m/%Y %H:%M')}\nATENDENTE: {usuario}\n--------------------------------\nQTD X VL.UN               VL.TOT\n--------------------------------\n"
            for i in lista: txt += f"{i['n']}\n" + formata_linha(f"1 x {float(i['v']):.2f}", f"{float(i['v']):.2f}") + "\n"
            txt += "--------------------------------\n" + formata_linha("TOTAL R$", f"{tot:.2f}") + "\n--------------------------------\n         VIA DE PREPARO         \n"
            conn.execute(text("INSERT INTO fila_impressao (conteudo) VALUES (:txt)"), {"txt": txt})
    except Exception: pass
    return RedirectResponse(url=f"/vendas?p={p}", status_code=303)

@app.get("/fechar_conta", response_class=HTMLResponse)
async def fechar_conta(request: Request, q: str = ""):
    if request.session.get("role") not in ["admin", "gerente", "garcom", "caixa"]: return RedirectResponse(url="/central")
    res = ""
    if q:
        q = q.strip()
        with engine.connect() as conn:
            query = conn.execute(text("SELECT p.numero_pulseira, p.total_conta, c.nome_completo FROM pulseiras p JOIN clientes c ON p.cliente_cpf = c.cpf WHERE (p.numero_pulseira = :q OR c.cpf = :q) AND p.status = 'ABERTA'"), {"q": q}).fetchone()
            if query:
                itens_q = conn.execute(text("SELECT item_nome, COUNT(*) as qtd, SUM(valor) as tot FROM vendas_itens WHERE pulseira_num = :p AND status = 'ABERTA' GROUP BY item_nome"), {"p": query.numero_pulseira}).fetchall()
                lista = "".join([f"<div class='item-linha'><span>{i.qtd}x {i.item_nome}</span><span>R$ {float(i.tot or 0):.2f}</span></div>" for i in itens_q]) + f"<div class='item-linha'><span>1x Couvert Artístico</span><span>R$ 7.00</span></div>"
                subtotal, taxa = float(query.total_conta or 0), float(query.total_conta or 0) * 0.10
                total_final = subtotal + taxa
                res = f"""<div style='background:#f4f4f4; padding:20px; border-radius:10px; color:#333; margin-top:20px; text-align:left;'><h3 style='text-align:center; margin-bottom:5px;'>{query.nome_completo}</h3><p style='text-align:center; margin-top:0; font-weight:bold'>Pulseira: {query.numero_pulseira}</p><div style='background:white; padding:15px; border-radius:8px; max-height:220px; overflow-y:auto; border:1px solid #ddd;'>{lista}</div><div style='padding-top:15px; font-size:16px;'><div class='item-linha'><span>Subtotal Consumo:</span><span>R$ {subtotal:.2f}</span></div><div class='item-linha'><span>Taxa Serviço (10%):</span><span>R$ {taxa:.2f}</span></div><div class='item-linha' style='color:#062b5e;'><span style='padding-top:5px;'>Desconto (R$):</span><div style='display:flex; gap:5px;'><input type='number' id='input_desconto' value='0' min='0' step='0.01' style='width:70px; text-align:right; border:1px solid #ccc; border-radius:3px; padding:5px;' placeholder='0.00'><button type='button' onclick='calcDiv()' style='background:#062b5e; color:white; border:none; border-radius:3px; padding:5px 10px; cursor:pointer; font-weight:bold;'>APLICAR</button></div></div><div class='item-linha' style='font-weight:bold; font-size:20px; color:#d31a21; margin-top:10px;'><span>TOTAL A PAGAR:</span><span id='tot_final'>R$ {total_final:.2f}</span></div><div class='item-linha' style='margin-top:10px;'><span>Dividir por:</span><input type='number' id='divisores' value='1' min='1' style='width:60px; text-align:center; border:1px solid #ccc; border-radius:3px; font-weight:bold; padding:5px;' oninput='calcDiv()'></div><div class='item-linha' style='font-weight:bold; font-size:18px;'><span>Por Pessoa:</span><span id='val_pessoa'>R$ {total_final:.2f}</span></div><div class='item-linha' style='margin-top:15px; align-items:center;'><span style='font-weight:bold;'>Pagamento:</span><select id='select_pag' class='input-padrao' style='width:auto; padding:5px; margin:0;' onchange='document.getElementById("input_pag_form").value = this.value'><option value='DINHEIRO'>DINHEIRO</option><option value='PIX'>PIX</option><option value='C. CREDITO'>C. CREDITO</option><option value='C. DEBITO'>C. DEBITO</option></select></div></div><form action='/confirmar_fechamento' method='post'><input type='hidden' name='p' value='{query.numero_pulseira}'><input type='hidden' name='divisao' id='input_div' value='1'><input type='hidden' name='desconto' id='input_desc_form' value='0'><input type='hidden' name='pagamento' id='input_pag_form' value='DINHEIRO'><button class='btn-acao' style='background:#28a745; font-size:18px; margin-top:15px;'>🖨️ CONFIRMAR E IMPRIMIR RECIBO</button></form><script>function calcDiv() {{ let subtotal = {subtotal}; let taxa = {taxa}; let descInput = document.getElementById('input_desconto').value.replace(',', '.'); let desc = parseFloat(descInput) || 0; let div = parseInt(document.getElementById('divisores').value) || 1; let totFinal = subtotal + taxa - desc; if (totFinal < 0) totFinal = 0; document.getElementById('tot_final').innerText = 'R$ ' + totFinal.toFixed(2); document.getElementById('val_pessoa').innerText = 'R$ ' + (totFinal / div).toFixed(2); document.getElementById('input_div').value = div; document.getElementById('input_desc_form').value = desc; }}</script></div>"""
            else: res = "<p style='color:red;'>Nenhuma comanda aberta localizada.</p>"
    return f"<html><head>{CSS}</head><body><div class='container-center'><div class='card-center'>{IMG_LOGO_PEQ}<h2>Fechar Conta</h2><form method='get'><input class='input-padrao' name='q' placeholder='CPF ou Nº Pulseira' value='{q}' required><button class='btn-acao'>CONSULTAR CONTA</button></form>{res}<br><a href='/central' style='color:gray'>Voltar</a></div></div></body></html>"

@app.post("/confirmar_fechamento")
async def confirmar_fechamento(request: Request):
    if request.session.get("role") not in ["admin", "gerente", "garcom", "caixa"]: return RedirectResponse(url="/central")
    form = await request.form()
    p, divisao, desconto_str, pagamento = form.get("p", ""), form.get("divisao", "1"), form.get("desconto", "0"), form.get("pagamento", "DINHEIRO")
    try: div_val = int(divisao)
    except: div_val = 1
    try: desc_val = float(desconto_str)
    except: desc_val = 0.0
    try:
        with engine.begin() as conn: 
            c_info = conn.execute(text("SELECT c.nome_completo, p.total_conta FROM pulseiras p JOIN clientes c ON p.cliente_cpf = c.cpf WHERE p.numero_pulseira = :p AND p.status = 'ABERTA'"), {"p": p}).fetchone()
            if not c_info: return RedirectResponse(url="/central", status_code=303)
            itens_q = conn.execute(text("SELECT item_nome, COUNT(*) as qtd, SUM(valor) as tot FROM vendas_itens WHERE pulseira_num = :p AND status = 'ABERTA' GROUP BY item_nome"), {"p": p}).fetchall()
            conn.execute(text("UPDATE pulseiras SET status = 'FECHADA', forma_pagamento = :pag, data_fechamento = CURRENT_TIMESTAMP WHERE numero_pulseira = :p AND status = 'ABERTA'"), {"p": p, "pag": pagamento})
            conn.execute(text("UPDATE vendas_itens SET status = 'FECHADA' WHERE pulseira_num = :p AND status = 'ABERTA'"), {"p": p})
            subt, taxa = float(c_info.total_conta or 0), float(c_info.total_conta or 0) * 0.10
            tot = max(subt + taxa - desc_val, 0)
            val_div = tot / div_val
            txt = "--------------------------------\n      QUIOSQUE CHOPP BRAHMA     \n      NOTA DE CONFERENCIA       \n     AGUARDE SUA NOTA FISCAL    \n--------------------------------\n"
            txt += f"PULSEIRA: {p}\nCLIENTE: {c_info.nome_completo[:20]}\nDATA: {datetime.now().strftime('%d/%m/%Y %H:%M')}\n--------------------------------\nQTD X VL.UN               VL.TOT\n--------------------------------\n"
            for i in itens_q: 
                v_unit = float(i.tot) / i.qtd if i.qtd > 0 else 0
                txt += f"{i.item_nome}\n" + formata_linha(f"{i.qtd} x {v_unit:.2f}", f"{float(i.tot or 0):.2f}") + "\n"
            txt += "COUVERT ARTISTICO\n" + formata_linha("1 x 7.00", "7.00") + "\n--------------------------------\n"
            txt += formata_linha("PRODUTOS", f"{subt:.2f}") + "\n" + formata_linha("SERVICOS 10%", f"{taxa:.2f}") + "\n" + formata_linha("DESCONTO", f"- {desc_val:.2f}") + "\n--------------------------------\n"
            txt += formata_linha("TOTAL R$", f"{tot:.2f}") + "\n--------------------------------\n"
            txt += formata_linha("PAGAMENTO:", pagamento) + "\n" + formata_linha("DIVIDIDO POR:", f"{div_val} PESSOA(S)") + "\n" + formata_linha("POR PESSOA R$:", f"{val_div:.2f}") + "\n"
            txt += "--------------------------------\n  COMANDA DE CIRCULACAO INTERNA \n      NAO TEM VALOR FISCAL      \n     OBRIGADO E VOLTE SEMPRE!   \n"
            conn.execute(text("INSERT INTO fila_impressao (conteudo) VALUES (:txt)"), {"txt": txt})
    except Exception: pass
    return RedirectResponse(url="/central", status_code=303)

@app.get("/buscar", response_class=HTMLResponse)
async def tela_busca(request: Request, q: str = ""):
    if not request.session.get("role"): return RedirectResponse(url="/")
    resultados = ""
    if q:
        with engine.connect() as conn:
            query = conn.execute(text("SELECT nome_completo, cpf, data_nascimento FROM clientes WHERE nome_completo ILIKE :q OR cpf LIKE :q"), {"q": f"%{q}%"}).fetchall()
            for r in query:
                is_bday = r.data_nascimento.strftime("%m-%d") == date.today().strftime("%m-%d") if r.data_nascimento else False
                resultados += f"<tr><td style='color:black'>{r.nome_completo}{' 🎁' if is_bday else ''}</td><td><form action='/abrir' method='post' style='display:flex;gap:5px'><input type='hidden' name='cpf' value='{r.cpf}'><input class='input-padrao' name='p' placeholder='Nº Pulseira' required style='width:100px;margin:0'><button class='btn-acao' style='background:#d31a21;padding:8px;margin:0'>ABRIR</button></form></td></tr>"
    return f"<html><head>{CSS}</head><body><div class='container-center'><div class='card-center'>{IMG_LOGO_PEQ}<h2>Buscar Cliente</h2><form method='get'><input class='input-padrao' name='q' placeholder='Nome ou CPF' value='{q}'><button class='btn-acao'>PESQUISAR</button></form><table>{resultados}</table><br><a href='/central'>Voltar</a></div></div></body></html>"

@app.post("/abrir")
async def abrir(request: Request):
    if not request.session.get("role"): return RedirectResponse(url="/")
    form = await request.form()
    cpf, p = form.get("cpf", "").strip(), form.get("p", "").strip()
    try:
        with engine.begin() as conn:
            if conn.execute(text("SELECT numero_pulseira FROM pulseiras WHERE cliente_cpf = :c AND status = 'ABERTA'"), {"c": cpf}).fetchone(): return HTMLResponse(f"<script>alert('Cliente já possui comanda!'); window.history.back();</script>")
            if conn.execute(text("SELECT cliente_cpf FROM pulseiras WHERE numero_pulseira = :p AND status = 'ABERTA'"), {"p": p}).fetchone(): return HTMLResponse(f"<script>alert('A pulseira {p} já está em uso!'); window.history.back();</script>")
            conn.execute(text("INSERT INTO pulseiras (numero_pulseira, cliente_cpf, total_conta, status) VALUES (:p, :c, 7.00, 'ABERTA')"), {"p": p, "c": cpf})
    except Exception: pass
    return RedirectResponse(url=f"/vendas?p={p}", status_code=303)

@app.get("/cadastro", response_class=HTMLResponse)
async def tela_cadastro(request: Request):
    if not request.session.get("role"): return RedirectResponse(url="/")
    return f"<html><head>{CSS}</head><body><div class='container-center'><div class='card-center'>{IMG_LOGO_PEQ}<h2>Novo Cliente</h2><form action='/salvar' method='post'><input class='input-padrao' name='nome' placeholder='Nome Completo' required><input class='input-padrao' name='cpf' placeholder='CPF' required><input class='input-padrao' name='nasc' type='date' required><input class='input-padrao' name='contato' placeholder='WhatsApp' required><input class='input-padrao' name='email' type='email' placeholder='E-mail (Opcional)'><input class='input-padrao' name='pulseira' placeholder='Nº Pulseira' required><button class='btn-acao' style='background:#d31a21'>SALVAR E ABRIR</button></form><br><a href='/central'>Voltar</a></div></div></body></html>"

@app.post("/salvar")
async def salvar(request: Request):
    if not request.session.get("role"): return RedirectResponse(url="/")
    f = await request.form()
    n, c, d, co, e, p = f.get("nome",""), f.get("cpf","").strip(), f.get("nasc",""), f.get("contato",""), f.get("email",None), f.get("pulseira","").strip()
    try:
        with engine.begin() as conn:
            conn.execute(text("INSERT INTO clientes (nome_completo, cpf, data_nascimento, contato, email) VALUES (:n, :c, :d, :co, :e) ON CONFLICT (cpf) DO NOTHING"), {"n":n, "c":c, "d":d, "co":co, "e":e})
            if conn.execute(text("SELECT numero_pulseira FROM pulseiras WHERE cliente_cpf = :c AND status = 'ABERTA'"), {"c": c}).fetchone(): return HTMLResponse("<script>alert('Cliente já possui comanda aberta!'); window.history.back();</script>")
            if conn.execute(text("SELECT cliente_cpf FROM pulseiras WHERE numero_pulseira = :p AND status = 'ABERTA'"), {"p": p}).fetchone(): return HTMLResponse(f"<script>alert('Pulseira {p} em uso!'); window.history.back();</script>")
            conn.execute(text("INSERT INTO pulseiras (numero_pulseira, cliente_cpf, total_conta, status) VALUES (:p, :c, 7.00, 'ABERTA')"), {"p":p, "c":c})
    except Exception: pass
    return RedirectResponse(url=f"/vendas?p={p}", status_code=303)

@app.get("/dashboard", response_class=HTMLResponse)
async def dashboard(request: Request, inicio: str = "", fim: str = "", cat: str = "", prod: str = ""):
    if request.session.get("role") not in ["admin", "gerente"]: return RedirectResponse(url="/central")
    
    where_pulseira = "status = 'FECHADA'"
    where_vendas = "status = 'FECHADA'"
    where_hist = "1=1"
    where_prod = "1=1"
    
    params_p = {}
    params_v = {}
    params_h = {}
    
    if inicio:
        where_pulseira += " AND CAST(data_fechamento AS DATE) >= CAST(:inicio AS DATE)"
        where_vendas += " AND CAST(data_venda AS DATE) >= CAST(:inicio AS DATE)"
        where_hist += " AND CAST(data_entrada AS DATE) >= CAST(:inicio AS DATE)"
        params_p["inicio"] = params_v["inicio"] = params_h["inicio"] = inicio
    if fim:
        where_pulseira += " AND CAST(data_fechamento AS DATE) <= CAST(:fim AS DATE)"
        where_vendas += " AND CAST(data_venda AS DATE) <= CAST(:fim AS DATE)"
        where_hist += " AND CAST(data_entrada AS DATE) <= CAST(:fim AS DATE)"
        params_p["fim"] = params_v["fim"] = params_h["fim"] = fim
        
    join_vendas = ""
    if cat or prod:
        join_vendas = "JOIN produtos p ON vendas_itens.item_nome = p.nome"
        if cat:
            where_vendas += " AND p.categoria = :cat"
            where_prod += " AND p.categoria = :cat"
            params_v["cat"] = cat
        if prod:
            prod_str = prod.replace("#", "").strip()
            try:
                prod_id = int(prod_str)
                where_vendas += " AND (p.nome ILIKE :prod OR p.id = :prod_id)"
                where_prod += " AND (p.nome ILIKE :prod OR p.id = :prod_id)"
                where_hist += " AND produto_nome IN (SELECT nome FROM produtos WHERE nome ILIKE :prod OR id = :prod_id)"
                params_v["prod_id"] = params_h["prod_id"] = prod_id
            except ValueError:
                where_vendas += " AND p.nome ILIKE :prod"
                where_prod += " AND p.nome ILIKE :prod"
                where_hist += " AND produto_nome ILIKE :prod"
            params_v["prod"] = params_h["prod"] = f"%{prod_str}%"

    with engine.connect() as conn:
        categorias_db = conn.execute(text("SELECT DISTINCT categoria FROM produtos WHERE categoria IS NOT NULL")).fetchall()
        opcoes_cat = "".join([f"<option value='{c.categoria}' {'selected' if cat == c.categoria else ''}>{c.categoria}</option>" for c in categorias_db])

        kpi = conn.execute(text(f"SELECT SUM(total_conta) as total, COUNT(*) as qtd, AVG(total_conta) as media FROM pulseiras WHERE {where_pulseira}"), params_p).fetchone()
        faturamento_total, total_comandas, ticket_medio = float(kpi.total or 0), int(kpi.qtd or 0), float(kpi.media or 0)

        pagamentos = conn.execute(text(f"SELECT forma_pagamento, COUNT(*) as qtd FROM pulseiras WHERE {where_pulseira} GROUP BY forma_pagamento"), params_p).fetchall()
        labels_pag, data_pag = [r.forma_pagamento or "N/D" for r in pagamentos], [r.qtd for r in pagamentos]

        garcons = conn.execute(text(f"SELECT garcom, SUM(vendas_itens.valor) as total FROM vendas_itens {join_vendas} WHERE {where_vendas} GROUP BY garcom ORDER BY total DESC"), params_v).fetchall()

        total_vendas_db = conn.execute(text(f"SELECT COUNT(*) as total_vendido FROM vendas_itens {join_vendas} WHERE {where_vendas}"), params_v).fetchone()
        total_saidas = int(total_vendas_db.total_vendido or 0)
        
        total_entradas_db = conn.execute(text(f"SELECT SUM(qtd_adicionada) as total_entrou FROM historico_estoque WHERE {where_hist}"), params_h).fetchone()
        total_entradas = int(total_entradas_db.total_entrou or 0)

        query_cruz = f"SELECT p.nome, p.estoque, COUNT(v.id) as vendidos FROM produtos p LEFT JOIN vendas_itens v ON p.nome = v.item_nome AND v.status = 'FECHADA' {'AND CAST(v.data_venda AS DATE) >= CAST(:inicio AS DATE)' if inicio else ''} {'AND CAST(v.data_venda AS DATE) <= CAST(:fim AS DATE)' if fim else ''} WHERE {where_prod} GROUP BY p.nome, p.estoque ORDER BY vendidos DESC LIMIT 10"
        cruzamento = conn.execute(text(query_cruz), params_v).fetchall()
        labels_cruz, data_cruz_vendidos, data_cruz_estoque = [r.nome for r in cruzamento], [r.vendidos for r in cruzamento], [r.estoque for r in cruzamento]

    dash_css = """<style>.grid-dash { display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 20px; width: 100%; max-width: 1100px; margin-bottom: 20px; } .card-kpi { background: white; padding: 20px; border-radius: 10px; color: #333; box-shadow: 0 4px 6px rgba(0,0,0,0.1); border-left: 5px solid #d31a21; } .card-kpi.estoque { border-left-color: #e67e22; } .card-kpi h3 { margin: 0; font-size: 14px; color: #666; text-transform: uppercase; } .card-kpi p { margin: 10px 0 0; font-size: 24px; font-weight: bold; color: #0a3a7a; } .chart-container { background: white; padding: 20px; border-radius: 10px; margin-bottom: 20px; width: 100%; max-width: 530px; display: inline-block; vertical-align: top; } .aba-btn { background: #062b5e; color: white; border: none; padding: 15px 30px; font-size: 16px; font-weight: bold; border-radius: 8px; cursor: pointer; margin-right: 10px; transition: 0.3s; } .aba-btn:hover { background: #d31a21; } .filtro-bar { background: rgba(255,255,255,0.1); padding: 15px; border-radius: 10px; margin-bottom: 20px; display: flex; flex-wrap: wrap; gap: 10px; align-items: center; border: 1px solid rgba(255,255,255,0.2); }</style><script src="https://cdn.jsdelivr.net/npm/chart.js"></script>"""

    return f"""<html><head>{CSS}{dash_css}</head><body><div class='main-area' style='padding: 30px; overflow-y: auto;'><h1 style='color:white; margin-bottom: 5px;'>📊 Painel de Gestão Avançado</h1>
    
    <form class='filtro-bar' method='GET'>
        <div><label style='font-size:12px;'>De:</label><br><input type='date' name='inicio' value='{inicio}' class='input-padrao' style='width:140px; margin:0;'></div>
        <div><label style='font-size:12px;'>Até:</label><br><input type='date' name='fim' value='{fim}' class='input-padrao' style='width:140px; margin:0;'></div>
        <div><label style='font-size:12px;'>Categoria:</label><br><select name='cat' class='input-padrao' style='width:130px; margin:0;'><option value=''>TODAS</option>{opcoes_cat}</select></div>
        <div><label style='font-size:12px;'>Produto (Nome/Cód):</label><br><input type='text' name='prod' value='{prod}' placeholder='Ex: Heineken ou 001' class='input-padrao' style='width:150px; margin:0;'></div>
        <div style='display:flex; align-items:flex-end;'><button class='btn-acao' style='background:#28a745; margin:0; height:45px; margin-top:17px; width:100px;'>FILTRAR</button></div>
        <div style='display:flex; align-items:flex-end;'><a href='/dashboard' class='btn-acao' style='background:#666; margin:0; height:45px; margin-top:17px; width:100px; line-height:15px'>LIMPAR</a></div>
    </form>

    <div style='margin-bottom: 30px;'><button id='btn-fin' class='aba-btn' style='background:#17a2b8' onclick="showTab('fin')">💰 VISÃO FINANCEIRA</button><button id='btn-est' class='aba-btn' style='opacity:0.6; background:#e67e22' onclick="showTab('est')">📦 VISÃO ESTOQUE</button></div>
    
    <div id='tab-fin'>
        <div class='grid-dash'><div class='card-kpi'><h3>Faturamento do Período</h3><p>R$ {faturamento_total:.2f}</p></div><div class='card-kpi'><h3>Ticket Médio</h3><p>R$ {ticket_medio:.2f}</p></div><div class='card-kpi'><h3>Comandas Fechadas</h3><p>{total_comandas}</p></div></div>
        <div style='width: 100%; max-width: 1100px;'><div class='chart-container'><h3 style='color:#333'>💰 Meios de Pagamento</h3><canvas id="chartPag"></canvas></div><div class='chart-container'><h3 style='color:#333'>👨‍🍳 Vendas por Garçom (R$)</h3><canvas id="chartGarcom"></canvas></div></div>
        <div class='card-center' style='max-width: 1100px; text-align: left; margin-top:20px;'><h3 style='color:black; margin-top:0'>👨‍🍳 Tabela de Performance</h3><table><tr style='color:black; border-bottom:2px solid #ccc'><th>Garçom</th><th>Total Vendido (R$)</th></tr>{"".join([f"<tr><td style='color:black'>{g.garcom or 'Não Identificado'}</td><td style='color:black; font-weight:bold'>R$ {float(g.total or 0):.2f}</td></tr>" for g in garcons])}</table></div>
    </div>
    
    <div id='tab-est' style='display:none;'>
        <div class='grid-dash'><div class='card-kpi estoque'><h3>Qtd de Entradas (Compras)</h3><p style='color:#28a745'>+{total_entradas} Itens</p></div><div class='card-kpi estoque'><h3>Qtd de Saídas (Vendas)</h3><p style='color:#d31a21'>-{total_saidas} Itens</p></div></div>
        <div style='width: 100%; max-width: 1100px;'><div class='chart-container' style='max-width: 100%; display:block;'><h3 style='color:#333'>🔄 Comparativo Geral: Estoque Físico vs Vendidos</h3><canvas id="chartCruzamento"></canvas></div></div>
    </div><br><a href='/central' class='btn-acao' style='width: 200px; margin:auto'>Voltar ao Início</a></div>
    
    <script>
        function showTab(tab) {{ document.getElementById('tab-fin').style.display = tab === 'fin' ? 'block' : 'none'; document.getElementById('tab-est').style.display = tab === 'est' ? 'block' : 'none'; document.getElementById('btn-fin').style.opacity = tab === 'fin' ? '1' : '0.6'; document.getElementById('btn-est').style.opacity = tab === 'est' ? '1' : '0.6'; }} 
        new Chart(document.getElementById('chartPag'), {{ type: 'doughnut', data: {{ labels: {json.dumps(labels_pag)}, datasets: [{{ data: {json.dumps(data_pag)}, backgroundColor: ['#0a3a7a', '#d31a21', '#ffc107', '#28a745'] }}] }} }}); 
        new Chart(document.getElementById('chartGarcom'), {{ type: 'bar', data: {{ labels: {json.dumps([g.garcom or 'N/D' for g in garcons])}, datasets: [{{ label: 'Total Vendido (R$)', data: {json.dumps([float(g.total or 0) for g in garcons])}, backgroundColor: '#17a2b8' }}] }} }}); 
        new Chart(document.getElementById('chartCruzamento'), {{ type: 'bar', data: {{ labels: {json.dumps(labels_cruz)}, datasets: [{{ label: 'Qtd Vendida no Período', data: {json.dumps(data_cruz_vendidos)}, backgroundColor: '#d31a21' }}, {{ label: 'Estoque Físico Atual', data: {json.dumps(data_cruz_estoque)}, backgroundColor: '#0a3a7a' }}] }} }});
    </script></body></html>
    
@app.get("/logout")
async def logout(request: Request):
    request.session.clear()
    return RedirectResponse(url="/")

@app.get("/api/pendentes")
async def api_pendentes():
    jobs = []
    try:
        with engine.connect() as conn:
            r = conn.execute(text("SELECT id, conteudo FROM fila_impressao WHERE status = 'PENDENTE' ORDER BY id ASC LIMIT 1")).fetchone()
            if r: jobs.append({"id": r.id, "conteudo": r.conteudo})
    except Exception: pass
    return {"jobs": jobs}

@app.post("/api/impresso/{job_id}")
async def api_impresso(job_id: int):
    try:
        with engine.begin() as conn: conn.execute(text("UPDATE fila_impressao SET status = 'IMPRESSO' WHERE id = :id"), {"id": job_id})
    except Exception: pass
    return {"status": "ok"}

@app.get("/download_conector")
async def download_conector():
    return FileResponse(path="conector.exe", filename="conector_brahma.exe", media_type="application/octet-stream")
