from fastapi import FastAPI
from dotenv import load_dotenv


from src.routes.routers import router


load_dotenv()


app = FastAPI(
    title="Query Risk Classifier API",
    description="API for evaluating the safety of user queries."
)

app.include_router(router)