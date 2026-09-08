from typing import Dict, Optional

from pydantic import BaseModel, Field


class SweepRequest(BaseModel):
    dca_total_usdc: float = Field(default=200, gt=0, le=10000)
    dca_split: Dict[str, float] = Field(default={"BTC": 0.5, "ETH": 0.3, "SOL": 0.2})
    sweep_idle_over_usdc: float = Field(default=100, ge=0, le=1000000)
    dust_under_usdc: float = Field(default=5, ge=0, le=1000)
    dry_run: bool = True
    confirmed: bool = False
    operation_id: Optional[str] = Field(default=None, min_length=8, max_length=80)


class PayRequest(BaseModel):
    to: str = Field(min_length=1, max_length=64)
    amount: float = Field(gt=0, le=100000)
    asset: str = Field(default="USDC", min_length=1, max_length=10)
    memo: str = Field(default="", max_length=140)
    dry_run: bool = True
    confirmed: bool = False
    obligation_id: Optional[int] = Field(default=None, gt=0)
    operation_id: Optional[str] = Field(default=None, min_length=8, max_length=80)


class ChatRequest(BaseModel):
    message: str = Field(min_length=1, max_length=500)
    dry_run: bool = True


class ConfigUpdate(BaseModel):
    max_per_pay_usdc: Optional[float] = Field(default=None, gt=0, le=500)
    max_daily_usdc: Optional[float] = Field(default=None, gt=0, le=100000)
    require_confirm_over_usdc: Optional[float] = Field(default=None, gt=0, le=500)
    dca_total_usdc: Optional[float] = Field(default=None, gt=0, le=10000)
    dca_split: Optional[Dict[str, float]] = None
    sweep_idle_over_usdc: Optional[float] = Field(default=None, ge=0, le=1000000)
    dust_under_usdc: Optional[float] = Field(default=None, ge=0, le=1000)
    minimum_reserve_usdc: Optional[float] = Field(default=None, ge=0, le=1000000)


class EarnRequest(BaseModel):
    asset: str = Field(default="USDC", min_length=1, max_length=10)
    amount: float = Field(gt=0, le=1000000)
    dry_run: bool = True
    confirmed: bool = False


class X402PayRequest(BaseModel):
    to: str = Field(min_length=1, max_length=64)
    amount: float = Field(gt=0, le=100000)
    asset: str = Field(default="USDC", min_length=1, max_length=10)
    memo: str = Field(default="", max_length=140)


class AddressbookEntry(BaseModel):
    id: str = Field(min_length=1, max_length=64)
    label: str = Field(min_length=1, max_length=80)
    asset: str = Field(default="USDC", min_length=1, max_length=10)
    email_or_uid: str = Field(min_length=3, max_length=120)


class AffordabilityRequest(BaseModel):
    amount: float = Field(gt=0, le=100000000)
    payment_fee: float = Field(default=0, ge=0, le=1000000)
    minimum_reserve: Optional[float] = Field(default=None, ge=0, le=1000000)
    obligation_id: Optional[int] = Field(default=None, gt=0)
    recipient: Optional[str] = Field(default=None, max_length=64)
    allowed_assets: Optional[list[str]] = None


class ObligationCreate(BaseModel):
    amount: float = Field(gt=0, le=100000000)
    asset: str = Field(default="USDC", min_length=1, max_length=16)
    due_date: Optional[str] = Field(default=None, max_length=32)
    recipient: Optional[str] = Field(default=None, max_length=64)
    memo: str = Field(default="", max_length=140)


class ObligationStatusUpdate(BaseModel):
    status: str = Field(min_length=1, max_length=24)


class AssetPolicyUpdate(BaseModel):
    protected: bool = False
    minimum_keep: float = Field(default=0, ge=0)


class FundingPlanRequest(AffordabilityRequest):
    max_conversion_fee_pct: float = Field(default=2.5, ge=0, le=100)
    max_slippage_pct: float = Field(default=1, ge=0, le=25)
    validity_seconds: int = Field(default=600, ge=30, le=3600)


class PlanApprovalRequest(BaseModel):
    version: int = Field(gt=0)
    confirmed: bool


class PlanExecutionRequest(BaseModel):
    version: int = Field(gt=0)
    operation_id: Optional[str] = Field(default=None, min_length=8, max_length=80)


class ReconciliationRequest(BaseModel):
    evidence: str = Field(min_length=8, max_length=500)
    confirmed: bool = False
