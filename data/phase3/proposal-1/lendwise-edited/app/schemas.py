from pydantic import BaseModel, Field

class ApplicationIn(BaseModel):
    full_name: str = Field(min_length=2, max_length=120)
    phone: str = Field(min_length=10, max_length=20)
    email: str = ""
    pan_last4: str = Field(min_length=4, max_length=4)
    date_of_birth: str = ""
    full_address: str = ""
    employer_name: str = ""
    bank_account_number: str = ""
    requested_amount: float = Field(gt=0, le=2_000_000)
    purpose: str = Field(min_length=2, max_length=80)
    consent: bool

class LegacyImportIn(BaseModel):
    full_name: str
    phone: str
    pan_last4: str
    requested_amount: float
    purpose: str
    # Planted scenario: this legacy intake schema has no consent field.

class RepaymentIn(BaseModel):
    amount: float = Field(gt=0)
    reference: str = Field(min_length=4, max_length=80)
