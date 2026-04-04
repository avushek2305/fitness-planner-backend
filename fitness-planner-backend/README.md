# Fitness Planner Backend

Minimal FastAPI backend for serving a hardcoded structured plan for today.

## Project structure

```text
fitness-planner-backend/
├── app/
│   ├── __init__.py
│   ├── crud.py
│   ├── database.py
│   ├── main.py
│   ├── models.py
│   ├── planner.py
│   └── schemas.py
├── .env.example
├── requirements.txt
└── README.md
```

## How to run the server

1. Move into the project folder:

```bash
cd /Users/avishekkumarshar/Documents/CodexProjects/fitness-planner-backend
```

2. Create a virtual environment:

```bash
python3 -m venv .venv
```

3. Activate the virtual environment:

```bash
source .venv/bin/activate
```

4. Install dependencies:

```bash
pip install -r requirements.txt
```

5. Configure PostgreSQL connection settings:

```bash
cp .env.example .env
export DATABASE_URL="postgresql+psycopg://postgres:postgres@localhost:5432/fitness_planner"
```

You can also use `POSTGRES_DB`, `POSTGRES_USER`, `POSTGRES_PASSWORD`, `POSTGRES_HOST`, and `POSTGRES_PORT` instead of `DATABASE_URL`.

6. Start the FastAPI server with Uvicorn:

```bash
uvicorn app.main:app --reload
```

The app creates tables automatically on startup.

7. Open these URLs in your browser:

- API: `http://127.0.0.1:8000/plan/demo-user`
- Docs: `http://127.0.0.1:8000/docs`

## Run with Docker

1. Build the image:

```bash
docker build -t fitness-planner-backend .
```

2. Run the container with your environment file:

```bash
docker run --env-file .env -p 8000:8000 fitness-planner-backend
```

3. Open:

- API: `http://127.0.0.1:8000`
- Docs: `http://127.0.0.1:8000/docs`

## Example curl requests

1. Create a user profile:

```bash
curl -X POST "http://127.0.0.1:8000/user" \
  -H "Content-Type: application/json" \
  -d '{
    "user_id": "demo-user",
    "gym_time": "19:00",
    "goal": "muscle_gain",
    "workout_days_per_week": 4
  }'
```

2. Fetch the saved plan:

```bash
curl "http://127.0.0.1:8000/plan/demo-user"
```

3. Update the user's gym schedule:

```bash
curl -X PUT "http://127.0.0.1:8000/user/schedule" \
  -H "Content-Type: application/json" \
  -d '{
    "user_id": "demo-user",
    "gym_time": "20:00"
  }'
```

4. Submit workout feedback:

```bash
curl -X POST "http://127.0.0.1:8000/feedback" \
  -H "Content-Type: application/json" \
  -d '{
    "user_id": "demo-user",
    "difficulty": 1,
    "energy_level": 4,
    "pain": false
  }'
```

5. Fetch the next plan after feedback:

```bash
curl "http://127.0.0.1:8000/plan/demo-user"
```

The API now stores users, plan logs, and feedback in PostgreSQL through SQLAlchemy. It uses the saved `gym_time` from the database and returns `day`, `workout`, `meals`, `time_blocks`, `next_action`, `current_time`, and `status`.

## Example response

```json
{
  "success": true,
  "data": {
    "day": 1,
    "workout": [
      {
        "name": "Brisk walk",
        "sets": null,
        "reps": null,
        "duration_minutes": 10,
        "notes": "Easy pace to warm up."
      }
    ],
    "meals": [
      {
        "name": "Breakfast oats bowl",
        "calories": 420,
        "protein_grams": 22,
        "notes": "Oats, Greek yogurt, berries, and chia seeds."
      }
    ],
    "time_blocks": {
      "pre_workout_time": "18:15",
      "workout_time": "19:00",
      "post_workout_time": "20:15"
    },
    "next_action": "Eat pre-workout meal",
    "current_time": "17:40",
    "status": "pre_workout",
    "streak": 0,
    "today_score": 0.0,
    "user_type": "beginner",
    "workout_days_per_week": 4
  }
}
```
