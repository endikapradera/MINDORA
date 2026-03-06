from __future__ import annotations

import os

import uvicorn


def main() -> None:
    os.environ.setdefault("OMP_NUM_THREADS", "1")
    os.environ.setdefault("KMP_DUPLICATE_LIB_OK", "TRUE")
    os.environ.setdefault("MKL_SERVICE_FORCE_INTEL", "1")
    host = os.getenv("IA_OFFLINE_HOST", "127.0.0.1")
    port = int(os.getenv("IA_OFFLINE_PORT", "8000"))
    uvicorn.run("app.main:app", host=host, port=port, reload=False)


if __name__ == "__main__":
    main()
