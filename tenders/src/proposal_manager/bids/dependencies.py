from fastapi import Depends
from sqlalchemy.orm import Session

from db.database import get_db
from proposal_manager.bids.service import BidService


def get_service(db: Session = Depends(get_db)) -> BidService:
    return BidService(db=db)
