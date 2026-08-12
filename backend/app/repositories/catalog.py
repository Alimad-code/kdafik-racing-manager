from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.models import Driver, Team, Track


class CatalogRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    def list_active_drivers(self) -> list[Driver]:
        statement = (
            select(Driver)
            .where(Driver.is_active.is_(True))
            .order_by(Driver.price_millions.desc(), Driver.last_name, Driver.first_name)
        )
        return list(self.session.scalars(statement))

    def list_active_teams(self) -> list[Team]:
        statement = (
            select(Team)
            .where(Team.is_active.is_(True))
            .order_by(Team.price_millions.desc(), Team.name)
        )
        return list(self.session.scalars(statement))

    def list_tracks(self) -> list[Track]:
        statement = select(Track).options(selectinload(Track.segments)).order_by(Track.name)
        return list(self.session.scalars(statement))
