"""Integration tests for violation processing with DB.

Tests: penalty transfer, escalation, violation record creation.
Charter reference: §7 (违约处理)
Requires MySQL connection.
"""

import pytest
import pytest_asyncio
from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

import app.models  # noqa: F401 - ensure all models loaded for FK resolution
from app.models.account import Account
from app.models.violation import Violation
from app.services.violation import process_violation


class TestProcessViolation:
    """Integration tests for process_violation with DB."""

    @pytest_asyncio.fixture
    async def accounts_with_pool(self, seeded_accounts: AsyncSession):
        """Seed B interest_pool = 100000 (1000 yuan), C balance = 50000."""
        await seeded_accounts.execute(
            text(
                "UPDATE account SET interest_pool = 100000 "
                "WHERE account_type = 'B'"
            )
        )
        await seeded_accounts.execute(
            text(
                "UPDATE account SET balance = 50000 "
                "WHERE account_type = 'C'"
            )
        )
        await seeded_accounts.commit()
        return seeded_accounts

    @pytest.mark.asyncio
    async def test_penalty_transfer(self, accounts_with_pool: AsyncSession):
        """Penalty transferred from B pool to C."""
        session = accounts_with_pool
        result = await process_violation(session, 20000, 0, "违规消费", family_id=1, user_id=2)

        # penalty = min(100000, 40000) = 40000
        assert result["penalty"] == 40000
        assert result["b_interest_pool_before"] == 100000
        assert result["b_interest_pool_after"] == 60000
        assert result["c_balance_before"] == 50000
        assert result["c_balance_after"] == 90000

    @pytest.mark.asyncio
    async def test_pool_less_than_2x_violation(self, seeded_accounts: AsyncSession):
        """When pool < 2*violation, entire pool is transferred."""
        session = seeded_accounts
        # Set B pool = 30000, C = 0
        await session.execute(
            text("UPDATE account SET interest_pool = 30000 WHERE account_type = 'B'")
        )
        await session.execute(
            text("UPDATE account SET balance = 0 WHERE account_type = 'C'")
        )
        await session.commit()

        result = await process_violation(session, 20000, 0, "违规", family_id=1, user_id=2)

        # penalty = min(30000, 40000) = 30000
        assert result["penalty"] == 30000
        assert result["b_interest_pool_after"] == 0
        assert result["c_balance_after"] == 30000

    @pytest.mark.asyncio
    async def test_pool_zero(self, seeded_accounts: AsyncSession):
        """When pool = 0, no penalty transferred."""
        session = seeded_accounts
        result = await process_violation(session, 20000, 0, "违规", family_id=1, user_id=2)

        assert result["penalty"] == 0
        assert result["b_interest_pool_after"] == 0
        assert result["c_balance_after"] == 0

    @pytest.mark.asyncio
    async def test_violation_record_created(self, accounts_with_pool: AsyncSession):
        """A Violation record is created in the database."""
        session = accounts_with_pool
        result = await process_violation(session, 20000, 5000, "测试违规", family_id=1, user_id=2)
        await session.flush()

        v_result = await session.execute(
            select(Violation).where(Violation.id == result["violation_id"])
        )
        violation = v_result.scalar_one()

        assert violation.violation_amount == 20000
        assert violation.penalty_amount == 40000
        assert violation.amount_entered_a == 5000
        assert violation.description == "测试违规"

    @pytest.mark.asyncio
    async def test_no_escalation_first_violation(self, accounts_with_pool: AsyncSession):
        """First violation in 12 months should NOT be escalated."""
        session = accounts_with_pool
        result = await process_violation(session, 10000, 0, "第一次违规", family_id=1, user_id=2)

        assert result["is_escalated"] is False

    @pytest.mark.asyncio
    async def test_escalation_second_violation(self, accounts_with_pool: AsyncSession):
        """Second violation in 12 months should trigger escalation."""
        session = accounts_with_pool

        # First violation
        await process_violation(session, 10000, 0, "第一次违规", family_id=1, user_id=2)
        await session.flush()

        # Second violation — should escalate
        result = await process_violation(session, 10000, 0, "第二次违规", family_id=1, user_id=2)

        assert result["is_escalated"] is True
        assert result["deposit_suspend_until"] is not None

        # Verify B account deposit_suspended flag
        acct = await session.execute(
            select(Account).where(Account.account_type == "B")
        )
        account_b = acct.scalar_one()
        assert account_b.is_deposit_suspended is True
        assert account_b.deposit_suspend_until is not None

    @pytest.mark.asyncio
    async def test_negative_violation_rejected(self, seeded_accounts: AsyncSession):
        """Negative violation amount is rejected."""
        with pytest.raises(ValueError, match="正数"):
            await process_violation(seeded_accounts, -100, 0, "负数", family_id=1, user_id=2)

    @pytest.mark.asyncio
    async def test_zero_violation_rejected(self, seeded_accounts: AsyncSession):
        """Zero violation amount is rejected."""
        with pytest.raises(ValueError, match="正数"):
            await process_violation(seeded_accounts, 0, 0, "零", family_id=1, user_id=2)

    @pytest.mark.asyncio
    async def test_negative_entered_a_rejected(self, seeded_accounts: AsyncSession):
        """Negative amount_entered_a is rejected."""
        with pytest.raises(ValueError, match="不能为负"):
            await process_violation(seeded_accounts, 100, -1, "负数", family_id=1, user_id=2)
