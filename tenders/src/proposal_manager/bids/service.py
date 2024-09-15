from datetime import datetime
from typing import List
from uuid import UUID

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.schemas import BidResponse, BidStatusResponse, UpdateBidStatusResponse, EditBidRequest, BidFeedbackResponse
from db.models import Tender, Bid, OrganizationResponsible, Employee, BidVersion, BidDecisionLog, BidFeedback
from proposal_manager.bids.exceptions import BidNotFoundError
from proposal_manager.bids.models import AuthorType, BidStatus, BidDecision
from proposal_manager.exceptions import UnauthorizedCreationError, UserNotFoundError, TenderBidError
from proposal_manager.tenders.exceptions import TenderNotFoundError


class BidService:
    def __init__(self, db: Session):
        self.db = db

    async def create_bid(
            self,
            name: str,
            description: str,
            tender_id: UUID,
            author_type: AuthorType,
            author_id: UUID
    ) -> BidResponse:
        """Create a new bid."""
        tender = await self._get_tender(tender_id)
        await self._authorize_creation(author_id, tender, author_type)

        try:
            new_bid = Bid(
                name=name,
                description=description,
                tender_id=tender_id,
                status=BidStatus.CREATED,
                author_type=author_type,
                author_id=author_id,
                version=1,
                created_at=datetime.utcnow(),
            )
            self.db.add(new_bid)
            self.db.commit()
            self.db.refresh(new_bid)

            return BidResponse.from_orm(new_bid)

        except IntegrityError:
            self.db.rollback()
            raise ValueError("Некорректные данные или повторяющийся идентификатор")

    async def get_user_bids(
            self,
            username: str,
            limit: int,
            offset: int
    ) -> List[BidResponse]:
        """Fetch bids created by the user."""
        creator = await self._get_creator(username)

        responsible_org_ids = self.db.query(OrganizationResponsible.organization_id).filter(
            OrganizationResponsible.user_id == creator.id
        ).subquery()

        bids = self.db.query(Bid).join(
            Tender, Bid.tender_id == Tender.id
        ).filter(
            Tender.organization_id.in_(responsible_org_ids)
        ).offset(offset).limit(limit).all()

        if not bids:
            raise BidNotFoundError("Нет предложений для данного пользователя и его организаций")

        return [BidResponse.from_orm(bid) for bid in bids]

    async def get_bids_for_tender(
            self,
            tender_id: UUID,
            username: str,
            limit: int,
            offset: int
    ) -> List[BidResponse]:
        """Fetch bids for a specific tender if the user is responsible for the organization."""
        creator = await self._get_creator(username)
        tender = await self._get_tender(tender_id)

        await self._check_organization_responsibility(creator.id, tender.organization_id)
        bids = self.db.query(Bid).filter(Bid.tender_id == tender_id).offset(offset).limit(limit).all()

        if not bids:
            raise TenderBidError("Тендер или предложение не найдено")

        return [BidResponse.from_orm(bid) for bid in bids]

    async def get_bid_status(
            self,
            bid_id: UUID,
            username: str
    ) -> BidStatusResponse:
        """Fetch the status of a specific bid."""
        creator = await self._get_creator(username)
        bid = await self._get_bid(bid_id)

        await self._check_organization_responsibility(creator.id, bid.tender.organization_id)

        return BidStatusResponse(status=bid.status)

    async def update_bid_status(
            self,
            bid_id: UUID,
            status: BidStatus,
            username: str
    ) -> UpdateBidStatusResponse:
        """Edit bid status."""
        creator = await self._get_creator(username)
        bid = await self._get_bid(bid_id)

        await self._check_organization_responsibility(creator.id, bid.tender.organization_id)

        bid.status = status.value
        self.db.commit()
        self.db.refresh(bid)

        return UpdateBidStatusResponse.from_orm(bid)

    async def edit_bid(
            self,
            bid_id: UUID,
            username: str,
            bid_data: EditBidRequest
    ) -> BidResponse:
        """Edit an existing bid."""
        creator = await self._get_creator(username)
        bid = await self._get_bid(bid_id)

        await self._check_organization_responsibility(creator.id, bid.tender.organization_id)
        await self._save_bid_version(bid)

        bid.name = bid_data.name or bid.name
        bid.description = bid_data.description or bid.description
        bid.version += 1

        self.db.commit()
        self.db.refresh(bid)

        return BidResponse.from_orm(bid)

    async def rollback_bid_version(self, bid_id: UUID, version: int, username: str) -> BidResponse:
        """Rollback a bid to a specific version."""
        creator = await self._get_creator(username)
        if not creator:
            raise UserNotFoundError("Пользователь не найден")

        bid = self.db.query(Bid).filter(Bid.id == bid_id).first()
        if not bid:
            raise BidNotFoundError("Предложение не найдено")

        is_responsible = self.db.query(OrganizationResponsible).filter(
            OrganizationResponsible.user_id == creator.id,
            OrganizationResponsible.organization_id == bid.tender.organization_id
        ).first()

        if not is_responsible:
            raise UnauthorizedCreationError("Пользователь не имеет права откатывать предложение")

        bid_version = self.db.query(BidVersion).filter(
            BidVersion.bid_id == bid_id,
            BidVersion.version == version
        ).first()

        if not bid_version:
            raise BidNotFoundError("Указанная версия тендера не найдена")

        await self._save_bid_version(bid)

        bid.name = bid_version.name
        bid.description = bid_version.description
        bid.status = bid_version.status
        bid.version += 1
        self.db.commit()
        self.db.refresh(bid)

        return BidResponse.from_orm(bid)

    async def submit_bid_decision(
            self,
            bid_id: UUID,
            decision: BidDecision,
            username: str
    ) -> BidResponse:
        """Submit a decision (approve or reject) for a bid."""
        creator = await self._get_creator(username)
        if not creator:
            raise UserNotFoundError("Пользователь не найден")

        bid = self.db.query(Bid).filter(Bid.id == bid_id).first()
        if not bid:
            raise BidNotFoundError("Предложение не найдено")

        responsible = self.db.query(OrganizationResponsible).filter(
            OrganizationResponsible.user_id == creator.id,
            OrganizationResponsible.organization_id == bid.tender.organization_id
        ).first()

        if not responsible:
            raise UnauthorizedCreationError("Пользователь не имеет права откатывать предложение")

        existing_decision = self.db.query(BidDecisionLog).filter(
            BidDecisionLog.bid_id == bid.id,
            BidDecisionLog.responsible_id == responsible.id
        ).first()

        if existing_decision:
            existing_decision.decision = BidDecision.REJECTED
        else:
            bid_decision_log = BidDecisionLog(
                bid_id=bid.id,
                responsible_id=responsible.id,
                decision=BidDecision.APPROVED
            )
            self.db.add(bid_decision_log)

        if decision == "Rejected" or await self._check_if_rejected(bid):
            bid.status = BidStatus.CANCELED
        else:
            if await self._check_if_quorum_reached(bid):
                bid.status = BidStatus.PUBLISHED

        self.db.commit()
        self.db.refresh(bid)

        return BidResponse.from_orm(bid)

    async def submit_feedback(
            self,
            bidId: UUID,
            bidFeedback: str,
            username: str
    ) -> BidResponse:
        creator = await self._get_creator(username)
        if not creator:
            raise UserNotFoundError("Пользователь не найден")

        bid = self.db.query(Bid).filter(Bid.id == bidId).first()

        if not bid:
            raise BidNotFoundError("Предложение не найдено")

        responsible = self.db.query(OrganizationResponsible).filter(
            OrganizationResponsible.user_id == creator.id,
            OrganizationResponsible.organization_id == bid.tender.organization_id
        ).first()

        if not responsible:
            raise UnauthorizedCreationError("Пользователь не имеет права откатывать предложение")

        feedback = BidFeedback(
            bid_id=bid.id,
            responsible_id=responsible.id,
            description=bidFeedback
        )
        self.db.add(feedback)
        self.db.commit()

        return BidResponse(
            id=bid.id,
            name=bid.name,
            description=bid.description,
            status=bid.status,
            tenderId=bid.tender_id,
            authorType=bid.author_type,
            authorId=bid.author_id,
            version=bid.version,
            createdAt=str(bid.created_at)
        )

    async def get_reviews_for_author(
            self,
            tender_id: UUID,
            author_username: str,
            requester_username: str,
            limit: int,
            offset: int
    ) -> List[BidFeedbackResponse]:
        creator = await self._get_creator(requester_username)
        if not creator:
            raise UserNotFoundError("Пользователь не найден")

        tender = await self._get_tender(tender_id)

        is_responsible = self.db.query(OrganizationResponsible).filter(
            OrganizationResponsible.organization_id == tender.organization_id,
            OrganizationResponsible.username == requester_username
        ).all()

        if not is_responsible:
            raise UnauthorizedCreationError("Пользователь не имеет права откатывать предложение")

        reviews = self._fetch_reviews(tender_id, author_username, limit, offset)
        return reviews

    async def _check_if_rejected(self, bid: Bid) -> bool:
        """Check if there are any 'Rejected' decisions for the bid."""
        rejected_decision_count = self.db.query(BidDecisionLog).filter(
            BidDecisionLog.bid_id == bid.id,
            BidDecisionLog.decision == BidDecision.REJECTED
        ).count()
        return rejected_decision_count > 0

    async def _check_if_quorum_reached(self, bid: Bid) -> bool:
        """Check if the quorum for approving the bid is reached."""
        total_responsibles = self.db.query(OrganizationResponsible).filter(
            OrganizationResponsible.organization_id == bid.tender.organization_id
        ).count()

        quorum = min(3, total_responsibles)

        approved_decisions = self.db.query(BidDecisionLog).filter(
            BidDecisionLog.bid_id == bid.id,
            BidDecisionLog.decision == BidDecision.APPROVED
        ).count()

        return approved_decisions >= quorum

    async def _get_creator(self, username: str) -> Employee:
        """Helper method to get the creator (employee) by username."""
        creator = self.db.query(Employee).filter(Employee.username == username).first()
        if not creator:
            raise UserNotFoundError("Пользователь не существует или некорректен")
        return creator

    async def _get_tender(self, tender_id: UUID) -> Tender:
        """Helper method to get a tender by ID."""
        tender = self.db.query(Tender).filter(Tender.id == tender_id).first()
        if not tender:
            raise TenderNotFoundError("Тендера не существует")
        return tender

    async def _get_bid(self, bid_id: UUID) -> Bid:
        """Helper method to get a bid by ID."""
        bid = self.db.query(Bid).filter(Bid.id == bid_id).first()
        if not bid:
            raise BidNotFoundError("Предложение не найдено")
        return bid

    async def _authorize_creation(
            self,
            author_id: UUID,
            tender: Tender,
            author_type: AuthorType
    ) -> None:
        """Authorize the creation of a bid."""
        if not await self._user_exists(author_id):
            raise UserNotFoundError(f"Пользователь не существует или некорректен.")
        if author_type == AuthorType.ORGANIZATION:
            is_responsible = await self.is_user_responsible_for_organization(author_id, tender.organization_id)
            if not is_responsible:
                raise UnauthorizedCreationError("Пользователь не имеет прав на создание предложения")

        elif author_type == AuthorType.USER:
            pass


    async def _check_authorization(
            self,
            author_id: UUID,
            tender: Tender,
            author_type: AuthorType
    ) -> bool:
        """Check if the author is authorized to create a bid for the given tender."""
        if author_type in [AuthorType.ORGANIZATION, AuthorType.USER]:
            return self.db.query(OrganizationResponsible).filter(
                OrganizationResponsible.user_id == author_id,
                OrganizationResponsible.organization_id == tender.organization_id
            ).first() is not None
        return False

    async def _check_organization_responsibility(
            self,
            user_id: UUID,
            organization_id: UUID
    ) -> None:
        """Check if the user is responsible for the organization."""
        is_responsible = self.db.query(OrganizationResponsible).filter(
            OrganizationResponsible.user_id == user_id,
            OrganizationResponsible.organization_id == organization_id
        ).first()

        if not is_responsible:
            raise UnauthorizedCreationError("Пользователь не имеет права выполнять данное действие")

    async def _save_bid_version(self, bid: Bid) -> None:
        """Save a version of the bid."""
        bid_version = BidVersion(
            bid_id=bid.id,
            name=bid.name,
            description=bid.description,
            status=bid.status,
            version=bid.version,
            tender_id=bid.tender_id,
            author_type=bid.author_type,
            author_id=bid.author_id,
            created_at=bid.created_at,
        )
        self.db.add(bid_version)
        self.db.commit()

    def _fetch_reviews(self, tender_id: UUID, author_username: str, limit: int, offset: int) -> List[
        BidFeedbackResponse]:
        reviews = self.db.query(BidFeedback).join(
            BidFeedback.bid
        ).filter(
            BidFeedback.bid_id.in_(
                self.db.query(Bid.id).filter(
                    Bid.author_username == author_username,
                    Bid.tender_id == tender_id
                )
            )
        ).offset(offset).limit(limit).all()

        return [BidFeedbackResponse.from_orm(review) for review in reviews]

    async def is_user_responsible_for_organization(self, user_id: UUID, organization_id: UUID) -> bool:
        responsible_users = await self.get_organization_responsibles(organization_id)
        return any(user.id == user_id for user in responsible_users)

    async def get_organization_responsibles(self, organization_id: UUID) -> List[Employee]:
        return self.db.query(Employee).join(OrganizationResponsible).filter(
            OrganizationResponsible.organization_id == organization_id
        ).all()

    async def _user_exists(self, user_id: UUID) -> bool:
        return self.db.query(Employee).filter(Employee.id == user_id).first() is not None