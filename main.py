from fastapi import FastAPI, Form, Request, Response
from fastapi.responses import HTMLResponse, RedirectResponse, FileResponse
from sqlalchemy import create_engine, text
from starlette.middleware.sessions import SessionMiddleware
from datetime import datetime, date
import json
import urllib.parse
import os

app = FastAPI()
app.add_middleware(SessionMiddleware, secret_key="jpms_solucoes_gestao_2026_seguro")

DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://postgres:GNlZnHiuKAcFnpgXhwILfigqKCNkaHqx@interchange.proxy.rlwy.net:44559/railway")
engine = create_engine(DATABASE_URL, pool_pre_ping=True)

MENU_INICIAL = {
    "CHOPP": [("Caneca 350ml", 11.9), ("Tulipa 700ml", 17.9), ("Torre 2.5L", 84.9)],
    "CERVEJAS": [("Cerveja 600ml Padrão", 12.9), ("Cerveja Long Neck", 9.9), ("Cerveja Zero", 10.0), ("Cerveja Artesanal IPA", 16.9)],
    "PETISCOS": [("Porção de Fritas", 21.9), ("Fritas c/ Cheddar e Bacon", 27.9), ("Frango a Passarinho", 28.9), ("Tábua de Frios", 34.9)],
    "BEBIDAS": [("Caipirinha de Limão", 14.9), ("Gin Tônica", 24.9), ("Refrigerante Lata", 5.0), ("Suco Natural", 7.0), ("Água Mineral", 4.0)]
}

IMAGENS_CAT = {
    "CHOPP": "https://cdn-icons-png.flaticon.com/512/1054/1054060.png",
    "CERVEJAS": "https://cdn-icons-png.flaticon.com/512/3014/3014490.png",
    "PETISCOS": "https://cdn-icons-png.flaticon.com/512/1046/1046786.png",
    "BEBIDAS": "https://cdn-icons-png.flaticon.com/512/2405/2405462.png",
    "OUTROS": "https://cdn-icons-png.flaticon.com/512/1032/1032130.png"
}

with engine.begin() as conn:
    conn.execute(text("""
        CREATE TABLE IF NOT EXISTS clientes (id SERIAL PRIMARY KEY, nome_completo TEXT NOT NULL, cpf TEXT UNIQUE NOT NULL, data_nascimento DATE, contato TEXT, email TEXT);
        CREATE TABLE IF NOT EXISTS comandas (id SERIAL PRIMARY KEY, numero_comanda TEXT NOT NULL, cliente_cpf TEXT REFERENCES clientes(cpf), total_conta DECIMAL(10,2) DEFAULT 0.00, status TEXT DEFAULT 'ABERTA', forma_pagamento TEXT, data_fechamento TIMESTAMP, nfe_solicitada BOOLEAN DEFAULT FALSE, cpf_nota TEXT, desconto DECIMAL(10,2) DEFAULT 0.00);
        CREATE TABLE IF NOT EXISTS vendas_itens (id SERIAL PRIMARY KEY, comanda_num TEXT, item_nome TEXT, valor DECIMAL(10,2), data_venda DATE DEFAULT CURRENT_DATE, hora_venda TIME DEFAULT CURRENT_TIME, status TEXT DEFAULT 'ABERTA', garcom TEXT, comissao_status TEXT DEFAULT 'PENDENTE');
        CREATE TABLE IF NOT EXISTS produtos (id SERIAL PRIMARY KEY, nome TEXT UNIQUE NOT NULL, categoria TEXT DEFAULT 'OUTROS', preco DECIMAL(10,2) DEFAULT 0.00, estoque INT DEFAULT 0);
        CREATE TABLE IF NOT EXISTS fila_impressao (id SERIAL PRIMARY KEY, conteudo TEXT, status TEXT DEFAULT 'PENDENTE', data_criacao TIMESTAMP DEFAULT CURRENT_TIMESTAMP);
        CREATE TABLE IF NOT EXISTS historico_estoque (id SERIAL PRIMARY KEY, produto_nome TEXT, qtd_adicionada INT, data_entrada DATE DEFAULT CURRENT_DATE);
        CREATE TABLE IF NOT EXISTS usuarios (id SERIAL PRIMARY KEY, username TEXT UNIQUE NOT NULL, password TEXT NOT NULL, role TEXT NOT NULL);
        CREATE TABLE IF NOT EXISTS caixa_movimentos (id SERIAL PRIMARY KEY, tipo TEXT, valor DECIMAL(10,2), descricao TEXT, data_registro TIMESTAMP DEFAULT CURRENT_TIMESTAMP, usuario TEXT);
        CREATE TABLE IF NOT EXISTS turnos (id SERIAL PRIMARY KEY, data_abertura TIMESTAMP DEFAULT CURRENT_TIMESTAMP, data_fechamento TIMESTAMP, fundo_inicial DECIMAL(10,2) DEFAULT 0.00, status TEXT DEFAULT 'ABERTO', usuario_abertura TEXT, usuario_fechamento TEXT);
    """))

MIGRACOES = [
    "ALTER TABLE comandas ADD COLUMN IF NOT EXISTS nfe_solicitada BOOLEAN DEFAULT FALSE;",
    "ALTER TABLE comandas ADD COLUMN IF NOT EXISTS cpf_nota TEXT;",
    "ALTER TABLE comandas ADD COLUMN IF NOT EXISTS status TEXT DEFAULT 'ABERTA';",
    "ALTER TABLE comandas ADD COLUMN IF NOT EXISTS forma_pagamento TEXT;",
    "ALTER TABLE comandas ADD COLUMN IF NOT EXISTS data_fechamento TIMESTAMP;",
    "ALTER TABLE comandas ADD COLUMN IF NOT EXISTS desconto DECIMAL(10,2) DEFAULT 0.00;",
    "ALTER TABLE vendas_itens ADD COLUMN IF NOT EXISTS comissao_status TEXT DEFAULT 'PENDENTE';",
    "ALTER TABLE produtos ADD COLUMN IF NOT EXISTS categoria TEXT DEFAULT 'OUTROS';",
    "ALTER TABLE produtos ADD COLUMN IF NOT EXISTS preco DECIMAL(10,2) DEFAULT 0.00;",
    "ALTER TABLE produtos ADD COLUMN IF NOT EXISTS estoque INT DEFAULT 0;"
]
for mig in MIGRACOES:
    try:
        with engine.begin() as conn: conn.execute(text(mig))
    except Exception: pass

try:
    with engine.begin() as conn:
        for cat, itens in MENU_INICIAL.items():
            for n, p in itens:
                conn.execute(text("INSERT INTO produtos (nome, categoria, preco, estoque) VALUES (:n, :c, :p, 100) ON CONFLICT (nome) DO NOTHING"), {"n": n, "c": cat, "p": p})
        conn.execute(text("INSERT INTO usuarios (username, password, role) VALUES ('admin', '1234', 'admin') ON CONFLICT (username) DO NOTHING"))
except Exception: pass

IMG_URL = "/logo.png"
CSS = f"""
<meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no">
<meta name="apple-mobile-web-app-capable" content="yes">
<link rel="apple-touch-icon" href="{IMG_URL}">
<style>
    * {{ box-sizing: border-box; font-family: 'Segoe UI', Tahoma, sans-serif; }}
    body {{ margin: 0; background: #0a3a7a; color: white; height: 100vh; display: flex; flex-direction: column; overflow: hidden; }}
    .layout-vendas {{ display: flex; flex: 1; height: 100vh; }}
    .menu-lateral {{ width: 220px; padding: 20px; display: flex; flex-direction: column; gap: 10px; border-right: 1px solid rgba(255,255,255,0.1); background: #082d5e; overflow-y:auto; }}
    .btn-menu {{ background: #0a3a7a; color: white; border: 1px solid #1352a3; padding: 15px; border-radius: 8px; text-align: left; font-weight: bold; font-size: 15px; cursor: pointer; text-decoration: none; display: flex; justify-content: flex-start; align-items:center; gap: 10px; }}
    .btn-menu:hover, .btn-menu.ativo {{ background: #d31a21; border-color: white; }}
    .main-area {{ flex: 1; padding: 20px; display: flex; flex-direction: column; overflow-y: auto; align-items: center; width: 100%; }}
    .logo-central {{ width: 280px; max-width: 100%; height: auto; margin-bottom: 20px; filter: drop-shadow(0px 4px 6px rgba(0,0,0,0.5)); }}
    .logo-peq {{ width: 180px; max-width: 100%; height: auto; margin-bottom: 10px; filter: drop-shadow(0px 2px 4px rgba(0,0,0,0.5)); }}
    .grid-produtos {{ display: grid; grid-template-columns: repeat(auto-fill, minmax(160px, 1fr)); gap: 15px; width: 100%; max-width: 900px; }}
    .prod-card {{ border-radius: 10px; padding: 15px 10px; text-align: center; cursor: pointer; display: flex; flex-direction: column; justify-content: space-between; min-height: 120px; box-shadow: 0 4px 6px rgba(0,0,0,0.3); transition: 0.2s; color: white; border-width: 2px; border-style: solid; }}
    .prod-card:hover {{ transform: scale(1.05); border-color: white; }}
    .bg-green {{ background: linear-gradient(180deg, #28a745 0%, #1e7e34 100%); border-color: #145523; }}
    .bg-red {{ background: linear-gradient(180deg, #d31a21 0%, #9e0b10 100%); border-color: #5a0407; opacity: 0.9; }}
    .prod-card b {{ font-size: 14px; margin-bottom: 8px; text-shadow: 1px 1px 2px rgba(0,0,0,0.6); line-height: 1.2; }}
    .prod-card span {{ font-size: 16px; font-weight: bold; background: rgba(0,0,0,0.3); padding: 5px; border-radius: 5px; }}
    .comanda-lateral {{ width: 340px; background: white; color: black; border-left: 5px solid #d31a21; display: flex; flex-direction: column; }}
    .comanda-header {{ background: #d31a21; color: white; padding: 15px; font-weight: bold; text-align: center; font-size: 18px; }}
    .comanda-body {{ flex: 1; overflow-y: auto; padding: 15px; background: #f9f9f9; }}
    .secao-titulo {{ font-size: 12px; color: #666; text-transform: uppercase; font-weight: bold; border-bottom: 1px solid #ccc; margin-bottom: 10px; padding-bottom: 5px; }}
    .item-linha {{ display: flex; justify-content: space-between; font-size: 14px; margin-bottom: 8px; border-bottom: 1px dashed #ddd; padding-bottom: 5px; align-items: center; color: #333; }}
    .comanda-footer {{ padding: 15px; background: white; border-top: 1px solid #ccc; }}
    .btn-acao {{ display: block; width: 100%; padding: 15px; margin-bottom: 8px; border: none; border-radius: 5px; font-weight: bold; color: white; cursor: pointer; text-align: center; text-decoration: none; font-size: 14px; background: #062b5e; }}
    .btn-acao:hover {{ background: #0d4b9c; }}
    .container-center {{ display: flex; align-items: center; justify-content: center; height: 100vh; padding: 20px; overflow-y: auto; }}
    .card-center {{ background: white; color: #333; padding: 30px; border-radius: 15px; width: 100%; max-width: 650px; text-align: center; box-shadow: 0 8px 20px rgba(0,0,0,0.4); margin: auto; }}
    .input-padrao {{ width: 100%; padding: 12px; margin: 8px 0; border: 1px solid #ccc; border-radius: 5px; font-size: 16px; box-sizing: border-box; background: white; color: #333; }}
    table {{ width: 100%; border-collapse: collapse; margin-top: 15px; }}
    th, td {{ padding: 8px; border-bottom: 1px solid #eee; text-align: left; vertical-align: middle; color: #333; }}
    
    .switch {{ position: relative; display: inline-block; width: 50px; height: 24px; }}
    .switch input {{ opacity: 0; width: 0; height: 0; }}
    .slider {{ position: absolute; cursor: pointer; top: 0; left: 0; right: 0; bottom: 0; background-color: #ccc; transition: .4s; border-radius: 24px; }}
    .slider:before {{ position: absolute; content: ""; height: 18px; width: 18px; left: 3px; bottom: 3px; background-color: white; transition: .4s; border-radius: 50%; }}
    input:checked + .slider {{ background-color: #28a745; }}
    input:checked + .slider:before {{ transform: translateX(26px); }}
    
    .menu-duas-colunas {{ display: grid; grid-template-columns: 1fr; gap: 40px; max-width: 1000px; margin: auto; padding: 10px; }}
    @media (min-width: 800px) {{ .menu-duas-colunas {{ grid-template-columns: 1fr 1fr; gap: 60px; }} }}
    .faixa-laranja {{ background: #e67e22; color: white; padding: 12px 20px; font-size: 22px; font-weight: bold; text-align: center; text-transform: uppercase; position: relative; margin: 0 auto 25px auto; box-shadow: 0 4px 6px rgba(0,0,0,0.6); max-width: 90%; font-family: 'Arial Black', sans-serif; letter-spacing: 1px; }}
    .faixa-laranja::before, .faixa-laranja::after {{ content: ""; position: absolute; top: 0; width: 0; height: 0; border-top: 25px solid transparent; border-bottom: 25px solid transparent; }}
    .faixa-laranja::before {{ left: -20px; border-right: 20px solid #e67e22; }}
    .faixa-laranja::after {{ right: -20px; border-left: 20px solid #e67e22; }}
    .linha-menu {{ display: flex; align-items: flex-end; margin-bottom: 12px; font-size: 15px; color: #ddd; }}
    .linha-nome {{ white-space: nowrap; text-transform: uppercase; font-family: 'Arial', sans-serif; letter-spacing: 0.5px; }}
    .linha-pontos {{ flex-grow: 1; border-bottom: 2px dotted #666; margin: 0 10px; position: relative; top: -5px; opacity: 0.7; }}
    .linha-preco {{ white-space: nowrap; font-weight: bold; color: white; font-size: 16px; }}
    .esgotado-txt {{ color: #d31a21; font-size: 11px; font-weight: bold; margin-left: 8px; background: rgba(0,0,0,0.6); padding: 2px 6px; border-radius: 4px; border: 1px solid #d31a21; vertical-align: middle; }}
    
    @media (max-width: 768px) {{
        body {{ height: auto; overflow: auto; }}
        .layout-vendas {{ display: flex; flex-direction: column; height: auto; min-height: 100vh; }}
        .menu-lateral {{ width: 100%; flex-direction: row; overflow-x: auto; padding: 10px; border-right: none; border-bottom: 2px solid rgba(255,255,255,0.1); display: flex; gap: 8px; flex-shrink: 0; white-space: nowrap; -webkit-overflow-scrolling: touch; }}
        .btn-menu {{ padding: 10px 15px; font-size: 14px; text-align: center; flex: 0 0 auto; justify-content: center; flex-direction: column; }}
        .main-area {{ display: flex; overflow: visible; padding: 10px; flex-shrink: 0; width: 100%; box-sizing: border-box; }}
        .grid-produtos {{ grid-template-columns: repeat(auto-fill, minmax(130px, 1fr)); gap: 10px; width: 100%; }}
        .prod-card {{ min-height: 110px; padding: 10px; }}
        .comanda-lateral {{ width: 100%; display: flex; border-left: none; border-top: 5px solid #d31a21; flex-shrink: 0; }}
        .card-center {{ width: 95%; padding: 20px; }}
    }}
</style>
<script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
"""

