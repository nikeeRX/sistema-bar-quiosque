from fastapi import FastAPI, Form, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlalchemy import create_engine, text
from starlette.middleware.sessions import SessionMiddleware
from datetime import date

app = FastAPI()
app.add_middleware(SessionMiddleware, secret_key="brahma_riacho_secret")

# --- CONEXÃO OFICIAL ---
DATABASE_URL = "postgresql://postgres:GNlZnHiuKAcFnpgXhwILfigqKCNkaHqx@interchange.proxy.rlwy.net:44559/railway"
engine = create_engine(DATABASE_URL, pool_pre_ping=True)

# --- CRIAÇÃO AUTOMÁTICA DAS TABELAS ---
with engine.begin() as conn:
    conn.execute(text("""
        CREATE TABLE IF NOT EXISTS clientes (
            id SERIAL PRIMARY KEY,
            nome_completo TEXT NOT NULL,
            cpf TEXT UNIQUE NOT NULL,
            rg_id TEXT,
            data_nascimento DATE,
            contato TEXT,
            data_cadastro DATE DEFAULT CURRENT_DATE
        );
        CREATE TABLE IF NOT EXISTS pulseiras (
            id SERIAL PRIMARY KEY,
            numero_pulseira TEXT UNIQUE NOT NULL,
            cliente_cpf TEXT REFERENCES clientes(cpf),
            status TEXT DEFAULT 'ativa',
            total_conta DECIMAL(10,2) DEFAULT 7.00
        );
    """))

CSS = """
<style>
    :root { --azul-brahma: #004795; --vermelho-brahma: #e21c21; --dourado: #f0ba00; --gelo: #e8ecef; }
    body { font-family: 'Segoe UI', Arial; background: #1a4a8e; margin: 0; color: white; height: 100vh; overflow: hidden; }
    .viewport { display: grid; grid-template-columns: 280px 1fr 320px; height: calc(100vh - 60px); padding: 15px; gap: 15px; }
    .sidebar { display: flex; flex-direction: column; gap: 10px; }
    .cat-button { background: rgba(255,255,255,0.1); border: 1px solid rgba(255,255,255,0.3); padding: 15px; border-radius: 12px; 
                  display: flex; align-items: center; color: white; text-decoration: none; font-weight: bold; position: relative; }
    .cat-button:hover, .cat-active { background: white; color: var(--azul-brahma); }
    .product-grid { background: rgba(255,255,255,0.05); border-radius: 15px; padding: 20px; display: grid; 
                    grid-template-columns: repeat(auto-fill, minmax(180px, 1fr)); gap: 15px; overflow-y: auto; }
    .product-card { background: white; border-radius: 12px; overflow: hidden; text-align: center; color: #333; cursor: pointer; }
    .product-info { background: var(--vermelho-brahma); color: white; padding: 10px; font-weight: bold; }
    .comanda-panel { background: white; border-radius: 15px; color: #333; display: flex; flex-direction: column; }
    .comanda-header { background: var(--azul-brahma); color: white; padding: 15px; text-align: center; font-weight: bold; }
    .function-bar { height: 60px; background: #002d5f; display: flex; align-items: center; justify-content: space-around; font-weight: bold; }
    input { width: 100%; padding: 12px; margin: 8px 0; border: 1px solid #ccc; border-radius: 5px; box-sizing: border-box; }
</style>
"""

@app.get("/", response_class=HTMLResponse)
async def login_page():
    return f"<html><head>{CSS}</head><body style='display:flex; align-items:center; justify-content:center; height:100vh;'><div style='background:white; padding:30px; border-radius:15px; color:#333; text-align:center; width:350px;'><img src='https://logodownload.org/wp-content/uploads/2014/07/brahma-logo-2.png' width='120'><h2>PDV Riacho Mall</h2><form action='/login' method='post'><input name='user' placeholder='Usuário'><input name='pw' type='password' placeholder='Senha'><button style='background:var(--azul-brahma); color:white; width:100%; padding:15px; border:none; border-radius:5px; font-weight:bold; cursor:pointer;'>ENTRAR</button></form></div></body></html>"

@app.post("/login")
async def login(request: Request, user: str = Form(...), pw: str = Form(...)):
    if (user == "admin" and pw == "1234") or (user == "garcom" and pw == "chopp") or (user == "portaria" and pw == "riacho"):
        request.session["user"] = user
        return RedirectResponse(url="/vendas", status_code=303)
    return RedirectResponse(url="/", status_code=303)

