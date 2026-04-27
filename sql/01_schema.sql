BEGIN;

CREATE TABLE "user" (
    user_id SERIAL PRIMARY KEY,
    email VARCHAR(255) NOT NULL UNIQUE,
    password_hash VARCHAR(255) NOT NULL,
    user_type VARCHAR(10) NOT NULL CHECK (user_type IN ('client', 'admin')),
    created_at DATE NOT NULL DEFAULT CURRENT_DATE
);

CREATE TABLE client (
    client_id INT PRIMARY KEY REFERENCES "user"(user_id) ON DELETE CASCADE,
    full_name VARCHAR(200) NOT NULL,
    address TEXT NOT NULL,
    movie_interests TEXT,
    reward_signup BOOLEAN NOT NULL DEFAULT FALSE,
    movies_watched INT NOT NULL DEFAULT 0
);

CREATE TABLE admin (
    admin_id INT PRIMARY KEY REFERENCES "user"(user_id) ON DELETE CASCADE,
    admin_role VARCHAR(100) NOT NULL
);

CREATE TABLE payment_method (
    payment_method_id SERIAL PRIMARY KEY,
    client_id INT NOT NULL REFERENCES client(client_id) ON DELETE CASCADE,
    payment_type VARCHAR(10) NOT NULL CHECK (payment_type IN ('credit', 'debit')),
    card_number VARCHAR(25) NOT NULL,
    billing_address TEXT,
    cardholder_name VARCHAR(200) NOT NULL,
    expiration_month INT NOT NULL CHECK (expiration_month BETWEEN 1 AND 12),
    expiration_year INT NOT NULL CHECK (expiration_year >= 2026),
    CHECK (payment_type != 'credit' OR billing_address IS NOT NULL)
);

CREATE TABLE person (
    person_id SERIAL PRIMARY KEY,
    full_name VARCHAR(200) NOT NULL,
    birthdate DATE,
    biography TEXT
);

CREATE TABLE movie (
    movie_id SERIAL PRIMARY KEY,
    title VARCHAR(200) NOT NULL,
    major_studio BOOLEAN NOT NULL DEFAULT FALSE,
    release_date DATE NOT NULL,
    length_min INT NOT NULL CHECK (length_min > 0),
    original_language VARCHAR(50) NOT NULL,
    description TEXT
);

CREATE TABLE movie_language (
    movie_id INT NOT NULL REFERENCES movie(movie_id) ON DELETE CASCADE,
    language_name VARCHAR(50) NOT NULL,
    PRIMARY KEY (movie_id, language_name)
);

CREATE TABLE movie_director (
    movie_id INT NOT NULL REFERENCES movie(movie_id) ON DELETE CASCADE,
    person_id INT NOT NULL REFERENCES person(person_id) ON DELETE CASCADE,
    PRIMARY KEY (movie_id, person_id)
);

CREATE TABLE movie_writer (
    movie_id INT NOT NULL REFERENCES movie(movie_id) ON DELETE CASCADE,
    person_id INT NOT NULL REFERENCES person(person_id) ON DELETE CASCADE,
    PRIMARY KEY (movie_id, person_id)
);

CREATE TABLE movie_producer (
    movie_id INT NOT NULL REFERENCES movie(movie_id) ON DELETE CASCADE,
    person_id INT NOT NULL REFERENCES person(person_id) ON DELETE CASCADE,
    PRIMARY KEY (movie_id, person_id)
);

CREATE TABLE movie_actor (
    movie_id INT NOT NULL REFERENCES movie(movie_id) ON DELETE CASCADE,
    person_id INT NOT NULL REFERENCES person(person_id) ON DELETE CASCADE,
    character_name VARCHAR(200) NOT NULL,
    PRIMARY KEY (movie_id, person_id, character_name)
);

CREATE TABLE award (
    award_id SERIAL PRIMARY KEY,
    person_id INT NOT NULL REFERENCES person(person_id) ON DELETE CASCADE,
    movie_id INT REFERENCES movie(movie_id) ON DELETE SET NULL,
    award_title VARCHAR(200) NOT NULL,
    award_year INT NOT NULL CHECK (award_year >= 1900),
    award_role VARCHAR(50) NOT NULL
);

CREATE TABLE theater (
    theater_id SERIAL PRIMARY KEY,
    theater_name VARCHAR(100) NOT NULL UNIQUE,
    max_occupancy INT NOT NULL CHECK (max_occupancy > 0),
    is_3d BOOLEAN NOT NULL DEFAULT FALSE,
    has_fancy_sound BOOLEAN NOT NULL DEFAULT FALSE
);

CREATE TABLE screening (
    screening_id SERIAL PRIMARY KEY,
    movie_id INT NOT NULL REFERENCES movie(movie_id) ON DELETE CASCADE,
    theater_id INT NOT NULL REFERENCES theater(theater_id) ON DELETE CASCADE,
    screening_date DATE NOT NULL,
    start_time TIME NOT NULL,
    end_time TIME NOT NULL,
    created_by_admin_id INT REFERENCES admin(admin_id) ON DELETE SET NULL,
    CHECK (end_time > start_time)
);

