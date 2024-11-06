from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from schemas import SearchCriteria, ExperienceLevel, EmploymentType
from retrive_resumes import RetrieveResumesWorkua, RetriveResumesRobotaua
from filtering import find_matching_candidates
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from datetime import datetime
from aiogram.filters import CommandStart
from app import keyborard as kb

router = Router()


class SearchForm(StatesGroup):
    position = State()
    location = State()
    experience_level = State()
    min_salary = State()
    max_salary = State()
    skills = State()
    employment_type = State()


work_ua = RetrieveResumesWorkua()
robota_ua = RetriveResumesRobotaua()
search_criteria = SearchCriteria()


# First create Start command
# second create Serch command
# third create Filter command
# 1. Position
# When it presses it allows user to enter the postion from the keybord
# 2. Location
# When it presses it allows user to choose location from avalible or type his own
# 3. Experience level
# Also keyoboard with choices
# 4. Salary
# Enter from the keyborad
# 5. Skills
# Also from the keyborad
# 6. Employment type
# Also from the keyborad wtih coices


@router.message(CommandStart())
async def start_command(message: Message):
    await message.answer("Welcome! I'm your job search assistant.")
    await message.answer("Let's build your search criteria.", reply_markup=kb.main)


@router.message(F.text == 'Filters')
async def search_menu(message: Message):
    await message.answer("Please select the filter which you want to apply", reply_markup=kb.filter_catalog)


@router.message(F.text == '🔍 Search for a job')
async def process_search(message: Message, state: FSMContext):
    try:
        data = await state.get_data()

        # Handle experience_level
        exp_level_str = data.get('experience_level')
        try:
            experience_level = ExperienceLevel(exp_level_str) if exp_level_str != 'Not set' else None
        except ValueError:
            experience_level = None

        # Handle employment_type
        emp_type_str = data.get('employment_type')
        try:
            employment_type = EmploymentType(emp_type_str) if emp_type_str != 'Not set' else None
        except ValueError:
            employment_type = None

        # Handle salary with default values and type conversion
        try:
            min_salary = int(data.get('min_salary', 0))
        except (ValueError, TypeError):
            min_salary = 0

        try:
            max_salary = int(data.get('max_salary', 0))
        except (ValueError, TypeError):
            max_salary = 0

        # Handle keywords/skills
        keywords = data.get('skills', [])
        if not keywords or (isinstance(keywords, str) and keywords == 'Not set'):
            keywords = None

        search_criteria.position = data.get('position', 'Not set')
        search_criteria.location = data.get('location', 'Not set') if data.get('location') != 'Not set' else None
        search_criteria.experience_level = experience_level
        search_criteria.min_salary = min_salary if min_salary > 0 else None
        search_criteria.max_salary = max_salary if max_salary > 0 else None
        search_criteria.keywords = keywords
        search_criteria.employment_type = employment_type

        # You might want to validate the criteria
        if search_criteria.position == 'Not set':
            await message.answer("Please set a position before searching.")
            return

        await message.answer("Starting search with your criteria...")
        await retrieve_resumes(message, state, search_criteria)

    except Exception as e:
        await message.answer(f"An error occurred while processing your search criteria. Please try again.")
        # You might want to log the error here
        print(f"Error in process_search: {str(e)}")


