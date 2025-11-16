"""SmartNumbers / KPI calculator for QBR metrics.

This module calculates 18 SmartNumbers (KPIs) from monthly raw metrics.
All formulas are based on CALCULATION_REFERENCE.md.
"""

from typing import Dict, Optional, List
from decimal import Decimal
from dataclasses import dataclass

from common.logging import get_logger


@dataclass
class MonthlyMetrics:
    """Container for monthly raw metrics."""
    # Operations metrics
    reactive_tickets_created: Optional[Decimal] = None
    reactive_tickets_closed: Optional[Decimal] = None
    total_time_reactive: Optional[Decimal] = None  # hours
    endpoints_managed: Optional[Decimal] = None

    # Revenue metrics
    nrr: Optional[Decimal] = None  # Non-recurring revenue
    mrr: Optional[Decimal] = None  # Monthly recurring revenue
    orr: Optional[Decimal] = None  # Other recurring revenue
    product_sales: Optional[Decimal] = None
    misc_revenue: Optional[Decimal] = None
    total_revenue: Optional[Decimal] = None

    # Expense metrics
    employee_expense: Optional[Decimal] = None
    owner_comp_taxes: Optional[Decimal] = None
    owner_comp: Optional[Decimal] = None
    product_cogs: Optional[Decimal] = None
    other_expenses: Optional[Decimal] = None
    total_expenses: Optional[Decimal] = None

    # Profit metrics
    net_profit: Optional[Decimal] = None

    # General info
    employees: Optional[Decimal] = None
    technical_employees: Optional[Decimal] = None
    seats_managed: Optional[Decimal] = None
    agreements: Optional[Decimal] = None

    # Sales metrics
    telemarketing_dials: Optional[Decimal] = None
    first_time_appointments: Optional[Decimal] = None
    prospects_to_pbr: Optional[Decimal] = None
    new_agreements: Optional[Decimal] = None
    new_mrr: Optional[Decimal] = None
    lost_mrr: Optional[Decimal] = None


@dataclass
class QuarterlyMetrics:
    """Container for quarterly aggregated metrics."""
    # Summed metrics
    reactive_tickets_created: Optional[Decimal] = None
    reactive_tickets_closed: Optional[Decimal] = None
    total_time_reactive: Optional[Decimal] = None
    nrr: Optional[Decimal] = None
    mrr: Optional[Decimal] = None
    orr: Optional[Decimal] = None
    product_sales: Optional[Decimal] = None
    misc_revenue: Optional[Decimal] = None
    total_revenue: Optional[Decimal] = None
    employee_expense: Optional[Decimal] = None
    owner_comp_taxes: Optional[Decimal] = None
    owner_comp: Optional[Decimal] = None
    product_cogs: Optional[Decimal] = None
    other_expenses: Optional[Decimal] = None
    total_expenses: Optional[Decimal] = None
    net_profit: Optional[Decimal] = None
    telemarketing_dials: Optional[Decimal] = None
    first_time_appointments: Optional[Decimal] = None
    prospects_to_pbr: Optional[Decimal] = None
    new_agreements: Optional[Decimal] = None
    new_mrr: Optional[Decimal] = None
    lost_mrr: Optional[Decimal] = None

    # Averaged metrics
    endpoints_managed: Optional[Decimal] = None
    employees: Optional[Decimal] = None
    technical_employees: Optional[Decimal] = None
    seats_managed: Optional[Decimal] = None
    agreements: Optional[Decimal] = None


