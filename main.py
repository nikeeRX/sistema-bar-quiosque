from fastapi import FastAPI, Form, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlalchemy import create_engine, text
from starlette.middleware.sessions import SessionMiddleware
from datetime import date

app = FastAPI()
app.add_middleware(SessionMiddleware, secret_key="brahma_riacho_secret")

# --- CONEXÃO (CONFIRA SUA PORTA AQUI) ---
DATABASE_URL = "postgresql://postgres:GNlZnHiuKAcFnpgXhwILfigqKCNkaHqx@interchange.proxy.rlwy.net:44559/railway"
engine = create_engine(DATABASE_URL, pool_pre_ping=True)

CSS = """
<style>
    :root { --azul: #004795; --vermelho: #e21c21; --dourado: #f0ba00; --gelo: #f4f4f4; }
    body { font-family: Arial; background: var(--gelo); margin: 0; text-align: center; }
    .header { background: var(--azul); color: white; padding: 15px; border-bottom: 4px solid var(--dourado); }
    .card { background: white; padding: 25px; border-radius: 10px; box-shadow: 0 4px 10px rgba(0,0,0,0.1); max-width: 500px; margin: 40px auto; }
    .btn { display: block; width: 100%; padding: 15px; margin: 10px 0; border: none; border-radius: 5px; font-weight: bold; cursor: pointer; text-decoration: none; font-size: 16px; }
    .btn-azul { background: var(--azul); color: white; }
    .btn-vermelho { background: var(--vermelho); color: white; }
    input { width: 100%; padding: 12px; margin: 8px 0; border: 1px solid #ccc; border-radius: 5px; box-sizing: border-box; }
</style>
"""

@app.get("/", response_class=HTMLResponse)
async def login_page():
    return f"<html><head>{CSS}</head><body style='display:flex; align-items:center; justify-content:center; height:100vh;'><div class='card'><img src='https://logodownload.org/wp-content/uploads/2014/07/brahma-logo-2.png' width='120'><h2>Acesso Quiosque</h2><form action='/login' method='post'><input name='user' placeholder='Usuário'><input name='pw' type='password' placeholder='Senha'><button class='btn btn-azul'>ENTRAR</button></form></div></body></html>"

@app.post("/login")
async def login(request: Request, user: str = Form(...), pw: str = Form(...)):
    if (user == "portaria" and pw == "riacho") or (user == "admin" and pw == "1234"):
        request.session["user"] = user
        return RedirectResponse(url="/central-portaria", status_code=303)
    return RedirectResponse(url="/", status_code=303)

# --- NOVA TELA: CENTRAL DA PORTARIA ---
@app.get("/central-portaria", response_class=HTMLResponse)
async def central_portaria(request: Request):
    if "user" not in request.session: return RedirectResponse(url="/")
    return f"""
    <html><head>{CSS}</head><body>
        <div class="header"><h1>CENTRAL DA PORTARIA</h1></div>
        <div class="card">
            <img src="https://logodownload.org/wp-content/uploads/2014/07/brahma-logo-2.png" width="100">
            <h3>O que deseja fazer hoje?</h3>
            <a href="/cadastro-cliente" class="btn btn-vermelho">➕ NOVO CADASTRO</a>
            <a href="/buscar-cliente" class="btn btn-azul">🔍 BUSCAR CLIENTE / PULSEIRA</a>
            <br>
            <a href="/" style="color:gray; text-decoration:none;">Sair do Sistema</a>
        </div>
    </body></html>
    """

@app.get("/cadastro-cliente", response_class=HTMLResponse)
async def tela_cadastro(request: Request):
    if "user" not in request.session: return RedirectResponse(url="/")
    hoje = date.today().strftime("%Y-%m-%d")
    return f"""
    <html><head>{CSS}</head><body>
        <div class="header"><h1>CADASTRO DE CLIENTE</h1></div>
        <div class="card" style="text-align:left;">
            <form action="/salvar-cliente" method="post">
                <label>Data:</label><input type="date" name="data_dia" value="{hoje}" readonly>
                <input name="nome" placeholder="Nome Completo" required>
                <input name="cpf" placeholder="CPF (Apenas números)" required>
                <input name="rg" placeholder="RG / ID">
                <label>Nascimento:</label><input type="date" name="nasc" required>
                <input name="contato" placeholder="Celular/WhatsApp" required>
                <input name="pulseira" placeholder="NÚMERO DA PULSEIRA" required style="background:#fff3cd; border: 2px solid orange;">
                <button class="btn btn-vermelho">FINALIZAR E ABRIR COMANDA</button>
            </form>
            <a href="/central-portaria" style="color:gray; display:block; text-align:center; margin-top:10px;">Voltar</a>
        </div>
    </body></html>
    """

@app.post("/salvar-cliente")
async def salvar_cliente(nome: str = Form(...), cpf: str = Form(...), rg: str = Form(...), nasc: str = Form(...), contato: str = Form(...), pulseira: str = Form(...)):
    try:
        with engine.begin() as conn:
            conn.execute(text("INSERT INTO clientes (nome_completo, cpf, rg_id, data_nascimento, contato) VALUES (:n, :cpf, :rg, :nasc, :con) ON CONFLICT (cpf) DO NOTHING"), {"n": nome, "cpf": cpf, "rg": rg, "nasc": nasc, "con": contato})
            conn.execute(text("INSERT INTO pulseiras (numero_pulseira, cliente_cpf, total_conta) VALUES (:p, :cpf, 7.00)"), {"p": pulseira, "cpf": cpf})
        
        # RETORNA O POP-UP EM JAVASCRIPT
        return HTMLResponse(f"""
            <script>
                alert("✅ Cadastro realizado com sucesso!\\n🎫 Comanda Nº {pulseira} aberta com Couvert de R$ 7,00.");
                window.location.href = "/central-portaria";
            </script>
        """)
    except:
        return HTMLResponse("<script>alert('❌ Erro: Pulseira já ativa ou CPF inválido!'); window.history.back();</script>")

@app.get("/buscar-cliente", response_class=HTMLResponse)
async def buscar_cliente(request: Request):
    return f"<html><head>{CSS}</head><body><div class='header'><h1>BUSCA DE CLIENTES</h1></div><div class='card'><h3>Tela de Busca (Em desenvolvimento)</h3><a href='/central-portaria' class='btn btn-azul'>VOLTAR</a></div></body></html>"
