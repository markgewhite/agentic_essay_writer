"""
Streamlit web interface for the multi-agent essay writer.

Provides configuration options and real-time streaming of agent progress.
"""

import streamlit as st
from dotenv import load_dotenv
from graph.workflow import create_essay_workflow
from config.models import MODEL_CONFIGS

# Load environment variables
load_dotenv()

# ============================================================================
# PAGE CONFIGURATION
# ============================================================================

st.set_page_config(
    page_title="AI Essay Writer",
    page_icon="📝",
    layout="wide"
)

st.title("📝 Multi-Agent Essay Writer")
st.markdown("""
This AI-powered essay writer uses multiple specialized agents:
- **Planner**: Develops thesis and outline
- **Researcher**: Gathers web-based research using Tavily
- **Writer**: Generates and revises essay drafts
- **Critic**: Evaluates quality and provides feedback

The system iteratively refines the essay through two feedback loops until high quality is achieved.
""")

# ============================================================================
# SIDEBAR CONFIGURATION
# ============================================================================

with st.sidebar:
    st.header("⚙️ Configuration")

    st.subheader("Model Selection")
    provider = st.selectbox(
        "Model Provider",
        options=list(MODEL_CONFIGS.keys()),
        format_func=lambda x: x.capitalize(),
        help="Choose the LLM provider (requires corresponding API key in .env)"
    )

    model = st.selectbox(
        "Model",
        options=MODEL_CONFIGS[provider]["models"],
        index=MODEL_CONFIGS[provider]["default_index"],
        help="Select the specific model to use"
    )

    st.divider()

    st.subheader("Essay Parameters")
    max_length = st.slider(
        "Max Essay Length (words)",
        min_value=500,
        max_value=5000,
        value=1500,
        step=100,
        help="Target word count for the final essay"
    )

    st.divider()

    st.subheader("Iteration Limits")
    max_planning = st.slider(
        "Max Planning Iterations",
        min_value=1,
        max_value=5,
        value=2,
        help="Maximum times the planner can request more research"
    )

    max_writing = st.slider(
        "Max Writing Iterations",
        min_value=1,
        max_value=5,
        value=3,
        help="Maximum times the writer can revise based on feedback"
    )

    st.divider()
    st.caption("Powered by LangGraph, Tavily & LangSmith")

# ============================================================================
# MAIN CONTENT
# ============================================================================

topic = st.text_area(
    "Essay Topic",
    placeholder="Enter your essay topic or prompt here...\n\nExample: 'Analyze the impact of artificial intelligence on modern education systems'",
    height=100,
    help="Provide a clear, specific topic for the essay"
)

if st.button("Generate Essay", type="primary", disabled=not topic):

    # Create workflow
    try:
        workflow = create_essay_workflow()
    except Exception as e:
        st.error(f"Error creating workflow: {str(e)}")
        st.stop()

    # Initialize state
    initial_state = {
        "messages": [],
        "topic": topic,
        "thesis": "",
        "outline": "",
        "research_queries": [],
        "research_results": [],
        "planning_iteration": 0,
        "planning_complete": False,
        "draft": "",
        "feedback": "",
        "writing_iteration": 0,
        "writing_complete": False,
        "max_planning_iterations": max_planning,
        "max_writing_iterations": max_writing,
        "max_essay_length": max_length,
        "model_provider": provider,
        "model_name": model,
        "current_outline": "",
        "current_feedback": ""
    }

    # ========================================================================
    # CREATE UI CONTAINERS FOR REAL-TIME UPDATES
    # ========================================================================

    st.header("🔄 Generation Progress")

    col1, col2 = st.columns(2)

    with col1:
        st.subheader("📋 Planning & Research")
        planning_status = st.empty()
        outline_display = st.empty()

    with col2:
        st.subheader("✍️ Writing & Critique")
        writing_status = st.empty()
        feedback_display = st.empty()

    st.divider()

    final_essay_container = st.empty()

    # ========================================================================
    # STREAM GRAPH EXECUTION
    # ========================================================================

    try:
        # Use workflow.stream() to get intermediate node outputs
        for event in workflow.stream(initial_state):
            # event is a dict with node name as key
            node_name = list(event.keys())[0]
            node_output = event[node_name]

            # Update planning section
            if node_name in ["planner", "researcher"]:
                # Update outline display if available
                if "current_outline" in node_output and node_output["current_outline"]:
                    with outline_display.container():
                        st.markdown("**Current Outline:**")
                        st.markdown(node_output["current_outline"])

                # Update iteration counter
                if "planning_iteration" in node_output:
                    planning_status.info(
                        f"📍 Planning Iteration: {node_output['planning_iteration']}/{max_planning}"
                    )

                # Show when researcher is working
                if node_name == "researcher":
                    planning_status.info("🔍 Researcher gathering web data...")

            # Update writing section
            if node_name in ["writer", "critic"]:
                # Update feedback display if available
                if "current_feedback" in node_output and node_output["current_feedback"]:
                    with feedback_display.container():
                        st.markdown("**Critic Feedback:**")
                        st.markdown(node_output["current_feedback"])

                # Update iteration counter
                if "writing_iteration" in node_output:
                    writing_status.info(
                        f"📍 Writing Iteration: {node_output['writing_iteration']}/{max_writing}"
                    )

                # Show when writer is working
                if node_name == "writer":
                    writing_status.info("✍️ Writer generating/revising draft...")

        # ====================================================================
        # DISPLAY FINAL ESSAY
        # ====================================================================

        # Get final state (note: stream doesn't return final state, so we need to track it)
        # For now, we'll extract from the last event
        # In production, you might want to use workflow.get_state() if available

        st.success("✅ Essay Complete!")

        with final_essay_container:
            st.header("📄 Final Essay")

            # Metadata expander
            with st.expander("📊 Generation Metadata", expanded=False):
                # Note: These values would come from final state
                # For now, showing placeholders
                st.write(f"**Topic:** {topic}")
                st.write(f"**Model:** {provider.capitalize()} - {model}")
                st.write(f"**Target Length:** {max_length} words")

            # Display the essay
            # Note: We need to track the final draft from the last writer node output
            # This is a simplified version - in production you'd track state properly
            if "draft" in node_output:
                st.markdown(node_output["draft"])

                # Download button
                st.download_button(
                    label="📥 Download Essay",
                    data=node_output["draft"],
                    file_name=f"essay_{topic[:30].replace(' ', '_')}.txt",
                    mime="text/plain"
                )
            else:
                st.warning("Draft not available in final output. This may indicate an error in the workflow.")

    except Exception as e:
        st.error(f"❌ Error during generation: {str(e)}")
        st.exception(e)

# ============================================================================
# FOOTER
# ============================================================================

st.divider()
st.markdown("""
**How it works:**
1. **Planning Phase**: The planner analyzes your topic and requests research
2. **Research Phase**: The researcher gathers information from the web using Tavily
3. **Writing Phase**: The writer creates a draft based on the outline and research
4. **Critique Phase**: The critic evaluates the draft and provides feedback
5. **Iteration**: Steps 3-4 repeat until the essay meets quality standards

*Tip: Use specific, focused topics for best results. Vague topics may produce generic essays.*
""")
