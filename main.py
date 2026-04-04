from fastapi import FastAPI, Form, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlalchemy import create_engine, text
from starlette.middleware.sessions import SessionMiddleware
from datetime import date
import json

app = FastAPI()
app.add_middleware(SessionMiddleware, secret_key="brahma_riacho_mall_2024")

DATABASE_URL = "postgresql://postgres:GNlZnHiuKAcFnpgXhwILfigqKCNkaHqx@interchange.proxy.rlwy.net:44559/railway"
engine = create_engine(DATABASE_URL, pool_pre_ping=True)

with engine.begin() as conn:
    conn.execute(text("""
        CREATE TABLE IF NOT EXISTS clientes (
            id SERIAL PRIMARY KEY, nome_completo TEXT NOT NULL, cpf TEXT UNIQUE NOT NULL,
            data_nascimento DATE, contato TEXT, email TEXT
        );
        CREATE TABLE IF NOT EXISTS pulseiras (
            id SERIAL PRIMARY KEY, numero_pulseira TEXT NOT NULL, cliente_cpf TEXT REFERENCES clientes(cpf),
            total_conta DECIMAL(10,2) DEFAULT 7.00, status TEXT DEFAULT 'ABERTA'
        );
        CREATE TABLE IF NOT EXISTS vendas_itens (
            id SERIAL PRIMARY KEY, pulseira_num TEXT, item_nome TEXT, valor DECIMAL(10,2),
            data_venda DATE DEFAULT CURRENT_DATE, hora_venda TIME DEFAULT CURRENT_TIME, status TEXT DEFAULT 'ABERTA'
        );
        CREATE TABLE IF NOT EXISTS estoque (
            item_nome TEXT UNIQUE NOT NULL, quantidade INT DEFAULT 0
        );
    """))
    try: conn.execute(text("ALTER TABLE pulseiras DROP CONSTRAINT IF EXISTS pulseiras_numero_pulseira_key;"))
    except: pass

