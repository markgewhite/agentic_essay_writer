"""
Streamlit web interface for the multi-agent essay writer.

Provides configuration options and real-time streaming of agent progress.
"""

import streamlit as st
from datetime import datetime
from dotenv import load_dotenv
from graph.workflow import create_essay_workflow
from graph.state import create_initial_state
from config.models import AVAILABLE_MODELS, get_model_by_id

# Load environment variables
load_dotenv()

# ============================================================================
# HELPER FUNCTIONS FOR EXECUTION TRACKING
# ============================================================================

def create_execution_entry(execution_id: int, agent: str, iteration_num: int,
                          user_prompt: str, response: str) -> dict:
    """Create a standardized execution history entry for the timeline UI."""
    agent_display_names = {
        "editor": "Editor",
        "researcher": "Researcher",
        "writer": "Writer",
        "critic": "Critic"
    }

    return {
        "id": execution_id,
        "agent": agent,
        "status": "complete",
        "timestamp": datetime.now().isoformat(),
        "iteration_context": f"{agent_display_names.get(agent, agent)} #{iteration_num}",
        "model_input": user_prompt,      # Only user message (not system)
        "model_output": response,
        "parsed_output": {}
    }

def count_agent_executions(history: list, agent: str) -> int:
    """Count how many times an agent has executed in the history."""
    return sum(1 for entry in history if entry["agent"] == agent) + 1

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
# MAIN CONTENT: Topic Input (left) + Final Essay Placeholder (right)
# ============================================================================

# Create top row layout BEFORE button
top_col1, top_col2 = st.columns([1, 2])

with top_col1:
    st.markdown("### 📝 Essay Topic")
    topic = st.text_area(
        "Essay Topic",
        placeholder="Enter your essay topic or prompt here...\n\nExample: 'Analyze the impact of artificial intelligence on modern education systems'",
        help="Provide a clear, specific topic for the essay",
        label_visibility="collapsed"
    )

