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

CSS = """
<style>
    :root { --azul: #004795; --vermelho: #e21c21; --dourado: #f0ba00; --gelo: #f4f4f4; }
    body { font-family: 'Segoe UI', Arial; background: var(--gelo); margin: 0; }
    .header { background: var(--azul); color: white; padding: 15px; border-bottom: 4px solid var(--dourado); text-align: center; }
    .card { background: white; padding: 20px; border-radius: 10px; box-shadow: 0 4px 10px rgba(0,0,0,0.1); max-width: 800px; margin: 20px auto; }
    .btn { display: block; width: 100%; padding: 15px; margin: 10px 0; border: none; border-radius: 5px; font-weight: bold; cursor: pointer; text-decoration: none; font-size: 16px; box-sizing: border-box; text-align: center; }
    .btn-azul { background: var(--azul); color: white; }
    .btn-vermelho { background: var(--vermelho); color: white; }
    .btn-dourado { background: var(--dourado); color: black; }
    .grid-categorias { display: grid; grid-template-columns: 1fr 1fr; gap: 15px; }
    .grid-produtos { display: grid; grid-template-columns: repeat(auto-fill, minmax(180px, 1fr)); gap: 15px; margin-top: 20px; }
    .card-prod { border: 2px solid var(--azul); padding: 15px; border-radius: 10px; cursor: pointer; background: white; transition: 0.3s; }
    .card-prod:hover { background: var(--dourado); }
    input { width: 100%; padding: 12px; margin: 8px 0; border: 1px solid #ccc; border-radius: 5px; box-sizing: border-box; }
</style>
"""

# --- LOGIN E CENTRAL (O que já funciona) ---
@app.get("/", response_class=HTMLResponse)
async def login_page():
    return f"<html><head>{CSS}</head><body style='display:flex; align-items:center; justify-content:center; height:100vh;'><div class='card' style='max-width:400px;'><img src='https://logodownload.org/wp-content/uploads/2014/07/brahma-logo-2.png' width='120'><h2>Quiosque Riacho Mall</h2><form action='/login' method='post'><input name='user' placeholder='Usuário'><input name='pw' type='password' placeholder='Senha'><button class='btn btn-azul'>ENTRAR</button></form></div></body></html>"

@app.post("/login")
async def login(request: Request, user: str = Form(...), pw: str = Form(...)):
    users = {"admin": "1234", "portaria": "riacho", "garcom": "chopp"}
    if user in users and users[user] == pw:
        request.session["user"] = user
        return RedirectResponse(url="/central", status_code=303)
    return RedirectResponse(url="/", status_code=303)

@app.get("/central", response_class=HTMLResponse)
async def central(request: Request):
    if "user" not in request.session: return RedirectResponse(url="/")
    return f"""
    <html><head>{CSS}</head><body>
        <div class="header"><h1>CENTRAL DE OPERAÇÕES</h1></div>
        <div class="card">
            <h3 style="color:var(--azul)">Olá, {request.session['user'].capitalize()}!</h3>
            <div class="grid-categorias">
                <a href="/cadastro-cliente" class="btn btn-vermelho">➕ NOVO CADASTRO</a>
                <a href="/buscar-cliente" class="btn btn-azul">🔍 BUSCAR CLIENTE</a>
            </div>
            <a href="/vendas" class="btn btn-dourado" style="font-size:20px; padding:25px;">🛒 ABRIR CARDÁPIO (VENDAS)</a>
            <br><a href="/logout" style="color:gray; text-decoration:none;">Sair do Sistema</a>
        </div>
    </body></html>
    """

