import os
import sys

from redis import Redis
from rq import Connection, Queue, Worker


def main() -> None:
    queue_name = os.getenv("QUEUE_NAME") or (sys.argv[1] if len(sys.argv) > 1 else "default")
    redis_url = os.getenv("REDIS_URL", "redis://localhost:6379/0")

    redis_conn = Redis.from_url(redis_url)
    queue = Queue(name=queue_name, connection=redis_conn)

    # TODO: Register worker lifecycle hooks and metrics.
    with Connection(redis_conn):
        worker = Worker([queue])
        worker.work(with_scheduler=False)


if __name__ == "__main__":
    main()
