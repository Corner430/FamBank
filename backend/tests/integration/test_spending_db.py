"""Integration tests for A spending service with DB.

Tests: balance deduction, transaction log creation, overdraft rejection.
Charter reference: §3 (零钱宝使用)
Requires MySQL connection.
"""

import pytest
import pytest_asyncio
from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

import app.models  # noqa: F401 - ensure all models loaded for FK resolution
from app.models.account import Account
from app.models.transaction import TransactionLog
from app.services.spending import spend_from_a


class TestSpendFromA:
    """Test spend_from_a service function."""

    @pytest_asyncio.fixture
    async def funded_a(self, seeded_accounts: AsyncSession):
        """Seed A account with 10000 cents (100 yuan)."""
        await seeded_accounts.execute(
            text("UPDATE account SET balance = 10000 WHERE account_type = 'A'")
        )
        await seeded_accounts.commit()
        return seeded_accounts

    @pytest.mark.asyncio
    async def test_spend_deducts_balance(self, funded_a: AsyncSession):
        """Spending 50 yuan from 100 yuan leaves 50 yuan."""
        result = await spend_from_a(funded_a, 5000, "买文具")
        assert result["balance_before"] == 10000
        assert result["balance_after"] == 5000
        assert result["amount"] == 5000

        # Verify account balance in DB
        acct = await funded_a.execute(
            select(Account).where(Account.account_type == "A")
        )
        account_a = acct.scalar_one()
        assert account_a.balance == 5000

    @pytest.mark.asyncio
    async def test_spend_creates_transaction_log(self, funded_a: AsyncSession):
        """Spending creates a transaction log entry with correct fields."""
        await spend_from_a(funded_a, 3000, "买书")

        txn_result = await funded_a.execute(
            select(TransactionLog).where(TransactionLog.type == "a_spend")
        )
        txn = txn_result.scalar_one()

        assert txn.source_account == "A"
        assert txn.target_account is None
        assert txn.amount == 3000
        assert txn.balance_before == 10000
        assert txn.balance_after == 7000
        assert txn.charter_clause == "第3条"
        assert txn.description == "买书"

    @pytest.mark.asyncio
    async def test_spend_exact_balance(self, funded_a: AsyncSession):
        """Spending exactly the entire balance should succeed."""
        result = await spend_from_a(funded_a, 10000, "全部花光")
        assert result["balance_after"] == 0

        acct = await funded_a.execute(
            select(Account).where(Account.account_type == "A")
        )
        account_a = acct.scalar_one()
        assert account_a.balance == 0

    @pytest.mark.asyncio
    async def test_overdraft_rejected(self, funded_a: AsyncSession):
        """Spending more than balance raises ValueError."""
        with pytest.raises(ValueError, match="余额不足"):
            await spend_from_a(funded_a, 10001, "超支")

    @pytest.mark.asyncio
    async def test_zero_balance_spend_rejected(self, seeded_accounts: AsyncSession):
        """Spending from zero balance raises ValueError."""
        with pytest.raises(ValueError, match="余额不足"):
            await spend_from_a(seeded_accounts, 1, "零余额消费")

    @pytest.mark.asyncio
    async def test_negative_amount_rejected(self, funded_a: AsyncSession):
        """Negative spend amount raises ValueError."""
        with pytest.raises(ValueError, match="正数"):
            await spend_from_a(funded_a, -100, "负数")

    @pytest.mark.asyncio
    async def test_zero_amount_rejected(self, funded_a: AsyncSession):
        """Zero spend amount raises ValueError."""
        with pytest.raises(ValueError, match="正数"):
            await spend_from_a(funded_a, 0, "零元")

    @pytest.mark.asyncio
    async def test_multiple_spends(self, funded_a: AsyncSession):
        """Multiple sequential spends should each deduct correctly."""
        await spend_from_a(funded_a, 3000, "第一笔")
        await spend_from_a(funded_a, 2000, "第二笔")
        result = await spend_from_a(funded_a, 1000, "第三笔")

        assert result["balance_before"] == 5000
        assert result["balance_after"] == 4000

        acct = await funded_a.execute(
            select(Account).where(Account.account_type == "A")
        )
        account_a = acct.scalar_one()
        assert account_a.balance == 4000
