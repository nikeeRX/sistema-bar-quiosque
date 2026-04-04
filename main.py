from fastapi import FastAPI, Form, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlalchemy import create_engine, text
from starlette.middleware.sessions import SessionMiddleware
from datetime import date

app = FastAPI()
app.add_middleware(SessionMiddleware, secret_key="brahma_riacho_mall_2024")

DATABASE_URL = "postgresql://postgres:GNlZnHiuKAcFnpgXhwILfigqKCNkaHqx@interchange.proxy.rlwy.net:44559/railway"
engine = create_engine(DATABASE_URL, pool_pre_ping=True)

with engine.begin() as conn:
    conn.execute(text("""
        CREATE TABLE IF NOT EXISTS clientes (
            id SERIAL PRIMARY KEY, nome_completo TEXT NOT NULL, cpf TEXT UNIQUE NOT NULL,
            data_nascimento DATE, contato TEXT, email TEXT
        );
        CREATE TABLE IF NOT EXISTS pulseiras (
            id SERIAL PRIMARY KEY, numero_pulseira TEXT NOT NULL, cliente_cpf TEXT REFERENCES clientes(cpf),
            total_conta DECIMAL(10,2) DEFAULT 7.00, status TEXT DEFAULT 'ABERTA'
        );
        CREATE TABLE IF NOT EXISTS vendas_itens (
            id SERIAL PRIMARY KEY, pulseira_num TEXT, item_nome TEXT, valor DECIMAL(10,2),
            data_venda DATE DEFAULT CURRENT_DATE, hora_venda TIME DEFAULT CURRENT_TIME
        );
        ALTER TABLE pulseiras ADD COLUMN IF NOT EXISTS status TEXT DEFAULT 'ABERTA';
    """))

CSS = """
<style>
    * { box-sizing: border-box; font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; }
    body { margin: 0; background: #0a3a7a; color: white; height: 100vh; display: flex; flex-direction: column; overflow-x: hidden; }
    .top-logo { position: absolute; top: 10px; left: 50%; transform: translateX(-50%); width: 140px; z-index: 100; filter: drop-shadow(0px 4px 6px rgba(0,0,0,0.5)); }
    .layout-vendas { display: flex; flex: 1; padding-top: 70px; }
    .menu-lateral { width: 220px; padding: 20px; display: flex; flex-direction: column; gap: 10px; border-right: 1px solid rgba(255,255,255,0.2); }
    .btn-menu { background: #062b5e; color: white; border: 2px solid #0a3a7a; padding: 15px; border-radius: 8px; text-align: left; font-weight: bold; font-size: 16px; cursor: pointer; text-decoration: none; transition: 0.3s; box-shadow: 0 4px 6px rgba(0,0,0,0.3); display: flex; align-items: center; justify-content: space-between; }
    .btn-menu:hover, .btn-menu.ativo { background: #0d4b9c; border-color: white; }
    .btn-menu span { font-size: 10px; color: #aaa; }
    .main-area { flex: 1; padding: 20px; }
    .main-area h2 { margin-top: 0; font-size: 28px; text-transform: uppercase; text-shadow: 1px 1px 2px black; }
    .grid-produtos { display: grid; grid-template-columns: repeat(auto-fill, minmax(180px, 1fr)); gap: 15px; }
    .prod-card { background: linear-gradient(180deg, #d31a21 0%, #a11015 100%); border: 2px solid #73070b; border-radius: 10px; padding: 15px 10px; text-align: center; cursor: pointer; transition: 0.2s; box-shadow: 0 4px 6px rgba(0,0,0,0.4); display: flex; flex-direction: column; justify-content: space-between; min-height: 120px; }
    .prod-card:hover { transform: scale(1.05); border-color: white; }
    .prod-card b { font-size: 14px; margin-bottom: 8px; text-shadow: 1px 1px 2px rgba(0,0,0,0.5); }
    .prod-card span { font-size: 18px; font-weight: bold; background: rgba(0,0,0,0.2); padding: 5px; border-radius: 5px; }
    .comanda-lateral { width: 320px; background: white; color: black; margin: 20px; border-radius: 10px; padding: 15px; display: flex; flex-direction: column; box-shadow: 0 8px 15px rgba(0,0,0,0.5); }
    .comanda-header { display: flex; justify-content: space-between; background: #0a3a7a; color: white; padding: 10px; border-radius: 5px; font-weight: bold; margin-bottom: 10px; }
    .comanda-items { flex: 1; overflow-y: auto; margin-bottom: 10px; border-bottom: 2px solid #eee; padding-bottom: 10px; }
    .item-linha { display: flex; justify-content: space-between; font-size: 13px; margin-bottom: 8px; border-bottom: 1px dashed #ccc; padding-bottom: 4px; }
    .comanda-total { display: flex; justify-content: space-between; font-size: 20px; font-weight: bold; margin-bottom: 15px; }
    .btn-acao { display: block; width: 100%; padding: 12px; margin-bottom: 8px; border: none; border-radius: 5px; font-weight: bold; color: white; cursor: pointer; text-align: center; text-decoration: none; font-size: 14px; background: #062b5e; box-shadow: 0 2px 4px rgba(0,0,0,0.3); }
    .btn-acao:hover { background: #0d4b9c; }
    .container-center { display: flex; align-items: center; justify-content: center; height: 100vh; padding: 20px; }
    .card-center { background: white; color: #333; padding: 30px; border-radius: 15px; width: 100%; max-width: 600px; text-align: center; box-shadow: 0 8px 20px rgba(0,0,0,0.4); }
    .input-padrao { width: 100%; padding: 12px; margin: 8px 0; border: 1px solid #ccc; border-radius: 5px; font-size: 16px; }
    .btn-vermelho { background: var(--vermelho); color: white; }
    table { width: 100%; border-collapse: collapse; margin-top: 15px; }
    th, td { padding: 10px; border-bottom: 1px solid #eee; text-align: left; }
</style>
"""