CSS = """
<style>
    * { box-sizing: border-box; font-family: 'Segoe UI', Tahoma, sans-serif; }
    body { margin: 0; background: #0a3a7a; color: white; height: 100vh; display: flex; flex-direction: column; overflow: hidden; }
    .layout-vendas { display: flex; flex: 1; height: 100vh; }
    .menu-lateral { width: 220px; padding: 20px; display: flex; flex-direction: column; gap: 10px; border-right: 1px solid rgba(255,255,255,0.1); background: #082d5e; }
    .btn-menu { background: #0a3a7a; color: white; border: 1px solid #1352a3; padding: 15px; border-radius: 8px; text-align: left; font-weight: bold; font-size: 16px; cursor: pointer; text-decoration: none; display: flex; justify-content: space-between; }
    .btn-menu:hover, .btn-menu.ativo { background: #d31a21; border-color: white; }
    .main-area { flex: 1; padding: 20px; display: flex; flex-direction: column; overflow-y: auto; align-items: center; }
    .logo-central { width: 160px; margin-bottom: 20px; filter: drop-shadow(0px 4px 6px rgba(0,0,0,0.5)); }
    .grid-produtos { display: grid; grid-template-columns: repeat(auto-fill, minmax(160px, 1fr)); gap: 15px; width: 100%; max-width: 900px; }
    .prod-card { background: linear-gradient(180deg, #d31a21 0%, #9e0b10 100%); border: 2px solid #5a0407; border-radius: 10px; padding: 15px 10px; text-align: center; cursor: pointer; display: flex; flex-direction: column; justify-content: space-between; min-height: 110px; box-shadow: 0 4px 6px rgba(0,0,0,0.3); }
    .prod-card:hover { transform: scale(1.05); border-color: white; }
    .prod-card b { font-size: 14px; margin-bottom: 8px; }
    .prod-card span { font-size: 16px; font-weight: bold; background: rgba(0,0,0,0.2); padding: 5px; border-radius: 5px; }
    .comanda-lateral { width: 340px; background: white; color: black; border-left: 5px solid #d31a21; display: flex; flex-direction: column; }
    .comanda-header { background: #d31a21; color: white; padding: 15px; font-weight: bold; text-align: center; font-size: 18px; }
    .comanda-body { flex: 1; overflow-y: auto; padding: 15px; background: #f9f9f9; }
    .secao-titulo { font-size: 12px; color: #666; text-transform: uppercase; font-weight: bold; border-bottom: 1px solid #ccc; margin-bottom: 10px; padding-bottom: 5px; }
    .item-linha { display: flex; justify-content: space-between; font-size: 14px; margin-bottom: 8px; border-bottom: 1px dashed #ddd; padding-bottom: 5px; }
    .comanda-footer { padding: 15px; background: white; border-top: 1px solid #ccc; }
    .btn-acao { display: block; width: 100%; padding: 15px; margin-bottom: 8px; border: none; border-radius: 5px; font-weight: bold; color: white; cursor: pointer; text-align: center; text-decoration: none; font-size: 14px; background: #062b5e; }
    .btn-acao:hover { background: #0d4b9c; }
    .container-center { display: flex; align-items: center; justify-content: center; height: 100vh; padding: 20px; overflow-y: auto;}
    .card-center { background: white; color: #333; padding: 30px; border-radius: 15px; width: 100%; max-width: 500px; text-align: center; box-shadow: 0 8px 20px rgba(0,0,0,0.4); margin: auto; }
    .input-padrao { width: 100%; padding: 12px; margin: 8px 0; border: 1px solid #ccc; border-radius: 5px; font-size: 16px; }
    table { width: 100%; border-collapse: collapse; margin-top: 15px; }
    th, td { padding: 10px; border-bottom: 1px solid #eee; text-align: left; }
    
    .cupom-bg { background: #fff; color: #000; font-family: 'Courier New', Courier, monospace; height: auto; display: block; overflow: visible; padding: 20px; }
    .cupom { width: 300px; margin: 0 auto; font-size: 13px; text-transform: uppercase; }
    .cupom-head { text-align: center; border-bottom: 1px dashed #000; padding-bottom: 10px; margin-bottom: 10px; }
    .cupom-row { display: flex; justify-content: space-between; margin-bottom: 5px; }
    .cupom-divider { border-top: 1px dashed #000; margin: 10px 0; }
    .cupom-bold { font-weight: bold; font-size: 15px; }
    .no-print { display: block; width: 300px; margin: 20px auto; text-align: center; background: #d31a21; color: white; padding: 15px; text-decoration: none; font-weight: bold; font-family: sans-serif; border-radius: 5px; }
    @media print { .no-print { display: none !important; } body { background: white; } }
</style>
"""

MENU = {
    "CHOPP": [("Caneca 350ml", 11.9), ("Descartável 500ml", 13.9), ("Tulipa 700ml", 17.9), ("Torre 2.5L", 84.9), ("Torre 3.5L", 99.9)],
    "CERVEJAS": [("Original 600ml", 12.9), ("Amstel 600ml", 12.0), ("Brahma Duplo Malte", 12.0), ("Heineken 600ml", 16.9), ("Spaten LN", 8.9), ("Corona LN", 10.0), ("Heineken LN", 10.0), ("Stella LN", 8.9), ("Heineken Zero", 10.0)],
    "PETISCOS": [("Fritas", 21.9), ("Fritas c/ Queijo", 25.9), ("Fritas Cheddar/Bacon", 27.9), ("Kibe 10un", 34.9), ("Kibe c/ Queijo", 37.9), ("Frango Passarinho", 28.9), ("Carne Sol c/ Fritas", 54.9), ("Calabresa Acebolada", 22.9), ("Tábua Frios", 34.9)],
    "BEBIDAS": [("Caipirinha", 14.9), ("Caipiroska Absolut", 16.9), ("Gin Tônica", 24.9), ("Gin Tropical", 26.9), ("Cozumel 600ml", 14.9), ("Refri Lata", 4.9), ("Soda Italiana", 13.9), ("Suco Lata", 5.9), ("Red Bull", 13.0), ("Água", 3.9)]
}

