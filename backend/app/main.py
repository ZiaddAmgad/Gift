# ENTRY POINT: Runs the server
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.api import chat

app = FastAPI()

# Configure CORS to allow Localhost AND your Live Vercel Frontend
origins = [
    "http://localhost:3000",                      # Local Development
    "https://gift-frontend-zeta.vercel.app",      # Your Live Frontend
    "https://gift-frontend-zeta.vercel.app/"      # (Safe measure: sometimes browsers add a slash)
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include chat router
app.include_router(chat.router, prefix="/api/chat", tags=["chat"])

@app.get("/")
def read_root():
    return {"Hello": "My World 2"}