from abc import ABC, abstractmethod
from typing import List, Optional
from bs4 import BeautifulSoup

from parseres import parse_experience_block_work_ua
from schemas import SearchCriteria, ResumeData, EmploymentType
from urllib.parse import urlencode, quote
import aiohttp
import re
import json
import asyncio


class JobSiteParser(ABC):
    def __init__(self):
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }

    @abstractmethod
    def build_search_url(self, criteria: SearchCriteria) -> str:
        """Build the search URL based on the given criteria"""
        pass

    @abstractmethod
    def parse_resume_list(self, html_content: str) -> List[str]:
        """Parse the list page and return resume IDs"""
        pass

    #
    @abstractmethod
    def parse_resume_details(self, resume_id: str) -> ResumeData:
        """Parse individual resume page and return structured data"""
        pass

    @abstractmethod
    def get_resumes(self, criteria: SearchCriteria, max_pages: int = 1) -> List[ResumeData]:
        pass


class RetrieveResumesWorkua(JobSiteParser):
    BASE_URL = 'https://www.work.ua'

    def __init__(self, page: int = 1):
        super().__init__()
        self.page = page
        self.list_of_resumes = []

    def build_search_url(self, criteria: SearchCriteria) -> str:
        """
          Builds URL with multiple experience levels support
          Example: .../resumes-kyiv-it-python/?experience=0+1+164+165+166&period=5
          """
        # Build base URL
        location_part = f"-{criteria.location.lower()}" if criteria.location and criteria.location != 'Not set' else ""
        position_part = criteria.position.lower() if criteria.position and criteria.position != 'Not set' else ""
        url = f'{self.BASE_URL}/resumes{location_part}-it-{position_part}/'

        # Build query parameters
        params = {}

        # add page parameter
        params['page'] = self.page
        # Add fixed period
        params['period'] = '5'

        # Add employment type if specified
        if criteria.employment_type is not None and criteria.employment_type != 'Not set':
            emp_id = EmploymentType.get_work_ua_id(criteria.employment_type)
            if emp_id:
                params['employment'] = emp_id

        # Add experience level(s)
        if criteria.experience_level is not None and criteria.experience_level != 'Not set':
            if isinstance(criteria.experience_level, (list, tuple)):
                exp_ids = [level.to_work_ua_id() for level in criteria.experience_level if level != 'Not set']
                if exp_ids:
                    params['experience'] = '+'.join(exp_ids)
            else:
                params['experience'] = criteria.experience_level.to_work_ua_id()

        # Add salary range if specified
        if criteria.min_salary is not None and criteria.min_salary != 'Not set':
            params['salaryfrom'] = str(criteria.min_salary)
        if criteria.max_salary is not None and criteria.max_salary != 'Not set':
            params['salaryto'] = str(criteria.max_salary)

        # Add parameters to URL
        if params:
            url += '?' + urlencode(params)

        return url

    def parse_resume_list(self, html_content: BeautifulSoup) -> List[str]:
        """
        Parse list of resume IDs from search results page
        Example: <div class="card card-hover card-search resume-link" ...><a href="/resumes/1234567/">
        """
        resume_ids = []
        try:
            resume_list_div = html_content.find('div', id='pjax-resume-list')
            if resume_list_div:
                # Find all resume cards
                resume_cards = resume_list_div.find_all('div', class_='card-hover')

                for card in resume_cards:
                    # Get resume link and extract ID
                    link = card.find('a', href=True)
                    if link and '/resumes/' in link['href']:
                        resume_id = link['href'].split('/')[-2]
                        resume_ids.append(resume_id)

        except Exception as e:
            print(f"Error parsing resume list: {str(e)}")

        return resume_ids

    async def parse_resume_details(self, resume_id: str) -> Optional[ResumeData]:
        """
        Parse detailed resume information
        Returns None if parsing fails
        """
        resume_url = f'{self.BASE_URL}/resumes/{resume_id}/'

        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(resume_url, headers=self.headers) as res:
                    if res.status != 200:
                        print(f"Failed to fetch resume {resume_id}, status: {res.status}")
                        return None

                    html_content = await res.text()
                    soup = BeautifulSoup(html_content, 'html.parser')

                    # Find main resume container
                    resume_container = soup.find('div', id=f'resume_{resume_id}')
                    if not resume_container:
                        return None

                try:
                    # Basic information
                    name = resume_container.find('h1', class_='mt-0').text.strip()
                    position = resume_container.find('h2', class_='mt-lg').text.strip()

                    # Parse salary
                    salary_elem = resume_container.find('h2', class_='mt-lg').find_next('p', class_='h5')
                    salary_expectation = None
                    if salary_elem:
                        salary_match = re.search(r'(\d+[\s\d]*)', salary_elem.text)
                        if salary_match:
                            salary_expectation = int(salary_match.group(1).replace(' ', ''))

                    # Location and employment type
                    location = "Unspecified"
                    employment_type = None

                    dl_info = resume_container.find('dl', class_='dl-horizontal')
                    if dl_info:
                        for dt, dd in zip(dl_info.find_all('dt'), dl_info.find_all('dd')):
                            key = dt.text.strip().rstrip(':')
                            value = dd.text.strip()

                            if key == "Місто проживання":
                                location = value
                            elif key == "Зайнятість":
                                if "повна зайнятість" in value.lower():
                                    employment_type = EmploymentType.FULL_TIME
                                elif "неповна зайнятість" in value.lower():
                                    employment_type = EmploymentType.PART_TIME
                                elif any(term in value.lower() for term in ["віддалена", "дистанційно"]):
                                    employment_type = EmploymentType.REMOTE

                    # Calculate experience
                    exp_header = resume_container.find('h2', string=lambda text: text and 'Досвід роботи' in text)
                    if exp_header:
                        # The experiences are in the parent container of the header
                        exp_container = exp_header.parent

                        # Parse the experience block
                        experiences, total_months = await parse_experience_block_work_ua(exp_container)
                    else:
                        experiences = []
                        total_months = 0

                    # Parse skills
                    skills = []
                    skills_section = resume_container.find('h2', string='Знання і навички')
                    if skills_section:
                        for skill in skills_section.find_next('ul').find_all('span', class_='ellipsis'):
                            skills.append(skill.text.strip())

                        return ResumeData(
                            id=resume_id,
                            name=name,
                            position=position,
                            experience=experiences,
                            salary_expectation=salary_expectation,
                            location=location,
                            skills=skills or ["Unspecified"],
                            employment_type=employment_type,
                            source_url=resume_url,
                            total_experience_years=round(total_months) / 12,
                        )

                except Exception as e:
                    print(f"Error parsing resume {resume_id} details: {str(e)}")

        except Exception as e:
            print(f"Network error for resume {resume_id}: {str(e)}")

    async def get_resumes(self, criteria: SearchCriteria, max_pages: int = 1) -> List[ResumeData]:
        """Get resumes with parallel processing"""
        resumes = []

        # Get first page and check for additional pages
        url = self.build_search_url(criteria)

        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(url, headers=self.headers) as res:
                    if res.status != 200:
                        return resumes

                    soup = BeautifulSoup(await res.text(), 'html.parser')

                    # Get resume IDs
                    resume_ids = self.parse_resume_list(soup)

                    # Process resumes in parallel
                    tasks = [self.parse_resume_details(rid) for rid in resume_ids]
                    results = await asyncio.gather(*tasks)

                    # Filter out None results
                    resumes.extend([r for r in results if r is not None])

        except Exception as e:
            print(f"Error fetching resumes: {str(e)}")

        return resumes


