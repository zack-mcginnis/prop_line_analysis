"""Correlation analysis for line movements and player performance."""

from datetime import datetime, timezone
from decimal import Decimal
from typing import List, Dict, Any, Optional, Tuple

import numpy as np
from scipy import stats as scipy_stats
from sqlalchemy import func, and_
from sqlalchemy.orm import Session

from src.config import get_settings
from src.models.database import (
    LineMovement,
    AnalysisResult,
    PropType,
    get_session,
)


class CorrelationAnalyzer:
    """
    Analyzes correlations between line movements and player performance.
    
    This is the core analysis that tests the thesis:
    "Large drops in yardage prop lines close to kickoff correlate with
    players going under their prop line."
    """
    
    def __init__(self):
        self.settings = get_settings()
    
    def get_movements_with_results(
        self,
        session: Session,
        prop_type: Optional[PropType] = None,
        min_movement_pct: Optional[float] = None,
        min_movement_abs: Optional[float] = None,
        max_hours_before: Optional[float] = None,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
    ) -> List[LineMovement]:
        """
        Get line movements that have matched game results.
        
        Args:
            session: Database session
            prop_type: Filter by prop type
            min_movement_pct: Minimum absolute percentage drop
            min_movement_abs: Minimum absolute yards drop
            max_hours_before: Maximum hours before kickoff
            start_date: Filter by game date
            end_date: Filter by game date
            
        Returns:
            List of LineMovement objects
        """
        query = (
            session.query(LineMovement)
            .filter(LineMovement.actual_yards.isnot(None))
        )
        
        if prop_type:
            query = query.filter(LineMovement.prop_type == prop_type)
        
        if min_movement_pct:
            # Movement is negative for drops, so we filter for <= -threshold
            query = query.filter(LineMovement.movement_pct <= -min_movement_pct)
        
        if min_movement_abs:
            query = query.filter(LineMovement.movement_absolute <= -min_movement_abs)
        
        if max_hours_before:
            query = query.filter(LineMovement.hours_before_kickoff <= max_hours_before)
        
        if start_date:
            query = query.filter(LineMovement.game_commence_time >= start_date)
        
        if end_date:
            query = query.filter(LineMovement.game_commence_time <= end_date)
        
        return query.all()
    
    def calculate_over_under_rates(
        self,
        movements: List[LineMovement],
    ) -> Dict[str, Any]:
        """
        Calculate over/under rates for a set of movements.
        
        Args:
            movements: List of movements with results
            
        Returns:
            Dict with rates and counts
        """
        total = len(movements)
        
        if total == 0:
            return {
                "total": 0,
                "over_count": 0,
                "under_count": 0,
                "push_count": 0,
                "over_rate": None,
                "under_rate": None,
            }
        
        over_count = sum(1 for m in movements if m.went_over)
        under_count = sum(1 for m in movements if m.went_under)
        push_count = total - over_count - under_count
        
        over_rate = Decimal(str(over_count / total))
        under_rate = Decimal(str(under_count / total))
        
        return {
            "total": total,
            "over_count": over_count,
            "under_count": under_count,
            "push_count": push_count,
            "over_rate": over_rate,
            "under_rate": under_rate,
        }
    
    def calculate_baseline_rates(
        self,
        session: Session,
        prop_type: Optional[PropType] = None,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
    ) -> Dict[str, Any]:
        """
        Calculate baseline over/under rates for props WITHOUT significant movement.
        
        This is the control group for comparison.
        
        Args:
            session: Database session
            prop_type: Filter by prop type
            start_date: Filter by date
            end_date: Filter by date
            
        Returns:
            Dict with baseline rates
        """
        # Get all movements (including non-significant ones would require
        # tracking all props, not just significant movements)
        # For now, we'll use the inverse - all movements NOT meeting
        # the significance threshold
        settings = get_settings()
        
        query = (
            session.query(LineMovement)
            .filter(LineMovement.actual_yards.isnot(None))
        )
        
        if prop_type:
            query = query.filter(LineMovement.prop_type == prop_type)
        
        if start_date:
            query = query.filter(LineMovement.game_commence_time >= start_date)
        
        if end_date:
            query = query.filter(LineMovement.game_commence_time <= end_date)
        
        # Get movements that are NOT significant (small movements)
        # These serve as a baseline
        query = query.filter(
            and_(
                LineMovement.movement_pct > -settings.line_movement_threshold_pct,
                LineMovement.movement_absolute > -settings.line_movement_threshold_abs,
            )
        )
        
        movements = query.all()
        return self.calculate_over_under_rates(movements)
    
    def perform_chi_square_test(
        self,
        observed_under: int,
        observed_total: int,
        expected_under_rate: float,
    ) -> Tuple[float, float]:
        """
        Perform chi-square test to determine statistical significance.
        
        Tests if the observed under rate differs significantly from expected.
        
        Args:
            observed_under: Number of unders in test group
            observed_total: Total sample size
            expected_under_rate: Expected under rate (baseline)
            
        Returns:
            Tuple of (chi_square_statistic, p_value)
        """
        if observed_total == 0 or expected_under_rate == 0:
            return 0.0, 1.0
        
        observed_over = observed_total - observed_under
        expected_under = observed_total * expected_under_rate
        expected_over = observed_total * (1 - expected_under_rate)
        
        # Chi-square test
        observed = np.array([observed_under, observed_over])
        expected = np.array([expected_under, expected_over])
        
        # Avoid division by zero
        if np.any(expected == 0):
            return 0.0, 1.0
        
        chi2, p_value = scipy_stats.chisquare(observed, expected)
        
        return float(chi2), float(p_value)
    
    def calculate_confidence_interval(
        self,
        successes: int,
        total: int,
        confidence: float = 0.95,
    ) -> Tuple[float, float]:
        """
        Calculate confidence interval for a proportion using Wilson score.
        
        Args:
            successes: Number of successes (e.g., unders)
            total: Total sample size
            confidence: Confidence level (default 95%)
            
        Returns:
            Tuple of (lower_bound, upper_bound)
        """
        if total == 0:
            return 0.0, 1.0
        
        p = successes / total
        z = scipy_stats.norm.ppf((1 + confidence) / 2)
        
        denominator = 1 + z**2 / total
        center = (p + z**2 / (2 * total)) / denominator
        spread = z * np.sqrt((p * (1 - p) + z**2 / (4 * total)) / total) / denominator
        
        lower = max(0, center - spread)
        upper = min(1, center + spread)
        
        return lower, upper
    
    def run_analysis(
        self,
        session: Session,
        name: str,
        prop_type: Optional[PropType] = None,
        movement_threshold_pct: Optional[float] = None,
        movement_threshold_abs: Optional[float] = None,
        hours_before_threshold: Optional[float] = None,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
    ) -> Optional[AnalysisResult]:
        """
        Run a complete correlation analysis.
        
        Args:
            session: Database session
            name: Name for this analysis
            prop_type: Filter by prop type
            movement_threshold_pct: Minimum percentage drop
            movement_threshold_abs: Minimum absolute drop
            hours_before_threshold: Maximum hours before kickoff
            start_date: Start of date range
            end_date: End of date range
            
        Returns:
            AnalysisResult object with all statistics
        """
        settings = get_settings()
        threshold_pct = movement_threshold_pct or settings.line_movement_threshold_pct
        threshold_abs = movement_threshold_abs or settings.line_movement_threshold_abs
        hours_threshold = hours_before_threshold or settings.hours_before_kickoff_threshold
        
        # Get test group (significant late drops)
        movements = self.get_movements_with_results(
            session=session,
            prop_type=prop_type,
            min_movement_pct=threshold_pct,
            min_movement_abs=threshold_abs,
            max_hours_before=hours_threshold,
            start_date=start_date,
            end_date=end_date,
        )
        
        test_rates = self.calculate_over_under_rates(movements)
        
        if test_rates["total"] == 0:
            print(f"No movements found for analysis '{name}'")
            return None
        
        # Get baseline group
        baseline_rates = self.calculate_baseline_rates(
            session=session,
            prop_type=prop_type,
            start_date=start_date,
            end_date=end_date,
        )
        
        # Statistical testing
        baseline_under_rate = float(baseline_rates["under_rate"] or 0.5)
        chi2, p_value = self.perform_chi_square_test(
            observed_under=test_rates["under_count"],
            observed_total=test_rates["total"],
            expected_under_rate=baseline_under_rate,
        )
        
        # Confidence interval for under rate
        ci_low, ci_high = self.calculate_confidence_interval(
            successes=test_rates["under_count"],
            total=test_rates["total"],
        )
        
        # Create result
        result = AnalysisResult(
            analysis_name=name,
            prop_type=prop_type,
            movement_threshold_pct=Decimal(str(threshold_pct)),
            movement_threshold_abs=Decimal(str(threshold_abs)),
            hours_before_threshold=Decimal(str(hours_threshold)),
            sample_size=test_rates["total"],
            date_range_start=start_date or datetime(2020, 1, 1, tzinfo=timezone.utc),
            date_range_end=end_date or datetime.now(timezone.utc),
            over_count=test_rates["over_count"],
            under_count=test_rates["under_count"],
            push_count=test_rates["push_count"],
            over_rate=test_rates["over_rate"],
            under_rate=test_rates["under_rate"],
            chi_square_statistic=Decimal(str(round(chi2, 4))),
            p_value=Decimal(str(round(p_value, 8))),
            is_significant=p_value < 0.05,
            confidence_interval_low=Decimal(str(round(ci_low, 4))),
            confidence_interval_high=Decimal(str(round(ci_high, 4))),
            baseline_over_rate=baseline_rates["over_rate"],
            baseline_sample_size=baseline_rates["total"],
        )
        
        return result
    
    def run_thesis_analysis(
        self,
        session: Session,
    ) -> List[AnalysisResult]:
        """
        Run the main thesis analysis with various threshold combinations.
        
        Tests: "Large drops in yardage prop lines close to kickoff correlate
        with players going under their prop line."
        
        Args:
            session: Database session
            
        Returns:
            List of AnalysisResult objects
        """
        results = []
        
        # Test various thresholds
        threshold_combinations = [
            (5.0, 3.0, 3.0),   # 5% or 3 yards, within 3 hours
            (10.0, 5.0, 3.0),  # 10% or 5 yards, within 3 hours
            (15.0, 7.0, 3.0),  # 15% or 7 yards, within 3 hours
            (10.0, 5.0, 1.0),  # 10% or 5 yards, within 1 hour
            (10.0, 5.0, 6.0),  # 10% or 5 yards, within 6 hours
        ]
        
        prop_types = [None, PropType.RUSHING_YARDS, PropType.RECEIVING_YARDS]
        
        for pct, abs_val, hours in threshold_combinations:
            for prop_type in prop_types:
                prop_name = prop_type.value if prop_type else "all"
                name = f"thesis_{prop_name}_pct{pct}_abs{abs_val}_hrs{hours}"
                
                result = self.run_analysis(
                    session=session,
                    name=name,
                    prop_type=prop_type,
                    movement_threshold_pct=pct,
                    movement_threshold_abs=abs_val,
                    hours_before_threshold=hours,
                )
                
                if result:
                    results.append(result)
        
        return results
    
    def save_results(
        self,
        session: Session,
        results: List[AnalysisResult],
    ) -> int:
        """
        Save analysis results to the database.
        
        Args:
            session: Database session
            results: List of AnalysisResult objects
            
        Returns:
            Number of results saved
        """
        if not results:
            return 0
        
        try:
            for result in results:
                # Check for existing result with same name
                existing = (
                    session.query(AnalysisResult)
                    .filter(AnalysisResult.analysis_name == result.analysis_name)
                    .first()
                )
                
                if existing:
                    # Update existing
                    for key in [
                        "sample_size", "over_count", "under_count", "push_count",
                        "over_rate", "under_rate", "chi_square_statistic", "p_value",
                        "is_significant", "confidence_interval_low", "confidence_interval_high",
                        "baseline_over_rate", "baseline_sample_size",
                    ]:
                        setattr(existing, key, getattr(result, key))
                else:
                    session.add(result)
            
            session.commit()
            return len(results)
        except Exception as e:
            session.rollback()
            raise e
    
    def get_summary_report(
        self,
        session: Session,
    ) -> str:
        """
        Generate a human-readable summary report of all analyses.
        
        Args:
            session: Database session
            
        Returns:
            Formatted string report
        """
        results = session.query(AnalysisResult).order_by(AnalysisResult.analysis_name).all()
        
        if not results:
            return "No analysis results found."
        
        lines = [
            "=" * 80,
            "PROP LINE MOVEMENT ANALYSIS - THESIS VALIDATION REPORT",
            "=" * 80,
            "",
            "THESIS: Large drops in yardage prop lines close to kickoff correlate",
            "        with players going UNDER their prop line.",
            "",
            "-" * 80,
        ]
        
        for result in results:
            lines.append(f"\nAnalysis: {result.analysis_name}")
            lines.append(f"  Prop Type: {result.prop_type.value if result.prop_type else 'All'}")
            lines.append(f"  Thresholds: {result.movement_threshold_pct}% or {result.movement_threshold_abs} yards")
            lines.append(f"  Time Window: Within {result.hours_before_threshold} hours of kickoff")
            lines.append(f"  Sample Size: {result.sample_size}")
            lines.append(f"  Under Rate: {float(result.under_rate) * 100:.1f}% ({result.under_count}/{result.sample_size})")
            lines.append(f"  Over Rate: {float(result.over_rate) * 100:.1f}% ({result.over_count}/{result.sample_size})")
            lines.append(f"  95% CI: [{float(result.confidence_interval_low) * 100:.1f}%, {float(result.confidence_interval_high) * 100:.1f}%]")
            lines.append(f"  P-Value: {float(result.p_value):.4f}")
            lines.append(f"  Statistically Significant: {'YES' if result.is_significant else 'NO'}")
            
            if result.baseline_sample_size:
                lines.append(f"  Baseline Under Rate: {float(result.baseline_over_rate or 0) * 100:.1f}% (n={result.baseline_sample_size})")
            
            lines.append("-" * 40)
        
        lines.append("\n" + "=" * 80)
        lines.append("CONCLUSION:")
        
        # Find the main analysis (10% threshold, 3 hours, all props)
        main_result = None
        for result in results:
            if "pct10" in result.analysis_name and "hrs3" in result.analysis_name and "all" in result.analysis_name:
                main_result = result
                break
        
        if main_result:
            under_rate = float(main_result.under_rate) * 100
            if main_result.is_significant and under_rate > 55:
                lines.append(f"The thesis is SUPPORTED. Players with significant line drops")
                lines.append(f"went under {under_rate:.1f}% of the time (p < 0.05).")
            elif under_rate > 50:
                lines.append(f"The thesis shows a TREND. Players with significant line drops")
                lines.append(f"went under {under_rate:.1f}% of the time, but more data is needed.")
            else:
                lines.append(f"The thesis is NOT SUPPORTED. Players with significant line drops")
                lines.append(f"went under only {under_rate:.1f}% of the time.")
        else:
            lines.append("Unable to generate conclusion - main analysis not found.")
        
        lines.append("=" * 80)
        
        return "\n".join(lines)


def run_full_analysis() -> str:
    """
    Run the complete thesis analysis and return a report.
    
    Returns:
        Summary report as string
    """
    session = get_session()
    try:
        analyzer = CorrelationAnalyzer()
        
        # Run thesis analysis
        results = analyzer.run_thesis_analysis(session)
        
        # Save results
        analyzer.save_results(session, results)
        
        # Generate report
        report = analyzer.get_summary_report(session)
        
        return report
    finally:
        session.close()


if __name__ == "__main__":
    report = run_full_analysis()
    print(report)

