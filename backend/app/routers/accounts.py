"""Accounts CRUD router."""

import uuid

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.logging_config import get_logger
from app.models.account import Account
from app.models.transaction import Transaction
from app.schemas.finance.account import AccountCreate, AccountResponse, AccountUpdate
from app.services.recurring_sync import process_recurring

logger = get_logger(__name__)
router = APIRouter(prefix="/api/accounts", tags=["accounts"])


@router.get("", response_model=list[AccountResponse])
async def list_accounts(db: AsyncSession = Depends(get_db)) -> list[Account]:
    await process_recurring(db)
    result = await db.execute(select(Account))
    return list(result.scalars().all())


@router.post("", response_model=AccountResponse, status_code=201)
async def create_account(
    body: AccountCreate,
    db: AsyncSession = Depends(get_db),
) -> Account:
    account = Account(**body.model_dump())
    db.add(account)
    await db.flush()
    logger.info("Created account %s (%s)", account.name, account.type.value)
    return account


@router.get("/{account_id}", response_model=AccountResponse)
async def get_account(
    account_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
) -> Account:
    account = await db.get(Account, account_id)
    if not account:
        raise HTTPException(status_code=404, detail="Account not found")
    return account


@router.put("/{account_id}", response_model=AccountResponse)
async def update_account(
    account_id: uuid.UUID,
    body: AccountUpdate,
    db: AsyncSession = Depends(get_db),
) -> Account:
    account = await db.get(Account, account_id)
    if not account:
        raise HTTPException(status_code=404, detail="Account not found")
    for field, value in body.model_dump(exclude_unset=True).items():
        setattr(account, field, value)
    await db.flush()
    await db.refresh(account)
    logger.info("Updated account %s", account_id)
    return account


@router.delete("/{account_id}")
async def delete_account(
    account_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
) -> dict[str, bool]:
    account = await db.get(Account, account_id)
    if not account:
        raise HTTPException(status_code=404, detail="Account not found")
    # Nullify toAccountId on transfers pointing to this account
    await db.execute(
        update(Transaction)
        .where(Transaction.to_account_id == account_id)
        .values(to_account_id=None)
    )
    await db.delete(account)
    await db.flush()
    logger.info("Deleted account %s", account_id)
    return {"success": True}
