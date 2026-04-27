BEGIN;

INSERT INTO "user" (email, password_hash, user_type) VALUES
('admin@cinema.com',   '8c6976e5b5410415bde908bd4dee15dfb167a9c873fc4bb8a81f6f2ab448a918', 'admin'),
('admin2@cinema.com',  '8c6976e5b5410415bde908bd4dee15dfb167a9c873fc4bb8a81f6f2ab448a918', 'admin'),
('john@email.com',     '8c6976e5b5410415bde908bd4dee15dfb167a9c873fc4bb8a81f6f2ab448a918', 'client'),
('emily@email.com',    '8c6976e5b5410415bde908bd4dee15dfb167a9c873fc4bb8a81f6f2ab448a918', 'client'),
('ava@email.com',      '8c6976e5b5410415bde908bd4dee15dfb167a9c873fc4bb8a81f6f2ab448a918', 'client');

INSERT INTO admin (admin_id, admin_role) VALUES
(1, 'General Manager'),
(2, 'Scheduling Coordinator');

INSERT INTO client (client_id, full_name, address, movie_interests, reward_signup, movies_watched) VALUES
(3, 'John Smith',  '123 Main St, Chicago IL',  'Action, Sci-Fi',       TRUE,  12),
(4, 'Emily Davis', '456 Oak Ave, Chicago IL',   'Drama, Mystery',       FALSE,  7),
(5, 'Ava Chen',    '789 Pine Rd, Skokie IL',    'Animation, Fantasy',   TRUE,  19);

INSERT INTO payment_method (client_id, payment_type, card_number, billing_address, cardholder_name, expiration_month, expiration_year) VALUES
(3, 'credit', '4111111111111111', '123 Main St, Chicago IL', 'John Smith',  7, 2028),
(3, 'debit',  '5222222222222222', NULL,                      'John Smith',  8, 2027),
(4, 'credit', '4000123412341234', '456 Oak Ave, Chicago IL', 'Emily Davis', 9, 2029),
(5, 'debit',  '5333444455556666', NULL,                      'Ava Chen',   10, 2027);

INSERT INTO person (full_name, birthdate, biography) VALUES
('Christopher Nolan', '1970-07-30', 'Director known for Inception and Interstellar.'),
('Cillian Murphy',    '1976-05-25', 'Actor known for Oppenheimer and Peaky Blinders.'),
('Emma Thomas',       '1971-12-09', 'Producer and frequent Nolan collaborator.'),
('Greta Gerwig',      '1983-08-04', 'Director and writer known for Barbie and Lady Bird.'),
('Julia Roberts',     '1967-10-28', 'Award-winning actress.'),
('Herbert Ross',      '1927-05-13', 'Director of Steel Magnolias.'),
('Meryl Streep',      '1949-06-22', 'Legendary actress with multiple Oscar wins.');

INSERT INTO movie (title, major_studio, release_date, length_min, original_language, description) VALUES
('Project Hail Mary',        TRUE,  '2026-03-20', 130, 'English',  'A lone astronaut must save Earth.'),
('Ready or Not 2',           TRUE,  '2026-03-20', 104, 'English',  'Horror-comedy sequel.'),
('Steel Magnolias',          TRUE,  '1989-11-15', 118, 'English',  'Classic drama about friendship.'),
('The Pout-Pout Fish',       TRUE,  '2026-04-10',  90, 'English',  'Family animation.'),
('Aadu 3',                   FALSE, '2026-03-19', 146, 'Malayalam','Comedy action sequel.'),
('Reminders of Him',         FALSE, '2026-02-15', 115, 'English',  'Relationship drama.'),
('Tow',                      FALSE, '2026-02-05',  95, 'English',  'Indie road dramedy.'),
('Undertone',                FALSE, '2026-02-10', 108, 'English',  'Coming-of-age drama.');

INSERT INTO movie_language (movie_id, language_name) VALUES
(1, 'English'), (1, 'Spanish'),
(2, 'English'),
(3, 'English'),
(4, 'English'), (4, 'Spanish'),
(5, 'Malayalam'), (5, 'English'),
(6, 'English'),
(7, 'English'),
(8, 'English');

INSERT INTO movie_director (movie_id, person_id) VALUES (1, 1), (3, 6), (4, 4);
INSERT INTO movie_writer  (movie_id, person_id) VALUES (1, 1), (3, 1), (4, 4);
INSERT INTO movie_producer(movie_id, person_id) VALUES (1, 3), (3, 3);
INSERT INTO movie_actor   (movie_id, person_id, character_name) VALUES
(1, 2, 'Ryland'),
(3, 5, 'Truvy'),
(3, 7, 'Ouiser');

INSERT INTO award (person_id, movie_id, award_title, award_year, award_role) VALUES
(1, 1, 'Best Director Nomination', 2026, 'director'),
(5, 3, 'Best Ensemble',            1990, 'actor'),
(7, 3, 'Best Actress Nomination',  1990, 'actor');

INSERT INTO theater (theater_name, max_occupancy, is_3d, has_fancy_sound) VALUES
('Theater 1',  180, TRUE,  TRUE),
('Theater 2',  180, TRUE,  FALSE),
('Theater 3',  180, FALSE, TRUE),
('Theater 4',   90, FALSE, TRUE),
('Theater 5',   90, FALSE, FALSE),
('Theater 6',  180, TRUE,  TRUE),
('Theater 7',  180, TRUE,  FALSE),
('Theater 8',  180, FALSE, TRUE),
('Theater 9',   90, FALSE, TRUE),
('Theater 10',  90, FALSE, FALSE);

INSERT INTO screening (movie_id, theater_id, screening_date, start_time, end_time, created_by_admin_id) VALUES
(1, 1, '2026-03-30', '11:00', '13:10', 1),
(2, 1, '2026-03-30', '14:00', '15:44', 1),
(3, 2, '2026-03-30', '11:00', '12:58', 1),
(4, 2, '2026-03-30', '13:20', '14:50', 2),
(5, 3, '2026-03-30', '11:00', '13:26', 2),
(6, 3, '2026-03-30', '14:00', '15:55', 2),
(1, 4, '2026-03-30', '18:00', '20:10', 1),
(2, 4, '2026-03-30', '20:30', '22:14', 1),
(7, 5, '2026-03-30', '11:00', '12:35', 2),
(8, 5, '2026-03-30', '13:00', '14:48', 2),
(1, 6, '2026-03-31', '11:00', '13:10', 1),
(3, 7, '2026-03-31', '11:00', '12:58', 1),
(4, 8, '2026-03-31', '14:00', '15:30', 2),
(5, 9, '2026-03-31', '11:00', '13:26', 2),
(6, 10,'2026-03-31', '13:00', '14:55', 2);

INSERT INTO ticket_sale (screening_id, client_id, payment_method_id, ticket_quantity) VALUES
(1, 3, 1, 2),
(1, NULL, NULL, 4),
(2, 4, 3, 2),
(3, 5, 4, 3),
(4, NULL, NULL, 5),
(5, 3, 2, 1),
(7, 4, 3, 6),
(8, NULL, NULL, 4),
(9, 5, 4, 2),
(10,NULL, NULL, 3);

COMMIT;
