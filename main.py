from fastapi import FastAPI, Form, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlalchemy import create_engine, text
from starlette.middleware.sessions import SessionMiddleware
from datetime import date, datetime

app = FastAPI()
app.add_middleware(SessionMiddleware, secret_key="brahma_riacho_mall_2024")

# --- CONEXÃO OFICIAL ---
DATABASE_URL = "postgresql://postgres:GNlZnHiuKAcFnpgXhwILfigqKCNkaHqx@interchange.proxy.rlwy.net:44559/railway"
engine = create_engine(DATABASE_URL, pool_pre_ping=True)

# --- GARANTIA DE TABELAS (RODA AO INICIAR) ---
with engine.begin() as conn:
    conn.execute(text("""
        CREATE TABLE IF NOT EXISTS clientes (
            id SERIAL PRIMARY KEY,
            nome_completo TEXT NOT NULL,
            cpf TEXT UNIQUE NOT NULL,
            data_nascimento DATE,
            contato TEXT,
            email TEXT
        );
        CREATE TABLE IF NOT EXISTS pulseiras (
            id SERIAL PRIMARY KEY,
            numero_pulseira TEXT UNIQUE NOT NULL,
            cliente_cpf TEXT REFERENCES clientes(cpf),
            total_conta DECIMAL(10,2) DEFAULT 7.00
        );
        CREATE TABLE IF NOT EXISTS vendas_itens (
            id SERIAL PRIMARY KEY,
            pulseira_num TEXT,
            item_nome TEXT,
            valor DECIMAL(10,2),
            data_venda DATE DEFAULT CURRENT_DATE,
            hora_venda TIME DEFAULT CURRENT_TIME
        );
    """))

CSS = """
<style>
    :root { --azul: #004795; --vermelho: #e21c21; --gelo: #f4f4f4; }
    * { box-sizing: border-box; }
    body { font-family: 'Segoe UI', Arial; background: var(--azul); margin: 0; color: white; min-height: 100vh; display: flex; flex-direction: column; }
    .container { flex: 1; display: flex; align-items: center; justify-content: center; padding: 20px; }
    .card { background: white; color: #333; padding: 30px; border-radius: 15px; width: 100%; max-width: 600px; text-align: center; box-shadow: 0 8px 20px rgba(0,0,0,0.4); }
    .btn { display: block; width: 100%; padding: 15px; margin: 10px 0; border: none; border-radius: 8px; font-weight: bold; cursor: pointer; text-decoration: none; font-size: 16px; text-align: center; }
    .btn-azul { background: var(--azul); color: white; }
    .btn-vermelho { background: var(--vermelho); color: white; }
    input { width: 100%; padding: 12px; margin: 8px 0; border: 1px solid #ccc; border-radius: 5px; }
    table { width: 100%; border-collapse: collapse; margin-top: 15px; }
    th, td { padding: 10px; border-bottom: 1px solid #eee; text-align: left; }
    .gift { font-size: 18px; }
</style>
"""

# --- 1. ROTA RAIZ (LOGIN) - RESOLVE O ERRO NOT FOUND ---
@app.get("/", response_class=HTMLResponse)
async def login_page():
    return f"""<html><head>{CSS}</head><body><div class='container'><div class='card'>
    <img src='https://logodownload.org/wp-content/uploads/2014/07/brahma-logo-2.png' width='120'>
    <h2>Acesso ao Sistema</h2>
    <form action='/login' method='post'>
        <input name='user' placeholder='Usuário' required>
        <input name='pw' type='password' placeholder='Senha' required>
        <button class='btn btn-azul'>ENTRAR</button>
    </form></div></div></body></html>"""

@app.post("/login")
async def login(request: Request, user: str = Form(...), pw: str = Form(...)):
    if (user == "admin" and pw == "1234") or (user == "garcom" and pw == "chopp"):
        request.session["user"] = user
        return RedirectResponse(url="/central", status_code=303)
    return RedirectResponse(url="/", status_code=303)

# --- 2. CENTRAL ---
@app.get("/central", response_class=HTMLResponse)
async def central(request: Request):
    if "user" not in request.session: return RedirectResponse(url="/")
    return f"""<html><head>{CSS}</head><body><div class='container'><div class='card'>
    <h3>Olá, {request.session['user'].capitalize()}</h3>
    <a href='/cadastro' class='btn btn-vermelho'>➕ NOVO CADASTRO</a>
    <a href='/buscar' class='btn btn-azul'>🔍 BUSCAR / ABRIR COMANDA</a>
    <a href='/vendas' class='btn btn-azul' style='background:#444'>🛒 MÓDULO DE VENDAS</a>
    <br><a href='/logout' style='color:gray; text-decoration:none;'>Sair</a>
    </div></div></body></html>"""

