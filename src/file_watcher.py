import time
import threading
import os
from pathlib import Path
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler

from database.metadata_store import init_db, get_all_watched_folders, clear_document
from crawler import SUPPORTED_EXTENSIONS as SUPPORTED

class DebouncedWatcher(FileSystemEventHandler):
    def __init__(self, index_callback, debounce_seconds=5):
        self.index_callback = index_callback
        self.debounce_seconds = debounce_seconds
        self.pending_files = set()
        self.pending_deletions = set()
        self.timer = None
        self.lock = threading.Lock()

    def on_created(self, event):
        if not event.is_directory:
            self._handle_change(event.src_path)

    def on_modified(self, event):
        if not event.is_directory:
            self._handle_change(event.src_path)

    def on_deleted(self, event):
        if not event.is_directory:
            self._handle_delete(event.src_path)

    def on_moved(self, event):
        if not event.is_directory:
            self._handle_delete(event.src_path)
            self._handle_change(event.dest_path)

    def _handle_change(self, path):
        if Path(path).suffix.lower() in SUPPORTED:
            with self.lock:
                self.pending_files.add(path)
                if path in self.pending_deletions:
                    self.pending_deletions.remove(path)
                self._reset_timer()

    def _handle_delete(self, path):
        with self.lock:
            self.pending_deletions.add(path)
            if path in self.pending_files:
                self.pending_files.remove(path)
            self._reset_timer()

    def _reset_timer(self):
        if self.timer:
            self.timer.cancel()
        self.timer = threading.Timer(self.debounce_seconds, self._process_events)
        self.timer.daemon = True
        self.timer.start()

    def _process_events(self):
        with self.lock:
            to_index = list(self.pending_files)
            to_delete = list(self.pending_deletions)
            self.pending_files.clear()
            self.pending_deletions.clear()
        
        if to_index or to_delete:
            self.index_callback(to_index, to_delete)

def start_watcher(db_path, index_callback):
    conn = init_db(db_path)
    try:
        folders = get_all_watched_folders(conn)
    finally:
        conn.close()

    if not folders:
        print("Watcher: No folders to watch.")
        return None

    print(f"Watcher: Starting observer for folders: {folders}")
    observer = Observer()
    event_handler = DebouncedWatcher(index_callback)
    scheduled_paths = 0
    
    for folder in folders:
        if not os.path.isdir(folder):
            print(f"Watcher: Folder does not exist, skipping: {folder}")
            continue
        try:
            print(f"Watcher: Scheduling watch for {folder}")
            observer.schedule(event_handler, folder, recursive=True)
            scheduled_paths += 1
        except Exception as e:
            print(f"Watcher: Failed to watch {folder}: {e}")

    if scheduled_paths == 0:
        print("Watcher: No valid folders could be scheduled.")
        return None
    
    try:
        observer.start()
    except Exception as e:
        print(f"Watcher: Failed to start observer: {e}")
        return None
    return observer
