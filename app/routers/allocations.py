from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy.sql import func
from typing import List, Optional
from datetime import datetime

from app.database import get_db
from app import models, schemas

router = APIRouter(prefix="/api/allocations", tags=["调拨管理"])

VALID_TRANSITIONS = {
    models.AllocationStatus.APPLIED: [models.AllocationStatus.REVIEWED, models.AllocationStatus.APPLIED],
    models.AllocationStatus.REVIEWED: [models.AllocationStatus.LOCKED, models.AllocationStatus.APPLIED],
    models.AllocationStatus.LOCKED: [models.AllocationStatus.SHIPPING, models.AllocationStatus.APPLIED],
    models.AllocationStatus.SHIPPING: [models.AllocationStatus.RECEIVED, models.AllocationStatus.APPLIED],
    models.AllocationStatus.RECEIVED: [],
}


def _generate_request_no(db: Session) -> str:
    today = datetime.now().strftime("%Y%m%d")
    prefix = f"DB{today}"
    last = db.query(models.AllocationRequest).filter(
        models.AllocationRequest.request_no.like(f"{prefix}%")
    ).order_by(models.AllocationRequest.id.desc()).first()
    if last:
        try:
            seq = int(last.request_no[-4:]) + 1
        except (ValueError, IndexError):
            seq = 1
    else:
        seq = 1
    return f"{prefix}{seq:04d}"


def _check_stock_availability(db: Session, stock_id: int, quantity: int) -> models.NurseryStock:
    stock = db.query(models.NurseryStock).filter(models.NurseryStock.id == stock_id).first()
    if not stock:
        raise HTTPException(status_code=400, detail=f"库存记录不存在(stock_id={stock_id})")
    if stock.available_stock < quantity:
        raise HTTPException(
            status_code=400,
            detail=f"规格[{stock.spec_name}]可用库存不足: 需{quantity}株, 仅剩{stock.available_stock}株"
        )
    return stock


@router.get("", response_model=List[schemas.AllocationRequest])
def list_allocations(
    status: Optional[models.AllocationStatus] = None,
    plot_id: Optional[int] = None,
    db: Session = Depends(get_db),
):
    query = db.query(models.AllocationRequest)
    if status:
        query = query.filter(models.AllocationRequest.status == status)
    if plot_id:
        query = query.filter(models.AllocationRequest.plot_id == plot_id)
    return query.order_by(models.AllocationRequest.id.desc()).all()


@router.get("/{allocation_id}", response_model=schemas.AllocationRequest)
def get_allocation(allocation_id: int, db: Session = Depends(get_db)):
    alloc = db.query(models.AllocationRequest).filter(models.AllocationRequest.id == allocation_id).first()
    if not alloc:
        raise HTTPException(status_code=404, detail="调拨申请不存在")
    return alloc


@router.post("", response_model=schemas.AllocationRequest)
def create_allocation(data: schemas.AllocationRequestCreate, db: Session = Depends(get_db)):
    plot = db.query(models.RestorationPlot).filter(models.RestorationPlot.id == data.plot_id).first()
    if not plot:
        raise HTTPException(status_code=400, detail="地块不存在")
    if not data.items:
        raise HTTPException(status_code=400, detail="至少需要一条调拨明细")

    alloc = models.AllocationRequest(
        request_no=_generate_request_no(db),
        plot_id=data.plot_id,
        applicant=data.applicant,
        apply_reason=data.apply_reason,
        status=models.AllocationStatus.APPLIED,
    )
    db.add(alloc)
    db.flush()

    for item in data.items:
        stock = db.query(models.NurseryStock).filter(models.NurseryStock.id == item.nursery_stock_id).first()
        if not stock:
            raise HTTPException(status_code=400, detail=f"库存ID={item.nursery_stock_id}不存在")
        db_item = models.AllocationItem(
            allocation_id=alloc.id,
            nursery_stock_id=item.nursery_stock_id,
            nursery_id=stock.nursery_id,
            spec_name=item.spec_name,
            applied_quantity=item.applied_quantity,
            unit_price=stock.unit_price,
        )
        db.add(db_item)

    db.commit()
    db.refresh(alloc)
    return alloc


@router.post("/{allocation_id}/review", response_model=schemas.AllocationRequest)
def review_allocation(
    allocation_id: int,
    data: schemas.AllocationRequestReview,
    db: Session = Depends(get_db),
):
    alloc = db.query(models.AllocationRequest).filter(models.AllocationRequest.id == allocation_id).first()
    if not alloc:
        raise HTTPException(status_code=404, detail="调拨申请不存在")
    if alloc.status != models.AllocationStatus.APPLIED:
        raise HTTPException(status_code=400, detail=f"当前状态[{alloc.status.value}]不能审核")

    if data.approved:
        alloc.status = models.AllocationStatus.REVIEWED
        for item in alloc.items:
            if data.item_approvals and str(item.id) in data.item_approvals:
                approved = data.item_approvals[str(item.id)]
            else:
                approved = item.applied_quantity
            item.approved_quantity = approved
    else:
        alloc.status = models.AllocationStatus.APPLIED

    alloc.reviewer = data.reviewer
    alloc.review_remark = data.review_remark
    alloc.reviewed_at = datetime.now()

    db.commit()
    db.refresh(alloc)
    return alloc


