from datetime import datetime
from pydantic import BaseModel, EmailStr, Field, ConfigDict, field_validator


class UserCreate(BaseModel):
    full_name: str = Field(min_length=3, max_length=120)
    email: EmailStr
    password: str = Field(min_length=6, max_length=72)


class UserLogin(BaseModel):
    email: EmailStr
    password: str = Field(min_length=6, max_length=72)


class UserOut(BaseModel):
    id: str
    full_name: str
    email: EmailStr
    role: str
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"


class DrawCreate(BaseModel):
    title: str = Field(min_length=3, max_length=150)
    ticket_price: float = Field(default=1.0, gt=0)
    sales_threshold_amount: float = Field(default=100.0, gt=0)


class DrawOut(BaseModel):
    id: str
    title: str
    ticket_price: float
    sales_threshold_amount: float
    tickets_sold: int
    sales_amount: float
    jackpot_pool: float
    tier10_pool: float
    free_ticket_pool: float
    status: str
    winning_numbers: list[int] | None = None
    created_at: datetime
    closed_at: datetime | None = None
    executed_at: datetime | None = None

    model_config = ConfigDict(from_attributes=True)


class TicketNumbers(BaseModel):
    numbers: list[int] = Field(min_length=11, max_length=11)

    @field_validator("numbers")
    @classmethod
    def validate_numbers(cls, value: list[int]) -> list[int]:
        if len(set(value)) != 11:
            raise ValueError("Los numeros no deben repetirse")
        if any(n < 1 or n > 26 for n in value):
            raise ValueError("Los numeros deben estar entre 1 y 26")
        return sorted(value)


class TicketCreate(BaseModel):
    draw_id: str
    numbers: list[int] | None = None
    auto_pick: bool = True

    @field_validator("numbers")
    @classmethod
    def validate_optional_numbers(cls, value):
        if value is None:
            return value
        if len(value) != 11:
            raise ValueError("Debes enviar exactamente 11 numeros")
        if len(set(value)) != 11:
            raise ValueError("Los numeros no deben repetirse")
        if any(n < 1 or n > 26 for n in value):
            raise ValueError("Los numeros deben estar entre 1 y 26")
        return sorted(value)


class TicketOut(BaseModel):
    id: str
    draw_id: str
    user_id: str
    payment_id: str | None = None
    numbers: list[int]
    hits: int
    prize_type: str | None = None
    prize_amount: float
    is_free_ticket: bool
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class PaymentCreate(BaseModel):
    draw_id: str
    quantity: int = Field(gt=0, le=50)
    auto_pick: bool = True
    selected_numbers: list[list[int]] | None = None

    @field_validator("selected_numbers")
    @classmethod
    def validate_selected_numbers(cls, value):
        if value is None:
            return value
        for combination in value:
            if len(combination) != 11:
                raise ValueError("Cada boleto debe tener exactamente 11 numeros")
            if len(set(combination)) != 11:
                raise ValueError("Los numeros del boleto no deben repetirse")
            if any(n < 1 or n > 26 for n in combination):
                raise ValueError("Los numeros deben estar entre 1 y 26")
        return [sorted(combination) for combination in value]


class PaymentOut(BaseModel):
    id: str
    user_id: str
    draw_id: str | None = None
    quantity: int
    amount: float
    status: str
    provider: str | None = None
    reference_note: str | None = None
    created_at: datetime
    confirmed_at: datetime | None = None

    model_config = ConfigDict(from_attributes=True)


class DrawRunOut(BaseModel):
    draw_id: str
    winning_numbers: list[int]
    extraction_order: list[int]
    total_tickets: int
    jackpot_winners: int
    tier10_winners: int
    tier9_winners: int
    executed_at: datetime


class PrizeSummaryOut(BaseModel):
    draw_id: str
    jackpot_pool: float
    tier10_pool: float
    free_ticket_pool: float
    jackpot_winners: int
    tier10_winners: int
    tier9_winners: int
    jackpot_prize_per_winner: float
    tier10_prize_per_winner: float


class BankAccountCreate(BaseModel):
    full_name: str
    id_number: str
    bank_name: str
    account_number: str
    account_type: str
    phone: str | None = None
    deuna_phone: str | None = None


class BankAccountOut(BaseModel):
    id: str
    user_id: str
    full_name: str
    id_number: str
    bank_name: str
    account_number: str
    account_type: str
    phone: str | None
    deuna_phone: str | None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)
    # =========================
# ADMIN SCHEMAS
# =========================

class AdminDashboardSummaryOut(BaseModel):
    total_users: int
    total_admins: int
    total_bank_accounts: int
    total_draws: int
    selling_draws: int
    closed_draws: int
    drawn_draws: int
    total_payments: int
    pending_payments: int
    confirmed_payments: int
    total_tickets: int
    total_winning_tickets: int
    total_free_ticket_credits: int
    available_free_ticket_credits: int
    used_free_ticket_credits: int
    total_paid_prizes: float


class AdminUserListItemOut(BaseModel):
    id: str
    full_name: str
    email: EmailStr
    role: str
    created_at: datetime
    has_bank_account: bool
    bank_name: str | None = None
    payments_count: int
    tickets_count: int
    winning_tickets_count: int
    free_tickets_count: int

    model_config = ConfigDict(from_attributes=True)


class AdminTicketDetailOut(BaseModel):
    id: str
    payment_id: str | None = None
    user_id: str
    draw_id: str
    draw_title: str | None = None
    numbers: list[int]
    hits: int
    prize_type: str | None = None
    prize_amount: float
    is_free_ticket: bool
    source_credit_id: str | None = None
    created_at: datetime


class AdminPaymentDetailOut(BaseModel):
    id: str
    user_id: str
    user_name: str | None = None
    user_email: EmailStr | None = None
    draw_id: str | None = None
    draw_title: str | None = None
    quantity: int
    amount: float
    status: str
    provider: str | None = None
    reference_note: str | None = None
    created_at: datetime
    confirmed_at: datetime | None = None
    generated_tickets_count: int = 0


class AdminFreeTicketCreditOut(BaseModel):
    id: str
    user_id: str
    draw_id: str
    draw_title: str | None = None
    source_ticket_id: str | None = None
    status: str
    created_at: datetime
    used_at: datetime | None = None


class AdminWinnerOut(BaseModel):
    ticket_id: str
    user_id: str
    user_name: str | None = None
    user_email: EmailStr | None = None
    draw_id: str
    draw_title: str | None = None
    numbers: list[int]
    hits: int
    prize_type: str | None = None
    prize_amount: float
    is_free_ticket: bool
    created_at: datetime


class AdminUserDetailOut(BaseModel):
    id: str
    full_name: str
    email: EmailStr
    role: str
    created_at: datetime
    bank_account: BankAccountOut | None = None
    payments: list[AdminPaymentDetailOut]
    tickets: list[AdminTicketDetailOut]
    winning_tickets: list[AdminWinnerOut]
    free_ticket_credits: list[AdminFreeTicketCreditOut]