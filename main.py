from fastapi import FastAPI, HTTPException, Request, Form
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlalchemy import create_engine, text
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles

app = FastAPI(title="Sistema Quiosque Brahma")

# --- 1. CONEXÃO (AJUSTADA COM A PORTA 6543) ---
DATABASE_URL = "postgresql://postgres:Somdeboas23@db.zykgsosahlavullteema.supabase.co:6543/postgres?prepare_threshold=0"
engine = create_engine(DATABASE_URL)

# --- 2. TELAS (HTML) ---
@app.get("/", response_class=HTMLResponse)
async def tela_login():
    return """
    <html>
        <head>
            <title>Login - Quiosque Chopp Brahma</title>
            <style>
                body { background-color: #004795; font-family: Arial; display: flex; justify-content: center; align-items: center; height: 100vh; margin: 0; }
                .login-card { background: white; padding: 40px; border-radius: 15px; border: 4px solid #f0ba00; text-align: center; width: 350px; box-shadow: 0 10px 25px rgba(0,0,0,0.3); }
                h1 { color: #e21c21; margin-bottom: 25px; font-size: 24px; text-transform: uppercase; }
                input { width: 100%; padding: 12px; margin: 10px 0; border: 2px solid #ccc; border-radius: 5px; box-sizing: border-box; font-size: 16px; }
                button { background: #e21c21; color: white; border: none; padding: 15px; width: 100%; border-radius: 5px; cursor: pointer; font-weight: bold; font-size: 18px; margin-top: 10px; }
                .atalhos { margin-top: 20px; font-size: 12px; color: #666; }
            </style>
        </head>
        <body>
            <div class="login-card">
                <img src="https://logodownload.org/wp-content/uploads/2014/04/brahma-logo-1.png" width="120">
                <h1>Quiosque Chopp Brahma</h1>
                <form action="/login" method="post">
                    <input type="text" name="username" placeholder="Usuário" required autofocus id="user">
                    <input type="password" name="password" placeholder="Senha" required id="pass">
                    <button type="submit">ENTRAR (F2)</button>
                </form>
                <div class="atalhos">
                    F2: Entrar | F3: Ajuda
                </div>
            </div>
            <script>
                document.addEventListener('keydown', function(e) {
                    if (e.key === 'F2') document.querySelector('form').submit();
                    if (e.key === 'F3') alert('Contate o gerente para suporte.');
                });
            </script>
        </body>
    </html>
    """

@app.post("/login")
async def processa_login(username: str = Form(...), password: str = Form(...)):
    with engine.connect() as conn:
        query = text("SELECT * FROM usuarios WHERE username = :u AND password = :p")
        user = conn.execute(query, {"u": username, "p": password}).fetchone()
        
        if user:
            return RedirectResponse(url="/vendas", status_code=303)
        else:
            return HTMLResponse("<script>alert('Usuário ou Senha Incorretos!'); window.location.href='/';</script>")

@app.get("/vendas", response_class=HTMLResponse)
async def tela_vendas():
    return "<h1>Login com Sucesso! Em breve a tela de vendas aqui...</h1>"

@app.get("/aniversariantes")
async def lista_aniversariantes():
    with engine.connect() as conn:
        result = conn.execute(text("SELECT nome FROM clientes WHERE EXTRACT(MONTH FROM data_nascimento) = EXTRACT(MONTH FROM CURRENT_DATE)"))
        return [row[0] for row in result]

INSERT INTO usuarios (username, password) VALUES ('admin', '1234');