class SmartNumbersCalculator:
    """
    Calculate SmartNumbers (KPIs) from monthly or quarterly metrics.

    All formulas are based on docs/qbr/shared/CALCULATION_REFERENCE.md.
    """

    # Working hours per tech per month (40 hours/week * 4.175 weeks/month)
    MONTHLY_WORKING_HOURS = 167

    def __init__(self):
        self.logger = get_logger(__name__)

    def calculate_quarterly(self, metrics: QuarterlyMetrics) -> Dict[str, Optional[Decimal]]:
        """
        Calculate all 18 SmartNumbers for a quarterly period.

        Args:
            metrics: Quarterly aggregated metrics

        Returns:
            Dict of smartnumber_name -> calculated_value (or None if cannot calculate)
        """
        return {
            # Operations SmartNumbers (1-6)
            'tickets_per_tech_per_month': self._tickets_per_tech(
                metrics.reactive_tickets_closed,
                metrics.technical_employees
            ),
            'total_close_pct': self._total_close_pct(
                metrics.reactive_tickets_closed,
                metrics.reactive_tickets_created
            ),
            'tickets_per_endpoint_per_month': self._tickets_per_endpoint(
                metrics.reactive_tickets_created,
                metrics.endpoints_managed
            ),
            'rhem': self._rhem(
                metrics.total_time_reactive,
                metrics.endpoints_managed
            ),
            'avg_resolution_time': self._avg_resolution_time(
                metrics.total_time_reactive,
                metrics.reactive_tickets_closed
            ),
            'reactive_service_pct': self._reactive_service_pct(
                metrics.total_time_reactive,
                metrics.technical_employees
            ),

            # Profit SmartNumbers (7)
            'net_profit_pct': self._net_profit_pct(
                metrics.net_profit,
                metrics.total_revenue
            ),

            # Revenue SmartNumbers (8-9)
            'revenue_from_services_pct': self._revenue_from_services_pct(
                metrics.nrr,
                metrics.mrr,
                metrics.total_revenue
            ),
            'services_from_mrr_pct': self._services_from_mrr_pct(
                metrics.mrr,
                metrics.nrr
            ),

            # Leverage SmartNumbers (10-13)
            'annual_service_rev_per_employee': self._annual_service_rev_per_employee(
                metrics.nrr,
                metrics.mrr,
                metrics.employees
            ),
            'annual_service_rev_per_tech': self._annual_service_rev_per_tech(
                metrics.nrr,
                metrics.mrr,
                metrics.technical_employees
            ),
            'avg_aisp': self._avg_aisp(
                metrics.mrr,
                metrics.seats_managed
            ),
            'avg_mrr_per_agreement': self._avg_mrr_per_agreement(
                metrics.mrr,
                metrics.agreements
            ),

            # Sales SmartNumbers (14-18)
            'new_mrr_added': metrics.new_mrr,  # Direct sum
            'lost_mrr': metrics.lost_mrr,  # Direct sum
            'net_mrr_gain': self._net_mrr_gain(
                metrics.new_mrr,
                metrics.lost_mrr
            ),
            'dials_per_appointment': self._dials_per_appointment(
                metrics.telemarketing_dials,
                metrics.first_time_appointments
            ),
            'sales_call_close_pct': self._sales_call_close_pct(
                metrics.new_agreements,
                metrics.first_time_appointments
            ),
        }

    # ============================================================================
    # Operations SmartNumbers (1-6)
    # ============================================================================

    def _tickets_per_tech(
        self,
        tickets_closed: Optional[Decimal],
        tech_count: Optional[Decimal]
    ) -> Optional[Decimal]:
        """
        1. Reactive Tickets / Tech / Month (closed)

        Formula: tickets_closed / tech_count / 3 months

        Example: 1,080 tickets / 5.5 techs / 3 = 65.45 tickets/tech/month
        """
        if tickets_closed is None or tech_count is None or tech_count == 0:
            return None

        result = tickets_closed / tech_count / Decimal('3')
        return result.quantize(Decimal('0.01'))

    def _total_close_pct(
        self,
        tickets_closed: Optional[Decimal],
        tickets_created: Optional[Decimal]
    ) -> Optional[Decimal]:
        """
        2. Total Close %

        Formula: tickets_closed / tickets_created

        Example: 1,080 / 1,081 = 0.9991 = 99.91%

        Note: >100% is possible if closing tickets from previous period
        """
        if tickets_closed is None or tickets_created is None or tickets_created == 0:
            return None

        result = tickets_closed / tickets_created
        return result.quantize(Decimal('0.0001'))

    def _tickets_per_endpoint(
        self,
        tickets_created: Optional[Decimal],
        endpoints: Optional[Decimal]
    ) -> Optional[Decimal]:
        """
        3. Reactive Tickets / Endpoint / Month (new)

        Formula: tickets_created / 3 months / avg_endpoints

        Example: 1,081 / 3 / 597 = 0.603 tickets/endpoint/month
        """
        if tickets_created is None or endpoints is None or endpoints == 0:
            return None

        result = tickets_created / Decimal('3') / endpoints
        return result.quantize(Decimal('0.0001'))

    def _rhem(
        self,
        hours: Optional[Decimal],
        endpoints: Optional[Decimal]
    ) -> Optional[Decimal]:
        """
        4. RHEM (Reactive Hours / Endpoint / Month)

        Formula: hours / avg_endpoints / 3 months

        Example: 452.08 / 597 / 3 = 0.252 hours/endpoint/month
        """
        if hours is None or endpoints is None or endpoints == 0:
            return None

        result = hours / endpoints / Decimal('3')
        return result.quantize(Decimal('0.0001'))

    def _avg_resolution_time(
        self,
        hours: Optional[Decimal],
        tickets_closed: Optional[Decimal]
    ) -> Optional[Decimal]:
        """
        5. Average Resolution Time

        Formula: total_hours / tickets_closed

        Example: 452.08 / 1,080 = 0.419 hours = 25.1 minutes

        Returns: Hours (decimal)
        """
        if hours is None or tickets_closed is None or tickets_closed == 0:
            return None

        result = hours / tickets_closed
        return result.quantize(Decimal('0.0001'))

    def _reactive_service_pct(
        self,
        hours: Optional[Decimal],
        tech_count: Optional[Decimal]
    ) -> Optional[Decimal]:
        """
        6. Reactive Service %

        Formula: (hours / 3) / (tech_count * 167 working_hours_per_month)

        Example: (452.08 / 3) / (5.5 * 167) = 0.164 = 16.4%

        Note: 167 = 40 hours/week * 4.175 weeks/month
        """
        if hours is None or tech_count is None or tech_count == 0:
            return None

        monthly_avg_hours = hours / Decimal('3')
        available_hours = tech_count * Decimal(str(self.MONTHLY_WORKING_HOURS))

        result = monthly_avg_hours / available_hours
        return result.quantize(Decimal('0.0001'))

    # ============================================================================
    # Profit SmartNumbers (7)
    # ============================================================================

    def _net_profit_pct(
        self,
        net_profit: Optional[Decimal],
        total_revenue: Optional[Decimal]
    ) -> Optional[Decimal]:
        """
        7. Net Profit %

        Formula: net_profit / total_revenue

        Example: $54,001 / $515,488 = 0.1048 = 10.48%
        """
        if net_profit is None or total_revenue is None or total_revenue == 0:
            return None

        result = net_profit / total_revenue
        return result.quantize(Decimal('0.0001'))

    # ============================================================================
    # Revenue SmartNumbers (8-9)
    # ============================================================================

    def _revenue_from_services_pct(
        self,
        nrr: Optional[Decimal],
        mrr: Optional[Decimal],
        total_revenue: Optional[Decimal]
    ) -> Optional[Decimal]:
        """
        8. % of Revenue from Services

        Formula: (nrr + mrr) / total_revenue

        Example: ($32,280 + $329,960) / $515,488 = 0.703 = 70.3%
        """
        if total_revenue is None or total_revenue == 0:
            return None

        service_revenue = (nrr or Decimal('0')) + (mrr or Decimal('0'))

        result = service_revenue / total_revenue
        return result.quantize(Decimal('0.0001'))

    def _services_from_mrr_pct(
        self,
        mrr: Optional[Decimal],
        nrr: Optional[Decimal]
    ) -> Optional[Decimal]:
        """
        9. % of Services from MRR

        Formula: mrr / (nrr + mrr)

        Example: $329,960 / ($32,280 + $329,960) = 0.911 = 91.1%
        """
        if mrr is None:
            return None

        service_revenue = (nrr or Decimal('0')) + mrr

        if service_revenue == 0:
            return None

        result = mrr / service_revenue
        return result.quantize(Decimal('0.0001'))

    # ============================================================================
    # Leverage SmartNumbers (10-13)
    # ============================================================================

    def _annual_service_rev_per_employee(
        self,
        nrr: Optional[Decimal],
        mrr: Optional[Decimal],
        employees: Optional[Decimal]
    ) -> Optional[Decimal]:
        """
        10. Annualized Service Revenue / Employee

        Formula: (service_revenue_quarter / avg_employees) * 4

        Example: ($362,240 / 8.5) * 4 = $170,582 annualized
        """
        if employees is None or employees == 0:
            return None

        service_revenue = (nrr or Decimal('0')) + (mrr or Decimal('0'))

        result = (service_revenue / employees) * Decimal('4')
        return result.quantize(Decimal('0.01'))

    def _annual_service_rev_per_tech(
        self,
        nrr: Optional[Decimal],
        mrr: Optional[Decimal],
        tech_employees: Optional[Decimal]
    ) -> Optional[Decimal]:
        """
        11. Annualized Service Revenue / Technical Employee

        Formula: (service_revenue_quarter / avg_tech_employees) * 4

        Example: ($362,240 / 5.5) * 4 = $263,265 annualized
        """
        if tech_employees is None or tech_employees == 0:
            return None

        service_revenue = (nrr or Decimal('0')) + (mrr or Decimal('0'))

        result = (service_revenue / tech_employees) * Decimal('4')
        return result.quantize(Decimal('0.01'))

    def _avg_aisp(
        self,
        mrr: Optional[Decimal],
        seats: Optional[Decimal]
    ) -> Optional[Decimal]:
        """
        12. Average AISP (Average Income per Seat/Position)

        Formula: mrr_quarter / avg_seats / 3 months

        Example: $329,960 / 546 / 3 = $201.43 per seat per month
        """
        if mrr is None or seats is None or seats == 0:
            return None

        result = mrr / seats / Decimal('3')
        return result.quantize(Decimal('0.01'))

    def _avg_mrr_per_agreement(
        self,
        mrr: Optional[Decimal],
        agreements: Optional[Decimal]
    ) -> Optional[Decimal]:
        """
        13. Average MRR per Agreement

        Formula: mrr_quarter / avg_agreements / 3 months

        Example: $329,960 / 37 / 3 = $2,972 per agreement per month
        """
        if mrr is None or agreements is None or agreements == 0:
            return None

        result = mrr / agreements / Decimal('3')
        return result.quantize(Decimal('0.01'))

    # ============================================================================
    # Sales SmartNumbers (14-18)
    # ============================================================================

    def _net_mrr_gain(
        self,
        new_mrr: Optional[Decimal],
        lost_mrr: Optional[Decimal]
    ) -> Optional[Decimal]:
        """
        16. Net MRR gain

        Formula: new_mrr - lost_mrr

        Example: $2,902 - $2,536 = $366
        """
        if new_mrr is None and lost_mrr is None:
            return None

        result = (new_mrr or Decimal('0')) - (lost_mrr or Decimal('0'))
        return result.quantize(Decimal('0.01'))

    def _dials_per_appointment(
        self,
        dials: Optional[Decimal],
        ftas: Optional[Decimal]
    ) -> Optional[Decimal]:
        """
        17. # of dials / appointment

        Formula: total_dials / total_ftas

        Example: 150 dials / 10 FTAs = 15 dials/appointment

        Returns None if FTAs = 0 (avoid division by zero)
        """
        if dials is None or ftas is None or ftas == 0:
            return None

        result = dials / ftas
        return result.quantize(Decimal('0.01'))

    def _sales_call_close_pct(
        self,
        new_agreements: Optional[Decimal],
        ftas: Optional[Decimal]
    ) -> Optional[Decimal]:
        """
        18. Sales Call Close %

        Formula: new_agreements / ftas

        Example: 1 / 2 = 0.50 = 50%

        Returns None if FTAs = 0 (avoid division by zero)
        """
        if new_agreements is None or ftas is None or ftas == 0:
            return None

        result = new_agreements / ftas
        return result.quantize(Decimal('0.0001'))


