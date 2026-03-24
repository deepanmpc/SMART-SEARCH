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

        file_path = file_meta["path"]
        filename = file_path.split("/")[-1]

        print(f"Processing: {file_path}")

        extraction_result = extract_any_document(file_path)

        if not extraction_result.get("success"):

            print(f"Extraction failed for {file_path}: {extraction_result.get('error')}")
            continue

        chunks = extraction_result.get("chunks", [])

        print(f"Inserted {len(chunks)} chunks")

        for chunk in chunks:

            record = {
                "path": file_path,
                "filename": filename,
                "content": chunk,
                "type": file_meta["type"],
                "modified": file_meta["modified"]
            }

            insert_file(conn, record)

    print("Indexing complete.")


if __name__ == "__main__":

    folder_to_index = sys.argv[1] if len(sys.argv) > 1 else FOLDER
    run_indexing(folder_to_index)