from typing import List, Set, Optional
from dataclasses import dataclass
import re
import logging
from functools import lru_cache
from schemas import ResumeData, SearchCriteria, ExperienceLevel

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@dataclass
class MatchingWeights:
    """Configurable weights for different matching criteria"""
    skills_weight: float = 25.0
    position_weight: float = 25.0
    experience_weight: float = 35.0
    location_weight: float = 10.0
    employment_type_weight: float = 10.0

    # New parameters for experience scoring
    experience_bonus_cap: float = 0.3  # Maximum bonus for extra experience (30%)
    experience_penalty_rate: float = 0.4  # Penalty rate for less experience


class SkillsMapper:
    """Handles skill matching with synonyms and related terms"""

    def __init__(self):
        self.skill_synonyms = {
            "python": {"python3", "python2", "py"},
            "javascript": {"js", "ecmascript"},
            "postgresql": {"postgres", "psql"},
        }

        self._reverse_map = {}
        for main, synonyms in self.skill_synonyms.items():
            for syn in synonyms:
                self._reverse_map[syn] = main
            self._reverse_map[main] = main

    @lru_cache(maxsize=1000)
    def normalize_skill(self, skill: str) -> str:
        """Normalize skill name using cached results"""
        normalized = re.sub(r'[^\w\s]', '', skill.lower())
        return self._reverse_map.get(normalized, normalized)


class ResumeScorer:
    def __init__(self, weights: Optional[MatchingWeights] = None):
        self.weights = weights or MatchingWeights()
        self.skills_mapper = SkillsMapper()
        self._text_cache = {}

    @lru_cache(maxsize=1000)
    def _normalize_text(self, text: str) -> str:
        if not text:
            return ""
        return re.sub(r'[^\w\s]', '', text.lower())

    def _calculate_skills_score(self, resume_skills: Set[str], search_keywords: Set[str]) -> float:
        if not search_keywords:
            return 0.0

        normalized_resume_skills = {
            self.skills_mapper.normalize_skill(skill)
            for skill in resume_skills
        }
        normalized_keywords = {
            self.skills_mapper.normalize_skill(keyword)
            for keyword in search_keywords
        }

        direct_matches = normalized_resume_skills.intersection(normalized_keywords)
        related_matches = {
            skill for skill in normalized_resume_skills
            for keyword in normalized_keywords
            if (skill in keyword or keyword in skill) and skill not in direct_matches
        }

        score = (len(direct_matches) * 0.7 + len(related_matches) * 0.3) / len(normalized_keywords)
        return score * self.weights.skills_weight

    def _calculate_experience_score(self, resume_exp: ExperienceLevel, target_levels: List[ExperienceLevel]) -> float:
        """
        Calculate experience score with advanced weighting for over/under qualification

        Args:
            resume_exp: Candidate's experience level
            target_levels: Required experience levels

        Returns:
            float: Weighted experience score
        """
        base_score = self.weights.experience_weight

        # Find the closest matching target level
        target_exp_values = [level.value.count('_') for level in target_levels]
        resume_exp_value = resume_exp.value.count('_')

        # Find the minimum experience required
        min_required_exp = min(target_exp_values)

        # Calculate experience difference
        exp_difference = resume_exp_value - min_required_exp

        if exp_difference == 0:  # Exact match
            return base_score
        elif exp_difference > 0:  # More experienced than required
            # Calculate bonus (capped at experience_bonus_cap)
            bonus_factor = min(exp_difference * 0.1, self.weights.experience_bonus_cap)
            return base_score * (1 + bonus_factor)
        else:  # Less experienced than required
            # Calculate penalty (more severe than bonus)
            penalty_factor = abs(exp_difference) * self.weights.experience_penalty_rate
            return max(0, base_score * (1 - penalty_factor))

    def calculate_match_score(self, resume: ResumeData, search_criteria: SearchCriteria) -> float:
        """Calculate match score and update resume's suitability score"""
        total_score = 0

        # 1. Skills Score
        total_score += self._calculate_skills_score(
            set(resume.skills),
            set(search_criteria.keywords or [])
        )

        # 2. Position Score
        if search_criteria.position:
            norm_search_pos = self._normalize_text(search_criteria.position)
            norm_resume_pos = self._normalize_text(resume.position)

            if norm_search_pos == norm_resume_pos:
                total_score += self.weights.position_weight
            else:
                search_words = set(norm_search_pos.split())
                resume_words = set(norm_resume_pos.split())
                overlap = len(search_words.intersection(resume_words))
                total_score += (overlap / len(search_words)) * self.weights.position_weight

        # 3. Enhanced Experience Score
        if search_criteria.experience_level:
            resume_exp = ExperienceLevel.from_years(resume.total_experience_years)
            target_levels = ([search_criteria.experience_level]
                             if isinstance(search_criteria.experience_level, ExperienceLevel)
                             else search_criteria.experience_level)

            total_score += self._calculate_experience_score(resume_exp, target_levels)

        # 4. Location Score
        if search_criteria.location and resume.location:
            norm_search_loc = self._normalize_text(search_criteria.location)
            norm_resume_loc = self._normalize_text(resume.location)

            if norm_search_loc == norm_resume_loc:
                total_score += self.weights.location_weight
            elif norm_search_loc in norm_resume_loc or norm_resume_loc in norm_search_loc:
                total_score += self.weights.location_weight * 0.5

        # 5. Employment Type Score
        if (search_criteria.employment_type and resume.employment_type and
                search_criteria.employment_type == resume.employment_type):
            total_score += self.weights.employment_type_weight

        return round(total_score, 2)


def find_matching_candidates(
        resumes: List[ResumeData],
        search_criteria: SearchCriteria,
        weights: Optional[MatchingWeights] = None
) -> List[ResumeData]:
    """
    Find and rank matching candidates based on search criteria.
    Returns a list of ResumeData objects with updated suitability scores.
    """
    scorer = ResumeScorer(weights)
    logger.info(f"Starting matching process for {len(resumes)} resumes")

    for resume in resumes:
        try:
            # Calculate and set the suitability score
            resume.suitable = scorer.calculate_match_score(resume, search_criteria)
        except Exception as e:
            logger.error(f"Error processing resume {resume.id}: {str(e)}")

    # Sort by suitability score
    matching_resumes = sorted(resumes, key=lambda x: x.suitable, reverse=True)

    logger.info(f"Ranked {len(matching_resumes)} candidates based on suitability")
    return matching_resumes
