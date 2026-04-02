from fastapi import FastAPI, Form, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlalchemy import create_engine, text
from starlette.middleware.sessions import SessionMiddleware

app = FastAPI()
app.add_middleware(SessionMiddleware, secret_key="brahma_riacho_secret")

# --- CONEXÃO OFICIAL ---
DATABASE_URL = "postgresql://postgres:GNlZnHiuKAcFnpgXhwILfigqKCNkaHqx@interchange.proxy.rlwy.net:44559/railway"
engine = create_engine(DATABASE_URL, pool_pre_ping=True)

CSS = """
<style>
    :root { --azul: #004795; --vermelho: #e21c21; --dourado: #f0ba00; --gelo: #f4f4f4; }
    * { box-sizing: border-box; }
    body { font-family: 'Segoe UI', Arial; background: var(--azul); margin: 0; color: white; min-height: 100vh; display: flex; flex-direction: column; }
    .main-container { flex: 1; display: flex; align-items: center; justify-content: center; padding: 20px; width: 100%; }
    .card { background: white; color: #333; padding: 25px; border-radius: 15px; box-shadow: 0 10px 25px rgba(0,0,0,0.3); width: 100%; max-width: 600px; text-align: center; }
    .btn { display: block; width: 100%; padding: 15px; margin: 10px 0; border: none; border-radius: 8px; font-weight: bold; cursor: pointer; text-decoration: none; font-size: 16px; transition: 0.2s; text-align: center; }
    .btn-azul { background: var(--azul); color: white; }
    .btn-vermelho { background: var(--vermelho); color: white; }
    input { width: 100%; padding: 12px; margin: 8px 0; border: 1px solid #ccc; border-radius: 5px; font-size: 16px; }
    table { width: 100%; border-collapse: collapse; margin-top: 15px; color: #333; }
    th, td { padding: 12px; border-bottom: 1px solid #eee; text-align: left; }
    .footer-atallhos { background: #002d5f; padding: 10px; display: flex; justify-content: space-around; font-size: 13px; }
</style>
"""

@app.get("/", response_class=HTMLResponse)
async def login_page():
    return f"<html><head>{CSS}</head><body><div class='main-container'><div class='card'><img src='https://logodownload.org/wp-content/uploads/2014/07/brahma-logo-2.png' width='120'><h2>Acesso Quiosque</h2><form action='/login' method='post'><input name='user' placeholder='Usuário'><input name='pw' type='password' placeholder='Senha'><button class='btn btn-azul'>ENTRAR</button></form></div></div></body></html>"

@app.post("/login")
async def login(request: Request, user: str = Form(...), pw: str = Form(...)):
    if (user == "admin" and pw == "1234") or (user == "garcom" and pw == "chopp") or (user == "portaria" and pw == "riacho"):
        request.session["user"] = user
        return RedirectResponse(url="/central", status_code=303)
    return RedirectResponse(url="/", status_code=303)

@app.get("/central", response_class=HTMLResponse)
async def central(request: Request):
    if "user" not in request.session: return RedirectResponse(url="/")
    return f"""<html><head>{CSS}</head><body><div class='main-container'><div class='card'>
    <img src='https://logodownload.org/wp-content/uploads/2014/07/brahma-logo-2.png' width='80'>
    <h3>Painel de Controle</h3>
    <a href='/cadastro' class='btn btn-vermelho'>➕ NOVO CADASTRO</a>
    <a href='/buscar' class='btn btn-azul'>🔍 BUSCAR CLIENTE / ABRIR COMANDA</a>
    <a href='/vendas' class='btn btn-azul' style='background:#555'>🛒 IR PARA VENDAS</a>
    <br><a href='/' style='color:gray; text-decoration:none;'>Sair</a>
    </div></div><div class='footer-atallhos'><span>F1: Menu</span><span>F3: Novo</span></div></body></html>"""