@app.get("/", response_class=HTMLResponse)
async def login_page():
    return f"<html><head>{CSS}</head><body><div class='container-center'><div class='card-center'><img src='https://logodownload.org/wp-content/uploads/2014/07/brahma-logo-2.png' width='140'><h2>Acesso Restrito</h2><form action='/login' method='post'><input class='input-padrao' name='user' placeholder='Usuário' required><input class='input-padrao' name='pw' type='password' placeholder='Senha' required><button class='btn-acao' style='padding:15px; font-size:18px;'>ENTRAR</button></form></div></div></body></html>"

@app.post("/login")
async def login(request: Request, user: str = Form(...), pw: str = Form(...)):
    if (user == "admin" and pw == "1234") or (user == "garcom" and pw == "chopp"):
        request.session["user"] = user
        return RedirectResponse(url="/central", status_code=303)
    return RedirectResponse(url="/", status_code=303)

@app.get("/central", response_class=HTMLResponse)
async def central(request: Request):
    if "user" not in request.session: return RedirectResponse(url="/")
    return f"<html><head>{CSS}</head><body><div class='container-center'><div class='card-center'><img src='https://logodownload.org/wp-content/uploads/2014/07/brahma-logo-2.png' width='120'><br><br><a href='/cadastro' class='btn-acao' style='background:#d31a21'>➕ NOVO CADASTRO</a><a href='/buscar' class='btn-acao'>🔍 BUSCAR / ABRIR COMANDA</a><a href='/vendas' class='btn-acao' style='background:#28a745'>🛒 CAIXA / VENDAS</a><a href='/estoque' class='btn-acao' style='background:#e67e22'>📦 GESTÃO DE ESTOQUE</a><a href='/fechar_conta' class='btn-acao' style='background:#333'>🔒 FECHAR CONTA</a><br><a href='/logout' style='color:gray'>Sair</a></div></div></body></html>"

@app.get("/estoque", response_class=HTMLResponse)
async def tela_estoque(request: Request):
    if "user" not in request.session or request.session["user"] != "admin": return RedirectResponse(url="/central")
    with engine.connect() as conn:
        est = {r.item_nome: r.quantidade for r in conn.execute(text("SELECT item_nome, quantidade FROM estoque")).fetchall()}
    linhas = ""
    for cat, itens in MENU.items():
        linhas += f"<tr><td colspan='3' style='background:#082d5e; color:white; font-weight:bold;'>{cat}</td></tr>"
        for n, v in itens:
            qtd = est.get(n, 0)
            linhas += f"<tr><td style='color:black'>{n}</td><td style='color:black; font-weight:bold;'>{qtd}</td><td><form action='/att_estoque' method='post' style='display:flex;gap:5px;margin:0'><input type='hidden' name='i' value='{n}'><input type='number' name='q' class='input-padrao' style='width:70px;margin:0;padding:5px' required><button class='btn-acao' style='background:#28a745;margin:0;padding:8px'>ADD</button></form></td></tr>"
    return f"<html><head>{CSS}</head><body><div class='container-center'><div class='card-center'><h2>Gestão de Estoque</h2><div style='max-height:400px; overflow-y:auto;'><table><tr><th style='color:black'>Item</th><th style='color:black'>Qtd</th><th style='color:black'>Ação</th></tr>{linhas}</table></div><br><a href='/central' style='color:gray'>Voltar</a></div></div></body></html>"

