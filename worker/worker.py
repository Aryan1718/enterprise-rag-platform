import os
import sys

from redis import Redis
from rq import Connection, Queue, Worker


def main() -> None:
    queue_arg = os.getenv("QUEUE_NAME") or (sys.argv[1] if len(sys.argv) > 1 else "default")
    redis_url = os.getenv("REDIS_URL", "redis://localhost:6379/0")
    queue_names = [name.strip() for name in queue_arg.split(",") if name.strip()]
    if not queue_names:
        queue_names = ["default"]

    redis_conn = Redis.from_url(redis_url)
    queues = [Queue(name=queue_name, connection=redis_conn) for queue_name in queue_names]

    # TODO: Register worker lifecycle hooks and metrics.
    with Connection(redis_conn):
        worker = Worker(queues)
        worker.work(with_scheduler=False)


if __name__ == "__main__":
    main()
