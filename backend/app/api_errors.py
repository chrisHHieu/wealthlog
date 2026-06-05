"""Shared HTTP error helpers for consistent API responses."""

from fastapi import HTTPException


def not_found(resource: str) -> HTTPException:
    return HTTPException(status_code=404, detail=f"{resource} not found")


def validation_error(message: str) -> HTTPException:
    return HTTPException(status_code=422, detail=message)


def bad_request(message: str) -> HTTPException:
    return HTTPException(status_code=400, detail=message)
