import os
from dotenv import load_dotenv

import glob
import time
import threading
from bs4 import BeautifulSoup
from selenium import webdriver
from colorama import Fore, Style, init

from . import driver
from . import schoology_manager
from . import lthslatin_manager
from .assignments import composition


def login_and_get_session(schoology_url, username, password):
    print('Logging in...')
    session = schoology_manager.login(url=schoology_url, username=username, password=password)
    return session

def select_latin_course(session, schoology_url):
    print('Checking for Latin courses...')
    courses = schoology_manager.get_courses(session, schoology_url)
    sections = schoology_manager.find_latin_courses(courses)
    if not sections:
        print('No Latin courses found, exiting...')
        return None
    if len(sections) == 1:
        return sections[0]
    print('Multiple Latin courses found, please specify which one to use:')
    for i, section in enumerate(sections):
        print(f'{i + 1}: {section.get("section_title")}')
    choice = int(input('Enter the number of the course you want to use: ')) - 1
    if choice < 0 or choice >= len(sections):
        print('Invalid choice, exiting...')
        return None
    return sections[choice]

def spawn_webwindow_and_login(session, schoology_url):
    print('Spawning web window...')
    webwindow = driver.get_driver('Chrome')
    try:
        webwindow.get(schoology_url)
    except:
        print('Unable to load Schoology page, exiting...')
        return None
    print('Injecting cookies...')
    for cookie in session.cookies:
        webwindow.add_cookie({
            'name': cookie.name,
            'value': cookie.value,
            'path': cookie.path,
            'domain': cookie.domain
        })
    return webwindow

def find_lths_latin_app(webwindow, course_url, schoology_url):
    print('Loading course page...')
    try:
        webwindow.get(course_url)
    except:
        print('Unable to load course page, exiting...')
        return None
    soup = BeautifulSoup(webwindow.page_source, 'html.parser')
    app = soup.find(string=lambda text: text and 'LTHSLatin' in text)
    if not app:
        print('Unable to find LTHSLatin app, exiting...')
        return None
    app_href = app.parent.parent['href']
    return schoology_url + app_href

def load_lths_latin_app(webwindow, schoology_app_url, lths_latin_url):
    print('Loading LTHSLatin app...')
    try:
        webwindow.get(schoology_app_url)
    except:
        print('Unable to load LTHSLatin app, exiting...')
        return False
    time.sleep(5) # Implement proper load detection later
    webwindow.get(lths_latin_url)
    return True

def print_colored_square_ascii():
    init(autoreset=True)
    # Define color blocks
    O = Fore.YELLOW + "■" + Style.RESET_ALL  # Orange (use yellow as closest)
    G = Fore.GREEN + "■" + Style.RESET_ALL
    B = Fore.BLUE + "■" + Style.RESET_ALL
    P = Fore.MAGENTA + "■" + Style.RESET_ALL  # Magenta as purple

    print(f"{O} {G}")
    print(f"{B} {P}")

def mode_watcher(webwindow, user):
    global mode, assignment

    mode = None
    assignment = None

    while True:
        mode, assignment = lthslatin_manager.find_mode(webwindow, mode, ['composition'], user)
        time.sleep(1)

def main():
    load_dotenv()

    username = os.getenv('MINERVA_USERNAME'),
    password = os.getenv('MINERVA_PASSWORD'),
    schoology_url = schoology_manager._format_schoology_url(url=os.getenv('SCHOOLOGY_URL'), protocol='https', remove_trailing_slash=True)
    lths_latin_url = os.getenv('LTHSLATIN_URL')
    data_dir = os.getenv('DATA_DIR')
    cache_dir = os.getenv('CACHE_DIR')

    print('Installing NLTK info')
    composition.install_wordnet()

    print('Installing NLTK info complete')

    print('Generating dictionary...')
    composition_dictionary_files: list[str] = glob.glob(os.path.join(data_dir, 'dictionary', '*.json'))
    composition_dictionary = composition.generate_dictionary(composition_dictionary_files)

    session = login_and_get_session(schoology_url, username, password)
    username, password = None, None # Clear from memory

    section = select_latin_course(session, schoology_url)

    if not section:
        return
    
    course_url = schoology_url + "/" + section.get('link')
    webwindow = spawn_webwindow_and_login(session, schoology_url)

    if not webwindow:
        return
    
    schoology_app_url = find_lths_latin_app(webwindow, course_url, schoology_url)

    if not schoology_app_url:
        return
    
    if not load_lths_latin_app(webwindow, schoology_app_url, lths_latin_url):
        return

    print_colored_square_ascii()
    
    user: str = lthslatin_manager.get_user(webwindow)

    print('Spawning mode watcher thread...')
    mode_watcher_thread = threading.Thread(target=mode_watcher, args=(webwindow, user))
    mode_watcher_thread.start()

    while True:
        user_input: str = input('Enter command: ').strip().lower()

        if user_input == 'exit':
            print('Exiting...')
            break
        elif user_input == 'help':
            print('Available commands:')
            print('  exit - Exit the program')
            print('  help - Show this help message')
            print('  solve - Solve the current assignment')
        elif user_input == 'solve':
            if mode == 'composition':
                print('Solving composition assignment...')
                composition.solve(webwindow, False, None, composition_dictionary, True, cache_dir)
            else:
                print('No assignment to solve or unsupported mode.')

        

if __name__ == '__main__':
    main()