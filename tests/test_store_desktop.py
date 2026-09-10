# -*- coding: utf-8 -*-
"""Desktop check for the xbmc-free JSON store / subscriptions repository.

No Kodi and no network needed: everything runs against a temp directory.
Usage:  python3 tests/test_store_desktop.py
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
    root = tempfile.mkdtemp(prefix="pipejoint-store-")
    try:
        # --- 1.1 tolerant reads -------------------------------------------------
        print("=== missing file starts empty ===")
        fresh_dir = os.path.join(root, "fresh")
        subs = store.SubscriptionStore(fresh_dir)
        check("missing file -> empty list", subs.list() == [], repr(subs.list()))
        check("missing file -> nothing subscribed", subs.is_subscribed("UC1") is False)
        check("read does not create the file", not os.path.exists(subs.path),
              subs.path)

        print("=== corrupt file does not crash ===")
        corrupt_dir = os.path.join(root, "corrupt")
        os.makedirs(corrupt_dir, exist_ok=True)
        corrupt = store.SubscriptionStore(corrupt_dir)
        write(corrupt.path, "{not json at all")
        check("corrupt JSON -> empty list", corrupt.list() == [])
        write(corrupt.path, "")
        check("empty file -> empty list", corrupt.list() == [])
        write(corrupt.path, json.dumps({"channel_id": "UC1"}))
        check("wrong top-level shape -> empty list", corrupt.list() == [])
        write(corrupt.path, json.dumps([1, "x", {"name": "no id"}, None,
                                        {"channel_id": "UCok", "name": "Kept"}]))
        check("bad entries dropped, good kept",
              corrupt.list() == [{"channel_id": "UCok", "name": "Kept"}],
              repr(corrupt.list()))

        print("=== directory is created on write ===")
        nested = os.path.join(root, "a", "b", "addon_data")
        created = store.SubscriptionStore(nested)
        check("ensure_directory creates the path",
              created.ensure_directory() and os.path.isdir(nested), nested)

        # --- 1.2 subscribe / unsubscribe / list ---------------------------------
        print("=== subscribe / unsubscribe / list ===")
        db_dir = os.path.join(root, "subs")
        db = store.SubscriptionStore(db_dir)
        check("subscribe returns True", db.subscribe("UC1", "Channel One") is True)
        check("channel is subscribed", db.is_subscribed("UC1") is True)
        check("file exists after write", os.path.exists(db.path), db.path)
        check("unrelated channel not subscribed", db.is_subscribed("UC9") is False)

        print("=== duplicate subscribe -> single entry ===")
        db.subscribe("UC1", "Channel One (renamed)")
        entries = db.list()
        check("one entry after subscribing twice", len(entries) == 1, repr(entries))
        check("existing name refreshed",
              entries and entries[0]["name"] == "Channel One (renamed)",
              repr(entries))

        print("=== newest first ===")
        db.subscribe("UC2", "Channel Two")
        db.subscribe("UC3", "Channel Three")
        check("newest first order",
              [s["channel_id"] for s in db.list()] == ["UC3", "UC2", "UC1"],
              repr([s["channel_id"] for s in db.list()]))

        print("=== persistence across instances ===")
        reopened = store.SubscriptionStore(db_dir)
        check("stored channels survive a reopen",
              [s["channel_id"] for s in reopened.list()] == ["UC3", "UC2", "UC1"])
        check("names survive a reopen",
              reopened.list()[0]["name"] == "Channel Three")

        print("=== unsubscribe ===")
        check("unsubscribe returns True", db.unsubscribe("UC2") is True)
        check("removed channel is gone", db.is_subscribed("UC2") is False)
        check("others untouched",
              [s["channel_id"] for s in db.list()] == ["UC3", "UC1"],
              repr(db.list()))
        check("unsubscribing again is harmless", db.unsubscribe("UC2") is True)
        check("re-subscribing after unsubscribe works",
              db.subscribe("UC2", "Channel Two") is True and db.is_subscribed("UC2"))

        print("=== no directory configured ===")
        empty = store.SubscriptionStore("")
        check("empty directory -> empty list, no crash",
              empty.list() == [] and empty.is_subscribed("UC1") is False)
        check("write without a directory fails cleanly",
              empty.subscribe("UC1", "x") is False)
    finally:
        shutil.rmtree(root, ignore_errors=True)

    if failures:
        print("RESULT: FAIL (%d check(s): %s)" % (len(failures), ", ".join(failures)))
        sys.exit(1)
    print("RESULT: OK (store loads safely and subscriptions dedupe/round-trip)")


if __name__ == "__main__":
    main()