IMG_LOGO = f"<div style='display:flex; justify-content:center; margin-bottom:20px;'><img src='{IMG_URL}' class='logo-central'></div>"
IMG_LOGO_PEQ = f"<div style='display:flex; justify-content:center; margin-bottom:15px;'><img src='{IMG_URL}' class='logo-peq'></div>"

@app.get("/sw.js")
async def get_sw(): return Response(content="self.addEventListener('fetch', e => {});", media_type="application/javascript")

@app.get("/logo.png")
async def exibir_logo(): 
    try: return FileResponse("logo_quiosque.png")
    except: return Response(status_code=404)

@app.get("/", response_class=HTMLResponse)
async def login_page(): 
    return f"""<html><head>{CSS}</head><body><div class='container-center'><div class='card-center'>{IMG_LOGO}<h2>Acesso ao Sistema JPMS</h2><form action='/login' method='post'><input class='input-padrao' name='user' placeholder='Usuário' required><input class='input-padrao' name='pw' type='password' placeholder='Senha' required><button class='btn-acao' style='padding:15px; font-size:18px;'>ENTRAR</button></form><br><a href='/cardapio' style='color:#062b5e; font-weight:bold; text-decoration:underline;'>Ver Cardápio Digital</a></div></div></body></html>"""

@app.post("/login")
async def login(request: Request):
    f = await request.form()
    with engine.connect() as conn:
        user = conn.execute(text("SELECT username, role FROM usuarios WHERE username = :u AND password = :p"), {"u": f.get("user", "").strip().lower(), "p": f.get("pw", "")}).fetchone()
        if user:
            request.session["user"], request.session["role"] = user.username, user.role
            return RedirectResponse(url="/central", status_code=303)
    return HTMLResponse("<script>alert('Usuário ou Senha incorretos!'); window.location.href='/';</script>")

@app.get("/central", response_class=HTMLResponse)
async def central(request: Request):
    user, role = request.session.get("user"), request.session.get("role")
    if not user: return RedirectResponse(url="/")
    
    with engine.connect() as conn:
        turno_aberto = conn.execute(text("SELECT id FROM turnos WHERE status = 'ABERTO' LIMIT 1")).fetchone()
        
    b = ""
    if not turno_aberto:
        b += f"<div style='background:#fef3c7; border:2px dashed #e67e22; padding:15px; border-radius:8px; margin-bottom:15px; color:#d31a21; font-weight:bold;'>⚠️ O CAIXA/EVENTO ESTÁ FECHADO!</div>"
        if role in ["admin", "gerente", "caixa"]:
            b += f"<a href='/caixa' class='btn-acao' style='background:#28a745; padding:20px; font-size:18px;'>🟢 INICIAR EVENTO (ABRIR CAIXA)</a>"
        if role in ["admin", "gerente"]:
            b += "<a href='/dashboard' class='btn-acao' style='background:#17a2b8'>📊 DASHBOARD GERENCIAL</a><a href='/estoque' class='btn-acao' style='background:#062b5e'>📦 GESTÃO DE ESTOQUE</a>"
        if role == "admin":
            b += "<a href='/usuarios' class='btn-acao' style='background:#9b59b6'>👥 GERENCIAR USUÁRIOS</a>"
    else:
        if role in ["admin", "gerente", "garcom", "caixa", "portaria"]:
            # Aqui entra a barra de acesso rápido da Comanda Topzeira
            b += f"""
            <div style='background:#f4f4f4; padding:15px; border-radius:8px; margin-bottom:15px; border:2px solid #ccc;'>
                <h3 style='margin-top:0; color:#d31a21; margin-bottom:10px;'>Acesso Rápido - Comanda</h3>
                <form action='/vendas' method='get' style='display:flex; gap:10px; margin:0;'>
                    <input type='text' name='p' class='input-padrao' placeholder='Nº da Comanda' required style='margin:0; font-size:18px; font-weight:bold; text-align:center; flex:1;'>
                    <button class='btn-acao' style='background:#28a745; margin:0; width:120px;'>ABRIR</button>
                </form>
            </div>
            """
            b += f"<a href='/cadastro' class='btn-acao' style='background:#d31a21'>➕ NOVO CLIENTE / COMANDA</a><a href='/buscar' class='btn-acao' style='background:#062b5e'>🔍 BUSCAR COMANDA (AVANÇADO)</a>"
        if role in ["admin", "gerente", "garcom", "caixa"]:
            b += f"<a href='/fechar_conta' class='btn-acao' style='background:#333'>🔒 FECHAR CONTA</a><a href='/caixa' class='btn-acao' style='background:#e67e22'>💰 GESTÃO DO EVENTO (CAIXA)</a>"
        if role in ["admin", "gerente"]:
            b += "<a href='/comissoes' class='btn-acao' style='background:#8e44ad'>💸 COMISSÕES DE VENDAS</a><a href='/dashboard' class='btn-acao' style='background:#17a2b8'>📊 DASHBOARD GERENCIAL</a><a href='/estoque' class='btn-acao' style='background:#062b5e'>📦 GESTÃO DE ESTOQUE</a><a href='/qr' class='btn-acao' style='background:#f1c40f; color:black;'>📱 QR CODE DO CARDÁPIO</a>"
            b += "<a href='/baixar_conector' class='btn-acao' style='background:#f39c12; color:black;'>📥 BAIXAR CONECTOR DE IMPRESSORA PC</a>"
        if role == "admin":
            b += "<a href='/usuarios' class='btn-acao' style='background:#9b59b6'>👥 GERENCIAR USUÁRIOS</a>"
            
    return f"""<html><head>{CSS}</head><body><div class='container-center'><div class='card-center'>{IMG_LOGO_PEQ}<p>Logado como: <b>{user.upper()}</b></p>{b}<br><a href='/logout' style='color:gray'>Sair</a></div></div></body></html>"""

@app.get("/baixar_conector")
async def baixar_conector(request: Request):
    if request.session.get("role") not in ["admin", "gerente"]: return RedirectResponse(url="/central")
    
    base_url = str(request.base_url).rstrip('/')
    script_content = f"""import time\nimport requests\nimport win32print\n\n# Conector de Impressao - JPMS Gestao\nAPI_URL = "{base_url}"\n\ndef imprimir_ticket(texto):\n    impressora_padrao = win32print.GetDefaultPrinter()\n    try:\n        hPrinter = win32print.OpenPrinter(impressora_padrao)\n        hJob = win32print.StartDocPrinter(hPrinter, 1, ("Ticket JPMS", None, "RAW"))\n        win32print.StartPagePrinter(hPrinter)\n        \n        win32print.WritePrinter(hPrinter, texto.encode("utf-8"))\n        win32print.WritePrinter(hPrinter, b"\\n\\n\\n\\n\\x1B\\x6D")\n        \n        win32print.EndPagePrinter(hPrinter)\n        win32print.EndDocPrinter(hPrinter)\n        win32print.ClosePrinter(hPrinter)\n        print("✔️ Ticket Impresso com Sucesso!")\n    except Exception as e:\n        print(f"❌ Erro na impressora: {{e}}")\n\nprint("=========================================")\nprint("🚀 CONECTOR DE IMPRESSORA JPMS INICIADO")\nprint(f"Conectado em: {{API_URL}}")\nprint("Deixe essa janela aberta para receber tickets...")\nprint("=========================================\\n")\n\nwhile True:\n    try:\n        resposta = requests.get(f"{{API_URL}}/api/pendentes", timeout=5)\n        if resposta.status_code == 200:\n            dados = resposta.json()\n            for job in dados.get("jobs", []):\n                print(f"🖨️ Imprimindo pedido ID {{job['id']}}...")\n                imprimir_ticket(job['conteudo'])\n                requests.post(f"{{API_URL}}/api/impresso/{{job['id']}}", timeout=5)\n    except Exception as e:\n        pass\n    time.sleep(3)\n"""
    return Response(content=script_content, media_type="text/x-python", headers={"Content-Disposition": "attachment; filename=conector_impressao_jpms.py"})