with top_col2:
    st.markdown("### 📄 Final Essay")
    final_essay_placeholder = st.empty()
    # Initially show dark grey placeholder
    with final_essay_placeholder.container():
        st.markdown(
            '<div style="background-color: #262730; padding: 20px; border-radius: 5px; color: #a0a0a0; text-align: center; border: 1px solid #404040; height: 150px; display: flex; align-items: center; justify-content: center;">Essay will appear here when complete...</div>',
            unsafe_allow_html=True
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

    # Initialize session state for UI tracking
    if "selected_execution_id" not in st.session_state:
        st.session_state.selected_execution_id = -1
    if "current_execution_history" not in st.session_state:
        st.session_state.current_execution_history = []

    # Reset execution history for new generation
    st.session_state.current_execution_history = []
    st.session_state.selected_execution_id = -1

    # ========================================================================
    # CREATE UI CONTAINERS FOR TIMELINE LAYOUT
    # ========================================================================

    st.divider()
    st.header("🔄 Generation Progress")

    # Status indicator for current activity
    current_status = st.empty()
    current_status.info("🚀 Starting workflow...")

    # ========================================================================
    # MAIN CONTENT: Timeline (left) + Details (right)
    # ========================================================================
    main_col1, main_col2 = st.columns([1, 2])

    # ------------------------------------------------------------------------
    # LEFT COLUMN: Progress Timeline
    # ------------------------------------------------------------------------
    with main_col1:
        st.subheader("🕒 Progress Timeline")
        timeline_container = st.empty()

    # ------------------------------------------------------------------------
    # RIGHT COLUMN: Execution Details (3 sections stacked)
    # ------------------------------------------------------------------------
    with main_col2:
        # Status Panel (top)
        st.subheader("📊 Status")
        status_display = st.empty()

        # Model Input Panel (middle)
        st.subheader("📥 Model Input")
        input_display = st.empty()

        # Model Output Panel (bottom)
        st.subheader("📤 Model Output")
        output_display = st.empty()

    # ========================================================================
    # STREAM GRAPH EXECUTION
    # ========================================================================

    try:
        # Track the final draft as we stream
        final_draft = None
        essay_complete = False

        # Agent icons mapping
        agent_icons = {
            "editor": "✏️",
            "researcher": "🔍",
            "writer": "✍️",
            "critic": "💭"
        }

        # Use workflow.stream() for reliable Streamlit compatibility
        for event in workflow.stream(initial_state):
            # event is a dict with node name as key
            node_name = list(event.keys())[0]
            node_output = event[node_name]

            # Update status to show which agent just completed
            agent_name_display = {
                "editor": "Editor",
                "researcher": "Researcher",
                "writer": "Writer",
                "critic": "Critic"
            }
            icon = agent_icons.get(node_name, "⚙️")
            current_status.success(f"{icon} {agent_name_display.get(node_name, node_name)} completed")

            # ================================================================
            # CAPTURE EXECUTION DATA FROM UI FIELDS
            # ================================================================
            ui_prompt = node_output.get("_ui_prompt", "")
            ui_response = node_output.get("_ui_response", "")

            # Only capture if fields have actual values (not empty strings)
            if ui_prompt and ui_response:
                execution_id = len(st.session_state.current_execution_history)
                iteration_num = count_agent_executions(
                    st.session_state.current_execution_history,
                    node_name
                )

                entry = create_execution_entry(
                    execution_id=execution_id,
                    agent=node_name,
                    iteration_num=iteration_num,
                    user_prompt=ui_prompt,
                    response=ui_response
                )

                st.session_state.current_execution_history.append(entry)
                st.session_state.selected_execution_id = execution_id  # Auto-select latest

            # ================================================================
            # RENDER TIMELINE (clickable buttons)
            # ================================================================
            with timeline_container.container():
                if st.session_state.current_execution_history:
                    # Display timeline with clickable buttons
                    for entry in st.session_state.current_execution_history:
                        icon = agent_icons.get(entry['agent'], '⚙️')
                        label = f"{icon} {entry['iteration_context']} - {entry['status'].upper()}"

                        # Use columns to create button with colored background
                        col = st.columns(1)[0]
                        with col:
                            # Highlight the selected/latest entry
                            if entry['id'] == st.session_state.selected_execution_id:
                                st.success(f"**{label}**")
                            else:
                                # Create clickable button
                                if st.button(label, key=f"timeline_btn_{entry['id']}", use_container_width=True):
                                    st.session_state.selected_execution_id = entry['id']
                                    st.rerun()
                else:
                    st.info("No executions yet. Workflow starting...")

            # ================================================================
            # RENDER DETAIL PANELS BASED ON SELECTION
            # ================================================================
            if st.session_state.selected_execution_id >= 0 and st.session_state.current_execution_history:
                # Find entry by ID, not by index (safer)
                selected_entry = next(
                    (entry for entry in st.session_state.current_execution_history
                     if entry['id'] == st.session_state.selected_execution_id),
                    None
                )

                if not selected_entry:
                    # Fallback to last entry if ID not found
                    selected_entry = st.session_state.current_execution_history[-1] if st.session_state.current_execution_history else None

                if selected_entry:
                    # Status panel
                    with status_display.container():
                        timestamp_formatted = datetime.fromisoformat(selected_entry['timestamp']).strftime('%H:%M:%S')
                        st.info(
                            f"{agent_icons.get(selected_entry['agent'], '⚙️')} "
                            f"{selected_entry['iteration_context']} | "
                            f"Status: {selected_entry['status'].upper()} | "
                            f"Time: {timestamp_formatted}"
                        )

                    # Input panel
                    with input_display.container():
                        st.markdown(
                            f'<div style="background-color: #1e1e1e; color: white; padding: 15px; border-radius: 5px; height: 375px; overflow-y: auto; white-space: pre-wrap; border: 1px solid #404040;">{selected_entry["model_input"]}</div>',
                            unsafe_allow_html=True
                        )

                    # Output panel
                    with output_display.container():
                        st.markdown(
                            f'<div style="background-color: #1e1e1e; color: white; padding: 15px; border-radius: 5px; height: 375px; overflow-y: auto; white-space: pre-wrap; border: 1px solid #404040;">{selected_entry["model_output"]}</div>',
                            unsafe_allow_html=True
                        )

            # ================================================================
            # TRACK FINAL DRAFT AND ESSAY COMPLETION
            # ================================================================
            if node_name == "writer" and "current_draft" in node_output:
                final_draft = node_output["current_draft"]

            if node_name == "editor" and node_output.get("essay_complete"):
                essay_complete = True
                current_status.success("✅ Essay approved! Workflow complete.")
            else:
                # Predict next agent and update status
                if node_name == "editor":
                    if node_output.get("draft", "") == "":
                        # Initial editing phase
                        if node_output.get("editing_complete"):
                            current_status.info("✍️ Writer starting draft...")
                        else:
                            current_status.info("🔍 Researcher gathering information...")
                    else:
                        # After critique review
                        decision = node_output.get("editor_decision", "revise")
                        if decision == "research":
                            current_status.info("🔍 Researcher gathering additional information...")
                        else:
                            current_status.info("✍️ Writer revising draft...")
                elif node_name == "researcher":
                    current_status.info("✏️ Editor reviewing research...")
                elif node_name == "writer":
                    current_status.info("💭 Critic evaluating draft...")
                elif node_name == "critic":
                    current_status.info("✏️ Editor reviewing feedback...")

        # ====================================================================
        # UPDATE FINAL ESSAY DISPLAY WHEN COMPLETE
        # ====================================================================
        if essay_complete:
            # Get the latest draft from session state or track it
            # The final draft should be the last one written
            if not final_draft and st.session_state.current_execution_history:
                # Find the most recent writer execution
                for entry in reversed(st.session_state.current_execution_history):
                    if entry['agent'] == 'writer':
                        final_draft = entry['model_output']
                        break

            if final_draft:
                with final_essay_placeholder.container():
                    st.success("✅ Essay Complete!")

                    # Top row: Metadata expander (left) + Download button (right)
                    meta_col1, meta_col2 = st.columns([3, 1])

                    with meta_col1:
                        # Metadata expander
                        with st.expander("📊 Generation Metadata", expanded=False):
                            st.write(f"**Topic:** {topic}")
                            st.write(f"**Target Length:** {max_length} words")
                            st.write("**Models Used:**")
                            st.write(f"  - Editor: {editor_model['provider'].capitalize()} - {editor_model['name']}")
                            st.write(f"  - Researcher: {researcher_model['provider'].capitalize()} - {researcher_model['name']}")
                            st.write(f"  - Writer: {writer_model['provider'].capitalize()} - {writer_model['name']}")
                            st.write(f"  - Critic: {critic_model['provider'].capitalize()} - {critic_model['name']}")

                    with meta_col2:
                        # Download button
                        st.download_button(
                            label="📥 Download",
                            data=final_draft,
                            file_name=f"essay_{topic[:30].replace(' ', '_')}.txt",
                            mime="text/plain",
                            use_container_width=True
                        )

                    # Display the essay with dark grey background
                    st.markdown(
                        '<div style="background-color: #262730; padding: 20px; border-radius: 5px; border: 1px solid #404040;">',
                        unsafe_allow_html=True
                    )
                    st.markdown(final_draft)
                    st.markdown('</div>', unsafe_allow_html=True)
            else:
                with final_essay_placeholder.container():
                    st.warning("Essay approved but draft not found. Please check the execution history for the latest writer output.")

    except Exception as e:
        st.error(f"❌ Error during generation: {str(e)}")
        st.exception(e)

# ============================================================================
# PERSISTENT TIMELINE VIEW (after workflow completes)
# ============================================================================
# If there's execution history, render it outside the button handler
# This allows interaction after the workflow finishes
if "current_execution_history" in st.session_state and st.session_state.current_execution_history:
    st.divider()
    st.header("📜 Execution History")

    agent_icons = {
        "editor": "✏️",
        "researcher": "🔍",
        "writer": "✍️",
        "critic": "💭"
    }

    view_col1, view_col2 = st.columns([1, 2])

    # Timeline
    with view_col1:
        st.subheader("🕒 Timeline")
        for entry in st.session_state.current_execution_history:
            icon = agent_icons.get(entry['agent'], '⚙️')
            label = f"{icon} {entry['iteration_context']}"

            # Highlight the selected entry
            if entry['id'] == st.session_state.selected_execution_id:
                st.success(f"**{label}**")
            else:
                # Clickable button
                if st.button(label, key=f"history_btn_{entry['id']}", use_container_width=True):
                    st.session_state.selected_execution_id = entry['id']
                    st.rerun()

    # Detail panels
    with view_col2:
        if st.session_state.selected_execution_id >= 0:
            # Find entry by ID, not by index (safer)
            selected_entry = next(
                (entry for entry in st.session_state.current_execution_history
                 if entry['id'] == st.session_state.selected_execution_id),
                None
            )

            if not selected_entry and st.session_state.current_execution_history:
                # Fallback to last entry if ID not found
                selected_entry = st.session_state.current_execution_history[-1]

            if selected_entry:
                # Status
                st.subheader("📊 Status")
                timestamp_formatted = datetime.fromisoformat(selected_entry['timestamp']).strftime('%H:%M:%S')
                st.info(
                    f"{agent_icons.get(selected_entry['agent'], '⚙️')} "
                    f"{selected_entry['iteration_context']} | "
                    f"Status: {selected_entry['status'].upper()} | "
                    f"Time: {timestamp_formatted}"
                )

                # Input
                st.subheader("📥 Model Input")
                st.markdown(
                    f'<div style="background-color: #1e1e1e; color: white; padding: 15px; border-radius: 5px; height: 375px; overflow-y: auto; white-space: pre-wrap; border: 1px solid #404040;">{selected_entry["model_input"]}</div>',
                    unsafe_allow_html=True
                )

                # Output
                st.subheader("📤 Model Output")
                st.markdown(
                    f'<div style="background-color: #1e1e1e; color: white; padding: 15px; border-radius: 5px; height: 375px; overflow-y: auto; white-space: pre-wrap; border: 1px solid #404040;">{selected_entry["model_output"]}</div>',
                    unsafe_allow_html=True
                )

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
