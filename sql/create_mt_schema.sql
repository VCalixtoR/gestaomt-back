CREATE SCHEMA gestao_mt;
USE gestao_mt;

CREATE TABLE tbl_person (
	person_id INT NOT NULL AUTO_INCREMENT,
    person_name VARCHAR(50) NOT NULL UNIQUE,
	person_cpf CHAR(12) UNIQUE,
	person_birth_date DATE,
	person_gender ENUM ('M', 'F') NOT NULL,
    PRIMARY KEY (person_id)
);

CREATE TABLE tbl_user (
    user_id INT NOT NULL,
	user_type ENUM ('A', 'E') NOT NULL,
	user_mail VARCHAR(50) NOT NULL UNIQUE,
	user_phone_num VARCHAR(15),
	user_hash_password CHAR(65) NOT NULL,
    user_entry_date_time DATETIME DEFAULT NOW() NOT NULL,
    user_entry_allowed BOOL DEFAULT FALSE NOT NULL,
    PRIMARY KEY (user_id),
    FOREIGN KEY (user_id) REFERENCES tbl_person(person_id)
);

CREATE TABLE tbl_employee(
	employee_id INT NOT NULL,
    employee_active BOOL DEFAULT TRUE NOT NULL,
    employee_comission FLOAT NOT NULL,
    PRIMARY KEY (employee_id),
    FOREIGN KEY (employee_id) REFERENCES tbl_user(user_id)
);

CREATE TRIGGER employee_event_after_insert AFTER INSERT ON tbl_employee
    FOR EACH ROW INSERT INTO tbl_event (event_user_id, event_name_id, event_description_args) VALUES
		(NEW.employee_id, 1, NULL);

CREATE TABLE tbl_auth_token(
	token_user_id INT NOT NULL,
    token_date_time DATETIME NOT NULL,
    PRIMARY KEY (token_user_id),
    FOREIGN KEY (token_user_id) REFERENCES tbl_user(user_id)
);

CREATE TABLE tbl_event_name (
	event_name_id TINYINT NOT NULL AUTO_INCREMENT,
    event_name VARCHAR(50) NOT NULL,
    PRIMARY KEY (event_name_id)
);

INSERT INTO tbl_event_name (event_name) VALUES
    ("Permissão de cadastro"),
    ("Desligamento de funcionário"),
    ("Mudança de comissão");

CREATE TABLE tbl_event(
	event_id INT NOT NULL AUTO_INCREMENT,
    event_user_id INT NOT NULL,
    event_name_id TINYINT NOT NULL,
    event_date_time DATETIME DEFAULT NOW() NOT NULL,
    event_description_args VARCHAR(50),
    PRIMARY KEY (event_id),
    FOREIGN KEY (event_user_id) REFERENCES tbl_user(user_id),
    FOREIGN KEY (event_name_id) REFERENCES tbl_event_name(event_name_id)
);

CREATE TABLE tbl_product(
	product_id INT NOT NULL AUTO_INCREMENT,
    product_code VARCHAR(20) NOT NULL,
    product_name VARCHAR(50) NOT NULL,
    product_observations VARCHAR(1000),
    is_product_immutable BOOL DEFAULT FALSE NOT NULL,
    is_product_active BOOL DEFAULT TRUE NOT NULL,
    product_creation_date_time DATETIME DEFAULT NOW() NOT NULL,
    PRIMARY KEY (product_id)
);

CREATE TABLE tbl_product_collection(
	product_collection_id INT NOT NULL AUTO_INCREMENT,
    product_collection_pos INT NOT NULL,
    product_collection_name VARCHAR(50) NOT NULL UNIQUE,
	PRIMARY KEY (product_collection_id)
);

INSERT INTO tbl_product_collection (product_collection_pos, product_collection_name) VALUES 
	(1, "Autumn Winter 23"), (2, "Party"), (3, "Winter is Coming"), (4,"Summer 22"), (5, "Lets Glow"), (6, "Back to Party");
    
CREATE TABLE tbl_product_has_collection(
	product_has_collection_id INT NOT NULL AUTO_INCREMENT,
    product_id INT NOT NULL,
    product_collection_id INT NOT NULL,
	PRIMARY KEY (product_has_collection_id),
    FOREIGN KEY (product_id) REFERENCES tbl_product(product_id),
    FOREIGN KEY (product_collection_id) REFERENCES tbl_product_collection(product_collection_id)
);

