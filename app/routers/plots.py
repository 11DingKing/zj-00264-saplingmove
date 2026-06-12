from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List

from app.database import get_db
from app import models, schemas

router = APIRouter(prefix="/api/plots", tags=["修复地块"])


@router.get("", response_model=List[schemas.RestorationPlot])
def list_plots(project: str = None, region: str = None, db: Session = Depends(get_db)):
    query = db.query(models.RestorationPlot)
    if project:
        query = query.filter(models.RestorationPlot.project.contains(project))
    if region:
        query = query.filter(models.RestorationPlot.region.contains(region))
    return query.all()


@router.get("/{plot_id}", response_model=schemas.RestorationPlot)
def get_plot(plot_id: int, db: Session = Depends(get_db)):
    plot = db.query(models.RestorationPlot).filter(models.RestorationPlot.id == plot_id).first()
    if not plot:
        raise HTTPException(status_code=404, detail="地块不存在")
    return plot


@router.post("", response_model=schemas.RestorationPlot)
def create_plot(data: schemas.RestorationPlotCreate, db: Session = Depends(get_db)):
    plot = models.RestorationPlot(**data.model_dump())
    db.add(plot)
    db.commit()
    db.refresh(plot)
    return plot


@router.put("/{plot_id}", response_model=schemas.RestorationPlot)
def update_plot(plot_id: int, data: schemas.RestorationPlotUpdate, db: Session = Depends(get_db)):
    plot = db.query(models.RestorationPlot).filter(models.RestorationPlot.id == plot_id).first()
    if not plot:
        raise HTTPException(status_code=404, detail="地块不存在")
    for key, value in data.model_dump(exclude_unset=True).items():
        setattr(plot, key, value)
    db.commit()
    db.refresh(plot)
    return plot


@router.delete("/{plot_id}")
def delete_plot(plot_id: int, db: Session = Depends(get_db)):
    plot = db.query(models.RestorationPlot).filter(models.RestorationPlot.id == plot_id).first()
    if not plot:
        raise HTTPException(status_code=404, detail="地块不存在")
    db.delete(plot)
    db.commit()
    return {"message": "删除成功"}


@router.get("/{plot_id}/requirements", response_model=List[schemas.PlotRequirement])
def list_plot_requirements(plot_id: int, db: Session = Depends(get_db)):
    plot = db.query(models.RestorationPlot).filter(models.RestorationPlot.id == plot_id).first()
    if not plot:
        raise HTTPException(status_code=404, detail="地块不存在")
    return db.query(models.PlotRequirement).filter(models.PlotRequirement.plot_id == plot_id).all()


@router.post("/{plot_id}/requirements", response_model=schemas.PlotRequirement)
def create_plot_requirement(plot_id: int, data: schemas.PlotRequirementCreate, db: Session = Depends(get_db)):
    plot = db.query(models.RestorationPlot).filter(models.RestorationPlot.id == plot_id).first()
    if not plot:
        raise HTTPException(status_code=404, detail="地块不存在")
    req_data = data.model_dump()
    req_data["plot_id"] = plot_id
    req = models.PlotRequirement(**req_data)
    db.add(req)
    db.commit()
    db.refresh(req)
    return req


@router.put("/requirements/{req_id}", response_model=schemas.PlotRequirement)
def update_plot_requirement(req_id: int, data: schemas.PlotRequirementUpdate, db: Session = Depends(get_db)):
    req = db.query(models.PlotRequirement).filter(models.PlotRequirement.id == req_id).first()
    if not req:
        raise HTTPException(status_code=404, detail="需苗计划不存在")
    for key, value in data.model_dump(exclude_unset=True).items():
        setattr(req, key, value)
    db.commit()
    db.refresh(req)
    return req


@router.delete("/requirements/{req_id}")
def delete_plot_requirement(req_id: int, db: Session = Depends(get_db)):
    req = db.query(models.PlotRequirement).filter(models.PlotRequirement.id == req_id).first()
    if not req:
        raise HTTPException(status_code=404, detail="需苗计划不存在")
    db.delete(req)
    db.commit()
    return {"message": "删除成功"}


@router.get("/gaps/all", response_model=List[schemas.PlotGapSummary])
def list_all_requirements_with_gap(
    project: str = None,
    region: str = None,
    has_gap_only: bool = False,
    db: Session = Depends(get_db),
):
    query = db.query(models.PlotRequirement).join(models.RestorationPlot)
    if project:
        query = query.filter(models.RestorationPlot.project.contains(project))
    if region:
        query = query.filter(models.RestorationPlot.region.contains(region))
    reqs = query.all()
    result = []
    for req in reqs:
        gap = req.required_quantity - req.received_quantity
        if has_gap_only and gap <= 0:
            continue
        fulfillment_rate = round(req.received_quantity / req.required_quantity * 100, 2) if req.required_quantity > 0 else 0.0
        result.append(schemas.PlotGapSummary(
            plot_id=req.plot_id,
            plot_name=req.plot.name,
            project=req.plot.project,
            region=req.plot.region,
            spec_name=req.spec_name,
            required_quantity=req.required_quantity,
            received_quantity=req.received_quantity,
            gap_quantity=gap if gap > 0 else 0,
            fulfillment_rate=fulfillment_rate,
        ))
    return sorted(result, key=lambda x: (-x.gap_quantity, x.plot_id))


@router.get("/{plot_id}/requirements-with-gap", response_model=List[schemas.PlotRequirementWithGap])
def list_plot_requirements_with_gap(plot_id: int, db: Session = Depends(get_db)):
    plot = db.query(models.RestorationPlot).filter(models.RestorationPlot.id == plot_id).first()
    if not plot:
        raise HTTPException(status_code=404, detail="地块不存在")
    reqs = db.query(models.PlotRequirement).filter(models.PlotRequirement.plot_id == plot_id).all()
    result = []
    for req in reqs:
        gap = req.required_quantity - req.received_quantity
        fulfillment_rate = round(req.received_quantity / req.required_quantity * 100, 2) if req.required_quantity > 0 else 0.0
        result.append(schemas.PlotRequirementWithGap(
            id=req.id,
            plot_id=req.plot_id,
            spec_name=req.spec_name,
            required_quantity=req.required_quantity,
            remark=req.remark,
            received_quantity=req.received_quantity,
            planted_quantity=req.planted_quantity,
            created_at=req.created_at,
            updated_at=req.updated_at,
            gap_quantity=gap if gap > 0 else 0,
            fulfillment_rate=fulfillment_rate,
        ))
    return result
