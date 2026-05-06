from flask import Flask, render_template, request, jsonify
import mercadopago
import uuid
import os

app = Flask(__name__)

# ---------------- CONFIG MERCADO PAGO ----------------
ACCESS_TOKEN = os.getenv("MERCADO_PAGO_TOKEN")
sdk = mercadopago.SDK(ACCESS_TOKEN)

pagamentos = {}

# ---------------- HOME ----------------
@app.route("/")
def home():
    return render_template("index.html")

# ---------------- CHECKOUT ----------------
@app.route("/checkout", methods=["GET", "POST"])
def checkout():
    if request.method == "POST":
        produto = request.form.get("produto")
        email = request.form.get("email")

        if not email:
            return "Digite um email válido"

        user_id = str(uuid.uuid4())

        valor = 29,99  # valor fixo

        payment_data = {
            "transaction_amount": float(valor),
            "payment_method_id": "pix",
            "external_reference": user_id,
            "notification_url": "https://SEU-SITE.onrender.com/webhook",
            "payer": {
                "email": email
            },
            "description": f"Compra do produto {produto}"
        }

        payment = sdk.payment().create(payment_data)
        response = payment.get("response", {})

        qr = response.get("point_of_interaction", {}).get("transaction_data", {}).get("qr_code_base64")
        code = response.get("point_of_interaction", {}).get("transaction_data", {}).get("qr_code")

        if not qr or not code:
            return "Erro ao gerar pagamento. Verifique o token do Mercado Pago."

        pagamentos[user_id] = {
            "produto": produto,
            "pago": False,
            "payment_id": response.get("id")
        }

        return render_template("pagar.html", qr=qr, code=code, user_id=user_id)

    produto = request.args.get("produto")
    return render_template("checkout.html", produto=produto)

# ---------------- STATUS ----------------
@app.route("/status/<user_id>")
def status(user_id):
    pago = pagamentos.get(user_id, {}).get("pago", False)
    return jsonify({"pago": pago})

# ---------------- ACESSO ----------------
@app.route("/acesso/<user_id>")
def acesso(user_id):
    user = pagamentos.get(user_id)

    if not user or not user["pago"]:
        return "Acesso negado"

    if user["produto"] == "vip":
        return "<h1>🔓 Link Telegram VIP</h1>"
    elif user["produto"] == "live":
        return "<h1>🔓 Link da Live</h1>"
    else:
        return "<h1>🔓 Link OnlyFans</h1>"

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
