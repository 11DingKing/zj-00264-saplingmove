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
