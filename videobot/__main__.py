"""CLI:
  python -m videobot add "Docker kya hai"      queue a topic
  python -m videobot ideas 10                  let AI fill the queue
  python -m videobot make                      make the next video (no upload)
  python -m videobot run                       make + upload one now
  python -m videobot upload <id>               upload an already-made video
  python -m videobot approve <id>              post it on Facebook (after you checked it)
  python -m videobot list                      queue + videos
  python -m videobot schedule                  run forever on SCHEDULE_DAYS/SCHEDULE_HOUR_PKT
"""
import sys

from . import ai, pipeline, store


def main(argv):
    if not argv or argv[0] in ("-h", "--help", "help"):
        print(__doc__)
        return 0
    cmd, args = argv[0], argv[1:]
    if cmd == "add":
        print(f"Added {store.add_topics([' '.join(args)])} topic.")
    elif cmd == "ideas":
        n = store.add_topics(ai.suggest_topics(int(args[0]) if args else 10, store.all_topics()))
        print(f"Added {n} topics.")
    elif cmd == "make":
        pipeline.make_one()
    elif cmd == "run":
        return 0 if pipeline.run_once() else 1
    elif cmd == "upload":
        pipeline.upload(int(args[0]))
    elif cmd == "approve":
        pipeline.approve(int(args[0]))
    elif cmd == "list":
        print("Queue:")
        for r in store.db().execute("SELECT id, topic, status FROM topics ORDER BY id DESC LIMIT 20"):
            print(f"  [{r['status']}] {r['topic']}")
        print("Videos:")
        for v in store.videos(20):
            print(f"  #{v['id']} {v['status']:<9} yt={v['yt_id'] or '-'} fb={v['fb_id'] or '-'}  {v['title']}  {v['error'] or ''}")
    elif cmd == "schedule":
        pipeline.scheduler()
    else:
        print(__doc__)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
