"""Entrada ASGI para a Vercel (e `uvicorn api.index:app`): só reexporta o app de api/main.py."""
from api.main import app

__all__ = ["app"]
