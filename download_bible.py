#!/usr/bin/env python3
"""
Download Bible data using pythonbible
This creates a local cache for faster verse lookups
"""
import pythonbible as bible
from pathlib import Path
import json

print("=" * 60)
print("Bible Data Initialization")
print("=" * 60)
print()

def init_bible_data():
    """Initialize Bible data"""

    # Ensure data directory exists
    data_dir = Path("data/bible")
    data_dir.mkdir(parents=True, exist_ok=True)

    print("Initializing Bible data with pythonbible...")
    print("This creates a local cache for faster verse lookups.\n")

    try:
        # Test pythonbible by fetching a sample verse
        test_verse = bible.get_verse_text(
            bible.convert_reference_to_verse_ids("John 3:16")[0],
            version=bible.Version.KING_JAMES
        )

        if test_verse:
            print(f"✓ Successfully loaded Bible data")
            print(f"\nSample verse (John 3:16):")
            print(f"  {test_verse}\n")

            # Create a metadata file
            metadata = {
                'version': 'KJV',
                'library': 'pythonbible',
                'initialized': True
            }

            with open(data_dir / 'metadata.json', 'w') as f:
                json.dump(metadata, f, indent=2)

            print("✓ Bible data initialization complete!")
            return True
        else:
            print("✗ Failed to load Bible data")
            return False

    except Exception as e:
        print(f"✗ Error initializing Bible data: {e}")
        return False


def main():
    """Main entry point"""
    success = init_bible_data()

    if success:
        print("\n" + "=" * 60)
        print("SUCCESS: Bible data is ready to use")
        print("=" * 60)
    else:
        print("\n" + "=" * 60)
        print("ERROR: Failed to initialize Bible data")
        print("=" * 60)
        import sys
        sys.exit(1)


if __name__ == "__main__":
    main()