@app.post("/att_estoque")
async def att_estoque(i: str = Form(...), q: int = Form(...)):
    with engine.begin() as conn: conn.execute(text("INSERT INTO estoque (item_nome, quantidade) VALUES (:i, :q) ON CONFLICT (item_nome) DO UPDATE SET quantidade = estoque.quantidade + :q"), {"i": i, "q": q})
    return RedirectResponse(url="/estoque", status_code=303)

@app.get("/vendas", response_class=HTMLResponse)
async def vendas(cat: str = "CHOPP", p: str = ""):
    prods = "".join([f"<div class='prod-card' onclick='add(\"{n}\", {v})'><b>{n}</b><span>R$ {v:.2f}</span></div>" for n, v in MENU.get(cat, [])])
    itens_html = ""
    if p:
        with engine.connect() as conn:
            query_itens = conn.execute(text("SELECT item_nome, COUNT(*) as qtd, SUM(valor) as tot FROM vendas_itens WHERE pulseira_num = :p AND status = 'ABERTA' GROUP BY item_nome"), {"p": p}).fetchall()
            for r in query_itens: itens_html += f"<div class='item-linha'><span>{r.qtd}x {r.item_nome}</span><span>R$ {float(r.tot):.2f}</span></div>"

    comanda_display = f"""
        <div class='comanda-header'>PULSEIRA: {p if p else 'NENHUMA'}</div>
        <div class='comanda-body'>
            <div class='secao-titulo'>Histórico de Consumo</div>
            {itens_html if p else "<div style='color:#999; text-align:center'>Defina a pulseira</div>"}
            <br>
            <div class='secao-titulo' style='color:#d31a21'>Novo Pedido</div>
            <div id='novo-pedido'></div>
        </div>
        <div class='comanda-footer'>
            <div style='display:flex; justify-content:space-between; font-size:18px; font-weight:bold; margin-bottom:10px;'><span>Subtotal Pedido:</span><span id='tot-pedido'>R$ 0.00</span></div>
            <button class='btn-acao' style='background:#28a745; font-size:16px;' onclick='enviarPedido()'>🖨️ FINALIZAR PEDIDO</button>
            <button class='btn-acao' onclick='setPulseira()'>Trocar Pulseira</button>
            <a href='/central' class='btn-acao' style='background:#333'>Voltar</a>
        </div>
    """

    return f"""<html><head>{CSS}
    <script>
        let cart = []; const p_num = new URLSearchParams(window.location.search).get("p");
        function add(n, v){{ if(!p_num) return alert("Defina a pulseira primeiro!"); cart.push({{n, v}}); render(); }}
        function render(){{
            let html = ""; let t = 0;
            cart.forEach((i, idx) => {{ html += `<div class='item-linha' style='color:#d31a21; font-weight:bold;'><span>${{i.n}}</span><span>R$ ${{i.v.toFixed(2)}} <b onclick='rem(${{idx}})' style='cursor:pointer; color:black;'>X</b></span></div>`; t += i.v; }});
            document.getElementById('novo-pedido').innerHTML = html; document.getElementById('tot-pedido').innerText = "R$ " + t.toFixed(2);
        }}
        function rem(idx) {{ cart.splice(idx, 1); render(); }}
        function enviarPedido() {{
            if(!p_num || cart.length === 0) return alert("Adicione itens ao pedido!");
            let f = document.createElement("form"); f.method = "POST"; f.action = "/lancar_pedido"; f.target = "_blank";
            let i1 = document.createElement("input"); i1.name = "p"; i1.value = p_num; f.appendChild(i1);
            let i2 = document.createElement("input"); i2.name = "itens"; i2.value = JSON.stringify(cart); f.appendChild(i2);
            document.body.appendChild(f); f.submit(); setTimeout(() => window.location.reload(), 1500);
        }}
        function setPulseira() {{ let num = prompt("Número da Pulseira ativa:"); if(num) window.location.href=`/vendas?cat={cat}&p=${{num}}`; }}
    </script>
    </head><body><div class='layout-vendas'>
        <div class='menu-lateral'>
            <a href='/vendas?cat=CHOPP&p={p}' class='btn-menu {"ativo" if cat=="CHOPP" else ""}'>🍺 CHOPP</a>
            <a href='/vendas?cat=CERVEJAS&p={p}' class='btn-menu {"ativo" if cat=="CERVEJAS" else ""}'>🍾 CERVEJAS</a>
            <a href='/vendas?cat=PETISCOS&p={p}' class='btn-menu {"ativo" if cat=="PETISCOS" else ""}'>🍟 PETISCOS</a>
            <a href='/vendas?cat=BEBIDAS&p={p}' class='btn-menu {"ativo" if cat=="BEBIDAS" else ""}'>🍹 BEBIDAS</a>
        </div>
        <div class='main-area'>
            <img src='https://logodownload.org/wp-content/uploads/2014/07/brahma-logo-2.png' class='logo-central'>
            <h2 style='margin-bottom:20px; font-size:24px;'>CARDÁPIO - {cat}</h2>
            <div class='grid-produtos'>{prods}</div>
        </div>
        <div class='comanda-lateral'>{comanda_display}</div>
    </div></body></html>"""

