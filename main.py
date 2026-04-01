from fastapi import FastAPI, HTTPException, Request, Form, UploadFile, File
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlalchemy import create_engine, text

app = FastAPI()

# --- CONEXÃO COM POOLER (PARA PULAR FIREWALL) ---
DATABASE_URL = "postgresql://postgres:Somdeboas23@db.zykgsosahlavullteema.supabase.co:5432/postgres?sslmode=require"
engine = create_engine(DATABASE_URL)

# --- TELA DE LOGIN ---
@app.get("/", response_class=HTMLResponse)
async def login():
    return """
    <body style="background:#004795; display:flex; justify-content:center; align-items:center; height:100vh; font-family:Arial;">
        <div style="background:white; padding:40px; border-radius:15px; text-align:center; border:4px solid #f0ba00;">
            <h2 style="color:#e21c21;">QUIOSQUE BRAHMA</h2>
            <form action="/login" method="post">
                <input name="username" placeholder="Usuário" style="display:block; width:100%; margin:10px 0; padding:10px;">
                <input name="password" type="password" placeholder="Senha" style="display:block; width:100%; margin:10px 0; padding:10px;">
                <button style="background:#e21c21; color:white; width:100%; padding:10px; cursor:pointer; font-weight:bold;">ENTRAR (F2)</button>
            </form>
        </div>
    </body>
    """

@app.post("/login")
async def do_login(username: str = Form(...), password: str = Form(...)):
    with engine.connect() as conn:
        res = conn.execute(text("SELECT * FROM usuarios WHERE username=:u AND password=:p"), {"u":username, "p":password}).fetchone()
        if res: return RedirectResponse("/painel", status_code=303)
        return "Erro: Usuário ou senha inválidos"

# --- PAINEL DE GESTÃO (ESTOQUE E CADASTRO) ---
@app.get("/painel", response_class=HTMLResponse)
async def painel():
    return """
    <body style="background:#004795; color:white; font-family:Arial; padding:20px;">
        <div style="display:flex; justify-content:space-between; border-bottom:2px solid #f0ba00;">
            <h1>GERENCIAMENTO DE ESTOQUE</h1>
            <a href="/" style="color:white; text-decoration:none;">SAIR (ESC)</a>
        </div>
        
        <div style="display:grid; grid-template-columns: 1fr 2fr; gap:20px; margin-top:20px;">
            <div style="background:rgba(255,255,255,0.1); padding:20px; border-radius:10px;">
                <h3>CADASTRAR NOVO PRODUTO</h3>
                <form action="/cadastrar" method="post">
                    <input name="codigo" placeholder="Código do Produto" style="width:100%; margin:5px 0; padding:8px;">
                    <input name="nome" placeholder="Descrição/Nome" style="width:100%; margin:5px 0; padding:8px;">
                    <input name="preco" placeholder="Valor de Venda (Ex: 12.50)" style="width:100%; margin:5px 0; padding:8px;">
                    <input name="estoque" placeholder="Qtd em Estoque" style="width:100%; margin:5px 0; padding:8px;">
                    <label><input type="checkbox" name="promo"> Item em Promoção?</label>
                    <button style="width:100%; background:#f0ba00; color:#004795; font-weight:bold; padding:10px; margin-top:10px; border:none; cursor:pointer;">SALVAR PRODUTO (F5)</button>
                </form>
            </div>

            <div style="background:white; color:#333; padding:20px; border-radius:10px;">
                <h3>ITENS NO INVENTÁRIO</h3>
                <table style="width:100%; border-collapse:collapse;">
                    <tr style="background:#eee;">
                        <th style="padding:10px; text-align:left;">Cod</th>
                        <th style="padding:10px; text-align:left;">Produto</th>
                        <th style="padding:10px; text-align:left;">Preço</th>
                        <th style="padding:10px; text-align:left;">Estoque</th>
                        <th style="padding:10px; text-align:left;">Status</th>
                    </tr>
                    </table>
            </div>
        </div>
    </body>
    """

# --- LÓGICA DE CADASTRO NO BANCO ---
@app.post("/cadastrar")
async def cadastrar(codigo: str = Form(...), nome: str = Form(...), preco: float = Form(...), estoque: int = Form(...), promo: bool = Form(False)):
    try:
        with engine.begin() as conn:
            conn.execute(text("""
                INSERT INTO produtos (nome, preco_venda, estoque_atual, codigo_barras, em_promocao) 
                VALUES (:n, :p, :e, :c, :promo)
            """), {"n": nome, "p": preco, "e": estoque, "c": codigo, "promo": promo})
        return RedirectResponse("/painel", status_code=303)
    except Exception as e:
        return f"Erro ao cadastrar: {str(e)}"
