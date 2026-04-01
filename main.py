from fastapi import FastAPI, HTTPException, Request, Form, UploadFile, File
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlalchemy import create_engine, text
import uvicorn

app = FastAPI(title="Sistema Quiosque Brahma")

# --- 1. CONEXÃO LIMPA (Removido o parâmetro que deu erro) ---
DATABASE_URL = "postgresql://postgres:Somdeboas23@db.zykgsosahlavullteema.supabase.co:6543/postgres"
engine = create_engine(DATABASE_URL)

# --- 2. TELA DE LOGIN ---
@app.get("/", response_class=HTMLResponse)
async def tela_login():
    return """
    <html>
        <head>
            <title>Login - Quiosque Chopp Brahma</title>
            <style>
                body { background-color: #004795; font-family: Arial; display: flex; justify-content: center; align-items: center; height: 100vh; margin: 0; }
                .login-card { background: white; padding: 40px; border-radius: 15px; border: 4px solid #f0ba00; text-align: center; width: 350px; box-shadow: 0 10px 25px rgba(0,0,0,0.3); }
                h1 { color: #e21c21; margin-bottom: 25px; font-size: 20px; text-transform: uppercase; }
                input { width: 100%; padding: 12px; margin: 10px 0; border: 2px solid #ccc; border-radius: 5px; box-sizing: border-box; font-size: 16px; }
                button { background: #e21c21; color: white; border: none; padding: 15px; width: 100%; border-radius: 5px; cursor: pointer; font-weight: bold; font-size: 18px; margin-top: 10px; }
            </style>
        </head>
        <body>
            <div class="login-card">
                <img src="https://logodownload.org/wp-content/uploads/2014/04/brahma-logo-1.png" width="100">
                <h1>Quiosque Chopp Brahma</h1>
                <form action="/login" method="post">
                    <input type="text" name="username" placeholder="Usuário" required autofocus>
                    <input type="password" name="password" placeholder="Senha" required>
                    <button type="submit">ENTRAR (F2)</button>
                </form>
            </div>
        </body>
    </html>
    """

# --- 3. PROCESSA O LOGIN ---
@app.post("/login")
async def processa_login(username: str = Form(...), password: str = Form(...)):
    try:
        with engine.connect() as conn:
            query = text("SELECT username FROM usuarios WHERE username = :u AND password = :p")
            user = conn.execute(query, {"u": username, "p": password}).fetchone()
            if user:
                return RedirectResponse(url="/vendas", status_code=303)
            else:
                return HTMLResponse("<script>alert('Usuário ou Senha Incorretos!'); window.location.href='/';</script>")
    except Exception as e:
        return HTMLResponse(f"<h1>Erro de Conexão: Verifique a senha do Banco</h1><p>{str(e)}</p>")

# --- 4. TELA DE VENDAS E GESTÃO ---
@app.get("/vendas", response_class=HTMLResponse)
async def tela_vendas():
    return """
    <html>
        <head>
            <title>Painel - Quiosque Brahma</title>
            <style>
                body { background-color: #004795; color: white; font-family: Arial; margin: 0; padding: 20px; }
                .header { display: flex; justify-content: space-between; align-items: center; border-bottom: 2px solid #f0ba00; padding-bottom: 10px; }
                .menu-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 20px; margin-top: 30px; }
                .btn-acao { background: #e21c21; border: 2px solid white; color: white; padding: 30px; border-radius: 10px; cursor: pointer; font-size: 18px; font-weight: bold; text-align: center; text-decoration: none; }
                .btn-acao:hover { background: #f0ba00; color: #004795; }
            </style>
        </head>
        <body>
            <div class="header">
                <img src="https://logodownload.org/wp-content/uploads/2014/04/brahma-logo-1.png" width="80">
                <h2>PAINEL DE CONTROLE</h2>
                <a href="/" style="color: white;">Sair (Esc)</a>
            </div>
            
            <div class="menu-grid">
                <div class="btn-acao">VENDAS (F1)</div>
                <div class="btn-acao">ESTOQUE / PRODUTOS (F4)</div>
                <div class="btn-acao">CADASTRAR ITEM (F5)</div>
                <div class="btn-acao">RELATÓRIOS (F9)</div>
            </div>

            <div style="margin-top: 50px; background: rgba(255,255,255,0.1); padding: 20px; border-radius: 10px;">
                <h3>Status do Sistema: <span style="color: #00ff00;">ONLINE</span></h3>
                <p>Banco de Dados Conectado com Sucesso.</p>
            </div>
        </body>
    </html>
    """