@app.get("/cardapio", response_class=HTMLResponse)
async def cardapio_digital():
    html_cats = ""
    with engine.connect() as conn:
        for cat in IMAGENS_CAT.keys():
            prods = conn.execute(text("SELECT nome, preco, estoque FROM produtos WHERE categoria=:c ORDER BY nome"), {"c": cat}).fetchall()
            if not prods: continue
            itens_html = ""
            for p in prods:
                if p.estoque > 0:
                    itens_html += f"<div class='linha-menu'><div class='linha-nome'>{p.nome}</div><div class='linha-pontos'></div><div class='linha-preco'>R$ {float(p.preco):.2f}</div></div>"
                else:
                    itens_html += f"<div class='linha-menu' style='opacity:0.6;'><div class='linha-nome'><del>{p.nome}</del><span class='esgotado-txt'>ESGOTADO</span></div><div class='linha-pontos'></div><div class='linha-preco'>R$ {float(p.preco):.2f}</div></div>"
            html_cats += f"""
                <div style='margin-bottom: 40px;'>
                    <div style='text-align:center; margin-bottom: -20px; position:relative; z-index:10;'>
                        <div style='background:rgba(255,255,255,0.1); border-radius:50%; width:90px; height:90px; display:inline-flex; align-items:center; justify-content:center; box-shadow:0 4px 10px rgba(0,0,0,0.8); border: 2px solid #e67e22; padding: 10px; backdrop-filter: blur(5px);'>
                            <img src='{IMAGENS_CAT.get(cat, "")}' style='width: 100%; height: 100%; object-fit: contain; filter: drop-shadow(2px 2px 4px rgba(0,0,0,0.8));'>
                        </div>
                    </div>
                    <div style='margin: 0 20px;'>
                        <div class='faixa-laranja'>{cat}</div>
                    </div>
                    <div style='padding: 0 10px; margin-top: 10px;'>
                        {itens_html}
                    </div>
                </div>
            """
    body_style = "background-color: #1a1a1a; background-image: radial-gradient(#333 1px, transparent 1px); background-size: 20px 20px; overflow-y:auto;"
    return f"""<html><head>{CSS}</head><body style='{body_style}'><div style='padding:40px 15px; width:100%; max-width:1100px; margin:auto;'>{IMG_LOGO}<h1 style='text-align:center; color:white; margin-bottom:50px; font-family:\"Arial Black\", sans-serif; letter-spacing: 2px; text-shadow: 2px 2px 4px black;'>CARDÁPIO DIGITAL</h1><div class='menu-duas-colunas'>{html_cats}</div><br><br><p style='text-align:center; color:#666;'>© JPMS - Soluções de Gestão</p></div></body></html>"""

@app.get("/qr", response_class=HTMLResponse)
async def gerar_qr(request: Request):
    if request.session.get("role") not in ["admin", "gerente"]: return RedirectResponse(url="/central")
    link_cardapio = str(request.base_url) + "cardapio"
    return f"""<html><head>{CSS}</head><body><div class='container-center'><div class='card-center'>{IMG_LOGO_PEQ}<h2 style='color:#d31a21;'>QR Code do Cardápio</h2><img src='https://api.qrserver.com/v1/create-qr-code/?size=250x250&data={urllib.parse.quote(link_cardapio)}' style='margin:20px; border:2px solid #ccc; border-radius:10px;'><br><a href='{link_cardapio}' class='btn-acao' style='background:#28a745'>ACESSAR LINK</a><a href='/central' class='btn-acao' style='background:#333'>VOLTAR</a></div></div></body></html>"""

@app.get("/caixa", response_class=HTMLResponse)
async def tela_caixa(request: Request):
    if request.session.get("role") not in ["admin", "gerente", "caixa"]: return RedirectResponse(url="/central")
    
    with engine.connect() as conn:
        turno = conn.execute(text("SELECT id, data_abertura, fundo_inicial FROM turnos WHERE status = 'ABERTO' ORDER BY id DESC LIMIT 1")).fetchone()
        
        if not turno:
            return f"<html><head>{CSS}</head><body><div class='container-center'><div class='card-center'>{IMG_LOGO_PEQ}<div style='background:#f4f4f4; padding:20px; border-radius:10px; border:1px solid #ccc;'><h3 style='color:#d31a21; margin-top:0;'>Iniciar Evento (Abrir Caixa)</h3><form action='/abrir_turno' method='post'><label style='color:#333; font-weight:bold; display:block; text-align:left; margin-bottom:5px;'>Fundo de Caixa Inicial (Dinheiro na Gaveta):</label><input type='number' step='0.01' name='fundo_inicial' class='input-padrao' required placeholder='R$ 0.00' style='font-size:20px; font-weight:bold;'><button class='btn-acao' style='background:#28a745; margin-top:15px; font-size:18px;'>🟢 INICIAR EVENTO</button></form></div><br><a href='/central' style='color:gray'>Voltar ao Menu</a></div></div></body></html>"

        pag_q = conn.execute(text(f"SELECT forma_pagamento, SUM(total_conta) as total FROM comandas WHERE data_fechamento >= :inicio AND status = 'FECHADA' GROUP BY forma_pagamento"), {"inicio": turno.data_abertura}).fetchall()
        totais = {"DINHEIRO": 0.0, "PIX": 0.0, "C. CREDITO": 0.0, "C. DEBITO": 0.0}
        for p in pag_q: totais[p.forma_pagamento] = float(p.total or 0)
        
        mov_q = conn.execute(text(f"SELECT tipo, descricao, valor, TO_CHAR(data_registro, 'HH24:MI') as hora FROM caixa_movimentos WHERE data_registro >= :inicio ORDER BY data_registro DESC"), {"inicio": turno.data_abertura}).fetchall()
        tot_sangria = sum([float(m.valor) for m in mov_q if m.tipo == 'SANGRIA'])
        linhas_mov = "".join([f"<tr><td style='color:black;'>{m.hora}</td><td style='color:black;'>{m.tipo} - {m.descricao}</td><td style='color:#d31a21; font-weight:bold;'>- R$ {float(m.valor):.2f}</td></tr>" for m in mov_q if m.tipo == 'SANGRIA'])
        
    return f"<html><head>{CSS}</head><body><div class='container-center'><div class='card-center' style='max-width:700px;'>{IMG_LOGO_PEQ}<h2>💰 Gestão de Caixa (Evento Atual)</h2><p style='color:#666; font-size:14px; margin-top:-15px;'>Aberto em: {turno.data_abertura.strftime('%d/%m/%Y %H:%M')}</p><div style='display:flex; justify-content:space-between; flex-wrap:wrap; gap:10px; margin-bottom:20px;'><div style='background:#f9f9f9; padding:15px; border-radius:8px; border-left:4px solid #28a745; flex:1; min-width:140px;'><b>💵 Dinheiro Vendas:</b><br><span style='font-size:20px; color:#28a745;'>R$ {totais['DINHEIRO']:.2f}</span></div><div style='background:#f9f9f9; padding:15px; border-radius:8px; border-left:4px solid #17a2b8; flex:1; min-width:140px;'><b>💠 PIX:</b><br><span style='font-size:20px; color:#17a2b8;'>R$ {totais['PIX']:.2f}</span></div><div style='background:#f9f9f9; padding:15px; border-radius:8px; border-left:4px solid #f39c12; flex:1; min-width:140px;'><b>💳 Cartões:</b><br><span style='font-size:20px; color:#f39c12;'>R$ {(totais['C. CREDITO'] + totais['C. DEBITO']):.2f}</span></div></div><div style='background:#f4f4f4; padding:20px; border-radius:10px; text-align:left; border:1px solid #ccc; margin-bottom:20px; display:flex; justify-content:space-between; align-items:center;'><span style='color:#333; font-size:16px; font-weight:bold;'>📥 Fundo de Caixa Inicial:</span><span style='color:#28a745; font-size:20px; font-weight:bold;'>R$ {float(turno.fundo_inicial):.2f}</span></div><div style='background:#f4f4f4; padding:20px; border-radius:10px; text-align:left; border:1px solid #ccc; margin-bottom:20px;'><h3 style='margin-top:0; color:#d31a21;'>🔻 Fazer Sangria (Retirada da Gaveta)</h3><form action='/sangria' method='post' style='display:flex; flex-wrap:wrap; gap:10px;'><input name='valor' type='number' step='0.01' placeholder='Valor R$' class='input-padrao' style='flex:1; min-width:100px;' required><input name='desc' type='text' placeholder='Motivo (Ex: Gelo, Vale)' class='input-padrao' style='flex:2; min-width:180px;' required><button class='btn-acao' style='background:#d31a21; margin:0; width:100px;'>TIRAR</button></form></div><h3 style='text-align:left; margin-bottom:5px;'>Histórico de Retiradas</h3><div style='max-height:150px; overflow-y:auto; border:1px solid #ddd; margin-bottom:20px;'><table><tr><th style='color:#333'>Hora</th><th style='color:#333'>Motivo</th><th style='color:#333'>Valor</th></tr>{linhas_mov if linhas_mov else '<tr><td colspan=3 style=color:black;text-align:center;>Nenhuma retirada.</td></tr>'}</table></div><a href='/caixa_cego' class='btn-acao' style='background:#062b5e; font-size:18px; padding:20px;'>🔒 ENCERRAR EVENTO (BATER CAIXA)</a><br><a href='/central' style='color:gray'>Voltar ao Menu</a></div></div></body></html>"

@app.post("/abrir_turno")
async def abrir_turno(request: Request):
    if request.session.get("role") not in ["admin", "gerente", "caixa"]: return RedirectResponse(url="/central")
    f = await request.form()
    try:
        with engine.begin() as conn:
            conn.execute(text("INSERT INTO turnos (fundo_inicial, usuario_abertura) VALUES (:f, :u)"), {"f": float(f.get("fundo_inicial", "0")), "u": request.session.get("user")})
    except: pass
    return RedirectResponse(url="/central", status_code=303)

@app.post("/sangria")
async def registrar_sangria(request: Request):
    if request.session.get("role") not in ["admin", "gerente", "caixa"]: return RedirectResponse(url="/central")
    f = await request.form()
    try:
        with engine.begin() as conn: conn.execute(text("INSERT INTO caixa_movimentos (tipo, valor, descricao, usuario) VALUES ('SANGRIA', :v, :d, :u)"), {"v": float(f.get("valor", "0")), "d": f.get("desc", ""), "u": request.session.get("user")})
    except: pass
    return RedirectResponse(url="/caixa", status_code=303)

@app.get("/caixa_cego", response_class=HTMLResponse)
async def tela_caixa_cego(request: Request):
    if request.session.get("role") not in ["admin", "gerente", "caixa"]: return RedirectResponse(url="/central")
    return f"<html><head>{CSS}</head><body><div class='container-center'><div class='card-center'>{IMG_LOGO_PEQ}<h2 style='color:#d31a21;'>Fechamento Cego</h2><p style='color:#333;'>Conte as notas da gaveta e digite abaixo o valor total exato do dinheiro físico (incluindo o Fundo Inicial).</p><form action='/resumo_whatsapp' method='post'><input class='input-padrao' name='dinheiro_gaveta' type='number' step='0.01' placeholder='R$ 0.00' required style='font-size:24px; text-align:center; padding:20px; font-weight:bold;'><button class='btn-acao' style='background:#28a745; font-size:18px; margin-top:20px;'>✔️ CONFIRMAR VALOR FÍSICO</button></form><br><a href='/caixa' style='color:gray'>Cancelar</a></div></div></body></html>"

