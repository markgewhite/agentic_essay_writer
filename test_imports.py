"""
Simple test script to verify all imports work correctly.
Run this before starting the application to catch any import errors.
"""

print("Testing imports...")

try:
    print("✓ Importing graph.state...")
    from graph.state import EssayState

    print("✓ Importing config.models...")
    from config.models import MODEL_CONFIGS, get_llm

    print("✓ Importing config.prompts...")
    from config.prompts import PLANNER_PROMPT, WRITER_PROMPT, CRITIC_PROMPT

    print("✓ Importing utils.parsers...")
    from utils.parsers import parse_planner_response, parse_critic_response, estimate_word_count

    print("✓ Importing graph.tools...")
    from graph.tools import create_tavily_tool, format_research_results, summarize_research

    print("✓ Importing graph.nodes...")
    from graph.nodes import planner_node, researcher_node, writer_node, critic_node

    print("✓ Importing graph.workflow...")
    from graph.workflow import create_essay_workflow

    print("\n✅ All imports successful!")
    print("\nAvailable model providers:")
    for provider, config in MODEL_CONFIGS.items():
        print(f"  - {provider.capitalize()}: {', '.join(config['models'])}")

    print("\nNext steps:")
    print("1. Copy .env.example to .env")
    print("2. Add your API keys to .env")
    print("3. Run: streamlit run app.py")

except ImportError as e:
    print(f"\n❌ Import error: {e}")
    print("Make sure all dependencies are installed: pip install -r requirements.txt")
except Exception as e:
    print(f"\n❌ Error: {e}")
