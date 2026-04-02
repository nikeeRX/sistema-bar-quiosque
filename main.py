from fastapi import FastAPI, Form, Request, HTTPException
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from sqlalchemy import create_engine, text
from starlette.middleware.sessions import SessionMiddleware

app = FastAPI()
# Adiciona suporte a login (sessão)
app.add_middleware(SessionMiddleware, secret_key="quiosque_secret_key")

# --- SUA URL DA RAILWAY (Mantenha a sua!) ---
DATABASE_URL = "postgresql://postgres:GNlZnHiuKAcFnpgXhwILfigqKCNkaHqx@interchange.proxy.rlwy.net:44559/railway"
engine = create_engine(DATABASE_URL, pool_pre_ping=True)

# --- ESTILOS CSS (Cores Chopp Brahma) ---
CSS = """
<style>
    :root { --azul: #004795; --vermelho: #e21c21; --dourado: #f0ba00; --gelo: #f4f4f4; }
    body { font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; background: var(--gelo); margin: 0; }
    .header { background: var(--azul); color: white; padding: 15px; text-align: center; border-bottom: 5px solid var(--dourado); }
    .container { max-width: 1200px; margin: 20px auto; display: flex; gap: 20px; padding: 0 15px; }
    .sidebar { width: 250px; background: white; border-radius: 10px; padding: 15px; box-shadow: 0 4px 10px rgba(0,0,0,0.1); }
    .menu-item { background: var(--azul); color: white; padding: 12px; margin-bottom: 10px; border-radius: 5px; text-align: center; cursor: pointer; text-decoration: none; display: block; font-weight: bold; }
    .menu-item:hover { background: #003570; }
    .main-content { flex: 1; background: white; padding: 25px; border-radius: 10px; box-shadow: 0 4px 10px rgba(0,0,0,0.1); }
    .login-card { max-width: 400px; margin: 100px auto; background: white; padding: 40px; border-radius: 15px; border-top: 10px solid var(--azul); text-align: center; }
    input { width: 90%; padding: 12px; margin: 10px 0; border: 1px solid #ccc; border-radius: 5px; }
    .btn { background: var(--vermelho); color: white; border: none; padding: 12px 25px; border-radius: 5px; cursor: pointer; font-weight: bold; width: 100%; }
    .grid-produtos { display: grid; grid-template-columns: repeat(auto-fill, minmax(200px, 1fr)); gap: 15px; }
    .card-prod { border: 1px solid #ddd; padding: 15px; border-radius: 8px; text-align: center; transition: 0.3s; }
    .card-prod:hover { transform: scale(1.02); box-shadow: 0 5px 15px rgba(0,0,0,0.1); }
</style>
"""

# --- ROTAS DE LOGIN ---
@app.get("/", response_class=HTMLResponse)
async def login_page(request: Request):
    return f"""
    <html><head>{CSS}</head><body>
        <div class="login-card">
            <img src="https://logodownload.org/wp-content/uploads/2014/07/brahma-logo-2.png" width="150">
            <h2 style="color:var(--azul)">Quiosque Riacho Mall</h2>
            <form action="/login" method="post">
                <input name="user" placeholder="Usuário" required>
                <input name="pw" type="password" placeholder="Senha" required>
                <button class="btn">ENTRAR NO SISTEMA</button>
            </form>
        </div>
    </body></html>
    """

@app.post("/login")
async def login(request: Request, user: str = Form(...), pw: str = Form(...)):
    # Lógica simples de usuários
    users = {"admin": ("1234", "admin"), "portaria": ("riacho", "portaria"), "garcom": ("chopp", "garcom")}
    if user in users and users[user][0] == pw:
        request.session["user"] = user
        request.session["role"] = users[user][1]
        return RedirectResponse(url="/painel", status_code=303)
    return HTMLResponse("<h2>Acesso Negado!</h2><a href='/'>Voltar</a>")

@app.get("/logout")
async def logout(request: Request):
    request.session.clear()
    return RedirectResponse(url="/")

# --- PAINEL PRINCIPAL (LAYOUT DA IMAGEM) ---
@app.get("/painel", response_class=HTMLResponse)
async def painel(request: Request):
    if "user" not in request.session: return RedirectResponse(url="/")
    
    role = request.session["role"]
    user_nome = request.session["user"].capitalize()
    
    # Busca produtos do banco
    lista_cards = ""
    with engine.connect() as conn:
        produtos = conn.execute(text("SELECT * FROM produtos")).fetchall()
        for p in produtos:
            lista_cards += f"""
            <div class="card-prod">
                <div style="font-size:12px; color:#888;">F{p.id}</div>
                <b style="color:var(--azul)">{p.nome}</b><br>
                <span style="color:var(--vermelho); font-weight:bold;">R$ {p.preco_venda}</span><br>
                <small>Estoque: {p.estoque_atual}</small>
            </div>
            """

    return f"""
    <html><head>{CSS}</head><body>
        <div class="header">
            <img src="https://logodownload.org/wp-content/uploads/2014/07/brahma-logo-2.png" width="80" style="float:left">
            <h1 style="margin:0;">QUIOSQUE CHOPP BRAHMA - RIACHO MALL</h1>
            <span style="float:right; margin-top:-30px;">Olá, {user_nome} | <a href="/logout" style="color:white">Sair</a></span>
        </div>
        
        <div class="container">
            <div class="sidebar">
                <a href="/painel" class="menu-item">F1 - CHOPP</a>
                <a href="#" class="menu-item">F2 - CERVEJAS</a>
                <a href="#" class="menu-item">F3 - PETISCOS</a>
                <a href="/estoque" class="menu-item" style="background:grey">F10 - GESTÃO ESTOQUE</a>
            </div>
            
            <div class="main-content">
                <h2 style="color:var(--azul)">🛒 Terminal de Vendas</h2>
                <div class="grid-produtos">
                    {lista_cards}
                </div>
            </div>
            
            <div class="sidebar" style="background:#eee;">
                <h3>Comanda Atual</h3>
                <p style="font-size:14px;">Mesa: <b>01</b></p>
                <hr>
                <p>Nenhum item lançado.</p>
                <button class="btn" style="background:var(--azul)">FECHAR CONTA</button>
            </div>
        </div>
        
        <div style="position:fixed; bottom:0; width:100%; background:var(--azul); color:white; padding:10px; display:flex; justify-content:space-around; font-size:12px;">
            <span>F1: Menu Principal</span>
            <span>F2: Consultar Produto</span>
            <span>F3: Novo Cliente (Pulseira)</span>
            <span>F12: Ajuda</span>
        </div>
    </body></html>
    """

# --- TELA DE ESTOQUE (ADMIN ONLY) ---
@app.get("/estoque", response_class=HTMLResponse)
async def estoque(request: Request):
    if request.session.get("role") != "admin": return "Acesso restrito ao Admin."
    # ... aqui você mantém a tabela de estoque que já tínhamos ...
    return "<h3>Página de Estoque em manutenção para o novo layout. Acesse o painel principal.</h3><a href='/painel'>Voltar</a>"
