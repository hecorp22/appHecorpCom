from typing import List
from app.models.quotation import Quotation
from app.repos.base_repo import BaseRepo


class QuotationRepo(BaseRepo[Quotation]):
    model = Quotation

    def next_code(self) -> str:
        last = self.db.query(Quotation).order_by(Quotation.id.desc()).first()
        n = (last.id + 1) if last else 1
        return f"COT-{n:04d}"

    def search(self, q: str, limit: int = 200, offset: int = 0) -> List[Quotation]:
        query = self.db.query(Quotation)
        if q:
            like = f"%{q.strip()}%"
            query = query.filter(
                (Quotation.company.ilike(like))
                | (Quotation.contact_name.ilike(like))
                | (Quotation.quote_code.ilike(like))
                | (Quotation.subject.ilike(like))
            )
        return query.order_by(Quotation.id.desc()).offset(offset).limit(limit).all()
