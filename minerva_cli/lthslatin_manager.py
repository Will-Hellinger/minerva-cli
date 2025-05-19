import time
import selenium.webdriver
from googletrans import Translator
from selenium.webdriver.common.by import By


def check_translation_delay() -> int | None:
    """
    Check the delay for the translation service.

    :return: The delay for the translation service. None if broken.
    """

    try:
        translator = Translator()
        translater_delay = time.time()
        translator.translate('le tit', src='fr', dest='en')
        
        return time.time() - translater_delay
    except:
        return None


def get_user(webdriver: selenium.webdriver) -> str | None:
    """
    Get the user from the Latin site.
    
    :param webdriver: The Selenium WebDriver object.
    :return: The user or None if not
    """

    user: str | None = None

    try:
        user = str(webdriver.find_element(By.CLASS_NAME, 'ui-title').text).split("'s")[0].title()
        print(f'Located user: {user}')
    except:
        print('User not found!')

    return user


def find_mode(webdriver: selenium.webdriver, mode: str | None, available_modes: list[str], user: str | None) -> tuple[str, str]:
    """
    Find the mode in the Latin site.

    :param webdriver: The Selenium WebDriver object.
    :param mode: The mode to find.
    :param available_modes: The available modes to search for.
    :param user: The user to search for.
    :return: A tuple containing the mode and assignment.
    """

    title_elements = webdriver.find_elements(By.CLASS_NAME, 'ui-title')
    assignment: str | None = None

    for element in title_elements:
        for available_mode in available_modes:
            try:
                if available_mode not in str(element.text).lower():
                    continue
                
                if user is not None:
                    assignment = str(element.text).lower().replace(f"{user.lower()}'s ", "")
                else:
                    assignment = str(element.text).lower().split("'s ")

                    if len(assignment) > 1:
                        assignment = assignment[1]
                    else:
                        assignment = None

                if available_mode != mode:
                    mode = available_mode

                break #once it's found the mode it immediately stops to continue with the rest of the while loop, make sure to order modes correctly if they're name dependent
            except:
                pass
    
    if (assignment is not None) and ('launchpad' in assignment or assignment == ""):
        assignment = None
    
    return (mode, assignment)