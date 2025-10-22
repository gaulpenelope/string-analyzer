
# String Analyzer API

This is a small REST API that analyzes strings and saves their properties.  
It was built with **FastAPI**, **SQLAlchemy**, and **SQLite** for simplicity.

---

## What It Does

When you send a string to the API, it calculates and stores:

- **length** – number of characters  
- **is_palindrome** – whether it reads the same backward  
- **unique_characters** – how many distinct characters it has  
- **word_count** – how many words are in the string  
- **sha256_hash** – a unique hash that acts as its ID  
- **character_frequency_map** – how many times each character appears  

All data is stored in a local (or cloud) database.

---

## API Routes

### 1. Analyze or Create a String  
**POST** `/strings`
```json
{
  "value": "madam"
}
````

Response:

```json
{
  "id": "765cc52b3dbc1bb8ec279ef9c8ec3d0f251c0c92a6ecdc1870be8f7dc7538b21",
  "value": "madam",
  "properties": {
    "length": 5,
    "is_palindrome": true,
    "unique_characters": 3,
    "word_count": 1,
    "sha256_hash": "765cc52b3dbc1bb8ec279ef9c8ec3d0f251c0c92a6ecdc1870be8f7dc7538b21",
    "character_frequency_map": {
      "m": 2,
      "a": 2,
      "d": 1
    }
  },
  "created_at": "2025-10-22T15:08:59.447528+00:00"
}
```

---

### 2. Get a String

**GET** `/strings/{string_value}`
Returns the saved analysis for that string.

---

### 3. Get All Strings

**GET** `/strings?is_palindrome=true&min_length=3&contains_character=a`
Supports filters like:

* `is_palindrome`
* `min_length` / `max_length`
* `word_count`
* `contains_character`

---

### 4. Natural Language Filter

**GET** `/strings/filter-by-natural-language?query=all single word palindromic strings`
This endpoint interprets plain English filters, like:

* “strings longer than 10 characters”
* “all single word palindromic strings”

---

### 5. Delete a String

**DELETE** `/strings/{string_value}`

Deletes the string from the database.

---

## Setup (Running Locally)

### 1. Clone the repo

```bash
git clone https://github.com/gaulpenelope/string-analyzer.git
cd string-analyzer
```

### 2. Create a virtual environment

Windows:

```bash
python -m venv venv
venv\Scripts\activate
```

Mac/Linux:

```bash
python3 -m venv venv
source venv/bin/activate
```

### 3. Install dependencies

```bash
pip install -r requirements.txt
```

### 4. Run the app

```bash
uvicorn app.main:app --reload
```

Visit → [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs)

---

## Environment Variable

Create a `.env` file with:

```
DATABASE_URL=sqlite:///./strings.db
```

---

## Example Flow

1. **POST** `/strings` with `"racecar"`
2. **GET** `/strings/racecar`
3. **GET** `/strings?is_palindrome=true`
4. **DELETE** `/strings/racecar`

---

## Deployment

You can host this on:

* [Railway.app](https://railway.app)
* [Heroku](https://heroku.com)
* [PXXL App](https://pxxl.app)
* AWS EC2

> Vercel and Render are **not allowed** for this cohort.

---

## Submission Info

When submitting, use the `/stage-one-backend` command in Slack and provide:

* API Base URL
* GitHub Repo
* Full Name
* Email
* Tech Stack

---

## Author

**Gaul Penelope Princess Anuoluwa**
Backend Developer | FastAPI

---

### Notes

Built for the **Backend Wizards – Stage 1 Challenge (2025)**.
Focused on clean design, persistence, and filterable data.