@app.post("/resumo_whatsapp", response_class=HTMLResponse)
async def resumo_whatsapp(request: Request):
    if request.session.get("role") not in ["admin", "gerente", "caixa"]: return RedirectResponse(url="/central")
    f = await request.form()
    gaveta = float(f.get("dinheiro_gaveta", "0"))
    usuario = request.session.get("user", "Desconhecido").upper()
    
    with engine.connect() as conn:
        turno = conn.execute(text("SELECT id, data_abertura, fundo_inicial FROM turnos WHERE status = 'ABERTO' ORDER BY id DESC LIMIT 1")).fetchone()
        if not turno: return RedirectResponse(url="/caixa")
        
        pag_q = conn.execute(text(f"SELECT forma_pagamento, SUM(total_conta) as total, SUM(desconto) as tot_desc FROM comandas WHERE data_fechamento >= :inicio AND status = 'FECHADA' GROUP BY forma_pagamento"), {"inicio": turno.data_abertura}).fetchall()
        totais = {"DINHEIRO": 0.0, "PIX": 0.0, "C. CREDITO": 0.0, "C. DEBITO": 0.0}
        tot_desconto = 0.0
        for p in pag_q: 
            totais[p.forma_pagamento] = float(p.total or 0)
            tot_desconto += float(p.tot_desc or 0)
            
        mov_q = conn.execute(text(f"SELECT SUM(valor) as tot FROM caixa_movimentos WHERE data_registro >= :inicio AND tipo = 'SANGRIA'"), {"inicio": turno.data_abertura}).fetchone()
        tot_sangria = float(mov_q.tot or 0)
        
        comissao_db = conn.execute(text(f"SELECT SUM(valor * 0.10) as tot FROM vendas_itens WHERE data_venda >= DATE(:inicio) AND status = 'FECHADA'"), {"inicio": turno.data_abertura}).fetchone()
        tot_comissao = float(comissao_db.tot or 0)
        
        conn.execute(text("UPDATE turnos SET status = 'FECHADO', data_fechamento = CURRENT_TIMESTAMP, usuario_fechamento = :u WHERE id = :t_id"), {"u": usuario, "t_id": turno.id})
        conn.commit()
        
    fundo_inicial = float(turno.fundo_inicial or 0)
    esperado = totais["DINHEIRO"] + fundo_inicial - tot_sangria
    dif = gaveta - esperado
    faturamento_bruto = sum(totais.values())
    faturamento_liq = faturamento_bruto - tot_comissao
    status_caixa = "✅ Bateu certinho! R$ 0.00" if dif == 0 else f"⚠️ Sobrou na gaveta: R$ {dif:.2f}" if dif > 0 else f"❌ FURO DE CAIXA: R$ {dif:.2f}"
    
    mensagem = f"📊 *FECHAMENTO DE EVENTO/CAIXA*\n*Descontos Totais Concedidos:* R$ {tot_desconto:.2f}\n*Abertura:* {turno.data_abertura.strftime('%d/%m/%Y %H:%M')}\n*Fechamento:* {datetime.now().strftime('%d/%m/%Y %H:%M')}\n*Operador:* {usuario}\n\n*Vendas por Pagamento:*\n💵 Dinheiro: R$ {totais['DINHEIRO']:.2f}\n💳 Cartão: R$ {(totais['C. CREDITO'] + totais['C. DEBITO']):.2f}\n💠 PIX: R$ {totais['PIX']:.2f}\n\n*Movimentações (Gaveta):*\n💵 Fundo Inicial: R$ {fundo_inicial:.2f}\n🔻 Sangrias: R$ {tot_sangria:.2f}\n\n*Auditoria da Gaveta:*\nInformado: R$ {gaveta:.2f}\nDeveria ter: R$ {esperado:.2f}\n*Status:* {status_caixa}\n\n*Resumo Geral:*\n💰 Bruto Vendido: R$ {faturamento_bruto:.2f}\n💸 Comissões: R$ {tot_comissao:.2f}\n✅ *Líquido: R$ {faturamento_liq:.2f}*"
    zap_url = f"https://wa.me/?text={urllib.parse.quote(mensagem)}"
    
    return f"<html><head>{CSS}</head><body><div class='container-center'><div class='card-center' style='max-width:600px;'><h2>Auditoria Concluída & Evento Fechado</h2><div style='background:#f4f4f4; padding:20px; border-radius:8px; text-align:left; color:#333; font-family:monospace; font-size:14px; margin-bottom:20px; white-space:pre-wrap;'>{mensagem.replace('*', '<b>').replace('<b>', '</b>', 1)}</div><a href='{zap_url}' target='_blank' class='btn-acao' style='background:#25D366; font-size:18px; padding:20px;'>📱 ENVIAR RESUMO WHATSAPP</a><br><a href='/central' style='color:gray'>Voltar ao Menu Inicial</a></div></div></body></html>"

