import unittest
from typing import List
from urllib.parse import urlparse, parse_qs
from retrive_resumes import SearchCriteria, ExperienceLevel, EmploymentType, RetriveResumesRobotaua, \
    RetrieveResumesWorkua

import unittest
from typing import List
from urllib.parse import urlparse, parse_qs


class TestResumeParsers(unittest.TestCase):
    def setUp(self):
        self.robotaua_parser = RetriveResumesRobotaua()
        self.workua_parser = RetrieveResumesWorkua()
        # Add printing of test name
        print(f"\nRunning: {self._testMethodName}")

    def print_urls(self, robota_url: str, work_url: str, test_case: str = ""):
        print(f"\n{'-' * 80}")
        if test_case:
            print(f"Test case: {test_case}")
        print(f"Robota.ua URL: {robota_url}")
        print(f"Work.ua URL:   {work_url}")
        print(f"{'-' * 80}")

    def test_basic_url_structure(self):
        criteria = SearchCriteria(
            position='python',
            location='kyiv'
        )

        robota_url = self.robotaua_parser.build_search_url(criteria)
        work_url = self.workua_parser.build_search_url(criteria)

        self.print_urls(robota_url, work_url, "Basic URL structure")

        parsed_robota = urlparse(robota_url)
        parsed_work = urlparse(work_url)

        self.assertEqual(parsed_robota.scheme, 'https')
        self.assertEqual(parsed_robota.netloc, 'robota.ua')
        self.assertEqual(parsed_robota.path, '/candidates/python/kyiv')

        self.assertEqual(parsed_work.scheme, 'https')
        self.assertEqual(parsed_work.netloc, 'www.work.ua')
        self.assertEqual(parsed_work.path, '/resumes-kyiv-it-python/')

    def test_full_parameters(self):
        criteria = SearchCriteria(
            position='java',
            location='kharkiv',
            experience_level=ExperienceLevel.ONE_TO_TWO,
            employment_type=EmploymentType.FULL_TIME,
            min_salary=10000,
            max_salary=30000
        )

        robota_url = self.robotaua_parser.build_search_url(criteria)
        work_url = self.workua_parser.build_search_url(criteria)

        self.print_urls(robota_url, work_url, "Full parameters")

        parsed_robota = urlparse(robota_url)
        parsed_work = urlparse(work_url)

        params_robota = parse_qs(parsed_robota.query)
        params_work = parse_qs(parsed_work.query)

        print("\nRobota.ua parameters:")
        for key, value in params_robota.items():
            print(f"{key}: {value[0]}")

        print("\nWork.ua parameters:")
        for key, value in params_work.items():
            print(f"{key}: {value[0]}")

        self.assertIn('experienceIds', params_robota)
        self.assertIn('scheduleIds', params_robota)
        self.assertEqual(params_robota['experienceIds'][0], '["3"]')
        self.assertEqual(params_robota['scheduleIds'][0], '["1"]')

        self.assertIn('employment', params_work)
        self.assertIn('experience', params_work)
        self.assertEqual(params_work['employment'][0], '74')
        self.assertEqual(params_work['experience'][0], '165')

    def test_experience_mapping(self):
        test_cases = [
            (ExperienceLevel.NO_EXPERIENCE, "163", "1"),
            (ExperienceLevel.LESS_THAN_1, "164", "2"),
            (ExperienceLevel.ONE_TO_TWO, "165", "3"),
            (ExperienceLevel.TWO_TO_FIVE, "166", "4"),
            (ExperienceLevel.FIVE_TO_TEN, "167", "5"),
            (ExperienceLevel.MORE_THAN_TEN, "168", "6")
        ]

        print("\nTesting experience level mapping:")
        for exp_level, work_id, robota_id in test_cases:
            criteria = SearchCriteria(
                position='python',
                location='kyiv',
                experience_level=exp_level
            )

            robota_url = self.robotaua_parser.build_search_url(criteria)
            work_url = self.workua_parser.build_search_url(criteria)

            self.print_urls(robota_url, work_url, f"Experience Level: {exp_level.value}")

    def test_employment_mapping(self):
        test_cases = [
            (EmploymentType.FULL_TIME, "74", "1"),
            (EmploymentType.PART_TIME, "75", "2"),
            (EmploymentType.REMOTE, "76", "3"),
        ]

        print("\nTesting employment type mapping:")
        for emp_type, work_id, robota_id in test_cases:
            criteria = SearchCriteria(
                position='python',
                location='kyiv',
                employment_type=emp_type
            )

            robota_url = self.robotaua_parser.build_search_url(criteria)
            work_url = self.workua_parser.build_search_url(criteria)

            self.print_urls(robota_url, work_url, f"Employment Type: {emp_type.value}")

    def test_edge_cases(self):
        test_cases = [
            ("Minimal parameters", SearchCriteria(position='python')),
            ("None values", SearchCriteria(
                position='python',
                location=None,
                experience_level=None,
                employment_type=None,
                min_salary=None,
                max_salary=None
            )),
            ("Empty location", SearchCriteria(position='python', location=''))
        ]

        print("\nTesting edge cases:")
        for case_name, criteria in test_cases:
            robota_url = self.robotaua_parser.build_search_url(criteria)
            work_url = self.workua_parser.build_search_url(criteria)

            self.print_urls(robota_url, work_url, case_name)


if __name__ == '__main__':
    runner = unittest.TextTestRunner(verbosity=2, buffer=False)

    test_suite = unittest.TestSuite()
    test_suite.addTest(TestResumeParsers('test_basic_url_structure'))
    test_suite.addTest(TestResumeParsers('test_full_parameters'))
    test_suite.addTest(TestResumeParsers('test_experience_mapping'))
    test_suite.addTest(TestResumeParsers('test_employment_mapping'))
    test_suite.addTest(TestResumeParsers('test_edge_cases'))

    runner.run(test_suite)