@router.post("/{allocation_id}/lock", response_model=schemas.AllocationRequest)
def lock_allocation(
    allocation_id: int,
    data: schemas.AllocationRequestLock,
    db: Session = Depends(get_db),
):
    alloc = db.query(models.AllocationRequest).filter(models.AllocationRequest.id == allocation_id).first()
    if not alloc:
        raise HTTPException(status_code=404, detail="调拨申请不存在")
    if alloc.status != models.AllocationStatus.REVIEWED:
        raise HTTPException(status_code=400, detail=f"当前状态[{alloc.status.value}]不能锁定库存")

    for item in alloc.items:
        if data.item_allocations and str(item.id) in data.item_allocations:
            allocate_qty = data.item_allocations[str(item.id)]
        else:
            allocate_qty = item.approved_quantity or item.applied_quantity

        stock = _check_stock_availability(db, item.nursery_stock_id, allocate_qty)

        stock.locked_stock += allocate_qty
        stock.available_stock = stock.total_stock - stock.locked_stock
        item.allocated_quantity = allocate_qty

    alloc.status = models.AllocationStatus.LOCKED
    alloc.locker = data.locker
    alloc.locked_at = datetime.now()

    db.commit()
    db.refresh(alloc)
    return alloc


@router.post("/{allocation_id}/revoke", response_model=schemas.AllocationRequest)
def revoke_allocation(
    allocation_id: int,
    data: schemas.AllocationRequestRevoke,
    db: Session = Depends(get_db),
):
    alloc = db.query(models.AllocationRequest).filter(models.AllocationRequest.id == allocation_id).first()
    if not alloc:
        raise HTTPException(status_code=404, detail="调拨申请不存在")
    if alloc.status not in [models.AllocationStatus.LOCKED, models.AllocationStatus.SHIPPING]:
        raise HTTPException(status_code=400, detail=f"当前状态[{alloc.status.value}]不能撤销(仅锁定或起运状态可撤销)")

    for item in alloc.items:
        if alloc.status == models.AllocationStatus.LOCKED:
            release_qty = item.allocated_quantity or 0
        else:
            release_qty = item.shipped_quantity or 0

        if release_qty > 0:
            stock = db.query(models.NurseryStock).filter(models.NurseryStock.id == item.nursery_stock_id).first()
            if stock:
                if stock.locked_stock >= release_qty:
                    stock.locked_stock -= release_qty
                else:
                    stock.locked_stock = 0
                stock.available_stock = stock.total_stock - stock.locked_stock
        item.allocated_quantity = 0
        item.shipped_quantity = None

    alloc.status = models.AllocationStatus.APPLIED
    alloc.revoker = data.revoker
    alloc.revoke_reason = data.revoke_reason
    alloc.revoked_at = datetime.now()

    db.commit()
    db.refresh(alloc)
    return alloc


@router.post("/{allocation_id}/ship", response_model=schemas.AllocationRequest)
def ship_allocation(
    allocation_id: int,
    data: schemas.AllocationRequestShip,
    db: Session = Depends(get_db),
):
    alloc = db.query(models.AllocationRequest).filter(models.AllocationRequest.id == allocation_id).first()
    if not alloc:
        raise HTTPException(status_code=404, detail="调拨申请不存在")
    if alloc.status != models.AllocationStatus.LOCKED:
        raise HTTPException(status_code=400, detail=f"当前状态[{alloc.status.value}]不能起运")

    for item in alloc.items:
        if data.item_shipments and str(item.id) in data.item_shipments:
            ship_qty = data.item_shipments[str(item.id)]
        else:
            ship_qty = item.allocated_quantity or item.approved_quantity or item.applied_quantity
        if ship_qty > (item.allocated_quantity or 0):
            raise HTTPException(status_code=400, detail=f"明细{item.id}起运数量超过锁定数量")
        item.shipped_quantity = ship_qty

        not_shipped = (item.allocated_quantity or 0) - ship_qty
        if not_shipped > 0:
            stock = db.query(models.NurseryStock).filter(models.NurseryStock.id == item.nursery_stock_id).first()
            if stock:
                if stock.locked_stock >= not_shipped:
                    stock.locked_stock -= not_shipped
                else:
                    stock.locked_stock = 0
                stock.available_stock = stock.total_stock - stock.locked_stock

    alloc.status = models.AllocationStatus.SHIPPING
    alloc.shipper = data.shipper
    alloc.shipping_info = data.shipping_info
    alloc.shipped_at = datetime.now()

    db.commit()
    db.refresh(alloc)
    return alloc