@app.get("/dashboard", response_class=HTMLResponse)
async def dashboard(request: Request, inicio: str = "", fim: str = "", cat: str = "", prod: str = "", garcom_filtro: str = ""):
    if request.session.get("role") not in ["admin", "gerente"]: return RedirectResponse(url="/central")
    where_comanda, where_vendas, where_hist, where_prod = "status = 'FECHADA'", "status = 'FECHADA'", "1=1", "1=1"
    params_p, params_v, params_h = {}, {}, {}
    if inicio:
        where_comanda += " AND CAST(data_fechamento AS DATE) >= CAST(:inicio AS DATE)"; where_vendas += " AND CAST(data_venda AS DATE) >= CAST(:inicio AS DATE)"; where_hist += " AND CAST(data_entrada AS DATE) >= CAST(:inicio AS DATE)"; params_p["inicio"] = params_v["inicio"] = params_h["inicio"] = inicio
    if fim:
        where_comanda += " AND CAST(data_fechamento AS DATE) <= CAST(:fim AS DATE)"; where_vendas += " AND CAST(data_venda AS DATE) <= CAST(:fim AS DATE)"; where_hist += " AND CAST(data_entrada AS DATE) <= CAST(:fim AS DATE)"; params_p["fim"] = params_v["fim"] = params_h["fim"] = fim
    
    if garcom_filtro:
        where_vendas += " AND vendas_itens.garcom = :g_filtro"
        params_v["g_filtro"] = garcom_filtro

    join_vendas = ""
    if cat or prod:
        join_vendas = "JOIN produtos p ON vendas_itens.item_nome = p.nome"
        if cat: where_vendas += " AND p.categoria = :cat"; where_prod += " AND p.categoria = :cat"; params_v["cat"] = cat
        if prod:
            prod_str = prod.replace("#", "").strip()
            try: prod_id = int(prod_str); where_vendas += " AND (p.nome ILIKE :prod OR p.id = :prod_id)"; where_prod += " AND (p.nome ILIKE :prod OR p.id = :prod_id)"; where_hist += " AND produto_nome IN (SELECT nome FROM produtos WHERE nome ILIKE :prod OR id = :prod_id)"; params_v["prod_id"] = params_h["prod_id"] = prod_id
            except ValueError: where_vendas += " AND p.nome ILIKE :prod"; where_prod += " AND p.nome ILIKE :prod"; where_hist += " AND produto_nome ILIKE :prod"
            params_v["prod"] = params_h["prod"] = f"%{prod_str}%"
            
    with engine.connect() as conn:
        categorias_db = conn.execute(text("SELECT DISTINCT categoria FROM produtos WHERE categoria IS NOT NULL")).fetchall()
        opcoes_cat = "".join([f"<option value='{c.categoria}' {'selected' if cat == c.categoria else ''}>{c.categoria}</option>" for c in categorias_db])
        
        garcons_lista = conn.execute(text("SELECT DISTINCT garcom FROM vendas_itens WHERE garcom IS NOT NULL")).fetchall()
        opcoes_garcom = "".join([f"<option value='{g.garcom}' {'selected' if garcom_filtro == g.garcom else ''}>{g.garcom}</option>" for g in garcons_lista])
        
        kpi = conn.execute(text(f"SELECT SUM(total_conta) as total, AVG(total_conta) as media FROM comandas WHERE {where_comanda}"), params_p).fetchone()
        faturamento_bruto = float(kpi.total or 0); ticket_medio = float(kpi.media or 0)
        comissao_db = conn.execute(text(f"SELECT SUM(valor * 0.10) as comissao_total FROM vendas_itens {join_vendas} WHERE {where_vendas} AND comissao_status = 'PAGA'"), params_v).fetchone()
        comissoes_pagas = float(comissao_db.comissao_total or 0); faturamento_liquido = faturamento_bruto - comissoes_pagas
        pagamentos = conn.execute(text(f"SELECT forma_pagamento, COUNT(*) as qtd FROM comandas WHERE {where_comanda} GROUP BY forma_pagamento"), params_p).fetchall()
        labels_pag, data_pag = [r.forma_pagamento or "N/D" for r in pagamentos], [r.qtd for r in pagamentos]
        
        top_qtd_db = conn.execute(text(f"SELECT item_nome, COUNT(*) as qtd FROM vendas_itens {join_vendas} WHERE {where_vendas} GROUP BY item_nome ORDER BY qtd DESC LIMIT 3"), params_v).fetchall()
        html_top_qtd = "".join([f"<div class='item-linha' style='color:#333; padding: 8px 0;'><span><b>{i+1}º</b> {r.item_nome}</span><b style='color:#062b5e;'>{r.qtd} un</b></div>" for i, r in enumerate(top_qtd_db)])
        
        top_valor_db = conn.execute(text(f"SELECT item_nome, SUM(valor) as total FROM vendas_itens {join_vendas} WHERE {where_vendas} GROUP BY item_nome ORDER BY total DESC LIMIT 3"), params_v).fetchall()
        html_top_valor = "".join([f"<div class='item-linha' style='color:#333; padding: 8px 0;'><span><b>{i+1}º</b> {r.item_nome}</span><b style='color:#28a745;'>R$ {float(r.total):.2f}</b></div>" for i, r in enumerate(top_valor_db)])
        
        rank_func_db = conn.execute(text(f"SELECT garcom, COUNT(*) as qtd, SUM(valor) as total FROM vendas_itens {join_vendas} WHERE {where_vendas} GROUP BY garcom ORDER BY total DESC"), params_v).fetchall()
        html_rank_func = "".join([f"<tr><td style='color:#333;'><b>{i+1}º</b> {r.garcom or 'N/D'}</td><td style='color:#062b5e; text-align:center;'>{r.qtd}</td><td style='color:#28a745; text-align:right; font-weight:bold;'>R$ {float(r.total):.2f}</td></tr>" for i, r in enumerate(rank_func_db)])
        
        garcons = rank_func_db
        total_vendas_db = conn.execute(text(f"SELECT COUNT(*) as total_vendido FROM vendas_itens {join_vendas} WHERE {where_vendas}"), params_v).fetchone()
        total_saidas = int(total_vendas_db.total_vendido or 0)
        total_entradas_db = conn.execute(text(f"SELECT SUM(qtd_adicionada) as total_entrou FROM historico_estoque WHERE {where_hist}"), params_h).fetchone()
        total_entradas = int(total_entradas_db.total_entrou or 0)
        query_cruz = f"SELECT p.nome, p.estoque, COUNT(v.id) as vendidos FROM produtos p LEFT JOIN vendas_itens v ON p.nome = v.item_nome AND v.status = 'FECHADA' {'AND CAST(v.data_venda AS DATE) >= CAST(:inicio AS DATE)' if inicio else ''} {'AND CAST(v.data_venda AS DATE) <= CAST(:fim AS DATE)' if fim else ''} WHERE {where_prod} GROUP BY p.nome, p.estoque ORDER BY vendidos DESC LIMIT 10"
        cruzamento = conn.execute(text(query_cruz), params_v).fetchall()
        labels_cruz, data_cruz_vendidos, data_cruz_estoque = [r.nome for r in cruzamento], [r.vendidos for r in cruzamento], [r.estoque for r in cruzamento]
        
    dash_css = """<style>
        .grid-dash { display: grid; grid-template-columns: repeat(auto-fit, minmax(140px, 1fr)); gap: 15px; width: 100%; max-width: 1100px; margin-bottom: 20px; } 
        @media (min-width: 600px) { .grid-dash { grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 20px; } }
        
        .grid-charts { display: grid; grid-template-columns: 1fr; gap: 15px; width: 100%; max-width: 1100px; margin-bottom: 20px; }
        @media (min-width: 800px) { .grid-charts { grid-template-columns: 1fr 1fr; gap: 20px; } }
        
        .card-kpi { background: white; padding: 15px; border-radius: 10px; color: #333; box-shadow: 0 4px 6px rgba(0,0,0,0.1); border-left: 5px solid #d31a21; } 
        .card-kpi h3 { margin: 0; font-size: 13px; color: #666; text-transform: uppercase; } 
        .card-kpi p { margin: 10px 0 0; font-size: 20px; font-weight: bold; color: #0a3a7a; word-wrap: break-word; } 
        @media (min-width: 600px) { .card-kpi p { font-size: 24px; } }
        
        .chart-container { background: white; padding: 15px; border-radius: 10px; width: 100%; box-shadow: 0 4px 6px rgba(0,0,0,0.1); overflow: hidden; box-sizing: border-box; } 
        
        .aba-btn { background: #062b5e; color: white; border: none; padding: 12px 20px; font-size: 14px; font-weight: bold; border-radius: 8px; cursor: pointer; margin-right: 10px; margin-bottom: 10px; transition: 0.3s; } 
        .aba-btn:hover { background: #d31a21; } 
        
        .filtro-bar { background: rgba(255,255,255,0.1); padding: 15px; border-radius: 10px; margin-bottom: 20px; display: flex; flex-wrap: wrap; gap: 10px; align-items: flex-end; border: 1px solid rgba(255,255,255,0.2); width: 100%; box-sizing: border-box; }
        .filtro-item { flex: 1; min-width: 110px; }
        
        .rank-table { width: 100%; border-collapse: collapse; margin-top:10px; font-size: 14px; }
        .rank-table th, .rank-table td { padding: 8px 4px; border-bottom: 1px solid #eee; text-align: left; color: #333;}
        .table-responsive { width: 100%; overflow-x: auto; -webkit-overflow-scrolling: touch; }
    </style>"""
    
    return f"<html><head>{CSS}{dash_css}</head><body><div class='main-area' style='padding: 15px; overflow-x: hidden;'><h1 style='color:white; margin-bottom: 10px; font-size: 24px;'>📊 Dashboard e Gestão</h1><form class='filtro-bar' method='GET'><div class='filtro-item'><label style='font-size:12px;'>De:</label><br><input type='date' name='inicio' value='{inicio}' class='input-padrao' style='margin:0;'></div><div class='filtro-item'><label style='font-size:12px;'>Até:</label><br><input type='date' name='fim' value='{fim}' class='input-padrao' style='margin:0;'></div><div class='filtro-item'><label style='font-size:12px;'>Categoria:</label><br><select name='cat' class='input-padrao' style='margin:0;'><option value=''>TODAS</option>{opcoes_cat}</select></div><div class='filtro-item'><label style='font-size:12px;'>Produto:</label><br><input type='text' name='prod' value='{prod}' class='input-padrao' style='margin:0;'></div><div class='filtro-item'><label style='font-size:12px;'>Funcionário:</label><br><select name='garcom_filtro' class='input-padrao' style='margin:0;'><option value=''>TODOS</option>{opcoes_garcom}</select></div><div class='filtro-item' style='min-width: 100%; display: flex; justify-content: flex-end;'><button class='btn-acao' style='background:#28a745; margin:0; height:45px; width:120px;'>FILTRAR</button></div></form><div style='margin-bottom: 20px;'><button id='btn-fin' class='aba-btn' style='background:#17a2b8' onclick=\"showTab('fin')\">💰 FINANCEIRO</button><button id='btn-est' class='aba-btn' style='opacity:0.6; background:#e67e22; color:#333;' onclick=\"showTab('est')\">📦 ESTOQUE</button></div><div id='tab-fin' style='width: 100%;'><div class='grid-dash'><div class='card-kpi'><h3>Bruto</h3><p>R$ {faturamento_bruto:.2f}</p></div><div class='card-kpi'><h3>Líquido</h3><p style='color:#28a745'>R$ {faturamento_liquido:.2f}</p></div><div class='card-kpi'><h3>Comissões Pagas</h3><p style='color:#8e44ad'>R$ {comissoes_pagas:.2f}</p></div><div class='card-kpi'><h3>Ticket Médio</h3><p>R$ {ticket_medio:.2f}</p></div></div><div class='grid-charts'><div class='chart-container'><h3 style='color:#333; margin-top:0; border-bottom:2px solid #eee; padding-bottom:5px; font-size:16px;'>🏆 Top 3 Mais Vendidos (Qtd)</h3>{html_top_qtd if html_top_qtd else '<p style=\"color:#666;\">Sem dados no período.</p>'}</div><div class='chart-container'><h3 style='color:#333; margin-top:0; border-bottom:2px solid #eee; padding-bottom:5px; font-size:16px;'>💎 Top 3 Lucrativos (R$)</h3>{html_top_valor if html_top_valor else '<p style=\"color:#666;\">Sem dados no período.</p>'}</div></div><div class='chart-container' style='margin-bottom:20px;'><h3 style='color:#333; margin-top:0; border-bottom:2px solid #eee; padding-bottom:5px; font-size:16px;'>👨‍🍳 Ranking de Funcionários</h3><div class='table-responsive' style='max-height: 250px;'><table class='rank-table'><tr><th>Funcionário</th><th style='text-align:center;'>Itens Vendidos</th><th style='text-align:right;'>Faturamento</th></tr>{html_rank_func if html_rank_func else '<tr><td colspan=\"3\" style=\"text-align:center;\">Sem dados de vendas.</td></tr>'}</table></div></div><div class='grid-charts'><div class='chart-container'><h3 style='color:#333; font-size:16px; margin-top:0;'>💰 Pagamentos</h3><div style='position: relative; height: 250px; width: 100%;'><canvas id='chartPag'></canvas></div></div><div class='chart-container'><h3 style='color:#333; font-size:16px; margin-top:0;'>📈 Gráfico de Garçons</h3><div style='position: relative; height: 250px; width: 100%;'><canvas id='chartGarcom'></canvas></div></div></div></div><div id='tab-est' style='display:none; width: 100%;'><div class='grid-dash'><div class='card-kpi'><h3>Entradas</h3><p style='color:#28a745'>+{total_entradas}</p></div><div class='card-kpi'><h3>Saídas</h3><p style='color:#d31a21'>-{total_saidas}</p></div></div><div class='chart-container'><h3 style='color:#333; font-size:16px; margin-top:0;'>🔄 Estoque vs Vendidos</h3><div style='position: relative; height: 300px; width: 100%;'><canvas id='chartCruzamento'></canvas></div></div></div><br><a href='/central' class='btn-acao' style='width: 100%; max-width: 200px; margin: 0 auto; background:#333;'>Voltar</a></div><script>function showTab(tab) {{ document.getElementById('tab-fin').style.display = tab === 'fin' ? 'block' : 'none'; document.getElementById('tab-est').style.display = tab === 'est' ? 'block' : 'none'; document.getElementById('btn-fin').style.opacity = tab === 'fin' ? '1' : '0.6'; document.getElementById('btn-est').style.opacity = tab === 'est' ? '1' : '0.6'; }} new Chart(document.getElementById('chartPag'), {{ type: 'doughnut', data: {{ labels: {json.dumps(labels_pag)}, datasets: [{{ data: {json.dumps(data_pag)}, backgroundColor: ['#0a3a7a', '#d31a21', '#f39c12', '#28a745'] }}] }}, options: {{ maintainAspectRatio: false, responsive: true }} }}); new Chart(document.getElementById('chartGarcom'), {{ type: 'bar', data: {{ labels: {json.dumps([g.garcom or 'N/D' for g in garcons])}, datasets: [{{ label: 'Total (R$)', data: {json.dumps([float(g.total or 0) for g in garcons])}, backgroundColor: '#17a2b8' }}] }}, options: {{ maintainAspectRatio: false, responsive: true }} }}); new Chart(document.getElementById('chartCruzamento'), {{ type: 'bar', data: {{ labels: {json.dumps(labels_cruz)}, datasets: [{{ label: 'Vendidos', data: {json.dumps(data_cruz_vendidos)}, backgroundColor: '#d31a21' }}, {{ label: 'Estoque Físico', data: {json.dumps(data_cruz_estoque)}, backgroundColor: '#0a3a7a' }}] }}, options: {{ maintainAspectRatio: false, responsive: true }} }});</script></body></html>"

@app.get("/estoque", response_class=HTMLResponse)
async def tela_estoque(request: Request):
    if request.session.get("role") not in ["admin", "gerente"]: return RedirectResponse(url="/central")
    linhas, curr_cat = "", ""
    with engine.connect() as conn:
        prods_db = conn.execute(text("SELECT p.id, p.nome, p.categoria, p.preco, p.estoque, MAX(h.data_entrada) as ultima_compra FROM produtos p LEFT JOIN historico_estoque h ON p.nome = h.produto_nome GROUP BY p.id, p.nome, p.categoria, p.preco, p.estoque ORDER BY p.categoria, p.nome")).fetchall()
        for r in prods_db:
            if r.categoria != curr_cat: linhas += f"<tr><td colspan='5' style='background:#082d5e; color:white; font-weight:bold; text-align:center;'>{r.categoria or 'OUTROS'}</td></tr>"; curr_cat = r.categoria
            acoes = f"<div style='display:flex; gap:5px;'><form action='/att_estoque' method='post' style='margin:0; display:flex;'><input type='hidden' name='i' value='{r.nome}'><input type='number' name='q' class='input-padrao' style='width:50px; padding:5px;' required><button class='btn-acao' style='background:#28a745; padding:8px;'>➕</button></form><form action='/excluir_produto' method='post' style='margin:0;' onsubmit='return confirm(\"Excluir?\");'><input type='hidden' name='nome' value='{r.nome}'><button class='btn-acao' style='background:#d31a21; padding:8px;'>🗑️</button></form></div>"
            linhas += f"<tr><td style='color:#d31a21;'>{r.id:03d}</td><td style='color:#333;'>{r.nome} <br><small>R$ {float(r.preco or 0):.2f}</small></td><td style='color:#062b5e; font-size:12px;'>{(r.ultima_compra.strftime('%d/%m/%Y') if r.ultima_compra else 'N/A')}</td><td style='color:#333; font-weight:bold; font-size:18px;'>{int(r.estoque or 0)}</td><td>{acoes}</td></tr>"
    add_form = f"<div style='background:#f4f4f4; padding:20px; border-radius:10px; margin-bottom:20px; text-align:left; border:1px solid #ccc;'><h3 style='margin-top:0; color:#d31a21;'>➕ NOVO PRODUTO</h3><form action='/novo_produto' method='post' style='display:flex; flex-wrap:wrap; gap:10px;'><input name='nome' placeholder='Produto' class='input-padrao' style='flex:1;' required><select name='cat' class='input-padrao' style='flex:1;' required><option value='CHOPP'>CHOPP</option><option value='CERVEJAS'>CERVEJAS</option><option value='PETISCOS'>PETISCOS</option><option value='BEBIDAS'>BEBIDAS</option><option value='OUTROS'>OUTROS</option></select><input name='preco' placeholder='Preço' class='input-padrao' style='width:80px;' required><input name='qtd' type='number' placeholder='Qtd' class='input-padrao' style='width:80px;' required><button class='btn-acao' style='background:#062b5e; width:100%;'>SALVAR</button></form></div>"
    return f"<html><head>{CSS}</head><body><div class='container-center'><div class='card-center'><h2>Estoque</h2>{add_form}<div style='max-height:400px; overflow-y:auto; border:1px solid #ccc;'><table><tr><th style='color:#333'>Cód</th><th style='color:#333'>Item</th><th style='color:#333'>Compra</th><th style='color:#333'>Qtd</th><th style='color:#333'>Ação</th></tr>{linhas}</table></div><br><a href='/central' style='color:gray'>Voltar</a></div></div></body></html>"

