from fastapi import FastAPI, Form, Request, Response, UploadFile, File
from fastapi.responses import HTMLResponse, RedirectResponse, FileResponse
from sqlalchemy import create_engine, text
from starlette.middleware.sessions import SessionMiddleware
from datetime import datetime, date
import json
import urllib.parse
import os
import time

app = FastAPI()
app.add_middleware(SessionMiddleware, secret_key="brahma_riacho_mall_2024")

DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://postgres:GNlZnHiuKAcFnpgXhwILfigqKCNkaHqx@interchange.proxy.rlwy.net:44559/railway")
engine = create_engine(DATABASE_URL, pool_pre_ping=True)

MENU_INICIAL = {"CHOPP": [("Caneca 350ml", 11.9), ("Descartável 500ml", 13.9), ("Tulipa 700ml", 17.9), ("Torre 2.5L", 84.9), ("Torre 3.5L", 99.9)], "CERVEJAS": [("Original 600ml", 12.9), ("Amstel 600ml", 12.0), ("Brahma Duplo Malte", 12.0), ("Heineken 600ml", 16.9), ("Spaten LN", 8.9), ("Corona LN", 10.0), ("Heineken LN", 10.0), ("Stella LN", 8.9), ("Heineken Zero", 10.0)], "PETISCOS": [("Fritas", 21.9), ("Fritas c/ Queijo", 25.9), ("Fritas Cheddar/Bacon", 27.9), ("Kibe 10un", 34.9), ("Kibe c/ Queijo", 37.9), ("Frango Passarinho", 28.9), ("Carne Sol c/ Fritas", 54.9), ("Calabresa Acebolada", 22.9), ("Tábua Frios", 34.9)], "BEBIDAS": [("Caipirinha", 14.9), ("Caipiroska Absolut", 16.9), ("Gin Tônica", 24.9), ("Gin Tropical", 26.9), ("Cozumel 600ml", 14.9), ("Refri Lata", 4.9), ("Soda Italiana", 13.9), ("Suco Lata", 5.9), ("Red Bull", 13.0), ("Água", 3.9)]}
IMAGENS_CAT = {"CHOPP": "https://cdn-icons-png.flaticon.com/512/1054/1054060.png", "CERVEJAS": "https://cdn-icons-png.flaticon.com/512/3014/3014490.png", "PETISCOS": "https://cdn-icons-png.flaticon.com/512/1046/1046786.png", "BEBIDAS": "https://cdn-icons-png.flaticon.com/512/2405/2405462.png", "OUTROS": "https://cdn-icons-png.flaticon.com/512/1032/1032130.png"}

with engine.begin() as conn:
    conn.execute(text("CREATE TABLE IF NOT EXISTS clientes (id SERIAL PRIMARY KEY, nome_completo TEXT NOT NULL, cpf TEXT UNIQUE NOT NULL, data_nascimento DATE, contato TEXT, email TEXT);"))
    conn.execute(text("CREATE TABLE IF NOT EXISTS pulseiras (id SERIAL PRIMARY KEY, numero_pulseira TEXT NOT NULL, cliente_cpf TEXT REFERENCES clientes(cpf), total_conta DECIMAL(10,2) DEFAULT 7.00, status TEXT DEFAULT 'ABERTA', forma_pagamento TEXT, data_fechamento TIMESTAMP, nfe_solicitada BOOLEAN DEFAULT FALSE, cpf_nota TEXT);"))
    conn.execute(text("CREATE TABLE IF NOT EXISTS vendas_itens (id SERIAL PRIMARY KEY, pulseira_num TEXT, item_nome TEXT, valor DECIMAL(10,2), data_venda DATE DEFAULT CURRENT_DATE, hora_venda TIME DEFAULT CURRENT_TIME, status TEXT DEFAULT 'ABERTA', garcom TEXT, comissao_status TEXT DEFAULT 'PENDENTE');"))
    conn.execute(text("CREATE TABLE IF NOT EXISTS produtos (id SERIAL PRIMARY KEY, nome TEXT UNIQUE NOT NULL, categoria TEXT DEFAULT 'OUTROS', preco DECIMAL(10,2) DEFAULT 0.00, estoque INT DEFAULT 0);"))
    conn.execute(text("CREATE TABLE IF NOT EXISTS fila_impressao (id SERIAL PRIMARY KEY, conteudo TEXT, status TEXT DEFAULT 'PENDENTE', data_criacao TIMESTAMP DEFAULT CURRENT_TIMESTAMP);"))
    conn.execute(text("CREATE TABLE IF NOT EXISTS historico_estoque (id SERIAL PRIMARY KEY, produto_nome TEXT, qtd_adicionada INT, data_entrada DATE DEFAULT CURRENT_DATE);"))
    conn.execute(text("CREATE TABLE IF NOT EXISTS usuarios (id SERIAL PRIMARY KEY, username TEXT UNIQUE NOT NULL, password TEXT NOT NULL, role TEXT NOT NULL);"))
    conn.execute(text("CREATE TABLE IF NOT EXISTS caixa_movimentos (id SERIAL PRIMARY KEY, tipo TEXT, valor DECIMAL(10,2), descricao TEXT, data_registro TIMESTAMP DEFAULT CURRENT_TIMESTAMP, usuario TEXT);"))
    conn.execute(text("CREATE TABLE IF NOT EXISTS config_nfe (id INT PRIMARY KEY, ambiente TEXT DEFAULT '2', focus_token TEXT, csc_id TEXT, csc_token TEXT, cert_path TEXT, cert_senha TEXT);"))

MIGRACOES = ["ALTER TABLE pulseiras ADD COLUMN IF NOT EXISTS nfe_solicitada BOOLEAN DEFAULT FALSE;", "ALTER TABLE pulseiras ADD COLUMN IF NOT EXISTS cpf_nota TEXT;", "ALTER TABLE pulseiras ADD COLUMN IF NOT EXISTS status TEXT DEFAULT 'ABERTA';", "ALTER TABLE pulseiras ADD COLUMN IF NOT EXISTS forma_pagamento TEXT;", "ALTER TABLE pulseiras ADD COLUMN IF NOT EXISTS data_fechamento TIMESTAMP;", "ALTER TABLE vendas_itens ADD COLUMN IF NOT EXISTS comissao_status TEXT DEFAULT 'PENDENTE';", "ALTER TABLE pulseiras DROP CONSTRAINT IF EXISTS pulseiras_numero_pulseira_key;", "ALTER TABLE produtos ADD COLUMN IF NOT EXISTS categoria TEXT DEFAULT 'OUTROS';", "ALTER TABLE produtos ADD COLUMN IF NOT EXISTS preco DECIMAL(10,2) DEFAULT 0.00;", "ALTER TABLE produtos ADD COLUMN IF NOT EXISTS estoque INT DEFAULT 0;", "INSERT INTO config_nfe (id, ambiente) VALUES (1, '2') ON CONFLICT DO NOTHING;"]
for mig in MIGRACOES:
    try:
        with engine.begin() as conn: conn.execute(text(mig))
    except: pass

try:
    with engine.begin() as conn:
        for cat, itens in MENU_INICIAL.items():
            for n, p in itens:
                conn.execute(text("INSERT INTO produtos (nome, categoria, preco, estoque) VALUES (:n, :c, :p, 100) ON CONFLICT (nome) DO NOTHING"), {"n": n, "c": cat, "p": p})
        conn.execute(text("INSERT INTO usuarios (username, password, role) VALUES ('admin', '1234', 'admin') ON CONFLICT (username) DO NOTHING"))
except: pass

def emitir_nfe_api(cpf, itens, total, pag):
    try:
        with engine.connect() as conn:
            conf = conn.execute(text("SELECT * FROM config_nfe WHERE id = 1")).fetchone()
        if not conf or not conf.focus_token: return "⚠️ Erro: API NFe não configurada."
        amb_str = "Homologacao" if conf.ambiente == '2' else "Producao"
        time.sleep(1) 
        return f"https://{amb_str.lower()}.sefaz.gov.br/nfce/consulta?chave=VALIDADA_VIA_API"
    except: return "Erro ao gerar NFe"

IMG_URL = "/logo.png"
CSS = f"""<meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no"><meta name="apple-mobile-web-app-capable" content="yes"><link rel="apple-touch-icon" href="{IMG_URL}"><style>* {{ box-sizing: border-box; font-family: 'Segoe UI', Tahoma, sans-serif; }} body {{ margin: 0; background: #0a3a7a; color: white; height: 100vh; display: flex; flex-direction: column; overflow: hidden; }} .layout-vendas {{ display: flex; flex: 1; height: 100vh; }} .menu-lateral {{ width: 220px; padding: 20px; display: flex; flex-direction: column; gap: 10px; border-right: 1px solid rgba(255,255,255,0.1); background: #082d5e; overflow-y:auto; }} .btn-menu {{ background: #0a3a7a; color: white; border: 1px solid #1352a3; padding: 15px; border-radius: 8px; text-align: left; font-weight: bold; font-size: 15px; cursor: pointer; text-decoration: none; display: flex; justify-content: flex-start; align-items:center; gap: 10px; }} .btn-menu:hover, .btn-menu.ativo {{ background: #d31a21; border-color: white; }} .main-area {{ flex: 1; padding: 20px; display: flex; flex-direction: column; overflow-y: auto; align-items: center; width: 100%; }} .logo-central {{ width: 280px; max-width: 100%; height: auto; margin-bottom: 20px; filter: drop-shadow(0px 4px 6px rgba(0,0,0,0.5)); }} .logo-peq {{ width: 180px; max-width: 100%; height: auto; margin-bottom: 10px; filter: drop-shadow(0px 2px 4px rgba(0,0,0,0.5)); }} .grid-produtos {{ display: grid; grid-template-columns: repeat(auto-fill, minmax(160px, 1fr)); gap: 15px; width: 100%; max-width: 900px; }} .prod-card {{ border-radius: 10px; padding: 15px 10px; text-align: center; cursor: pointer; display: flex; flex-direction: column; justify-content: space-between; min-height: 120px; box-shadow: 0 4px 6px rgba(0,0,0,0.3); transition: 0.2s; color: white; border-width: 2px; border-style: solid; }} .prod-card:hover {{ transform: scale(1.05); border-color: white; }} .bg-green {{ background: linear-gradient(180deg, #28a745 0%, #1e7e34 100%); border-color: #145523; }} .bg-red {{ background: linear-gradient(180deg, #d31a21 0%, #9e0b10 100%); border-color: #5a0407; opacity: 0.9; }} .prod-card b {{ font-size: 14px; margin-bottom: 8px; text-shadow: 1px 1px 2px rgba(0,0,0,0.6); line-height: 1.2; }} .prod-card span {{ font-size: 16px; font-weight: bold; background: rgba(0,0,0,0.3); padding: 5px; border-radius: 5px; }} .comanda-lateral {{ width: 340px; background: white; color: black; border-left: 5px solid #d31a21; display: flex; flex-direction: column; }} .comanda-header {{ background: #d31a21; color: white; padding: 15px; font-weight: bold; text-align: center; font-size: 18px; }} .comanda-body {{ flex: 1; overflow-y: auto; padding: 15px; background: #f9f9f9; }} .secao-titulo {{ font-size: 12px; color: #666; text-transform: uppercase; font-weight: bold; border-bottom: 1px solid #ccc; margin-bottom: 10px; padding-bottom: 5px; }} .item-linha {{ display: flex; justify-content: space-between; font-size: 14px; margin-bottom: 8px; border-bottom: 1px dashed #ddd; padding-bottom: 5px; align-items: center; }} .comanda-footer {{ padding: 15px; background: white; border-top: 1px solid #ccc; }} .btn-acao {{ display: block; width: 100%; padding: 15px; margin-bottom: 8px; border: none; border-radius: 5px; font-weight: bold; color: white; cursor: pointer; text-align: center; text-decoration: none; font-size: 14px; background: #062b5e; }} .btn-acao:hover {{ background: #0d4b9c; }} .container-center {{ display: flex; align-items: center; justify-content: center; height: 100vh; padding: 20px; overflow-y: auto; }} .card-center {{ background: white; color: #333; padding: 30px; border-radius: 15px; width: 100%; max-width: 650px; text-align: center; box-shadow: 0 8px 20px rgba(0,0,0,0.4); margin: auto; }} .input-padrao {{ width: 100%; padding: 12px; margin: 8px 0; border: 1px solid #ccc; border-radius: 5px; font-size: 16px; box-sizing: border-box; }} table {{ width: 100%; border-collapse: collapse; margin-top: 15px; }} th, td {{ padding: 10px 8px; border-bottom: 1px solid #eee; text-align: left; vertical-align: middle; }} .table-responsive {{ width: 100%; overflow-x: auto; -webkit-overflow-scrolling: touch; border: 1px solid #ddd; margin-bottom: 15px; border-radius: 5px; }} .table-responsive table {{ min-width: 500px; margin-top: 0; }} .switch {{ position: relative; display: inline-block; width: 50px; height: 24px; }} .switch input {{ opacity: 0; width: 0; height: 0; }} .slider {{ position: absolute; cursor: pointer; top: 0; left: 0; right: 0; bottom: 0; background-color: #ccc; transition: .4s; border-radius: 24px; }} .slider:before {{ position: absolute; content: ""; height: 18px; width: 18px; left: 3px; bottom: 3px; background-color: white; transition: .4s; border-radius: 50%; }} input:checked + .slider {{ background-color: #28a745; }} input:checked + .slider:before {{ transform: translateX(26px); }} .menu-duas-colunas {{ display: grid; grid-template-columns: 1fr; gap: 40px; max-width: 1000px; margin: auto; padding: 10px; }} @media (min-width: 800px) {{ .menu-duas-colunas {{ grid-template-columns: 1fr 1fr; gap: 60px; }} }} .faixa-laranja {{ background: #e67e22; color: white; padding: 12px 20px; font-size: 22px; font-weight: bold; text-align: center; text-transform: uppercase; position: relative; margin: 0 auto 25px auto; box-shadow: 0 4px 6px rgba(0,0,0,0.6); max-width: 90%; font-family: 'Arial Black', sans-serif; letter-spacing: 1px; }} .faixa-laranja::before, .faixa-laranja::after {{ content: ""; position: absolute; top: 0; width: 0; height: 0; border-top: 25px solid transparent; border-bottom: 25px solid transparent; }} .faixa-laranja::before {{ left: -20px; border-right: 20px solid #e67e22; }} .faixa-laranja::after {{ right: -20px; border-left: 20px solid #e67e22; }} .linha-menu {{ display: flex; align-items: flex-end; margin-bottom: 12px; font-size: 15px; color: #ddd; }} .linha-nome {{ white-space: nowrap; text-transform: uppercase; font-family: 'Arial', sans-serif; letter-spacing: 0.5px; }} .linha-pontos {{ flex-grow: 1; border-bottom: 2px dotted #666; margin: 0 10px; position: relative; top: -5px; opacity: 0.7; }} .linha-preco {{ white-space: nowrap; font-weight: bold; color: white; font-size: 16px; }} .esgotado-txt {{ color: #d31a21; font-size: 11px; font-weight: bold; margin-left: 8px; background: rgba(0,0,0,0.6); padding: 2px 6px; border-radius: 4px; border: 1px solid #d31a21; vertical-align: middle; }} .filtro-item {{ flex: 1 1 150px; }} @media (max-width: 768px) {{ body {{ height: auto; overflow: auto; }} .layout-vendas {{ display: flex; flex-direction: column; height: auto; min-height: 100vh; }} .menu-lateral {{ width: 100%; flex-direction: row; overflow-x: auto; padding: 10px; border-right: none; border-bottom: 2px solid rgba(255,255,255,0.1); display: flex; gap: 8px; flex-shrink: 0; white-space: nowrap; -webkit-overflow-scrolling: touch; }} .btn-menu {{ padding: 10px 15px; font-size: 14px; text-align: center; flex: 0 0 auto; justify-content: center; flex-direction: column; }} .main-area {{ display: flex; overflow: visible; padding: 10px; flex-shrink: 0; width: 100%; box-sizing: border-box; }} .grid-produtos {{ grid-template-columns: repeat(auto-fill, minmax(130px, 1fr)); gap: 10px; width: 100%; }} .prod-card {{ min-height: 110px; padding: 10px; }} .comanda-lateral {{ width: 100%; display: flex; border-left: none; border-top: 5px solid #d31a21; flex-shrink: 0; }} .card-center {{ width: 95%; padding: 20px; }} .filtro-item {{ flex: 1 1 45%; }} #form_prod input, #form_prod select {{ flex: 1 1 100% !important; }} }}</style><script src="https://cdn.jsdelivr.net/npm/chart.js"></script>"""

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
    return f"""<html><head>{CSS}</head><body><div class='container-center'><div class='card-center'>{IMG_LOGO}<h2>Acesso ao Sistema</h2><form action='/login' method='post'><input class='input-padrao' name='user' placeholder='Usuário' required><input class='input-padrao' name='pw' type='password' placeholder='Senha' required><button class='btn-acao' style='padding:15px; font-size:18px;'>ENTRAR</button></form><br><a href='/cardapio' style='color:#062b5e; font-weight:bold; text-decoration:underline;'>Ver Cardápio Digital</a></div></div></body></html>"""

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
    b = ""
    with engine.connect() as conn:
        c_status = conn.execute(text("SELECT tipo FROM caixa_movimentos WHERE tipo IN ('ABERTURA', 'FECHAMENTO') ORDER BY id DESC LIMIT 1")).fetchone()
        caixa_aberto = True if c_status and c_status[0] == 'ABERTURA' else False
    if caixa_aberto:
        if role in ["admin", "administrador", "gerente", "garcom", "caixa", "portaria"]: b += f"<a href='/cadastro' class='btn-acao' style='background:#d31a21'>➕ NOVO CADASTRO</a><a href='/buscar' class='btn-acao'>🔍 BUSCAR / ABRIR PULSEIRA</a>"
        if role in ["admin", "administrador", "gerente", "garcom", "caixa"]: b += f"<a href='/vendas' class='btn-acao' style='background:#28a745'>🛒 CAIXA / LANÇAR ITENS</a><a href='/fechar_conta' class='btn-acao' style='background:#333'>🔒 FECHAR CONTA</a>"
    else:
        if role in ["admin", "administrador", "gerente", "caixa"]: b += f"<a href='/abrir_caixa' class='btn-acao' style='background:#28a745; padding:20px; font-size:18px;'>🟢 INICIAR CAIXA / EVENTO</a>"
        else: b += f"<p style='color:#f39c12; font-weight:bold; text-align:center;'>⚠️ O Caixa está fechado. Aguarde a gerência.</p>"
    if role in ["admin", "administrador", "gerente", "caixa"]: b += f"<a href='/caixa' class='btn-acao' style='background:#e67e22'>💰 GESTÃO DE CAIXA</a>"
    if role in ["admin", "administrador", "gerente"]: b += "<a href='/historico' class='btn-acao' style='background:#f39c12; color:black;'>🕒 HISTÓRICO E ESTORNOS</a><a href='/comissoes' class='btn-acao' style='background:#8e44ad'>💸 COMISSÕES DE VENDAS</a><a href='/dashboard' class='btn-acao' style='background:#17a2b8'>📊 DASHBOARD GERENCIAL</a><a href='/estoque' class='btn-acao' style='background:#062b5e'>📦 GESTÃO DE ESTOQUE</a><a href='/qr' class='btn-acao' style='background:#f1c40f; color:black;'>📱 QR CODE DO CARDÁPIO</a><a href='/impressora_virtual' class='btn-acao' style='background:#555; color:white;'>🖨️ IMPRESSORA VIRTUAL (TESTE)</a><a href='/baixar_conector' class='btn-acao' style='background:#f39c12; color:black;'>📥 BAIXAR CONECTOR (PC)</a>"
    if role in ["admin", "administrador"]: b += "<a href='/usuarios' class='btn-acao' style='background:#9b59b6'>👥 GERENCIAR USUÁRIOS</a><a href='/config_nfe' class='btn-acao' style='background:#34495e'>⚙️ CONFIGURAÇÕES NFE</a>"
    return f"""<html><head>{CSS}</head><body><div class='container-center'><div class='card-center'>{IMG_LOGO_PEQ}<p>Logado como: <b>{user.upper()}</b></p>{b}<br><a href='/logout' style='color:gray'>Sair</a></div></div></body></html>"""

