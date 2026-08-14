import csv
import asyncio
import api.models as models
from api.database import AsyncSessionLocal

BOOK_CSV_PATH = "./data/books_k10.csv"
BATCH_SIZE = 5000

async def seed_books():
    async with AsyncSessionLocal() as db:
        books_batch = []

        with open(BOOK_CSV_PATH, mode="r", encoding="utf-8") as f:
            reader = csv.DictReader(f)

            for count, book in enumerate(reader, start=1):
                new_book = models.Book(
                    isbn=book["ISBN"],
                    title=book["Book-Title"],
                    author=book["Book-Author"],
                    year=int(book["Year-Of-Publication"]),
                    average_rating=float(book["mean"]),
                    rating_count=int(book["count"]),
                )
                books_batch.append(new_book)

                if len(books_batch) >= BATCH_SIZE:
                    db.add_all(books_batch)
                    await db.flush()
                    books_batch = []
                    print(f"Pushed {count} books...")

            if books_batch:
                db.add_all(books_batch)
                print(f"Pushed all leftover books.")

        await db.commit()

if __name__ == "__main__":
    asyncio.run(seed_books())