import sys

from pipeline import build_pipeline


def main():
    pipeline = build_pipeline()
    result = pipeline.invoke({"dataset_path": sys.argv[1]})

    with open("output.txt", "w") as f:
        for txn_id in result["fraud_ids"]:
            f.write(f"{txn_id}\n")

    print(f"Found {len(result['fraud_ids'])} fraudulent transactions")


if __name__ == "__main__":
    main()