CREATE TABLE tbl_product_type(
	product_type_id INT NOT NULL AUTO_INCREMENT,
    product_type_pos INT NOT NULL,
	product_type_name VARCHAR(50) NOT NULL UNIQUE,
	PRIMARY KEY (product_type_id)
);

INSERT INTO tbl_product_type (product_type_pos, product_type_name) VALUES 
	(1, "Vestido"), (2, "Cropped"), (3, "Conjunto"), (4, "Saia"), (5, "Blusa"), (6, "Body"), (7, "Calça"), (8, "Short"), (9, "Top");

CREATE TABLE tbl_product_has_type(
	product_has_type_id INT NOT NULL AUTO_INCREMENT,
    product_id INT NOT NULL,
    product_type_id INT NOT NULL,
	PRIMARY KEY (product_has_type_id),
    FOREIGN KEY (product_id) REFERENCES tbl_product(product_id),
    FOREIGN KEY (product_type_id) REFERENCES tbl_product_type(product_type_id)
);

CREATE TABLE tbl_product_color(
	product_color_id INT NOT NULL AUTO_INCREMENT,
	product_color_pos INT NOT NULL,
    product_color_name VARCHAR(50) NOT NULL UNIQUE,
	PRIMARY KEY (product_color_id)
);

INSERT INTO tbl_product_color (product_color_pos, product_color_name) VALUES
	(1, "Preto"), (2, "Branco"), (3, "Amarelo"), (4, "Azul"), (5, "Azul Celeste"), (6, "Azul Ceu"),
    (7, "Azul Índigo"), (8, "Bronze"), (9, "Dourado"), (10, "Fucsia"), (11, "Laranja"), (12, "Lavanda"),
    (13, "Lilás"), (14, "Marinho"), (15, "Off"), (16, "Pink"), (17, "Prata"), (18, "Prateado"),
    (19, "Rosa"), (20, "Verde"), (21, "Verde Pistache"), (22, "Vermelho");

CREATE TABLE tbl_product_other(
	product_other_id INT NOT NULL AUTO_INCREMENT,
    product_other_pos INT NOT NULL,
    product_other_name VARCHAR(50) NOT NULL UNIQUE,
	PRIMARY KEY (product_other_id)
);

INSERT INTO tbl_product_other (product_other_pos, product_other_name) VALUES 
	(1, "Com Babado"), (2, "Sem Babado"), (3, "Com Bordado"), (4, "Sem Bordado"), (5, "Com cinto"), 
    (6, "Sem cinto"), (7, "Com Decote"), (8, "Sem Decote"), (9, "Com Tule"), (10, "Sem Tule");

CREATE TABLE tbl_product_size(
	product_size_id INT NOT NULL AUTO_INCREMENT,
    product_size_pos INT NOT NULL,
    product_size_name VARCHAR(20) NOT NULL UNIQUE,
	PRIMARY KEY (product_size_id)
);

INSERT INTO tbl_product_size (product_size_pos, product_size_name) VALUES 
	(1, "30"), (2, "32"), (3, "34"), (4, "36"), (5, "38"), (6, "40"), (7, "42"), (8, "44"), (9, "PP"), (10, "P"), (11, "M"), (12, "G");
    
CREATE TABLE tbl_customized_product(
	customized_product_id INT NOT NULL AUTO_INCREMENT,
	product_id INT NOT NULL,
    product_color_id INT,
    product_other_id INT,
    product_size_id INT NOT NULL,
    is_customized_product_immutable BOOL DEFAULT FALSE NOT NULL,
    is_customized_product_active BOOL DEFAULT TRUE NOT NULL,
    customized_product_price FLOAT NOT NULL,
    customized_product_quantity INT NOT NULL,
	PRIMARY KEY (customized_product_id),
    FOREIGN KEY (product_id) REFERENCES tbl_product(product_id),
    FOREIGN KEY (product_color_id) REFERENCES tbl_product_color(product_color_id),
    FOREIGN KEY (product_other_id) REFERENCES tbl_product_other(product_other_id),
    FOREIGN KEY (product_size_id) REFERENCES tbl_product_size(product_size_id),
    CHECK (customized_product_quantity >= 0)
);