CREATE TABLE ticket_sale (
    sale_id SERIAL PRIMARY KEY,
    screening_id INT NOT NULL REFERENCES screening(screening_id) ON DELETE CASCADE,
    client_id INT REFERENCES client(client_id) ON DELETE SET NULL,
    payment_method_id INT REFERENCES payment_method(payment_method_id) ON DELETE SET NULL,
    ticket_quantity INT NOT NULL CHECK (ticket_quantity > 0),
    unit_price NUMERIC(10,2) NOT NULL DEFAULT 0,
    purchase_time TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    total_price NUMERIC(10,2) GENERATED ALWAYS AS (ticket_quantity * unit_price) STORED,
    CHECK ((client_id IS NULL AND payment_method_id IS NULL) OR (client_id IS NOT NULL AND payment_method_id IS NOT NULL))
);

CREATE OR REPLACE FUNCTION calculate_ticket_price(p_screening_id INT)
RETURNS NUMERIC(10,2)
LANGUAGE plpgsql AS $$
DECLARE
    v_price NUMERIC(10,2) := 15.00;
    v_is_3d BOOLEAN;
    v_fancy BOOLEAN;
    v_major BOOLEAN;
    v_release DATE;
    v_date DATE;
BEGIN
    SELECT t.is_3d, t.has_fancy_sound, m.major_studio, m.release_date, s.screening_date
    INTO v_is_3d, v_fancy, v_major, v_release, v_date
    FROM screening s
    JOIN theater t ON t.theater_id = s.theater_id
    JOIN movie m ON m.movie_id = s.movie_id
    WHERE s.screening_id = p_screening_id;

    IF NOT FOUND THEN
        RAISE EXCEPTION 'Screening not found: %', p_screening_id;
    END IF;

    IF v_is_3d THEN v_price := v_price + 5.00; END IF;
    IF v_fancy THEN v_price := v_price + 3.00; END IF;
    IF v_major THEN v_price := v_price + 3.00; END IF;

    IF v_release <= (v_date - INTERVAL '2 years')::DATE THEN
        v_price := ROUND(v_price * 0.60, 2);
    ELSIF v_release <= (v_date - INTERVAL '2 months')::DATE THEN
        v_price := ROUND(v_price * 0.80, 2);
    END IF;

    RETURN v_price;
END;
$$;

CREATE OR REPLACE FUNCTION check_screening_overlap()
RETURNS TRIGGER LANGUAGE plpgsql AS $$
BEGIN
    IF EXISTS (
        SELECT 1 FROM screening s
        WHERE s.theater_id = NEW.theater_id
        AND s.screening_date = NEW.screening_date
        AND s.screening_id != COALESCE(NEW.screening_id, -1)
        AND NOT (NEW.start_time >= (s.end_time + INTERVAL '20 minutes')
              OR (NEW.end_time + INTERVAL '20 minutes') <= s.start_time)
    ) THEN
        RAISE EXCEPTION 'Theater is already booked at that time (20 min buffer required)';
    END IF;
    RETURN NEW;
END;
$$;

CREATE TRIGGER trg_screening_overlap
BEFORE INSERT OR UPDATE ON screening
FOR EACH ROW EXECUTE FUNCTION check_screening_overlap();

CREATE OR REPLACE FUNCTION check_ticket_sale()
RETURNS TRIGGER LANGUAGE plpgsql AS $$
DECLARE
    v_capacity INT;
    v_sold INT;
BEGIN
    PERFORM 1 FROM screening WHERE screening_id = NEW.screening_id FOR UPDATE;

    SELECT t.max_occupancy INTO v_capacity
    FROM screening s JOIN theater t ON t.theater_id = s.theater_id
    WHERE s.screening_id = NEW.screening_id;

    SELECT COALESCE(SUM(ticket_quantity), 0) INTO v_sold
    FROM ticket_sale
    WHERE screening_id = NEW.screening_id AND sale_id != COALESCE(NEW.sale_id, -1);

    IF v_sold + NEW.ticket_quantity > v_capacity THEN
        RAISE EXCEPTION 'Not enough seats. Only % left', v_capacity - v_sold;
    END IF;

    IF NEW.client_id IS NOT NULL THEN
        IF NOT EXISTS (
            SELECT 1 FROM payment_method
            WHERE payment_method_id = NEW.payment_method_id AND client_id = NEW.client_id
        ) THEN
            RAISE EXCEPTION 'Payment method does not belong to this client';
        END IF;
    END IF;

    NEW.unit_price := calculate_ticket_price(NEW.screening_id);
    RETURN NEW;
END;
$$;

CREATE TRIGGER trg_ticket_sale
BEFORE INSERT OR UPDATE ON ticket_sale
FOR EACH ROW EXECUTE FUNCTION check_ticket_sale();

COMMIT;
