BEGIN;

CREATE INDEX idx_user_email            ON "user"(email);
CREATE INDEX idx_client_name           ON client(full_name);
CREATE INDEX idx_payment_client        ON payment_method(client_id);
CREATE INDEX idx_movie_title           ON movie(title);
CREATE INDEX idx_movie_release         ON movie(release_date);
CREATE INDEX idx_person_name           ON person(full_name);
CREATE INDEX idx_screening_movie       ON screening(movie_id);
CREATE INDEX idx_screening_theater     ON screening(theater_id, screening_date);
CREATE INDEX idx_screening_date        ON screening(screening_date, start_time);
CREATE INDEX idx_ticket_screening      ON ticket_sale(screening_id);
CREATE INDEX idx_ticket_client         ON ticket_sale(client_id);
CREATE INDEX idx_ticket_time           ON ticket_sale(purchase_time);

COMMIT;