def aggregate_monthly_to_quarterly(monthly_data: List[MonthlyMetrics]) -> QuarterlyMetrics:
    """
    Aggregate 3 monthly metrics into quarterly metrics.

    Aggregation rules:
    - Counts, hours, revenue, expenses: SUM of 3 months
    - Employees, agreements, endpoints, seats: AVERAGE of 3 months

    Args:
        monthly_data: List of 3 MonthlyMetrics objects (in order)

    Returns:
        QuarterlyMetrics object
    """
    if len(monthly_data) != 3:
        raise ValueError(f"Expected 3 monthly metrics, got {len(monthly_data)}")

    def sum_metrics(*values):
        """Sum non-None values, return None if all None"""
        non_null = [v for v in values if v is not None]
        return sum(non_null, Decimal('0')) if non_null else None

    def avg_metrics(*values):
        """Average non-None values, return None if all None"""
        non_null = [v for v in values if v is not None]
        if not non_null:
            return None
        return sum(non_null, Decimal('0')) / Decimal(str(len(non_null)))

    m1, m2, m3 = monthly_data

    return QuarterlyMetrics(
        # Summed metrics (tickets, hours, revenue, expenses)
        reactive_tickets_created=sum_metrics(m1.reactive_tickets_created, m2.reactive_tickets_created, m3.reactive_tickets_created),
        reactive_tickets_closed=sum_metrics(m1.reactive_tickets_closed, m2.reactive_tickets_closed, m3.reactive_tickets_closed),
        total_time_reactive=sum_metrics(m1.total_time_reactive, m2.total_time_reactive, m3.total_time_reactive),
        nrr=sum_metrics(m1.nrr, m2.nrr, m3.nrr),
        mrr=sum_metrics(m1.mrr, m2.mrr, m3.mrr),
        orr=sum_metrics(m1.orr, m2.orr, m3.orr),
        product_sales=sum_metrics(m1.product_sales, m2.product_sales, m3.product_sales),
        misc_revenue=sum_metrics(m1.misc_revenue, m2.misc_revenue, m3.misc_revenue),
        total_revenue=sum_metrics(m1.total_revenue, m2.total_revenue, m3.total_revenue),
        employee_expense=sum_metrics(m1.employee_expense, m2.employee_expense, m3.employee_expense),
        owner_comp_taxes=sum_metrics(m1.owner_comp_taxes, m2.owner_comp_taxes, m3.owner_comp_taxes),
        owner_comp=sum_metrics(m1.owner_comp, m2.owner_comp, m3.owner_comp),
        product_cogs=sum_metrics(m1.product_cogs, m2.product_cogs, m3.product_cogs),
        other_expenses=sum_metrics(m1.other_expenses, m2.other_expenses, m3.other_expenses),
        total_expenses=sum_metrics(m1.total_expenses, m2.total_expenses, m3.total_expenses),
        net_profit=sum_metrics(m1.net_profit, m2.net_profit, m3.net_profit),
        telemarketing_dials=sum_metrics(m1.telemarketing_dials, m2.telemarketing_dials, m3.telemarketing_dials),
        first_time_appointments=sum_metrics(m1.first_time_appointments, m2.first_time_appointments, m3.first_time_appointments),
        prospects_to_pbr=sum_metrics(m1.prospects_to_pbr, m2.prospects_to_pbr, m3.prospects_to_pbr),
        new_agreements=sum_metrics(m1.new_agreements, m2.new_agreements, m3.new_agreements),
        new_mrr=sum_metrics(m1.new_mrr, m2.new_mrr, m3.new_mrr),
        lost_mrr=sum_metrics(m1.lost_mrr, m2.lost_mrr, m3.lost_mrr),

        # Averaged metrics (employees, agreements, endpoints, seats)
        endpoints_managed=avg_metrics(m1.endpoints_managed, m2.endpoints_managed, m3.endpoints_managed),
        employees=avg_metrics(m1.employees, m2.employees, m3.employees),
        technical_employees=avg_metrics(m1.technical_employees, m2.technical_employees, m3.technical_employees),
        seats_managed=avg_metrics(m1.seats_managed, m2.seats_managed, m3.seats_managed),
        agreements=avg_metrics(m1.agreements, m2.agreements, m3.agreements),
    )