class RetriveResumesRobotaua(JobSiteParser):
    BASE_URL = "https://robota.ua"

    def __init__(self, page: int = 1):
        super().__init__()
        self.page = page
        self.list_of_resumes = []

    def build_search_url(self, criteria: SearchCriteria) -> str:
        """
        Builds URL with multiple experience levels support
        Example: .../candidates/java/kharkiv?experienceIds=["0","1","2","3","4","5"]
        """
        # Base URL construction
        position = criteria.position.lower() if criteria.position else "all"
        location = criteria.location.lower() if criteria.location else "ukraine"
        url = f'{self.BASE_URL}/candidates/{position}/{location}'

        # Initialize params list
        params = []

        # Add period (always "All")
        params.append(('period', '"All"'))

        # Add salary if either min or max is specified
        if criteria.min_salary is not None or criteria.max_salary is not None:
            salary_dict = {
                "from": criteria.min_salary if criteria.min_salary is not None else 0,
                "to": criteria.max_salary if criteria.max_salary is not None else 100000
            }
            params.append(('salary', json.dumps(salary_dict)))

        # Always add rubrics for IT category
        params.append(('rubrics', '["1"]'))

        # Add employment type if specified
        if criteria.employment_type is not None:
            schedule_id = EmploymentType.get_robota_ua_id(criteria.employment_type)
            if schedule_id:
                params.append(('scheduleIds', f'["{schedule_id}"]'))

        # Add experience level(s)
        if criteria.experience_level is not None:
            if isinstance(criteria.experience_level, (list, tuple)):
                exp_ids = [level.to_robota_ua_id() for level in criteria.experience_level]
                exp_ids_str = ','.join(f'"{id}"' for id in exp_ids)
                params.append(('experienceIds', f'[{exp_ids_str}]'))
            else:
                exp_id = criteria.experience_level.to_robota_ua_id()
                params.append(('experienceIds', f'["{exp_id}"]'))

        # Build final URL with encoded parameters
        if params:
            param_strings = []
            for key, value in params:
                if key in ['salary', 'rubrics', 'scheduleIds', 'experienceIds', 'period']:
                    param_strings.append(f"{key}={quote(value)}")
                else:
                    param_strings.append(f"{key}={quote(str(value))}")

            url += '?' + '&'.join(param_strings)

        return url

    def parse_resume_list(self, html_content: BeautifulSoup) -> List[str]:
        resume_ids = []
        try:
            resume_cards = html_content.select('alliance-employer-cvdb-cv-list-card')

            for card in resume_cards:
                link = card.select_one('a[href^="/candidates/"]')
                if link:
                    resume_id = link['href'].split('/')[-1]
                    resume_ids.append(resume_id)

        except Exception as e:
            print(f"Error parsing resume list: {str(e)}")

        return resume_ids

    def parse_resume_details(self, resume_id: str) -> ResumeData:
        pass

    async def get_resumes(self, criteria: SearchCriteria, max_pages: int = 1) -> List[ResumeData]:
        """Get resumes with parallel processing"""
        resumes = []

        # Get first page and check for additional pages
        url = self.build_search_url(criteria)

        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(url, headers=self.headers) as res:
                    if res.status != 200:
                        return resumes

                    soup = BeautifulSoup(await res.text(), 'html.parser')

                    # Get resume IDs
                    resume_ids = self.parse_resume_list(soup)
                    print(resume_ids)
        except Exception as e:
            print(f"Error fetching resumes: {str(e)}")

        return resumes