@app.post("/novo_produto")
async def novo_produto(request: Request):
    f = await request.form()
    try:
        with engine.begin() as conn: 
            conn.execute(text("INSERT INTO produtos (nome, categoria, preco, estoque) VALUES (:n, :c, :p, :q) ON CONFLICT (nome) DO NOTHING"), {"n": f.get("nome"), "c": f.get("cat"), "p": float(f.get("preco").replace(",", ".")), "q": int(f.get("qtd"))})
            conn.execute(text("INSERT INTO historico_estoque (produto_nome, qtd_adicionada) VALUES (:n, :q)"), {"n": f.get("nome"), "q": int(f.get("qtd"))})
    except: pass
    return RedirectResponse(url="/estoque", status_code=303)

@app.post("/att_estoque")
async def att_estoque(request: Request):
    f = await request.form()
    try:
        with engine.begin() as conn: 
            conn.execute(text("UPDATE produtos SET estoque = COALESCE(estoque, 0) + :q WHERE nome = :i"), {"i": f.get("i"), "q": int(f.get("q", "0"))})
            conn.execute(text("INSERT INTO historico_estoque (produto_nome, qtd_adicionada) VALUES (:i, :q)"), {"i": f.get("i"), "q": int(f.get("q", "0"))})
    except: pass
    return RedirectResponse(url="/estoque", status_code=303)

@app.post("/excluir_produto")
async def excluir_produto(request: Request):
    f = await request.form()
    try:
        with engine.begin() as conn: conn.execute(text("DELETE FROM produtos WHERE nome = :n"), {"n": f.get("nome", "")})
    except: pass
    return RedirectResponse(url="/estoque", status_code=303)

@app.get("/comissoes", response_class=HTMLResponse)
async def tela_comissoes(request: Request, garcom_filtro: str = ""):
    if request.session.get("role") not in ["admin", "gerente"]: return RedirectResponse(url="/central")
    linhas_pendentes, linhas_pagas = "", ""
    with engine.connect() as conn:
        garcons_db = conn.execute(text("SELECT DISTINCT garcom FROM vendas_itens WHERE garcom IS NOT NULL ORDER BY garcom")).fetchall()
        opcoes_garcom = "".join([f"<option value='{g.garcom}' {'selected' if garcom_filtro == g.garcom else ''}>{g.garcom}</option>" for g in garcons_db])
        where_clause = "status = 'FECHADA' AND comissao_status = 'PENDENTE'"
        params = {}
        if garcom_filtro:
            where_clause += " AND garcom = :g"
            params["g"] = garcom_filtro
        res_pend = conn.execute(text(f"SELECT CAST(data_venda AS DATE) as data, garcom, SUM(valor) as total_vendido, (SUM(valor) * 0.10) as comissao FROM vendas_itens WHERE {where_clause} GROUP BY CAST(data_venda AS DATE), garcom ORDER BY data DESC"), params).fetchall()
        for r in res_pend:
            linhas_pendentes += f"<tr><td style='color:#333;'>{r.garcom}</td><td style='color:#062b5e;'>{r.data.strftime('%d/%m/%Y')}</td><td style='color:#333;'>R$ {float(r.total_vendido):.2f}</td><td style='color:#d31a21; font-weight:bold;'>R$ {float(r.comissao):.2f}</td><td><form action='/pagar_comissao' method='post' style='margin:0;'><input type='hidden' name='data_venda' value='{r.data}'><input type='hidden' name='garcom' value='{r.garcom}'><button class='btn-acao' style='background:#28a745; padding:8px; font-size:12px;'>✔️ PAGO</button></form></td></tr>"
        where_clause_pagas = "status = 'FECHADA' AND comissao_status = 'PAGA'"
        if garcom_filtro: where_clause_pagas += " AND garcom = :g"
        res_pagas = conn.execute(text(f"SELECT CAST(data_venda AS DATE) as data, garcom, SUM(valor) as total_vendido, (SUM(valor) * 0.10) as comissao FROM vendas_itens WHERE {where_clause_pagas} GROUP BY CAST(data_venda AS DATE), garcom ORDER BY data DESC LIMIT 30"), params).fetchall()
        for r in res_pagas:
            linhas_pagas += f"<tr><td style='color:#333;'>{r.garcom}</td><td style='color:#062b5e;'>{r.data.strftime('%d/%m/%Y')}</td><td style='color:#333;'>R$ {float(r.total_vendido):.2f}</td><td style='color:#28a745; font-weight:bold;'>R$ {float(r.comissao):.2f}</td><td><span style='color:#28a745;'>PAGO</span></td></tr>"
    return f"<html><head>{CSS}</head><body><div class='container-center'><div class='card-center' style='max-width:800px;'><h2>💸 Gestão de Comissões</h2><form method='GET' style='margin-bottom:20px; display:flex; gap:10px;'><select name='garcom_filtro' class='input-padrao' style='flex:1;'><option value=''>Todos</option>{opcoes_garcom}</select><button class='btn-acao' style='background:#062b5e; width:120px;'>FILTRAR</button></form><h3 style='color:#d31a21; text-align:left; border-bottom:2px solid #ccc;'>🔴 Pendentes</h3><div style='max-height:300px; overflow-y:auto; border:1px solid #ccc; margin-bottom:20px;'><table><tr><th style='color:#333'>Func.</th><th style='color:#333'>Data</th><th style='color:#333'>Vendido</th><th style='color:#333'>Comissão</th><th style='color:#333'>Ação</th></tr>{linhas_pendentes if linhas_pendentes else '<tr><td colspan=5 style=color:#666;text-align:center;>Nada pendente.</td></tr>'}</table></div><h3 style='color:#28a745; text-align:left; border-bottom:2px solid #ccc;'>🟢 Pagos</h3><div style='max-height:300px; overflow-y:auto; border:1px solid #ccc;'><table><tr><th style='color:#333'>Func.</th><th style='color:#333'>Data</th><th style='color:#333'>Vendido</th><th style='color:#333'>Comissão</th><th style='color:#333'>Status</th></tr>{linhas_pagas if linhas_pagas else '<tr><td colspan=5 style=color:#666;text-align:center;>Sem histórico.</td></tr>'}</table></div><br><a href='/central' class='btn-acao' style='width: 200px; margin:auto; background:#333;'>Voltar</a></div></div></body></html>"

@app.post("/pagar_comissao")
async def pagar_comissao(request: Request):
    f = await request.form()
    try:
        with engine.begin() as conn: conn.execute(text("UPDATE vendas_itens SET comissao_status = 'PAGA' WHERE CAST(data_venda AS DATE) = CAST(:d AS DATE) AND garcom = :g AND status = 'FECHADA' AND comissao_status = 'PENDENTE'"), {"d": f.get("data_venda"), "g": f.get("garcom")})
    except: pass
    return RedirectResponse(url="/comissoes", status_code=303)

@app.get("/usuarios", response_class=HTMLResponse)
async def tela_usuarios(request: Request):
    if request.session.get("role") != "admin": return RedirectResponse(url="/central")
    linhas = ""
    with engine.connect() as conn:
        users_db = conn.execute(text("SELECT id, username, role FROM usuarios ORDER BY role, username")).fetchall()
        for r in users_db:
            acoes = f"<form action='/excluir_usuario' method='post' style='margin:0;' onsubmit='return confirm(\"Excluir?\");'><input type='hidden' name='id' value='{r.id}'><button class='btn-acao' style='background:#d31a21; padding:8px; width:auto;'>🗑️</button></form>" if r.username != "admin" else ""
            linhas += f"<tr><td style='color:#333; font-weight:bold;'>{r.username.upper()}</td><td style='color:#062b5e;'>{r.role.upper()}</td><td>{acoes}</td></tr>"
    add_form = f"<div style='background:#f4f4f4; padding:20px; border-radius:10px; margin-bottom:20px; text-align:left; border:1px solid #ccc;'><h3 style='margin-top:0; color:#9b59b6;'>➕ NOVO USUÁRIO</h3><form action='/novo_usuario' method='post' style='display:flex; flex-wrap:wrap; gap:10px;'><input name='u' placeholder='Login' class='input-padrao' style='flex:1;' required><input name='p' type='password' placeholder='Senha' class='input-padrao' style='flex:1;' required><select name='r' class='input-padrao' style='flex:1;'><option value='gerente'>GERENTE</option><option value='caixa'>CAIXA</option><option value='garcom'>GARÇOM</option><option value='portaria'>PORTARIA</option></select><button class='btn-acao' style='background:#9b59b6; width:100%;'>CRIAR ACESSO</button></form></div>"
    return f"<html><head>{CSS}</head><body><div class='container-center'><div class='card-center'><h2>Usuários</h2>{add_form}<div style='max-height:400px; overflow-y:auto; border:1px solid #ccc;'><table><tr><th style='color:#333'>Login</th><th style='color:#333'>Cargo</th><th style='color:#333'>Ação</th></tr>{linhas}</table></div><br><a href='/central' style='color:gray'>Voltar</a></div></div></body></html>"

@app.post("/novo_usuario")
async def novo_usuario(request: Request):
    f = await request.form()
    try:
        with engine.begin() as conn: conn.execute(text("INSERT INTO usuarios (username, password, role) VALUES (:u, :p, :r) ON CONFLICT (username) DO NOTHING"), {"u": f.get("u").lower(), "p": f.get("p"), "r": f.get("r")})
    except: pass
    return RedirectResponse(url="/usuarios", status_code=303)

@app.post("/excluir_usuario")
async def excluir_usuario(request: Request):
    f = await request.form()
    try:
        with engine.begin() as conn: conn.execute(text("DELETE FROM usuarios WHERE id = :id AND username != 'admin'"), {"id": f.get("id")})
    except: pass
    return RedirectResponse(url="/usuarios", status_code=303)

