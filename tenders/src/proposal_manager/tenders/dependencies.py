from fastapi import Depends
from sqlalchemy.orm import Session

from db.database import get_db
from proposal_manager.tenders.service import TenderService


def get_service(db: Session = Depends(get_db)) -> TenderService:
    return TenderService(db=db)
