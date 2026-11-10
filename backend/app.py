
from flask import Flask, jsonify
from flask_cors import CORS

from routes.dashboard_routes import dashboard_bp
from routes.fulfillment_routes import fulfillment_bp


app = Flask(__name__)

CORS(app)

app.register_blueprint(
    dashboard_bp,
    url_prefix="/api"
)

app.register_blueprint(
    fulfillment_bp,
    url_prefix="/api"
)


@app.route("/")
def home():
    return jsonify({
        "success": True,
        "message": "Order Fulfillment Management System API is running!"
    })


@app.route("/health")
def health():
    return jsonify({
        "success": True,
        "message": "Backend is healthy"
    })


if __name__ == "__main__":
    app.run(
        host="127.0.0.1",
        port=5000,
        debug=True
    )