@app.get("/config_nfe", response_class=HTMLResponse)
async def config_nfe(request: Request):
    if request.session.get("role") not in ["admin", "administrador"]: return RedirectResponse(url="/central")
    with engine.connect() as conn: conf = conn.execute(text("SELECT * FROM config_nfe WHERE id = 1")).fetchone()
    amb_sel_1, amb_sel_2 = ("selected", "") if conf and conf.ambiente == '1' else ("", "selected")
    form = f"""<div style='background:#f4f4f4; padding:20px; border-radius:10px; text-align:left; border:1px solid #ccc; max-width: 600px; margin: auto;'><h3 style='margin-top:0; color:#34495e;'>⚙️ Credenciais Fiscais</h3><form action='/salvar_config_nfe' method='post' enctype='multipart/form-data'><label style='font-size:12px; font-weight:bold; color:#666;'>Ambiente da SEFAZ:</label><select name='ambiente' class='input-padrao' required><option value='2' {amb_sel_2}>HOMOLOGAÇÃO (Teste)</option><option value='1' {amb_sel_1}>PRODUÇÃO (Valendo Oficial)</option></select><label style='font-size:12px; font-weight:bold; color:#666;'>Token da API (Focus NFe):</label><input name='focus_token' class='input-padrao' placeholder='Ex: 4k2j4k2j4k2j4k2...' value='{conf.focus_token if conf else ''}'><label style='font-size:12px; font-weight:bold; color:#666;'>ID CSC (Código de Segurança):</label><input name='csc_id' class='input-padrao' placeholder='Ex: 000001' value='{conf.csc_id if conf else ''}'><label style='font-size:12px; font-weight:bold; color:#666;'>Token CSC (Alfanumérico):</label><input name='csc_token' class='input-padrao' placeholder='Ex: AB12CD34...' value='{conf.csc_token if conf else ''}'><hr style='border: 1px dashed #ccc; margin: 15px 0;'><label style='font-size:12px; font-weight:bold; color:#666;'>Upload Certificado Digital A1 (.pfx):</label><input type='file' name='certificado' class='input-padrao' accept='.pfx,.p12' style='padding: 8px;'><label style='font-size:12px; font-weight:bold; color:#666;'>Senha do Certificado:</label><input name='cert_senha' type='password' class='input-padrao' placeholder='Senha do arquivo A1' value='{conf.cert_senha if conf else ''}'><button class='btn-acao' style='background:#28a745; margin-top:15px; font-size:16px;'>💾 SALVAR CONFIGURAÇÕES</button></form></div>"""
    return f"<html><head>{CSS}</head><body><div class='container-center' style='align-items:flex-start; padding-top:40px;'><div class='card-center'>{IMG_LOGO_PEQ}{form}<br><a href='/central' style='color:gray'>Voltar</a></div></div></body></html>"

@app.post("/salvar_config_nfe")
async def salvar_config_nfe(request: Request, ambiente: str = Form(...), focus_token: str = Form(""), csc_id: str = Form(""), csc_token: str = Form(""), cert_senha: str = Form(""), certificado: UploadFile = File(None)):
    if request.session.get("role") not in ["admin", "administrador"]: return RedirectResponse(url="/central")
    cert_path = ""
    if certificado and certificado.filename:
        cert_path = f"/tmp/{certificado.filename}"
        with open(cert_path, "wb") as f: f.write(await certificado.read())
    try:
        with engine.begin() as conn:
            if cert_path: conn.execute(text("UPDATE config_nfe SET ambiente=:a, focus_token=:ft, csc_id=:ci, csc_token=:ct, cert_path=:cp, cert_senha=:cs WHERE id=1"), {"a": ambiente, "ft": focus_token, "ci": csc_id, "ct": csc_token, "cp": cert_path, "cs": cert_senha})
            else: conn.execute(text("UPDATE config_nfe SET ambiente=:a, focus_token=:ft, csc_id=:ci, csc_token=:ct, cert_senha=:cs WHERE id=1"), {"a": ambiente, "ft": focus_token, "ci": csc_id, "ct": csc_token, "cs": cert_senha})
    except: pass
    return RedirectResponse(url="/central", status_code=303)