# --- 3. BUSCA COM DATA E ANIVERSÁRIO ---
@app.get("/buscar", response_class=HTMLResponse)
async def tela_busca(q: str = ""):
    resultados = ""
    hoje = date.today().strftime("%m-%d")
    if q:
        with engine.connect() as conn:
            query = conn.execute(text("SELECT nome_completo, cpf, data_nascimento FROM clientes WHERE nome_completo ILIKE :q OR cpf LIKE :q"), {"q": f"%{q}%"}).fetchall()
            for r in query:
                is_bday = r.data_nascimento.strftime("%m-%d") == hoje if r.data_nascimento else False
                gift = " <span class='gift'>🎁</span>" if is_bday else ""
                nasc = r.data_nascimento.strftime("%d/%m") if r.data_nascimento else "--"
                resultados += f"<tr><td>{r.nome_completo}{gift}</td><td>{nasc}</td><td><form action='/abrir' method='post' style='display:flex;gap:5px'><input type='hidden' name='cpf' value='{r.cpf}'><input name='p' placeholder='Nº Pulseira' required style='width:80px;padding:5px;margin:0'><button class='btn-vermelho' style='border:none;padding:5px;cursor:pointer'>ABRIR</button></form></td></tr>"
    
    return f"<html><head>{CSS}</head><body><div class='container'><div class='card'><h2>Buscar Cliente</h2><form method='get'><input name='q' placeholder='Nome ou CPF...' value='{q}'><button class='btn btn-azul'>BUSCAR</button></form><table><tr><th>Nome</th><th>Nasc.</th><th>Ação</th></tr>{resultados}</table><br><a href='/central'>Voltar</a></div></div></body></html>"

@app.post("/abrir")
async def abrir(cpf: str = Form(...), p: str = Form(...)):
    with engine.begin() as conn:
        conn.execute(text("INSERT INTO pulseiras (numero_pulseira, cliente_cpf, total_conta) VALUES (:p, :c, 7.00)"), {"p": p, "c": cpf})
    return HTMLResponse(f"<script>alert('✅ Comanda {p} aberta!'); window.location.href='/vendas';</script>")

# --- 4. CADASTRO COMPLETO ---
@app.get("/cadastro", response_class=HTMLResponse)
async def tela_cadastro():
    return f"""<html><head>{CSS}</head><body><div class='container'><div class='card' style='text-align:left;'>
    <h2 style='text-align:center;'>Novo Cliente</h2>
    <form action='/salvar' method='post'>
        <input name='nome' placeholder='Nome Completo' required>
        <input name='cpf' placeholder='CPF' required>
        <input name='nasc' type='date' required>
        <input name='contato' placeholder='WhatsApp' required>
        <input name='email' placeholder='E-mail'>
        <input name='pulseira' placeholder='Nº Pulseira' required style='border:2px solid orange'>
        <button class='btn btn-vermelho'>SALVAR E ABRIR COMANDA (R$ 7,00)</button>
    </form><a href='/central' style='display:block;text-align:center;color:gray'>Voltar</a></div></div></body></html>"""

@app.post("/salvar")
async def salvar(nome: str = Form(...), cpf: str = Form(...), nasc: str = Form(...), contato: str = Form(...), email: str = Form(None), pulseira: str = Form(...)):
    with engine.begin() as conn:
        conn.execute(text("INSERT INTO clientes (nome_completo, cpf, data_nascimento, contato, email) VALUES (:n, :c, :d, :co, :e) ON CONFLICT (cpf) DO NOTHING"), {"n":nome, "c":cpf, "d":nasc, "co":contato, "e":email})
        conn.execute(text("INSERT INTO pulseiras (numero_pulseira, cliente_cpf, total_conta) VALUES (:p, :c, 7.00)"), {"p":pulseira, "c":cpf})
    return RedirectResponse(url="/vendas", status_code=303)

# --- 5. VENDAS E LOG FINANCEIRO ---
@app.get("/vendas", response_class=HTMLResponse)
async def vendas(cat: str = "Chopps"):
    menu = {"Chopps": [("Caneca 350ml", 11.9), ("Tulipa 700ml", 17.9), ("Torre 2.5L", 84.9)], "Cervejas": [("Original 600ml", 12.9), ("Spaten LN", 8.9)], "Petiscos": [("Batata Frita", 21.9), ("Carne Sol", 54.9)]}
    prods = "".join([f"<div style='background:#fff;padding:15px;border-radius:10px;color:#333;cursor:pointer' onclick='lancar(\"{n}\", {p})'><b>{n}</b><br><span style='color:red'>R$ {p}</span></div>" for n, p in menu.get(cat, [])])
    return f"""<html><head>{CSS}
    <script>function lancar(n, v){{ let p = prompt("Nº Pulseira:"); if(p) window.location.href=`/lancar?p=${{p}}&v=${{v}}&i=${{n}}`; }}</script>
    </head><body><div class='container'><div class='card' style='max-width:800px'>
    <div style='display:flex;gap:10px;margin-bottom:20px'><a href='/vendas?cat=Chopps' class='btn btn-azul'>🍺 CHOPPS</a><a href='/vendas?cat=Cervejas' class='btn btn-azul'>🍾 CERVEJAS</a><a href='/vendas?cat=Petiscos' class='btn btn-azul'>🍟 PETISCOS</a></div>
    <div style='display:grid;grid-template-columns:repeat(auto-fill, minmax(140px, 1fr));gap:10px'>{prods}</div>
    <br><a href='/central' class='btn btn-vermelho'>VOLTAR</a>
    </div></div></body></html>"""

@app.get("/lancar")
async def lancar(p: str, v: float, i: str):
    with engine.begin() as conn:
        conn.execute(text("UPDATE pulseiras SET total_conta = total_conta + :v WHERE numero_pulseira = :p"), {"v": v, "p": p})
        conn.execute(text("INSERT INTO vendas_itens (pulseira_num, item_nome, valor) VALUES (:p, :i, :v)"), {"p": p, "i": i, "v": v})
    return HTMLResponse(f"<script>alert('{i} lançado!'); window.location.href='/vendas';</script>")

@app.get("/logout")
async def logout(request: Request):
    request.session.clear()
    return RedirectResponse(url="/")
