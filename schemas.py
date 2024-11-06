from dataclasses import dataclass
from typing import List, Optional, Union
from enum import Enum
from datetime import datetime


class EmploymentType(Enum):
    FULL_TIME = "full_time"
    PART_TIME = "part_time"
    REMOTE = "remote"

    @classmethod
    def get_work_ua_id(cls, emp_type) -> Optional[str]:
        mapping = {
            cls.FULL_TIME: "74",
            cls.PART_TIME: "75",
            cls.REMOTE: "76",
        }
        return mapping.get(emp_type)

    @classmethod
    def get_robota_ua_id(cls, emp_type) -> Optional[str]:
        mapping = {
            cls.FULL_TIME: "1",
            cls.PART_TIME: "2",
            cls.REMOTE: "3",
        }
        return mapping.get(emp_type)


class ExperienceLevel(Enum):
    NO_EXPERIENCE = "no_experience"  # без досвіду
    LESS_THAN_1 = "less_than_1"  # до 1 року
    ONE_TO_TWO = "one_to_two"  # від 1 до 2 років
    TWO_TO_FIVE = "two_to_five"  # від 2 до 5 років
    FIVE_TO_TEN = "five_to_ten"  # від 5 до 10 років
    MORE_THAN_TEN = "more_than_ten"  # більше 10 років

    @classmethod
    def from_years(cls, years: float) -> 'ExperienceLevel':
        """Convert years of experience to ExperienceLevel"""
        if years == 0:
            return cls.NO_EXPERIENCE
        elif years < 1:
            return cls.LESS_THAN_1
        elif years < 2:
            return cls.ONE_TO_TWO
        elif years < 5:
            return cls.TWO_TO_FIVE
        elif years < 10:
            return cls.FIVE_TO_TEN
        else:
            return cls.MORE_THAN_TEN

    def to_work_ua_id(self) -> str:
        """Get work.ua specific ID for this experience level"""
        mapping = {
            self.NO_EXPERIENCE: "0",
            self.LESS_THAN_1: "1",
            self.ONE_TO_TWO: "164",
            self.TWO_TO_FIVE: "165",
            self.FIVE_TO_TEN: "166",
            self.MORE_THAN_TEN: "166"  # work.ua combines 5+ years
        }
        return mapping[self]

    def to_robota_ua_id(self) -> str:
        """Get robota.ua specific ID for this experience level"""
        mapping = {
            self.NO_EXPERIENCE: "0",
            self.LESS_THAN_1: "1",
            self.ONE_TO_TWO: "2",
            self.TWO_TO_FIVE: "3",
            self.FIVE_TO_TEN: "4",
            self.MORE_THAN_TEN: "5"
        }
        return mapping[self]


@dataclass
class SearchCriteria:
    position: str | None = None
    location: Optional[str] = None
    experience_level: Optional[Union[ExperienceLevel, List[ExperienceLevel]]] = None
    min_salary: Optional[int] = None
    max_salary: Optional[int] = None
    keywords: Optional[List[str]] = None
    employment_type: Optional[EmploymentType] = None

    def clear_all_state(self):
        self.position = None
        self.location = None
        self.experience_level = None
        self.min_salary = None
        self.max_salary = None
        self.keywords = None
        self.employment_type = None


@dataclass
class WorkExperience:
    position: str
    company: str
    duration_months: int
    start_date: str  # "MM.YYYY"
    end_date: Optional[str]  # "MM.YYYY" or None for current job
    is_current: bool  # Flag for current job
    description: Optional[str]
    industry: Optional[str]


@dataclass
class ResumeData:
    id: str
    name: str
    position: str
    salary_expectation: Optional[int]
    location: str
    skills: List[str]
    employment_type: Optional[EmploymentType]
    source_url: str
    experience: List[WorkExperience]  # List of work experiences
    total_experience_years: float  # Sum of all experiences in years
    suitable: Optional[float | int] = None

    @property
    def latest_position(self) -> Optional[WorkExperience]:
        """Get the most recent work experience"""
        if not self.experience:
            return None
        return sorted(
            self.experience,
            key=lambda x: datetime.strptime(x.end_date, "%m.%Y"),
            reverse=True
        )[0]
