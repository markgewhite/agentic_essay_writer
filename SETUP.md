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
- **Editor Model**: GPT-5 Mini (faster and cheaper for testing)
- **Researcher Model**: GPT-5 Nano (cheapest option)
- **Writer Model**: GPT-5 Mini (balanced)
- **Critic Model**: GPT-5 Mini (or Claude Haiku for different perspective)
- **Max Essay Length**: 1000 words
- **Max Editing Iterations**: 3
- **Max Critique Cycles**: 2
- **Max Writing Iterations**: 2
- **Max Queries per Research Request**: 2
- **Max Results per Query**: 3

### What to Expect

1. **Editing Phase** (30-90 seconds):
   - Editor develops thesis and outline
   - Editor commissions research queries
   - Researcher gathers web data
   - Timeline shows Editor and Researcher entries
   - Process repeats until outline is complete

2. **Writing & Critique Phase** (60-120 seconds):
   - Writer generates initial draft
   - Critic evaluates quality and provides feedback
   - Editor reviews feedback and decides next step
   - Timeline shows Writer, Critic, and Editor entries
   - May loop through research → writing → critique as needed

3. **Completion**:
   - Final essay displayed in top-right panel
   - Timeline shows complete execution history
   - Click any timeline entry to view that agent's work
   - Download button available for final essay

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
- `editor_node` - Develops thesis/outline, commissions research, reviews critiques, directs revisions
- `researcher_node` - Executes web searches with configurable query/result limits
- `writer_node` - Generates/revises drafts based on editor direction
- `critic_node` - Evaluates quality and provides detailed feedback

### 3. Workflow (`graph/workflow.py`)
LangGraph configuration with editor-orchestrated routing:
- Editing phase: editor ↔ researcher (outline development)
- Critique phase: writer → critic → editor → (research/revise/approve)

### 4. Streamlit App (`app.py`)
Web interface with interactive timeline and execution history tracking.

## Development Tips

### Debugging

1. Enable LangSmith tracing (set `LANGCHAIN_TRACING_V2=true`)
2. View full traces at https://smith.langchain.com/
3. Check Streamlit terminal output for errors

### Testing Individual Agents

You can test agents in isolation:

```python
from graph.state import create_initial_state
from graph.nodes import editor_node
from config.models import get_model_by_id

# Create initial state with per-agent models
state = create_initial_state(
    topic="Test topic",
    editor_model=get_model_by_id("gpt-5.1"),
    researcher_model=get_model_by_id("gpt-5-nano"),
    writer_model=get_model_by_id("gpt-5-mini"),
    critic_model=get_model_by_id("claude-sonnet-4.5"),
    max_editing_iterations=2,
    max_critique_iterations=2,
    max_writing_iterations=2,
    max_essay_length=1500,
    max_queries=3,
    max_results_per_query=5
)

# Test editor
result = editor_node(state)
print(result["outline"])
```

### Customizing Prompts

Edit `config/prompts.py` to adjust agent behavior:
- Make planner more/less detailed
- Adjust critic's standards
- Change writer's style

### Adjusting Parameters

In `app.py`, change slider defaults and ranges:
```python
max_editing = st.slider("Max Editing Iterations", min_value=2, max_value=12, value=5)
max_queries = st.slider("Max Queries per Research Request", min_value=1, max_value=5, value=3)
```

## Common Workflows

### Academic Essays
- Max length: 1500-3000 words
- Max editing iterations: 4-6 (comprehensive outline development)
- Max critique cycles: 3-4 (higher quality standards)
- Max writing iterations: 3-4 (detailed revisions)
- Max queries per request: 3-4
- Max results per query: 5-7

### Quick Analyses
- Max length: 500-1000 words
- Max editing iterations: 2-3
- Max critique cycles: 2
- Max writing iterations: 2-3
- Max queries per request: 2-3
- Max results per query: 3-5

### In-Depth Research Papers
- Max length: 3000-5000 words
- Max editing iterations: 6-8 (extensive research needed)
- Max critique cycles: 4-5 (very high quality standards)
- Max writing iterations: 4-5 (thorough revisions)
- Max queries per request: 4-5
- Max results per query: 7-10

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
