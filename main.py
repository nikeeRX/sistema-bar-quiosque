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
    * { box-sizing: border-box; }
    body { font-family: 'Segoe UI', Arial; background: var(--azul); margin: 0; color: white; min-height: 100vh; display: flex; flex-direction: column; }
    
    .main-container { flex: 1; display: flex; align-items: center; justify-content: center; padding: 20px; }
    .card { background: white; color: #333; padding: 30px; border-radius: 15px; box-shadow: 0 10px 25px rgba(0,0,0,0.3); width: 100%; max-width: 500px; text-align: center; }
    
    .btn { display: block; width: 100%; padding: 15px; margin: 10px 0; border: none; border-radius: 8px; font-weight: bold; cursor: pointer; text-decoration: none; font-size: 16px; transition: 0.2s; }
    .btn-azul { background: var(--azul); color: white; }
    .btn-vermelho { background: var(--vermelho); color: white; }
    
    input, select { width: 100%; padding: 12px; margin: 8px 0; border: 1px solid #ccc; border-radius: 5px; font-size: 16px; }
    
    .footer-atallhos { background: #002d5f; padding: 10px; display: flex; justify-content: space-around; font-size: 13px; font-weight: bold; }
    
    /* Layout de Vendas Responsivo */
    .vendas-wrapper { display: flex; flex-wrap: wrap; gap: 20px; width: 100%; max-width: 1200px; }
    .menu-lateral { flex: 1; min-width: 250px; }
    .grade-produtos { flex: 2; min-width: 300px; display: grid; grid-template-columns: repeat(auto-fill, minmax(140px, 1fr)); gap: 10px; }
    .prod-item { background: white; color: #333; padding: 10px; border-radius: 10px; text-align: center; cursor: pointer; border: 2px solid transparent; }
    .prod-item:hover { border-color: var(--vermelho); }
</style>
"""

@app.get("/", response_class=HTMLResponse)
async def login_page():
    return f"<html><head>{CSS}</head><body><div class='main-container'><div class='card'><img src='https://logodownload.org/wp-content/uploads/2014/07/brahma-logo-2.png' width='120'><h2>Acesso Restrito</h2><form action='/login' method='post'><input name='user' placeholder='Usuário'><input name='pw' type='password' placeholder='Senha'><button class='btn btn-azul'>ENTRAR</button></form></div></div></body></html>"

@app.post("/login")
async def login(request: Request, user: str = Form(...), pw: str = Form(...)):
    if (user == "admin" and pw == "1234") or (user == "garcom" and pw == "chopp") or (user == "portaria" and pw == "riacho"):
        request.session["user"] = user
        return RedirectResponse(url="/central", status_code=303)
    return RedirectResponse(url="/", status_code=303)

@app.get("/central", response_class=HTMLResponse)
async def central(request: Request):
    if "user" not in request.session: return RedirectResponse(url="/")
    return f"<html><head>{CSS}</head><body><div class='main-container'><div class='card'><h3>Olá, {request.session['user'].capitalize()}</h3><a href='/cadastro' class='btn btn-vermelho'>➕ NOVO CADASTRO</a><a href='/vendas' class='btn btn-azul'>🛒 IR PARA VENDAS</a><br><a href='/' style='color:gray; text-decoration:none;'>Sair</a></div></div><div class='footer-atallhos'><span>F1: Menu</span><span>F3: Novo Cliente</span></div></body></html>"

@app.get("/cadastro", response_class=HTMLResponse)
async def tela_cadastro():
    return f"""<html><head>{CSS}</head><body><div class='main-container'><div class='card' style='text-align:left;'><h2>Cadastro de Cliente</h2><form action='/salvar-abrir' method='post'>
    <input name='nome' placeholder='Nome Completo' required>
    <input name='cpf' placeholder='CPF (obrigatório)' required>
    <input name='nasc' type='date' required>
    <input name='fone' placeholder='Contato' required>
    <input name='pulseira' placeholder='Nº DA PULSEIRA' required style='border: 2px solid orange; background: #fff3cd;'>
    <button class='btn btn-vermelho'>SALVAR E ABRIR COMANDA</button>
    </form><a href='/central' style='display:block; text-align:center; color:gray;'>Voltar</a></div></div></body></html>"""

@app.post("/salvar-abrir")
async def salvar_abrir(nome: str = Form(...), cpf: str = Form(...), pulseira: str = Form(...)):
    try:
        with engine.begin() as conn:
            conn.execute(text("INSERT INTO clientes (nome_completo, cpf) VALUES (:n, :c) ON CONFLICT (cpf) DO NOTHING"), {{"n":nome, "c":cpf}})
            conn.execute(text("INSERT INTO pulseiras (numero_pulseira, cliente_cpf, total_conta) VALUES (:p, :c, 7.00)"), {{"p":pulseira, "c":cpf}})
        return HTMLResponse(f"<script>alert('✅ Cadastro Sucesso! Pulseira {pulseira} ativa.'); window.location.href='/vendas';</script>")
    except: return "Erro ao processar. Verifique se a pulseira já está em uso."

@app.get("/vendas", response_class=HTMLResponse)
async def tela_vendas(cat: str = "Chopps"):
    # Itens extraídos do seu cardápio oficial [cite: 17, 19, 88]
    menu = {{
        "Chopps": [("Caneca 350ml", 11.90), ("Tulipa 700ml", 17.90), ("Torre 2.5L", 84.90)],
        "Cervejas": [("Original 600ml", 12.90), ("Spaten LN", 8.90), ("Heineken 600ml", 16.90)],
        "Petiscos": [("Batata Frita", 21.90), ("Frango Passarinho", 28.90), ("Carne de Sol", 54.90)]
    }}
    
    prod_html = ""
    for nome, preco in menu.get(cat, []):
        prod_html += f"<div class='prod-item' onclick='lancar(\"{{nome}}\", {{preco}})'><b>{{nome}}</b><br><span style='color:red'>R$ {{preco}}</span></div>"

    return f"""<html><head>{CSS}
    <script>
        function lancar(n, v) {{
            let p = prompt("Digite o Nº da Pulseira do Cliente:");
            if(p) window.location.href = `/lancar?p=${{p}}&v=${{v}}`;
        }}
    </script>
    </head><body><div class='main-container'><div class='vendas-wrapper'>
        <div class='menu-lateral'>
            <a href='/vendas?cat=Chopps' class='btn btn-azul'>🍺 CHOPPS</a>
            <a href='/vendas?cat=Cervejas' class='btn btn-azul'>🍾 CERVEJAS</a>
            <a href='/vendas?cat=Petiscos' class='btn btn-azul'>🍟 PETISCOS</a>
            <a href='/central' class='btn btn-vermelho'>VOLTAR</a>
        </div>
        <div class='grade-produtos'>{{prod_html}}</div>
    </div></div></body></html>"""

@app.get("/lancar")
async def lancar(p: str, v: float):
    with engine.begin() as conn:
        conn.execute(text("UPDATE pulseiras SET total_conta = total_conta + :v WHERE numero_pulseira = :p"), {{"v": v, "p": p}})
    return HTMLResponse("<script>alert('✅ Lançado com sucesso!'); window.location.href='/vendas';</script>")