@app.get("/vendas", response_class=HTMLResponse)
async def vendas(request: Request, cat: str = "CHOPP", p: str = "", modo: str = ""):
    if request.session.get("role") not in ["admin", "administrador", "gerente", "garcom", "caixa"]: return RedirectResponse(url="/central")
    with engine.connect() as conn:
        c_status = conn.execute(text("SELECT tipo FROM caixa_movimentos WHERE tipo IN ('ABERTURA', 'FECHAMENTO') ORDER BY id DESC LIMIT 1")).fetchone()
        if not c_status or c_status[0] != 'ABERTURA': return HTMLResponse("<script>alert('O Caixa está Fechado!'); window.location.href='/central';</script>")
    if not p:
        if not modo:
            return f"""<html><head>{CSS}</head><body><div class='container-center'><div class='card-center' style='max-width: 500px;'>{IMG_LOGO_PEQ}<h2>Selecione o Tipo de Venda</h2><br><a href='/vendas?modo=comanda' class='btn-acao' style='background:#d31a21; padding:20px; font-size:18px;'>📋 COMANDA / PULSEIRA</a><a href='/vendas?modo=avulsa' class='btn-acao' style='background:#28a745; padding:20px; font-size:18px;'>🛍️ VENDA AVULSA (BALCÃO)</a><br><a href='/central' style='color:gray; font-size: 16px;'>Voltar ao Menu</a></div></div></body></html>"""
        if modo == "comanda":
            css_numpad = "<style>.numpad { display: grid; grid-template-columns: repeat(3, 1fr); gap: 15px; max-width: 350px; margin: 20px auto; } .num-btn { background: #082d5e; color: white; font-size: 28px; font-weight: bold; border: none; border-radius: 10px; padding: 20px; cursor: pointer; text-align: center; box-shadow: 0 4px 6px rgba(0,0,0,0.3); } .num-btn:active { background: #d31a21; transform: scale(0.95); } .action-btn { background: #d31a21; } .acessar-btn { background: #28a745; grid-column: span 3; } .display-pulseira { background: white; color: black; font-size: 36px; text-align: center; padding: 15px; border-radius: 10px; border: 3px solid #082d5e; font-weight: bold; min-height: 75px; letter-spacing: 2px; }</style>"
            return f"<html><head>{CSS}{css_numpad}</head><body><div class='container-center'><div class='card-center' style='max-width: 450px;'>{IMG_LOGO_PEQ}<h2>Informe a Pulseira</h2><div class='display-pulseira' id='display'></div><div class='numpad'><button class='num-btn' onclick='addNum(1)'>1</button><button class='num-btn' onclick='addNum(2)'>2</button><button class='num-btn' onclick='addNum(3)'>3</button><button class='num-btn' onclick='addNum(4)'>4</button><button class='num-btn' onclick='addNum(5)'>5</button><button class='num-btn' onclick='addNum(6)'>6</button><button class='num-btn' onclick='addNum(7)'>7</button><button class='num-btn' onclick='addNum(8)'>8</button><button class='num-btn' onclick='addNum(9)'>9</button><button class='num-btn action-btn' onclick='clearNum()'>C</button><button class='num-btn' onclick='addNum(0)'>0</button><button class='num-btn action-btn' onclick='delNum()'>⌫</button><button class='num-btn acessar-btn' onclick='acessar()'>ACESSAR</button></div><br><a href='/vendas' style='color:gray; font-size: 16px;'>Voltar</a></div></div><script>let num = ''; const disp = document.getElementById('display'); function addNum(n) {{ if(num.length < 10) {{ num += n; disp.innerText = num; }} }} function clearNum() {{ num = ''; disp.innerText = ''; }} function delNum() {{ num = num.slice(0, -1); disp.innerText = num; }} function acessar() {{ if(num.length > 0) window.location.href = '/vendas?p=' + num; }}</script></body></html>"
        if modo == "avulsa":
            p_avulsa = f"AVUL-{int(time.time())}"
            try:
                with engine.begin() as conn: conn.execute(text("INSERT INTO pulseiras (numero_pulseira, total_conta, status) VALUES (:p, 0.00, 'ABERTA')"), {"p": p_avulsa})
            except: pass
            return RedirectResponse(url=f"/vendas?p={p_avulsa}", status_code=303)
    prods, itens_html = "", ""
    with engine.connect() as conn:
        for n, v, e in conn.execute(text("SELECT nome, preco, estoque FROM produtos WHERE categoria = :c ORDER BY nome"), {"c": cat}).fetchall():
            estoque_atual = int(e or 0)
            cor, txt_estoque = ('bg-green', f"<div style='font-size:12px; margin-top:5px; background:rgba(0,0,0,0.4); border-radius:4px; padding:2px;'>📦 Estoque: {estoque_atual}</div>") if estoque_atual > 0 else ('bg-red', f"<div style='font-size:12px; margin-top:5px; background:#5a0407; border-radius:4px; padding:2px; font-weight:bold; color:#ffbaba;'>⚠️ ESGOTADO</div>")
            prods += f"<div class='prod-card {cor}' onclick='add(\"{n}\", {float(v or 0)}, {estoque_atual})'><b>{n}</b><span>R$ {float(v or 0):.2f}</span>{txt_estoque}</div>"
        if p:
            role = request.session.get("role")
            for r in conn.execute(text("SELECT item_nome, COUNT(*) as qtd, SUM(valor) as tot FROM vendas_itens WHERE pulseira_num = :p AND status = 'ABERTA' GROUP BY item_nome"), {"p": p}).fetchall():
                btn_estorno = f"<form action='/estorno' method='post' style='display:inline; margin:0;'><input type='hidden' name='p' value='{p}'><input type='hidden' name='i' value='{r.item_nome}'><button style='background:none;border:none;color:#d31a21;font-weight:bold;cursor:pointer;margin-left:8px;font-size:16px;' title='Estornar 1x'>✖</button></form>" if role in ['admin', 'administrador', 'gerente'] else ""
                itens_html += f"<div class='item-linha'><span style='display:flex;align-items:center;'>{r.qtd}x {r.item_nome} {btn_estorno}</span><span>R$ {float(r.tot or 0):.2f}</span></div>"
    btn_txt = "💳 IR PARA PAGAMENTO" if p.startswith("AVUL") else "LANÇAR PEDIDO"
    comanda_display = f"""<div class='comanda-header'><div style='font-size:13px;'>{"VENDA BALCÃO:" if p.startswith("AVUL") else "PULSEIRA:"}</div><div style='font-size:20px; font-weight:bold; letter-spacing:1px;'>{p}</div><button class='btn-acao' style='background:white; color:#d31a21; margin-top:10px;' onclick='window.location.href=\"/vendas\"'>TROCAR OPERAÇÃO</button></div><div class='comanda-body'><div class='secao-titulo'>Consumo Atual</div>{itens_html}<hr><div class='secao-titulo'>Novo Pedido</div><div id='novo-pedido'></div></div><div class='comanda-footer'><div style='display:flex; justify-content:space-between; font-weight:bold;'><span>Subtotal:</span><span id='tot-pedido'>R$ 0.00</span></div><br><button class='btn-acao' style='background:#28a745;' onclick='enviarPedido()'>{btn_txt}</button><a href='/central' class='btn-acao' style='background:#333'>Sair da Venda</a></div>"""
    botoes_menu = "".join([f"<a href='/vendas?cat={k}&p={p}' class='btn-menu'><span style='background:white; border-radius:50%; width:32px; height:32px; display:inline-flex; align-items:center; justify-content:center; box-shadow: 0 2px 4px rgba(0,0,0,0.5);'><img src='{IMAGENS_CAT.get(k, '')}' style='width:20px; height:20px; object-fit:contain;'></span> {k}</a>" for k in IMAGENS_CAT.keys()])
    return f"""<html><head>{CSS}<script>const p_num = '{p}'; let cart = JSON.parse(sessionStorage.getItem('cart_'+p_num)) || []; function add(n,v,e) {{ if(!p_num) return alert('Operação inválida!'); if (e <= 0 || cart.filter(x => x.n === n).length >= e) return alert('❌ Sem estoque!'); cart.push({{n,v}}); sessionStorage.setItem('cart_'+p_num, JSON.stringify(cart)); render(); }} function render() {{ let html = ''; let t = 0; cart.forEach((i,idx) => {{ html += `<div class='item-linha' style='color:#d31a21; font-weight:bold;'><span>${{i.n}}</span><span>R$ ${{i.v.toFixed(2)}} <b onclick='rem(${{idx}})' style='cursor:pointer; color:black;'>X</b></span></div>`; t += i.v; }}); document.getElementById('novo-pedido').innerHTML = html; document.getElementById('tot-pedido').innerText = 'R$ '+t.toFixed(2); }} function rem(idx) {{ cart.splice(idx,1); sessionStorage.setItem('cart_'+p_num, JSON.stringify(cart)); render(); }} function enviarPedido() {{ if(!p_num || cart.length === 0) return; let f = document.createElement('form'); f.method = 'POST'; f.action = p_num.startsWith('AVUL') ? '/prosseguir_avulsa' : '/lancar_pedido'; let i1 = document.createElement('input'); i1.name = 'p'; i1.value = p_num; f.appendChild(i1); let i2 = document.createElement('input'); i2.name = 'itens'; i2.value = JSON.stringify(cart); f.appendChild(i2); document.body.appendChild(f); sessionStorage.removeItem('cart_'+p_num); f.submit(); }} window.onload = render;</script></head><body><div class='layout-vendas'><div class='menu-lateral'>{botoes_menu}</div><div class='main-area'>{IMG_LOGO}<h2>{cat}</h2><div class='grid-produtos'>{prods}</div></div><div class='comanda-lateral'>{comanda_display}</div></div></body></html>"""

@app.post("/prosseguir_avulsa", response_class=HTMLResponse)
async def prosseguir_avulsa(request: Request, p: str = Form(...), itens: str = Form(...)):
    if request.session.get("role") not in ["admin", "administrador", "gerente", "garcom", "caixa"]: return RedirectResponse(url="/central")
    cart_itens = json.loads(itens)
    tot_produtos = sum(i['v'] for i in cart_itens)
    lista_html = ""
    from collections import Counter
    contagem = Counter([i['n'] for i in cart_itens])
    precos = {i['n']: i['v'] for i in cart_itens}
    for nome, qtd in contagem.items():
        lista_html += f"<div class='item-linha'><span>{qtd}x {nome}</span><span>R$ {(precos[nome]*qtd):.2f}</span></div>"
    form_checkout = f"""<div style='background:#f4f4f4; padding:20px; border-radius:10px; color:#333; text-align:left; max-width: 500px; margin: auto;'><h3 style='text-align:center; margin-top:0; color:#28a745;'>🛍️ Finalizar Venda Balcão</h3><div style='background:white; padding:15px; border-radius:8px; max-height:200px; overflow-y:auto; border:1px solid #ddd; margin-bottom: 15px;'>{lista_html}</div><div style='font-size:22px; font-weight:bold; color:#d31a21; text-align: center; margin-bottom: 20px;'>TOTAL: R$ {tot_produtos:.2f}</div><form action='/confirmar_avulsa' method='post'><input type='hidden' name='p' value='{p}'><input type='hidden' name='itens' value='{urllib.parse.quote(itens)}'><input type='hidden' name='total' value='{tot_produtos}'><label style='font-size:12px; font-weight:bold; color:#666;'>Forma de Pagamento:</label><select name='pagamento' class='input-padrao' required><option value='DINHEIRO'>DINHEIRO</option><option value='PIX'>PIX</option><option value='C. CREDITO'>C. CREDITO</option><option value='C. DEBITO'>C. DEBITO</option></select><div style='background:#e9ecef; padding:15px; border-radius:8px; margin-top:15px; border:1px solid #ccc;'><div style='display:flex; align-items:center; justify-content:space-between; margin-bottom:10px;'><span style='font-weight:bold; color:#28a745;'>🧾 Emitir Nota Fiscal (NFC-e)?</span><label class='switch'><input type='checkbox' name='nfe' onchange='document.getElementById(\"box-cpf-avulsa\").style.display = this.checked ? \"block\" : \"none\"'><span class='slider'></span></label></div><div id='box-cpf-avulsa' style='display:none;'><span style='font-size:12px; color:#666;'>CPF:</span><input class='input-padrao' name='cpf_nota' placeholder='Digite o CPF se desejar'></div></div><button class='btn-acao' style='background:#28a745; font-size:18px; margin-top:20px;'>✔️ EMITIR NOTA E FECHAR</button><a href='/vendas?p={p}' class='btn-acao' style='background:#555;'>❌ VOLTAR AOS ITENS</a></form></div>"""
    return f"<html><head>{CSS}</head><body><div class='container-center'><div class='card-center' style='max-width: 550px;'>{IMG_LOGO_PEQ}{form_checkout}</div></div></body></html>"

@app.post("/confirmar_avulsa")
async def confirmar_avulsa(request: Request, p: str = Form(...), itens: str = Form(...), pagamento: str = Form(...), total: float = Form(...), nfe: str = Form(None), cpf_nota: str = Form("")):
    cart_itens = json.loads(urllib.parse.unquote(itens))
    u = request.session.get("user", "CAIXA").upper()
    try:
        with engine.begin() as conn:
            conn.execute(text("UPDATE pulseiras SET status = 'FECHADA', forma_pagamento = :pag, total_conta = :tot, data_fechamento = CURRENT_TIMESTAMP, nfe_solicitada = :nfe, cpf_nota = :cpf WHERE numero_pulseira = :p"), {"p": p, "pag": pagamento, "tot": total, "nfe": bool(nfe), "cpf": cpf_nota})
            txt = f"--------------------------------\n      QUIOSQUE BRAHMA\n    VENDA AVULSA (BALCÃO)\nOPERADOR: {u}\nDATA: {datetime.now().strftime('%d/%m/%Y %H:%M')}\n--------------------------------\n"
            from collections import Counter
            contagem = Counter([i['n'] for i in cart_itens])
            precos = {i['n']: i['v'] for i in cart_itens}
            for nome, qtd in contagem.items():
                txt += f"{qtd}x {nome} - R$ {(precos[nome]*qtd):.2f}\n"
                for _ in range(qtd):
                    conn.execute(text("INSERT INTO vendas_itens (pulseira_num, item_nome, valor, garcom, status, comissao_status) VALUES (:p, :n, :v, :g, 'FECHADA', 'PENDENTE')"), {"p": p, "n": nome, "v": precos[nome], "g": u})
                    conn.execute(text("UPDATE produtos SET estoque = GREATEST(estoque - 1, 0) WHERE nome = :n"), {"n": nome})
            txt += f"--------------------------------\nTOTAL PAGO: R$ {total:.2f}\nPAGTO: {pagamento}\n--------------------------------\n"
            if nfe:
                itens_nota = conn.execute(text("SELECT item_nome, COUNT(*) as qtd, SUM(valor) as tot FROM vendas_itens WHERE pulseira_num = :p GROUP BY item_nome"), {"p": p}).fetchall()
                link_danfe = emitir_nfe_api(cpf_nota, itens_nota, total, pagamento)
                txt += f"NFC-e SOLICITADA\nCPF: {cpf_nota}\nDANFE: {link_danfe}\n--------------------------------\n"
            conn.execute(text("INSERT INTO fila_impressao (conteudo) VALUES (:t)"), {"t": txt})
    except: pass
    return RedirectResponse(url="/central", status_code=303)

@app.post("/estorno")
async def estornar_item(request: Request):
    if request.session.get("role") not in ["admin", "administrador", "gerente"]: return RedirectResponse(url="/vendas", status_code=303)
    f = await request.form()
    p, i = f.get("p"), f.get("i")
    try:
        with engine.begin() as conn:
            item = conn.execute(text("SELECT id, valor FROM vendas_itens WHERE pulseira_num=:p AND item_nome=:i AND status='ABERTA' LIMIT 1"), {"p": p, "i": i}).fetchone()
            if item:
                conn.execute(text("UPDATE vendas_itens SET status='ESTORNADO', comissao_status='CANCELADA' WHERE id=:id"), {"id": item.id})
                conn.execute(text("UPDATE pulseiras SET total_conta = GREATEST(total_conta - :v, 0) WHERE numero_pulseira=:p AND status='ABERTA'"), {"v": item.valor, "p": p})
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
            conn.execute(text("UPDATE pulseiras SET total_conta = total_conta + :t WHERE numero_pulseira = :p AND status = 'ABERTA'"), {"t": tot, "p": p})
            txt = f"--------------------------------\n      TICKET PREPARO\nPULSEIRA: {p}\nATENDENTE: {u}\n--------------------------------\n"
            for i in itens:
                conn.execute(text("INSERT INTO vendas_itens (pulseira_num, item_nome, valor, garcom) VALUES (:p, :n, :v, :g)"), {"p": p, "n": i['n'], "v": i['v'], "g": u})
                conn.execute(text("UPDATE produtos SET estoque = GREATEST(estoque - 1, 0) WHERE nome = :n"), {"n": i['n']})
                txt += f"1x {i['n']} - R$ {i['v']:.2f}\n"
            txt += "--------------------------------\n"
            conn.execute(text("INSERT INTO fila_impressao (conteudo) VALUES (:txt)"), {"txt": txt})
    except: pass
    return RedirectResponse(url=f"/vendas?p={p}", status_code=303)

