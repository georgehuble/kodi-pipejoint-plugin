# -*- coding: utf-8 -*-
"""Desktop check for the xbmc-free history collections (watch + search).

No Kodi and no network needed: everything runs against a temp directory, so
dedup, ordering, capping and the resume position are verified deterministically.
Usage:  python3 tests/test_history_store_desktop.py
"""

import json
import os
import shutil
import sys
import tempfile

sys.path.insert(0, os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "resources", "lib"))

import store  # noqa: E402

failures = []


def check(name, ok, detail=""):
    print("  [%s] %s%s" % ("OK" if ok else "FAIL", name,
                           (" - %s" % detail) if detail else ""))
    if not ok:
        failures.append(name)


def write(path, text):
    with open(path, "w", encoding="utf-8") as stream:
        stream.write(text)


def main():
    root = tempfile.mkdtemp(prefix="pipejoint-history-")
    try:
        # --- 1.1 watch history --------------------------------------------------
        print("=== 1.1 missing file starts empty ===")
        fresh = store.WatchHistoryStore(os.path.join(root, "fresh"))
        check("missing file -> empty list", fresh.list() == [], repr(fresh.list()))
        check("missing video -> nothing found", fresh.find("vid1") is None)
        check("read does not create the file", not os.path.exists(fresh.path),
              fresh.path)

        print("=== 1.1 recording adds a video at the top ===")
        db_dir = os.path.join(root, "history")
        watch = store.WatchHistoryStore(db_dir)
        check("record returns True",
              watch.record("vid1", "First video", url="https://y/vid1",
                           thumbnail="https://t/1.png", duration=120) is True)
        entries = watch.list()
        check("one entry stored", len(entries) == 1, repr(entries))
        entry = entries[0]
        check("fields round-trip",
              entry["video_id"] == "vid1" and entry["title"] == "First video"
              and entry["url"] == "https://y/vid1"
              and entry["thumbnail"] == "https://t/1.png"
              and entry["duration"] == 120.0, repr(entry))
        check("fresh entry has no position", entry["position"] is None, repr(entry))
        check("timestamp recorded", entry["timestamp"] > 0, repr(entry))
        check("file written", os.path.exists(watch.path), watch.path)
        check("entry is findable",
              (watch.find("vid1") or {}).get("title") == "First video")

        print("=== 1.1 rewatch moves to the top without duplicating ===")
        watch.record("vid2", "Second video")
        watch.record("vid3", "Third video")
        watch.record("vid1", "First video (renamed)")
        check("newest first order",
              [e["video_id"] for e in watch.list()] == ["vid1", "vid3", "vid2"],
              repr([e["video_id"] for e in watch.list()]))
        check("no duplicate after a rewatch", len(watch.list()) == 3,
              repr(watch.list()))
        check("refreshed title kept",
              watch.find("vid1")["title"] == "First video (renamed)")

        print("=== 1.1 persistence across instances ===")
        reopened = store.WatchHistoryStore(db_dir)
        check("entries survive a reopen",
              [e["video_id"] for e in reopened.list()] == ["vid1", "vid3", "vid2"],
              repr([e["video_id"] for e in reopened.list()]))
        check("fields survive a reopen",
              reopened.find("vid3")["title"] == "Third video")

        print("=== 1.1 tolerant reads ===")
        corrupt = store.WatchHistoryStore(os.path.join(root, "corrupt"))
        os.makedirs(os.path.dirname(corrupt.path), exist_ok=True)
        write(corrupt.path, "{not json at all")
        check("corrupt JSON -> empty list", corrupt.list() == [])
        write(corrupt.path, json.dumps([1, "x", None]))
        check("wrong top-level shape -> empty list", corrupt.list() == [])
        write(corrupt.path, json.dumps(
            {"watch": [None, "x", {"title": "no id"}, {"video_id": "vidOk"}]}))
        check("bad entries dropped, good kept",
              [e["video_id"] for e in corrupt.list()] == ["vidOk"],
              repr(corrupt.list()))

        # --- 1.2 resume position ------------------------------------------------
        print("=== 1.2 set_position updates the stored entry ===")
        check("set_position returns True", watch.set_position("vid3", 75) is True)
        check("position stored", watch.find("vid3")["position"] == 75.0,
              repr(watch.find("vid3")))
        check("other entries untouched", watch.find("vid1")["position"] is None)
        check("position persists",
              store.WatchHistoryStore(db_dir).find("vid3")["position"] == 75.0)
        check("unknown video is not created",
              watch.set_position("nope", 10) is False and watch.find("nope") is None)
        check("garbage position ignored",
              watch.set_position("vid3", "later") is False
              and watch.find("vid3")["position"] == 75.0)
        check("negative position ignored",
              watch.set_position("vid3", -5) is False
              and watch.find("vid3")["position"] == 75.0)

        print("=== 1.2 rewatch keeps the position until stop updates it ===")
        watch.record("vid3", "Third video")
        check("position survives re-recording", watch.find("vid3")["position"] == 75.0,
              repr(watch.find("vid3")))
        check("rewatch moved it to the top", watch.list()[0]["video_id"] == "vid3",
              repr(watch.list()))
        check("an explicit position overrides",
              watch.record("vid3", "Third video", position=0) is True
              and watch.find("vid3")["position"] == 0.0)

        print("=== 1.2 remove / clear ===")
        check("remove returns True", watch.remove("vid2") is True)
        check("removed entry is gone", watch.find("vid2") is None)
        check("others remain",
              [e["video_id"] for e in watch.list()] == ["vid3", "vid1"],
              repr([e["video_id"] for e in watch.list()]))
        check("removing again is harmless", watch.remove("vid2") is True)
        check("clear empties the history", watch.clear() is True and watch.list() == [],
              repr(watch.list()))
        check("cleared history persists",
              store.WatchHistoryStore(db_dir).list() == [])

        # --- 1.3 search history -------------------------------------------------
        print("=== 1.3 recording queries ===")
        search_dir = os.path.join(root, "search")
        search = store.SearchHistoryStore(search_dir)
        check("empty file -> no queries", search.list_queries() == [])
        check("record_query returns True", search.record_query("kodi tips") is True)
        search.record_query("linux")
        search.record_query("python")
        check("newest first", search.list_queries() == ["python", "linux", "kodi tips"],
              repr(search.list_queries()))
        check("blank query ignored", search.record_query("   ") is False)
        check("None query ignored", search.record_query(None) is False)
        check("queries persist",
              store.SearchHistoryStore(search_dir).list_queries() ==
              ["python", "linux", "kodi tips"])

        print("=== 1.3 repeating a query moves it to the top ===")
        search.record_query("kodi tips")
        check("repeat moved to the top",
              search.list_queries() == ["kodi tips", "python", "linux"],
              repr(search.list_queries()))
        check("no duplicate", len(search.list_queries()) == 3,
              repr(search.list_queries()))

        print("=== 1.3 the list is capped, oldest dropped ===")
        capped = store.SearchHistoryStore(os.path.join(root, "capped"))
        for index in range(store.SEARCH_HISTORY_LIMIT + 5):
            capped.record_query("query %02d" % index)
        queries = capped.list_queries()
        check("cap respected", len(queries) == store.SEARCH_HISTORY_LIMIT,
              "%d entries" % len(queries))
        check("newest kept at the top",
              queries[0] == "query %02d" % (store.SEARCH_HISTORY_LIMIT + 4), queries[0])
        check("oldest dropped", "query 00" not in queries and "query 04" not in queries,
              repr(queries[-3:]))

        print("=== 1.3 remove / clear ===")
        check("remove_query returns True", search.remove_query("python") is True)
        check("removed query is gone", "python" not in search.list_queries())
        check("others remain", search.list_queries() == ["kodi tips", "linux"],
              repr(search.list_queries()))
        check("removing again is harmless", search.remove_query("python") is True)
        check("clear_queries empties the list",
              search.clear_queries() is True and search.list_queries() == [])
        check("cleared queries persist",
              store.SearchHistoryStore(search_dir).list_queries() == [])

        print("=== 1.3 both collections share the file without clobbering ===")
        shared_dir = os.path.join(root, "shared")
        shared_watch = store.WatchHistoryStore(shared_dir)
        shared_search = store.SearchHistoryStore(shared_dir)
        shared_watch.record("vid1", "Video one")
        shared_search.record_query("kodi")
        check("watch keeps its entry after a search write",
              [e["video_id"] for e in shared_watch.list()] == ["vid1"],
              repr(shared_watch.list()))
        check("search keeps its query after a watch write",
              shared_search.list_queries() == ["kodi"],
              repr(shared_search.list_queries()))
        shared_watch.record("vid2", "Video two")
        check("both collections readable from the same file",
              store.WatchHistoryStore(shared_dir).find("vid1") is not None
              and store.SearchHistoryStore(shared_dir).list_queries() == ["kodi"])

        print("=== no directory configured ===")
        empty_watch = store.WatchHistoryStore("")
        empty_search = store.SearchHistoryStore("")
        check("watch: empty list, no crash",
              empty_watch.list() == [] and empty_watch.find("vid1") is None)
        check("watch: writes fail cleanly", empty_watch.record("vid1", "x") is False)
        check("watch: position write fails cleanly",
              empty_watch.set_position("vid1", 10) is False)
        check("search: empty list, no crash", empty_search.list_queries() == [])
        check("search: writes fail cleanly", empty_search.record_query("x") is False)
    finally:
        shutil.rmtree(root, ignore_errors=True)

    if failures:
        print("RESULT: FAIL (%d check(s): %s)" % (len(failures), ", ".join(failures)))
        sys.exit(1)
    print("RESULT: OK (history collections dedupe, order, cap and persist)")


if __name__ == "__main__":
    main()