CREATE TABLE tbl_client(
	client_id INT NOT NULL,
    client_cep VARCHAR(10),
    client_adress VARCHAR(50),
    client_city VARCHAR(20),
    client_neighborhood VARCHAR(20),
    client_state CHAR(2),
    client_number INT,
    client_complement VARCHAR(50),
    client_classification ENUM('Ruim', 'Boa', 'Excelente') DEFAULT 'Ruim' NOT NULL,
    client_observations VARCHAR(1000),
    client_creation_date_time DATETIME DEFAULT NOW() NOT NULL,
    PRIMARY KEY (client_id),
    FOREIGN KEY (client_id) REFERENCES tbl_person(person_id)
);

CREATE TABLE tbl_client_contact(
	contact_id INT NOT NULL AUTO_INCREMENT,
    contact_client_id INT NOT NULL,
    contact_type ENUM ('T', 'E', 'I', 'W') NOT NULL,
    contact_value VARCHAR(256) NOT NULL,
    PRIMARY KEY (contact_id),
    FOREIGN KEY (contact_client_id) REFERENCES tbl_client(client_id)
);

CREATE TABLE tbl_client_children(
	children_id INT NOT NULL AUTO_INCREMENT,
    children_client_id INT NOT NULL,
    children_name VARCHAR(50) NOT NULL,
    children_birth_date DATE,
	children_product_size_id INT NOT NULL,
    PRIMARY KEY (children_id),
    FOREIGN KEY (children_client_id) REFERENCES tbl_client(client_id),
    FOREIGN KEY (children_product_size_id) REFERENCES tbl_product_size(product_size_id)
);

CREATE TABLE tbl_payment_method(
	payment_method_id INT NOT NULL AUTO_INCREMENT,
    payment_method_name VARCHAR(30) NOT NULL UNIQUE,
	PRIMARY KEY (payment_method_id)
);

CREATE TABLE tbl_payment_method_installment(
	payment_method_installment_id INT NOT NULL AUTO_INCREMENT,
    payment_method_id INT NOT NULL,
    payment_method_installment_number INT NOT NULL,
	PRIMARY KEY (payment_method_installment_id),
    FOREIGN KEY (payment_method_id) REFERENCES tbl_payment_method(payment_method_id),
    CHECK (payment_method_installment_number > 0)
);

INSERT INTO tbl_payment_method(payment_method_name) VALUES 
    ('Cartão de crédito'),
    ('Cartão de débito'),
    ('Cheque'),
    ('Dinheiro'),
    ('Pix');
   
INSERT INTO tbl_payment_method_installment(payment_method_id, payment_method_installment_number) VALUES 
	(1, 1),(1, 2),(1, 3),(1, 4),(1, 5),(1, 6),(1, 7),(1, 8),(1, 9),(1, 10),
    (2, 1),(2, 2),(2, 3),(2, 4),(2, 5),(2, 6),(2, 7),(2, 8),(2, 9),(2, 10),
    (3, 1),(3, 2),(3, 3),(3, 4),(3, 5),(3, 6),(3, 7),(3, 8),(3, 9),(3, 10),
    (4, 1),(4, 2),(4, 3),(4, 4),(4, 5),(4, 6),(4, 7),(4, 8),(4, 9),(4, 10),
    (5, 1),(5, 2),(5, 3),(5, 4),(5, 5),(5, 6),(5, 7),(5, 8),(5, 9),(5, 10);

CREATE TABLE tbl_sale(
	sale_id INT NOT NULL AUTO_INCREMENT,
    sale_client_id INT NOT NULL,
    sale_employee_id INT NOT NULL,
    sale_status ENUM('Confirmado', 'Cancelado') DEFAULT ('Confirmado') NOT NULL,
    sale_total_discount_percentage FLOAT NOT NULL,
    sale_total_value FLOAT NOT NULL,
    sale_creation_date_time DATETIME DEFAULT NOW() NOT NULL,
	PRIMARY KEY (sale_id),
    FOREIGN KEY (sale_client_id) REFERENCES tbl_client(client_id),
    FOREIGN KEY (sale_employee_id) REFERENCES tbl_employee(employee_id),
	CHECK (sale_total_discount_percentage >= 0)
);

