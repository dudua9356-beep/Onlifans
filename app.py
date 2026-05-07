from flask import Flask, render_template, request, jsonify, redirect
import mercadopago
import uuid
import os

app = Flask(__name__)

# ---------------- MERCADO PAGO ----------------

ACCESS_TOKEN = os.getenv("MERCADO_PAGO_TOKEN")

sdk = mercadopago.SDK(ACCESS_TOKEN)

pagamentos = {}

# ---------------- HOME ----------------

@app.route("/", methods=["GET", "POST"])
def home():

    if request.method == "POST":

        produto = request.form.get("produto")
        email = request.form.get("email")

        if not email:
            return "Digite um email válido"

        return redirect(f"/checkout?produto={produto}&email={email}")

    return render_template("index.html")

# ---------------- CHECKOUT ----------------

@app.route("/checkout")
def checkout():

    produto = request.args.get("produto")
    email = request.args.get("email")

    if not produto or not email:
        return redirect("/")

    user_id = str(uuid.uuid4())

    valor = 45

    preference_data = {

        "items": [
            {
                "title": f"Acesso {produto}",
                "quantity": 1,
                "currency_id": "BRL",
                "unit_price": float(valor)
            }
        ],

        "payer": {
            "email": email
        },

        "payment_methods": {
            "excluded_payment_types": []
        },

        "external_reference": user_id,

        "notification_url": "https://onlifans.onrender.com/webhook",

        "back_urls": {
            "success": f"https://onlifans.onrender.com/acesso/{user_id}",
            "failure": "https://onlifans.onrender.com",
            "pending": "https://onlifans.onrender.com"
        }
    }

    preference = sdk.preference().create(preference_data)

    link_pagamento = preference["response"]["init_point"]

    pagamentos[user_id] = {
        "produto": produto,
        "pago": False
    }

    return redirect(link_pagamento)

# ---------------- STATUS ----------------

@app.route("/status/<user_id>")
def status(user_id):

    pago = pagamentos.get(user_id, {}).get("pago", False)

    return jsonify({
        "pago": pago
    })

# ---------------- ACESSO ----------------

@app.route("/acesso/<user_id>")
def acesso(user_id):

    user = pagamentos.get(user_id)

    if not user:
        return "Acesso inválido"

    if user["produto"] == "vip":
        return "<h1>🔓 Grupo VIP liberado</h1>"

    elif user["produto"] == "live":
        return "<h1>🔓 Live liberada</h1>"

    else:
        return "<h1>🔓 OnlyFans Premium liberado</h1>"

# ---------------- WEBHOOK ----------------

@app.route("/webhook", methods=["POST"])
def webhook():

    data = request.json

    try:

        if data and data.get("type") == "payment":

            payment_id = data["data"]["id"]

            payment = sdk.payment().get(payment_id)

            payment_info = payment.get("response", {})

            if payment_info.get("status") == "approved":

                user_id = payment_info.get("external_reference")

                if user_id in pagamentos:
                    pagamentos[user_id]["pago"] = True

    except Exception as e:
        print("Erro webhook:", e)

    return "ok"

# ---------------- START ----------------

if __name__ == "__main__":
    app.run(debug=True)
