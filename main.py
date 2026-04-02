from fastapi import FastAPI, Form, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlalchemy import create_engine, text
from starlette.middleware.sessions import SessionMiddleware
from datetime import date

app = FastAPI()
app.add_middleware(SessionMiddleware, secret_key="brahma_riacho_secret")

# --- CONEXÃO (USE A SUA PORTA REAL AQUI) ---
DATABASE_URL = "postgresql://postgres:GNlZnHiuKAcFnpgXhwILfigqKCNkaHqx@interchange.proxy.rlwy.net:44559/railway"
engine = create_engine(DATABASE_URL, pool_pre_ping=True)

# Criar tabelas de Clientes e Comandas
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
    :root { --azul: #004795; --vermelho: #e21c21; --dourado: #f0ba00; --gelo: #f4f4f4; }
    body { font-family: Arial; background: var(--gelo); margin: 0; }
    .header { background: var(--azul); color: white; padding: 15px; border-bottom: 4px solid var(--dourado); text-align: center; }
    .card { background: white; padding: 25px; border-radius: 10px; box-shadow: 0 4px 10px rgba(0,0,0,0.1); max-width: 600px; margin: 20px auto; }
    input { width: 100%; padding: 12px; margin: 8px 0; border: 1px solid #ccc; border-radius: 5px; box-sizing: border-box; }
    .btn-reg { background: var(--vermelho); color: white; border: none; padding: 15px; border-radius: 5px; font-weight: bold; width: 100%; cursor: pointer; font-size: 16px; margin-top: 10px; }
</style>
"""

@app.get("/", response_class=HTMLResponse)
async def login_page():
    return f"<html><head>{CSS}</head><body style='display:flex; align-items:center; justify-content:center; height:100vh;'><div class='card' style='text-align:center;'><img src='https://logodownload.org/wp-content/uploads/2014/07/brahma-logo-2.png' width='120'><h2>Acesso Quiosque</h2><form action='/login' method='post'><input name='user' placeholder='Usuário'><input name='pw' type='password' placeholder='Senha'><button class='btn-reg' style='background:var(--azul)'>ENTRAR</button></form></div></body></html>"

@app.post("/login")
async def login(request: Request, user: str = Form(...), pw: str = Form(...)):
    users = {"admin": "1234", "portaria": "riacho", "garcom": "chopp"}
    if user in users and users[user] == pw:
        request.session["user"] = user
        # REDIRECIONAMENTO DA PORTARIA
        if user == "portaria": return RedirectResponse(url="/cadastro-cliente", status_code=303)
        return RedirectResponse(url="/painel", status_code=303)
    return RedirectResponse(url="/", status_code=303)

@app.get("/cadastro-cliente", response_class=HTMLResponse)
async def tela_cadastro(request: Request):
    if "user" not in request.session: return RedirectResponse(url="/")
    hoje = date.today().strftime("%Y-%m-%d")
    return f"""
    <html><head>{CSS}</head><body>
        <div class="header"><h1>PORTARIA - CADASTRO OBRIGATÓRIO</h1></div>
        <div class="card">
            <form action="/salvar-cliente" method="post">
                <label>Data de Hoje:</label><input type="date" name="data_dia" value="{hoje}" readonly>
                <input name="nome" placeholder="Nome Completo" required>
                <input name="cpf" placeholder="CPF (Apenas números)" required>
                <input name="rg" placeholder="RG / ID">
                <label>Data de Nascimento:</label><input type="date" name="nasc" required>
                <input name="contato" placeholder="Celular/WhatsApp" required>
                <hr>
                <h3 style="color:var(--azul)">ABRIR COMANDA</h3>
                <input name="pulseira" placeholder="NÚMERO DA PULSEIRA" required style="background:#fff3cd; border: 2px solid var(--dourado);">
                <button class="btn-reg">SALVAR E LIBERAR ENTRADA</button>
            </form>
            <br><a href="/painel" style="text-decoration:none; color:gray;">Pular para Painel (Busca)</a>
        </div>
    </body></html>
    """

@app.post("/salvar-cliente")
async def salvar_cliente(nome: str = Form(...), cpf: str = Form(...), rg: str = Form(...), nasc: str = Form(...), contato: str = Form(...), pulseira: str = Form(...)):
    try:
        with engine.begin() as conn:
            # 1. Salva o Cliente
            conn.execute(text("""
                INSERT INTO clientes (nome_completo, cpf, rg_id, data_nascimento, contato) 
                VALUES (:n, :cpf, :rg, :nasc, :con) ON CONFLICT (cpf) DO NOTHING
            """), {"n": nome, "cpf": cpf, "rg": rg, "nasc": nasc, "con": contato})
            
            # 2. Abre a Pulseira com o Couvert de R$ 7,00
            conn.execute(text("""
                INSERT INTO pulseiras (numero_pulseira, cliente_cpf, total_conta) 
                VALUES (:p, :cpf, 7.00)
            """), {"p": pulseira, "cpf": cpf})
            
        return RedirectResponse(url="/painel", status_code=303)
    except Exception as e:
        return f"<h2>Erro: Pulseira já ativa ou CPF duplicado!</h2><p>{e}</p><a href='/cadastro-cliente'>Voltar</a>"

@app.get("/painel", response_class=HTMLResponse)
async def painel(request: Request):
    if "user" not in request.session: return RedirectResponse(url="/")
    # ... aqui você mantém a lógica de busca e visualização que já fizemos ...
    return f"<html><head>{CSS}</head><body><div class='header'><h1>SISTEMA OPERACIONAL</h1></div><div class='card'><h2>Bem-vindo, {request.session['user']}</h2><a href='/cadastro-cliente'>Novo Cadastro</a> | <a href='/logout'>Sair</a></div></body></html>"
