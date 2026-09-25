from fastapi import FastAPI


app = FastAPI(
    title="POS Management System",
    description="Vegetable and Broiler Shop POS API",
    version="1.0.0"
)
from fastapi import FastAPI

from routers.user  import router as user_router
from routers.shops import router as shop_router
from routers.categories import router as category_router
from routers.product import router as product_router
from routers.bill import router as bill_router
app.include_router(user_router)
app.include_router(shop_router)
app.include_router(category_router)
app.include_router(product_router)
app.include_router(bill_router)

@app.get("/")
def root():
    return {
        "message": "Vegetable Shop Backend API is running"
    }