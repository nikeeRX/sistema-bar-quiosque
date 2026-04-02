from fastapi import FastAPI, Form, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlalchemy import create_engine, text
from starlette.middleware.sessions import SessionMiddleware

app = FastAPI()
app.add_middleware(SessionMiddleware, secret_key="brahma_riacho_secret")

# --- CONEXÃO (USE A SUA PORTA REAL AQUI) ---
DATABASE_URL = "postgresql://postgres:GNlZnHiuKAcFnpgXhwILfigqKCNkaHqx@interchange.proxy.rlwy.net:44559/railway"
engine = create_engine(DATABASE_URL, pool_pre_ping=True)

# Criar tabelas extras se não existirem
with engine.begin() as conn:
    conn.execute(text("""
        CREATE TABLE IF NOT EXISTS pulseiras (
            id SERIAL PRIMARY KEY,
            numero_pulseira TEXT UNIQUE NOT NULL,
            status TEXT DEFAULT 'ativa',
            total_conta DECIMAL(10,2) DEFAULT 7.00
        );
    """))

CSS = """
<style>
    :root { --azul: #004795; --vermelho: #e21c21; --dourado: #f0ba00; --gelo: #f4f4f4; }
    body { font-family: Arial; background: var(--gelo); margin: 0; padding-bottom: 60px; }
    .header { background: var(--azul); color: white; padding: 10px 20px; border-bottom: 4px solid var(--dourado); display: flex; justify-content: space-between; align-items: center; }
    .container { max-width: 1200px; margin: 20px auto; display: grid; grid-template-columns: 250px 1fr 300px; gap: 20px; padding: 0 10px; }
    .card { background: white; padding: 20px; border-radius: 10px; box-shadow: 0 4px 10px rgba(0,0,0,0.1); }
    .btn-menu { display: block; background: var(--azul); color: white; padding: 15px; margin-bottom: 10px; text-decoration: none; border-radius: 5px; font-weight: bold; text-align: center; border: none; width: 100%; cursor: pointer; }
    .btn-f3 { background: var(--vermelho); color: white; border: none; padding: 15px; border-radius: 5px; font-weight: bold; width: 100%; cursor: pointer; font-size: 16px; }
    .footer-bars { position: fixed; bottom: 0; width: 100%; background: var(--azul); color: white; display: flex; justify-content: space-around; padding: 10px 0; font-weight: bold; font-size: 13px; }
    .grid-prod { display: grid; grid-template-columns: repeat(auto-fill, minmax(150px, 1fr)); gap: 15px; }
    .prod-item { border: 2px solid #ddd; border-radius: 8px; padding: 10px; text-align: center; background: white; }
</style>
"""

@app.get("/", response_class=HTMLResponse)
async def login_page():
    return f"<html><head>{CSS}</head><body style='display:flex; align-items:center; justify-content:center; height:100vh;'><div class='card' style='width:350px; text-align:center;'><img src='https://logodownload.org/wp-content/uploads/2014/07/brahma-logo-2.png' width='120'><br><h2>Acesso Restrito</h2><form action='/login' method='post'><input name='user' placeholder='Usuário' style='width:100%; padding:10px; margin:10px 0;'><input name='pw' type='password' placeholder='Senha' style='width:100%; padding:10px; margin:10px 0;'><button class='btn-menu'>ENTRAR</button></form></div></body></html>"

@app.post("/login")
async def login(request: Request, user: str = Form(...), pw: str = Form(...)):
    users = {"admin": "1234", "portaria": "riacho", "garcom": "chopp"}
    if user in users and users[user] == pw:
        request.session["user"] = user
        return RedirectResponse(url="/painel", status_code=303)
    return RedirectResponse(url="/", status_code=303)

@app.get("/painel", response_class=HTMLResponse)
async def painel(request: Request):
    if "user" not in request.session: return RedirectResponse(url="/")
    
    # Busca Pulseiras Ativas e Produtos
    with engine.connect() as conn:
        prods = conn.execute(text("SELECT * FROM produtos")).fetchall()
        ativos = conn.execute(text("SELECT * FROM pulseiras WHERE status = 'ativa'")).fetchall()
    
    html_prods = "".join([f"<div class='prod-item'><b>{p.nome}</b><br><span style='color:red'>R$ {p.preco_venda}</span></div>" for p in prods])
    html_pulseiras = "".join([f"<div style='border-bottom:1px solid #ddd; padding:5px;'>Pulseira: <b>{ps.numero_pulseira}</b> - R$ {ps.total_conta}</div>" for ps in ativos])

    return f"""
    <html><head>{CSS}</head><body>
        <div class="header">
            <span>🍺 QUIOSQUE CHOPP BRAHMA - RIACHO MALL</span>
            <a href="/" style="color:white; text-decoration:none;">Sair</a>
        </div>
        <div class="container">
            <div class="card">
                <button class="btn-menu">F1 - CHOPP</button>
                <button class="btn-menu">F2 - CERVEJAS</button>
                <form action="/nova-pulseira" method="post">
                    <input name="num" placeholder="Nº Pulseira" required style="width:100%; padding:10px; margin-bottom:5px;">
                    <button class="btn-f3">F3 - ENTRADA (COUVERT)</button>
                </form>
                <br>
                <a href="/estoque" class="btn-menu" style="background:#666; font-size:12px;">F10 - ESTOQUE</a>
            </div>
            
            <div class="card">
                <h3>🛒 Produtos Disponíveis</h3>
                <div class="grid-prod">{html_prods}</div>
            </div>

            <div class="card" style="background:#eee;">
                <h3>🎫 Pulseiras no Bar</h3>
                {html_pulseiras if html_pulseiras else "Nenhuma pulseira ativa."}
            </div>
        </div>
        <div class="footer-bars">
            <span>F1: Menu</span><span>F2: Consulta</span><span>F3: Portaria</span><span>F12: Ajuda</span>
        </div>
    </body></html>
    """

@app.post("/nova-pulseira")
async def nova_pulseira(num: str = Form(...)):
    try:
        with engine.begin() as conn:
            # Já entra cobrando os 7,00 de couvert do Riacho Mall [cite: 20]
            conn.execute(text("INSERT INTO pulseiras (numero_pulseira, total_conta) VALUES (:n, 7.00)"), {"n": num})
        return RedirectResponse(url="/painel", status_code=303)
    except: return "Pulseira já está ativa ou erro no banco."

@app.get("/estoque", response_class=HTMLResponse)
async def estoque_view(request: Request):
    if request.session.get("user") != "admin": return "Acesso negado."
    # ... código da tabela de estoque que já tínhamos ...
    return "<h1>Área do Admin</h1><a href='/painel'>Voltar</a>"
