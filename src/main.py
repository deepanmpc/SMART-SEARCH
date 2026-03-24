import sys
from crawler import crawl_directory
from extractor import extract_any_document
from FileName import init_db, insert_file

FOLDER = "/Users/deepandee/Desktop/od_alms"

def run_indexing(folder):
    conn = init_db()

    files = crawl_directory(folder)
    print(f"Found {len(files)} files")

    for file_meta in files:
        print(f"Processing: {file_meta['path']}")

        extraction_result = extract_any_document(file_meta["path"])
        if extraction_result.get("success"):
            file_meta["content"] = extraction_result.get("text", "")
        else:
            file_meta["content"] = ""
            print(f"Extraction failed for {file_meta['path']}: {extraction_result.get('error')}")

        insert_file(conn, file_meta)

    print("Indexing complete.")

if __name__ == "__main__":
    folder_to_index = sys.argv[1] if len(sys.argv) > 1 else FOLDER
    run_indexing(folder_to_index)