@app.get("/buscar", response_class=HTMLResponse)
async def tela_busca(q: str = ""):
    resultados = ""
    if q:
        with engine.connect() as conn:
            query = conn.execute(text("SELECT nome_completo, cpf FROM clientes WHERE nome_completo ILIKE :q OR cpf LIKE :q"), {"q": f"%{q}%"}).fetchall()
            for r in query:
                resultados += f"""<tr>
                    <td>{r.nome_completo}</td>
                    <td><form action='/abrir-existente' method='post' style='display:flex; gap:5px;'>
                        <input type='hidden' name='cpf' value='{r.cpf}'>
                        <input name='p' placeholder='Nº Pulseira' required style='margin:0; padding:5px;'>
                        <button class='btn-vermelho' style='padding:5px 10px; border-radius:5px; border:none; cursor:pointer;'>ABRIR</button>
                    </form></td>
                </tr>"""
    
    return f"""<html><head>{CSS}</head><body><div class='main-container'><div class='card'>
    <h2>Buscar Cliente</h2>
    <form method='get'><input name='q' placeholder='Nome ou CPF...' value='{q}'><button class='btn btn-azul'>PESQUISAR</button></form>
    <table><tr><th>Nome</th><th>Ação</th></tr>{resultados if resultados else "<tr><td colspan='2'>Nenhum cliente selecionado</td></tr>"}</table>
    <br><a href='/central' style='color:gray;'>Voltar</a>
    </div></div></body></html>"""

@app.post("/abrir-existente")
async def abrir_existente(cpf: str = Form(...), p: str = Form(...)):
    try:
        with engine.begin() as conn:
            conn.execute(text("INSERT INTO pulseiras (numero_pulseira, cliente_cpf, total_conta) VALUES (:p, :c, 7.00)"), {"p": p, "c": cpf})
        return HTMLResponse(f"<script>alert('✅ Comanda {p} aberta!'); window.location.href='/vendas';</script>")
    except: return "Erro: Pulseira já em uso ou problema no banco."

@app.get("/cadastro", response_class=HTMLResponse)
async def tela_cadastro():
    return f"""<html><head>{CSS}</head><body><div class='main-container'><div class='card' style='text-align:left;'>
    <h2 style='text-align:center;'>Novo Cadastro</h2>
    <form action='/salvar-novo' method='post'>
        <input name='nome' placeholder='Nome Completo' required>
        <input name='cpf' placeholder='CPF' required>
        <input name='pulseira' placeholder='Nº DA PULSEIRA' required style='border: 2px solid orange;'>
        <button class='btn btn-vermelho'>CADASTRAR E ABRIR COMANDA</button>
    </form>
    <a href='/central' style='display:block; text-align:center; color:gray;'>Voltar</a>
    </div></div></body></html>"""

@app.post("/salvar-novo")
async def salvar_novo(nome: str = Form(...), cpf: str = Form(...), pulseira: str = Form(...)):
    with engine.begin() as conn:
        conn.execute(text("INSERT INTO clientes (nome_completo, cpf) VALUES (:n, :c) ON CONFLICT (cpf) DO NOTHING"), {"n":nome, "c":cpf})
        conn.execute(text("INSERT INTO pulseiras (numero_pulseira, cliente_cpf, total_conta) VALUES (:p, :c, 7.00)"), {"p":pulseira, "c":cpf})
    return HTMLResponse(f"<script>alert('✅ Tudo pronto! Pulseira {pulseira} ativa.'); window.location.href='/vendas';</script>")

@app.get("/vendas", response_class=HTMLResponse)
async def tela_vendas():
    # Tela simples de vendas para teste de responsividade
    return f"<html><head>{CSS}</head><body><div class='main-container'><div class='card'><h2>Módulo de Vendas</h2><p>Aqui aparecerá o cardápio do PDF.</p><a href='/central' class='btn btn-azul'>VOLTAR À CENTRAL</a></div></div></body></html>"
