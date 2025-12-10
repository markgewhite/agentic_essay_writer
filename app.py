"""
Streamlit web interface for the multi-agent essay writer.

Provides configuration options and real-time streaming of agent progress.
"""

import streamlit as st
from dotenv import load_dotenv
from graph.workflow import create_essay_workflow
from graph.state import create_initial_state
from config.models import AVAILABLE_MODELS, get_model_by_id

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
- **Editor**: Develops thesis and outline, commissions research, reviews critiques and directs revisions
- **Researcher**: Gathers web-based research using Tavily
- **Writer**: Generates and revises essay drafts based on editor direction
- **Critic**: Evaluates quality and provides detailed feedback

The editor orchestrates the entire process, iteratively refining the essay through multiple cycles until high quality is achieved.
""")

# ============================================================================
# SIDEBAR CONFIGURATION
# ============================================================================

with st.sidebar:
    st.header("⚙️ Configuration")

    st.subheader("Model Selection")
    st.caption("Select different models for each agent to optimize cost and performance")

    # Create list of display names and IDs for selectbox
    model_options = [m["display"] for m in AVAILABLE_MODELS]
    model_ids = [m["id"] for m in AVAILABLE_MODELS]

    # Helper to get index by ID
    def get_index_by_id(target_id):
        try:
            return model_ids.index(target_id)
        except ValueError:
            return 0  # Default to first model if not found

    editor_model_id = st.selectbox(
        "Editor Model",
        options=model_ids,
        format_func=lambda x: next(m["display"] for m in AVAILABLE_MODELS if m["id"] == x),
        index=get_index_by_id("gpt-5.1"),  # Default (most intelligent)
        help="Model for developing thesis, outline, and making strategic decisions"
    )

    researcher_model_id = st.selectbox(
        "Researcher Model",
        options=model_ids,
        format_func=lambda x: next(m["display"] for m in AVAILABLE_MODELS if m["id"] == x),
        index=get_index_by_id("gpt-5-nano"),  # Default (cheapest for summarization)
        help="Model for summarizing research results (recommend cheap model - this agent uses many tokens)"
    )

    writer_model_id = st.selectbox(
        "Writer Model",
        options=model_ids,
        format_func=lambda x: next(m["display"] for m in AVAILABLE_MODELS if m["id"] == x),
        index=get_index_by_id("gpt-5-mini"),  # Default (balance of intelligence and cost)
        help="Model for generating and revising essay drafts"
    )

    critic_model_id = st.selectbox(
        "Critic Model",
        options=model_ids,
        format_func=lambda x: next(m["display"] for m in AVAILABLE_MODELS if m["id"] == x),
        index=get_index_by_id("claude-sonnet-4.5"),  # Default (different perspective)
        help="Model for evaluating draft quality and providing feedback"
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
    max_editing = st.slider(
        "Max Editing Iterations",
        min_value=1,
        max_value=10,
        value=5,
        help="Maximum times the editor can request research for the outline"
    )

    max_critique = st.slider(
        "Max Critique Cycles",
        min_value=1,
        max_value=5,
        value=3,
        help="Maximum full cycles through editor review → research/writing → critique"
    )

    max_writing = st.slider(
        "Max Writing Iterations (per cycle)",
        min_value=1,
        max_value=3,
        value=2,
        help="Maximum revisions within a single critique cycle"
    )

    st.divider()
    st.caption("Powered by LangGraph, Tavily & LangSmith")

# ============================================================================
# MAIN CONTENT
# ============================================================================

topic = st.text_area(
    "Essay Topic",
    placeholder="Enter your essay topic or prompt here...\n\nExample: 'Analyze the impact of artificial intelligence on modern education systems'",
    height=120,
    help="Provide a clear, specific topic for the essay"
)

if st.button("Generate Essay", type="primary", disabled=not topic):

    # Create workflow
    try:
        workflow = create_essay_workflow()
    except Exception as e:
        st.error(f"Error creating workflow: {str(e)}")
        st.stop()

    # Convert model IDs to model configs
    editor_model = get_model_by_id(editor_model_id)
    researcher_model = get_model_by_id(researcher_model_id)
    writer_model = get_model_by_id(writer_model_id)
    critic_model = get_model_by_id(critic_model_id)

    # Initialize state using centralized helper function
    initial_state = create_initial_state(
        topic=topic,
        editor_model=editor_model,
        researcher_model=researcher_model,
        writer_model=writer_model,
        critic_model=critic_model,
        max_editing_iterations=max_editing,
        max_critique_iterations=max_critique,
        max_writing_iterations=max_writing,
        max_essay_length=max_length
    )

    # ========================================================================
    # CREATE UI CONTAINERS FOR REAL-TIME UPDATES - 2x2 GRID
    # ========================================================================

    st.header("🔄 Generation Progress")

    # Create 2x2 grid layout
    col1, col2 = st.columns(2)

    # Top row: Outline (left) and Research Highlights (right)
    with col1:
        st.subheader("📋 Outline")
        outline_status = st.empty()
        outline_display = st.container(height=400)

    with col2:
        st.subheader("🔍 Research Highlights")
        research_status = st.empty()
        research_display = st.container(height=400)

    # Bottom row: Draft (left) and Critical Feedback (right)
    col3, col4 = st.columns(2)

    with col3:
        st.subheader("✍️ Draft")
        draft_status = st.empty()
        draft_display = st.container(height=400)

    with col4:
        st.subheader("💭 Critical Feedback")
        feedback_status = st.empty()
        feedback_display = st.container(height=400)

    st.divider()

    final_essay_container = st.empty()

    # ========================================================================
    # STREAM GRAPH EXECUTION
    # ========================================================================

    try:
        # Track the final draft as we stream
        final_draft = None

        # Use workflow.stream() to get intermediate node outputs
        for event in workflow.stream(initial_state):
            # event is a dict with node name as key
            node_name = list(event.keys())[0]
            node_output = event[node_name]

            # ================================================================
            # Panel 1: OUTLINE
            # ================================================================
            if node_name == "editor":
                # Update status based on context
                if "editing_iteration" in node_output:
                    outline_status.info(
                        f"🔄 Editing Iteration: {node_output['editing_iteration']}/{max_editing}"
                    )
                elif "critique_iteration" in node_output:
                    outline_status.info(
                        f"📝 Editor reviewing critique (Cycle {node_output['critique_iteration']}/{max_critique})"
                    )
                else:
                    outline_status.info("🔄 Editor working...")

                # Update outline display if available
                if "current_outline" in node_output and node_output["current_outline"]:
                    with outline_display:
                        st.markdown(node_output["current_outline"])

                # Mark complete if editing is done
                if node_output.get("editing_complete"):
                    outline_status.success("✅ Outline complete - Ready for writing")

                # Show approval status
                if node_output.get("essay_complete"):
                    outline_status.success("✅ Essay approved by editor!")

            # Signal research panel when editor requests research
            if node_name == "editor" and not node_output.get("editing_complete") and node_output.get("draft", "") == "":
                research_status.info("⏳ Waiting for research queries...")

            # ================================================================
            # Panel 2: RESEARCH HIGHLIGHTS
            # ================================================================
            if node_name == "researcher":
                # Update status
                research_status.info("🔍 Gathering research from the web...")

                # Display research highlights using the prepared highlights
                if "current_research_highlights" in node_output and node_output["current_research_highlights"]:
                    with research_display:
                        for i, highlight in enumerate(node_output["current_research_highlights"], 1):
                            st.markdown(f"**Query {i}:** {highlight['query']}")
                            st.text(highlight['preview'])
                            st.markdown("---")

                    research_status.success(f"✅ Research complete - {len(node_output['current_research_highlights'])} results found")

            # Signal when transitioning from research to writing
            if node_name == "researcher" and node_output.get("editing_complete"):
                draft_status.info("⏳ Research complete - Starting draft...")

            # ================================================================
            # Panel 3: DRAFT
            # ================================================================
            if node_name == "writer":
                # Update status
                if "writing_iteration" in node_output and node_output["writing_iteration"] > 0:
                    draft_status.info(
                        f"✍️ Revising (Iteration {node_output['writing_iteration']}/{max_writing})"
                    )
                else:
                    draft_status.info("✍️ Generating draft...")

                # Update draft display if available
                if "current_draft" in node_output and node_output["current_draft"]:
                    final_draft = node_output["current_draft"]
                    with draft_display:
                        st.markdown(node_output["current_draft"])

                # Signal feedback panel that draft is ready
                feedback_status.info("⏳ Draft ready - Awaiting critique...")

                # Mark complete if essay is done
                if node_output.get("essay_complete"):
                    draft_status.success("✅ Draft complete and approved")

            # ================================================================
            # Panel 4: CRITICAL FEEDBACK
            # ================================================================
            if node_name == "critic":
                # Update status
                feedback_status.info("💭 Evaluating draft quality...")

                # Update feedback display if available
                if "current_feedback" in node_output and node_output["current_feedback"]:
                    with feedback_display:
                        st.markdown(node_output["current_feedback"])

                    # Check if essay passed
                    if "essay passed" in node_output["current_feedback"].lower() or "approved" in node_output["current_feedback"].lower():
                        feedback_status.success("✅ Essay approved!")
                    else:
                        feedback_status.warning("⚠️ Revisions requested - Returning to writer...")

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
                st.write(f"**Topic:** {topic}")
                st.write(f"**Target Length:** {max_length} words")
                st.write("**Models Used:**")
                st.write(f"  - Editor: {editor_model['provider'].capitalize()} - {editor_model['name']}")
                st.write(f"  - Researcher: {researcher_model['provider'].capitalize()} - {researcher_model['name']}")
                st.write(f"  - Writer: {writer_model['provider'].capitalize()} - {writer_model['name']}")
                st.write(f"  - Critic: {critic_model['provider'].capitalize()} - {critic_model['name']}")

            # Display the essay
            # Note: We need to track the final draft from the last writer node output
            # This is a simplified version - in production you'd track state properly
            if final_draft:
                st.markdown(final_draft)

                # Download button
                st.download_button(
                    label="📥 Download Essay",
                    data=final_draft,
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