MENU = {
    "CHOPP": [("Caneca 350ml", 11.9), ("Descartável 500ml", 13.9), ("Tulipa 700ml", 17.9), ("Torre 2.5L", 84.9), ("Torre 3.5L", 99.9)],
    "CERVEJAS": [("Original 600ml", 12.9), ("Amstel 600ml", 12.0), ("Brahma Duplo Malte", 12.0), ("Heineken 600ml", 16.9), ("Spaten LN", 8.9), ("Corona LN", 10.0), ("Heineken LN", 10.0), ("Stella LN", 8.9), ("Heineken Zero", 10.0)],
    "PETISCOS": [("Fritas", 21.9), ("Fritas c/ Queijo", 25.9), ("Fritas Cheddar/Bacon", 27.9), ("Kibe 10un", 34.9), ("Kibe c/ Queijo", 37.9), ("Frango Passarinho", 28.9), ("Carne Sol c/ Fritas", 54.9), ("Calabresa Acebolada", 22.9), ("Tábua Frios", 34.9)],
    "BEBIDAS": [("Caipirinha", 14.9), ("Caipiroska Absolut", 16.9), ("Gin Tônica", 24.9), ("Gin Tropical", 26.9), ("Cozumel 600ml", 14.9), ("Refri Lata", 4.9), ("Soda Italiana", 13.9), ("Suco Lata", 5.9), ("Red Bull", 13.0), ("Água", 3.9)]
}

@app.get("/", response_class=HTMLResponse)
async def login_page():
    return f"<html><head>{CSS}</head><body><div class='container-center'><div class='card-center'><img src='https://logodownload.org/wp-content/uploads/2014/07/brahma-logo-2.png' width='120'><h2>Acesso ao PDV</h2><form action='/login' method='post'><input class='input-padrao' name='user' placeholder='Usuário' required><input class='input-padrao' name='pw' type='password' placeholder='Senha' required><button class='btn-acao' style='padding:15px; font-size:18px;'>ENTRAR</button></form></div></div></body></html>"

