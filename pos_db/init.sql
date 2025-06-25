-- Inicialización de tabla de usuarios
CREATE TABLE usuarios (
    usuario_id serial NOT NULL,
    nombre varchar(15) NOT NULL,
    apellido varchar(15) NOT NULL,

    CONSTRAINT usuarios_pk PRIMARY KEY (usuario_id)
);

-- Inicialización de tabla de productos
CREATE TABLE productos (
    producto_id serial NOT NULL,
    nombre_producto varchar(25) NOT NULL,
    manufacturador varchar(20) NOT NULL,
    precio real NOT NULL,

    CONSTRAINT producto_pk PRIMARY KEY (producto_id),
    CONSTRAINT precio_check CHECK (precio >= 0)
);

-- Inicialización de tabla de pedidos
CREATE TABLE pedidos (
    pedido_id serial NOT NULL,
    usuario_id integer NOT NULL,
    producto_id integer NOT NULL,
    cantidad integer NOT NULL,
    fecha_pedido timestamp NOT NULL,

    CONSTRAINT pedidos_pk PRIMARY KEY (pedido_id),
    CONSTRAINT pedidos_fk_usuarios FOREIGN KEY (usuario_id) REFERENCES usuarios (usuario_id) ON DELETE CASCADE,
    CONSTRAINT pedidos_fk_productos FOREIGN KEY (producto_id) REFERENCES productos (producto_id) ON DELETE CASCADE,
    CONSTRAINT cantidad_check CHECK (cantidad >= 0)
);
