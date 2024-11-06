from datetime import datetime
from typing import List, Tuple, Optional
from bs4 import Tag
from schemas import WorkExperience
import re


def calculate_months_between_dates(start_date: datetime, end_date: datetime) -> int:
    """Calculate months between two dates accurately"""
    return (end_date.year - start_date.year) * 12 + (end_date.month - start_date.month)


def parse_date(date_str: str) -> Optional[datetime]:
    """Parse date string into datetime object"""
    try:
        month, year = map(int, date_str.split('.'))
        return datetime(year, month, 1)
    except (ValueError, AttributeError):
        return None


async def parse_experience_block_work_ua(exp_container: Tag) -> Tuple[List[WorkExperience], int]:
    experiences = []
    total_months = 0
    current_date = datetime.now().replace(day=1)

    if not exp_container:
        return [], 0

    try:
        experience_items = exp_container.find_all('h2', class_='h4 strong-600 mt-lg sm:mt-xl')

        for item in experience_items:
            try:
                position_title = item.get_text(strip=True)
                details_elem = item.find_next_sibling('p', class_='mb-0')
                if not details_elem:
                    continue

                period_text = details_elem.contents[0].strip()

                # Extract dates using more precise patterns
                start_date = end_date = None
                is_current = False

                if "по нині" in period_text:
                    date_match = re.search(r'з (\d{2}\.\d{4}) по нині', period_text)
                    if date_match:
                        start_date = parse_date(date_match.group(1))
                        end_date = current_date
                        is_current = True
                else:
                    date_match = re.search(r'з (\d{2}\.\d{4}) по (\d{2}\.\d{4})', period_text)
                    if date_match:
                        start_date = parse_date(date_match.group(1))
                        end_date = parse_date(date_match.group(2))

                if not (start_date and end_date):
                    continue

                duration_months = calculate_months_between_dates(start_date, end_date)

                company_info = extract_company_info(details_elem)
                if not company_info:
                    continue

                company, city, industry = company_info

                # Extract description
                description = extract_description(details_elem)

                experience = WorkExperience(
                    position=position_title,
                    company=company,
                    duration_months=max(duration_months, 0),
                    start_date=start_date.strftime('%m.%Y'),
                    end_date=None if is_current else end_date.strftime('%m.%Y'),
                    is_current=is_current,
                    description=description,
                    industry=industry
                )

                experiences.append(experience)
                total_months += duration_months

            except Exception as e:
                print(f"Error parsing individual experience: {str(e)}")
                continue

    except Exception as e:
        print(f"Error parsing experience block: {str(e)}")

    return experiences, total_months


def extract_company_info(details_elem: Tag) -> Optional[tuple]:
    """Extract company information from details element"""
    br_elem = details_elem.find('br')
    if not (br_elem and br_elem.next_sibling):
        return None

    company_text = br_elem.next_sibling.strip()
    company_match = re.search(r'^(.*?)(?:, (.*?))?(?: \((.*?)\))?$', company_text)

    if company_match:
        return (
            company_match.group(1).strip(),
            company_match.group(2).strip() if company_match.group(2) else None,
            company_match.group(3).strip() if company_match.group(3) else None
        )
    return (company_text, None, None)


def extract_description(details_elem: Tag) -> Optional[str]:
    """Extract description from details element"""
    description_elem = details_elem.find_next_sibling('p', class_='text-default-7')
    return description_elem.get_text(strip=True) if description_elem else None