@app.get("/vendas", response_class=HTMLResponse)
async def vendas_interface(request: Request, cat: str = "Chopp"):
    if "user" not in request.session: return RedirectResponse(url="/")
    
    # Produtos do seu Cardápio [cite: 17, 19, 88]
    menu = {
        "Chopp": [("Caneca 350ml", 11.90), ("Tulipa 700ml", 17.90), ("Torre 2.5L", 84.90)],
        "Cervejas": [("Original 600ml", 12.90), ("Spaten LN", 8.90), ("Heineken 600ml", 16.90)],
        "Petiscos": [("Batata Frita", 21.90), ("Frango Passarinho", 28.90), ("Carne de Sol", 54.90)]
    }

    prod_html = ""
    for nome, preco in menu.get(cat, []):
        prod_html += f"""
        <div class="product-card" onclick="lancar('{nome}', {preco})">
            <img src="https://logodownload.org/wp-content/uploads/2014/07/brahma-logo-2.png" style="width:60px; margin:20px;">
            <div class="product-info">{nome}<br>R$ {preco}</div>
        </div>"""

    return f"""
    <html><head>{CSS}
    <script>
        function lancar(nome, preco) {{
            let p = prompt("Digite o Nº da Pulseira:");
            if(p) window.location.href = `/efetuar-venda?p=${{p}}&item=${{nome}}&v=${{preco}}`;
        }}
    </script>
    </head><body>
        <div class="viewport">
            <div class="sidebar">
                <a href="/vendas?cat=Chopp" class="cat-button {'cat-active' if cat=='Chopp' else ''}">🍺 CHOPP <span style="position:absolute; right:10px;">F1</span></a>
                <a href="/vendas?cat=Cervejas" class="cat-button {'cat-active' if cat=='Cervejas' else ''}">🍾 CERVEJAS <span style="position:absolute; right:10px;">F2</span></a>
                <a href="/vendas?cat=Petiscos" class="cat-button {'cat-active' if cat=='Petiscos' else ''}">🍟 PETISCOS <span style="position:absolute; right:10px;">F3</span></a>
                <hr>
                <a href="/cadastro-cliente" class="cat-button" style="background:var(--vermelho-brahma)">➕ NOVO CLIENTE</a>
            </div>
            <div class="product-grid">{prod_html}</div>
            <div class="comanda-panel">
                <div class="comanda-header">Comanda Atual (Mesa 04)</div>
                <div style="flex:1; padding:15px; color:#999; text-align:center;">Selecione um item...</div>
                <div style="padding:15px; border-top:1px solid #eee; color:#333;">
                    <div style="display:flex; justify-content:space-between; font-size:20px; font-weight:bold;"><span>Total</span><span>R$ 0,00</span></div>
                </div>
            </div>
        </div>
        <div class="function-bar">
            <span>F1: Menu Principal</span><span>F2: Consultar</span><span>F3: Novo Cliente</span><span>F12: Ajuda</span>
        </div>
    </body></html>
    """

@app.get("/efetuar-venda")
async def efetuar_venda(p: str, item: str, v: float):
    with engine.begin() as conn:
        conn.execute(text("UPDATE pulseiras SET total_conta = total_conta + :v WHERE numero_pulseira = :p"), {"v": v, "p": p})
    return HTMLResponse(f"<script>alert('✅ {item} lançado!'); window.location.href='/vendas';</script>")

@app.get("/cadastro-cliente", response_class=HTMLResponse)
async def tela_cadastro():
    return f"<html><head>{CSS}</head><body style='display:flex; align-items:center; justify-content:center; height:100vh;'><div style='background:white; padding:30px; border-radius:15px; color:#333; width:400px;'><h2>Novo Cadastro</h2><form action='/salvar' method='post'><input name='n' placeholder='Nome Completo' required><input name='c' placeholder='CPF' required><input name='p' placeholder='Nº Pulseira' required style='border:2px solid orange'><button style='background:var(--vermelho-brahma); color:white; width:100%; padding:15px; border:none; border-radius:5px; font-weight:bold; cursor:pointer;'>SALVAR E ABRIR (R$ 7,00)</button></form><br><a href='/vendas'>Voltar</a></div></body></html>"

@app.post("/salvar")
async def salvar(n: str = Form(...), c: str = Form(...), p: str = Form(...)):
    with engine.begin() as conn:
        conn.execute(text("INSERT INTO clientes (nome_completo, cpf) VALUES (:n, :c) ON CONFLICT (cpf) DO NOTHING"), {"n":n, "c":c})
        conn.execute(text("INSERT INTO pulseiras (numero_pulseira, cliente_cpf, total_conta) VALUES (:p, :c, 7.00)"), {"p":p, "c":c})
    return HTMLResponse("<script>alert('✅ Cliente Cadastrado!'); window.location.href='/vendas';</script>")
