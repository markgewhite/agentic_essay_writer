# Multi-Agent Essay Writer

AI-powered essay writing application using LangGraph's multi-agent architecture with real-time feedback loops.

## Overview

This application uses four specialized AI agents working together to research, plan, write, and refine essays:

- **Planner Agent**: Analyzes topics, develops thesis statements, and creates detailed outlines
- **Researcher Agent**: Gathers web-based research using Tavily search
- **Writer Agent**: Generates and revises essay drafts based on outlines and research
- **Critic Agent**: Evaluates essay quality and provides specific feedback for improvements

The system employs two iterative feedback loops:
1. **Planning Loop**: Planner ↔ Researcher (until sufficient research is gathered)
2. **Writing Loop**: Writer ↔ Critic (until essay meets quality standards)

## Architecture

```
START → Planner → Researcher → [Planning Loop]
                                 ↓ (outline ready)
                              Writer → Critic → [Writing Loop]
                                                   ↓ (approved)
                                                  END
```

Built with:
- **LangGraph**: Multi-agent workflow orchestration
- **Tavily**: Web research and information gathering
- **LangSmith**: Performance monitoring and tracing
- **Streamlit**: Interactive web interface
- **Multiple LLM Providers**: OpenAI, Anthropic, Google

## Features

- 📝 Automated essay research, planning, and writing
- 🔄 Iterative refinement through agent feedback
- 🎯 Separate iteration controls for planning and writing phases
- 📊 Real-time streaming of planner outlines and critic feedback
- 🤖 Support for multiple LLM providers (OpenAI, Anthropic, Google)
- 📥 Download completed essays
- 📈 LangSmith monitoring integration
- ☁️ Ready for deployment on Render.com

## Installation

### Prerequisites

- Python 3.11 or higher
- API keys for:
  - At least one LLM provider (OpenAI, Anthropic, or Google)
  - Tavily (for web research)
  - LangSmith (optional, for monitoring)

### Setup

1. Clone the repository:
```bash
git clone <repository-url>
cd essay_writer
```

2. Create a virtual environment:
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. Install dependencies:
```bash
pip install -r requirements.txt
```

4. Configure environment variables:
```bash
cp .env.example .env
```

5. Edit `.env` and add your API keys:
```bash
# Required
OPENAI_API_KEY=sk-...
TAVILY_API_KEY=tvly-...

# Optional (for other providers)
ANTHROPIC_API_KEY=sk-ant-...
GOOGLE_API_KEY=...

# Optional (for monitoring)
LANGCHAIN_TRACING_V2=true
LANGCHAIN_API_KEY=lsv2_pt_...
LANGCHAIN_PROJECT=essay-writer-dev
```

## Usage

### Running Locally

Start the Streamlit application:
```bash
streamlit run app.py
```

The app will open in your browser at `http://localhost:8501`.

### Using the Application

1. **Configure Settings** (in sidebar):
   - Select model provider (OpenAI, Anthropic, or Google)
   - Choose specific model
   - Set target essay length (500-5000 words)
   - Set max planning iterations (1-5)
   - Set max writing iterations (1-5)

2. **Enter Topic**:
   - Provide a clear, specific essay topic
   - Example: "Analyze the impact of artificial intelligence on modern education systems"

3. **Generate Essay**:
   - Click "Generate Essay" button
   - Watch real-time progress in two columns:
     - Left: Planning & Research updates
     - Right: Writing & Critique updates

4. **Review & Download**:
   - View final essay
   - Download as .txt file

## Project Structure

```
essay_writer/
├── app.py                        # Streamlit interface
├── config/
│   ├── models.py                 # LLM provider configurations
│   └── prompts.py                # System prompts for agents
├── graph/
│   ├── state.py                  # State schema (TypedDict)
│   ├── nodes.py                  # Agent implementations
│   ├── tools.py                  # Tavily integration
│   └── workflow.py               # LangGraph construction
├── utils/
│   └── parsers.py                # Response parsing utilities
├── requirements.txt              # Python dependencies
├── render.yaml                   # Render.com deployment config
├── .env.example                  # Environment template
└── README.md                     # This file
```

