"""
Debug script for testing the essay workflow without Streamlit.

Run this script directly in PyCharm debugger to step through the workflow execution.
Set breakpoints anywhere to inspect state and node outputs.
"""

from dotenv import load_dotenv
from graph.workflow import create_essay_workflow
from graph.state import create_initial_state
from config.models import get_model_by_id

# Load environment variables
load_dotenv()


def main():
    """Run the workflow with a test topic and print progress."""

    # Test configuration
    test_topic = "Analyze the impact of artificial intelligence on modern education systems"

    print("=" * 80)
    print("ESSAY WORKFLOW DEBUG SESSION")
    print("=" * 80)
    print(f"\nTopic: {test_topic}\n")

    # Create workflow
    print("Creating workflow...")
    try:
        workflow = create_essay_workflow()
        print("✓ Workflow created successfully\n")
    except Exception as e:
        print(f"✗ Error creating workflow: {e}")
        return

    # Configure models for each agent
    # Tip: Use cheaper models (gpt-4o-mini) for researcher to reduce costs
    editor_model = get_model_by_id("gpt-5.1"),  # Default (most intelligent)
    researcher_model = get_model_by_id("gpt-5-nano"),  # Default (cheapest for summarization)
    writer_model = get_model_by_id("gpt-5-mini"),  # Default (balance of intelligence and cost)
    critic_model = get_model_by_id("claude-sonnet-4-5-latest"),  # Default (different perspective)

    # Initialize state using centralized helper function
    initial_state = create_initial_state(
        topic=test_topic,
        editor_model=editor_model,
        researcher_model=researcher_model,
        writer_model=writer_model,
        critic_model=critic_model,
        max_editing_iterations=2,
        max_critique_iterations=2,
        max_writing_iterations=2,
        max_essay_length=1500
    )

    print("Initial State:")
    print(f"  - Max editing iterations: {initial_state['max_editing_iterations']}")
    print(f"  - Max critique cycles: {initial_state['max_critique_iterations']}")
    print(f"  - Max writing iterations: {initial_state['max_writing_iterations']}")
    print(f"  - Editor model: {initial_state['editor_model']['provider']} - {initial_state['editor_model']['name']}")
    print(f"  - Researcher model: {initial_state['researcher_model']['provider']} - {initial_state['researcher_model']['name']}")
    print(f"  - Writer model: {initial_state['writer_model']['provider']} - {initial_state['writer_model']['name']}")
    print(f"  - Critic model: {initial_state['critic_model']['provider']} - {initial_state['critic_model']['name']}")
    print(f"  - Target length: {initial_state['max_essay_length']} words\n")

    # Track the final draft
    final_draft = None
    final_state = None

    # Stream through the workflow
    print("Starting workflow execution...")
    print("-" * 80)

    try:
        event_count = 0
        for event in workflow.stream(initial_state):
            event_count += 1

            # Extract node name and output
            node_name = list(event.keys())[0]
            node_output = event[node_name]

            print(f"\n[Event {event_count}] Node: {node_name}")
            print("-" * 40)

            # Display relevant information based on node type
            if node_name == "editor":
                print(f"Editing Iteration: {node_output.get('editing_iteration', 'N/A')}")
                print(f"Editing Complete: {node_output.get('editing_complete', 'N/A')}")
                print(f"Critique Iteration: {node_output.get('critique_iteration', 'N/A')}")
                print(f"Essay Complete: {node_output.get('essay_complete', 'N/A')}")
                print(f"Editor Decision: {node_output.get('editor_decision', 'N/A')}")
                if node_output.get('current_outline'):
                    print(f"Outline Preview: {node_output['current_outline'][:200]}...")
                if node_output.get('research_queries'):
                    print(f"Research Queries: {node_output['research_queries']}")
                if node_output.get('editor_direction'):
                    print(f"Direction to Writer: {node_output['editor_direction'][:150]}...")

            elif node_name == "researcher":
                print(f"Research Results Count: {len(node_output.get('research_results', []))}")
                if node_output.get('research_results'):
                    print(f"Latest Research: {len(node_output['research_results'][-1])} characters")

            elif node_name == "writer":
                print(f"Writing Iteration: {node_output.get('writing_iteration', 'N/A')}")
                if node_output.get('draft'):
                    draft_preview = node_output['draft'][:200].replace('\n', ' ')
                    print(f"Draft Preview: {draft_preview}...")
                    print(f"Draft Length: {len(node_output['draft'])} characters")
                    # Track the final draft
                    final_draft = node_output['draft']

            elif node_name == "critic":
                print(f"Critique Iteration: {node_output.get('critique_iteration', 'N/A')}")
                print(f"Essay Complete: {node_output.get('essay_complete', 'N/A')}")
                if node_output.get('current_feedback'):
                    feedback_preview = node_output['current_feedback'][:200].replace('\n', ' ')
                    print(f"Feedback Preview: {feedback_preview}...")

            # Store the latest state
            final_state = node_output

            # SET BREAKPOINT HERE to inspect node_output and state
            # You can examine all values in the debugger
            pass  # <-- Good place for a breakpoint

        print("\n" + "=" * 80)
        print("WORKFLOW COMPLETE")
        print("=" * 80)

        # Display final results
        if final_draft:
            print(f"\n✓ Final Draft Available ({len(final_draft)} characters)")
            print("\nFinal Essay:")
            print("-" * 80)
            print(final_draft)
            print("-" * 80)
        else:
            print("\n✗ No final draft available!")

        if final_state:
            print("\nFinal State Summary:")
            print(f"  - Editing iterations completed: {final_state.get('editing_iteration', 'N/A')}")
            print(f"  - Critique cycles completed: {final_state.get('critique_iteration', 'N/A')}")
            print(f"  - Writing iterations completed: {final_state.get('writing_iteration', 'N/A')}")
            print(f"  - Editing complete: {final_state.get('editing_complete', 'N/A')}")
            print(f"  - Essay complete: {final_state.get('essay_complete', 'N/A')}")

    except Exception as e:
        print(f"\n✗ Error during workflow execution: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()
