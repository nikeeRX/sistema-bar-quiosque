from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from datetime import date
from typing import List, Optional
import sqlalchemy
from sqlalchemy import create_engine, text

# --- 1. CONEXÃO COM O TANQUE (BANCO DE DADOS) ---
# COLE O SEU LINK DA URI AQUI EMBAIXO
DATABASE_URL = "postgresql://postgres:Somdeboas2026@db.zykgsosahlavullteema.supabase.co:5432/postgres"

engine = create_engine(DATABASE_URL)
app = FastAPI(title="Motor do Bar do Mano")

# --- 2. MODELOS (O que o motor entende) ---
class ClienteSchema(BaseModel):
    nome: str
    telefone: str
    data_nascimento: date

class PedidoSchema(BaseModel):
    id_cartao: int
    id_produto: int
    quantidade: int

# --- 3. ROTAS (O que o motor faz) ---

@app.get("/")
def inicio():
    return {"status": "Motor Rodando!", "msg": "Sistema do Bar do Mano Online"}

# ROTA: Fazer Check-in (Ativar Cartão)
@app.post("/checkin/{id_cartao}/{id_mesa}")
def checkin(id_cartao: int, id_mesa: int, cliente: ClienteSchema):
    with engine.connect() as conn:
        # Cadastra o cliente e abre a comanda
        query_cliente = text("INSERT INTO clientes (nome, telefone, data_nascimento) VALUES (:n, :t, :d) RETURNING id")
        res = conn.execute(query_cliente, {"n": cliente.nome, "t": cliente.telefone, "d": cliente.data_nascimento})
        cliente_id = res.fetchone()[0]
        
        query_comanda = text("INSERT INTO comandas (id_cartao, id_mesa, id_cliente) VALUES (:c, :m, :id_c)")
        conn.execute(query_comanda, {"c": id_cartao, "m": id_mesa, "id_c": cliente_id})
        conn.commit()
    return {"msg": f"Cartão {id_cartao} ativo na Mesa {id_mesa}"}

# ROTA: Lançar Pedido (Cerveja, Jantinha, etc)
@app.post("/lancar-pedido")
def lancar(pedido: PedidoSchema):
    with engine.connect() as conn:
        # 1. Tira do estoque
        query_baixa = text("UPDATE produtos SET estoque_atual = estoque_atual - :q WHERE id = :p")
        conn.execute(query_baixa, {"q": pedido.quantidade, "p": pedido.id_produto})
        
        # 2. Registra na conta do cartão
        query_pedido = text("INSERT INTO pedidos (id_cartao, id_produto, quantidade) VALUES (:c, :p, :q)")
        conn.execute(query_pedido, {"c": pedido.id_cartao, "p": pedido.id_produto, "q": pedido.quantidade})
        
        conn.commit()
    return {"status": "Sucesso", "msg": "Pedido registrado e estoque atualizado!"}

# ROTA: Ver Aniversariantes do Dia
@app.get("/aniversariantes")
def niver():
    with engine.connect() as conn:
        query = text("SELECT nome, telefone FROM clientes WHERE EXTRACT(DAY FROM data_nascimento) = EXTRACT(DAY FROM CURRENT_DATE) AND EXTRACT(MONTH FROM data_nascimento) = EXTRACT(MONTH FROM CURRENT_DATE)")
        res = conn.execute(query).fetchall()
        # Transforma em lista fácil de ler
        lista = [{"nome": r[0], "telefone": r[1]} for r in res]
    return lista
