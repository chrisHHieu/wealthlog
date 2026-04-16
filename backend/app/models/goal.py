import enum
import uuid

from sqlalchemy import Boolean, Float, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base
from app.models.base import CreatedAtMixin, TimestampMixin, UUIDMixin


class GoalType(str, enum.Enum):
    EMERGENCY = "emergency"
    SAVINGS = "savings"
    PURCHASE = "purchase"
    INVESTMENT = "investment"
    DEBT = "debt"
    CUSTOM = "custom"


class Goal(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "goals"

    name: Mapped[str] = mapped_column(String(200), nullable=False)
    type: Mapped[GoalType] = mapped_column(default=GoalType.CUSTOM)
    target_amount: Mapped[float] = mapped_column(Float, nullable=False)
    current_amount: Mapped[float] = mapped_column(Float, default=0)
    deadline: Mapped[str | None] = mapped_column(String(10))  # ISO date
    icon: Mapped[str] = mapped_column(String(10), default="🎯")
    color: Mapped[str] = mapped_column(String(20), default="#00C896")
    description: Mapped[str | None] = mapped_column(String(500))
    is_completed: Mapped[bool] = mapped_column(Boolean, default=False)

    # Relationships
    contributions: Mapped[list["GoalContribution"]] = relationship(
        back_populates="goal",
        cascade="all, delete-orphan",
    )

    def __repr__(self) -> str:
        return f"<Goal {self.name} {self.current_amount}/{self.target_amount}>"


class GoalContribution(Base, UUIDMixin, CreatedAtMixin):
    __tablename__ = "goal_contributions"

    goal_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("goals.id", ondelete="CASCADE"),
        nullable=False,
    )
    amount: Mapped[float] = mapped_column(Float, nullable=False)
    note: Mapped[str | None] = mapped_column(String(500))
    date: Mapped[str] = mapped_column(String(10), nullable=False)

    # Relationships
    goal: Mapped[Goal] = relationship(back_populates="contributions")

    def __repr__(self) -> str:
        return f"<GoalContribution {self.amount} on {self.date}>"
