from sqlalchemy import text

from database import engine


def update_product_shop_table():
    print("Updating product_shops table...")

    with engine.begin() as connection:
        connection.execute(
            text("""
                ALTER TABLE product_shops
                ADD COLUMN IF NOT EXISTS created_at
                TIMESTAMP WITH TIME ZONE
                DEFAULT CURRENT_TIMESTAMP;
            """)
        )

    print("product_shops table updated successfully.")


if __name__ == "__main__":
    update_product_shop_table()