@app.post("/lancar_pedido", response_class=HTMLResponse)
async def lancar_pedido(p: str = Form(...), itens: str = Form(...)):
    lista = json.loads(itens)
    tot = sum(i['v'] for i in lista)
    linhas_cupom = ""
    with engine.begin() as conn:
        conn.execute(text("UPDATE pulseiras SET total_conta = total_conta + :t WHERE numero_pulseira = :p AND status = 'ABERTA'"), {"t": tot, "p": p})
        for i in lista:
            conn.execute(text("INSERT INTO vendas_itens (pulseira_num, item_nome, valor, status) VALUES (:p, :n, :v, 'ABERTA')"), {"p": p, "n": i['n'], "v": i['v']})
            conn.execute(text("INSERT INTO estoque (item_nome, quantidade) VALUES (:n, -1) ON CONFLICT (item_nome) DO UPDATE SET quantidade = estoque.quantidade - 1"), {"n": i['n']})
            linhas_cupom += f"<div class='cupom-row'><span>1x {i['n']}</span><span>{i['v']:.2f}</span></div>"
    
    return f"""<html class='cupom-bg'><body onload='window.print();'><div class='cupom'>
        <div class='cupom-head'><b>QUIOSQUE CHOPP BRAHMA</b><br>TICKET DE PREPARO<br><br>PULSEIRA: {p}</div>
        <div class='cupom-row cupom-bold'><span>Qtd Item</span><span>Valor</span></div><div class='cupom-divider'></div>
        {linhas_cupom}
        <div class='cupom-divider'></div><div class='cupom-row cupom-bold'><span>TOTAL PEDIDO</span><span>R$ {tot:.2f}</span></div>
        <div style='text-align:center; margin-top:15px;'>------------------------<br>VIA DO ESTABELECIMENTO</div>
    </div></body></html>"""