@app.get("/vendas", response_class=HTMLResponse)
async def vendas(request: Request, cat: str = "CHOPP", p: str = ""):
    if request.session.get("role") not in ["admin", "gerente", "garcom", "caixa"]: return RedirectResponse(url="/central")
    with engine.connect() as conn:
        if not conn.execute(text("SELECT id FROM turnos WHERE status = 'ABERTO'")).fetchone():
            return HTMLResponse("<script>alert('O Evento está fechado! Inicie o evento no menu principal primeiro.'); window.location.href='/central';</script>")
            
        prods, itens_html = "", ""
        for n, v, e in conn.execute(text("SELECT nome, preco, estoque FROM produtos WHERE categoria = :c ORDER BY nome"), {"c": cat}).fetchall():
            estoque_atual = int(e or 0)
            if estoque_atual > 0:
                cor = 'bg-green'
                txt_estoque = f"<div style='font-size:12px; margin-top:5px; background:rgba(0,0,0,0.4); border-radius:4px; padding:2px;'>📦 Estoque: {estoque_atual}</div>"
            else:
                cor = 'bg-red'
                txt_estoque = f"<div style='font-size:12px; margin-top:5px; background:#d31a21; border-radius:4px; padding:2px; font-weight:bold; color:white;'>⚠️ ESGOTADO</div>"
            prods += f"<div class='prod-card {cor}' onclick='add(\"{n}\", {float(v or 0)}, {estoque_atual})'><b>{n}</b><span>R$ {float(v or 0):.2f}</span>{txt_estoque}</div>"
        if p:
            role = request.session.get("role")
            for r in conn.execute(text("SELECT item_nome, COUNT(*) as qtd, SUM(valor) as tot FROM vendas_itens WHERE comanda_num = :p AND status = 'ABERTA' GROUP BY item_nome"), {"p": p}).fetchall():
                btn_estorno = f"<form action='/estorno' method='post' style='display:inline; margin:0;'><input type='hidden' name='p' value='{p}'><input type='hidden' name='i' value='{r.item_nome}'><button style='background:none;border:none;color:#d31a21;font-weight:bold;cursor:pointer;margin-left:8px;font-size:16px;' title='Estornar 1x'>✖</button></form>" if role in ['admin', 'gerente'] else ""
                itens_html += f"<div class='item-linha'><span style='display:flex;align-items:center;'>{r.qtd}x {r.item_nome} {btn_estorno}</span><span>R$ {float(r.tot or 0):.2f}</span></div>"
    comanda_display = f"""<div class='comanda-header'><div style='font-size:13px;'>MESA / COMANDA:</div><input type='text' id='input-comanda' class='input-padrao' style='text-align:center; font-weight:bold; font-size:20px;' value='{p}'><button class='btn-acao' style='background:white; color:#d31a21;' onclick='window.location.href=\"/vendas?cat={cat}&p=\"+document.getElementById(\"input-comanda\").value'>ACESSAR</button></div><div class='comanda-body'><div class='secao-titulo'>Consumo</div>{itens_html}<hr><div class='secao-titulo'>Novo Pedido</div><div id='novo-pedido'></div></div><div class='comanda-footer'><div style='display:flex; justify-content:space-between; font-weight:bold;'><span>Subtotal:</span><span id='tot-pedido'>R$ 0.00</span></div><br><button class='btn-acao' style='background:#28a745;' onclick='enviarPedido()'>LANÇAR PEDIDO</button><a href='/central' class='btn-acao' style='background:#333'>Voltar</a></div>"""
    botoes_menu = "".join([f"<a href='/vendas?cat={k}&p={p}' class='btn-menu'><span style='background:white; border-radius:50%; width:32px; height:32px; display:inline-flex; align-items:center; justify-content:center; box-shadow: 0 2px 4px rgba(0,0,0,0.5);'><img src='{IMAGENS_CAT.get(k, '')}' style='width:20px; height:20px; object-fit:contain;'></span> {k}</a>" for k in IMAGENS_CAT.keys()])
    return f"""<html><head>{CSS}<script>const c_num = '{p}'; let cart = JSON.parse(sessionStorage.getItem('cart_'+c_num)) || []; function add(n,v,e) {{ if(!c_num) return alert('Acesse uma comanda ou mesa!'); if (e <= 0 || cart.filter(x => x.n === n).length >= e) return alert('❌ Sem estoque!'); cart.push({{n,v}}); sessionStorage.setItem('cart_'+c_num, JSON.stringify(cart)); render(); }} function render() {{ let html = ''; let t = 0; cart.forEach((i,idx) => {{ html += `<div class='item-linha' style='color:#d31a21; font-weight:bold;'><span>${{i.n}}</span><span>R$ ${{i.v.toFixed(2)}} <b onclick='rem(${{idx}})' style='cursor:pointer; color:#333;'>X</b></span></div>`; t += i.v; }}); document.getElementById('novo-pedido').innerHTML = html; document.getElementById('tot-pedido').innerText = 'R$ '+t.toFixed(2); }} function rem(idx) {{ cart.splice(idx,1); sessionStorage.setItem('cart_'+c_num, JSON.stringify(cart)); render(); }} function enviarPedido() {{ if(!c_num || cart.length === 0) return; let f = document.createElement('form'); f.method = 'POST'; f.action = '/lancar_pedido'; let i1 = document.createElement('input'); i1.name = 'p'; i1.value = c_num; f.appendChild(i1); let i2 = document.createElement('input'); i2.name = 'itens'; i2.value = JSON.stringify(cart); f.appendChild(i2); document.body.appendChild(f); sessionStorage.removeItem('cart_'+c_num); f.submit(); }} window.onload = render;</script></head><body><div class='layout-vendas'><div class='menu-lateral'>{botoes_menu}</div><div class='main-area'>{IMG_LOGO}<h2>{cat}</h2><div class='grid-produtos'>{prods}</div></div><div class='comanda-lateral'>{comanda_display}</div></div></body></html>"""

@app.post("/estorno")
async def estornar_item(request: Request):
    if request.session.get("role") not in ["admin", "gerente"]: return RedirectResponse(url="/vendas", status_code=303)
    f = await request.form()
    p, i = f.get("p"), f.get("i")
    try:
        with engine.begin() as conn:
            item = conn.execute(text("SELECT id, valor FROM vendas_itens WHERE comanda_num=:p AND item_nome=:i AND status='ABERTA' LIMIT 1"), {"p": p, "i": i}).fetchone()
            if item:
                conn.execute(text("UPDATE vendas_itens SET status='ESTORNADO' WHERE id=:id"), {"id": item.id})
                conn.execute(text("UPDATE comandas SET total_conta = total_conta - :v WHERE numero_comanda=:p AND status='ABERTA'"), {"v": item.valor, "p": p})
                conn.execute(text("UPDATE produtos SET estoque = estoque + 1 WHERE nome=:n"), {"n": i})
    except: pass
    return RedirectResponse(url=f"/vendas?p={p}", status_code=303)

@app.post("/lancar_pedido")
async def lancar_pedido(request: Request):
    f = await request.form()
    p, itens, u = f.get("p"), json.loads(f.get("itens", "[]")), request.session.get("user")
    tot = sum(i['v'] for i in itens)
    try:
        with engine.begin() as conn:
            conn.execute(text("UPDATE comandas SET total_conta = total_conta + :t WHERE numero_comanda = :p AND status = 'ABERTA'"), {"t": tot, "p": p})
            txt = f"--------------------------------\n      TICKET DE PREPARO\nSISTEMA JPMS\nCOMANDA/MESA: {p}\nATENDENTE: {u}\n--------------------------------\n"
            for i in itens:
                conn.execute(text("INSERT INTO vendas_itens (comanda_num, item_nome, valor, garcom) VALUES (:p, :n, :v, :g)"), {"p": p, "n": i['n'], "v": i['v'], "g": u})
                conn.execute(text("UPDATE produtos SET estoque = GREATEST(estoque - 1, 0) WHERE nome = :n"), {"n": i['n']})
                txt += f"1x {i['n']} - R$ {i['v']:.2f}\n"
            txt += "--------------------------------\n"
            conn.execute(text("INSERT INTO fila_impressao (conteudo) VALUES (:txt)"), {"txt": txt})
    except: pass
    return RedirectResponse(url=f"/vendas?p={p}", status_code=303)

@app.get("/fechar_conta", response_class=HTMLResponse)
async def fechar_conta(request: Request, q: str = ""):
    if request.session.get("role") not in ["admin", "gerente", "garcom", "caixa"]: return RedirectResponse(url="/central")
    res = ""
    with engine.connect() as conn:
        if not conn.execute(text("SELECT id FROM turnos WHERE status = 'ABERTO'")).fetchone():
            return HTMLResponse("<script>alert('O Evento está fechado! Inicie o evento no menu principal primeiro.'); window.location.href='/central';</script>")
            
        if q:
            query = conn.execute(text("SELECT p.numero_comanda, p.total_conta, c.nome_completo, c.cpf FROM comandas p JOIN clientes c ON p.cliente_cpf = c.cpf WHERE (p.numero_comanda = :q OR c.cpf = :q) AND p.status = 'ABERTA'"), {"q": q.strip()}).fetchone()
            if query:
                itens_q = conn.execute(text("SELECT item_nome, COUNT(*) as qtd, SUM(valor) as tot FROM vendas_itens WHERE comanda_num = :p AND status = 'ABERTA' GROUP BY item_nome"), {"p": query.numero_comanda}).fetchall()
                lista = "".join([f"<div class='item-linha'><span>{i.qtd}x {i.item_nome}</span><span>R$ {float(i.tot or 0):.2f}</span></div>" for i in itens_q])
                subt = float(query.total_conta or 0)
                taxa = subt * 0.10
                tot_final = subt + taxa
                form_parcial = f"""
                <div style='background:#ffeaa7; padding:15px; border-radius:8px; margin-top:15px; border:1px solid #fdcb6e;'>
                    <h4 style='margin-top:0; color:#d35400; border-bottom:1px solid #fdcb6e; padding-bottom:5px;'>💸 Pagamento Parcial (Rachar a Conta)</h4>
                    <form action='/parcial' method='post' style='display:flex; flex-wrap:wrap; gap:10px; align-items:center; margin:0;'>
                        <input type='hidden' name='p' value='{query.numero_comanda}'>
                        <input type='hidden' name='cpf' value='{query.cpf}'>
                        <input type='number' step='0.01' name='val' max='{tot_final}' class='input-padrao' placeholder='R$ Valor' required style='flex:1; min-width:80px; margin:0;'>
                        <select name='pg' class='input-padrao' style='flex:1; min-width:110px; margin:0;'>
                            <option value='DINHEIRO'>DINHEIRO</option><option value='PIX'>PIX</option><option value='C. CREDITO'>C. CREDITO</option><option value='C. DEBITO'>C. DEBITO</option>
                        </select>
                        <button class='btn-acao' style='background:#d35400; margin:0; flex:1; min-width:100px;'>RECEBER</button>
                    </form>
                </div>
                """
                res = f"""<div style='background:#f4f4f4; padding:20px; border-radius:10px; color:#333; margin-top:20px; text-align:left;'>
                    <h3 style='text-align:center; margin-top:0;'>{query.nome_completo}</h3><p style='text-align:center;'>Comanda/Mesa: <b>{query.numero_comanda}</b></p>
                    <div style='background:white; padding:15px; border-radius:8px; max-height:220px; overflow-y:auto; border:1px solid #ccc;'>{lista}</div>
                    <div style='padding-top:15px; font-size:16px;'>
                        <div class='item-linha'><span>Saldo Devedor S/ Tx:</span><span>R$ {subt:.2f}</span></div>
                        <div class='item-linha'><span>Serviço (10%):</span><span>R$ {taxa:.2f}</span></div>
                        <div class='item-linha' style='color:#062b5e;'><span>Desconto (R$):</span><input type='number' id='input_desconto' value='0' min='0' step='0.01' style='width:70px; padding:5px;' oninput='calcDiv()'></div>
                        <div class='item-linha' style='font-weight:bold; font-size:20px; color:#d31a21;'><span>RESTANTE A PAGAR:</span><span id='tot_final'>R$ {tot_final:.2f}</span></div>
                        <div class='item-linha'><span>Dividir por:</span><input type='number' id='divisores' value='1' min='1' style='width:60px; text-align:center; padding:5px;' oninput='calcDiv()'></div>
                        <div class='item-linha' style='font-weight:bold; font-size:18px;'><span>Por Pessoa:</span><span id='val_pessoa'>R$ {tot_final:.2f}</span></div>
                        <div class='item-linha'><span>Pagamento:</span><select id='select_pag' class='input-padrao' style='width:auto;' onchange='document.getElementById("input_pag_form").value = this.value'><option value='DINHEIRO'>DINHEIRO</option><option value='PIX'>PIX</option><option value='C. CREDITO'>C. CREDITO</option><option value='C. DEBITO'>C. DEBITO</option></select></div>
                    </div>
                    {form_parcial}
                    <form action='/confirmar_fechamento' method='post'>
                        <input type='hidden' name='p' value='{query.numero_comanda}'><input type='hidden' name='divisao' id='input_div' value='1'><input type='hidden' name='desconto' id='input_desc_form' value='0'><input type='hidden' name='pagamento' id='input_pag_form' value='DINHEIRO'>
                        <div style='background:#e9ecef; padding:15px; border-radius:8px; margin-top:15px; border:1px solid #ccc;'>
                            <div style='display:flex; align-items:center; justify-content:space-between; margin-bottom:10px;'><span style='font-weight:bold; color:#28a745;'>🧾 Emitir Nota Fiscal (NFC-e)?</span><label class='switch'><input type='checkbox' name='nfe' onchange='document.getElementById("box-cpf").style.display = this.checked ? "block" : "none"'><span class='slider'></span></label></div>
                            <div id='box-cpf' style='display:none;'><span style='font-size:12px; color:#666;'>CPF:</span><input class='input-padrao' name='cpf_nota' value='{query.cpf}'></div>
                        </div>
                        <button class='btn-acao' style='background:#28a745; font-size:18px; margin-top:15px;'>🖨️ ZERAR CONTA E IMPRIMIR</button>
                    </form>
                    <script>function calcDiv() {{ let subt = {subt}; let taxa = {taxa}; let desc = parseFloat(document.getElementById('input_desconto').value.replace(',', '.')) || 0; let div = parseInt(document.getElementById('divisores').value) || 1; let totFinal = Math.max(subt + taxa - desc, 0); document.getElementById('tot_final').innerText = 'R$ ' + totFinal.toFixed(2); document.getElementById('val_pessoa').innerText = 'R$ ' + (totFinal / div).toFixed(2); document.getElementById('input_div').value = div; document.getElementById('input_desc_form').value = desc; }}</script>
                </div>"""
    return f"<html><head>{CSS}</head><body><div class='container-center'><div class='card-center'>{IMG_LOGO_PEQ}<h2>Fechar Conta</h2><form method='get'><input class='input-padrao' name='q' placeholder='CPF ou Nº Comanda/Mesa' value='{q}' required><button class='btn-acao'>CONSULTAR CONTA</button></form>{res}<br><a href='/central' style='color:gray'>Voltar</a></div></div></body></html>"

