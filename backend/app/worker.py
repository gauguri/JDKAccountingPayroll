"""Background worker placeholder.

MVP 1 has no background jobs yet. This keeps the worker container alive so the
compose stack is stable; later phases (OCR, large imports, scheduled CPA
exports) will add real job handling here.
"""
import time


def main():
    print("[worker] JDK Books worker started — idle (no jobs in MVP 1).", flush=True)
    while True:
        time.sleep(60)


if __name__ == "__main__":
    main()
