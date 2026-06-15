from dotenv import load_dotenv
import os

load_dotenv()

DB_URL = os.getenv("DB_URL")
JWT_SECRET_KEY = os.getenv("JWT_SECRET_KEY")