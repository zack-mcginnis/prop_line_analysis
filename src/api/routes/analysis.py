"""Analysis endpoints for thesis validation."""

from datetime import datetime, timezone
from typing import Optional, List

from fastapi import APIRouter, Depends, HTTPException, Query, BackgroundTasks
from pydantic import BaseModel
from sqlalchemy.orm import Session

from src.models.database import AnalysisResult, PropType, get_session
from src.analysis.correlation import CorrelationAnalyzer, run_full_analysis

router = APIRouter()


class AnalysisResultResponse(BaseModel):
    """Response model for an analysis result."""
    id: int
    analysis_name: str
    prop_type: Optional[str]
    movement_threshold_pct: Optional[float]
    movement_threshold_abs: Optional[float]
    hours_before_threshold: Optional[float]
    sample_size: int
    over_count: int
    under_count: int
    push_count: int
    over_rate: float
    under_rate: float
    p_value: Optional[float]
    is_significant: Optional[bool]
    confidence_interval_low: Optional[float]
    confidence_interval_high: Optional[float]
    baseline_over_rate: Optional[float]
    baseline_sample_size: Optional[int]
    created_at: datetime
    
    class Config:
        from_attributes = True


class ThesisSummary(BaseModel):
    """Summary of the thesis analysis."""
    thesis: str
    conclusion: str
    is_supported: bool
    key_finding: str
    sample_size: int
    under_rate: float
    over_rate: float
    p_value: Optional[float]
    is_significant: bool
    recommendations: List[str]


@router.get("/results", response_model=List[AnalysisResultResponse])
async def get_analysis_results(
    prop_type: Optional[str] = Query(None),
    is_significant: Optional[bool] = Query(None),
):
    """Get all analysis results."""
    session = get_session()
    try:
        query = session.query(AnalysisResult)
        
        if prop_type:
            if prop_type == "all":
                query = query.filter(AnalysisResult.prop_type.is_(None))
            else:
                try:
                    pt = PropType(prop_type)
                    query = query.filter(AnalysisResult.prop_type == pt)
                except ValueError:
                    raise HTTPException(status_code=400, detail=f"Invalid prop_type: {prop_type}")
        
        if is_significant is not None:
            query = query.filter(AnalysisResult.is_significant == is_significant)
        
        results = query.order_by(AnalysisResult.analysis_name).all()
        
        return [
            AnalysisResultResponse(
                id=r.id,
                analysis_name=r.analysis_name,
                prop_type=r.prop_type.value if r.prop_type else None,
                movement_threshold_pct=float(r.movement_threshold_pct) if r.movement_threshold_pct else None,
                movement_threshold_abs=float(r.movement_threshold_abs) if r.movement_threshold_abs else None,
                hours_before_threshold=float(r.hours_before_threshold) if r.hours_before_threshold else None,
                sample_size=r.sample_size,
                over_count=r.over_count,
                under_count=r.under_count,
                push_count=r.push_count,
                over_rate=float(r.over_rate),
                under_rate=float(r.under_rate),
                p_value=float(r.p_value) if r.p_value else None,
                is_significant=r.is_significant,
                confidence_interval_low=float(r.confidence_interval_low) if r.confidence_interval_low else None,
                confidence_interval_high=float(r.confidence_interval_high) if r.confidence_interval_high else None,
                baseline_over_rate=float(r.baseline_over_rate) if r.baseline_over_rate else None,
                baseline_sample_size=r.baseline_sample_size,
                created_at=r.created_at,
            )
            for r in results
        ]
    finally:
        session.close()