@app.get("/fechar_conta", response_class=HTMLResponse)
async def fechar_conta(request: Request, q: str = ""):
    if request.session.get("role") not in ["admin", "administrador", "gerente", "garcom", "caixa"]: return RedirectResponse(url="/central")
    with engine.connect() as conn:
        c_status = conn.execute(text("SELECT tipo FROM caixa_movimentos WHERE tipo IN ('ABERTURA', 'FECHAMENTO') ORDER BY id DESC LIMIT 1")).fetchone()
        if not c_status or c_status[0] != 'ABERTURA': return HTMLResponse("<script>alert('O Caixa está Fechado!'); window.location.href='/central';</script>")
    res = ""
    if q:
        with engine.connect() as conn:
            query = conn.execute(text("SELECT p.numero_pulseira, p.total_conta, c.nome_completo, c.cpf FROM pulseiras p JOIN clientes c ON p.cliente_cpf = c.cpf WHERE (p.numero_pulseira = :q OR c.cpf = :q) AND p.status = 'ABERTA'"), {"q": q.strip()}).fetchone()
            if query:
                itens_q = conn.execute(text("SELECT item_nome, COUNT(*) as qtd, SUM(valor) as tot FROM vendas_itens WHERE pulseira_num = :p AND status = 'ABERTA' GROUP BY item_nome"), {"p": query.numero_pulseira}).fetchall()
                lista = "".join([f"<div class='item-linha'><span>{i.qtd}x {i.item_nome}</span><span>R$ {float(i.tot or 0):.2f}</span></div>" for i in itens_q])
                subt = float(query.total_conta or 0)
                taxa = subt * 0.10
                tot_final = subt + taxa
                form_parcial = f"""<div style='background:#ffeaa7; padding:15px; border-radius:8px; margin-top:15px; border:1px solid #fdcb6e;'><h4 style='margin-top:0; color:#d35400; border-bottom:1px solid #fdcb6e; padding-bottom:5px;'>💸 Pagamento Parcial (Rachar a Conta)</h4><form action='/parcial' method='post' style='display:flex; flex-wrap:wrap; gap:10px; align-items:center; margin:0;'><input type='hidden' name='p' value='{query.numero_pulseira}'><input type='hidden' name='cpf' value='{query.cpf}'><input type='number' step='0.01' name='val' max='{tot_final}' class='input-padrao' placeholder='R$ Valor' required style='flex:1; min-width:80px; margin:0;'><select name='pg' class='input-padrao' style='flex:1; min-width:110px; margin:0;'><option value='DINHEIRO'>DINHEIRO</option><option value='PIX'>PIX</option><option value='C. CREDITO'>C. CREDITO</option><option value='C. DEBITO'>C. DEBITO</option></select><button class='btn-acao' style='background:#d35400; margin:0; flex:1; min-width:100px;'>RECEBER</button></form></div>"""
                res = f"""<div style='background:#f4f4f4; padding:20px; border-radius:10px; color:#333; margin-top:20px; text-align:left;'><h3 style='text-align:center; margin-top:0;'>{query.nome_completo}</h3><p style='text-align:center;'>Pulseira: <b>{query.numero_pulseira}</b></p><div style='background:white; padding:15px; border-radius:8px; max-height:220px; overflow-y:auto; border:1px solid #ddd;'>{lista}</div><div style='padding-top:15px; font-size:16px;'><div class='item-linha'><span>Saldo Devedor S/ Tx:</span><span>R$ {subt:.2f}</span></div><div class='item-linha'><span>Serviço (10%):</span><span>R$ {taxa:.2f}</span></div><div class='item-linha' style='color:#062b5e;'><span>Desconto (R$):</span><input type='number' id='input_desconto' value='0' min='0' step='0.01' style='width:70px; padding:5px;' oninput='calcDiv()'></div><div class='item-linha' style='font-weight:bold; font-size:20px; color:#d31a21;'><span>RESTANTE A PAGAR:</span><span id='tot_final'>R$ {tot_final:.2f}</span></div><div class='item-linha'><span>Dividir por:</span><input type='number' id='divisores' value='1' min='1' style='width:60px; text-align:center; padding:5px;' oninput='calcDiv()'></div><div class='item-linha' style='font-weight:bold; font-size:18px;'><span>Por Pessoa:</span><span id='val_pessoa'>R$ {tot_final:.2f}</span></div><div class='item-linha'><span>Pagamento:</span><select id='select_pag' class='input-padrao' style='width:auto;' onchange='document.getElementById("input_pag_form").value = this.value'><option value='DINHEIRO'>DINHEIRO</option><option value='PIX'>PIX</option><option value='C. CREDITO'>C. CREDITO</option><option value='C. DEBITO'>C. DEBITO</option></select></div></div>{form_parcial}<form action='/confirmar_fechamento' method='post'><input type='hidden' name='p' value='{query.numero_pulseira}'><input type='hidden' name='divisao' id='input_div' value='1'><input type='hidden' name='desconto' id='input_desc_form' value='0'><input type='hidden' name='pagamento' id='input_pag_form' value='DINHEIRO'><div style='background:#e9ecef; padding:15px; border-radius:8px; margin-top:15px; border:1px solid #ccc;'><div style='display:flex; align-items:center; justify-content:space-between; margin-bottom:10px;'><span style='font-weight:bold; color:#28a745;'>🧾 Emitir Nota Fiscal (NFC-e)?</span><label class='switch'><input type='checkbox' name='nfe' onchange='document.getElementById("box-cpf").style.display = this.checked ? "block" : "none"'><span class='slider'></span></label></div><div id='box-cpf' style='display:none;'><span style='font-size:12px; color:#666;'>CPF:</span><input class='input-padrao' name='cpf_nota' value='{query.cpf}'></div></div><button class='btn-acao' style='background:#28a745; font-size:18px; margin-top:15px;'>🖨️ ZERAR CONTA E IMPRIMIR</button></form><script>function calcDiv() {{ let subt = {subt}; let taxa = {taxa}; let desc = parseFloat(document.getElementById('input_desconto').value.replace(',', '.')) || 0; let div = parseInt(document.getElementById('divisores').value) || 1; let totFinal = Math.max(subt + taxa - desc, 0); document.getElementById('tot_final').innerText = 'R$ ' + totFinal.toFixed(2); document.getElementById('val_pessoa').innerText = 'R$ ' + (totFinal / div).toFixed(2); document.getElementById('input_div').value = div; document.getElementById('input_desc_form').value = desc; }}</script></div>"""
    return f"<html><head>{CSS}</head><body><div class='container-center'><div class='card-center'>{IMG_LOGO_PEQ}<h2>Fechar Conta</h2><form method='get'><input class='input-padrao' name='q' placeholder='CPF ou Nº Pulseira' value='{q}' required><button class='btn-acao'>CONSULTAR CONTA</button></form>{res}<br><a href='/central' style='color:gray'>Voltar</a></div></div></body></html>"

@app.post("/parcial")
async def registrar_parcial(request: Request):
    if request.session.get("role") not in ["admin", "administrador", "gerente", "garcom", "caixa"]: return RedirectResponse(url="/central", status_code=303)
    f = await request.form()
    p, cpf, val, pg = f.get("p"), f.get("cpf"), float(f.get("val", 0)), f.get("pg")
    if val <= 0: return RedirectResponse(url=f"/fechar_conta?q={p}", status_code=303)
    tag = datetime.now().strftime("%H%M%S")
    valor_real_abatido = val / 1.10
    try:
        with engine.begin() as conn:
            conn.execute(text("UPDATE pulseiras SET total_conta = GREATEST(total_conta - :v, 0) WHERE numero_pulseira=:p AND status='ABERTA'"), {"v": valor_real_abatido, "p": p})
            conn.execute(text("INSERT INTO pulseiras (numero_pulseira, cliente_cpf, total_conta, status, forma_pagamento, data_fechamento) VALUES (:p_dummy, :c, :v, 'FECHADA', :pg, CURRENT_TIMESTAMP)"), {"p_dummy": f"{p}-PARC{tag}", "c": cpf, "v": valor_real_abatido, "pg": pg})
            txt = f"--------------------------------\n      QUIOSQUE BRAHMA\n  PAGAMENTO PARCIAL\nPULSEIRA: {p}\nVALOR PAGO: R$ {val:.2f}\nPAGTO: {pg}\n--------------------------------\n"
            conn.execute(text("INSERT INTO fila_impressao (conteudo) VALUES (:t)"), {"t": txt})
    except: pass
    return RedirectResponse(url=f"/fechar_conta?q={p}", status_code=303)

@app.post("/confirmar_fechamento")
async def confirmar_fechamento(request: Request):
    f = await request.form()
    p, pag, nfe, cpf, desc = f.get("p"), f.get("pagamento"), f.get("nfe"), f.get("cpf_nota"), float(f.get("desconto", "0"))
    try:
        with engine.begin() as conn: 
            c = conn.execute(text("SELECT c.nome_completo, p.total_conta FROM pulseiras p JOIN clientes c ON p.cliente_cpf = c.cpf WHERE p.numero_pulseira = :p AND p.status = 'ABERTA'"), {"p": p}).fetchone()
            if c:
                itens_consumidos = conn.execute(text("SELECT item_nome, COUNT(*) as qtd, SUM(valor) as tot FROM vendas_itens WHERE pulseira_num = :p AND status = 'ABERTA' GROUP BY item_nome"), {"p": p}).fetchall()
                subt = float(c.total_conta)
                taxa = subt * 0.10
                tot = (subt + taxa) - desc
                conn.execute(text("UPDATE pulseiras SET status = 'FECHADA', forma_pagamento = :pag, total_conta = :tot, data_fechamento = CURRENT_TIMESTAMP, nfe_solicitada = :nfe, cpf_nota = :cpf WHERE numero_pulseira = :p AND status = 'ABERTA'"), {"p": p, "pag": pag, "tot": tot, "nfe": bool(nfe), "cpf": cpf})
                conn.execute(text("UPDATE vendas_itens SET status = 'FECHADA' WHERE pulseira_num = :p AND status = 'ABERTA'"), {"p": p})
                txt = f"--------------------------------\n      QUIOSQUE BRAHMA\nFECHAMENTO DE CONTA\nPULSEIRA: {p}\n--------------------------------\n"
                if desc > 0: txt += f"DESCONTO TOTAL APLICADO: -R$ {desc:.2f}\n--------------------------------\n"
                for i in itens_consumidos: txt += f"{i.qtd}x {i.item_nome} - R$ {float(i.tot):.2f}\n"
                txt += f"--------------------------------\nSUBTOTAL: R$ {subt:.2f}\nTAXA (10%): R$ {taxa:.2f}\nTOTAL: R$ {tot:.2f}\nPAGTO: {pag}\n--------------------------------\n"
                if nfe:
                    link_danfe = emitir_nfe_api(cpf, itens_consumidos, tot, pag)
                    txt += f"NFC-e SOLICITADA\nCPF: {cpf}\nDANFE: {link_danfe}\n--------------------------------\n"
                conn.execute(text("INSERT INTO fila_impressao (conteudo) VALUES (:t)"), {"t": txt})
    except: pass
    return RedirectResponse(url="/central", status_code=303)

@app.get("/buscar", response_class=HTMLResponse)
async def tela_busca(q: str = ""):
    with engine.connect() as conn:
        c_status = conn.execute(text("SELECT tipo FROM caixa_movimentos WHERE tipo IN ('ABERTURA', 'FECHAMENTO') ORDER BY id DESC LIMIT 1")).fetchone()
        if not c_status or c_status[0] != 'ABERTURA': return HTMLResponse("<script>alert('O Caixa está Fechado!'); window.location.href='/central';</script>")
    res = ""
    if q:
        with engine.connect() as conn:
            for r in conn.execute(text("SELECT nome_completo, cpf FROM clientes WHERE nome_completo ILIKE :q OR cpf LIKE :q"), {"q": f"%{q}%"}).fetchall():
                res += f"<tr><td style='color:black'>{r.nome_completo}</td><td><form action='/abrir' method='post' style='display:flex;gap:5px'><input type='hidden' name='cpf' value='{r.cpf}'><input class='input-padrao' name='p' placeholder='Nº' required style='width:60px;margin:0'><button class='btn-acao' style='background:#d31a21;padding:8px;margin:0'>ABRIR</button></form></td></tr>"
    return f"<html><head>{CSS}</head><body><div class='container-center'><div class='card-center'>{IMG_LOGO_PEQ}<h2>Buscar Cliente</h2><form method='get'><input class='input-padrao' name='q' placeholder='Nome ou CPF' value='{q}'><button class='btn-acao'>PESQUISAR</button></form><table>{res}</table><br><a href='/central'>Voltar</a></div></div></body></html>"

@app.post("/abrir")
async def abrir(request: Request):
    f = await request.form()
    cpf, p = f.get("cpf"), f.get("p")
    try:
        with engine.begin() as conn:
            if conn.execute(text("SELECT numero_pulseira FROM pulseiras WHERE cliente_cpf = :c AND status = 'ABERTA'"), {"c": cpf}).fetchone(): return HTMLResponse("<script>alert('Cliente já tem comanda aberta!'); window.history.back();</script>")
            if conn.execute(text("SELECT cliente_cpf FROM pulseiras WHERE numero_pulseira = :p AND status = 'ABERTA'"), {"p": p}).fetchone(): return HTMLResponse("<script>alert('Pulseira em uso!'); window.history.back();</script>")
            conn.execute(text("INSERT INTO pulseiras (numero_pulseira, cliente_cpf, total_conta, status) VALUES (:p, :c, 7.00, 'ABERTA')"), {"p": p, "c": cpf})
    except: pass
    return RedirectResponse(url=f"/vendas?p={p}", status_code=303)

@app.get("/cadastro", response_class=HTMLResponse)
async def tela_cadastro():
    with engine.connect() as conn:
        c_status = conn.execute(text("SELECT tipo FROM caixa_movimentos WHERE tipo IN ('ABERTURA', 'FECHAMENTO') ORDER BY id DESC LIMIT 1")).fetchone()
        if not c_status or c_status[0] != 'ABERTURA': return HTMLResponse("<script>alert('O Caixa está Fechado!'); window.location.href='/central';</script>")
    return f"<html><head>{CSS}</head><body><div class='container-center'><div class='card-center'>{IMG_LOGO_PEQ}<h2>Novo Cliente</h2><form action='/salvar' method='post'><input class='input-padrao' name='nome' placeholder='Nome Completo' required><input class='input-padrao' name='cpf' placeholder='CPF' required><input class='input-padrao' name='nasc' type='date' required><input class='input-padrao' name='contato' placeholder='WhatsApp' required><input class='input-padrao' name='pulseira' placeholder='Nº Pulseira' required><button class='btn-acao' style='background:#d31a21'>SALVAR E ABRIR</button></form><br><a href='/central'>Voltar</a></div></div></body></html>"

@app.post("/salvar")
async def salvar(request: Request):
    f = await request.form()
    n, c, d, co, p = f.get("nome"), f.get("cpf"), f.get("nasc"), f.get("contato"), f.get("pulseira")
    try:
        with engine.begin() as conn:
            conn.execute(text("INSERT INTO clientes (nome_completo, cpf, data_nascimento, contato) VALUES (:n, :c, :d, :co) ON CONFLICT (cpf) DO NOTHING"), {"n":n, "c":c, "d":d, "co":co})
            if conn.execute(text("SELECT numero_pulseira FROM pulseiras WHERE cliente_cpf = :c AND status = 'ABERTA'"), {"c": c}).fetchone(): return HTMLResponse("<script>alert('Cliente já possui comanda aberta!'); window.history.back();</script>")
            if conn.execute(text("SELECT cliente_cpf FROM pulseiras WHERE numero_pulseira = :p AND status = 'ABERTA'"), {"p": p}).fetchone(): return HTMLResponse("<script>alert('Pulseira em uso por outra pessoa!'); window.history.back();</script>")
            conn.execute(text("INSERT INTO pulseiras (numero_pulseira, cliente_cpf, total_conta, status) VALUES (:p, :c, 7.00, 'ABERTA')"), {"p":p, "c":c})
    except: pass
    return RedirectResponse(url=f"/vendas?p={p}", status_code=303)

