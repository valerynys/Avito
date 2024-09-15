from datetime import datetime
from typing import List, Optional
from uuid import UUID

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from db.models import Tender, Employee, OrganizationResponsible, TenderVersion
from app.schemas import TenderResponse, TenderStatusResponse, EditTenderRequest, CreateTenderResponse
from proposal_manager.exceptions import UserNotFoundError, UnauthorizedCreationError
from proposal_manager.tenders.exceptions import TenderNotFoundError
from proposal_manager.tenders.models import TenderServiceType, TenderStatus


class TenderService:
    def __init__(self, db: Session):
        self.db = db

    async def get_tenders(
            self,
            limit: int,
            offset: int,
            service_type: Optional[List[TenderServiceType]] = None
    ) -> List[TenderResponse]:
        """Fetch tenders with optional filtering by service type."""
        query = self.db.query(Tender)

        if service_type:
            service_type_values = [t.value for t in service_type]
            query = query.filter(Tender.service_type.in_(service_type_values))

        query = query.order_by(Tender.name).offset(offset).limit(limit)

        tenders = query.all()
        if not tenders:
            raise TenderNotFoundError("Тендера не существует")

        return [TenderResponse.from_orm(tender) for tender in tenders]

    async def create_tender(
            self,
            name: str,
            description: str,
            service_type: TenderServiceType,
            organization_id: UUID,
            creator_username: str
    ) -> CreateTenderResponse:
        """Create a new tender."""
        creator = self._get_creator(creator_username)

        if not self._check_authorization(creator, organization_id):
            raise UnauthorizedCreationError("Пользователь не имеет права создавать тендер для этой организации")

        try:
            new_tender = Tender(
                name=name,
                description=description,
                service_type=service_type.value,
                status=TenderStatus.CREATED.value,
                organization_id=organization_id,
                creator_username=creator_username,
                version=1,
                created_at=datetime.utcnow(),
            )
            self.db.add(new_tender)
            self.db.commit()
            self.db.refresh(new_tender)
            return CreateTenderResponse.from_orm(new_tender)
        except IntegrityError:
            self.db.rollback()
            raise ValueError("Некорректные данные или повторяющийся идентификатор")

    async def edit_tender(
            self,
            tender_id: UUID,
            username: str,
            tender_data: EditTenderRequest
    ) -> TenderResponse:
        """Edit an existing tender."""
        creator = self._get_creator(username)
        tender = self._get_tender(tender_id)

        if not self._is_user_responsible_for_organization(username, tender.organization_id):
            raise UnauthorizedCreationError("Пользователь не имеет прав на изменение тендера")

        await self.save_tender_version(tender)

        if tender_data.name is not None:
            tender.name = tender_data.name
        if tender_data.description is not None:
            tender.description = tender_data.description
        if tender_data.service_type is not None:
            tender.service_type = tender_data.service_type.value

        tender.version += 1
        self.db.commit()
        self.db.refresh(tender)

        return TenderResponse.from_orm(tender)

    async def save_tender_version(self, tender: Tender):
        """Save a version of the tender."""
        tender_version = TenderVersion(
            tender_id=tender.id,
            name=tender.name,
            description=tender.description,
            status=tender.status,
            service_type=tender.service_type,
            version=tender.version,
            organization_id=tender.organization_id,
            creator_username=tender.creator_username,
            created_at=tender.created_at
        )
        self.db.add(tender_version)
        self.db.commit()

    async def get_user_tenders(
            self,
            username: str,
            limit: int,
            offset: int
    ) -> List[TenderResponse]:
        """Fetch tenders that the user is responsible for."""
        creator = self._get_creator(username)

        responsible_orgs = (
            self.db.query(OrganizationResponsible.organization_id)
            .filter(OrganizationResponsible.user_id == creator.id)
            .subquery()
        )

        tenders = (
            self.db.query(Tender)
            .filter(Tender.organization_id.in_(responsible_orgs))
            .offset(offset)
            .limit(limit)
            .all()
        )

        if not tenders:
            raise TenderNotFoundError("Тендера не существует")

        return [TenderResponse.from_orm(tender) for tender in tenders]

    async def get_tender_status(
            self,
            tender_id: UUID,
            username: str
    ) -> TenderStatusResponse:
        """Fetch the status of a specific tender."""
        creator = self._get_creator(username)
        tender = self._get_tender(tender_id)

        if not self._is_authorized_for_status(username, tender):
            raise UnauthorizedCreationError("Пользователь не имеет прав получения статуса")

        return TenderStatusResponse(status=tender.status)

    async def update_tender_status(
            self,
            tender_id: UUID,
            status: TenderStatus,
            username: str
    ) -> TenderStatusResponse:
        """Update the status of a specific tender."""
        creator = self._get_creator(username)
        tender = self._get_tender(tender_id)

        if not self._is_user_responsible_for_organization(username, tender.organization_id):
            raise UnauthorizedCreationError("Пользователь не имеет прав на изменение статуса тендера")

        tender.status = status.value
        self.db.commit()
        self.db.refresh(tender)

        return TenderStatusResponse(status=tender.status)

    async def rollback_tender(
            self,
            tender_id: UUID,
            version: int,
            username: str
    ) -> TenderResponse:
        creator = self._get_creator(username)
        tender = self._get_tender(tender_id)

        if tender.creator_username != username and not self._check_authorization(creator, tender.organization_id):
            raise UnauthorizedCreationError("Пользователь не имеет прав на откат тендера")

        tender_version = self.db.query(TenderVersion).filter_by(
            tender_id=tender_id, version=version
        ).first()

        if not tender_version:
            raise TenderNotFoundError("Указанная версия тендера не найдена")

        await self.save_tender_version(tender)

        tender.name = tender_version.name
        tender.description = tender_version.description
        tender.service_type = tender_version.service_type
        tender.status = tender_version.status
        tender.version += 1
        tender.created_at = datetime.utcnow()

        self.db.commit()
        self.db.refresh(tender)

        return TenderResponse.from_orm(tender)

    def _is_user_responsible_for_organization(self, username: str, organization_id: UUID) -> bool:
        """Check if the user is responsible for the given organization."""
        return self.db.query(OrganizationResponsible).join(Employee).filter(
            Employee.username == username,
            OrganizationResponsible.organization_id == organization_id
        ).first() is not None

    def _get_creator(self, username: str) -> Employee:
        """Helper method to get the creator (employee) by username."""
        creator = self.db.query(Employee).filter(Employee.username == username).first()
        if not creator:
            raise UserNotFoundError("Пользователь не существует или некорректен")
        return creator

    def _check_authorization(self, creator: Employee, organization_id: UUID) -> bool:
        """Check if the creator is authorized for the given organization."""
        return self.db.query(OrganizationResponsible).filter(
            OrganizationResponsible.user_id == creator.id,
            OrganizationResponsible.organization_id == organization_id
        ).first() is not None

    def _get_tender(self, tender_id: UUID) -> Tender:
        """Helper method to get a tender by ID."""
        tender = self.db.query(Tender).filter(Tender.id == tender_id).first()
        if not tender:
            raise TenderNotFoundError("Тендера не существует")
        return tender

    def _is_authorized_for_status(self, username: str, tender: Tender) -> bool:
        """Check if the user is authorized to get the status of the tender."""
        return (tender.creator_username == username) or self._check_authorization(self._get_creator(username),
                                                                                  tender.organization_id)
