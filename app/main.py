from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

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
from routers.menu import router as menu_router
from routers.report import router as report_router

app.include_router(user_router)
app.include_router(shop_router)
app.include_router(category_router)
app.include_router(product_router)
app.include_router(bill_router)
app.include_router(menu_router)
app.include_router(report_router)
origins = [
    "http://localhost:5173",  # Your Vite React frontend
    "http://127.0.0.1:5173",  # Sometimes Vite uses this origin
    # You can add your production domain later when you deploy
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,          # Allows these origins
    allow_credentials=True,        # Allows cookies/authorization headers
    allow_methods=["*"],           # Allows all HTTP methods (GET, POST, etc.)
    allow_headers=["*"],           # Allows all headers
)
@app.get("/")
def root():
    return {
        "message": "Vegetable Shop Backend API is running"
    }