from fastapi import FastAPI, Request
from telegram import Update, Bot, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    ApplicationBuilder, CommandHandler, CallbackQueryHandler, ContextTypes
)
import os
import json

app = FastAPI()

TOKEN = os.getenv("TELEGRAM_TOKEN")
if not TOKEN:
    raise ValueError("A variável de ambiente TELEGRAM_TOKEN não está definida.")

bot = Bot(token=TOKEN)
application = ApplicationBuilder().token(TOKEN).build()

ARQUIVO_DADOS = "dados.json"

saldo_total = 0
entradas = {}
saidas = {}
dividas = {}

def salvar_dados():
    dados = {
        "saldo_total": saldo_total,
        "entradas": entradas,
        "saidas": saidas,
        "dividas": dividas
    }
    with open(ARQUIVO_DADOS, "w") as f:
        json.dump(dados, f)

def carregar_dados():
    global saldo_total, entradas, saidas, dividas
    try:
        with open(ARQUIVO_DADOS, "r") as f:
            dados = json.load(f)
            saldo_total = dados.get("saldo_total", 0)
            entradas = dados.get("entradas", {})
            saidas = dados.get("saidas", {})
            dividas = dados.get("dividas", {})
    except FileNotFoundError:
        pass

carregar_dados()

# =================== Comandos ===================

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await mostrar_menu(update)

async def mostrar_menu(update: Update):
    keyboard = [
        [InlineKeyboardButton("📊 Saldo", callback_data='saldo')],
        [InlineKeyboardButton("➕ Entrada", callback_data='entrada')],
        [InlineKeyboardButton("➖ Saída", callback_data='saida')],
        [InlineKeyboardButton("💸 Adicionar Dívida", callback_data='divida_add')],
        [InlineKeyboardButton("📋 Ver Dívidas", callback_data='divida_list')],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    if update.message:
        await update.message.reply_text("📱 Escolha uma opção:", reply_markup=reply_markup)
    elif update.callback_query:
        await update.callback_query.edit_message_text("📱 Escolha uma opção:", reply_markup=reply_markup)

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    if query.data == 'saldo':
        await query.message.reply_text(f"💰 Saldo atual: R$ {saldo_total:.2f}")

    elif query.data == 'entrada':
        await query.message.reply_text("Digite: /entrada nome valor")

    elif query.data == 'saida':
        await query.message.reply_text("Digite: /saida nome valor")

    elif query.data == 'divida_add':
        await query.message.reply_text("Digite: /divida_add nome valor")

    elif query.data == 'divida_list':
        if dividas:
            texto = "📋 Dívidas cadastradas:\n"
            for nome, val in dividas.items():
                texto += f"- {nome}: R$ {val:.2f}\n"
            await query.message.reply_text(texto)
        else:
            await query.message.reply_text("✅ Nenhuma dívida cadastrada.")

async def saldo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(f"Saldo total: R$ {saldo_total:.2f}")

async def entrada(update: Update, context: ContextTypes.DEFAULT_TYPE):
    global saldo_total
    args = context.args
    if len(args) < 2:
        await update.message.reply_text("Use: /entrada nome valor")
        return
    nome = args[0]
    try:
        valor = float(args[1].replace(",", "."))
    except:
        await update.message.reply_text("Valor inválido! Use ponto ou vírgula como decimal.")
        return
    entradas[nome] = entradas.get(nome, 0) + valor
    saldo_total += valor
    salvar_dados()
    await update.message.reply_text(f"✅ Entrada '{nome}' adicionada com R$ {valor:.2f}")

async def saida(update: Update, context: ContextTypes.DEFAULT_TYPE):
    global saldo_total
    args = context.args
    if len(args) < 2:
        await update.message.reply_text("Use: /saida nome valor")
        return
    nome = args[0]
    try:
        valor = float(args[1].replace(",", "."))
    except:
        await update.message.reply_text("Valor inválido!")
        return
    saidas[nome] = saidas.get(nome, 0) + valor
    saldo_total -= valor
    salvar_dados()
    await update.message.reply_text(f"🔻 Saída '{nome}' registrada com R$ {valor:.2f}")

async def divida_add(update: Update, context: ContextTypes.DEFAULT_TYPE):
    args = context.args
    if len(args) < 2:
        await update.message.reply_text("Use: /divida_add nome valor")
        return
    nome = args[0]
    try:
        valor = float(args[1].replace(",", "."))
    except:
        await update.message.reply_text("Valor inválido!")
        return
    dividas[nome] = dividas.get(nome, 0) + valor
    salvar_dados()
    await update.message.reply_text(f"❗ Dívida '{nome}' adicionada com R$ {valor:.2f}")

async def divida_list(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if dividas:
        texto = "📋 Dívidas cadastradas:\n"
        for nome, val in dividas.items():
            texto += f"- {nome}: R$ {val:.2f}\n"
        await update.message.reply_text(texto)
    else:
        await update.message.reply_text("✅ Nenhuma dívida cadastrada.")

async def divida_remove(update: Update, context: ContextTypes.DEFAULT_TYPE):
    args = context.args
    if len(args) < 1:
        await update.message.reply_text("Use: /divida_remove nome")
        return
    nome = args[0]
    if nome in dividas:
        del dividas[nome]
        salvar_dados()
        await update.message.reply_text(f"Dívida '{nome}' removida com sucesso.")
    else:
        await update.message.reply_text("Dívida não encontrada.")

# =================== Handlers ===================

application.add_handler(CommandHandler("start", start))
application.add_handler(CommandHandler("menu", mostrar_menu))
application.add_handler(CommandHandler("saldo", saldo))
application.add_handler(CommandHandler("entrada", entrada))
application.add_handler(CommandHandler("saida", saida))
application.add_handler(CommandHandler("divida_add", divida_add))
application.add_handler(CommandHandler("divida_list", divida_list))
application.add_handler(CommandHandler("divida_remove", divida_remove))
application.add_handler(CallbackQueryHandler(button_handler))

# ============ Eventos FastAPI para iniciar e parar bot ============

@app.on_event("startup")
async def on_startup():
    await bot.initialize()
    await application.initialize()

@app.on_event("shutdown")
async def on_shutdown():
    await application.shutdown()
    await bot.shutdown()

# =================== Webhook ===================

@app.post("/webhook")
async def webhook(request: Request):
    data = await request.json()
    update = Update.de_json(data, bot)
    await application.process_update(update)
    return {"ok": True}

# =================== Rodar localmente ===================

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=10000)