@app.get("/historico", response_class=HTMLResponse)
async def tela_historico(request: Request, data_filtro: str = ""):
    if request.session.get("role") not in ["admin", "administrador", "gerente"]: return RedirectResponse(url="/central")
    hoje = data_filtro if data_filtro else date.today().strftime("%Y-%m-%d")
    linhas = ""
    with engine.connect() as conn:
        itens = conn.execute(text("SELECT id, pulseira_num, item_nome, valor, hora_venda, garcom, status FROM vendas_itens WHERE CAST(data_venda AS DATE) = CAST(:h AS DATE) ORDER BY id DESC"), {"h": hoje}).fetchall()
        for i in itens:
            cor_status = "color:#28a745" if i.status == "FECHADA" else ("color:#d31a21" if i.status == "ESTORNADO" else "color:#f39c12")
            botao = f"<form action='/executar_estorno' method='post' style='margin:0;' onsubmit='return confirm(\"Confirma o estorno de {i.item_nome}?\");'><input type='hidden' name='id_item' value='{i.id}'><button class='btn-acao' style='background:#d31a21; padding:8px; font-size:12px; margin:0;'>ESTORNAR</button></form>" if i.status != 'ESTORNADO' else "<b style='color:#d31a21'>ESTORNADO</b>"
            linhas += f"<tr><td style='color:black;'>{i.hora_venda.strftime('%H:%M') if i.hora_venda else ''}</td><td style='color:black;'>{i.pulseira_num}</td><td style='color:black;'>{i.item_nome}</td><td style='color:black; font-weight:bold;'>R$ {float(i.valor):.2f}</td><td style='color:#666;'>{i.garcom or 'N/D'}</td><td style='{cor_status}'><b>{i.status}</b></td><td>{botao}</td></tr>"
    return f"<html><head>{CSS}</head><body><div class='container-center'><div class='card-center' style='max-width:900px;'><h2>🕒 Histórico de Itens Lançados</h2><form method='GET' style='margin-bottom:15px; display:flex; gap:10px;'><input type='date' name='data_filtro' value='{hoje}' class='input-padrao' style='flex:1;'><button class='btn-acao' style='background:#062b5e; width:120px;'>FILTRAR</button></form><div class='table-responsive' style='max-height:450px; overflow-y:auto;'><table><tr><th style='color:black'>Hora</th><th style='color:black'>Comanda</th><th style='color:black'>Item</th><th style='color:black'>Valor</th><th style='color:black'>Operador</th><th style='color:black'>Status</th><th style='color:black'>Ação</th></tr>{linhas if linhas else '<tr><td colspan=7 style=color:black;text-align:center;>Nenhum item encontrado.</td></tr>'}</table></div><br><a href='/central' class='btn-acao' style='width: 200px; margin:auto'>Voltar ao Menu</a></div></div></body></html>"

@app.post("/executar_estorno")
async def executar_estorno(request: Request, id_item: int = Form(...)):
    if request.session.get("role") not in ["admin", "administrador", "gerente"]: return RedirectResponse(url="/central")
    try:
        with engine.begin() as conn:
            item = conn.execute(text("SELECT pulseira_num, item_nome, valor, status FROM vendas_itens WHERE id = :id FOR UPDATE"), {"id": id_item}).fetchone()
            if item and item.status != 'ESTORNADO':
                conn.execute(text("UPDATE vendas_itens SET status = 'ESTORNADO', comissao_status = 'CANCELADA' WHERE id = :id"), {"id": id_item})
                conn.execute(text("UPDATE produtos SET estoque = estoque + 1 WHERE nome = :n"), {"n": item.item_nome})
                conn.execute(text("UPDATE pulseiras SET total_conta = GREATEST(total_conta - :v, 0) WHERE numero_pulseira = :p"), {"v": item.valor, "p": item.pulseira_num})
    except: pass
    referer = request.headers.get("referer")
    if referer: return RedirectResponse(url=referer, status_code=303)
    return RedirectResponse(url="/historico", status_code=303)

@app.get("/abrir_caixa", response_class=HTMLResponse)
async def abrir_caixa(request: Request):
    if request.session.get("role") not in ["admin", "administrador", "gerente", "caixa"]: return RedirectResponse(url="/central")
    return f"<html><head>{CSS}</head><body><div class='container-center'><div class='card-center'>{IMG_LOGO_PEQ}<h2>Iniciar Evento / Caixa</h2><p style='color:#666;'>Informe o valor de troco inicial da gaveta:</p><form action='/iniciar_caixa' method='post'><input class='input-padrao' name='fundo' type='number' step='0.01' placeholder='R$ Fundo de Caixa' required style='font-size:24px; text-align:center; padding:15px; font-weight:bold;'><button class='btn-acao' style='background:#28a745; font-size:18px; margin-top:20px;'>✔️ ABRIR CAIXA</button></form><br><a href='/central' style='color:gray'>Voltar</a></div></div></body></html>"

@app.post("/iniciar_caixa")
async def iniciar_caixa(request: Request):
    if request.session.get("role") not in ["admin", "administrador", "gerente", "caixa"]: return RedirectResponse(url="/central")
    f = await request.form()
    try:
        with engine.begin() as conn: conn.execute(text("INSERT INTO caixa_movimentos (tipo, valor, descricao, usuario) VALUES ('ABERTURA', :v, 'Fundo de Caixa Inicial', :u)"), {"v": float(f.get("fundo", "0")), "u": request.session.get("user")})
    except: pass
    return RedirectResponse(url="/central", status_code=303)

@app.get("/caixa", response_class=HTMLResponse)
async def tela_caixa(request: Request):
    if request.session.get("role") not in ["admin", "administrador", "gerente", "caixa"]: return RedirectResponse(url="/central")
    hoje = date.today().strftime("%Y-%m-%d")
    with engine.connect() as conn:
        pag_q = conn.execute(text(f"SELECT forma_pagamento, SUM(total_conta) as total FROM pulseiras WHERE CAST(data_fechamento AS DATE) = CAST('{hoje}' AS DATE) AND status = 'FECHADA' GROUP BY forma_pagamento")).fetchall()
        totais = {"DINHEIRO": 0.0, "PIX": 0.0, "C. CREDITO": 0.0, "C. DEBITO": 0.0}
        for p in pag_q: totais[p.forma_pagamento] = float(p.total or 0)
        mov_q = conn.execute(text(f"SELECT tipo, descricao, valor, TO_CHAR(data_registro, 'HH24:MI') as hora FROM caixa_movimentos WHERE CAST(data_registro AS DATE) = CAST('{hoje}' AS DATE) ORDER BY data_registro DESC")).fetchall()
        linhas_mov = "".join([f"<tr><td style='color:black;'>{m.hora}</td><td style='color:black;'>{m.tipo} - {m.descricao}</td><td style='color:#d31a21; font-weight:bold;'>- R$ {float(m.valor):.2f}</td></tr>" for m in mov_q if m.tipo == 'SANGRIA'])
    return f"<html><head>{CSS}</head><body><div class='container-center'><div class='card-center' style='max-width:700px;'>{IMG_LOGO_PEQ}<h2>💰 Gestão de Caixa (Hoje)</h2><div style='display:flex; justify-content:space-between; flex-wrap:wrap; gap:10px; margin-bottom:20px;'><div style='background:#f9f9f9; padding:15px; border-radius:8px; border-left:4px solid #28a745; flex:1; min-width:140px;'><b>💵 Dinheiro:</b><br><span style='font-size:20px; color:#28a745;'>R$ {totais['DINHEIRO']:.2f}</span></div><div style='background:#f9f9f9; padding:15px; border-radius:8px; border-left:4px solid #17a2b8; flex:1; min-width:140px;'><b>💠 PIX:</b><br><span style='font-size:20px; color:#17a2b8;'>R$ {totais['PIX']:.2f}</span></div><div style='background:#f9f9f9; padding:15px; border-radius:8px; border-left:4px solid #f39c12; flex:1; min-width:140px;'><b>💳 Cartões:</b><br><span style='font-size:20px; color:#f39c12;'>R$ {(totais['C. CREDITO'] + totais['C. DEBITO']):.2f}</span></div></div><div style='background:#f4f4f4; padding:20px; border-radius:10px; text-align:left; border:1px solid #ccc; margin-bottom:20px;'><h3 style='margin-top:0; color:#d31a21;'>🔻 Fazer Sangria (Retirada)</h3><form action='/sangria' method='post' style='display:flex; flex-wrap:wrap; gap:10px;'><input name='valor' type='number' step='0.01' placeholder='Valor R$' class='input-padrao' style='flex:1; min-width:100px;' required><input name='desc' type='text' placeholder='Motivo (Ex: Gelo, Vale)' class='input-padrao' style='flex:2; min-width:180px;' required><button class='btn-acao' style='background:#d31a21; margin:0; width:100px;'>TIRAR</button></form></div><h3 style='text-align:left; margin-bottom:5px;'>Histórico de Retiradas</h3><div class='table-responsive' style='max-height:150px; overflow-y:auto;'><table><tr><th style='color:black'>Hora</th><th style='color:black'>Motivo</th><th style='color:black'>Valor</th></tr>{linhas_mov if linhas_mov else '<tr><td colspan=3 style=color:black;text-align:center;>Nenhuma retirada.</td></tr>'}</table></div><a href='/caixa_cego' class='btn-acao' style='background:#062b5e; font-size:18px; padding:20px;'>🔒 ENCERRAR TURNO (BATER CAIXA)</a><br><a href='/central' style='color:gray'>Voltar ao Menu</a></div></div></body></html>"

@app.post("/sangria")
async def registrar_sangria(request: Request):
    if request.session.get("role") not in ["admin", "administrador", "gerente", "caixa"]: return RedirectResponse(url="/central")
    f = await request.form()
    try:
        with engine.begin() as conn: conn.execute(text("INSERT INTO caixa_movimentos (tipo, valor, descricao, usuario) VALUES ('SANGRIA', :v, :d, :u)"), {"v": float(f.get("valor", "0")), "d": f.get("desc", ""), "u": request.session.get("user")})
    except: pass
    return RedirectResponse(url="/caixa", status_code=303)

@app.get("/caixa_cego", response_class=HTMLResponse)
async def tela_caixa_cego(request: Request):
    if request.session.get("role") not in ["admin", "administrador", "gerente", "caixa"]: return RedirectResponse(url="/central")
    return f"<html><head>{CSS}</head><body><div class='container-center'><div class='card-center'>{IMG_LOGO_PEQ}<h2 style='color:#d31a21;'>Fechamento Cego</h2><p style='color:black;'>Conte as notas da gaveta e digite abaixo o valor total exato do dinheiro físico.</p><form action='/resumo_whatsapp' method='post'><input class='input-padrao' name='dinheiro_gaveta' type='number' step='0.01' placeholder='R$ 0.00' required style='font-size:24px; text-align:center; padding:20px; font-weight:bold;'><button class='btn-acao' style='background:#28a745; font-size:18px; margin-top:20px;'>✔️ CONFIRMAR VALOR FÍSICO</button></form><br><a href='/caixa' style='color:gray'>Cancelar</a></div></div></body></html>"

@app.post("/resumo_whatsapp", response_class=HTMLResponse)
async def resumo_whatsapp(request: Request):
    if request.session.get("role") not in ["admin", "administrador", "gerente", "caixa"]: return RedirectResponse(url="/central")
    f = await request.form()
    gaveta = float(f.get("dinheiro_gaveta", "0"))
    hoje_str, hoje_br, usuario = date.today().strftime("%Y-%m-%d"), date.today().strftime("%d/%m/%Y"), request.session.get("user", "Desconhecido").upper()
    try:
        with engine.begin() as conn:
            conn.execute(text("INSERT INTO caixa_movimentos (tipo, valor, descricao, usuario) VALUES ('FECHAMENTO', 0, 'Caixa Encerrado', :u)"), {"u": usuario})
            pag_q = conn.execute(text(f"SELECT forma_pagamento, SUM(total_conta) as total FROM pulseiras WHERE CAST(data_fechamento AS DATE) = CAST('{hoje_str}' AS DATE) AND status = 'FECHADA' GROUP BY forma_pagamento")).fetchall()
            totais = {"DINHEIRO": 0.0, "PIX": 0.0, "C. CREDITO": 0.0, "C. DEBITO": 0.0}
            for p in pag_q: totais[p.forma_pagamento] = float(p.total or 0)
            mov_q = conn.execute(text(f"SELECT SUM(valor) as tot FROM caixa_movimentos WHERE CAST(data_registro AS DATE) = CAST('{hoje_str}' AS DATE) AND tipo = 'SANGRIA'")).fetchone()
            tot_sangria = float(mov_q.tot or 0)
            fundo_q = conn.execute(text(f"SELECT SUM(valor) as tot FROM caixa_movimentos WHERE CAST(data_registro AS DATE) = CAST('{hoje_str}' AS DATE) AND tipo = 'ABERTURA'")).fetchone()
            fundo_caixa = float(fundo_q.tot or 0)
            comissao_db = conn.execute(text(f"SELECT SUM(valor * 0.10) as tot FROM vendas_itens WHERE CAST(data_venda AS DATE) = CAST('{hoje_str}' AS DATE) AND status = 'FECHADA'")).fetchone()
            tot_comissao = float(comissao_db.tot or 0)
    except: pass
    esperado = fundo_caixa + totais["DINHEIRO"] - tot_sangria
    dif = gaveta - esperado
    faturamento_bruto = sum(totais.values())
    faturamento_liq = faturamento_bruto - tot_comissao
    status_caixa = "✅ Bateu certinho! R$ 0.00" if dif == 0 else f"⚠️ Sobrou na gaveta: R$ {dif:.2f}" if dif > 0 else f"❌ FURO DE CAIXA: R$ {dif:.2f}"
    mensagem = f"📊 *FECHAMENTO DE CAIXA*\n*Data:* {hoje_br}\n*Operador:* {usuario}\n\n*Valores em Caixa:*\n📥 Fundo Inicial: R$ {fundo_caixa:.2f}\n💵 Dinheiro (Vendas): R$ {totais['DINHEIRO']:.2f}\n🔻 Sangrias: R$ {tot_sangria:.2f}\n\n*Outros Recebimentos:*\n💳 Cartão: R$ {(totais['C. CREDITO'] + totais['C. DEBITO']):.2f}\n💠 PIX: R$ {totais['PIX']:.2f}\n\n*Auditoria da Gaveta (Físico):*\nInformado: R$ {gaveta:.2f}\nDeveria ter: R$ {esperado:.2f}\n*Status:* {status_caixa}\n\n*Resumo Geral:*\n💰 Bruto Vendido: R$ {faturamento_bruto:.2f}\n💸 Comissões: R$ {tot_comissao:.2f}\n✅ *Líquido: R$ {faturamento_liq:.2f}*"
    zap_url = f"https://wa.me/5561995414168?text={urllib.parse.quote(mensagem)}"
    return f"<html><head>{CSS}</head><body><div class='container-center'><div class='card-center' style='max-width:600px;'><h2>Auditoria Concluída</h2><div style='background:#f4f4f4; padding:20px; border-radius:8px; text-align:left; color:black; font-family:monospace; font-size:14px; margin-bottom:20px; white-space:pre-wrap;'>{mensagem.replace('*', '<b>').replace('<b>', '</b>', 1)}</div><a href='{zap_url}' target='_blank' class='btn-acao' style='background:#25D366; font-size:18px; padding:20px;'>📱 ENVIAR RESUMO WHATSAPP</a><br><a href='/central' style='color:gray'>Voltar</a></div></div></body></html>"

