#!/usr/bin/env python3
import sys
import logging
from pathlib import Path
from src.catalogs import load_catalogs
from src.indexer import IndicatorIndex

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(message)s', datefmt='%H:%M:%S')

def main():
    indicators_file = "data/indicators.csv"
    output_dir = "indices/index"

    print("\n" + "=" * 60)
    print("Building search index...")
    print("=" * 60)

    if not Path(indicators_file).exists():
        print(f"Error: {indicators_file} not found")
        sys.exit(1)

    logging.info("Loading indicators...")
    ind_df, _, _ = load_catalogs(indicators_path=indicators_file)
    logging.info(f"Loaded {len(ind_df)} indicators")

    logging.info("Building embedding index...")
    index = IndicatorIndex()
    index.build(ind_df)

    logging.info(f"Saving to {output_dir}...")
    index.save(output_dir)

    print("\n" + "=" * 60)
    print("Done!")
    print(f"Index saved to: {output_dir}")
    print(f"Documents indexed: {len(index.docs)}")
    print("\nNext: python run_api.py")
    print("=" * 60 + "\n")

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\nCancelled")
        sys.exit(0)
    except Exception as e:
        print(f"\nError: {e}")
        sys.exit(1)
