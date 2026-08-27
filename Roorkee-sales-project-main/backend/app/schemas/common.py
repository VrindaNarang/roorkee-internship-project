from pydantic import BaseModel


class PaginationMeta(BaseModel):
    total: int
    page: int
    page_size: int
    total_pages: int