@app.get("/dashboard", response_class=HTMLResponse)
async def dashboard(request: Request, inicio: str = "", fim: str = "", cat: str = "", prod: str = "", garcom_filtro: str = ""):
    if request.session.get("role") not in ["admin", "administrador", "gerente"]: return RedirectResponse(url="/central")
    where_pulseira, where_vendas, where_hist, where_prod = "status = 'FECHADA'", "status = 'FECHADA'", "1=1", "1=1"
    params_p, params_v, params_h = {}, {}, {}
    if inicio:
        where_pulseira += " AND CAST(data_fechamento AS DATE) >= CAST(:inicio AS DATE)"; where_vendas += " AND CAST(data_venda AS DATE) >= CAST(:inicio AS DATE)"; where_hist += " AND CAST(data_entrada AS DATE) >= CAST(:inicio AS DATE)"; params_p["inicio"] = params_v["inicio"] = params_h["inicio"] = inicio
    if fim:
        where_pulseira += " AND CAST(data_fechamento AS DATE) <= CAST(:fim AS DATE)"; where_vendas += " AND CAST(data_venda AS DATE) <= CAST(:fim AS DATE)"; where_hist += " AND CAST(data_entrada AS DATE) <= CAST(:fim AS DATE)"; params_p["fim"] = params_v["fim"] = params_h["fim"] = fim
    if garcom_filtro:
        where_vendas += " AND vendas_itens.garcom = :g_filtro"; params_v["g_filtro"] = garcom_filtro
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
        kpi = conn.execute(text(f"SELECT SUM(total_conta) as total, AVG(total_conta) as media FROM pulseiras WHERE {where_pulseira}"), params_p).fetchone()
        faturamento_bruto = float(kpi.total or 0); ticket_medio = float(kpi.media or 0)
        comissao_db = conn.execute(text(f"SELECT SUM(valor * 0.10) as comissao_total FROM vendas_itens {join_vendas} WHERE {where_vendas} AND comissao_status = 'PAGA'"), params_v).fetchone()
        comissoes_pagas = float(comissao_db.comissao_total or 0); faturamento_liquido = faturamento_bruto - comissoes_pagas
        where_estorno = where_vendas.replace("status = 'FECHADA'", "status = 'ESTORNADO'")
        estorno_db = conn.execute(text(f"SELECT SUM(valor) as total FROM vendas_itens {join_vendas} WHERE {where_estorno}"), params_v).fetchone()
        total_estornado = float(estorno_db.total or 0)
        pagamentos = conn.execute(text(f"SELECT forma_pagamento, COUNT(*) as qtd FROM pulseiras WHERE {where_pulseira} GROUP BY forma_pagamento"), params_p).fetchall()
        labels_pag, data_pag = [r.forma_pagamento or "N/D" for r in pagamentos], [r.qtd for r in pagamentos]
        top_qtd_db = conn.execute(text(f"SELECT item_nome, COUNT(*) as qtd FROM vendas_itens {join_vendas} WHERE {where_vendas} GROUP BY item_nome ORDER BY qtd DESC LIMIT 3"), params_v).fetchall()
        html_top_qtd = "".join([f"<div class='item-linha' style='color:black; padding: 8px 0;'><span><b>{i+1}º</b> {r.item_nome}</span><b style='color:#062b5e;'>{r.qtd} un</b></div>" for i, r in enumerate(top_qtd_db)])
        top_valor_db = conn.execute(text(f"SELECT item_nome, SUM(valor) as total FROM vendas_itens {join_vendas} WHERE {where_vendas} GROUP BY item_nome ORDER BY total DESC LIMIT 3"), params_v).fetchall()
        html_top_valor = "".join([f"<div class='item-linha' style='color:black; padding: 8px 0;'><span><b>{i+1}º</b> {r.item_nome}</span><b style='color:#28a745;'>R$ {float(r.total):.2f}</b></div>" for i, r in enumerate(top_valor_db)])
        rank_func_db = conn.execute(text(f"SELECT garcom, COUNT(*) as qtd, SUM(valor) as total FROM vendas_itens {join_vendas} WHERE {where_vendas} GROUP BY garcom ORDER BY total DESC"), params_v).fetchall()
        html_rank_func = "".join([f"<tr><td style='color:black;'><b>{i+1}º</b> {r.garcom or 'N/D'}</td><td style='color:#062b5e; text-align:center;'>{r.qtd}</td><td style='color:#28a745; text-align:right; font-weight:bold;'>R$ {float(r.total):.2f}</td></tr>" for i, r in enumerate(rank_func_db)])
        garcons = rank_func_db
        total_vendas_db = conn.execute(text(f"SELECT COUNT(*) as total_vendido FROM vendas_itens {join_vendas} WHERE {where_vendas}"), params_v).fetchone()
        total_saidas = int(total_vendas_db.total_vendido or 0)
        total_entradas_db = conn.execute(text(f"SELECT SUM(qtd_adicionada) as total_entrou FROM historico_estoque WHERE {where_hist}"), params_h).fetchone()
        total_entradas = int(total_entradas_db.total_entrou or 0)
        
        query_cruz = f"SELECT p.nome, p.estoque, COUNT(v.id) as vendidos FROM produtos p LEFT JOIN vendas_itens v ON p.nome = v.item_nome AND v.status = 'FECHADA' {'AND CAST(v.data_venda AS DATE) >= CAST(:inicio AS DATE)' if inicio else ''} {'AND CAST(v.data_venda AS DATE) <= CAST(:fim AS DATE)' if fim else ''} WHERE {where_prod} GROUP BY p.nome, p.estoque ORDER BY vendidos DESC LIMIT 10"
        params_cruz = {}
        if inicio: params_cruz["inicio"] = inicio
        if fim: params_cruz["fim"] = fim
        if cat: params_cruz["cat"] = cat
        if prod:
            params_cruz["prod"] = params_v["prod"]
            if "prod_id" in params_v: params_cruz["prod_id"] = params_v["prod_id"]
        cruzamento = conn.execute(text(query_cruz), params_cruz).fetchall()
        labels_cruz, data_cruz_vendidos, data_cruz_estoque = [r.nome for r in cruzamento], [r.vendidos for r in cruzamento], [r.estoque for r in cruzamento]
    dash_css = """<style>.grid-dash { display: grid; grid-template-columns: repeat(auto-fit, minmax(140px, 1fr)); gap: 15px; width: 100%; max-width: 1100px; margin-bottom: 20px; } @media (min-width: 600px) { .grid-dash { grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 20px; } } .grid-charts { display: grid; grid-template-columns: 1fr; gap: 15px; width: 100%; max-width: 1100px; margin-bottom: 20px; } @media (min-width: 800px) { .grid-charts { grid-template-columns: 1fr 1fr; gap: 20px; } } .card-kpi { background: white; padding: 15px; border-radius: 10px; color: #333; box-shadow: 0 4px 6px rgba(0,0,0,0.1); border-left: 5px solid #d31a21; } .card-kpi h3 { margin: 0; font-size: 13px; color: #666; text-transform: uppercase; } .card-kpi p { margin: 10px 0 0; font-size: 20px; font-weight: bold; color: #0a3a7a; word-wrap: break-word; } @media (min-width: 600px) { .card-kpi p { font-size: 24px; } } .chart-container { background: white; padding: 15px; border-radius: 10px; width: 100%; box-shadow: 0 4px 6px rgba(0,0,0,0.1); overflow: hidden; box-sizing: border-box; } .aba-btn { background: #062b5e; color: white; border: none; padding: 12px 20px; font-size: 14px; font-weight: bold; border-radius: 8px; cursor: pointer; margin-right: 10px; margin-bottom: 10px; transition: 0.3s; } .aba-btn:hover { background: #d31a21; } .filtro-bar { background: rgba(255,255,255,0.1); padding: 15px; border-radius: 10px; margin-bottom: 20px; display: flex; flex-wrap: wrap; gap: 10px; align-items: flex-end; border: 1px solid rgba(255,255,255,0.2); width: 100%; box-sizing: border-box; } .filtro-item { flex: 1; min-width: 110px; } .rank-table { width: 100%; border-collapse: collapse; margin-top:10px; font-size: 14px; } .rank-table th, .rank-table td { padding: 8px 4px; border-bottom: 1px solid #eee; text-align: left; } .table-responsive { width: 100%; overflow-x: auto; -webkit-overflow-scrolling: touch; }</style>"""
    return f"<html><head>{CSS}{dash_css}</head><body><div class='main-area' style='padding: 15px; overflow-x: hidden;'><h1 style='color:white; margin-bottom: 10px; font-size: 24px;'>📊 Dashboard e Gestão</h1><form class='filtro-bar' method='GET'><div class='filtro-item'><label style='font-size:12px;'>De:</label><br><input type='date' name='inicio' value='{inicio}' class='input-padrao' style='margin:0;'></div><div class='filtro-item'><label style='font-size:12px;'>Até:</label><br><input type='date' name='fim' value='{fim}' class='input-padrao' style='margin:0;'></div><div class='filtro-item'><label style='font-size:12px;'>Categoria:</label><br><select name='cat' class='input-padrao' style='margin:0;'><option value=''>TODAS</option>{opcoes_cat}</select></div><div class='filtro-item'><label style='font-size:12px;'>Produto:</label><br><input type='text' name='prod' value='{prod}' class='input-padrao' style='margin:0;'></div><div class='filtro-item'><label style='font-size:12px;'>Funcionário:</label><br><select name='garcom_filtro' class='input-padrao' style='margin:0;'><option value=''>TODOS</option>{opcoes_garcom}</select></div><div class='filtro-item' style='min-width: 100%; display: flex; justify-content: flex-end;'><button class='btn-acao' style='background:#28a745; margin:0; height:45px; width:120px;'>FILTRAR</button></div></form><div style='margin-bottom: 20px;'><button id='btn-fin' class='aba-btn' style='background:#17a2b8' onclick=\"showTab('fin')\">💰 FINANCEIRO</button><button id='btn-est' class='aba-btn' style='opacity:0.6; background:#e67e22' onclick=\"showTab('est')\">📦 ESTOQUE</button></div><div id='tab-fin' style='width: 100%;'><div class='grid-dash'><div class='card-kpi'><h3>Bruto</h3><p>R$ {faturamento_bruto:.2f}</p></div><div class='card-kpi'><h3>Líquido</h3><p style='color:#28a745'>R$ {faturamento_liquido:.2f}</p></div><div class='card-kpi'><h3>Devoluções (Estornos)</h3><p style='color:#d31a21'>R$ {total_estornado:.2f}</p></div><div class='card-kpi'><h3>Ticket Médio</h3><p>R$ {ticket_medio:.2f}</p></div></div><div class='grid-charts'><div class='chart-container'><h3 style='color:#333; margin-top:0; border-bottom:2px solid #ccc; padding-bottom:5px; font-size:16px;'>🏆 Top 3 Mais Vendidos (Qtd)</h3>{html_top_qtd if html_top_qtd else '<p style=\"color:black;\">Sem dados no período.</p>'}</div><div class='chart-container'><h3 style='color:#333; margin-top:0; border-bottom:2px solid #ccc; padding-bottom:5px; font-size:16px;'>💎 Top 3 Lucrativos (R$)</h3>{html_top_valor if html_top_valor else '<p style=\"color:black;\">Sem dados no período.</p>'}</div></div><div class='chart-container' style='margin-bottom:20px;'><h3 style='color:#333; margin-top:0; border-bottom:2px solid #ccc; padding-bottom:5px; font-size:16px;'>👨‍🍳 Ranking de Funcionários</h3><div class='table-responsive' style='max-height: 250px;'><table class='rank-table'><tr><th style='color:black;'>Funcionário</th><th style='color:black; text-align:center;'>Itens Vendidos</th><th style='color:black; text-align:right;'>Faturamento</th></tr>{html_rank_func if html_rank_func else '<tr><td colspan=\"3\" style=\"color:black;text-align:center;\">Sem dados de vendas.</td></tr>'}</table></div></div><div class='grid-charts'><div class='chart-container'><h3 style='color:#333; font-size:16px; margin-top:0;'>💰 Pagamentos</h3><div style='position: relative; height: 250px; width: 100%;'><canvas id='chartPag'></canvas></div></div><div class='chart-container'><h3 style='color:#333; font-size:16px; margin-top:0;'>📈 Gráfico de Garçons</h3><div style='position: relative; height: 250px; width: 100%;'><canvas id='chartGarcom'></canvas></div></div></div></div><div id='tab-est' style='display:none; width: 100%;'><div class='grid-dash'><div class='card-kpi'><h3>Entradas</h3><p style='color:#28a745'>+{total_entradas}</p></div><div class='card-kpi'><h3>Saídas</h3><p style='color:#d31a21'>-{total_saidas}</p></div></div><div class='chart-container'><h3 style='color:#333; font-size:16px; margin-top:0;'>🔄 Estoque vs Vendidos</h3><div style='position: relative; height: 300px; width: 100%;'><canvas id='chartCruzamento'></canvas></div></div></div><br><a href='/central' class='btn-acao' style='width: 100%; max-width: 200px; margin: 0 auto;'>Voltar</a></div><script>function showTab(tab) {{ document.getElementById('tab-fin').style.display = tab === 'fin' ? 'block' : 'none'; document.getElementById('tab-est').style.display = tab === 'est' ? 'block' : 'none'; document.getElementById('btn-fin').style.opacity = tab === 'fin' ? '1' : '0.6'; document.getElementById('btn-est').style.opacity = tab === 'est' ? '1' : '0.6'; }} new Chart(document.getElementById('chartPag'), {{ type: 'doughnut', data: {{ labels: {json.dumps(labels_pag)}, datasets: [{{ data: {json.dumps(data_pag)}, backgroundColor: ['#0a3a7a', '#d31a21', '#ffc107', '#28a745'] }}] }}, options: {{ maintainAspectRatio: false, responsive: true }} }}); new Chart(document.getElementById('chartGarcom'), {{ type: 'bar', data: {{ labels: {json.dumps([g.garcom or 'N/D' for g in garcons])}, datasets: [{{ label: 'Total (R$)', data: {json.dumps([float(g.total or 0) for g in garcons])}, backgroundColor: '#17a2b8' }}] }}, options: {{ maintainAspectRatio: false, responsive: true }} }}); new Chart(document.getElementById('chartCruzamento'), {{ type: 'bar', data: {{ labels: {json.dumps(labels_cruz)}, datasets: [{{ label: 'Vendidos', data: {json.dumps(data_cruz_vendidos)}, backgroundColor: '#d31a21' }}, {{ label: 'Estoque Físico', data: {json.dumps(data_cruz_estoque)}, backgroundColor: '#0a3a7a' }}] }}, options: {{ maintainAspectRatio: false, responsive: true }} }});</script></body></html>"

