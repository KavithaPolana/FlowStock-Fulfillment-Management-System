import mysql.connector
from pathlib import Path
from dotenv import load_dotenv
import os

# Load .env from the backend folder
env_path = Path(__file__).resolve().parents[1] / ".env"
load_dotenv(env_path)

def get_connection():
    try:
        connection = mysql.connector.connect(
            host=os.getenv("DB_HOST"),
            user=os.getenv("DB_USER"),
            password=os.getenv("DB_PASSWORD"),
            database=os.getenv("DB_NAME")
        )
        return connection

    except mysql.connector.Error as error:
        print("Database connection failed:", error)
        return None