from __future__ import annotations

from dataclasses import dataclass, asdict
from typing import Any, Dict, Optional


@dataclass(slots=True)
class Driver:
    id: Optional[int]
    full_name: str
    phone: str = ""
    email: str = ""
    license_number: str = ""
    license_expiry: str = ""
    notes: str = ""

    @classmethod
    def from_row(cls, row: Dict[str, Any]) -> "Driver":
        return cls(**row)

    def to_record(self) -> Dict[str, Any]:
        record = asdict(self)
        record.pop("id", None)
        return record


@dataclass(slots=True)
class Vehicle:
    id: Optional[int]
    registry_number: str
    vin: str
    make: str
    model: str
    year: int
    mileage: int
    status: str
    acquisition_date: str
    next_service_date: str
    fuel_type: str
    assigned_driver_id: Optional[int]
    notes: str = ""

    @classmethod
    def from_row(cls, row: Dict[str, Any]) -> "Vehicle":
        return cls(**row)

    def to_record(self) -> Dict[str, Any]:
        record = asdict(self)
        record.pop("id", None)
        return record


@dataclass(slots=True)
class Maintenance:
    id: Optional[int]
    vehicle_id: int
    service_date: str
    description: str
    mileage: int
    cost: float
    service_center: str
    notes: str = ""

    @classmethod
    def from_row(cls, row: Dict[str, Any]) -> "Maintenance":
        return cls(**row)

    def to_record(self) -> Dict[str, Any]:
        record = asdict(self)
        record.pop("id", None)
        return record