@router.post("/{allocation_id}/receive", response_model=schemas.AllocationRequest)
def receive_allocation(
    allocation_id: int,
    data: schemas.AllocationRequestReceive,
    db: Session = Depends(get_db),
):
    alloc = db.query(models.AllocationRequest).filter(models.AllocationRequest.id == allocation_id).first()
    if not alloc:
        raise HTTPException(status_code=404, detail="调拨申请不存在")
    if alloc.status != models.AllocationStatus.SHIPPING:
        raise HTTPException(status_code=400, detail=f"当前状态[{alloc.status.value}]不能签收")

    for item in alloc.items:
        if data.item_receives and str(item.id) in data.item_receives:
            recv_qty = data.item_receives[str(item.id)]
        else:
            recv_qty = item.shipped_quantity or item.allocated_quantity
        if recv_qty > (item.shipped_quantity or 0):
            raise HTTPException(status_code=400, detail=f"明细{item.id}签收数量超过起运数量")
        item.received_quantity = recv_qty

        stock = db.query(models.NurseryStock).filter(models.NurseryStock.id == item.nursery_stock_id).first()
        if stock:
            still_locked = item.shipped_quantity or 0
            if stock.locked_stock >= still_locked:
                stock.locked_stock -= still_locked
            else:
                stock.locked_stock = 0
            if stock.total_stock >= recv_qty:
                stock.total_stock -= recv_qty
            stock.available_stock = stock.total_stock - stock.locked_stock

    alloc.status = models.AllocationStatus.RECEIVED
    alloc.receiver = data.receiver
    alloc.received_at = datetime.now()

    db.commit()
    db.refresh(alloc)
    return alloc


@router.post("/{allocation_id}/planting", response_model=List[schemas.PlantingRecord])
def record_planting(
    allocation_id: int,
    data: schemas.PlantingRecordCreate,
    db: Session = Depends(get_db),
):
    alloc = db.query(models.AllocationRequest).filter(models.AllocationRequest.id == allocation_id).first()
    if not alloc:
        raise HTTPException(status_code=404, detail="调拨申请不存在")
    if alloc.status != models.AllocationStatus.RECEIVED:
        raise HTTPException(status_code=400, detail=f"当前状态[{alloc.status.value}]，签收后才能登记栽植")
    if data.allocation_id != allocation_id:
        raise HTTPException(status_code=400, detail="allocation_id不匹配")

    existing = db.query(models.PlantingRecord).filter(
        models.PlantingRecord.allocation_id == allocation_id
    ).first()
    if existing:
        raise HTTPException(status_code=400, detail="该调拨已登记栽植信息，不可重复登记")

    records = []
    for ri in data.items:
        item = db.query(models.AllocationItem).filter(
            models.AllocationItem.id == ri.allocation_item_id,
            models.AllocationItem.allocation_id == allocation_id,
        ).first()
        if not item:
            raise HTTPException(status_code=400, detail=f"调拨明细不存在(item_id={ri.allocation_item_id})")
        if ri.planted_quantity > (item.received_quantity or 0):
            raise HTTPException(
                status_code=400,
                detail=f"规格[{ri.spec_name}]栽植数量{ri.planted_quantity}超过签收数量{item.received_quantity}"
            )
        if ri.survived_judgement > ri.planted_quantity:
            raise HTTPException(status_code=400, detail=f"规格[{ri.spec_name}]成活初判数不能超过栽植数")

        survival_rate = round(ri.survived_judgement / ri.planted_quantity * 100, 2) if ri.planted_quantity > 0 else 0.0
        record = models.PlantingRecord(
            allocation_id=allocation_id,
            allocation_item_id=ri.allocation_item_id,
            plot_id=data.plot_id,
            spec_name=ri.spec_name,
            planted_quantity=ri.planted_quantity,
            survived_judgement=ri.survived_judgement,
            survival_rate=survival_rate,
            record_date=data.record_date or datetime.now(),
            recorder=data.recorder,
            remark=ri.remark,
        )
        db.add(record)
        records.append(record)

        req = db.query(models.PlotRequirement).filter(
            models.PlotRequirement.plot_id == data.plot_id,
            models.PlotRequirement.spec_name == ri.spec_name,
        ).first()
        if req:
            req.planted_quantity = (req.planted_quantity or 0) + ri.planted_quantity

    db.commit()
    for r in records:
        db.refresh(r)
    return records


@router.get("/{allocation_id}/planting", response_model=List[schemas.PlantingRecord])
def get_planting_records(allocation_id: int, db: Session = Depends(get_db)):
    alloc = db.query(models.AllocationRequest).filter(models.AllocationRequest.id == allocation_id).first()
    if not alloc:
        raise HTTPException(status_code=404, detail="调拨申请不存在")
    return db.query(models.PlantingRecord).filter(
        models.PlantingRecord.allocation_id == allocation_id
    ).all()