@app.post("/login")
async def login(request: Request, user: str = Form(...), pw: str = Form(...)):
    if (user == "admin" and pw == "1234") or (user == "garcom" and pw == "chopp"):
        request.session["user"] = user
        return RedirectResponse(url="/central", status_code=303)
    return RedirectResponse(url="/", status_code=303)

@app.get("/central", response_class=HTMLResponse)
async def central(request: Request):
    if "user" not in request.session: return RedirectResponse(url="/")
    return f"<html><head>{CSS}</head><body><div class='container-center'><div class='card-center'><h3>Bem-vindo</h3><a href='/cadastro' class='btn-acao' style='background:#d31a21'>➕ NOVO CADASTRO</a><a href='/buscar' class='btn-acao'>🔍 BUSCAR / ABRIR COMANDA</a><a href='/vendas' class='btn-acao' style='background:#0d4b9c'>🛒 MÓDULO DE VENDAS</a><a href='/fechar_conta' class='btn-acao' style='background:#333'>🔒 FECHAR CONTA</a><br><a href='/logout' style='color:gray'>Sair</a></div></div></body></html>"

@app.get("/vendas", response_class=HTMLResponse)
async def vendas(cat: str = "CHOPP", p: str = ""):
    prods = "".join([f"<div class='prod-card' onclick='lancar(\"{n}\", {v})'><b>{n}</b><span>R$ {v:.2f}</span></div>" for n, v in MENU.get(cat, [])])
    
    itens_html = ""
    total = 0.0
    if p:
        with engine.connect() as conn:
            query_itens = conn.execute(text("SELECT item_nome, COUNT(*) as qtd, SUM(valor) as tot FROM vendas_itens WHERE pulseira_num = :p GROUP BY item_nome"), {"p": p}).fetchall()
            for r in query_itens:
                itens_html += f"<div class='item-linha'><span>{r.qtd}x {r.item_nome}</span><span>R$ {r.tot:.2f}</span></div>"
            query_tot = conn.execute(text("SELECT total_conta FROM pulseiras WHERE numero_pulseira = :p AND status = 'ABERTA'"), {"p": p}).fetchone()
            total = query_tot.total_conta if query_tot else 0.0
            if total > 0 and not query_itens: itens_html = "<div class='item-linha'><span>1x Couvert</span><span>R$ 7.00</span></div>"

    comanda_display = f"""
        <div class='comanda-header'><span>Comanda Atual</span><span>F5</span></div>
        <div style='text-align:center; margin-bottom:10px;'><b>Pulseira: {p if p else 'Nenhuma'}</b></div>
        <div class='comanda-items'>
            <div style='display:flex; justify-content:space-between; font-weight:bold; border-bottom:2px solid #333; margin-bottom:5px;'><span>Item</span><span>Preço</span></div>
            {itens_html if p else "<div style='text-align:center; padding:20px; color:#999'>Informe a pulseira</div>"}
        </div>
        <div class='comanda-total'><span>Total</span><span>R$ {total:.2f}</span></div>
        <button class='btn-acao' onclick='setPulseira()'>Definir Pulseira (F4)</button>
        <a href='/fechar_conta?q={p}' class='btn-acao' style='background:#d31a21'>Finalizar Comanda (F10)</a>
        <a href='/central' class='btn-acao'>Menu Principal (F1)</a>
    """

    return f"""<html><head>{CSS}
    <script>
        function lancar(n, v){{
            const p = new URLSearchParams(window.location.search).get("p");
            if(!p) {{ alert("Defina a pulseira primeiro!"); return; }}
            window.location.href=`/lancar?p=${{p}}&v=${{v}}&i=${{n}}&c={cat}`;
        }}
        function setPulseira() {{
            let num = prompt("Digite o número da Pulseira ativa:");
            if(num) window.location.href=`/vendas?cat={cat}&p=${{num}}`;
        }}
    </script>
    </head><body>
    <img src='https://logodownload.org/wp-content/uploads/2014/07/brahma-logo-2.png' class='top-logo'>
    <div class='layout-vendas'>
        <div class='menu-lateral'>
            <a href='/vendas?cat=CHOPP&p={p}' class='btn-menu {"ativo" if cat=="CHOPP" else ""}'>🍺 CHOPP <span>F1</span></a>
            <a href='/vendas?cat=CERVEJAS&p={p}' class='btn-menu {"ativo" if cat=="CERVEJAS" else ""}'>🍾 CERVEJAS <span>F2</span></a>
            <a href='/vendas?cat=PETISCOS&p={p}' class='btn-menu {"ativo" if cat=="PETISCOS" else ""}'>🍟 PETISCOS <span>F3</span></a>
            <a href='/vendas?cat=BEBIDAS&p={p}' class='btn-menu {"ativo" if cat=="BEBIDAS" else ""}'>🍹 BEBIDAS <span>F4</span></a>
        </div>
        <div class='main-area'>
            <h2>{cat}</h2>
            <div class='grid-produtos'>{prods}</div>
        </div>
        <div class='comanda-lateral'>{comanda_display}</div>
    </div></body></html>"""

