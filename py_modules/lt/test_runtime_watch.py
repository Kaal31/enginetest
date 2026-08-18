import os
import tempfile
import threading
import time
import unittest

from .runtime_watch import DirectoryWatcher


class RuntimeWatchTests(unittest.TestCase):
    def test_directory_watcher_observes_atomic_replace(self):
        with tempfile.TemporaryDirectory() as d:
            seen = []
            event = threading.Event()

            def callback(path):
                seen.append(os.path.basename(path))
                event.set()

            watcher = DirectoryWatcher(d, callback)
            self.assertTrue(watcher.start())
            try:
                tmp = os.path.join(d, "keys.txt.tmp")
                final = os.path.join(d, "keys.txt")
                with open(tmp, "w", encoding="utf-8") as f:
                    f.write("test")
                os.replace(tmp, final)
                self.assertTrue(event.wait(2.0), "inotify event was not observed")
                self.assertIn("keys.txt", seen)
            finally:
                watcher.stop()


if __name__ == "__main__":
    unittest.main()