## Key Design Decisions

### State Management
- Single comprehensive state object with fields for both loops
- Separate iteration counters for independent loop control
- Boolean completion flags for explicit loop termination
- Dedicated streaming fields for real-time UI updates

### Loop Termination
Multiple safety mechanisms:
- Agent-driven completion (planner/critic decide when done)
- Hard iteration limits (user-configurable)
- Empty query list for planning loop

### Response Parsing
- Text-based parsing with clear format markers
- More robust across different LLM providers than JSON mode
- Regex-based extraction with fallbacks

### Model Provider Abstraction
- Unified `get_llm()` function with provider parameter
- Runtime model switching without code changes
- Easy to add new providers

## Deployment

### Render.com

This application is configured for deployment on Render.com.

1. Push code to GitHub repository

2. Connect repository to Render.com

3. Render will automatically detect `render.yaml` configuration

4. Add environment variables in Render dashboard:
   - `OPENAI_API_KEY` (or ANTHROPIC/GOOGLE)
   - `TAVILY_API_KEY`
   - `LANGCHAIN_API_KEY` (optional)

5. Deploy

The `render.yaml` file configures:
- Python 3.11 environment
- Automatic dependency installation
- Streamlit server on dynamic port
- Environment variable management

## Monitoring with LangSmith

LangSmith provides full visibility into agent interactions:

1. Set environment variables:
```bash
LANGCHAIN_TRACING_V2=true
LANGCHAIN_API_KEY=your_key_here
LANGCHAIN_PROJECT=essay-writer
```

2. View traces at: https://smith.langchain.com/

Traces include:
- Full conversation history for each agent
- Token usage per node
- Latency metrics
- Error tracking
- State inspection at each step

## Development

### Adding New Agents

1. Define agent function in `graph/nodes.py`:
```python
def new_agent_node(state: EssayState) -> dict:
    # Agent logic
    return {"field": value}
```

2. Add node to graph in `graph/workflow.py`:
```python
graph.add_node("new_agent", new_agent_node)
graph.add_edge("previous_node", "new_agent")
```

3. Update state schema in `graph/state.py` if needed

### Adding New LLM Providers

1. Add provider configuration in `config/models.py`:
```python
MODEL_CONFIGS["new_provider"] = {
    "models": ["model-1", "model-2"],
    "default_index": 0
}
```

2. Add provider case in `get_llm()` function
3. Update `.env.example` with new API key

## Troubleshooting

### Common Issues

**"API key not found" error**
- Ensure .env file exists and contains required keys
- Check that .env is in the correct directory
- Verify API keys are valid and active

**"Tavily search failed" error**
- Check TAVILY_API_KEY is set correctly
- Verify internet connection
- Check Tavily API status

**Essay generation stops unexpectedly**
- Check LangSmith traces for errors
- Verify sufficient API credits/quota
- Check for parsing errors in agent responses

**Streamlit not updating in real-time**
- This is expected behavior - updates occur after each node completes
- Not a true token-by-token stream, but node-by-node updates

### Debug Mode

To see detailed logging, set environment variable:
```bash
LANGCHAIN_VERBOSE=true
```

## Contributing

Contributions welcome! Areas for improvement:
- Token-by-token streaming instead of node-by-node
- Additional agent types (fact-checker, citation formatter)
- Support for different essay formats (MLA, APA, Chicago)
- Multi-language support
- PDF export with formatting

## License

MIT License - see LICENSE file for details

## Acknowledgments

Built with:
- [LangGraph](https://github.com/langchain-ai/langgraph) for agent orchestration
- [LangChain](https://github.com/langchain-ai/langchain) for LLM integration
- [Tavily](https://tavily.com/) for web research
- [Streamlit](https://streamlit.io/) for web interface
- [LangSmith](https://smith.langchain.com/) for monitoring

Based on the ReAct agent pattern from the LangGraph documentation.
