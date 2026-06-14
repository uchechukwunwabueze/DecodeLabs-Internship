# DecodeLabs Backend Development Project 1

## REST API Fundamentals

This is my first backend development project for the DecodeLabs internship. The goal of the project is to create a simple stateless web server that can return data using API routes.

The project uses Python and returns product data in JSON format.

## Features

- Runs a local server
- Has a home route
- Has a route to get all productsq 
- Has a route to get one product by ID
- Has a POST route to add a new product
- Returns JSON responses
- Handles basic errors like invalid routes or missing products

## Tech Used

- Python
- HTTP Server
- JSON

## How To Run The Project

Open the project folder in a terminal and run:

```bash
python server.py
```

If that does not work, try:

```bash
py server.py
```

The server should start at:

```text
http://localhost:8000
```

## API Routes

### 1. Home Route

```http
GET /
```

This returns a welcome message and shows the available routes.

### 2. Get All Products

```http
GET /api/products
```

Example response:

```json
{
  "products": [
    {
      "id": 1,
      "name": "Pancakes",
      "price": 500
    },
    {
      "id": 2,
      "name": "Cakes",
      "price": 1500
    },
    {
      "id": 3,
      "name": "Donuts",
      "price": 700
    }
  ]
}
```

### 3. Get One Product

```http
GET /api/products/1
```

Example response:

```json
{
  "product": {
    "id": 1,
    "name": "Pancakes",
    "price": 500
  }
}
```

### 4. Add A New Product

```http
POST /api/products
```

Example request body:

```json
{
  "name": "Brownies",
  "price": 1000
}
```

Example response:

```json
{
  "message": "Product created successfully",
  "product": {
    "id": 4,
    "name": "Brownies",
    "price": 1000
  }
}
```

## What I Learned

From this project, I learned the basics of how a backend server works. I learned how to create routes, return JSON data, handle GET and POST requests, and send simple error responses.