@app.get("/lancar")
async def lancar(p: str, v: float, i: str, c: str):
    with engine.begin() as conn:
        conn.execute(text("UPDATE pulseiras SET total_conta = total_conta + :v WHERE numero_pulseira = :p AND status = 'ABERTA'"), {"v": v, "p": p})
        conn.execute(text("INSERT INTO vendas_itens (pulseira_num, item_nome, valor) VALUES (:p, :i, :v)"), {"p": p, "i": i, "v": v})
    return RedirectResponse(url=f"/vendas?cat={c}&p={p}", status_code=303)

@app.get("/fechar_conta", response_class=HTMLResponse)
async def fechar_conta(q: str = ""):
    res = ""
    if q:
        with engine.connect() as conn:
            query = conn.execute(text("""
                SELECT p.numero_pulseira, p.total_conta, c.nome_completo 
                FROM pulseiras p 
                JOIN clientes c ON p.cliente_cpf = c.cpf 
                WHERE (p.numero_pulseira = :q OR c.cpf = :q) AND p.status = 'ABERTA'
            """), {"q": q}).fetchone()
            
            if query:
                res = f"""<div style='background:#f4f4f4; padding:20px; border-radius:10px; color:#333; margin-top:20px;'>
                    <h3>Cliente: {query.nome_completo}</h3>
                    <h2 style='color:#d31a21'>Total: R$ {query.total_conta:.2f}</h2>
                    <form action='/confirmar_fechamento' method='post'>
                        <input type='hidden' name='p' value='{query.numero_pulseira}'>
                        <button class='btn-acao' style='background:#28a745; padding:15px; font-size:18px;'>💰 CONFIRMAR PAGAMENTO</button>
                    </form>
                </div>"""
            else:
                res = "<p style='color:red; margin-top:20px;'>Nenhuma comanda aberta encontrada para esta busca.</p>"

    return f"<html><head>{CSS}</head><body><div class='container-center'><div class='card-center'><h2>Fechar Conta</h2><form method='get'><input class='input-padrao' name='q' placeholder='CPF ou Nº da Pulseira' value='{q}' required><button class='btn-acao'>BUSCAR</button></form>{res}<br><a href='/central' style='color:gray'>Voltar</a></div></div></body></html>"