@app.get("/fechar_conta", response_class=HTMLResponse)
async def fechar_conta(q: str = ""):
    res = ""
    if q:
        q = q.strip()
        with engine.connect() as conn:
            query = conn.execute(text("SELECT p.numero_pulseira, p.total_conta, c.nome_completo FROM pulseiras p JOIN clientes c ON p.cliente_cpf = c.cpf WHERE (p.numero_pulseira = :q OR c.cpf = :q) AND p.status = 'ABERTA'"), {"q": q}).fetchone()
            if query:
                itens_q = conn.execute(text("SELECT item_nome, COUNT(*) as qtd, SUM(valor) as tot FROM vendas_itens WHERE pulseira_num = :p AND status = 'ABERTA' GROUP BY item_nome"), {"p": query.numero_pulseira}).fetchall()
                lista = "".join([f"<div class='item-linha'><span>{i.qtd}x {i.item_nome}</span><span>R$ {float(i.tot):.2f}</span></div>" for i in itens_q])
                lista += f"<div class='item-linha'><span>1x Couvert Artístico</span><span>R$ 7.00</span></div>"
                
                subtotal = float(query.total_conta or 0)
                taxa = subtotal * 0.10
                total_final = subtotal + taxa
                res = f"""<div style='background:#f4f4f4; padding:20px; border-radius:10px; color:#333; margin-top:20px; text-align:left;'>
                    <h3 style='text-align:center; margin-bottom:5px;'>{query.nome_completo}</h3>
                    <p style='text-align:center; margin-top:0; font-weight:bold'>Pulseira: {query.numero_pulseira}</p>
                    <div style='background:white; padding:15px; border-radius:8px; max-height:220px; overflow-y:auto; border:1px solid #ddd;'>{lista}</div>
                    <div style='padding-top:15px; font-size:16px;'>
                        <div class='item-linha'><span>Subtotal Consumo:</span><span>R$ {subtotal:.2f}</span></div>
                        <div class='item-linha'><span>Taxa Serviço (10%):</span><span>R$ {taxa:.2f}</span></div>
                        <div class='item-linha' style='font-weight:bold; font-size:20px; color:#d31a21'><span>TOTAL:</span><span>R$ {total_final:.2f}</span></div>
                        <div class='item-linha' style='margin-top:10px;'><span>Dividir por:</span><input type='number' id='divisores' value='1' min='1' style='width:60px; text-align:center; border:1px solid #ccc; border-radius:3px;' oninput='calcDiv()'></div>
                        <div class='item-linha' style='font-weight:bold; font-size:18px;'><span>Por Pessoa:</span><span id='val_pessoa'>R$ {total_final:.2f}</span></div>
                    </div>
                    <form action='/confirmar_fechamento' method='post' target='_blank' onsubmit='setTimeout(()=>window.location.href="/central", 1000)'>
                        <input type='hidden' name='p' value='{query.numero_pulseira}'>
                        <input type='hidden' name='divisao' id='input_div' value='1'>
                        <button class='btn-acao' style='background:#28a745; font-size:18px; margin-top:15px;'>🖨️ CONFIRMAR E IMPRIMIR RECIBO</button>
                    </form>
                    <script>
                        function calcDiv() {{
                            let div = parseInt(document.getElementById('divisores').value) || 1;
                            let tot = {total_final}; document.getElementById('val_pessoa').innerText = "R$ " + (tot / div).toFixed(2);
                            document.getElementById('input_div').value = div;
                        }}
                    </script>
                </div>"""
            else: res = "<p style='color:red;'>Nenhuma comanda aberta localizada para essa busca.</p>"
    return f"<html><head>{CSS}</head><body><div class='container-center'><div class='card-center'><img src='https://logodownload.org/wp-content/uploads/2014/07/brahma-logo-2.png' width='100'><br><h2>Fechar Conta</h2><form method='get'><input class='input-padrao' name='q' placeholder='CPF ou Nº Pulseira' value='{q}' required><button class='btn-acao'>CONSULTAR CONTA</button></form>{res}<br><a href='/central' style='color:gray'>Voltar</a></div></div></body></html>"

