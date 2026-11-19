"""Compatibility entrypoint: python database.py initializes the five existing tables."""
from app.config import Settings
from app.database import Base, Document, Flashcard, Quiz, User, UserProgress, make_database

if __name__ == "__main__":
    engine, _ = make_database(Settings.from_env().database_url)
    Base.metadata.create_all(engine)
    engine.dispose()
    print("Khởi tạo SQLite thành công với 5 bảng.")