@router.get("/thesis-summary", response_model=ThesisSummary)
async def get_thesis_summary():
    """Get a summary of the thesis validation analysis."""
    session = get_session()
    try:
        # Find the main analysis (10% threshold, 3 hours, all props)
        result = (
            session.query(AnalysisResult)
            .filter(AnalysisResult.analysis_name.contains("pct10"))
            .filter(AnalysisResult.analysis_name.contains("hrs3"))
            .filter(AnalysisResult.analysis_name.contains("all"))
            .first()
        )
        
        if not result:
            raise HTTPException(
                status_code=404,
                detail="Thesis analysis not found. Run the analysis first."
            )
        
        under_rate = float(result.under_rate) * 100
        over_rate = float(result.over_rate) * 100
        is_supported = result.is_significant and under_rate > 55
        
        if is_supported:
            conclusion = (
                f"The thesis is SUPPORTED. When player prop lines dropped significantly "
                f"({result.movement_threshold_pct}%+ or {result.movement_threshold_abs}+ yards) "
                f"within {result.hours_before_threshold} hours of kickoff, "
                f"players went UNDER their line {under_rate:.1f}% of the time."
            )
            key_finding = f"Under rate of {under_rate:.1f}% is statistically significant (p < 0.05)"
        elif under_rate > 50:
            conclusion = (
                f"The thesis shows a TREND but is not statistically significant. "
                f"Players went under {under_rate:.1f}% of the time when lines dropped significantly."
            )
            key_finding = f"Under rate of {under_rate:.1f}% suggests a pattern, but more data needed"
        else:
            conclusion = (
                f"The thesis is NOT SUPPORTED. Players went under only {under_rate:.1f}% "
                f"of the time when lines dropped significantly."
            )
            key_finding = f"Under rate of {under_rate:.1f}% does not support the thesis"
        
        recommendations = []
        if result.sample_size < 100:
            recommendations.append("Collect more data to increase statistical power")
        if not result.is_significant:
            recommendations.append("Consider adjusting thresholds to find significant patterns")
        if is_supported:
            recommendations.append("Monitor for lines dropping 10%+ within 3 hours of kickoff")
            recommendations.append("Consider betting the under when significant late drops occur")
        
        return ThesisSummary(
            thesis=(
                "Large drops in yardage prop lines close to kickoff (within 3 hours) "
                "correlate with players going UNDER their prop line."
            ),
            conclusion=conclusion,
            is_supported=is_supported,
            key_finding=key_finding,
            sample_size=result.sample_size,
            under_rate=under_rate,
            over_rate=over_rate,
            p_value=float(result.p_value) if result.p_value else None,
            is_significant=result.is_significant or False,
            recommendations=recommendations,
        )
    finally:
        session.close()


@router.post("/run")
async def trigger_analysis(background_tasks: BackgroundTasks):
    """Trigger the full thesis analysis as a background task."""
    def run_in_background():
        report = run_full_analysis()
        print(report)
    
    background_tasks.add_task(run_in_background)
    
    return {
        "status": "started",
        "message": "Analysis started in background. Check /api/analysis/results when complete.",
    }


@router.get("/report")
async def get_analysis_report():
    """Get a formatted text report of all analysis results."""
    session = get_session()
    try:
        analyzer = CorrelationAnalyzer()
        report = analyzer.get_summary_report(session)
        
        return {
            "report": report,
            "generated_at": datetime.now(timezone.utc).isoformat(),
        }
    finally:
        session.close()


@router.get("/compare")
async def compare_thresholds(
    prop_type: Optional[str] = Query(None),
):
    """Compare results across different threshold combinations."""
    session = get_session()
    try:
        query = session.query(AnalysisResult)
        
        if prop_type:
            if prop_type == "all":
                query = query.filter(AnalysisResult.prop_type.is_(None))
            else:
                try:
                    pt = PropType(prop_type)
                    query = query.filter(AnalysisResult.prop_type == pt)
                except ValueError:
                    raise HTTPException(status_code=400, detail=f"Invalid prop_type: {prop_type}")
        
        results = query.order_by(AnalysisResult.under_rate.desc()).all()
        
        comparison = []
        for r in results:
            comparison.append({
                "name": r.analysis_name,
                "thresholds": {
                    "pct": float(r.movement_threshold_pct) if r.movement_threshold_pct else None,
                    "abs": float(r.movement_threshold_abs) if r.movement_threshold_abs else None,
                    "hours": float(r.hours_before_threshold) if r.hours_before_threshold else None,
                },
                "sample_size": r.sample_size,
                "under_rate": float(r.under_rate) * 100,
                "over_rate": float(r.over_rate) * 100,
                "is_significant": r.is_significant,
                "p_value": float(r.p_value) if r.p_value else None,
            })
        
        # Find best threshold combination
        best = None
        for c in comparison:
            if c["is_significant"] and c["sample_size"] >= 30:
                if best is None or c["under_rate"] > best["under_rate"]:
                    best = c
        
        return {
            "comparisons": comparison,
            "best_threshold": best,
            "recommendation": (
                f"Best results with {best['thresholds']} - {best['under_rate']:.1f}% under rate"
                if best else "No statistically significant threshold found"
            ),
        }
    finally:
        session.close()

