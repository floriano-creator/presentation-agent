# AI Presentation Agent

Production-ready MVP backend that generates PowerPoint presentations from minimal user input.

## Setup

```bash
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

## Configuration

Create a `.env` file in the project root:

```
OPENAI_API_KEY=your-openai-api-key
UNSPLASH_ACCESS_KEY=your-unsplash-access-key
```

Optional: `OPENAI_MODEL` (default: gpt-4o), `UNSPLASH_BASE_URL`

## Usage

```bash
python main.py --topic "Introduction to Machine Learning" --duration 15 --audience "Technical team" --language "English" -o presentation.pptx
```

### Parameters

| Parameter | Required | Description |
|-----------|----------|-------------|
| `--topic` | Yes | Presentation topic |
| `--duration` | No | Duration in minutes (default: 10) |
| `--audience` | No | Target audience (default: General audience) |
| `--language` | No | Presentation language (default: English) |
| `--output`, `-o` | No | Output path for .pptx (default: temp file) |

## Programmatic Usage

```python
from presentation_agent import PresentationAgent
from presentation_agent.config import Config
from presentation_agent.models import UserInput

config = Config.from_env()
agent = PresentationAgent(config)

user_input = UserInput(
    topic="Climate Change Overview",
    duration_minutes=10,
    audience="Students",
    language="German",
)

import asyncio
result = asyncio.run(agent.generate(user_input, output_path="output.pptx"))
print(f"Saved to {result.output_path}, {result.slide_count} slides, {result.images_included} images")
```

## Pipeline

1. **Outline** – Generate structure from topic, duration, audience
2. **Script** – Expand to slide-level content (titles, bullets, speaker notes)
3. **Slides** – Add image search queries per slide
4. **Images** – Fetch from Unsplash API
5. **Export** – Create PowerPoint with python-pptx

## Project Structure

```
presentation_agent/
    agent.py          # Orchestrator
    config.py         # Environment config
    models.py         # Pydantic models
    llm_client.py     # OpenAI client
    outline_generator.py
    script_generator.py
    slide_generator.py
    image_service.py  # Unsplash
    ppt_exporter.py
    main.py           # CLI entry point
```
