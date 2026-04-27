# CS 480 — Movie Ticketing System
Spring 2026 | Prof. Boris Glavic | UIC

## Group Members
- Rudra Patel
- Kirtan Patel
- Nisarg Patel

## Tech Stack
- Python / Flask
- PostgreSQL + pgvector (bonus)
- sentence-transformers (bonus RAG)
- scikit-learn Random Forest (bonus ML)
- HTML / CSS / Jinja2

## Setup

### 1. Create the database
```
psql -U postgres -c "CREATE DATABASE movie_ticketing;"
```

### 2. Run SQL files in order
```
psql -U postgres -d movie_ticketing -f sql/01_schema.sql
psql -U postgres -d movie_ticketing -f sql/02_data.sql
psql -U postgres -d movie_ticketing -f sql/03_indexes.sql
```

### 3. BONUS — Install pgvector and run bonus SQL
```
# Install pgvector extension (https://github.com/pgvector/pgvector)
psql -U postgres -d movie_ticketing -f sql/04_bonus_pgvector.sql
```

### 4. Install dependencies
```
pip install -r requirements.txt
```

### 5. Run the app

Mac/Linux:
```
DB_HOST=localhost DB_NAME=movie_ticketing DB_USER=postgres DB_PASS=postgres python app.py
```

Windows PowerShell:
```
$env:DB_HOST="localhost"; $env:DB_NAME="movie_ticketing"; $env:DB_USER="postgres"; $env:DB_PASS="postgres"; python app.py
```

Open http://localhost:5000

## Features

### Client
- Register / Login
- Search screenings by title, date, time, 3D, fancy sound
- See movie info (cast, directors, language, length) in search results
- See real-time seat availability and computed ticket price
- Book tickets (registered with payment method, or anonymous)
- Manage payment methods (add / update / delete credit and debit cards)
- Reward program tracking
- ⭐ BONUS: AI movie recommendations based on personal interests (RAG)

### Admin
- Register / Login
- Schedule new screenings (DB enforces 20-min buffer between screenings)
- View all screenings with remaining seat capacity
- Analytics: revenue by movie, theater, date; min/avg/max occupancy; registered vs anonymous
- 🤖 BONUS: AI Schedule Optimizer — ML model predicts occupancy and generates optimal 7-day schedule
- 🤖 BONUS: Embed movie descriptions for recommendation system

## Bonus Features

### RAG Movie Recommendations (Bonus 1)
- Uses sentence-transformers (all-MiniLM-L6-v2) to embed movie descriptions
- Stores embeddings in PostgreSQL using pgvector extension with HNSW index
- Client enters their interests → system embeds them → finds 3 most similar movies using cosine similarity
- Admin runs embedding step once from the AI Scheduler page

### Occupancy Prediction + Schedule Optimizer (Bonus 2)
- Random Forest model trained on past ticket sales
- Features: day of week, hour, weekend flag, evening flag, major studio, days since release, theater size, 3D, fancy sound
- Predicts expected ticket sales for each movie/theater/timeslot combination
- Greedy optimizer assigns movies to maximize predicted revenue for next 7 days
- Accessible from Admin → AI Scheduler page

## File Structure
```
app.py                     All routes including bonus
embeddings.py              RAG embedding logic
ml_model.py                Random Forest occupancy predictor
requirements.txt
static/style.css
templates/
  base.html
  login.html
  register_client.html
  register_admin.html
  client_home.html
  search.html
  book.html
  payments.html
  recommendations.html     BONUS
  admin_home.html
  admin_screenings.html
  admin_analytics.html
  schedule_optimizer.html  BONUS
sql/
  01_schema.sql
  02_data.sql
  03_indexes.sql
  04_bonus_pgvector.sql    BONUS
docs/
  er_model_mermaid.md
```