async def retrieve_resumes(message: Message, state: FSMContext, criteria: SearchCriteria):
    # Show searching message
    processing_msg = await message.answer("🔍 Searching for matching candidates...")

    work_ua_resumes = await work_ua.get_resumes(criteria)
    robota_ua_resumes = await robota_ua.get_resumes(criteria)
    combined_resumes = work_ua_resumes + robota_ua_resumes
    matching_resumes = find_matching_candidates(combined_resumes, criteria)

    # Update processing message
    await processing_msg.edit_text(f"✅ Found {len(matching_resumes)} matching candidates!")

    # Debugging: print the number of matching resumes
    print(f"Number of matching resumes: {len(matching_resumes)}")

    try:
        # Show top matches (limit to avoid message length issues)
        for index, resume in enumerate(matching_resumes[:10], 1):
            # Determine latest experience
            if resume.experience:
                # Convert start_date strings to datetime objects for comparison
                for exp in resume.experience:
                    exp.start_date_obj = datetime.strptime(exp.start_date, '%m.%Y') if exp.start_date else datetime.min

                latest_exp = max(resume.experience, key=lambda x: x.start_date_obj)
            else:
                latest_exp = None

            # Format experience
            experience_text = ""
            if latest_exp:
                experience_text = (
                    f"🏢 Latest Position: {latest_exp.position} at {latest_exp.company}\n"
                    f"📅 Duration: {latest_exp.start_date} - "
                    f"{'Present' if latest_exp.is_current else latest_exp.end_date}\n"
                )
            else:
                experience_text = "No experience information available."

            # Format skills
            skills_text = "• " + "\n• ".join(resume.skills[:5]) if resume.skills else "Not specified"
            if resume.skills and len(resume.skills) > 5:
                skills_text += f"\n... and {len(resume.skills) - 5} more"

            # Calculate match percentage
            match_percentage = resume.suitable or 0

            # Create message text with emojis and formatting
            message_text = (
                f"👤 Candidate #{index} - {match_percentage}% Match\n\n"
                f"📋 Name: {resume.name}\n"
                f"💼 Position: {resume.position}\n"
                f"📍 Location: {resume.location}\n"
                f"💰 Salary Expectation: {'Not specified' if resume.salary_expectation is None else f'{resume.salary_expectation:,} UAH'}\n"
                f"⏳ Total Experience: {resume.total_experience_years or 0:.1f} years\n\n"
                f"📝 Latest Experience:\n{experience_text}\n"
                f"🔧 Key Skills:\n{skills_text}\n\n"
                f"💼 Employment Type: {resume.employment_type.value if resume.employment_type else 'Not specified'}\n"
                f"🔗 Source: {resume.source_url}"
            )

            # Create inline keyboard for each resume
            keyboard = InlineKeyboardMarkup(
                inline_keyboard=[
                    [
                        InlineKeyboardButton(
                            text="View Full Resume",
                            url=resume.source_url
                        )
                    ],
                ]
            )

            await message.answer(text=message_text, reply_markup=keyboard)

        # If there are more resumes, show a message
        if len(matching_resumes) > 10:
            await message.answer(
                f"ℹ️ Showing top 10 matches out of {len(matching_resumes)} total candidates.\n"
                f"Visit the source websites to see more candidates."
            )

        # Final summary message
        if matching_resumes:
            average_match = sum(r.suitable or 0 for r in matching_resumes) / len(matching_resumes)
        else:
            average_match = 0

        await message.answer(
            f"✨ Search Complete!\n"
            f"📊 Total Matches: {len(matching_resumes)}\n"
            f"🎯 Average Match Score: {average_match:.1f}%\n\n"
            f"Would you like to turn to the next page?",
            reply_markup=kb.nav_keyboard
        )
    except Exception as e:

        # You might want to log the error here
        print(f"Error in retrieve_resumes: {str(e)}")


@router.callback_query(F.data == 'next page')
async def next_page(callback: CallbackQuery, state: FSMContext):
    # Show loading state
    loading_message = await callback.message.answer("🔄 Loading next page...")

    # Increment page counters for both sources
    work_ua.page += 1
    robota_ua.page += 1
    print(work_ua.page)
    # Store current page in state
    await state.update_data(current_page=work_ua.page)

    # Retrieve new resumes with updated page numbers
    await retrieve_resumes(callback.message, state, search_criteria)

    # Remove loading message
    await loading_message.delete()

    # Acknowledge the callback
    await callback.answer("✅ Next page loaded")


@router.message(F.text == 'Filter info' or F.text == 'Filters')
async def process_filtering(message: Message, state: FSMContext):
    # await message.answer("Please enter the position you are looking for:", reply_markup=kb.filter_catalog)
    filter_data = await state.get_data()
    if filter_data:
        filter_status = (
            f"Current filters:\n"
            f"Position: {filter_data.get('position', 'Not set')}\n"
            f"Location: {filter_data.get('location', 'Not set')}\n"
            f"Experience: {filter_data.get('experience_level', 'Not set')}\n"
            f"Salary: {filter_data.get('min_salary', 'Not set')} - {filter_data.get('max_salary', 'Not set')}\n"
            f"Employment type: {filter_data.get('employment_type', 'Not set')}\n"
            f"Keywords: {filter_data.get('keywords', 'Not set')}"
        )
        await message.answer(filter_status)
        await message.answer("Would you like to modify the filters?", reply_markup=kb.filter_catalog)
    else:
        await message.answer("No filtering criteria provided.")


