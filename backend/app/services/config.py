"""Config service: read/announce/apply parameter changes (charter S8).

Supports:
- init_default_config: create default config values for a new family
- get_all_config: list all current config values for a family
- announce_change: schedule a parameter change for next month 1st
- apply_pending_announcements: activate announcements during settlement
"""

from datetime import date

import structlog
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.config import Announcement, Config

logger = structlog.get_logger("config")

# Charter default values (from seed.sql reference)
DEFAULT_CONFIG = {
    "split_ratio_a": "15",
    "split_ratio_b": "30",
    "split_ratio_c": "55",
    "b_tier1_rate": "200",
    "b_tier1_limit": "100000",
    "b_tier2_rate": "120",
    "b_tier3_rate": "30",
    "c_annual_rate": "500",
    "penalty_multiplier": "2",
    "redemption_fee_rate": "10",
    "wishlist_lock_months": "3",
    "wishlist_valid_months": "12",
    "b_suspend_months": "12",
    "c_lock_age": "18",
}


async def init_default_config(family_id: int, session: AsyncSession) -> None:
    """Insert default config values for a newly created family.

    Called during family creation to initialize all charter parameters.
    """
    today = date.today()
    for key, value in DEFAULT_CONFIG.items():
        config = Config(
            family_id=family_id,
            key=key,
            value=value,
            effective_from=today,
        )
        session.add(config)
    await session.flush()
    logger.info("default_config_initialized", family_id=family_id, config_count=len(DEFAULT_CONFIG))


async def get_all_config(session: AsyncSession, family_id: int | None = None) -> list[dict]:
    """Return all current config values.

    For each key, returns the most recent effective entry.
    If family_id is provided, filters by family.

    Returns:
        List of dicts with key, value, effective_from.
    """
    query = select(Config).order_by(Config.key, Config.effective_from.desc())
    if family_id is not None:
        query = query.where(Config.family_id == family_id)
    result = await session.execute(query)
    rows = result.scalars().all()

    # Deduplicate: keep only the latest effective value per key
    seen: dict[str, dict] = {}
    for row in rows:
        if row.key not in seen:
            seen[row.key] = {
                "key": row.key,
                "value": row.value,
                "effective_from": str(row.effective_from),
            }

    return list(seen.values())


async def announce_change(
    session: AsyncSession,
    key: str,
    new_value: str,
    reason: str = "",
    family_id: int | None = None,
) -> dict:
    """Announce a config parameter change.

    Creates an Announcement record with effective_from = next month 1st.
    Does NOT change the config value immediately.

    Args:
        session: DB session
        key: Config key to change
        new_value: New value (string)
        reason: Reason for change

    Returns:
        Dict with announcement details.
    """
    # Get current value for this key
    query = select(Config).where(Config.key == key).order_by(Config.effective_from.desc()).limit(1)
    if family_id is not None:
        query = query.where(Config.family_id == family_id)
    result = await session.execute(query)
    row = result.scalars().first()
    old_value = row.value if row else ""

    # Calculate next month 1st
    today = date.today()
    if today.month == 12:
        effective = date(today.year + 1, 1, 1)
    else:
        effective = date(today.year, today.month + 1, 1)

    # Create announcement
    announcement = Announcement(
        family_id=family_id,
        config_key=key,
        old_value=old_value,
        new_value=new_value,
        announced_at=today,
        effective_from=effective,
    )
    session.add(announcement)
    await session.flush()

    logger.info(
        "config_announced",
        config_key=key,
        old_value=old_value,
        new_value=new_value,
        effective_from=str(effective),
        reason=reason,
    )

    return {
        "id": announcement.id,
        "config_key": key,
        "old_value": old_value,
        "new_value": new_value,
        "announced_at": str(today),
        "effective_from": str(effective),
        "reason": reason,
    }


async def apply_pending_announcements(
    session: AsyncSession,
    settlement_date: date,
    *,
    family_id: int,
) -> list[dict]:
    """Apply announcements whose effective_from <= settlement_date.

    Called during settlement to activate scheduled config changes.
    Creates new Config entries with the announced values.

    Returns:
        List of applied announcements.
    """
    # Find announcements that should take effect
    result = await session.execute(
        select(Announcement).where(
            Announcement.effective_from <= settlement_date,
            Announcement.family_id == family_id,
        )
    )
    announcements = result.scalars().all()

    applied = []

    # Collect already-applied config entries to avoid duplicates
    for ann in announcements:
        # Check if this announcement's config change has already been applied
        existing = await session.execute(
            select(Config).where(
                Config.family_id == family_id,
                Config.key == ann.config_key,
                Config.effective_from == ann.effective_from,
                Config.value == ann.new_value,
            )
        )
        if existing.scalars().first():
            continue  # Already applied

        # Create new config entry with the announced value
        new_config = Config(
            family_id=ann.family_id,
            key=ann.config_key,
            value=ann.new_value,
            effective_from=ann.effective_from,
            announced_at=ann.announced_at,
        )
        session.add(new_config)

        applied.append({
            "config_key": ann.config_key,
            "old_value": ann.old_value,
            "new_value": ann.new_value,
            "effective_from": str(ann.effective_from),
        })

    if applied:
        await session.flush()
        logger.info("config_applied", count=len(applied), changes=applied)

    return applied