# --- TELA DE VENDAS (CARDÁPIO POR CATEGORIA) ---
@app.get("/vendas", response_class=HTMLResponse)
async def tela_vendas(cat: str = "Chopps"):
    # Mock de produtos baseado no seu PDF (Isso aqui depois puxamos do banco)
    menu = {
        "Chopps": [("Caneca 350ml", 11.90), ("Tulipa 700ml", 17.90), ("Torre 2.5L", 84.90)],
        "Cervejas": [("Original 600ml", 12.90), ("Spaten LN", 8.90), ("Heineken 600ml", 16.90)],
        "Petiscos": [("Batata Frita", 21.90), ("Frango Passarinho", 28.90), ("Carne de Sol", 54.90)],
        "Drinks": [("Caipirinha", 14.90), ("Gin Tônica", 22.00)],
        "Refris": [("Lata", 4.90), ("Água", 3.50)]
    }
    
    produtos_html = ""
    for nome, preco in menu.get(cat, []):
        produtos_html += f"""
        <div class="card-prod" onclick="lancar('{nome}', '{preco}')">
            <b>{nome}</b><br>
            <span style="color:var(--vermelho)">R$ {preco}</span>
        </div>"""

    return f"""
    <html><head>{CSS}
    <script>
        function lancar(nome, preco) {{
            let pulseira = prompt("Digite o número da PULSEIRA para lançar " + nome + ":");
            if (pulseira) {{
                window.location.href = "/efetuar-venda?p=" + pulseira + "&item=" + nome + "&valor=" + preco;
            }}
        }}
    </script>
    </head><body>
        <div class="header"><h1>CARDÁPIO - {cat.upper()}</h1></div>
        <div class="card">
            <div class="grid-categorias">
                <a href="/vendas?cat=Chopps" class="btn btn-azul">🍺 CHOPPS</a>
                <a href="/vendas?cat=Cervejas" class="btn btn-azul">🍾 CERVEJAS</a>
                <a href="/vendas?cat=Petiscos" class="btn btn-azul">🍟 PETISCOS</a>
                <a href="/vendas?cat=Drinks" class="btn btn-azul">🍹 DRINKS</a>
                <a href="/vendas?cat=Refris" class="btn btn-azul">🥤 BEBIDAS/SUCOS</a>
            </div>
            <div class="grid-produtos">{produtos_html}</div>
            <br><a href="/central" class="btn btn-vermelho">VOLTAR AO MENU</a>
        </div>
    </body></html>"""

@app.get("/efetuar-venda")
async def efetuar_venda(p: str, item: str, valor: float):
    try:
        with engine.begin() as conn:
            # Atualiza o saldo da pulseira
            conn.execute(text("UPDATE pulseiras SET total_conta = total_conta + :v WHERE numero_pulseira = :p"), {"v": valor, "p": p})
        return HTMLResponse(f"<script>alert('✅ {item} lançado na pulseira {p}!'); window.location.href='/vendas';</script>")
    except:
        return HTMLResponse("<script>alert('❌ Erro: Pulseira não encontrada!'); window.history.back();</script>")

@app.get("/logout")
async def logout(request: Request):
    request.session.clear()
    return RedirectResponse(url="/")

# --- MANTÉM AS ROTAS DE CADASTRO E BUSCA QUE JÁ FUNCIONAM ---
@app.get("/cadastro-cliente", response_class=HTMLResponse)
async def tela_cadastro(request: Request):
    hoje = date.today().strftime("%Y-%m-%d")
    return f"<html><head>{CSS}</head><body><div class='header'><h1>NOVO CADASTRO</h1></div><div class='card'><form action='/salvar-cliente' method='post'><input name='nome' placeholder='Nome Completo' required><input name='cpf' placeholder='CPF' required><input name='pulseira' placeholder='Nº PULSEIRA' required style='background:#fff3cd; border: 2px solid orange;'><button class='btn btn-vermelho'>CADASTRAR E ABRIR</button></form><a href='/central'>Voltar</a></div></body></html>"

@app.post("/salvar-cliente")
async def salvar_cliente(nome: str = Form(...), cpf: str = Form(...), pulseira: str = Form(...)):
    with engine.begin() as conn:
        conn.execute(text("INSERT INTO clientes (nome_completo, cpf) VALUES (:n, :c) ON CONFLICT (cpf) DO NOTHING"), {"n":nome, "c":cpf})
        conn.execute(text("INSERT INTO pulseiras (numero_pulseira, cliente_cpf, total_conta) VALUES (:p, :c, 7.00)"), {"p":pulseira, "c":cpf})
    return HTMLResponse(f"<script>alert('✅ OK!'); window.location.href='/central';</script>")
