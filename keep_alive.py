from flask import Flask
from threading import Thread
import os

app = Flask("")

@app.route("/")
def home():
    return "Estou vivo!"

def run():
  # Obtém a porta da variável de ambiente PORT, ou usa 8080 como padrão
  port = int(os.environ.get("PORT", 8080))
  # Escuta em 0.0.0.0 para ser acessível externamente
  app.run(host="0.0.0.0", port=port)

def keep_alive():
    print("--- Iniciando servidor Keep Alive ---")
    t = Thread(target=run)
    t.start()
    print("--- Servidor Keep Alive rodando em background ---")
