#!/usr/bin/env python3
import sys
import logging
from pathlib import Path
from contextlib import asynccontextmanager
from typing import Optional

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
import uvicorn

from src.query_engine import QueryEngine

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(message)s')
logger = logging.getLogger(__name__)

engine = None

class QuestionRequest(BaseModel):
    question: str = Field(..., json_schema_extra={"example": "What is the GDP of Saudi Arabia in 2022?"})

class QuestionResponse(BaseModel):
    question: str
    country: str
    indicator_code: str
    indicator_name: str
    unit: str
    value: str
    year_used: Optional[int] = None
    api_url: str
    confidence_margin: float
    resolver_note: str
    note: Optional[str] = None

class HealthResponse(BaseModel):
    status: str
    parser: str

@asynccontextmanager
async def lifespan(app: FastAPI):
    global engine

    logger.info("Starting API...")

    index_path = "indices/index"
    if not Path(index_path).exists():
        logger.error(f"Index not found at {index_path}")
        logger.error("Run: python build_index.py")
        raise FileNotFoundError(f"Missing index: {index_path}")

    # check if ollama is running
    try:
        import requests
        resp = requests.get('http://localhost:11434/api/tags', timeout=2)
        if resp.status_code == 200:
            logger.info("Ollama detected")
        else:
            logger.warning("Ollama not available, using fallback parser")
    except:
        logger.warning("Ollama not available, using fallback parser")

    engine = QueryEngine(
        indicators_path="data/indicators.csv",
        countries_path="data/countries.csv",
        index_path=index_path,
        dspy_model="llama3.2"
    )

    logger.info("API ready")
    yield
    logger.info("Shutting down")

app = FastAPI(
    title="World Bank Query API",
    description="Natural language queries for World Bank statistics",
    version="1.0.0",
    lifespan=lifespan
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
async def root():
    return {
        "name": "World Bank Query API",
        "version": "1.0.0",
        "endpoints": {
            "POST /query": "Answer a question (JSON)",
            "GET /ask": "Answer a question (query param)",
            "GET /health": "Health check",
            "GET /docs": "API documentation"
        }
    }

@app.get("/health", response_model=HealthResponse)
async def health():
    if engine is None:
        raise HTTPException(status_code=503, detail="Engine not initialized")

    return HealthResponse(
        status="ok",
        parser="DSPy + Ollama (llama3.2)"
    )

@app.post("/query", response_model=QuestionResponse)
async def query_post(request: QuestionRequest):
    if engine is None:
        raise HTTPException(status_code=503, detail="Engine not ready")

    try:
        result = engine.answer(request.question)
        return QuestionResponse(**result)
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))
    except RuntimeError as e:
        raise HTTPException(status_code=500, detail=f"API error: {e}")
    except Exception as e:
        logger.error(f"Query failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/ask", response_model=QuestionResponse)
async def query_get(q: str = Query(..., example="What is the GDP of Saudi Arabia in 2022?")):
    if engine is None:
        raise HTTPException(status_code=503, detail="Engine not ready")

    try:
        result = engine.answer(q)
        return QuestionResponse(**result)
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))
    except RuntimeError as e:
        raise HTTPException(status_code=500, detail=f"API error: {e}")
    except Exception as e:
        logger.error(f"Query failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('--host', default='0.0.0.0')
    parser.add_argument('--port', type=int, default=8000)
    parser.add_argument('--reload', action='store_true')
    args = parser.parse_args()

    print("\n" + "=" * 60)
    print("World Bank Query API")
    print("=" * 60)
    print(f"Starting on http://{args.host}:{args.port}")
    print(f"Docs at http://localhost:{args.port}/docs")
    print("=" * 60 + "\n")

    uvicorn.run(
        "run_api:app",
        host=args.host,
        port=args.port,
        reload=args.reload,
        log_level="info"
    )
