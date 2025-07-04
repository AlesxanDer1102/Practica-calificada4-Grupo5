INSERT INTO
    usuarios (nombre, apellido)
VALUES
    ('Juan', 'Pérez'),
    ('María', 'García'),
    ('Carlos', 'López'),
    ('Ana', 'Martínez'),
    ('Luis', 'Rodríguez'),
    ('Carmen', 'Sánchez'),
    ('Pedro', 'González'),
    ('Laura', 'Hernández'),
    ('Miguel', 'Díaz'),
    ('Sofia', 'Ruiz');


INSERT INTO
    productos (nombre_producto, manufacturador, precio)
VALUES
    ('Laptop HP Pavilion', 'HP', 850.00),
    ('iPhone 14', 'Apple', 999.00),
    ('Samsung Galaxy S23', 'Samsung', 899.00),
    ('MacBook Air M2', 'Apple', 1199.00),
    ('Logitech MX Master 3', 'Logitech', 99.99),
    ('Sony WH-1000XM4', 'Sony', 349.99),
    ('iPad Air', 'Apple', 599.00),
    ('Dell XPS 13', 'Dell', 1200.00),
    ('Nintendo Switch', 'Nintendo', 299.99),
    ('AirPods Pro', 'Apple', 249.00);


INSERT INTO
    pedidos (usuario_id, producto_id, cantidad, fecha_pedido)
VALUES
    (1, 1, 1, '2025-04-15 14:30:00'),
    (2, 2, 2, '2025-04-15 15:00:00'),
    (3, 3, 1, '2025-04-15 17:30:00'),
    (1, 5, 1, '2025-04-16 09:15:00'),
    (4, 6, 1, '2025-04-16 10:45:00'),
    (5, 4, 1, '2025-04-17 11:20:00'),
    (2, 7, 1, '2025-04-17 13:30:00'),
    (6, 8, 1, '2025-04-18 08:45:00'),
    (7, 9, 2, '2025-04-18 16:00:00'),
    (3, 10, 1, '2025-04-19 12:15:00'),
    (8, 1, 1, '2025-04-19 14:30:00'),
    (9, 2, 1, '2025-04-20 09:00:00'),
    (10, 3, 1, '2025-04-20 15:45:00'),
    (4, 9, 1, '2025-04-21 10:30:00'),
    (5, 10, 3, '2025-04-21 17:00:00');
