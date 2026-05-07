from flask import Flask, render_template, request, jsonify, redirect
import mercadopago
import uuid
import os

app = Flask(__name__)

# ---------------- MERCADO PAGO ----------------

ACCESS_TOKEN = os.getenv("MERCADO_PAGO_TOKEN")

sdk = mercadopago.SDK(ACCESS_TOKEN)

# banco simples em memória (pode trocar depois por banco real)
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

    pagamentos[user_id] = {
        "produto": produto,
        "pago": False
    }

    return render_template(
        "checkout.html",
        produto=produto,
        email=email,
        user_id=user_id
    )

# ---------------- PIX PAYMENT ----------------

@app.route("/process_payment", methods=["POST"])
def process_payment():

    data = request.json

    try:

        payment_data = {
            "transaction_amount": float(data.get("transaction_amount", 45)),
            "description": "Acesso VIP",
            "payment_method_id": "pix",
            "payer": {
                "email": data["payer"]["email"]
            }
        }

        payment = sdk.payment().create(payment_data)
        response = payment["response"]

        pix = response.get("point_of_interaction", {}).get("transaction_data", {})

        return jsonify({
            "payment_id": response.get("id"),
            "status": response.get("status"),
            "qr_code": pix.get("qr_code"),
            "qr_base64": pix.get("qr_code_base64"),
            "ticket_url": pix.get("ticket_url")
        })

    except Exception as e:
        print("Erro PIX:", e)
        return jsonify({"error": str(e)}), 500

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

    if not user["pago"]:
        return "Pagamento ainda não aprovado"

    if user["produto"] == "vip":
        return "<h1>🔓 Grupo VIP liberado</h1>"

    elif user["produto"] == "live":
        return "<h1>🔓 Live liberada</h1>"

    else:
        return "<h1>🔓 Acesso liberado</h1>"

# ---------------- WEBHOOK (CONFIRMAÇÃO PIX) ----------------

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