@router.callback_query(F.data == 'position')
async def enter_position(callback: CallbackQuery, state: FSMContext):
    await callback.message.answer("Please enter the position you are looking for:")
    await state.set_state(SearchForm.position)
    await callback.answer()


@router.message(SearchForm.position)
async def set_position(message: Message, state: FSMContext):
    await state.update_data(position=message.text)
    data = await state.get_data()
    await message.answer(f"You have entered the position: {data['position']}")
    await message.answer("Do you want to add another filter?", reply_markup=kb.filter_catalog)
    await state.set_state(None)


# Handling the location filter
@router.callback_query(F.data == 'location')
async def enter_location(callback: CallbackQuery, state: FSMContext):
    await callback.message.answer("Please enter the location where you are looking for:")
    await state.set_state(SearchForm.location)
    await callback.answer()


@router.message(SearchForm.position)
async def set_location(message: Message, state: FSMContext):
    await state.update_data(location=message.text)
    data = await state.get_data()
    await message.answer(f"You have entered the location: {data['location']}")
    await message.answer("Do you want to add another filter?", reply_markup=kb.filter_catalog)
    await state.set_state(None)


# Handling the Salary (min and max) filter
@router.callback_query(F.data == 'salary')
async def enter_min_salary(callback: CallbackQuery, state: FSMContext):
    await callback.message.answer("Please enter the minimum salary you are looking for:")
    await state.set_state(SearchForm.min_salary)
    await callback.answer()


@router.message(SearchForm.min_salary)
async def set_min_salary(message: Message, state: FSMContext):
    await state.update_data(min_salary=message.text)
    data = await state.get_data()
    await message.answer(f"You have entered the minimum salary: {data['min_salary']}")
    await state.set_state(SearchForm.max_salary)
    await message.answer("Please enter the maximum salary you are looking for:")


@router.message(SearchForm.max_salary)
async def set_max_salary(message: Message, state: FSMContext):
    await state.update_data(max_salary=message.text)
    data = await state.get_data()
    await message.answer(f"You have entered the maximum salary: {data['max_salary']}")
    await message.answer("Do you want to add another filter?", reply_markup=kb.filter_catalog)
    await state.set_state(None)


# Handling the skills filter
@router.callback_query(F.data == 'skills')
async def enter_skills(callback: CallbackQuery, state: FSMContext):
    await callback.message.answer("Please enter your skills (separate them with commas):")
    await state.set_state(SearchForm.skills)
    await callback.answer()


@router.message(SearchForm.skills)
async def set_skills(message: Message, state: FSMContext):
    skills_list = [skill.strip() for skill in message.text.split(',')]
    await state.update_data(skills=skills_list)

    data = await state.get_data()
    skills_formatted = '\n• '.join(data['skills'])
    await message.answer(f"You have entered the skills: {skills_formatted}")
    await message.answer("Do you want to add another filter?", reply_markup=kb.filter_catalog)
    await state.set_state(None)


@router.callback_query(F.data == 'experience_level')
async def choose_experience_level(callback: CallbackQuery, state: FSMContext):
    await callback.message.answer("Please choose the experience level:", reply_markup=kb.experience_level)
    await state.set_state(SearchForm.experience_level)
    await callback.answer()


@router.callback_query(SearchForm.experience_level)
async def process_experience_level(callback: CallbackQuery, state: FSMContext):
    experience_display = next(
        (button.text
         for row in kb.experience_level.inline_keyboard
         for button in row
         if button.callback_data == callback.data),
        "Unknown"
    )
    await callback.message.edit_text('You have chosen the experience level: ' + experience_display)
    await state.update_data(experience_level=callback.data)
    await callback.answer('would you like to add another filter?', reply_markup=kb.filter_catalog)
    await state.set_state(None)


@router.callback_query(F.data == 'employment_type')
async def choose_employment_type(callback: CallbackQuery, state: FSMContext):
    await callback.message.answer("Please choose the experience level:", reply_markup=kb.employment_type)
    await state.set_state(SearchForm.employment_type)
    await callback.answer()


@router.callback_query(SearchForm.employment_type)
async def process_experience_level(callback: CallbackQuery, state: FSMContext):
    employment_type_display = next(
        (button.text
         for row in kb.employment_type.inline_keyboard
         for button in row
         if button.callback_data == callback.data),
        "Unknown"
    )
    await callback.message.edit_text('You have chosen the experience level: ' + employment_type_display)
    await state.update_data(employment_type=callback.data)
    await callback.answer()
    await state.set_state(None)