CREATE TABLE tbl_sale_has_payment_method_installment(
	sale_has_payment_method_installment_id INT NOT NULL AUTO_INCREMENT,
    sale_id INT NOT NULL,
    payment_method_installment_id INT NOT NULL,
    payment_method_value FLOAT NOT NULL,
    PRIMARY KEY (sale_has_payment_method_installment_id),
    FOREIGN KEY (sale_id) REFERENCES tbl_sale(sale_id),
    FOREIGN KEY (payment_method_installment_id) REFERENCES tbl_payment_method_installment(payment_method_installment_id),
    CHECK (payment_method_value > 0)
);

CREATE TABLE tbl_sale_has_product(
	sale_has_product_id INT NOT NULL AUTO_INCREMENT,
    sale_id INT NOT NULL,
    product_id INT NOT NULL,
    customized_product_id INT NOT NULL,
    sale_has_product_price FLOAT NOT NULL,
    sale_has_product_quantity INT NOT NULL,
	PRIMARY KEY (sale_has_product_id),
    FOREIGN KEY (sale_id) REFERENCES tbl_sale(sale_id),
    FOREIGN KEY (product_id) REFERENCES tbl_product(product_id),
    FOREIGN KEY (customized_product_id) REFERENCES tbl_customized_product(customized_product_id),
    CHECK (sale_has_product_price > 0),
    CHECK (sale_has_product_quantity >= 0)
);

CREATE TABLE tbl_conditional(
	conditional_id INT NOT NULL AUTO_INCREMENT,
    conditional_client_id INT NOT NULL,
    conditional_employee_id INT NOT NULL,
    conditional_status ENUM('Pendente', 'Devolvido', 'Cancelado') DEFAULT 'Pendente' NOT NULL,
    conditional_creation_date_time DATETIME DEFAULT NOW() NOT NULL,
	PRIMARY KEY (conditional_id),
    FOREIGN KEY (conditional_client_id) REFERENCES tbl_client(client_id),
    FOREIGN KEY (conditional_employee_id) REFERENCES tbl_employee(employee_id)
);

CREATE TABLE tbl_conditional_has_product(
	conditional_has_product_id  INT NOT NULL AUTO_INCREMENT,
    conditional_id INT NOT NULL,
    product_id INT NOT NULL,
    customized_product_id INT NOT NULL,
    conditional_has_product_quantity INT NOT NULL,
	PRIMARY KEY (conditional_has_product_id),
    FOREIGN KEY (conditional_id) REFERENCES tbl_conditional(conditional_id),
    FOREIGN KEY (product_id) REFERENCES tbl_product(product_id),
    FOREIGN KEY (customized_product_id) REFERENCES tbl_customized_product(customized_product_id),
    CHECK (conditional_has_product_quantity >= 0)
);

INSERT INTO tbl_person (person_name, person_cpf, person_birth_date, person_gender) VALUES
	("Postman","99999999999", "1999-07-21","M"),
	("Admin","00000000000", "1999-07-21","M"),
    ("Funcionario","11111111111", "1999-07-21","M");

INSERT INTO tbl_user (user_id, user_type, user_mail, user_phone_num, user_hash_password, user_entry_allowed) VALUES
	(1,"A","postman@gmail.com","+55997791557","03ac674216f3e15c761ee1a5e255f067953623c8b388b4459e13f978d7c846f4", TRUE),
	(2,"A","admin@gmail.com","+55997791557","03ac674216f3e15c761ee1a5e255f067953623c8b388b4459e13f978d7c846f4", TRUE),
    (3,"E","funcionario@gmail.com","+55997791557","03ac674216f3e15c761ee1a5e255f067953623c8b388b4459e13f978d7c846f4", FALSE);
    
INSERT INTO tbl_employee (employee_id, employee_active, employee_comission) VALUES
	(1, TRUE, 0.0),
    (2, TRUE, 0.0);

/*
USE gestao_mt_homol;
UPDATE tbl_user SET user_hash_password = "03ac674216f3e15c761ee1a5e255f067953623c8b388b4459e13f978d7c846f4";
*/