from pydantic import BaseModel, Field
from datetime import datetime
from typing import List, Optional
from app.models import AllocationStatus


class NurseryBase(BaseModel):
    name: str = Field(..., max_length=200)
    location: str = Field(..., max_length=300)
    contact_person: Optional[str] = None
    contact_phone: Optional[str] = None
    total_area: Optional[float] = None


class NurseryCreate(NurseryBase):
    pass


class NurseryUpdate(BaseModel):
    name: Optional[str] = None
    location: Optional[str] = None
    contact_person: Optional[str] = None
    contact_phone: Optional[str] = None
    total_area: Optional[float] = None


class Nursery(NurseryBase):
    id: int
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class NurseryStockBase(BaseModel):
    nursery_id: int
    spec_name: str = Field(..., max_length=100)
    height_cm: Optional[float] = None
    dbh_cm: Optional[float] = None
    crown_cm: Optional[float] = None
    total_stock: int = 0
    unit_price: Optional[float] = None


class NurseryStockCreate(NurseryStockBase):
    pass


class NurseryStockUpdate(BaseModel):
    spec_name: Optional[str] = None
    height_cm: Optional[float] = None
    dbh_cm: Optional[float] = None
    crown_cm: Optional[float] = None
    total_stock: Optional[int] = None
    unit_price: Optional[float] = None


class NurseryStock(NurseryStockBase):
    id: int
    locked_stock: int
    available_stock: int
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class NurseryStockWithNursery(NurseryStock):
    nursery: Optional[Nursery] = None


class RestorationPlotBase(BaseModel):
    name: str = Field(..., max_length=200)
    project: str = Field(..., max_length=200)
    region: str = Field(..., max_length=200)
    location: str = Field(..., max_length=300)
    area_mu: float
    site_condition: Optional[str] = None
    planter: Optional[str] = None
    contact_phone: Optional[str] = None


class RestorationPlotCreate(RestorationPlotBase):
    pass


class RestorationPlotUpdate(BaseModel):
    name: Optional[str] = None
    project: Optional[str] = None
    region: Optional[str] = None
    location: Optional[str] = None
    area_mu: Optional[float] = None
    site_condition: Optional[str] = None
    planter: Optional[str] = None
    contact_phone: Optional[str] = None


class RestorationPlot(RestorationPlotBase):
    id: int
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class PlotRequirementBase(BaseModel):
    plot_id: int
    spec_name: str = Field(..., max_length=100)
    required_quantity: int
    remark: Optional[str] = None


class PlotRequirementCreate(PlotRequirementBase):
    pass


class PlotRequirementUpdate(BaseModel):
    spec_name: Optional[str] = None
    required_quantity: Optional[int] = None
    remark: Optional[str] = None


class PlotRequirement(PlotRequirementBase):
    id: int
    received_quantity: int
    planted_quantity: int
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class PlotRequirementWithGap(PlotRequirement):
    gap_quantity: int
    fulfillment_rate: float


class GapBySpec(BaseModel):
    spec_name: str
    total_required: int
    total_received: int
    total_gap: int
    affected_plots: int


class PlotGapSummary(BaseModel):
    plot_id: int
    plot_name: str
    project: str
    region: str
    spec_name: str
    required_quantity: int
    received_quantity: int
    gap_quantity: int
    fulfillment_rate: float


class DispatchRecommendation(BaseModel):
    spec_name: str
    total_gap: int
    total_available: int
    plots_needing: List[PlotGapSummary] = []


class AllocationItemBase(BaseModel):
    nursery_stock_id: int
    spec_name: str
    applied_quantity: int


class AllocationItemCreate(AllocationItemBase):
    pass


class AllocationItem(AllocationItemBase):
    id: int
    allocation_id: int
    nursery_id: int
    approved_quantity: Optional[int] = None
    allocated_quantity: Optional[int] = None
    shipped_quantity: Optional[int] = None
    received_quantity: Optional[int] = None
    unit_price: Optional[float] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class AllocationRequestBase(BaseModel):
    plot_id: int
    applicant: str
    apply_reason: Optional[str] = None


class AllocationRequestCreate(AllocationRequestBase):
    items: List[AllocationItemCreate]


class AllocationRequestReview(BaseModel):
    reviewer: str
    review_remark: Optional[str] = None
    approved: bool = True
    item_approvals: Optional[dict[int, int]] = None


class AllocationRequestLock(BaseModel):
    locker: str
    item_allocations: Optional[dict[int, int]] = None


class AllocationRequestRevoke(BaseModel):
    revoker: str
    revoke_reason: Optional[str] = None


class AllocationRequestShip(BaseModel):
    shipper: str
    shipping_info: Optional[str] = None
    item_shipments: Optional[dict[int, int]] = None


class AllocationRequestReceive(BaseModel):
    receiver: str
    item_receives: Optional[dict[int, int]] = None


class AllocationRequest(AllocationRequestBase):
    id: int
    request_no: str
    status: AllocationStatus
    reviewer: Optional[str] = None
    review_remark: Optional[str] = None
    reviewed_at: Optional[datetime] = None
    locker: Optional[str] = None
    locked_at: Optional[datetime] = None
    shipper: Optional[str] = None
    shipping_info: Optional[str] = None
    shipped_at: Optional[datetime] = None
    receiver: Optional[str] = None
    received_at: Optional[datetime] = None
    revoker: Optional[str] = None
    revoked_at: Optional[datetime] = None
    revoke_reason: Optional[str] = None
    created_at: datetime
    updated_at: datetime
    items: List[AllocationItem] = []
    plot: Optional[RestorationPlot] = None

    class Config:
        from_attributes = True


class PlantingRecordItem(BaseModel):
    allocation_item_id: int
    spec_name: str
    planted_quantity: int
    survived_judgement: int
    remark: Optional[str] = None


class PlantingRecordCreate(BaseModel):
    allocation_id: int
    plot_id: int
    recorder: str
    record_date: Optional[datetime] = None
    items: List[PlantingRecordItem]


class PlantingRecord(BaseModel):
    id: int
    allocation_id: int
    allocation_item_id: int
    plot_id: int
    spec_name: str
    planted_quantity: int
    survived_judgement: int
    survival_rate: Optional[float] = None
    record_date: Optional[datetime] = None
    recorder: Optional[str] = None
    remark: Optional[str] = None
    created_at: datetime

    class Config:
        from_attributes = True


class StatBySpec(BaseModel):
    spec_name: str
    total_allocated: int = 0
    total_received: int = 0
    receive_rate: float = 0.0
    total_planted: int = 0
    total_survived: int = 0
    survival_rate: float = 0.0


class StatByPlot(BaseModel):
    plot_id: int
    plot_name: str
    project: str
    region: str
    total_allocated: int = 0
    total_received: int = 0
    receive_rate: float = 0.0
    total_planted: int = 0
    total_survived: int = 0
    survival_rate: float = 0.0


class StatByPlotSpec(BaseModel):
    plot_id: int
    plot_name: str
    spec_name: str
    total_allocated: int = 0
    total_received: int = 0
    receive_rate: float = 0.0
    total_planted: int = 0
    total_survived: int = 0
    survival_rate: float = 0.0