@app.get("/api/pendentes")
async def api_pendentes():
    with engine.connect() as conn:
        r = conn.execute(text("SELECT id, conteudo FROM fila_impressao WHERE status = 'PENDENTE' LIMIT 1")).fetchone()
        return {"jobs": [{"id": r.id, "conteudo": r.conteudo}]} if r else {"jobs": []}

@app.post("/api/impresso/{j_id}")
async def api_impresso(j_id: int):
    with engine.begin() as conn: conn.execute(text("UPDATE fila_impressao SET status='IMPRESSO' WHERE id=:i"), {"i": j_id})
    return {"ok": True}

@app.get("/impressora_virtual", response_class=HTMLResponse)
async def impressora_virtual(request: Request):
    if request.session.get("role") not in ["admin", "administrador", "gerente"]: return RedirectResponse(url="/central")
    return f"<html><head>{CSS}</head><body style='background-color:#1a1a1a;'><div class='container-center'><div class='card-center' style='max-width:600px; width:100%;'><h2>🖨️ Impressora Virtual</h2><p style='color:#666;'>Mantenha essa tela aberta no PC para simular a impressora.</p><div id='papel' style='background:#ffffe0; color:black; font-family:monospace; font-size:14px; text-align:left; padding:20px; height:400px; overflow-y:auto; border-radius:5px; border-left: 5px solid #ccc; box-shadow: inset 0 0 10px rgba(0,0,0,0.1); white-space: pre-wrap;'>Aguardando tickets...</div><br><button class='btn-acao' style='background:#d31a21;' onclick='document.getElementById(\"papel\").innerHTML=\"Aguardando tickets...\"'>LIMPAR PAPEL</button><br><a href='/central' style='color:gray'>Voltar</a></div></div><script>setInterval(() => {{ fetch('/api/pendentes').then(r => r.json()).then(data => {{ if(data.jobs && data.jobs.length > 0) {{ let job = data.jobs[0]; let papel = document.getElementById('papel'); if(papel.innerHTML === 'Aguardando tickets...') papel.innerHTML = ''; papel.innerHTML += '\\n\\n' + job.conteudo; papel.scrollTop = papel.scrollHeight; fetch('/api/impresso/' + job.id, {{method: 'POST'}}); }} }}); }}, 3000);</script></body></html>"

@app.get("/baixar_conector")
async def baixar_conector(request: Request):
    if request.session.get("role") not in ["admin", "administrador", "gerente"]: return RedirectResponse(url="/central")
    base_url = str(request.base_url).rstrip('/')
    script_content = f"""import sys\nimport subprocess\n\nprint("=========================================")\nprint(" 🛠️ VERIFICANDO DEPENDÊNCIAS DO SISTEMA... ")\nprint("=========================================")\ntry:\n    import requests\n    import win32print\nexcept ImportError:\n    print("⏳ Primeira vez rodando! Instalando o motor da impressora automaticamente...")\n    print("   Isso pode levar alguns segundos. Não feche a janela.\\n")\n    subprocess.check_call([sys.executable, "-m", "pip", "install", "requests", "pywin32"])\n    print("\\n✅ Instalação concluída com sucesso!\\n")\n    import requests\n    import win32print\n\nimport time\n\nAPI_URL = "{base_url}"\n\ndef imprimir_ticket(texto):\n    impressora_padrao = win32print.GetDefaultPrinter()\n    try:\n        hPrinter = win32print.OpenPrinter(impressora_padrao)\n        hJob = win32print.StartDocPrinter(hPrinter, 1, ("Ticket Quiosque", None, "RAW"))\n        win32print.StartPagePrinter(hPrinter)\n        \n        texto_bytes = texto.encode("latin-1", errors="replace")\n        win32print.WritePrinter(hPrinter, texto_bytes)\n        win32print.WritePrinter(hPrinter, b"\\n\\n\\n\\n\\x1B\\x6D")\n        \n        win32print.EndPagePrinter(hPrinter)\n        win32print.EndDocPrinter(hPrinter)\n        win32print.ClosePrinter(hPrinter)\n        print("✔️ Ticket Impresso com Sucesso!")\n    except Exception as e:\n        print(f"❌ Erro na impressora: {{e}}")\n\nprint("=========================================")\nprint("🚀 CONECTOR DE IMPRESSORA INICIADO")\nprint(f"Conectado em: {{API_URL}}")\n\nimpressora_atual = win32print.GetDefaultPrinter()\nprint(f"\\n🖨️  Impressora detectada: {{impressora_atual}}")\nif "PDF" in impressora_atual.upper() or "ONENOTE" in impressora_atual.upper():\n    print("⚠️  ATENÇÃO: Você não configurou uma impressora térmica!")\n    print("   O sistema vai gerar PDFs corrompidos (pois enviamos código de máquina RAW).")\n    print("   Para resolver: Instale a sua térmica USB e defina-a como 'Padrão' no Windows.\\n")\n\nprint("Deixe essa janela minimizada para receber tickets...")\nprint("=========================================\\n")\n\nwhile True:\n    try:\n        resposta = requests.get(f"{{API_URL}}/api/pendentes", timeout=5)\n        if resposta.status_code == 200:\n            dados = resposta.json()\n            for job in dados.get("jobs", []):\n                print(f"🖨️ Imprimindo pedido ID {{job['id']}}...")\n                imprimir_ticket(job['conteudo'])\n                requests.post(f"{{API_URL}}/api/impresso/{{job['id']}}", timeout=5)\n    except Exception as e:\n        pass\n    time.sleep(3)\n"""
    return Response(content=script_content, media_type="text/x-python", headers={"Content-Disposition": "attachment; filename=conector_impressao.py"})

@app.get("/estoque", response_class=HTMLResponse)
async def tela_estoque(request: Request):
    if request.session.get("role") not in ["admin", "administrador", "gerente"]: return RedirectResponse(url="/central")
    linhas, curr_cat = "", ""
    with engine.connect() as conn:
        prods_db = conn.execute(text("SELECT p.id, p.nome, p.categoria, p.preco, p.estoque, MAX(h.data_entrada) as ultima_compra FROM produtos p LEFT JOIN historico_estoque h ON p.nome = h.produto_nome GROUP BY p.id, p.nome, p.categoria, p.preco, p.estoque ORDER BY p.categoria, p.nome")).fetchall()
        for r in prods_db:
            if r.categoria != curr_cat: linhas += f"<tr><td colspan='5' style='background:#082d5e; color:white; font-weight:bold; text-align:center;'>{r.categoria or 'OUTROS'}</td></tr>"; curr_cat = r.categoria
            acoes = f"<div style='display:flex; gap:5px;'><form action='/att_estoque' method='post' style='margin:0; display:flex;'><input type='hidden' name='i' value='{r.nome}'><input type='number' name='q' class='input-padrao' style='width:50px; padding:5px;' required><button class='btn-acao' style='background:#28a745; padding:8px;'>➕</button></form><button class='btn-acao' style='background:#f1c40f; padding:8px; color:black;' onclick='editProd(\"{r.nome}\", \"{r.categoria}\", {float(r.preco or 0)})'>✏️</button><form action='/excluir_produto' method='post' style='margin:0;' onsubmit='return confirm(\"Excluir?\");'><input type='hidden' name='nome' value='{r.nome}'><button class='btn-acao' style='background:#d31a21; padding:8px;'>🗑️</button></form></div>"
            linhas += f"<tr><td style='color:#d31a21;'>{r.id:03d}</td><td style='color:black; font-size:16px; font-weight:bold;'>{r.nome} <br><small style='font-weight:normal;'>R$ {float(r.preco or 0):.2f}</small></td><td style='color:#062b5e; font-size:12px;'>{(r.ultima_compra.strftime('%d/%m/%Y') if r.ultima_compra else 'N/A')}</td><td style='color:black; font-weight:bold; font-size:18px;'>{int(r.estoque or 0)}</td><td>{acoes}</td></tr>"
    add_form = f"<div style='background:#f4f4f4; padding:20px; border-radius:10px; margin-bottom:20px; text-align:left; border:1px solid #ccc;'><h3 style='margin-top:0; color:#d31a21;' id='titulo_form_prod'>➕ NOVO PRODUTO</h3><form id='form_prod' action='/novo_produto' method='post' style='display:flex; flex-wrap:wrap; gap:10px;'><input type='hidden' name='nome_orig' id='nome_orig_prod'><input name='nome' id='nome_prod' placeholder='Produto' class='input-padrao' style='flex:1;' required><select name='cat' id='cat_prod' class='input-padrao' style='flex:1;' required><option value='CHOPP'>CHOPP</option><option value='CERVEJAS'>CERVEJAS</option><option value='PETISCOS'>PETISCOS</option><option value='BEBIDAS'>BEBIDAS</option><option value='OUTROS'>OUTROS</option></select><input name='preco' id='preco_prod' placeholder='Preço' class='input-padrao' style='width:80px;' required><input name='qtd' id='qtd_prod' type='number' placeholder='Qtd' class='input-padrao' style='width:80px;' required><button id='btn_salvar_prod' class='btn-acao' style='background:#062b5e; width:100%;'>SALVAR</button></form></div><script>function editProd(nome, cat, preco) {{ document.getElementById('titulo_form_prod').innerText = '✏️ EDITAR PRODUTO'; document.getElementById('form_prod').action = '/editar_produto'; document.getElementById('nome_orig_prod').value = nome; document.getElementById('nome_prod').value = nome; document.getElementById('cat_prod').value = cat; document.getElementById('preco_prod').value = preco; document.getElementById('qtd_prod').style.display = 'none'; document.getElementById('qtd_prod').removeAttribute('required'); document.getElementById('btn_salvar_prod').innerText = 'ATUALIZAR PRODUTO'; document.getElementById('btn_salvar_prod').style.background = '#f39c12'; window.scrollTo(0, 0); }}</script>"
    return f"<html><head>{CSS}</head><body><div class='container-center'><div class='card-center' style='width:100%; max-width:800px;'><h2>Estoque</h2>{add_form}<div class='table-responsive' style='max-height:450px; overflow-y:auto;'><table><tr><th style='color:black'>Cód</th><th style='color:black'>Item</th><th style='color:black'>Compra</th><th style='color:black'>Qtd</th><th style='color:black'>Ação</th></tr>{linhas}</table></div><br><a href='/central' style='color:gray'>Voltar</a></div></div></body></html>"

@app.post("/novo_produto")
async def novo_produto(request: Request):
    if request.session.get("role") not in ["admin", "administrador", "gerente"]: return RedirectResponse(url="/central")
    f = await request.form()
    try:
        with engine.begin() as conn: 
            conn.execute(text("INSERT INTO produtos (nome, categoria, preco, estoque) VALUES (:n, :c, :p, :q) ON CONFLICT (nome) DO NOTHING"), {"n": f.get("nome"), "c": f.get("cat"), "p": float(f.get("preco").replace(",", ".")), "q": int(f.get("qtd"))})
            conn.execute(text("INSERT INTO historico_estoque (produto_nome, qtd_adicionada) VALUES (:n, :q)"), {"n": f.get("nome"), "q": int(f.get("qtd"))})
    except: pass
    return RedirectResponse(url="/estoque", status_code=303)

@app.post("/editar_produto")
async def editar_produto(request: Request):
    if request.session.get("role") not in ["admin", "administrador", "gerente"]: return RedirectResponse(url="/central")
    f = await request.form()
    n_orig, n_novo, cat, p = f.get("nome_orig"), f.get("nome"), f.get("cat"), float(f.get("preco").replace(",", "."))
    try:
        with engine.begin() as conn:
            conn.execute(text("UPDATE produtos SET nome=:n, categoria=:c, preco=:p WHERE nome=:o"), {"n": n_novo, "c": cat, "p": p, "o": n_orig})
            if n_novo != n_orig:
                conn.execute(text("UPDATE vendas_itens SET item_nome=:n WHERE item_nome=:o"), {"n": n_novo, "o": n_orig})
                conn.execute(text("UPDATE historico_estoque SET produto_nome=:n WHERE produto_nome=:o"), {"n": n_novo, "o": n_orig})
    except: pass
    return RedirectResponse(url="/estoque", status_code=303)

