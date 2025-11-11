# World Bank Query API

Natural language interface for World Bank statistics. Ask questions, get answers.

## Setup

**Prerequisites:**

- Python 3.9+
- [Ollama](https://ollama.ai) with llama3.2 model

Install Ollama:

```bash
brew install ollama  # macOS
# or download from https://ollama.ai

ollama pull llama3.2
ollama serve
```

Install dependencies:

```bash
pip install -r requirements.txt
```

## Usage

### 1. Build Index (first time only)

```bash
python build_index.py
```

Builds a semantic embedding-based search index from the indicators catalog using `sentence-transformers` and FAISS. Takes about 30-60 seconds depending on your hardware.

### 2. Run API

```bash
python run_api.py
```

API starts at http://localhost:8000

Interactive docs at http://localhost:8000/docs

## Example Queries

```bash
# POST request
curl -X POST http://localhost:8000/query \
  -H "Content-Type: application/json" \
  -d '{"question": "What is the GDP of Leba in 2022?"}'

# GET request
curl "http://localhost:8000/ask?q=Latest+inflation+rate+for+LEBANON"
```

**Python:**

```python
import requests

resp = requests.post(
    "http://localhost:8000/query",
    json={"question": "What is the GDP of Lebanon in 2022?"}
)

print(resp.json()['value'])  # "$1.11T"
```

## Sample Questions

- "GDP per capita PPP for United States in 2021"
- "Unemployment rate for males aged 15-24 in Egypt in 2020"
- "Life expectancy in Japan in 2022"
- "CO2 emissions per capita for China in 2021"

## API Response

```json
{
  "question": "What is the GDP of Lebanon in 2022?",
  "country": "SAU",
  "indicator_code": "NY.GDP.MKTP.CD",
  "indicator_name": "GDP (current US$)",
  "value": "$1.11T",
  "year_used": 2022,
  "confidence_margin": 0.4523,
  "api_url": "https://api.worldbank.org/v2/...",
  "resolver_note": "query='gdp current_usd', semantic=0.892"
}
```

## Configuration

Edit `run_api.py` to change settings:

```python
engine = QueryEngine(
    indicators_path="data/indicators.csv",
    countries_path="data/countries.csv",
    index_path="indices/index",
    use_dspy=True,           # Use Ollama for parsing
    dspy_model="llama3.2",   # Or: mistral, phi3, etc.
    index_mode="embedding"   # Semantic embedding search (default)
)
```

Run on different port:

```bash
python run_api.py --port 3000
```

## Troubleshooting

**Ollama not detected:**

- Check if running: `curl http://localhost:11434/api/tags`
- Start it: `ollama serve`
- System will use fallback parser if Ollama unavailable

**Index not found:**

- Run `python build_index.py` first

**Data files missing:**

- Ensure `data/indicators.csv` and `data/countries.csv` exist

## Project Structure

```
wb_api/
├── build_index.py      # Step 1: Build search index
├── run_api.py          # Step 2: Run API server
├── requirements.txt    # Dependencies
├── data/
│   ├── indicators.csv
│   └── countries.csv
└── src/
    ├── parser.py       # DSPy + Ollama query parser
    ├── indexer.py      # Embedding/TF-IDF/Lexical search
    ├── resolver.py     # Indicator matching
    ├── catalogs.py     # Data loading
    ├── api_client.py   # World Bank API
    └── query_engine.py # Pipeline orchestrator
```

## How It Works

1. **Parse**: DSPy + Ollama extracts country, concept, year, etc.
2. **Search**: Semantic embedding search finds matching indicators using sentence-transformers
3. **Resolve**: Constraint-based matching picks best indicator
4. **Fetch**: World Bank API call for actual data
5. **Format**: Return structured JSON response

## Notes

- Uses DSPy with Ollama for intelligent parsing
- Falls back to regex-based parsing if Ollama unavailable
- Semantic embedding search provides better accuracy than TF-IDF or lexical search
- Embeddings are generated using `sentence-transformers` (all-MiniLM-L6-v2 model)
- FAISS vector index enables fast similarity search
- Index needs to be rebuilt if indicators.csv changes
