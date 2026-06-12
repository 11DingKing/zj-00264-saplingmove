from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy.sql import func
from typing import List, Optional

from app.database import get_db
from app import models, schemas

router = APIRouter(prefix="/api/stats", tags=["统计分析"])


@router.get("/by-spec", response_model=List[schemas.StatBySpec])
def stats_by_spec(
    spec_name: Optional[str] = None,
    db: Session = Depends(get_db),
):
    query = db.query(
        models.AllocationItem.spec_name,
        func.coalesce(func.sum(models.AllocationItem.allocated_quantity), 0).label("total_allocated"),
        func.coalesce(func.sum(models.AllocationItem.received_quantity), 0).label("total_received"),
    ).join(
        models.AllocationRequest,
        models.AllocationItem.allocation_id == models.AllocationRequest.id,
    ).filter(
        models.AllocationRequest.status.in_([
            models.AllocationStatus.LOCKED,
            models.AllocationStatus.SHIPPING,
            models.AllocationStatus.RECEIVED,
        ])
    )
    if spec_name:
        query = query.filter(models.AllocationItem.spec_name.contains(spec_name))
    query = query.group_by(models.AllocationItem.spec_name)
    items = query.all()

    planting_stats = db.query(
        models.PlantingRecord.spec_name,
        func.coalesce(func.sum(models.PlantingRecord.planted_quantity), 0).label("total_planted"),
        func.coalesce(func.sum(models.PlantingRecord.survived_judgement), 0).label("total_survived"),
    ).group_by(models.PlantingRecord.spec_name).all()

    planting_map = {row.spec_name: (row.total_planted, row.total_survived) for row in planting_stats}

    results = []
    for row in items:
        receive_rate = round(row.total_received / row.total_allocated * 100, 2) if row.total_allocated > 0 else 0.0
        planted, survived = planting_map.get(row.spec_name, (0, 0))
        survival_rate = round(survived / planted * 100, 2) if planted > 0 else 0.0
        results.append(schemas.StatBySpec(
            spec_name=row.spec_name,
            total_allocated=row.total_allocated or 0,
            total_received=row.total_received or 0,
            receive_rate=receive_rate,
            total_planted=planted or 0,
            total_survived=survived or 0,
            survival_rate=survival_rate,
        ))
    return results


@router.get("/by-plot", response_model=List[schemas.StatByPlot])
def stats_by_plot(
    project: Optional[str] = None,
    region: Optional[str] = None,
    db: Session = Depends(get_db),
):
    alloc_query = db.query(
        models.AllocationRequest.plot_id,
        func.coalesce(func.sum(models.AllocationItem.allocated_quantity), 0).label("total_allocated"),
        func.coalesce(func.sum(models.AllocationItem.received_quantity), 0).label("total_received"),
    ).join(
        models.AllocationItem,
        models.AllocationItem.allocation_id == models.AllocationRequest.id,
    ).filter(
        models.AllocationRequest.status.in_([
            models.AllocationStatus.LOCKED,
            models.AllocationStatus.SHIPPING,
            models.AllocationStatus.RECEIVED,
        ])
    ).group_by(models.AllocationRequest.plot_id)
    alloc_rows = alloc_query.all()
    alloc_map = {row.plot_id: (row.total_allocated, row.total_received) for row in alloc_rows}

    plant_query = db.query(
        models.PlantingRecord.plot_id,
        func.coalesce(func.sum(models.PlantingRecord.planted_quantity), 0).label("total_planted"),
        func.coalesce(func.sum(models.PlantingRecord.survived_judgement), 0).label("total_survived"),
    ).group_by(models.PlantingRecord.plot_id)
    plant_rows = plant_query.all()
    plant_map = {row.plot_id: (row.total_planted, row.total_survived) for row in plant_rows}

    plot_query = db.query(models.RestorationPlot)
    if project:
        plot_query = plot_query.filter(models.RestorationPlot.project.contains(project))
    if region:
        plot_query = plot_query.filter(models.RestorationPlot.region.contains(region))
    plots = plot_query.all()

    results = []
    for plot in plots:
        allocated, received = alloc_map.get(plot.id, (0, 0))
        receive_rate = round(received / allocated * 100, 2) if allocated > 0 else 0.0
        planted, survived = plant_map.get(plot.id, (0, 0))
        survival_rate = round(survived / planted * 100, 2) if planted > 0 else 0.0
        results.append(schemas.StatByPlot(
            plot_id=plot.id,
            plot_name=plot.name,
            project=plot.project,
            region=plot.region,
            total_allocated=allocated or 0,
            total_received=received or 0,
            receive_rate=receive_rate,
            total_planted=planted or 0,
            total_survived=survived or 0,
            survival_rate=survival_rate,
        ))
    return results


