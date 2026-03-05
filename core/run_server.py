from __future__ import annotations

import os

import uvicorn


def main() -> None:
    host = os.getenv("IA_OFFLINE_HOST", "127.0.0.1")
    port = int(os.getenv("IA_OFFLINE_PORT", "8000"))
    uvicorn.run("app.main:app", host=host, port=port, reload=False)


if __name__ == "__main__":
    main()
