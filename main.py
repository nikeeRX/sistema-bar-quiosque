from fastapi import FastAPI, HTTPException, Request, Form
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlalchemy import create_engine, text

app = FastAPI(title="Sistema Quiosque Brahma")

# --- 1. CONEXÃO ---
DATABASE_URL = "postgresql://postgres:Somdeboas2026@db.zykgsosahlavullteema.supabase.co:6543/postgres?prepare_threshold=0"
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
                # Se achou o usuário, manda para a tela de vendas
                return RedirectResponse(url="/vendas", status_code=302)
            else:
                return HTMLResponse("<script>alert('Usuário ou Senha Incorretos!'); window.location.href='/';</script>")
    except Exception as e:
        return HTMLResponse(f"<h1>Erro de Conexão: {str(e)}</h1>")

# --- 4. TELA DE VENDAS (O Balcão) ---
@app.get("/vendas", response_class=HTMLResponse)
async def tela_vendas():
    return """
    <html>
        <head><title>Balcão - Quiosque Brahma</title></head>
        <body style="background-color: #004795; color: white; font-family: Arial; text-align: center; padding-top: 50px;">
            <img src="https://logodownload.org/wp-content/uploads/2014/04/brahma-logo-1.png" width="150">
            <h1>SISTEMA LIBERADO! 🍻</h1>
            <p>O motor está roncando. Agora vamos montar os botões do Chopp!</p>
            <button onclick="window.location.href='/'" style="padding: 10px; cursor: pointer;">Sair</button>
        </body>
    </html>
    """