@app.post("/parcial")
async def registrar_parcial(request: Request):
    if request.session.get("role") not in ["admin", "gerente", "garcom", "caixa"]: return RedirectResponse(url="/central", status_code=303)
    f = await request.form()
    p, cpf, val, pg = f.get("p"), f.get("cpf"), float(f.get("val", 0)), f.get("pg")
    if val <= 0: return RedirectResponse(url=f"/fechar_conta?q={p}", status_code=303)
    tag = datetime.now().strftime("%H%M%S")
    valor_real_abatido = val / 1.10
    try:
        with engine.begin() as conn:
            conn.execute(text("UPDATE comandas SET total_conta = total_conta - :v WHERE numero_comanda=:p AND status='ABERTA'"), {"v": valor_real_abatido, "p": p})
            conn.execute(text("INSERT INTO comandas (numero_comanda, cliente_cpf, total_conta, status, forma_pagamento, data_fechamento) VALUES (:p_dummy, :c, :v, 'FECHADA', :pg, CURRENT_TIMESTAMP)"), {"p_dummy": f"{p}-PARC{tag}", "c": cpf, "v": valor_real_abatido, "pg": pg})
            txt = f"--------------------------------\n      SISTEMA JPMS\n  PAGAMENTO PARCIAL\nCOMANDA/MESA: {p}\nVALOR PAGO: R$ {val:.2f}\nPAGTO: {pg}\n--------------------------------\n"
            conn.execute(text("INSERT INTO fila_impressao (conteudo) VALUES (:t)"), {"t": txt})
    except: pass
    return RedirectResponse(url=f"/fechar_conta?q={p}", status_code=303)

@app.post("/confirmar_fechamento")
async def confirmar_fechamento(request: Request):
    f = await request.form()
    p, pag, nfe, cpf, desc = f.get("p"), f.get("pagamento"), f.get("nfe"), f.get("cpf_nota"), float(f.get("desconto", "0"))
    try:
        with engine.begin() as conn: 
            c = conn.execute(text("SELECT c.nome_completo, p.total_conta FROM comandas p JOIN clientes c ON p.cliente_cpf = c.cpf WHERE p.numero_comanda = :p AND p.status = 'ABERTA'"), {"p": p}).fetchone()
            if c:
                conn.execute(text("UPDATE comandas SET status = 'FECHADA', forma_pagamento = :pag, data_fechamento = CURRENT_TIMESTAMP, nfe_solicitada = :nfe, cpf_nota = :cpf, desconto = :desc WHERE numero_comanda = :p AND status = 'ABERTA'"), {"p": p, "pag": pag, "nfe": bool(nfe), "cpf": cpf, "desc": desc})
                conn.execute(text("UPDATE vendas_itens SET status = 'FECHADA' WHERE comanda_num = :p AND status = 'ABERTA'"), {"p": p})
                tot = (float(c.total_conta) * 1.1) - desc
                txt = f"--------------------------------\n      SISTEMA JPMS\nFECHAMENTO DE CONTA\nCOMANDA/MESA: {p}\nTOTAL: R$ {tot:.2f}\nPAGTO: {pag}\n--------------------------------\n"
                if nfe: txt += f"NFC-e SOLICITADA\nCPF: {cpf}\n--------------------------------\n"
                conn.execute(text("INSERT INTO fila_impressao (conteudo) VALUES (:t)"), {"t": txt})
    except: pass
    return RedirectResponse(url="/central", status_code=303)

@app.get("/buscar", response_class=HTMLResponse)
async def tela_busca(q: str = ""):
    with engine.connect() as conn:
        if not conn.execute(text("SELECT id FROM turnos WHERE status = 'ABERTO'")).fetchone():
            return HTMLResponse("<script>alert('O Evento está fechado! Inicie o evento no menu principal primeiro.'); window.location.href='/central';</script>")
            
    res = ""
    if q:
        with engine.connect() as conn:
            for r in conn.execute(text("SELECT nome_completo, cpf FROM clientes WHERE nome_completo ILIKE :q OR cpf LIKE :q"), {"q": f"%{q}%"}).fetchall():
                res += f"<tr><td style='color:#333'>{r.nome_completo}</td><td><form action='/abrir' method='post' style='display:flex;gap:5px'><input type='hidden' name='cpf' value='{r.cpf}'><input class='input-padrao' name='p' placeholder='Nº' required style='width:60px;margin:0'><button class='btn-acao' style='background:#d31a21;padding:8px;margin:0'>ABRIR</button></form></td></tr>"
    return f"<html><head>{CSS}</head><body><div class='container-center'><div class='card-center'>{IMG_LOGO_PEQ}<h2>Buscar Cliente / Comanda</h2><form method='get'><input class='input-padrao' name='q' placeholder='Nome ou CPF' value='{q}'><button class='btn-acao' style='background:#062b5e;'>PESQUISAR</button></form><table>{res}</table><br><a href='/central'>Voltar</a></div></div></body></html>"

@app.post("/abrir")
async def abrir(request: Request):
    f = await request.form()
    cpf, p = f.get("cpf"), f.get("p")
    try:
        with engine.begin() as conn:
            if conn.execute(text("SELECT numero_comanda FROM comandas WHERE cliente_cpf = :c AND status = 'ABERTA'"), {"c": cpf}).fetchone(): return HTMLResponse("<script>alert('Cliente já tem comanda aberta!'); window.history.back();</script>")
            if conn.execute(text("SELECT cliente_cpf FROM comandas WHERE numero_comanda = :p AND status = 'ABERTA'"), {"p": p}).fetchone(): return HTMLResponse("<script>alert('Comanda/Mesa em uso!'); window.history.back();</script>")
            conn.execute(text("INSERT INTO comandas (numero_comanda, cliente_cpf, total_conta, status) VALUES (:p, :c, 0.00, 'ABERTA')"), {"p": p, "c": cpf})
    except: pass
    return RedirectResponse(url=f"/vendas?p={p}", status_code=303)

@app.get("/cadastro", response_class=HTMLResponse)
async def tela_cadastro(): 
    with engine.connect() as conn:
        if not conn.execute(text("SELECT id FROM turnos WHERE status = 'ABERTO'")).fetchone():
            return HTMLResponse("<script>alert('O Evento está fechado! Inicie o evento no menu principal primeiro.'); window.location.href='/central';</script>")
            
    return f"<html><head>{CSS}</head><body><div class='container-center'><div class='card-center'>{IMG_LOGO_PEQ}<h2>Novo Cliente / Mesa</h2><form action='/salvar' method='post'><input class='input-padrao' name='nome' placeholder='Nome Completo' required><input class='input-padrao' name='cpf' placeholder='CPF' required><input class='input-padrao' name='nasc' type='date' required><input class='input-padrao' name='contato' placeholder='WhatsApp' required><input class='input-padrao' name='comanda' placeholder='Nº Comanda/Mesa' required><button class='btn-acao' style='background:#d31a21'>SALVAR E ABRIR</button></form><br><a href='/central'>Voltar</a></div></div></body></html>"

@app.post("/salvar")
async def salvar(request: Request):
    f = await request.form()
    n, c, d, co, p = f.get("nome"), f.get("cpf"), f.get("nasc"), f.get("contato"), f.get("comanda")
    try:
        with engine.begin() as conn:
            conn.execute(text("INSERT INTO clientes (nome_completo, cpf, data_nascimento, contato) VALUES (:n, :c, :d, :co) ON CONFLICT (cpf) DO NOTHING"), {"n":n, "c":c, "d":d, "co":co})
            if conn.execute(text("SELECT numero_comanda FROM comandas WHERE cliente_cpf = :c AND status = 'ABERTA'"), {"c": c}).fetchone(): return HTMLResponse("<script>alert('Cliente já possui comanda aberta!'); window.history.back();</script>")
            if conn.execute(text("SELECT cliente_cpf FROM comandas WHERE numero_comanda = :p AND status = 'ABERTA'"), {"p": p}).fetchone(): return HTMLResponse("<script>alert('Comanda/Mesa em uso por outra pessoa!'); window.history.back();</script>")
            conn.execute(text("INSERT INTO comandas (numero_comanda, cliente_cpf, total_conta, status) VALUES (:p, :c, 0.00, 'ABERTA')"), {"p":p, "c":c})
    except: pass
    return RedirectResponse(url=f"/vendas?p={p}", status_code=303)

@app.get("/logout")
async def logout(request: Request): 
    request.session.clear()
    return RedirectResponse("/")

@app.get("/api/pendentes")
async def api_pendentes():
    with engine.connect() as conn:
        r = conn.execute(text("SELECT id, conteudo FROM fila_impressao WHERE status = 'PENDENTE' LIMIT 1")).fetchone()
        return {"jobs": [{"id": r.id, "conteudo": r.conteudo}]} if r else {"jobs": []}

@app.post("/api/impresso/{j_id}")
async def api_impresso(j_id: int):
    with engine.begin() as conn: conn.execute(text("UPDATE fila_impressao SET status='IMPRESSO' WHERE id=:i"), {"i": j_id})
    return {"ok": True}