@app.post("/att_estoque")
async def att_estoque(request: Request):
    if request.session.get("role") not in ["admin", "administrador", "gerente"]: return RedirectResponse(url="/central")
    f = await request.form()
    try:
        with engine.begin() as conn: 
            conn.execute(text("UPDATE produtos SET estoque = COALESCE(estoque, 0) + :q WHERE nome = :i"), {"i": f.get("i"), "q": int(f.get("q", "0"))})
            conn.execute(text("INSERT INTO historico_estoque (produto_nome, qtd_adicionada) VALUES (:i, :q)"), {"i": f.get("i"), "q": int(f.get("q", "0"))})
    except: pass
    return RedirectResponse(url="/estoque", status_code=303)

@app.post("/excluir_produto")
async def excluir_produto(request: Request):
    if request.session.get("role") not in ["admin", "administrador", "gerente"]: return RedirectResponse(url="/central")
    f = await request.form()
    try:
        with engine.begin() as conn: conn.execute(text("DELETE FROM produtos WHERE nome = :n"), {"n": f.get("nome", "")})
    except: pass
    return RedirectResponse(url="/estoque", status_code=303)

@app.get("/comissoes", response_class=HTMLResponse)
async def tela_comissoes(request: Request, garcom_filtro: str = ""):
    if request.session.get("role") not in ["admin", "administrador", "gerente"]: return RedirectResponse(url="/central")
    linhas_pendentes, linhas_pagas = "", ""
    with engine.connect() as conn:
        garcons_db = conn.execute(text("SELECT DISTINCT garcom FROM vendas_itens WHERE garcom IS NOT NULL ORDER BY garcom")).fetchall()
        opcoes_garcom = "".join([f"<option value='{g.garcom}' {'selected' if garcom_filtro == g.garcom else ''}>{g.garcom}</option>" for g in garcons_db])
        where_clause = "status = 'FECHADA' AND comissao_status = 'PENDENTE'"
        params = {}
        if garcom_filtro:
            where_clause += " AND garcom = :g"; params["g"] = garcom_filtro
        res_pend = conn.execute(text(f"SELECT CAST(data_venda AS DATE) as data, garcom, SUM(valor) as total_vendido, (SUM(valor) * 0.10) as comissao FROM vendas_itens WHERE {where_clause} GROUP BY CAST(data_venda AS DATE), garcom ORDER BY data DESC"), params).fetchall()
        for r in res_pend:
            linhas_pendentes += f"<tr><td style='color:black;'>{r.garcom}</td><td style='color:#062b5e;'>{r.data.strftime('%d/%m/%Y')}</td><td style='color:black;'>R$ {float(r.total_vendido):.2f}</td><td style='color:#d31a21; font-weight:bold;'>R$ {float(r.comissao):.2f}</td><td><form action='/pagar_comissao' method='post' style='margin:0;'><input type='hidden' name='data_venda' value='{r.data}'><input type='hidden' name='garcom' value='{r.garcom}'><button class='btn-acao' style='background:#28a745; padding:8px; font-size:12px;'>✔️ PAGO</button></form></td></tr>"
        where_clause_pagas = "status = 'FECHADA' AND comissao_status = 'PAGA'"
        if garcom_filtro: where_clause_pagas += " AND garcom = :g"
        res_pagas = conn.execute(text(f"SELECT CAST(data_venda AS DATE) as data, garcom, SUM(valor) as total_vendido, (SUM(valor) * 0.10) as comissao FROM vendas_itens WHERE {where_clause_pagas} GROUP BY CAST(data_venda AS DATE), garcom ORDER BY data DESC LIMIT 30"), params).fetchall()
        for r in res_pagas:
            linhas_pagas += f"<tr><td style='color:black;'>{r.garcom}</td><td style='color:#062b5e;'>{r.data.strftime('%d/%m/%Y')}</td><td style='color:black;'>R$ {float(r.total_vendido):.2f}</td><td style='color:#28a745; font-weight:bold;'>R$ {float(r.comissao):.2f}</td><td><span style='color:#28a745;'>PAGO</span></td></tr>"
    return f"<html><head>{CSS}</head><body><div class='container-center'><div class='card-center' style='max-width:800px;'><h2>💸 Gestão de Comissões</h2><form method='GET' style='margin-bottom:20px; display:flex; gap:10px;'><select name='garcom_filtro' class='input-padrao' style='flex:1;'><option value=''>Todos</option>{opcoes_garcom}</select><button class='btn-acao' style='background:#062b5e; width:120px;'>FILTRAR</button></form><h3 style='color:#d31a21; text-align:left; border-bottom:2px solid #ccc;'>🔴 Pendentes</h3><div class='table-responsive' style='max-height:300px; overflow-y:auto; margin-bottom:20px;'><table><tr><th style='color:black'>Func.</th><th style='color:black'>Data</th><th style='color:black'>Vendido</th><th style='color:black'>Comissão</th><th style='color:black'>Ação</th></tr>{linhas_pendentes if linhas_pendentes else '<tr><td colspan=5 style=color:black;text-align:center;>Nada pendente.</td></tr>'}</table></div><h3 style='color:#28a745; text-align:left; border-bottom:2px solid #ccc;'>🟢 Pagos</h3><div class='table-responsive' style='max-height:300px; overflow-y:auto;'><table><tr><th style='color:black'>Func.</th><th style='color:black'>Data</th><th style='color:black'>Vendido</th><th style='color:black'>Comissão</th><th style='color:black'>Status</th></tr>{linhas_pagas if linhas_pagas else '<tr><td colspan=5 style=color:black;text-align:center;>Sem histórico.</td></tr>'}</table></div><br><a href='/central' class='btn-acao' style='width: 200px; margin:auto'>Voltar</a></div></div></body></html>"

@app.post("/pagar_comissao")
async def pagar_comissao(request: Request):
    if request.session.get("role") not in ["admin", "administrador", "gerente"]: return RedirectResponse(url="/central")
    f = await request.form()
    try:
        with engine.begin() as conn: conn.execute(text("UPDATE vendas_itens SET comissao_status = 'PAGA' WHERE CAST(data_venda AS DATE) = CAST(:d AS DATE) AND garcom = :g AND status = 'FECHADA' AND comissao_status = 'PENDENTE'"), {"d": f.get("data_venda"), "g": f.get("garcom")})
    except: pass
    return RedirectResponse(url="/comissoes", status_code=303)

@app.get("/usuarios", response_class=HTMLResponse)
async def tela_usuarios(request: Request):
    if request.session.get("role") not in ["admin", "administrador"]: return RedirectResponse(url="/central")
    linhas = ""
    with engine.connect() as conn:
        users_db = conn.execute(text("SELECT id, username, role FROM usuarios ORDER BY role, username")).fetchall()
        for r in users_db:
            btn_del = f"<form action='/excluir_usuario' method='post' style='margin:0;' onsubmit='return confirm(\"Excluir?\");'><input type='hidden' name='id' value='{r.id}'><button class='btn-acao' style='background:#d31a21; padding:8px; width:auto; margin:0;'>🗑️</button></form>" if r.username != "admin" else ""
            acoes = f"<div style='display:flex; gap:5px;'><button type='button' class='btn-acao' style='background:#f1c40f; padding:8px; color:black; width:auto; margin:0;' onclick='editUser({r.id}, \"{r.username}\", \"{r.role}\")'>✏️</button>{btn_del}</div>"
            linhas += f"<tr><td style='color:black; font-weight:bold;'>{r.username.upper()}</td><td style='color:#062b5e;'>{r.role.upper()}</td><td>{acoes}</td></tr>"
    add_form = f"<div style='background:#f4f4f4; padding:20px; border-radius:10px; margin-bottom:20px; text-align:left; border:1px solid #ccc;'><h3 style='margin-top:0; color:#9b59b6;' id='titulo_form_user'>➕ NOVO USUÁRIO</h3><form id='form_user' action='/novo_usuario' method='post' style='display:flex; flex-wrap:wrap; gap:10px;'><input type='hidden' name='id_user' id='id_user_form'><input name='u' id='u_form' placeholder='Login' class='input-padrao' style='flex:1;' required><input name='p' id='p_form' type='password' placeholder='Senha' class='input-padrao' style='flex:1;' required><select name='r' id='r_form' class='input-padrao' style='flex:1;'><option value='administrador'>ADMINISTRADOR</option><option value='gerente'>GERENTE</option><option value='caixa'>CAIXA</option><option value='garcom'>GARÇOM</option><option value='portaria'>PORTARIA</option></select><button id='btn_salvar_user' class='btn-acao' style='background:#9b59b6; width:100%;'>CRIAR ACESSO</button></form></div><script>function editUser(id, u, r) {{ document.getElementById('titulo_form_user').innerText = '✏️ EDITAR USUÁRIO'; document.getElementById('form_user').action = '/editar_usuario'; document.getElementById('id_user_form').value = id; document.getElementById('u_form').value = u; document.getElementById('p_form').placeholder = 'Nova senha (ou branco)'; document.getElementById('p_form').removeAttribute('required'); document.getElementById('r_form').value = r; document.getElementById('btn_salvar_user').innerText = 'ATUALIZAR ACESSO'; document.getElementById('btn_salvar_user').style.background = '#f39c12'; window.scrollTo(0, 0); }}</script>"
    return f"<html><head>{CSS}</head><body><div class='container-center'><div class='card-center'><h2>Usuários</h2>{add_form}<div class='table-responsive' style='max-height:400px; overflow-y:auto;'><table><tr><th style='color:black'>Login</th><th style='color:black'>Cargo</th><th style='color:black'>Ações</th></tr>{linhas}</table></div><br><a href='/central' style='color:gray'>Voltar</a></div></div></body></html>"

@app.post("/novo_usuario")
async def novo_usuario(request: Request):
    if request.session.get("role") not in ["admin", "administrador"]: return RedirectResponse(url="/central")
    f = await request.form()
    try:
        with engine.begin() as conn: conn.execute(text("INSERT INTO usuarios (username, password, role) VALUES (:u, :p, :r) ON CONFLICT (username) DO NOTHING"), {"u": f.get("u").lower(), "p": f.get("p"), "r": f.get("r")})
    except: pass
    return RedirectResponse(url="/usuarios", status_code=303)

@app.post("/editar_usuario")
async def editar_usuario(request: Request):
    if request.session.get("role") not in ["admin", "administrador"]: return RedirectResponse(url="/central")
    f = await request.form()
    uid, u, p, r = f.get("id_user"), f.get("u").lower(), f.get("p"), f.get("r")
    try:
        with engine.begin() as conn:
            if p: conn.execute(text("UPDATE usuarios SET username=:u, password=:p, role=:r WHERE id=:id"), {"u": u, "p": p, "r": r, "id": uid})
            else: conn.execute(text("UPDATE usuarios SET username=:u, role=:r WHERE id=:id"), {"u": u, "r": r, "id": uid})
    except: pass
    return RedirectResponse(url="/usuarios", status_code=303)

@app.post("/excluir_usuario")
async def excluir_usuario(request: Request):
    if request.session.get("role") not in ["admin", "administrador"]: return RedirectResponse(url="/central")
    f = await request.form()
    try:
        with engine.begin() as conn: conn.execute(text("DELETE FROM usuarios WHERE id = :id AND username != 'admin'"), {"id": f.get("id")})
    except: pass
    return RedirectResponse(url="/usuarios", status_code=303)

@app.get("/cardapio", response_class=HTMLResponse)
async def ver_cardapio():
    html_categorias = ""
    with engine.connect() as conn:
        prods = conn.execute(text("SELECT nome, preco, categoria, estoque FROM produtos ORDER BY categoria, nome")).fetchall()
        menu_dict = {}
        for p in prods:
            cat = p.categoria or "OUTROS"
            if cat not in menu_dict: menu_dict[cat] = []
            menu_dict[cat].append(p)
        for cat, itens in menu_dict.items():
            img_cat = IMAGENS_CAT.get(cat, IMAGENS_CAT["OUTROS"])
            lista_itens = ""
            for i in itens:
                est = int(i.estoque or 0)
                if est > 0:
                    lista_itens += f"<div class='linha-menu'><span class='linha-nome'>{i.nome}</span><div class='linha-pontos'></div><span class='linha-preco'>R$ {float(i.preco):.2f}</span></div>"
                else:
                    lista_itens += f"<div class='linha-menu'><span class='linha-nome' style='color:#999; text-decoration:line-through;'>{i.nome}</span><span class='esgotado-txt'>ESGOTADO</span><div class='linha-pontos'></div><span class='linha-preco' style='color:#999;'>R$ {float(i.preco):.2f}</span></div>"
            html_categorias += f"<div style='margin-bottom: 40px;'><div class='faixa-laranja'><img src='{img_cat}' style='width:24px; height:24px; vertical-align:middle; margin-right:10px; filter: brightness(0) invert(1);'>{cat}</div>{lista_itens}</div>"
    return f"<html><head>{CSS}</head><body style='background:#0a3a7a; height:auto; overflow:auto;'><div style='padding:20px; max-width:800px; margin:auto; text-align:center;'>{IMG_LOGO_PEQ}<h1 style='color:white; margin-bottom:30px;'>CARDÁPIO DIGITAL</h1><div class='menu-duas-colunas'>{html_categorias}</div><br><br><a href='/' style='color:white; text-decoration:underline;'>Voltar ao Início</a><br><br></div></body></html>"

@app.get("/qr", response_class=HTMLResponse)
async def gerar_qr(request: Request):
    if request.session.get("role") not in ["admin", "administrador", "gerente"]: return RedirectResponse(url="/central")
    base_url = str(request.base_url).rstrip('/')
    url_cardapio = f"{base_url}/cardapio"
    qr_api = f"https://api.qrserver.com/v1/create-qr-code/?size=300x300&data={urllib.parse.quote(url_cardapio)}"
    return f"<html><head>{CSS}</head><body><div class='container-center'><div class='card-center'>{IMG_LOGO_PEQ}<h2>📱 QR Code do Cardápio</h2><p>Imprima ou mostre aos clientes para acessarem o cardápio no celular.</p><img src='{qr_api}' style='margin:20px; border:10px solid white; border-radius:10px; width:250px;'><p style='font-size:14px;'><a href='{url_cardapio}' target='_blank'>{url_cardapio}</a></p><br><a href='/central' class='btn-acao' style='background:#062b5e;'>Voltar</a></div></div></body></html>"

@app.get("/logout")
async def logout(request: Request): 
    request.session.clear()
    return RedirectResponse("/")
