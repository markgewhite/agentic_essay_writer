"""
Debug script for testing the essay workflow without Streamlit.

Run this script directly in PyCharm debugger to step through the workflow execution.
Set breakpoints anywhere to inspect state and node outputs.
"""

from dotenv import load_dotenv
from graph.workflow import create_essay_workflow

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

    # Initialize state
    initial_state = {
        "messages": [],
        "topic": test_topic,
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
        "max_planning_iterations": 2,
        "max_writing_iterations": 2,
        "max_essay_length": 1500,
        "model_provider": "openai",  # Change to your preferred provider
        "model_name": "gpt-4o-mini",  # Change to your preferred model
        "current_outline": "",
        "current_feedback": ""
    }

    print("Initial State:")
    print(f"  - Max planning iterations: {initial_state['max_planning_iterations']}")
    print(f"  - Max writing iterations: {initial_state['max_writing_iterations']}")
    print(f"  - Model: {initial_state['model_provider']} - {initial_state['model_name']}")
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
            if node_name == "planner":
                print(f"Planning Iteration: {node_output.get('planning_iteration', 'N/A')}")
                print(f"Planning Complete: {node_output.get('planning_complete', 'N/A')}")
                if node_output.get('current_outline'):
                    print(f"Outline Preview: {node_output['current_outline'][:200]}...")
                if node_output.get('research_queries'):
                    print(f"Research Queries: {node_output['research_queries']}")

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
                print(f"Writing Iteration: {node_output.get('writing_iteration', 'N/A')}")
                print(f"Writing Complete: {node_output.get('writing_complete', 'N/A')}")
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
            print(f"  - Planning iterations completed: {final_state.get('planning_iteration', 'N/A')}")
            print(f"  - Writing iterations completed: {final_state.get('writing_iteration', 'N/A')}")
            print(f"  - Planning complete: {final_state.get('planning_complete', 'N/A')}")
            print(f"  - Writing complete: {final_state.get('writing_complete', 'N/A')}")

    except Exception as e:
        print(f"\n✗ Error during workflow execution: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()
