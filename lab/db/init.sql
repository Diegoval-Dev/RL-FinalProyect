CREATE TABLE products (
    id          serial PRIMARY KEY,
    name        text NOT NULL,
    description text NOT NULL,
    price       numeric(10, 2) NOT NULL,
    category    text NOT NULL,
    hidden      boolean NOT NULL DEFAULT false
);

CREATE TABLE users (
    id       serial PRIMARY KEY,
    username text NOT NULL UNIQUE,
    password text NOT NULL,
    role     text NOT NULL
);

CREATE TABLE orders (
    id      serial PRIMARY KEY,
    user_id integer NOT NULL REFERENCES users (id),
    total   numeric(10, 2) NOT NULL,
    status  text NOT NULL
);

CREATE TABLE comments (
    id         serial PRIMARY KEY,
    product_id integer NOT NULL REFERENCES products (id),
    author     text NOT NULL,
    body       text NOT NULL,
    created_at timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE cart_items (
    id         serial PRIMARY KEY,
    user_id    integer NOT NULL REFERENCES users (id),
    product_id integer NOT NULL REFERENCES products (id),
    qty        integer NOT NULL
);

INSERT INTO products (name, description, price, category) VALUES
    ('Laptop Aurora 14', 'Portátil ligero de 14 pulgadas con 16 GB de memoria', 8999.00, 'Electrónica'),
    ('Audífonos Bluetooth Nova', 'Audífonos inalámbricos con cancelación de ruido', 749.00, 'Electrónica'),
    ('Teclado mecánico Quetzal', 'Teclado mecánico en español con retroiluminación', 1299.00, 'Electrónica'),
    ('Lámpara de escritorio Sol', 'Lámpara LED regulable para escritorio', 349.50, 'Hogar'),
    ('Cafetera de goteo Antigua', 'Cafetera de goteo para doce tazas', 899.00, 'Hogar'),
    ('Juego de sartenes Volcán', 'Set de tres sartenes antiadherentes', 1249.00, 'Hogar'),
    ('Cien años de soledad', 'Novela de Gabriel García Márquez', 189.00, 'Libros'),
    ('El Señor Presidente', 'Novela de Miguel Ángel Asturias', 165.00, 'Libros'),
    ('Manual de PostgreSQL', 'Guía práctica de administración y consultas', 420.00, 'Libros'),
    ('Camisa de lino Atitlán', 'Camisa de lino para clima cálido', 459.00, 'Ropa'),
    ('Chumpa de invierno Xela', 'Chumpa impermeable para clima frío', 1099.00, 'Ropa'),
    ('Gorra Tikal', 'Gorra de algodón ajustable', 149.00, 'Ropa');

INSERT INTO users (username, password, role) VALUES
    ('admin', 'admin123', 'admin'),
    ('ana', 'ana2024', 'customer'),
    ('luis', 'luis2024', 'customer'),
    ('maria', 'maria2024', 'customer');

INSERT INTO orders (user_id, total, status) VALUES
    (2, 8999.00, 'entregado'),
    (2, 189.00, 'enviado'),
    (3, 1299.00, 'pendiente'),
    (3, 349.50, 'entregado'),
    (4, 1099.00, 'enviado'),
    (4, 459.00, 'pendiente');

INSERT INTO comments (product_id, author, body) VALUES
    (1, 'ana', 'Muy rápida y liviana'),
    (1, 'luis', 'La batería dura todo el día'),
    (7, 'maria', 'Un clásico que vale la pena releer');

INSERT INTO cart_items (user_id, product_id, qty) VALUES (2, 4, 1);