@app.post("/confirmar_fechamento")
async def confirmar_fechamento(p: str = Form(...)):
    with engine.begin() as conn:
        conn.execute(text("UPDATE pulseiras SET status = 'FECHADA' WHERE numero_pulseira = :p"), {"p": p})
    return HTMLResponse("<script>alert('Conta fechada com sucesso!'); window.location.href='/central';</script>")

@app.get("/buscar", response_class=HTMLResponse)
async def tela_busca(q: str = ""):
    resultados = ""
    hoje = date.today().strftime("%m-%d")
    if q:
        with engine.connect() as conn:
            query = conn.execute(text("SELECT nome_completo, cpf, data_nascimento FROM clientes WHERE nome_completo ILIKE :q OR cpf LIKE :q"), {"q": f"%{q}%"}).fetchall()
            for r in query:
                is_bday = r.data_nascimento.strftime("%m-%d") == hoje if r.data_nascimento else False
                resultados += f"<tr><td style='color:black'>{r.nome_completo}{' 🎁' if is_bday else ''}</td><td><form action='/abrir' method='post' style='display:flex;gap:5px'><input type='hidden' name='cpf' value='{r.cpf}'><input class='input-padrao' name='p' placeholder='Nº Pulseira' required style='width:100px;margin:0'><button class='btn-acao' style='background:#d31a21;margin:0;padding:8px'>ABRIR</button></form></td></tr>"
    return f"<html><head>{CSS}</head><body><div class='container-center'><div class='card-center'><h2>Buscar Cliente</h2><form method='get'><input class='input-padrao' name='q' placeholder='Nome ou CPF...' value='{q}'><button class='btn-acao'>BUSCAR</button></form><table><tr><th style='color:black'>Nome</th><th style='color:black'>Ação</th></tr>{resultados}</table><br><a href='/central' style='color:gray'>Voltar</a></div></div></body></html>"

@app.post("/abrir")
async def abrir(cpf: str = Form(...), p: str = Form(...)):
    with engine.begin() as conn:
        conn.execute(text("INSERT INTO pulseiras (numero_pulseira, cliente_cpf, total_conta) VALUES (:p, :c, 7.00)"), {"p": p, "c": cpf})
    return RedirectResponse(url=f"/vendas?p={p}", status_code=303)

@app.get("/cadastro", response_class=HTMLResponse)
async def tela_cadastro():
    return f"<html><head>{CSS}</head><body><div class='container-center'><div class='card-center' style='text-align:left;'><h2>Novo Cliente</h2><form action='/salvar' method='post'><input class='input-padrao' name='nome' placeholder='Nome Completo' required><input class='input-padrao' name='cpf' placeholder='CPF' required><input class='input-padrao' name='nasc' type='date' required><input class='input-padrao' name='contato' placeholder='WhatsApp' required><input class='input-padrao' name='pulseira' placeholder='Nº Pulseira' required style='border:2px solid orange'><button class='btn-acao' style='background:#d31a21'>SALVAR E ABRIR (R$ 7,00)</button></form><a href='/central' style='display:block;text-align:center;color:gray'>Voltar</a></div></div></body></html>"

@app.post("/salvar")
async def salvar(nome: str = Form(...), cpf: str = Form(...), nasc: str = Form(...), contato: str = Form(...), pulseira: str = Form(...)):
    with engine.begin() as conn:
        conn.execute(text("INSERT INTO clientes (nome_completo, cpf, data_nascimento, contato) VALUES (:n, :c, :d, :co) ON CONFLICT (cpf) DO NOTHING"), {"n":nome, "c":cpf, "d":nasc, "co":contato})
        conn.execute(text("INSERT INTO pulseiras (numero_pulseira, cliente_cpf, total_conta) VALUES (:p, :c, 7.00)"), {"p":pulseira, "c":cpf})
    return RedirectResponse(url=f"/vendas?p={pulseira}", status_code=303)

@app.get("/logout")
async def logout(request: Request):
    request.session.clear()
    return RedirectResponse(url="/")
