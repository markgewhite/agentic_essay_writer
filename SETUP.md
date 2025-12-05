# Setup Guide for Multi-Agent Essay Writer

## Quick Start

Follow these steps to get the application running:

### 1. Install Dependencies

Create a virtual environment (recommended):
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

Install required packages:
```bash
pip install -r requirements.txt
```

### 2. Configure Environment Variables

Copy the example environment file:
```bash
cp .env.example .env
```

Edit `.env` and add your API keys:

**Required:**
- `OPENAI_API_KEY` - Get from https://platform.openai.com/api-keys
- `TAVILY_API_KEY` - Get from https://tavily.com/

**Optional (for other providers):**
- `ANTHROPIC_API_KEY` - Get from https://console.anthropic.com/
- `GOOGLE_API_KEY` - Get from https://makersuite.google.com/app/apikey

**Optional (for monitoring):**
- `LANGCHAIN_API_KEY` - Get from https://smith.langchain.com/
- Set `LANGCHAIN_TRACING_V2=true` to enable tracing

### 3. Test the Setup

Run the import test:
```bash
python test_imports.py
```

If all imports succeed, you're ready to go!

### 4. Run the Application

Start the Streamlit app:
```bash
streamlit run app.py
```

The app will open in your browser at `http://localhost:8501`.

## Troubleshooting

### Import Errors

If you see "No module named..." errors:
```bash
pip install --upgrade pip
pip install -r requirements.txt
```

### API Key Errors

If you see "API key not found":
1. Verify `.env` file exists in the project root
2. Check API keys are correctly formatted (no extra spaces or quotes)
3. Ensure you've activated the virtual environment

### Tavily Search Errors

If web searches fail:
1. Verify TAVILY_API_KEY is set
2. Check your Tavily account has available credits
3. Try with a different search query

## Testing the Application

### Simple Test Topic

Try this topic to test the basic workflow:
```
Analyze the benefits and challenges of remote work in modern organizations
```

### Configuration for Testing

Start with conservative settings:
- Model: gpt-4o-mini (faster and cheaper)
- Max Essay Length: 1000 words
- Max Planning Iterations: 2
- Max Writing Iterations: 2

### What to Expect

1. **Planning Phase** (30-60 seconds):
   - Planner analyzes topic
   - Researcher gathers web data
   - Outline appears in left column

2. **Writing Phase** (60-120 seconds):
   - Writer generates draft
   - Critic provides feedback
   - Feedback appears in right column
   - Writer revises (if needed)

3. **Completion**:
   - Final essay displayed
   - Download button available

## Project Structure Overview

```
essay_writer/
├── app.py                     # Streamlit UI - main entry point
├── config/
│   ├── models.py              # LLM provider abstraction
│   └── prompts.py             # Agent system prompts
├── graph/
│   ├── state.py               # State schema
│   ├── nodes.py               # Agent implementations
│   ├── tools.py               # Tavily integration
│   └── workflow.py            # LangGraph construction
├── utils/
│   └── parsers.py             # Response parsing
├── requirements.txt           # Dependencies
├── .env                       # Your API keys (create this)
└── README.md                  # Full documentation
```

## Key Components

### 1. State Management (`graph/state.py`)
Defines the data structure that flows through all agents.

### 2. Agent Nodes (`graph/nodes.py`)
Four agent implementations:
- `planner_node` - Creates thesis and outline
- `researcher_node` - Executes web searches
- `writer_node` - Generates/revises drafts
- `critic_node` - Evaluates and provides feedback

### 3. Workflow (`graph/workflow.py`)
LangGraph configuration with two feedback loops:
- Planning: planner ↔ researcher
- Writing: writer ↔ critic

### 4. Streamlit App (`app.py`)
Web interface with real-time progress updates.

## Development Tips

### Debugging

1. Enable LangSmith tracing (set `LANGCHAIN_TRACING_V2=true`)
2. View full traces at https://smith.langchain.com/
3. Check Streamlit terminal output for errors

### Testing Individual Agents

You can test agents in isolation:

```python
from graph.state import EssayState
from graph.nodes import planner_node
from config.models import get_llm

# Create minimal state
state = {
    "topic": "Test topic",
    "messages": [],
    "planning_iteration": 0,
    "research_results": [],
    "max_planning_iterations": 2,
    "model_provider": "openai",
    "model_name": "gpt-4o-mini"
}

# Test planner
result = planner_node(state)
print(result["outline"])
```

### Customizing Prompts

Edit `config/prompts.py` to adjust agent behavior:
- Make planner more/less detailed
- Adjust critic's standards
- Change writer's style

### Adjusting Iteration Limits

In `app.py`, change slider defaults:
```python
max_planning = st.slider("Max Planning Iterations", 1, 10, 3)  # Changed default to 3
```

## Common Workflows

### Academic Essays
- Max length: 1500-3000 words
- Planning iterations: 2-3 (more research needed)
- Writing iterations: 3-4 (higher quality standards)

### Quick Analyses
- Max length: 500-1000 words
- Planning iterations: 1-2
- Writing iterations: 2-3

### In-Depth Research Papers
- Max length: 3000-5000 words
- Planning iterations: 3-5
- Writing iterations: 4-5

## Next Steps

Once basic setup works:

1. **Try different topics** - Test various complexity levels
2. **Experiment with models** - Compare OpenAI, Anthropic, Google
3. **Adjust iteration limits** - Find optimal settings
4. **Review LangSmith traces** - Understand agent decisions
5. **Deploy to Render** - Make it publicly accessible

## Getting Help

- Check `README.md` for full documentation
- Review LangSmith traces for debugging
- Verify API keys and quotas
- Test with simpler topics if complex ones fail

## Production Deployment

See `README.md` section on Render.com deployment for full instructions.

Quick version:
1. Push code to GitHub
2. Connect to Render.com
3. Add environment variables
4. Deploy (automatic with `render.yaml`)