@app.post("/confirmar_fechamento", response_class=HTMLResponse)
async def confirmar_fechamento(p: str = Form(...), divisao: int = Form(1)):
    with engine.begin() as conn: 
        c_info = conn.execute(text("SELECT c.nome_completo, p.total_conta FROM pulseiras p JOIN clientes c ON p.cliente_cpf = c.cpf WHERE p.numero_pulseira = :p AND p.status = 'ABERTA'"), {"p": p}).fetchone()
        itens_q = conn.execute(text("SELECT item_nome, COUNT(*) as qtd, SUM(valor) as tot FROM vendas_itens WHERE pulseira_num = :p AND status = 'ABERTA' GROUP BY item_nome"), {"p": p}).fetchall()
        
        conn.execute(text("UPDATE pulseiras SET status = 'FECHADA' WHERE numero_pulseira = :p AND status = 'ABERTA'"), {"p": p})
        conn.execute(text("UPDATE vendas_itens SET status = 'FECHADA' WHERE pulseira_num = :p AND status = 'ABERTA'"), {"p": p})

    linhas_cupom = ""
    for i in itens_q: linhas_cupom += f"<div class='cupom-row'><span>{i.qtd}x {i.item_nome}</span><span>{float(i.tot):.2f}</span></div>"
    linhas_cupom += f"<div class='cupom-row'><span>1x Couvert Artístico</span><span>7.00</span></div>"
    
    subt = float(c_info.total_conta)
    taxa = subt * 0.10
    tot = subt + taxa
    val_div = tot / divisao

    return f"""<html class='cupom-bg'><body onload='window.print();'><div class='cupom'>
        <div class='cupom-head'><b>QUIOSQUE CHOPP BRAHMA</b><br>CONFERENCIA DE MESA<br>NÃO É DOCUMENTO FISCAL<br><br>Cliente: {c_info.nome_completo}<br>Pulseira: {p}</div>
        <div class='cupom-row cupom-bold'><span>Qtd Item</span><span>Valor</span></div><div class='cupom-divider'></div>
        {linhas_cupom}
        <div class='cupom-divider'></div>
        <div class='cupom-row'><span>SUBTOTAL PRODUTOS:</span><span>{subt:.2f}</span></div>
        <div class='cupom-row'><span>SERVICOS 10%:</span><span>{taxa:.2f}</span></div>
        <div class='cupom-divider'></div>
        <div class='cupom-row cupom-bold'><span>TOTAL:</span><span>{tot:.2f}</span></div>
        <div class='cupom-row' style='margin-top:10px;'><span>DIVIDIDO POR:</span><span>{divisao} PESSOA(S)</span></div>
        <div class='cupom-row cupom-bold'><span>VALOR POR PESSOA:</span><span>{val_div:.2f}</span></div>
        <div style='text-align:center; margin-top:20px;'>OBRIGADO E VOLTE SEMPRE!</div>
        <a href='/central' class='no-print'>VOLTAR AO SISTEMA</a>
    </div></body></html>"""

@app.get("/buscar", response_class=HTMLResponse)
async def tela_busca(q: str = ""):
    resultados = ""
    if q:
        with engine.connect() as conn:
            query = conn.execute(text("SELECT nome_completo, cpf, data_nascimento FROM clientes WHERE nome_completo ILIKE :q OR cpf LIKE :q"), {"q": f"%{q}%"}).fetchall()
            for r in query:
                is_bday = r.data_nascimento.strftime("%m-%d") == date.today().strftime("%m-%d") if r.data_nascimento else False
                resultados += f"<tr><td style='color:black'>{r.nome_completo}{' 🎁' if is_bday else ''}</td><td><form action='/abrir' method='post' style='display:flex;gap:5px'><input type='hidden' name='cpf' value='{r.cpf}'><input class='input-padrao' name='p' placeholder='Nº Pulseira' required style='width:100px;margin:0'><button class='btn-acao' style='background:#d31a21;padding:8px;margin:0'>ABRIR</button></form></td></tr>"
    return f"<html><head>{CSS}</head><body><div class='container-center'><div class='card-center'><img src='https://logodownload.org/wp-content/uploads/2014/07/brahma-logo-2.png' width='100'><br><h2>Buscar Cliente</h2><form method='get'><input class='input-padrao' name='q' placeholder='Nome ou CPF' value='{q}'><button class='btn-acao'>PESQUISAR</button></form><table>{resultados}</table><br><a href='/central'>Voltar</a></div></div></body></html>"

