# %% imports
import json
import sys
import tempfile

from config import generate_session_id, langfuse_client
from pipeline import build_pipeline

# %% config — flip this to switch between sample and real data
USE_SAMPLE_DATA = False


# %% main
def main():
    if USE_SAMPLE_DATA:
        from _sample import SAMPLE_TXNS

        tmp = tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False)
        json.dump(SAMPLE_TXNS, tmp)
        tmp.close()
        dataset_path = tmp.name
        print(f"Using sample data ({len(SAMPLE_TXNS)} txns)")
    else:
        # Accepts a directory (with transactions + supplementary files)
        # or a single transactions file path
        dataset_path = (
            sys.argv[1]
            if len(sys.argv) > 1
            else "challenges/2. Brave New World - train"
        )
        print(f"Using dataset: {dataset_path}")

    session_id = generate_session_id()
    print(f"Session: {session_id}")

    pipeline = build_pipeline()
    result = pipeline.invoke({"dataset_path": dataset_path, "session_id": session_id})

    with open("output.txt", "w") as f:
        for txn_id in result["fraud_ids"]:
            f.write(f"{txn_id}\n")

    with open("debug.json", "w") as f:
        json.dump(result.get("debug_output", []), f, indent=2, default=str)

    # Log a summary generation to Langfuse so the platform finds the session
    from langchain_openai import ChatOpenAI
    from langchain_core.messages import HumanMessage
    from config import OPENROUTER_API_KEY
    from config.models import LLM_BASE_URL, SPEED_MODEL
    from config.tracing import get_langfuse_callback

    summary_llm = ChatOpenAI(
        model=SPEED_MODEL,
        base_url=LLM_BASE_URL,
        api_key=OPENROUTER_API_KEY or "ollama",
        temperature=0.0,
        max_tokens=100,
    )
    summary_llm.invoke(
        [HumanMessage(content=f"Fraud detection complete. {len(result['fraud_ids'])} of {len(result.get('transactions', []))} transactions flagged.")],
        config={
            "callbacks": [get_langfuse_callback()],
            "metadata": {"langfuse_session_id": session_id},
        },
    )

    langfuse_client.flush()

    print(f"Found {len(result['fraud_ids'])} fraudulent transactions")
    print(f"Debug: debug.json ({len(result.get('debug_output', []))} entries)")
    print(f"Langfuse session: {session_id}")


# %% entrypoint
if __name__ == "__main__":
    main()
