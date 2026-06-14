from http.server import BaseHTTPRequestHandler, HTTPServer
import json
from urllib.parse import urlparse


products = [
    {"id": 1, "name": "Pancakes", "price": 500},
    {"id": 2, "name": "Cakes", "price": 1500},
    {"id": 3, "name": "Donuts", "price": 700},
]


class RequestHandler(BaseHTTPRequestHandler):
    def send_json(self, data, status=200):
        response = json.dumps(data).encode("utf-8")

        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(response)))
        self.end_headers()
        self.wfile.write(response)

    def read_json_body(self):
        content_length = int(self.headers.get("Content-Length", 0))

        if content_length == 0:
            return None

        raw_body = self.rfile.read(content_length)
        return json.loads(raw_body)

    def do_GET(self):
        path = urlparse(self.path).path

        if path == "/":
            self.send_json(
                {
                    "message": "Welcome to Decode Labs Backend Project 1",
                    "routes": ["GET /api/products", "GET /api/products/<id>", "POST /api/products"],
                }
            )
            return

        if path == "/api/products":
            self.send_json({"products": products})
            return

        if path.startswith("/api/products/"):
            product_id_text = path.split("/")[-1]

            if not product_id_text.isdigit():
                self.send_json({"error": "Product id must be a number"}, 400)
                return

            product_id = int(product_id_text)
            product = next(
                (item for item in products if item["id"] == product_id), None)

            if product is None:
                self.send_json({"error": "Product not found"}, 404)
                return

            self.send_json({"product": product})
            return

        self.send_json({"error": "Route not found"}, 404)

    def do_POST(self):
        path = urlparse(self.path).path

        if path != "/api/products":
            self.send_json({"error": "Route not found"}, 404)
            return

        try:
            body = self.read_json_body()
        except json.JSONDecodeError:
            self.send_json({"error": "Invalid JSON body"}, 400)
            return

        if not body or "name" not in body or "price" not in body:
            self.send_json({"error": "Product must have name and price"}, 400)
            return

        new_product = {
            "id": products[-1]["id"] + 1 if products else 1,
            "name": body["name"],
            "price": body["price"],
        }
        products.append(new_product)

        self.send_json(
            {
                "message": "Product created successfully",
                "product": new_product,
            },
            201,
        )


def run_server():
    server_address = ("localhost", 8000)
    server = HTTPServer(server_address, RequestHandler)
    print("Server running at http://localhost:8000")
    server.serve_forever()


if __name__ == "__main__":
    run_server()