@app.post("/abrir")
async def abrir(cpf: str = Form(...), p: str = Form(...)):
    cpf, p = cpf.strip(), p.strip()
    with engine.begin() as conn:
        chk_cpf = conn.execute(text("SELECT numero_pulseira FROM pulseiras WHERE cliente_cpf = :c AND status = 'ABERTA'"), {"c": cpf}).fetchone()
        if chk_cpf: return HTMLResponse(f"<script>alert('❌ Cliente já possui a comanda {chk_cpf[0]} aberta!'); window.history.back();</script>")
        chk_p = conn.execute(text("SELECT cliente_cpf FROM pulseiras WHERE numero_pulseira = :p AND status = 'ABERTA'"), {"p": p}).fetchone()
        if chk_p: return HTMLResponse(f"<script>alert('❌ A pulseira {p} já está em uso!'); window.history.back();</script>")
        conn.execute(text("INSERT INTO pulseiras (numero_pulseira, cliente_cpf, total_conta, status) VALUES (:p, :c, 7.00, 'ABERTA')"), {"p": p, "c": cpf})
    return RedirectResponse(url=f"/vendas?p={p}", status_code=303)

@app.get("/cadastro", response_class=HTMLResponse)
async def tela_cadastro():
    return f"<html><head>{CSS}</head><body><div class='container-center'><div class='card-center'><img src='https://logodownload.org/wp-content/uploads/2014/07/brahma-logo-2.png' width='100'><br><h2>Novo Cliente</h2><form action='/salvar' method='post'><input class='input-padrao' name='nome' placeholder='Nome Completo' required><input class='input-padrao' name='cpf' placeholder='CPF' required><input class='input-padrao' name='nasc' type='date' required><input class='input-padrao' name='contato' placeholder='WhatsApp' required><input class='input-padrao' name='email' type='email' placeholder='E-mail (Opcional)'><input class='input-padrao' name='pulseira' placeholder='Nº Pulseira' required><button class='btn-acao' style='background:#d31a21'>SALVAR E ABRIR</button></form><br><a href='/central'>Voltar</a></div></div></body></html>"

@app.post("/salvar")
async def salvar(nome: str = Form(...), cpf: str = Form(...), nasc: str = Form(...), contato: str = Form(...), email: str = Form(None), pulseira: str = Form(...)):
    cpf, pulseira = cpf.strip(), pulseira.strip()
    with engine.begin() as conn:
        conn.execute(text("INSERT INTO clientes (nome_completo, cpf, data_nascimento, contato, email) VALUES (:n, :c, :d, :co, :e) ON CONFLICT (cpf) DO NOTHING"), {"n":nome, "c":cpf, "d":nasc, "co":contato, "e":email})
        chk_cpf = conn.execute(text("SELECT numero_pulseira FROM pulseiras WHERE cliente_cpf = :c AND status = 'ABERTA'"), {"c": cpf}).fetchone()
        if chk_cpf: return HTMLResponse(f"<script>alert('❌ Cliente já possui a comanda {chk_cpf[0]} aberta!'); window.history.back();</script>")
        chk_p = conn.execute(text("SELECT cliente_cpf FROM pulseiras WHERE numero_pulseira = :p AND status = 'ABERTA'"), {"p": pulseira}).fetchone()
        if chk_p: return HTMLResponse(f"<script>alert('❌ A pulseira {pulseira} já está em uso!'); window.history.back();</script>")
        conn.execute(text("INSERT INTO pulseiras (numero_pulseira, cliente_cpf, total_conta, status) VALUES (:p, :c, 7.00, 'ABERTA')"), {"p":pulseira, "c":cpf})
    return RedirectResponse(url=f"/vendas?p={pulseira}", status_code=303)

@app.get("/logout")
async def logout(request: Request):
    request.session.clear()
    return RedirectResponse(url="/")
