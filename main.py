from fastapi import FastAPI, Form, Request, Response
from fastapi.responses import HTMLResponse, RedirectResponse, FileResponse
from sqlalchemy import create_engine, text
from starlette.middleware.sessions import SessionMiddleware
from datetime import datetime, date
import json
import urllib.parse
import os

app = FastAPI()
app.add_middleware(SessionMiddleware, secret_key="brahma_riacho_mall_2024")

DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://postgres:GNlZnHiuKAcFnpgXhwILfigqKCNkaHqx@interchange.proxy.rlwy.net:44559/railway")
engine = create_engine(DATABASE_URL, pool_pre_ping=True)

MENU_INICIAL = {
    "CHOPP": [("Caneca 350ml", 11.9), ("Descartável 500ml", 13.9), ("Tulipa 700ml", 17.9), ("Torre 2.5L", 84.9), ("Torre 3.5L", 99.9)],
    "CERVEJAS": [("Original 600ml", 12.9), ("Amstel 600ml", 12.0), ("Brahma Duplo Malte", 12.0), ("Heineken 600ml", 16.9), ("Spaten LN", 8.9), ("Corona LN", 10.0), ("Heineken LN", 10.0), ("Stella LN", 8.9), ("Heineken Zero", 10.0)],
    "PETISCOS": [("Fritas", 21.9), ("Fritas c/ Queijo", 25.9), ("Fritas Cheddar/Bacon", 27.9), ("Kibe 10un", 34.9), ("Kibe c/ Queijo", 37.9), ("Frango Passarinho", 28.9), ("Carne Sol c/ Fritas", 54.9), ("Calabresa Acebolada", 22.9), ("Tábua Frios", 34.9)],
    "BEBIDAS": [("Caipirinha", 14.9), ("Caipiroska Absolut", 16.9), ("Gin Tônica", 24.9), ("Gin Tropical", 26.9), ("Cozumel 600ml", 14.9), ("Refri Lata", 4.9), ("Soda Italiana", 13.9), ("Suco Lata", 5.9), ("Red Bull", 13.0), ("Água", 3.9)]
}

