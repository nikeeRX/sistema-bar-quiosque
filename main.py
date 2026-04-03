from fastapi import FastAPI, Form, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlalchemy import create_engine, text
from starlette.middleware.sessions import SessionMiddleware
from datetime import date, datetime

app = FastAPI()
app.add_middleware(SessionMiddleware, secret_key="brahma_riacho_secret")

# --- CONEXÃO OFICIAL ---
DATABASE_URL = "postgresql://postgres:GNlZnHiuKAcFnpgXhwILfigqKCNkaHqx@interchange.proxy.rlwy.net:44559/railway"
engine = create_engine(DATABASE_URL, pool_pre_ping=True)

# --- CRIAÇÃO DA ESTRUTURA DE GESTÃO ---
with engine.begin() as conn:
    # Tabela para salvar o histórico de cada item vendido (O CORAÇÃO DA GESTÃO)
    conn.execute(text("""
        CREATE TABLE IF NOT EXISTS vendas_dia (
            id SERIAL PRIMARY KEY,
            numero_pulseira TEXT,
            item_nome TEXT,
            valor_item DECIMAL(10,2),
            categoria TEXT,
            data_venda DATE DEFAULT CURRENT_DATE,
            hora_venda TIME DEFAULT CURRENT_TIME
        );
    """))

CSS = """
<style>
    :root { --azul: #004795; --vermelho: #e21c21; --gelo: #f4f4f4; }
    * { box-sizing: border-box; }
    body { font-family: 'Segoe UI', Arial; background: var(--azul); margin: 0; color: white; min-height: 100vh; display: flex; flex-direction: column; }
    .main-container { flex: 1; display: flex; align-items: center; justify-content: center; padding: 20px; width: 100%; }
    .card { background: white; color: #333; padding: 25px; border-radius: 15px; box-shadow: 0 10px 25px rgba(0,0,0,0.3); width: 100%; max-width: 900px; text-align: center; }
    .btn { display: block; width: 100%; padding: 15px; margin: 10px 0; border: none; border-radius: 8px; font-weight: bold; cursor: pointer; text-decoration: none; font-size: 16px; transition: 0.2s; text-align: center; }
    .btn-azul { background: var(--azul); color: white; }
    .btn-vermelho { background: var(--vermelho); color: white; }
    .b-vendas { display: grid; grid-template-columns: repeat(auto-fill, minmax(160px, 1fr)); gap: 12px; margin-top: 15px; }
    .prod-card { background: #fff; border: 2px solid #ddd; padding: 15px; border-radius: 12px; cursor: pointer; color: #333; transition: 0.2s; }
    .prod-card:hover { border-color: var(--vermelho); background: #fff9f9; transform: translateY(-3px); }
    .prod-card b { display: block; margin-bottom: 5px; font-size: 14px; }
    .prod-card span { color: var(--vermelho); font-weight: bold; font-size: 16px; }
    .nav-tabs { display: flex; gap: 10px; margin-bottom: 20px; flex-wrap: wrap; }
</style>
"""

@app.get("/vendas", response_class=HTMLResponse)
async def tela_vendas(cat: str = "Chopps"):
    # Cardápio atualizado conforme a foto e os dados do banco
    menu = {
        "Chopps": [("Caneca 350ml", 11.90), ("Tulipa 700ml", 17.90), ("Torre 2.5L", 84.90)],
        "Cervejas": [("Antarctica Original 600ml", 12.90), ("Spaten LN", 8.90), ("Heineken 600ml", 16.90)],
        "Petiscos": [("Batata Frita", 21.90), ("Frango Passarinho", 28.90), ("Carne de Sol c/ Fritas", 54.90)],
        "Doses/Drinks": [("Caipirinha Limão", 14.90), ("Whisky Jack Daniels", 17.90), ("Red Bull", 13.00)]
    }
    
    prod_html = "".join([
        f"<div class='prod-card' onclick='vender(\"{n}\", {p}, \"{cat}\")'><b>{n}</b><span>R$ {p:.2f}</span></div>" 
        for n, p in menu.get(cat, [])
    ])

    return f"""<html><head>{CSS}
    <script>
        function vender(nome, valor, categoria) {{
            let p = prompt("🛒 Lançar " + nome + "\\n\\nDigite o Nº da Pulseira:");
            if(p) {{
                window.location.href = `/registrar-venda?p=${{p}}&v=${{valor}}&i=${{nome}}&c=${{categoria}}`;
            }}
        }}
    </script>
    </head><body>
    <div class='main-container'>
        <div class='card'>
            <img src='https://logodownload.org/wp-content/uploads/2014/07/brahma-logo-2.png' width='100' style='margin-bottom:10px;'>
            <div class='nav-tabs'>
                <a href='/vendas?cat=Chopps' class='btn btn-azul' style='flex:1'>🍺 CHOPPS</a>
                <a href='/vendas?cat=Cervejas' class='btn btn-azul' style='flex:1'>🍾 CERVEJAS</a>
                <a href='/vendas?cat=Petiscos' class='btn btn-azul' style='flex:1'>🍟 PETISCOS</a>
                <a href='/vendas?cat=Doses/Drinks' class='btn btn-azul' style='flex:1'>🍹 DRINKS</a>
            </div>
            <div class='b-vendas'>{prod_html}</div>
            <br><a href='/central' class='btn btn-vermelho' style='max-width:200px; margin: 20px auto 0;'>VOLTAR À CENTRAL</a>
        </div>
    </div>
    </body></html>"""

@app.get("/registrar-venda")
async def registrar_venda(p: str, v: float, i: str, c: str):
    with engine.begin() as conn:
        # 1. Atualiza o total na comanda do cliente
        conn.execute(text("UPDATE pulseiras SET total_conta = total_conta + :v WHERE numero_pulseira = :p"), {"v": v, "p": p})
        
        # 2. Salva o registro detalhado para a GESTÃO FINANCEIRA
        conn.execute(text("""
            INSERT INTO vendas_dia (numero_pulseira, item_nome, valor_item, categoria) 
            VALUES (:p, :i, :v, :c)
        """), {"p": p, "i": i, "v": v, "c": c})
        
    return HTMLResponse(f"<script>alert('✅ {i} lançado na pulseira {p}!'); window.location.href='/vendas?cat={c}';</script>")