@router.get("/by-plot-spec", response_model=List[schemas.StatByPlotSpec])
def stats_by_plot_spec(
    plot_id: Optional[int] = None,
    spec_name: Optional[str] = None,
    db: Session = Depends(get_db),
):
    alloc_query = db.query(
        models.AllocationRequest.plot_id,
        models.AllocationItem.spec_name,
        func.coalesce(func.sum(models.AllocationItem.allocated_quantity), 0).label("total_allocated"),
        func.coalesce(func.sum(models.AllocationItem.received_quantity), 0).label("total_received"),
    ).join(
        models.AllocationItem,
        models.AllocationItem.allocation_id == models.AllocationRequest.id,
    ).filter(
        models.AllocationRequest.status.in_([
            models.AllocationStatus.LOCKED,
            models.AllocationStatus.SHIPPING,
            models.AllocationStatus.RECEIVED,
        ])
    )
    if plot_id:
        alloc_query = alloc_query.filter(models.AllocationRequest.plot_id == plot_id)
    if spec_name:
        alloc_query = alloc_query.filter(models.AllocationItem.spec_name.contains(spec_name))
    alloc_query = alloc_query.group_by(models.AllocationRequest.plot_id, models.AllocationItem.spec_name)
    alloc_rows = alloc_query.all()

    plant_query = db.query(
        models.PlantingRecord.plot_id,
        models.PlantingRecord.spec_name,
        func.coalesce(func.sum(models.PlantingRecord.planted_quantity), 0).label("total_planted"),
        func.coalesce(func.sum(models.PlantingRecord.survived_judgement), 0).label("total_survived"),
    )
    if plot_id:
        plant_query = plant_query.filter(models.PlantingRecord.plot_id == plot_id)
    if spec_name:
        plant_query = plant_query.filter(models.PlantingRecord.spec_name.contains(spec_name))
    plant_query = plant_query.group_by(models.PlantingRecord.plot_id, models.PlantingRecord.spec_name)
    plant_rows = plant_query.all()
    plant_map = {(r.plot_id, r.spec_name): (r.total_planted, r.total_survived) for r in plant_rows}

    plot_ids = set()
    spec_by_plot = {}
    for row in alloc_rows:
        plot_ids.add(row.plot_id)
        key = (row.plot_id, row.spec_name)
        if key not in spec_by_plot:
            spec_by_plot[key] = [0, 0]
        spec_by_plot[key][0] += row.total_allocated or 0
        spec_by_plot[key][1] += row.total_received or 0
    for (pid, sp), (pl, su) in plant_map.items():
        plot_ids.add(pid)
        key = (pid, sp)
        if key not in spec_by_plot:
            spec_by_plot[key] = [0, 0]

    plots = db.query(models.RestorationPlot).filter(
        models.RestorationPlot.id.in_(list(plot_ids)) if plot_ids else True
    ).all()
    plot_map = {p.id: p.name for p in plots}

    results = []
    for (pid, sp), (allocated, received) in spec_by_plot.items():
        receive_rate = round(received / allocated * 100, 2) if allocated > 0 else 0.0
        planted, survived = plant_map.get((pid, sp), (0, 0))
        survival_rate = round(survived / planted * 100, 2) if planted > 0 else 0.0
        results.append(schemas.StatByPlotSpec(
            plot_id=pid,
            plot_name=plot_map.get(pid, f"地块{pid}"),
            spec_name=sp,
            total_allocated=allocated or 0,
            total_received=received or 0,
            receive_rate=receive_rate,
            total_planted=planted or 0,
            total_survived=survived or 0,
            survival_rate=survival_rate,
        ))
    return results