# --- CRIAÇÃO DAS TABELAS ---
with engine.begin() as conn:
    conn.execute(text("""
        CREATE TABLE IF NOT EXISTS clientes (id SERIAL PRIMARY KEY, nome_completo TEXT NOT NULL, cpf TEXT UNIQUE NOT NULL, data_nascimento DATE, contato TEXT, email TEXT);
        CREATE TABLE IF NOT EXISTS pulseiras (id SERIAL PRIMARY KEY, numero_pulseira TEXT NOT NULL, cliente_cpf TEXT REFERENCES clientes(cpf), total_conta DECIMAL(10,2) DEFAULT 7.00);
        CREATE TABLE IF NOT EXISTS vendas_itens (id SERIAL PRIMARY KEY, pulseira_num TEXT, item_nome TEXT, valor DECIMAL(10,2), data_venda DATE DEFAULT CURRENT_DATE, hora_venda TIME DEFAULT CURRENT_TIME);
        CREATE TABLE IF NOT EXISTS produtos (id SERIAL PRIMARY KEY, nome TEXT UNIQUE NOT NULL);
        CREATE TABLE IF NOT EXISTS fila_impressao (id SERIAL PRIMARY KEY, conteudo TEXT, status TEXT DEFAULT 'PENDENTE', data_criacao TIMESTAMP DEFAULT CURRENT_TIMESTAMP);
        CREATE TABLE IF NOT EXISTS historico_estoque (id SERIAL PRIMARY KEY, produto_nome TEXT, qtd_adicionada INT, data_entrada DATE DEFAULT CURRENT_DATE);
        CREATE TABLE IF NOT EXISTS usuarios (id SERIAL PRIMARY KEY, username TEXT UNIQUE NOT NULL, password TEXT NOT NULL, role TEXT NOT NULL);
        CREATE TABLE IF NOT EXISTS caixa_movimentos (id SERIAL PRIMARY KEY, tipo TEXT, valor DECIMAL(10,2), descricao TEXT, data_registro TIMESTAMP DEFAULT CURRENT_TIMESTAMP, usuario TEXT);
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
    "ALTER TABLE pulseiras ADD COLUMN IF NOT EXISTS data_fechamento TIMESTAMP;",
    "ALTER TABLE vendas_itens ADD COLUMN IF NOT EXISTS data_venda DATE DEFAULT CURRENT_DATE;",
    "ALTER TABLE vendas_itens ADD COLUMN IF NOT EXISTS hora_venda TIME DEFAULT CURRENT_TIME;",
    "ALTER TABLE vendas_itens ADD COLUMN IF NOT EXISTS comissao_status TEXT DEFAULT 'PENDENTE';",
    "ALTER TABLE pulseiras ADD COLUMN IF NOT EXISTS nfe_solicitada BOOLEAN DEFAULT FALSE;",
    "ALTER TABLE pulseiras ADD COLUMN IF NOT EXISTS cpf_nota TEXT;"
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

def formata_linha(esq, dir, width=32):
    dir_str = str(dir)
    esq_str = str(esq)[:width - len(dir_str) - 1]
    return esq_str + " " * (width - len(esq_str) - len(dir_str)) + dir_str

# --- CSS E DESIGN ATUALIZADO ---
CSS = """
<meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no">
<meta name="apple-mobile-web-app-capable" content="yes">
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
    
    /* ESTILOS DO SWITCH DA NOTA FISCAL */
    .switch { position: relative; display: inline-block; width: 50px; height: 24px; }
    .switch input { opacity: 0; width: 0; height: 0; }
    .slider { position: absolute; cursor: pointer; top: 0; left: 0; right: 0; bottom: 0; background-color: #ccc; transition: .4s; border-radius: 24px; }
    .slider:before { position: absolute; content: ""; height: 18px; width: 18px; left: 3px; bottom: 3px; background-color: white; transition: .4s; border-radius: 50%; }
    input:checked + .slider { background-color: #28a745; }
    input:checked + .slider:before { transform: translateX(26px); }
    
    @media (max-width: 768px) {
        body { height: auto; overflow: auto; }
        .layout-vendas { display: flex; flex-direction: column; height: auto; min-height: 100vh; }
        .menu-lateral { width: 100%; flex-direction: row; overflow-x: auto; padding: 10px; border-right: none; border-bottom: 2px solid rgba(255,255,255,0.1); display: flex; gap: 8px; flex-shrink: 0; white-space: nowrap; -webkit-overflow-scrolling: touch; }
        .btn-menu { padding: 10px 15px; font-size: 14px; text-align: center; flex: 0 0 auto; justify-content: center; }
        .main-area { display: flex; overflow: visible; padding: 15px; flex-shrink: 0; width: 100%; }
        .grid-produtos { grid-template-columns: repeat(auto-fill, minmax(130px, 1fr)); gap: 10px; }
        .prod-card { min-height: 110px; padding: 10px; }
        .prod-card b { font-size: 13px; }
        .prod-card span { font-size: 14px; }
        .comanda-lateral { width: 100%; display: flex; border-left: none; border-top: 5px solid #d31a21; flex-shrink: 0; }
        .card-center { width: 95%; padding: 20px; }
    }
</style>
"""

IMG_LOGO = """<div style='display:flex; justify-content:center; margin-bottom:20px;'><img src='https://upload.wikimedia.org/wikipedia/commons/thumb/1/18/Brahma_Logo.svg/512px-Brahma_Logo.svg.png' class='logo-central' style='margin:0;'></div>"""
IMG_LOGO_PEQ = """<div style='display:flex; justify-content:center; margin-bottom:15px;'><img src='https://upload.wikimedia.org/wikipedia/commons/thumb/1/18/Brahma_Logo.svg/512px-Brahma_Logo.svg.png' class='logo-peq' style='margin:0;'></div>"""

@app.get("/sw.js")
async def get_sw(): return Response(content="self.addEventListener('fetch', e => {});", media_type="application/javascript")

@app.get("/", response_class=HTMLResponse)
async def login_page(): return f"""<html><head>{CSS}</head><body><div class='container-center'><div class='card-center'>{IMG_LOGO}<h2>Acesso ao Sistema</h2><form action='/login' method='post'><input class='input-padrao' name='user' placeholder='Usuário' required><input class='input-padrao' name='pw' type='password' placeholder='Senha' required><button class='btn-acao' style='padding:15px; font-size:18px;'>ENTRAR</button></form><br><a href='/cardapio' style='color:#062b5e; font-weight:bold; text-decoration:underline;'>Ver Cardápio Digital</a></div></div></body></html>"""

@app.post("/login")
async def login(request: Request):
    f = await request.form()
    u, p = f.get("user", "").strip().lower(), f.get("pw", "")
    with engine.connect() as conn:
        user = conn.execute(text("SELECT username, role FROM usuarios WHERE username = :u AND password = :p"), {"u": u, "p": p}).fetchone()
        if user:
            request.session["user"], request.session["role"] = user.username, user.role
            return RedirectResponse(url="/central", status_code=303)
    return HTMLResponse("<script>alert('Usuário ou Senha incorretos!'); window.location.href='/';</script>")

@app.get("/central", response_class=HTMLResponse)
async def central(request: Request):
    user, role = request.session.get("user"), request.session.get("role")
    if not user: return RedirectResponse(url="/")
    botoes = ""
    if role in ["admin", "gerente", "garcom", "caixa", "portaria"]:
        botoes += f"<a href='/cadastro' class='btn-acao' style='background:#d31a21'>➕ NOVO CADASTRO</a><a href='/buscar' class='btn-acao'>🔍 BUSCAR / ABRIR NOVA PULSEIRA</a>"
    if role in ["admin", "gerente", "garcom", "caixa"]:
        botoes += f"<a href='/vendas' class='btn-acao' style='background:#28a745'>🛒 CAIXA / LANÇAR ITENS</a><a href='/fechar_conta' class='btn-acao' style='background:#333'>🔒 FECHAR CONTA</a><a href='/caixa' class='btn-acao' style='background:#e67e22'>💰 GESTÃO DE CAIXA (SANGRIA)</a>"
    if role in ["admin", "gerente"]:
        botoes += "<a href='/comissoes' class='btn-acao' style='background:#8e44ad'>💸 COMISSÕES DE VENDAS</a><a href='/dashboard' class='btn-acao' style='background:#17a2b8'>📊 DEMONSTRATIVO GESTÃO</a><a href='/estoque' class='btn-acao' style='background:#062b5e'>📦 GESTÃO DE ESTOQUE</a><a href='/qr' class='btn-acao' style='background:#f1c40f; color:black;'>📱 QR CODE DO CARDÁPIO</a>"
    if role == "admin":
        botoes += "<a href='/usuarios' class='btn-acao' style='background:#9b59b6'>👥 GERENCIAR USUÁRIOS</a>"
    return f"<html><head>{CSS}</head><body><div class='container-center'><div class='card-center'>{IMG_LOGO_PEQ}<p style='margin-top:0;'>Logado como: <b>{user.upper()}</b></p>{botoes}<br><a href='/logout' style='color:gray'>Sair do Sistema</a></div></div></body></html>"


# ==========================================
# NOVO MÓDULO: CARDÁPIO DIGITAL (CLIENTE)
# ==========================================
@app.get("/cardapio", response_class=HTMLResponse)
async def cardapio_digital(request: Request):
    html_cats = ""
    with engine.connect() as conn:
        prods = conn.execute(text("SELECT nome, categoria, preco, estoque FROM produtos ORDER BY categoria, nome")).fetchall()
        menu_dict = {}
        for p in prods:
            c = p.categoria or 'OUTROS'
            if c not in menu_dict: menu_dict[c] = []
            menu_dict[c].append(p)
        
        for cat, lista in menu_dict.items():
            html_cats += f"<h2 style='text-align:center; margin-top:30px; color:#f1c40f; border-bottom: 2px solid #d31a21; padding-bottom:5px;'>{cat}</h2><div class='grid-produtos' style='justify-content:center; max-width:800px; margin:auto;'>"
            for p in lista:
                if p.estoque > 0:
                    html_cats += f"<div class='prod-card' style='background:#fff; color:#333; border:2px solid #ccc; cursor:default;'><b style='font-size:16px;'>{p.nome}</b><span style='background:#28a745; color:white; font-size:18px;'>R$ {float(p.preco):.2f}</span></div>"
                else:
                    html_cats += f"<div class='prod-card' style='background:#ffe6e6; color:#999; border:2px solid #d31a21; opacity:0.6; cursor:default;'><b><del style='font-size:16px;'>{p.nome}</del></b><span style='background:#d31a21; color:white; font-size:16px;'>❌ INDISPONÍVEL</span></div>"
            html_cats += "</div>"
            
    return f"""<html><head>{CSS}</head><body style='background:#111; overflow-y:auto;'><div style='padding:30px; width:100%;'>{IMG_LOGO}<h1 style='text-align:center; color:white; margin-bottom:0;'>CARDÁPIO DIGITAL</h1><p style='text-align:center; color:#ccc; margin-top:5px;'>Sincronizado em tempo real</p>{html_cats}<br><br><p style='text-align:center; color:#666;'>© 2024 Quiosque Brahma</p></div></body></html>"""

@app.get("/qr", response_class=HTMLResponse)
async def gerar_qr(request: Request):
    if request.session.get("role") not in ["admin", "gerente"]: return RedirectResponse(url="/central")
    link_cardapio = str(request.base_url) + "cardapio"
    # Usa uma API pública gratuita do QRServer para gerar a imagem na hora
    qr_url = f"https://api.qrserver.com/v1/create-qr-code/?size=300x300&data={urllib.parse.quote(link_cardapio)}"
    
    return f"""<html><head>{CSS}</head><body><div class='container-center'><div class='card-center'>{IMG_LOGO_PEQ}<h2 style='color:#d31a21;'>QR Code do Cardápio</h2><p style='color:#333;'>Imprima esta imagem e coloque nas mesas. O cardápio atualiza automaticamente conforme as vendas!</p>
    <div style='background:white; padding:20px; display:inline-block; border-radius:15px; border:2px dashed #ccc; margin:20px 0;'>
        <img src='{qr_url}' style='width:250px; height:250px;'>
    </div>
    <br><a href='{link_cardapio}' target='_blank' style='color:#062b5e; font-weight:bold; font-size:18px; text-decoration:underline;'>🔗 Acessar Link do Cardápio</a><br><br><br>
    <a href='/central' class='btn-acao' style='background:#333;'>Voltar ao Painel</a></div></div></body></html>"""
# ==========================================


@app.get("/caixa", response_class=HTMLResponse)
async def tela_caixa(request: Request):
    if request.session.get("role") not in ["admin", "gerente", "caixa"]: return RedirectResponse(url="/central")
    hoje = date.today().strftime("%Y-%m-%d")
    with engine.connect() as conn:
        pag_q = conn.execute(text(f"SELECT forma_pagamento, SUM(total_conta) as total FROM pulseiras WHERE CAST(data_fechamento AS DATE) = CAST('{hoje}' AS DATE) AND status = 'FECHADA' GROUP BY forma_pagamento")).fetchall()
        totais = {"DINHEIRO": 0.0, "PIX": 0.0, "C. CREDITO": 0.0, "C. DEBITO": 0.0}
        for p in pag_q: totais[p.forma_pagamento] = float(p.total or 0)
        mov_q = conn.execute(text(f"SELECT tipo, descricao, valor, TO_CHAR(data_registro, 'HH24:MI') as hora FROM caixa_movimentos WHERE CAST(data_registro AS DATE) = CAST('{hoje}' AS DATE) ORDER BY data_registro DESC")).fetchall()
        tot_sangria = sum([float(m.valor) for m in mov_q if m.tipo == 'SANGRIA'])
        linhas_mov = "".join([f"<tr><td style='color:black;'>{m.hora}</td><td style='color:black;'>{m.tipo} - {m.descricao}</td><td style='color:#d31a21; font-weight:bold;'>- R$ {float(m.valor):.2f}</td></tr>" for m in mov_q if m.tipo == 'SANGRIA'])
    return f"""<html><head>{CSS}</head><body><div class='container-center'><div class='card-center' style='max-width:700px;'>{IMG_LOGO_PEQ}<h2>💰 Gestão de Caixa (Hoje)</h2><div style='display:flex; justify-content:space-between; flex-wrap:wrap; gap:10px; margin-bottom:20px;'><div style='background:#f9f9f9; padding:15px; border-radius:8px; border-left:4px solid #28a745; flex:1; min-width:140px;'><b>💵 Dinheiro:</b><br><span style='font-size:20px; color:#28a745;'>R$ {totais['DINHEIRO']:.2f}</span></div><div style='background:#f9f9f9; padding:15px; border-radius:8px; border-left:4px solid #17a2b8; flex:1; min-width:140px;'><b>💠 PIX:</b><br><span style='font-size:20px; color:#17a2b8;'>R$ {totais['PIX']:.2f}</span></div><div style='background:#f9f9f9; padding:15px; border-radius:8px; border-left:4px solid #f39c12; flex:1; min-width:140px;'><b>💳 Cartões:</b><br><span style='font-size:20px; color:#f39c12;'>R$ {(totais['C. CREDITO'] + totais['C. DEBITO']):.2f}</span></div></div><div style='background:#f4f4f4; padding:20px; border-radius:10px; text-align:left; border:1px solid #ccc; margin-bottom:20px;'><h3 style='margin-top:0; color:#d31a21;'>🔻 Fazer Sangria (Retirada)</h3><form action='/sangria' method='post' style='display:flex; flex-wrap:wrap; gap:10px;'><input name='valor' type='number' step='0.01' placeholder='Valor R$' class='input-padrao' style='flex:1; min-width:100px;' required><input name='desc' type='text' placeholder='Motivo (Ex: Gelo)' class='input-padrao' style='flex:2; min-width:180px;' required><button class='btn-acao' style='background:#d31a21; margin:0; width:100px;'>TIRAR</button></form></div><h3 style='text-align:left; margin-bottom:5px;'>Histórico de Retiradas</h3><div style='max-height:150px; overflow-y:auto; border:1px solid #ddd; margin-bottom:20px;'><table><tr><th style='color:black'>Hora</th><th style='color:black'>Motivo</th><th style='color:black'>Valor</th></tr>{linhas_mov if linhas_mov else "<tr><td colspan='3' style='color:black; text-align:center;'>Nenhuma retirada.</td></tr>"}</table></div><a href='/caixa_cego' class='btn-acao' style='background:#062b5e; font-size:18px; padding:20px;'>🔒 ENCERRAR TURNO (BATER CAIXA)</a><br><a href='/central' style='color:gray'>Voltar ao Menu</a></div></div></body></html>"""

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
    return f"""<html><head>{CSS}</head><body><div class='container-center'><div class='card-center'>{IMG_LOGO_PEQ}<h2 style='color:#d31a21;'>Fechamento de Caixa Cego</h2><p style='color:black;'>Conte as notas da gaveta e digite abaixo o valor total exato do dinheiro físico.</p><form action='/resumo_whatsapp' method='post'><input class='input-padrao' name='dinheiro_gaveta' type='number' step='0.01' placeholder='R$ 0.00' required style='font-size:24px; text-align:center; padding:20px; font-weight:bold;'><button class='btn-acao' style='background:#28a745; font-size:18px; margin-top:20px;'>✔️ CONFIRMAR VALOR FÍSICO</button></form><br><a href='/caixa' style='color:gray'>Cancelar</a></div></div></body></html>"""

@app.post("/resumo_whatsapp", response_class=HTMLResponse)
async def resumo_whatsapp(request: Request):
    if request.session.get("role") not in ["admin", "gerente", "caixa"]: return RedirectResponse(url="/central")
    f = await request.form()
    gaveta = float(f.get("dinheiro_gaveta", "0"))
    hoje_str, hoje_br, usuario = date.today().strftime("%Y-%m-%d"), date.today().strftime("%d/%m/%Y"), request.session.get("user", "Desconhecido").upper()
    with engine.connect() as conn:
        pag_q = conn.execute(text(f"SELECT forma_pagamento, SUM(total_conta) as total FROM pulseiras WHERE CAST(data_fechamento AS DATE) = CAST('{hoje_str}' AS DATE) AND status = 'FECHADA' GROUP BY forma_pagamento")).fetchall()
        totais = {"DINHEIRO": 0.0, "PIX": 0.0, "C. CREDITO": 0.0, "C. DEBITO": 0.0}
        for p in pag_q: totais[p.forma_pagamento] = float(p.total or 0)
        mov_q = conn.execute(text(f"SELECT SUM(valor) as tot FROM caixa_movimentos WHERE CAST(data_registro AS DATE) = CAST('{hoje_str}' AS DATE) AND tipo = 'SANGRIA'")).fetchone()
        tot_sangria = float(mov_q.tot or 0)
        comissao_db = conn.execute(text(f"SELECT SUM(valor * 0.10) as tot FROM vendas_itens WHERE CAST(data_venda AS DATE) = CAST('{hoje_str}' AS DATE) AND status = 'FECHADA'")).fetchone()
        tot_comissao = float(comissao_db.tot or 0)
    esperado_dinheiro = totais["DINHEIRO"] - tot_sangria
    diferenca = gaveta - esperado_dinheiro
    faturamento_bruto = sum(totais.values())
    faturamento_liq = faturamento_bruto - tot_comissao
    status_caixa = "✅ Bateu certinho! R$ 0.00" if diferenca == 0 else f"⚠️ Sobrou na gaveta: R$ {diferenca:.2f}" if diferenca > 0 else f"❌ FURO DE CAIXA: R$ {diferenca:.2f}"
    mensagem = f"""📊 *FECHAMENTO DE CAIXA*\n*Data:* {hoje_br}\n*Operador:* {usuario}\n\n*Vendas por Pagamento:*\n💵 Dinheiro: R$ {totais['DINHEIRO']:.2f}\n💳 Cartão: R$ {(totais['C. CREDITO'] + totais['C. DEBITO']):.2f}\n💠 PIX: R$ {totais['PIX']:.2f}\n\n*Movimentações:*\n🔻 Sangrias: R$ {tot_sangria:.2f}\n\n*Auditoria da Gaveta:*\nInformado: R$ {gaveta:.2f}\nDeveria ter: R$ {esperado_dinheiro:.2f}\n*Status:* {status_caixa}\n\n*Resumo Geral:*\n💰 Bruto: R$ {faturamento_bruto:.2f}\n💸 Comissões: R$ {tot_comissao:.2f}\n✅ *Líquido: R$ {faturamento_liq:.2f}*"""
    zap_url = f"https://wa.me/5561995414168?text={urllib.parse.quote(mensagem)}"
    return f"""<html><head>{CSS}</head><body><div class='container-center'><div class='card-center' style='max-width:600px;'><h2>Auditoria Concluída</h2><div style='background:#f4f4f4; padding:20px; border-radius:8px; text-align:left; color:black; font-family:monospace; font-size:14px; margin-bottom:20px; white-space:pre-wrap;'>{mensagem.replace('*', '<b>').replace('<b>', '</b>', 1)}</div><a href='{zap_url}' target='_blank' class='btn-acao' style='background:#25D366; font-size:18px; padding:20px;'>📱 ENVIAR RESUMO PELO WHATSAPP</a><br><a href='/caixa' style='color:gray'>Voltar</a></div></div></body></html>"""

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
            linhas_pendentes += f"<tr><td style='color:black;'>{r.garcom}</td><td style='color:#062b5e;'>{r.data.strftime('%d/%m/%Y')}</td><td style='color:black;'>R$ {float(r.total_vendido):.2f}</td><td style='color:#d31a21; font-weight:bold;'>R$ {float(r.comissao):.2f}</td><td><form action='/pagar_comissao' method='post' style='margin:0;'><input type='hidden' name='data_venda' value='{r.data}'><input type='hidden' name='garcom' value='{r.garcom}'><button class='btn-acao' style='background:#28a745; padding:8px; font-size:12px;'>✔️ PAGO</button></form></td></tr>"
        where_clause_pagas = "status = 'FECHADA' AND comissao_status = 'PAGA'"
        if garcom_filtro: where_clause_pagas += " AND garcom = :g"
        res_pagas = conn.execute(text(f"SELECT CAST(data_venda AS DATE) as data, garcom, SUM(valor) as total_vendido, (SUM(valor) * 0.10) as comissao FROM vendas_itens WHERE {where_clause_pagas} GROUP BY CAST(data_venda AS DATE), garcom ORDER BY data DESC LIMIT 30"), params).fetchall()
        for r in res_pagas:
            linhas_pagas += f"<tr><td style='color:black;'>{r.garcom}</td><td style='color:#062b5e;'>{r.data.strftime('%d/%m/%Y')}</td><td style='color:black;'>R$ {float(r.total_vendido):.2f}</td><td style='color:#28a745; font-weight:bold;'>R$ {float(r.comissao):.2f}</td><td><span style='color:#28a745;'>PAGO</span></td></tr>"
    return f"""<html><head>{CSS}</head><body><div class='container-center'><div class='card-center' style='max-width:800px;'><h2>💸 Gestão de Comissões</h2><form method='GET' style='margin-bottom:20px; display:flex; gap:10px;'><select name='garcom_filtro' class='input-padrao' style='flex:1;'><option value=''>Todos os Funcionários</option>{opcoes_garcom}</select><button class='btn-acao' style='background:#062b5e; width:120px;'>FILTRAR</button></form><h3 style='color:#d31a21; text-align:left; border-bottom:2px solid #ccc;'>🔴 Pendentes</h3><div style='max-height:300px; overflow-y:auto; border:1px solid #ddd; margin-bottom:20px;'><table><tr><th style='color:black'>Func.</th><th style='color:black'>Data</th><th style='color:black'>Vendido</th><th style='color:black'>Comissão</th><th style='color:black'>Ação</th></tr>{linhas_pendentes if linhas_pendentes else "<tr><td colspan='5' style='color:black;text-align:center;'>Nenhuma pendência.</td></tr>"}</table></div><h3 style='color:#28a745; text-align:left; border-bottom:2px solid #ccc;'>🟢 Pagos</h3><div style='max-height:300px; overflow-y:auto; border:1px solid #ddd;'><table><tr><th style='color:black'>Func.</th><th style='color:black'>Data</th><th style='color:black'>Vendido</th><th style='color:black'>Comissão</th><th style='color:black'>Status</th></tr>{linhas_pagas if linhas_pagas else "<tr><td colspan='5' style='color:black;text-align:center;'>Nenhum histórico.</td></tr>"}</table></div><br><a href='/central' class='btn-acao' style='width: 200px; margin:auto'>Voltar</a></div></div></body></html>"""

@app.post("/pagar_comissao")
async def pagar_comissao(request: Request):
    if request.session.get("role") not in ["admin", "gerente"]: return RedirectResponse(url="/central")
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
            acoes = f"<form action='/excluir_usuario' method='post' style='margin:0;'><input type='hidden' name='id' value='{r.id}'><button class='btn-acao' style='background:#d31a21; padding:8px; width:auto;'>🗑️</button></form>" if r.username != "admin" else ""
            linhas += f"<tr><td style='color:black; font-weight:bold;'>{r.username.upper()}</td><td style='color:#062b5e;'>{r.role.upper()}</td><td>{acoes}</td></tr>"
    add_form = f"""<div style='background:#f4f4f4; padding:20px; border-radius:10px; margin-bottom:20px; text-align:left; border:1px solid #ccc;'><h3 style='margin-top:0; color:#9b59b6;'>➕ NOVO USUÁRIO</h3><form action='/novo_usuario' method='post' style='display:flex; flex-wrap:wrap; gap:10px;'><input name='u' placeholder='Login' class='input-padrao' style='flex:1;' required><input name='p' type='password' placeholder='Senha' class='input-padrao' style='flex:1;' required><select name='r' class='input-padrao' style='flex:1;'><option value='gerente'>GERENTE</option><option value='caixa'>CAIXA</option><option value='garcom'>GARÇOM</option><option value='portaria'>PORTARIA</option></select><button class='btn-acao' style='background:#9b59b6; width:100%;'>CRIAR ACESSO</button></form></div>"""
    return f"""<html><head>{CSS}</head><body><div class='container-center'><div class='card-center'><h2>Usuários</h2>{add_form}<div style='max-height:400px; overflow-y:auto; border:1px solid #ddd;'><table><tr><th style='color:black'>Login</th><th style='color:black'>Cargo</th><th style='color:black'>Ação</th></tr>{linhas}</table></div><br><a href='/central' style='color:gray'>Voltar</a></div></div></body></html>"""

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

@app.get("/estoque", response_class=HTMLResponse)
async def tela_estoque(request: Request):
    if request.session.get("role") not in ["admin", "gerente"]: return RedirectResponse(url="/central")
    linhas, curr_cat = "", ""
    with engine.connect() as conn:
        prods_db = conn.execute(text("SELECT p.id, p.nome, p.categoria, p.preco, p.estoque, MAX(h.data_entrada) as ultima_compra FROM produtos p LEFT JOIN historico_estoque h ON p.nome = h.produto_nome GROUP BY p.id, p.nome, p.categoria, p.preco, p.estoque ORDER BY p.categoria, p.nome")).fetchall()
        for r in prods_db:
            if r.categoria != curr_cat:
                linhas += f"<tr><td colspan='5' style='background:#082d5e; color:white; font-weight:bold; text-align:center;'>{r.categoria or 'OUTROS'}</td></tr>"
                curr_cat = r.categoria
            acoes = f"""<div style='display:flex; gap:5px;'><form action='/att_estoque' method='post' style='margin:0; display:flex;'><input type='hidden' name='i' value='{r.nome}'><input type='number' name='q' class='input-padrao' style='width:50px; padding:5px;' required><button class='btn-acao' style='background:#28a745; padding:8px;'>➕</button></form><form action='/excluir_produto' method='post' style='margin:0;'><input type='hidden' name='nome' value='{r.nome}'><button class='btn-acao' style='background:#d31a21; padding:8px;'>🗑️</button></form></div>"""
            linhas += f"<tr><td style='color:#d31a21;'>{r.id:03d}</td><td style='color:black;'>{r.nome} <br><small>R$ {float(r.preco or 0):.2f}</small></td><td style='color:#062b5e; font-size:12px;'>{(r.ultima_compra.strftime('%d/%m/%Y') if r.ultima_compra else 'Sem Registro')}</td><td style='color:black; font-weight:bold; font-size:18px;'>{int(r.estoque or 0)}</td><td>{acoes}</td></tr>"
    add_form = f"""<div style='background:#f4f4f4; padding:20px; border-radius:10px; margin-bottom:20px; text-align:left; border:1px solid #ccc;'><h3 style='margin-top:0; color:#d31a21;'>➕ NOVO PRODUTO</h3><form action='/novo_produto' method='post' style='display:flex; flex-wrap:wrap; gap:10px;'><input name='nome' placeholder='Produto' class='input-padrao' style='flex:1;' required><select name='cat' class='input-padrao' style='flex:1;' required><option value='CHOPP'>CHOPP</option><option value='CERVEJAS'>CERVEJAS</option><option value='PETISCOS'>PETISCOS</option><option value='BEBIDAS'>BEBIDAS</option><option value='OUTROS'>OUTROS</option></select><input name='preco' placeholder='Preço' class='input-padrao' style='width:80px;' required><input name='qtd' type='number' placeholder='Qtd' class='input-padrao' style='width:80px;' required><button class='btn-acao' style='background:#062b5e; width:100%;'>SALVAR</button></form></div>"""
    return f"""<html><head>{CSS}</head><body><div class='container-center'><div class='card-center'><h2>Estoque</h2>{add_form}<div style='max-height:400px; overflow-y:auto; border:1px solid #ddd;'><table><tr><th style='color:black'>Cód</th><th style='color:black'>Item</th><th style='color:black'>Compra</th><th style='color:black'>Qtd</th><th style='color:black'>Ação</th></tr>{linhas}</table></div><br><a href='/central' style='color:gray'>Voltar</a></div></div></body></html>"""

@app.post("/novo_produto")
async def novo_produto(request: Request):
    f = await request.form()
    n, c, p, q = f.get("nome", "").strip(), f.get("cat", "OUTROS"), f.get("preco", "0").replace(",", "."), f.get("qtd", "0")
    try:
        with engine.begin() as conn: 
            conn.execute(text("INSERT INTO produtos (nome, categoria, preco, estoque) VALUES (:n, :c, :p, :q) ON CONFLICT (nome) DO NOTHING"), {"n": n, "c": c, "p": float(p), "q": int(q)})
            conn.execute(text("INSERT INTO historico_estoque (produto_nome, qtd_adicionada) VALUES (:n, :q)"), {"n": n, "q": int(q)})
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

@app.get("/vendas", response_class=HTMLResponse)
async def vendas(request: Request, cat: str = "CHOPP", p: str = ""):
    if request.session.get("role") not in ["admin", "gerente", "garcom", "caixa"]: return RedirectResponse(url="/central")
    prods, itens_html = "", ""
    with engine.connect() as conn:
        for n, v, e in conn.execute(text("SELECT nome, preco, estoque FROM produtos WHERE categoria = :c ORDER BY nome"), {"c": cat}).fetchall():
            cor = 'bg-green' if e > 0 else 'bg-red'
            prods += f"<div class='prod-card {cor}' onclick='add(\"{n}\", {float(v or 0)}, {int(e or 0)})'><b>{n}</b><span>R$ {float(v or 0):.2f}</span><div class='badge-estoque'>Estoque: {int(e or 0)}</div></div>"
        if p:
            for r in conn.execute(text("SELECT item_nome, COUNT(*) as qtd, SUM(valor) as tot FROM vendas_itens WHERE pulseira_num = :p AND status = 'ABERTA' GROUP BY item_nome"), {"p": p}).fetchall():
                itens_html += f"<div class='item-linha'><span>{r.qtd}x {r.item_nome}</span><span>R$ {float(r.tot or 0):.2f}</span></div>"
    comanda_display = f"""<div class='comanda-header'><div style='font-size:13px;'>PULSEIRA:</div><input type='number' id='input-pulseira' class='input-padrao' style='text-align:center; font-weight:bold; font-size:20px;' value='{p}'><button class='btn-acao' style='background:white; color:#d31a21;' onclick='window.location.href="/vendas?cat={cat}&p="+document.getElementById("input-pulseira").value'>ACESSAR</button></div><div class='comanda-body'><div class='secao-titulo'>Consumo</div>{itens_html}<hr><div class='secao-titulo'>Novo Pedido</div><div id='novo-pedido'></div></div><div class='comanda-footer'><div style='display:flex; justify-content:space-between; font-weight:bold;'><span>Subtotal:</span><span id='tot-pedido'>R$ 0.00</span></div><br><button class='btn-acao' style='background:#28a745;' onclick='enviarPedido()'>LANÇAR PEDIDO</button><a href='/central' class='btn-acao' style='background:#333'>Voltar</a></div>"""
    return f"""<html><head>{CSS}<script>const p_num = '{p}'; let cart = JSON.parse(sessionStorage.getItem('cart_'+p_num)) || []; function add(n,v,e) {{ if(!p_num) return alert('Acesse uma pulseira!'); if (e <= 0 || cart.filter(x => x.n === n).length >= e) return alert('❌ Sem estoque!'); cart.push({{n,v}}); sessionStorage.setItem('cart_'+p_num, JSON.stringify(cart)); render(); }} function render() {{ let html = ''; let t = 0; cart.forEach((i,idx) => {{ html += `<div class='item-linha' style='color:#d31a21; font-weight:bold;'><span>${{i.n}}</span><span>R$ ${{i.v.toFixed(2)}} <b onclick='rem(${{idx}})' style='cursor:pointer; color:black;'>X</b></span></div>`; t += i.v; }}); document.getElementById('novo-pedido').innerHTML = html; document.getElementById('tot-pedido').innerText = 'R$ '+t.toFixed(2); }} function rem(idx) {{ cart.splice(idx,1); sessionStorage.setItem('cart_'+p_num, JSON.stringify(cart)); render(); }} function enviarPedido() {{ if(!p_num || cart.length === 0) return; let f = document.createElement('form'); f.method = 'POST'; f.action = '/lancar_pedido'; let i1 = document.createElement('input'); i1.name = 'p'; i1.value = p_num; f.appendChild(i1); let i2 = document.createElement('input'); i2.name = 'itens'; i2.value = JSON.stringify(cart); f.appendChild(i2); document.body.appendChild(f); sessionStorage.removeItem('cart_'+p_num); f.submit(); }} window.onload = render;</script></head><body><div class='layout-vendas'><div class='menu-lateral'><a href='/vendas?cat=CHOPP&p={p}' class='btn-menu'>🍺 CHOPP</a><a href='/vendas?cat=CERVEJAS&p={p}' class='btn-menu'>🍾 CERVEJAS</a><a href='/vendas?cat=PETISCOS&p={p}' class='btn-menu'>🍟 PETISCOS</a><a href='/vendas?cat=BEBIDAS&p={p}' class='btn-menu'>🍹 BEBIDAS</a><a href='/vendas?cat=OUTROS&p={p}' class='btn-menu'>📦 OUTROS</a></div><div class='main-area'>{IMG_LOGO}<h2>{cat}</h2><div class='grid-produtos'>{prods}</div></div><div class='comanda-lateral'>{comanda_display}</div></div></body></html>"""

@app.post("/lancar_pedido")
async def lancar_pedido(request: Request):
    f = await request.form()
    p, itens, u = f.get("p"), json.loads(f.get("itens", "[]")), request.session.get("user")
    tot = sum(i['v'] for i in itens)
    try:
        with engine.begin() as conn:
            conn.execute(text("UPDATE pulseiras SET total_conta = total_conta + :t WHERE numero_pulseira = :p AND status = 'ABERTA'"), {"t": tot, "p": p})
            for i in itens:
                conn.execute(text("INSERT INTO vendas_itens (pulseira_num, item_nome, valor, garcom) VALUES (:p, :n, :v, :g)"), {"p": p, "n": i['n'], "v": i['v'], "g": u})
                conn.execute(text("UPDATE produtos SET estoque = GREATEST(estoque - 1, 0) WHERE nome = :n"), {"n": i['n']})
            txt = f"--------------------------------\n      TICKET PREPARO\nPULSEIRA: {p}\nATENDENTE: {u}\n--------------------------------\n"
            for i in itens: txt += f"1x {i['n']} - R$ {i['v']:.2f}\n"
            txt += "--------------------------------\n"
            conn.execute(text("INSERT INTO fila_impressao (conteudo) VALUES (:txt)"), {"txt": txt})
    except: pass
    return RedirectResponse(url=f"/vendas?p={p}", status_code=303)

@app.get("/fechar_conta", response_class=HTMLResponse)
async def fechar_conta(request: Request, q: str = ""):
    res = ""
    if q:
        with engine.connect() as conn:
            query = conn.execute(text("SELECT p.numero_pulseira, p.total_conta, c.nome_completo, c.cpf FROM pulseiras p JOIN clientes c ON p.cliente_cpf = c.cpf WHERE (p.numero_pulseira = :q OR c.cpf = :q) AND p.status = 'ABERTA'"), {"q": q.strip()}).fetchone()
            if query:
                itens_q = conn.execute(text("SELECT item_nome, COUNT(*) as qtd, SUM(valor) as tot FROM vendas_itens WHERE pulseira_num = :p AND status = 'ABERTA' GROUP BY item_nome"), {"p": query.numero_pulseira}).fetchall()
                lista = "".join([f"<div class='item-linha'><span>{i.qtd}x {i.item_nome}</span><span>R$ {float(i.tot or 0):.2f}</span></div>" for i in itens_q])
                subtotal = float(query.total_conta or 0)
                taxa = subtotal * 0.10
                total_final = subtotal + taxa
                res = f"""<div style='background:#f4f4f4; padding:20px; border-radius:10px; color:#333; margin-top:20px; text-align:left;'>
                    <h3 style='text-align:center; margin-bottom:5px;'>{query.nome_completo}</h3><p style='text-align:center;'>Pulseira: <b>{query.numero_pulseira}</b></p>
                    <div style='background:white; padding:15px; border-radius:8px; max-height:220px; overflow-y:auto; border:1px solid #ddd;'>{lista}</div>
                    <div style='padding-top:15px; font-size:16px;'>
                        <div class='item-linha'><span>Consumo:</span><span>R$ {subtotal:.2f}</span></div>
                        <div class='item-linha'><span>Serviço (10%):</span><span>R$ {taxa:.2f}</span></div>
                        <div class='item-linha' style='color:#062b5e;'><span style='padding-top:5px;'>Desconto (R$):</span><div style='display:flex; gap:5px;'><input type='number' id='input_desconto' value='0' min='0' step='0.01' style='width:70px; text-align:right; border:1px solid #ccc; border-radius:3px; padding:5px;' placeholder='0.00'><button type='button' onclick='calcDiv()' style='background:#062b5e; color:white; border:none; border-radius:3px; padding:5px 10px; cursor:pointer;'>APLICAR</button></div></div>
                        <div class='item-linha' style='font-weight:bold; font-size:20px; color:#d31a21; margin-top:10px;'><span>TOTAL A PAGAR:</span><span id='tot_final'>R$ {total_final:.2f}</span></div>
                        <div class='item-linha' style='margin-top:10px;'><span>Dividir por:</span><input type='number' id='divisores' value='1' min='1' style='width:60px; text-align:center; border:1px solid #ccc; border-radius:3px; padding:5px;' oninput='calcDiv()'></div>
                        <div class='item-linha' style='font-weight:bold; font-size:18px;'><span>Por Pessoa:</span><span id='val_pessoa'>R$ {total_final:.2f}</span></div>
                        <div class='item-linha' style='margin-top:15px; align-items:center;'><span style='font-weight:bold;'>Pagamento:</span><select id='select_pag' class='input-padrao' style='width:auto; padding:5px; margin:0;' onchange='document.getElementById("input_pag_form").value = this.value'><option value='DINHEIRO'>DINHEIRO</option><option value='PIX'>PIX</option><option value='C. CREDITO'>C. CREDITO</option><option value='C. DEBITO'>C. DEBITO</option></select></div>
                    </div>
                    <form action='/confirmar_fechamento' method='post'>
                        <input type='hidden' name='p' value='{query.numero_pulseira}'>
                        <input type='hidden' name='divisao' id='input_div' value='1'>
                        <input type='hidden' name='desconto' id='input_desc_form' value='0'>
                        <input type='hidden' name='pagamento' id='input_pag_form' value='DINHEIRO'>
                        <div style='background:#e9ecef; padding:15px; border-radius:8px; margin-top:15px; border:1px solid #ccc;'>
                            <div style='display:flex; align-items:center; justify-content:space-between; margin-bottom:10px;'>
                                <span style='font-weight:bold; color:#28a745; font-size:16px;'>🧾 Emitir Nota Fiscal (NFC-e)?</span>
                                <label class='switch'><input type='checkbox' name='nfe' onchange='document.getElementById("box-cpf").style.display = this.checked ? "block" : "none"'><span class='slider'></span></label>
                            </div>
                            <div id='box-cpf' style='display:none;'><span style='font-size:12px; color:#666;'>CPF do cliente:</span><input class='input-padrao' name='cpf_nota' value='{query.cpf}' placeholder='Digite o CPF'></div>
                        </div>
                        <button class='btn-acao' style='background:#28a745; font-size:18px; margin-top:15px;'>🖨️ CONFIRMAR E IMPRIMIR RECIBO</button>
                    </form>
                    <script>function calcDiv() {{ let subtotal = {subtotal}; let taxa = {taxa}; let desc = parseFloat(document.getElementById('input_desconto').value.replace(',', '.')) || 0; let div = parseInt(document.getElementById('divisores').value) || 1; let totFinal = Math.max(subtotal + taxa - desc, 0); document.getElementById('tot_final').innerText = 'R$ ' + totFinal.toFixed(2); document.getElementById('val_pessoa').innerText = 'R$ ' + (totFinal / div).toFixed(2); document.getElementById('input_div').value = div; document.getElementById('input_desc_form').value = desc; }}</script>
                </div>"""
            else: res = "<p style='color:red;'>Nenhuma comanda aberta localizada.</p>"
    return f"<html><head>{CSS}</head><body><div class='container-center'><div class='card-center'>{IMG_LOGO_PEQ}<h2>Fechar Conta</h2><form method='get'><input class='input-padrao' name='q' placeholder='CPF ou Nº Pulseira' value='{q}' required><button class='btn-acao'>CONSULTAR CONTA</button></form>{res}<br><a href='/central' style='color:gray'>Voltar</a></div></div></body></html>"

@app.post("/confirmar_fechamento")
async def confirmar_fechamento(request: Request):
    f = await request.form()
    p, pag, nfe, cpf, desc_str = f.get("p"), f.get("pagamento"), f.get("nfe"), f.get("cpf_nota"), f.get("desconto", "0")
    try: desc = float(desc_str)
    except: desc = 0.0
    try:
        with engine.begin() as conn: 
            c = conn.execute(text("SELECT c.nome_completo, p.total_conta FROM pulseiras p JOIN clientes c ON p.cliente_cpf = c.cpf WHERE p.numero_pulseira = :p AND p.status = 'ABERTA'"), {"p": p}).fetchone()
            if c:
                conn.execute(text("UPDATE pulseiras SET status = 'FECHADA', forma_pagamento = :pag, data_fechamento = CURRENT_TIMESTAMP, nfe_solicitada = :nfe, cpf_nota = :cpf WHERE numero_pulseira = :p AND status = 'ABERTA'"), {"p": p, "pag": pag, "nfe": bool(nfe), "cpf": cpf})
                conn.execute(text("UPDATE vendas_itens SET status = 'FECHADA' WHERE pulseira_num = :p AND status = 'ABERTA'"), {"p": p})
                tot = (float(c.total_conta) * 1.1) - desc
                txt = f"--------------------------------\n      QUIOSQUE BRAHMA\nFECHAMENTO DE CONTA\nPULSEIRA: {p}\nTOTAL: R$ {tot:.2f}\nPAGTO: {pag}\n--------------------------------\n"
                if nfe: txt += f"NFC-e SOLICITADA\nCPF: {cpf}\n--------------------------------\n"
                txt += "OBRIGADO E VOLTE SEMPRE!\n"
                conn.execute(text("INSERT INTO fila_impressao (conteudo) VALUES (:t)"), {"t": txt})
    except: pass
    return RedirectResponse(url="/central", status_code=303)

@app.get("/buscar", response_class=HTMLResponse)
async def tela_busca(request: Request, q: str = ""):
    res = ""
    if q:
        with engine.connect() as conn:
            c = conn.execute(text("SELECT nome_completo, cpf, data_nascimento FROM clientes WHERE nome_completo ILIKE :q OR cpf LIKE :q"), {"q": f"%{q}%"}).fetchall()
            for r in c: res += f"<tr><td style='color:black'>{r.nome_completo}</td><td><form action='/abrir' method='post' style='display:flex;gap:5px'><input type='hidden' name='cpf' value='{r.cpf}'><input class='input-padrao' name='p' placeholder='Nº' required style='width:60px;margin:0'><button class='btn-acao' style='background:#d31a21;padding:8px;margin:0'>ABRIR</button></form></td></tr>"
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
async def tela_cadastro(): return f"<html><head>{CSS}</head><body><div class='container-center'><div class='card-center'>{IMG_LOGO_PEQ}<h2>Novo Cliente</h2><form action='/salvar' method='post'><input class='input-padrao' name='nome' placeholder='Nome Completo' required><input class='input-padrao' name='cpf' placeholder='CPF' required><input class='input-padrao' name='nasc' type='date' required><input class='input-padrao' name='contato' placeholder='WhatsApp' required><input class='input-padrao' name='email' type='email' placeholder='E-mail (Opcional)'><input class='input-padrao' name='pulseira' placeholder='Nº Pulseira' required><button class='btn-acao' style='background:#d31a21'>SALVAR E ABRIR</button></form><br><a href='/central'>Voltar</a></div></div></body></html>"

@app.post("/salvar")
async def salvar(request: Request):
    f = await request.form()
    n, c, d, co, e, p = f.get("nome"), f.get("cpf"), f.get("nasc"), f.get("contato"), f.get("email"), f.get("pulseira")
    try:
        with engine.begin() as conn:
            conn.execute(text("INSERT INTO clientes (nome_completo, cpf, data_nascimento, contato, email) VALUES (:n, :c, :d, :co, :e) ON CONFLICT (cpf) DO NOTHING"), {"n":n, "c":c, "d":d, "co":co, "e":e})
            if conn.execute(text("SELECT numero_pulseira FROM pulseiras WHERE cliente_cpf = :c AND status = 'ABERTA'"), {"c": c}).fetchone(): return HTMLResponse("<script>alert('Cliente já possui comanda aberta!'); window.history.back();</script>")
            if conn.execute(text("SELECT cliente_cpf FROM pulseiras WHERE numero_pulseira = :p AND status = 'ABERTA'"), {"p": p}).fetchone(): return HTMLResponse("<script>alert('Pulseira em uso por outra pessoa!'); window.history.back();</script>")
            conn.execute(text("INSERT INTO pulseiras (numero_pulseira, cliente_cpf, total_conta, status) VALUES (:p, :c, 7.00, 'ABERTA')"), {"p":p, "c":c})
    except: pass
    return RedirectResponse(url=f"/vendas?p={p}", status_code=303)

@app.get("/dashboard", response_class=HTMLResponse)
async def dashboard(request: Request, inicio: str = "", fim: str = ""):
    if request.session.get("role") not in ["admin", "gerente"]: return RedirectResponse(url="/central")
    where_p = "status = 'FECHADA'"
    params = {}
    if inicio:
        where_p += " AND CAST(data_fechamento AS DATE) >= CAST(:inicio AS DATE)"
        params["inicio"] = inicio
    if fim:
        where_p += " AND CAST(data_fechamento AS DATE) <= CAST(:fim AS DATE)"
        params["fim"] = fim
    with engine.connect() as conn:
        kpi = conn.execute(text(f"SELECT SUM(total_conta) as total, COUNT(*) as qtd FROM pulseiras WHERE {where_p}"), params).fetchone()
        faturamento_bruto = float(kpi.total or 0)
        pagamentos = conn.execute(text(f"SELECT forma_pagamento, COUNT(*) as qtd FROM pulseiras WHERE {where_p} GROUP BY forma_pagamento"), params).fetchall()
        labels_pag, data_pag = [r.forma_pagamento or "N/D" for r in pagamentos], [r.qtd for r in pagamentos]
    return f"""<html><head>{CSS}<script src="https://cdn.jsdelivr.net/npm/chart.js"></script></head><body><div class='main-area' style='padding: 30px;'><h1 style='color:white;'>📊 Dashboard</h1><form method='GET' style='margin-bottom:20px; display:flex; gap:10px;'><input type='date' name='inicio' value='{inicio}' class='input-padrao'><input type='date' name='fim' value='{fim}' class='input-padrao'><button class='btn-acao' style='width:100px;'>FILTRAR</button></form><div style='background:white; padding:20px; border-radius:10px; color:#333; margin-bottom:20px;'><h3>Faturamento Bruto</h3><p style='font-size:24px; font-weight:bold; color:#0a3a7a;'>R$ {faturamento_bruto:.2f}</p></div><div style='background:white; padding:20px; border-radius:10px; width:100%; max-width:500px;'><h3 style='color:#333'>Meios de Pagamento</h3><canvas id="chartPag"></canvas></div><br><a href='/central' class='btn-acao' style='width: 200px;'>Voltar</a></div><script>new Chart(document.getElementById('chartPag'), {{ type: 'doughnut', data: {{ labels: {json.dumps(labels_pag)}, datasets: [{{ data: {json.dumps(data_pag)}, backgroundColor: ['#0a3a7a', '#d31a21', '#ffc107', '#28a745'] }}] }} }});</script></body></html>"""

@app.get("/logout")
async def logout(request: Request): request.session.clear(); return RedirectResponse("/")
@app.get("/api/pendentes")
async def api_pendentes():
    with engine.connect() as conn:
        r = conn.execute(text("SELECT id, conteudo FROM fila_impressao WHERE status = 'PENDENTE' LIMIT 1")).fetchone()
        return {"jobs": [{"id": r.id, "conteudo": r.conteudo}]} if r else {"jobs": []}
@app.post("/api/impresso/{j_id}")
async def api_impresso(j_id: int):
    with engine.begin() as conn: conn.execute(text("UPDATE fila_impressao SET status='IMPRESSO' WHERE id=:i"), {"i": j_id})
    return {"ok": True}
@app.get("/download_conector")
async def download_conector(): return FileResponse(path="conector.exe", filename="conector_brahma.exe", media_type="application/octet-stream")
