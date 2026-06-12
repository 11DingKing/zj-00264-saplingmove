from sqlalchemy import Column, Integer, String, Float, DateTime, ForeignKey, Enum, Text
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
import enum

from app.database import Base


class AllocationStatus(str, enum.Enum):
    APPLIED = "applied"           # 已申请
    REVIEWED = "reviewed"         # 已审核
    LOCKED = "locked"             # 已锁定（库存已锁定）
    SHIPPING = "shipping"         # 起运中
    RECEIVED = "received"         # 已签收


class Nursery(Base):
    __tablename__ = "nurseries"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(200), nullable=False, comment="苗圃名称")
    location = Column(String(300), nullable=False, comment="苗圃位置")
    contact_person = Column(String(50), comment="联系人")
    contact_phone = Column(String(30), comment="联系电话")
    total_area = Column(Float, comment="苗圃总面积(亩)")
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())

    stocks = relationship("NurseryStock", back_populates="nursery", cascade="all, delete-orphan")


class NurseryStock(Base):
    __tablename__ = "nursery_stocks"

    id = Column(Integer, primary_key=True, index=True)
    nursery_id = Column(Integer, ForeignKey("nurseries.id"), nullable=False)
    spec_name = Column(String(100), nullable=False, comment="苗木规格名称")
    height_cm = Column(Float, comment="高度(cm)")
    dbh_cm = Column(Float, comment="地径(cm)")
    crown_cm = Column(Float, comment="冠幅(cm)")
    total_stock = Column(Integer, nullable=False, default=0, comment="总库存株数")
    locked_stock = Column(Integer, nullable=False, default=0, comment="已锁定株数")
    available_stock = Column(Integer, nullable=False, default=0, comment="可用株数")
    unit_price = Column(Float, comment="单价(元/株)")
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())

    nursery = relationship("Nursery", back_populates="stocks")
    __table_args__ = ()


class RestorationPlot(Base):
    __tablename__ = "restoration_plots"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(200), nullable=False, comment="地块名称")
    project = Column(String(200), nullable=False, comment="所属项目(祁连山/三北工程等)")
    region = Column(String(200), nullable=False, comment="所属区域")
    location = Column(String(300), nullable=False, comment="具体位置")
    area_mu = Column(Float, nullable=False, comment="面积(亩)")
    site_condition = Column(Text, comment="立地条件描述(海拔、坡度、土壤、降水等)")
    planter = Column(String(100), comment="实施单位/负责人")
    contact_phone = Column(String(30), comment="联系电话")
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())

    requirements = relationship("PlotRequirement", back_populates="plot", cascade="all, delete-orphan")
    allocations = relationship("AllocationRequest", back_populates="plot")


class PlotRequirement(Base):
    __tablename__ = "plot_requirements"

    id = Column(Integer, primary_key=True, index=True)
    plot_id = Column(Integer, ForeignKey("restoration_plots.id"), nullable=False)
    spec_name = Column(String(100), nullable=False, comment="苗木规格名称")
    required_quantity = Column(Integer, nullable=False, comment="需求株数")
    received_quantity = Column(Integer, default=0, comment="已签收株数")
    planted_quantity = Column(Integer, default=0, comment="已栽植株数")
    remark = Column(String(500), comment="备注")
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())

    plot = relationship("RestorationPlot", back_populates="requirements")


class AllocationRequest(Base):
    __tablename__ = "allocation_requests"

    id = Column(Integer, primary_key=True, index=True)
    request_no = Column(String(50), unique=True, nullable=False, comment="申请单号")
    plot_id = Column(Integer, ForeignKey("restoration_plots.id"), nullable=False)
    applicant = Column(String(100), nullable=False, comment="申请人")
    apply_reason = Column(Text, comment="申请事由")
    status = Column(Enum(AllocationStatus), default=AllocationStatus.APPLIED, nullable=False, comment="状态")
    reviewer = Column(String(100), comment="审核人")
    review_remark = Column(Text, comment="审核意见")
    reviewed_at = Column(DateTime, comment="审核时间")
    locker = Column(String(100), comment="锁定操作人")
    locked_at = Column(DateTime, comment="锁定时间")
    shipper = Column(String(100), comment="起运操作人")
    shipping_info = Column(Text, comment="起运信息(车辆、司机等)")
    shipped_at = Column(DateTime, comment="起运时间")
    receiver = Column(String(100), comment="签收人")
    received_at = Column(DateTime, comment="签收时间")
    revoker = Column(String(100), comment="撤销操作人")
    revoked_at = Column(DateTime, comment="撤销时间")
    revoke_reason = Column(Text, comment="撤销原因")
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())

    plot = relationship("RestorationPlot", back_populates="allocations")
    items = relationship("AllocationItem", back_populates="allocation", cascade="all, delete-orphan")
    planting_records = relationship("PlantingRecord", back_populates="allocation", cascade="all, delete-orphan")


class AllocationItem(Base):
    __tablename__ = "allocation_items"

    id = Column(Integer, primary_key=True, index=True)
    allocation_id = Column(Integer, ForeignKey("allocation_requests.id"), nullable=False)
    nursery_stock_id = Column(Integer, ForeignKey("nursery_stocks.id"), nullable=False)
    nursery_id = Column(Integer, ForeignKey("nurseries.id"), nullable=False)
    spec_name = Column(String(100), nullable=False, comment="苗木规格")
    applied_quantity = Column(Integer, nullable=False, comment="申请株数")
    approved_quantity = Column(Integer, comment="审核批准株数")
    allocated_quantity = Column(Integer, comment="实际调拨株数(锁定)")
    shipped_quantity = Column(Integer, comment="实际起运株数")
    received_quantity = Column(Integer, comment="实际签收株数")
    unit_price = Column(Float, comment="调拨单价")
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())

    allocation = relationship("AllocationRequest", back_populates="items")
    nursery = relationship("Nursery")
    nursery_stock = relationship("NurseryStock")


class PlantingRecord(Base):
    __tablename__ = "planting_records"

    id = Column(Integer, primary_key=True, index=True)
    allocation_id = Column(Integer, ForeignKey("allocation_requests.id"), nullable=False)
    allocation_item_id = Column(Integer, ForeignKey("allocation_items.id"), nullable=False)
    plot_id = Column(Integer, ForeignKey("restoration_plots.id"), nullable=False)
    spec_name = Column(String(100), nullable=False, comment="苗木规格")
    planted_quantity = Column(Integer, nullable=False, comment="实际栽植数量")
    survived_judgement = Column(Integer, comment="成活初判数量")
    survival_rate = Column(Float, comment="成活初判率")
    record_date = Column(DateTime, comment="登记日期")
    recorder = Column(String(100), comment="登记人")
    remark = Column(Text, comment="备注")
    created_at = Column(DateTime, server_default=func.now())

    allocation = relationship("AllocationRequest", back_populates="planting_records")
    allocation_item = relationship("AllocationItem")
    plot = relationship("RestorationPlot")