@router.get("/gap-by-spec", response_model=List[schemas.GapBySpec])
def stats_gap_by_spec(
    spec_name: Optional[str] = None,
    has_gap_only: bool = True,
    db: Session = Depends(get_db),
):
    query = db.query(
        models.PlotRequirement.spec_name,
        func.coalesce(func.sum(models.PlotRequirement.required_quantity), 0).label("total_required"),
        func.coalesce(func.sum(models.PlotRequirement.received_quantity), 0).label("total_received"),
        func.count(func.distinct(models.PlotRequirement.plot_id)).label("affected_plots"),
    )
    if spec_name:
        query = query.filter(models.PlotRequirement.spec_name.contains(spec_name))
    query = query.group_by(models.PlotRequirement.spec_name)
    rows = query.all()

    results = []
    for row in rows:
        gap = (row.total_required or 0) - (row.total_received or 0)
        if has_gap_only and gap <= 0:
            continue
        results.append(schemas.GapBySpec(
            spec_name=row.spec_name,
            total_required=row.total_required or 0,
            total_received=row.total_received or 0,
            total_gap=gap if gap > 0 else 0,
            affected_plots=row.affected_plots or 0,
        ))
    return sorted(results, key=lambda x: -x.total_gap)


@router.get("/dispatch", response_model=List[schemas.DispatchRecommendation])
def stats_dispatch(
    spec_name: Optional[str] = None,
    db: Session = Depends(get_db),
):
    gap_specs = db.query(
        models.PlotRequirement.spec_name,
        func.coalesce(func.sum(models.PlotRequirement.required_quantity), 0).label("total_required"),
        func.coalesce(func.sum(models.PlotRequirement.received_quantity), 0).label("total_received"),
    )
    if spec_name:
        gap_specs = gap_specs.filter(models.PlotRequirement.spec_name.contains(spec_name))
    gap_specs = gap_specs.group_by(models.PlotRequirement.spec_name).all()

    stock_query = db.query(
        models.NurseryStock.spec_name,
        func.coalesce(func.sum(models.NurseryStock.available_stock), 0).label("total_available"),
    ).group_by(models.NurseryStock.spec_name).all()
    stock_map = {row.spec_name: (row.total_available or 0) for row in stock_query}

    results = []
    for row in gap_specs:
        gap = (row.total_required or 0) - (row.total_received or 0)
        if gap <= 0:
            continue

        plot_gaps = db.query(models.PlotRequirement).filter(
            models.PlotRequirement.spec_name == row.spec_name,
            (models.PlotRequirement.required_quantity - models.PlotRequirement.received_quantity) > 0,
        ).join(models.RestorationPlot).all()

        plots_needing = []
        for pg in plot_gaps:
            pg_gap = pg.required_quantity - pg.received_quantity
            fulfillment_rate = round(pg.received_quantity / pg.required_quantity * 100, 2) if pg.required_quantity > 0 else 0.0
            plots_needing.append(schemas.PlotGapSummary(
                plot_id=pg.plot_id,
                plot_name=pg.plot.name,
                project=pg.plot.project,
                region=pg.plot.region,
                spec_name=pg.spec_name,
                required_quantity=pg.required_quantity,
                received_quantity=pg.received_quantity,
                gap_quantity=pg_gap if pg_gap > 0 else 0,
                fulfillment_rate=fulfillment_rate,
            ))
        plots_needing.sort(key=lambda x: (-x.gap_quantity, x.fulfillment_rate))

        results.append(schemas.DispatchRecommendation(
            spec_name=row.spec_name,
            total_gap=gap if gap > 0 else 0,
            total_available=stock_map.get(row.spec_name, 0),
            plots_needing=plots_needing,
        ))
    return sorted(results, key=lambda x: -x.total_gap)


@router.get("/summary")
def stats_summary(db: Session = Depends(get_db)):
    total_nurseries = db.query(func.count(models.Nursery.id)).scalar() or 0
    total_stock = db.query(func.coalesce(func.sum(models.NurseryStock.total_stock), 0)).scalar() or 0
    available_stock = db.query(func.coalesce(func.sum(models.NurseryStock.available_stock), 0)).scalar() or 0
    locked_stock = db.query(func.coalesce(func.sum(models.NurseryStock.locked_stock), 0)).scalar() or 0
    total_plots = db.query(func.count(models.RestorationPlot.id)).scalar() or 0
    total_area = db.query(func.coalesce(func.sum(models.RestorationPlot.area_mu), 0)).scalar() or 0
    total_req = db.query(func.coalesce(func.sum(models.PlotRequirement.required_quantity), 0)).scalar() or 0
    req_received = db.query(func.coalesce(func.sum(models.PlotRequirement.received_quantity), 0)).scalar() or 0
    req_planted = db.query(func.coalesce(func.sum(models.PlotRequirement.planted_quantity), 0)).scalar() or 0
    total_gap = max(0, (total_req or 0) - (req_received or 0))

    gap_specs = db.query(
        models.PlotRequirement.spec_name,
    ).group_by(models.PlotRequirement.spec_name).having(
        (func.sum(models.PlotRequirement.required_quantity) - func.sum(models.PlotRequirement.received_quantity)) > 0
    ).count()

    gap_plots = db.query(
        models.PlotRequirement.plot_id,
    ).group_by(models.PlotRequirement.plot_id).having(
        (func.sum(models.PlotRequirement.required_quantity) - func.sum(models.PlotRequirement.received_quantity)) > 0
    ).count()

    alloc_query = db.query(
        func.count(models.AllocationRequest.id).label("count"),
        func.coalesce(func.sum(models.AllocationItem.allocated_quantity), 0).label("allocated"),
        func.coalesce(func.sum(models.AllocationItem.received_quantity), 0).label("received"),
    ).join(models.AllocationItem, models.AllocationItem.allocation_id == models.AllocationRequest.id, isouter=True)
    alloc_row = alloc_query.first()

    status_counts = db.query(
        models.AllocationRequest.status,
        func.count(models.AllocationRequest.id),
    ).group_by(models.AllocationRequest.status).all()
    status_map = {s.value: c for s, c in status_counts}

    planted_qty = db.query(func.coalesce(func.sum(models.PlantingRecord.planted_quantity), 0)).scalar() or 0
    survived_qty = db.query(func.coalesce(func.sum(models.PlantingRecord.survived_judgement), 0)).scalar() or 0

    return {
        "nurseries": {
            "total": total_nurseries,
            "total_stock": total_stock,
            "available_stock": available_stock,
            "locked_stock": locked_stock,
        },
        "plots": {
            "total": total_plots,
            "total_area_mu": round(total_area or 0, 2),
            "required_seedlings": total_req,
            "received_from_requirement": req_received,
            "planted_from_requirement": req_planted,
            "total_gap": total_gap,
            "gap_specs_count": gap_specs,
            "gap_plots_count": gap_plots,
            "requirement_fulfillment_rate": round(req_received / total_req * 100, 2) if total_req > 0 else 0.0,
        },
        "allocations": {
            "total_requests": alloc_row.count or 0,
            "total_allocated": alloc_row.allocated or 0,
            "total_received": alloc_row.received or 0,
            "overall_receive_rate": round(
                (alloc_row.received or 0) / (alloc_row.allocated or 0) * 100, 2
            ) if (alloc_row.allocated or 0) > 0 else 0.0,
            "status_counts": status_map,
        },
        "planting": {
            "total_planted": planted_qty,
            "total_survived_judgement": survived_qty,
            "overall_survival_rate": round(survived_qty / planted_qty * 100, 2) if planted_qty > 0 else 0.0,
        },
    }
