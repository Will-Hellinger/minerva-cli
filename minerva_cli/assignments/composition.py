import os
import time
import json
import nltk
import hashlib
import inflect
import selenium
import pyinflect
import unicodedata
from nltk.corpus import wordnet
from googletrans import Translator
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys

def encode_file_name(file_name: str) -> str:
    """
    Encode a file name using SHA-256.

    :param file_name: The file name to encode.
    :return: The encoded file name.
    """

    return hashlib.md5(file_name.encode()).hexdigest()

def save_file(file: bytes, data: dict) -> None:
    """
    Save data to a file.

    :param file: The file object.
    :param data: The data to save as a dictionary.
    :return: None
    """

    file.seek(0)
    json.dump(data, file, indent=4)
    file.truncate()

def install_wordnet():
    """
    Install the WordNet data for NLTK.

    This function downloads the WordNet data if it is not already present.
    """

    try:
        nltk.download('wordnet')
        nltk.download('omw-1.4')
    except Exception as e:
        print(f"Error installing WordNet: {e}")


def strip_accents(text: str) -> str:
    """
    Remove accents from a given text.

    :param text: The text to remove accents from.
    :return: The text without accents as a string.
    """

    return str(''.join(char for char in unicodedata.normalize('NFKD', text) if unicodedata.category(char) != 'Mn')).lower()


def synonym_extractor(phrase: str) -> list[str]:
    """
    Extract synonyms for a given phrase using NLTK WordNet.

    :param phrase: The phrase for which to find synonyms.
    :return: A list of synonyms as strings.
    """

    synonyms: list[str] = []

    for syn in wordnet.synsets(phrase):
        for l in syn.lemmas():
            synonyms.append(l.name())

    return synonyms


def generate_dictionary(file_list: list[str]) -> dict:
    """
    Get the Latin-English dictionary.

    This function retrieves and constructs a Latin-English dictionary from JSON files located in the specified directory.

    :return: A dictionary containing Latin and English word mappings with morphology information.
    """

    dictionary: dict = {}
    latin_dictionary: dict = {}
    english_dictionary: dict = {}

    print(f'Generating dictionary... {len(file_list)} files found')
    start_time = time.time()

    for file in file_list:
        with open(file, mode='r', encoding='utf-8') as f:
            temp_data = json.load(f)
        
        latin_word: str | None = temp_data.get('word', None)

        if latin_word is None:
            continue

        latin_word = latin_word.encode('utf-8').decode('unicode_escape')

        english_words: list[str] | None = temp_data.get('definitions', None)
        latin_dictionary[latin_word] = {"english" : english_words}

        if english_words is None:
            continue

        for english_word in english_words:
            english_word = english_word.lower()
            english_dictionary.setdefault(english_word, [])

            if latin_word not in english_dictionary[english_word]:
                english_dictionary[english_word].append(latin_word)
    
    dictionary['english'] = english_dictionary
    dictionary['latin'] = latin_dictionary

    print(f'Dictionary generated in {time.time() - start_time} seconds')

    return dictionary


def convert_to_base(word: str) -> str:
    """
    Convert an English word to its base form.

    This function takes an English word, analyzes its part of speech (noun or verb), and converts it to its base form
    using linguistic libraries.

    :param word: The English word to be converted.
    :return: The base form of the English word.
    """
    p: inflect.engine = inflect.engine()
    words: list[str] = word.split(' ')
    base_words: list[str] = []

    for word in words:
        if word == '':
            continue

        try:
            word_type: str = nltk.pos_tag(nltk.word_tokenize(word))[0][1]

            if word_type.startswith("N") and p.singular_noun(word) is not False:
                word = p.singular_noun(word)
            elif word_type.startswith("V") and pyinflect.getInflection(word, 'VB')[0] is not False:
                word = pyinflect.getInflection(word, 'VB')[0]

            base_words.append(word)
        except:
            base_words.append(word)

    return ' '.join(base_words)


def translate(word: str, language: str, dictionary: dict | None, use_base: bool = False) -> list:
    """
    Translate a word between Latin and English.

    This function translates a given word between Latin and English. It can use the base form of English words for
    improved translation accuracy.

    :param word: The word to be translated.
    :param language: The starting language ('latin' or 'english') for translation.
    :param dictionary: The Latin-English dictionary.
    :param use_base: Whether to use the base form of English words for translation.
    :return: A list of translations for the input word in the target language.
    """

    if dictionary is None:
        raise ValueError('Dictionary not found')

    language_dict: dict | None = dictionary.get(language.lower(), None)
    
    if language_dict is None:
        raise ValueError(f'Unsupported language: {language}')
    
    if use_base == True:
        word = convert_to_base(word)
    
    if word == "":
        return None
        
    return language_dict.get(word.lower())


def solve(driver: selenium.webdriver, compositions_fallback: bool, translator: Translator | None, dictionary: dict, compositions_synonyms_enabled: bool, cache_path: str | None) -> None:
    """
    Solve Latin-English composition assignments.

    This function solves Latin-English composition assignments by extracting English text, translating it to Latin, and
    entering the Latin translations into text input fields on a web page. It also handles translation fallback using
    Google Translate if enabled.

    :return: None
    """

    parentElement = driver.find_element(By.CLASS_NAME, 'ui-block-a')
    english_text_parents = parentElement.find_elements(By.XPATH, "// p[@style='white-space:pre-wrap;margin-right:2em;font-size:1em']")
    latin_inputs = parentElement.find_elements(By.XPATH, "// div[@class='latin composition ui-input-text ui-shadow-inset ui-body-inherit ui-corner-all ui-textinput-autogrow']")
    assignment_header = driver.find_element(By.ID, 'assessHead')

    all_inputs = []
    english_texts = []

    if cache_path is None:
        cache_path = f'.{os.sep}'
    
    if not cache_path.endswith(os.sep):
        cache_path += os.sep
    
    for english_text_parent in english_text_parents:
        english_texts.append(english_text_parent.text.lower().replace(',', '').replace('.', ''))
    
    for english_text in english_texts:
        if compositions_fallback == True and translator is not None:
            trans_words = str(translator.translate(english_text, dest='la', src='en').text)
            trans_words = trans_words.replace('.', '')
            trans_words = trans_words.replace(',', '')

            trans_words = trans_words.split(' ')
            
        english_text: list[str] = english_text.split(' ')

        processed_words: list[str] = []

        inputs: list[str] = []
        for i in range(len(english_text)):
            for j in range(i+1, len(english_text)+1):
                combined_word = ''.join(english_text[i:j])
                synonyms = None

                if compositions_synonyms_enabled == True:
                    synonyms = synonym_extractor(combined_word)

                if combined_word in processed_words:
                    continue
                    
                processed_words.append(combined_word)

                output = []

                if synonyms is not None or synonyms != [] and compositions_synonyms_enabled == True:
                    for synonym in synonyms:
                        processed_words.append(synonym)

                        synonym_translation = translate(word=synonym, language='english', dictionary=dictionary, use_base=False)
                        base_synonym_translation = translate(word=synonym, language='english', dictionary=dictionary, use_base=False)

                        if synonym_translation is not None and synonym_translation not in output:
                            output.extend(synonym_translation)

                        if base_synonym_translation is not None and base_synonym_translation not in output:
                            output.extend(base_synonym_translation)

                translation_output = translate(word=combined_word, language='english', dictionary=dictionary, use_base=False)
                base_translation_output = translate(word=combined_word, language='english', dictionary=dictionary, use_base=True)

                if translation_output is not None and translation_output not in output:
                    output.extend(translation_output)
                
                if base_translation_output is not None and base_translation_output not in output:
                    output.extend(base_translation_output)

                if output is not None:
                    inputs.append(output)
        
        if compositions_fallback == True and translator is not None:
            inputs.append(trans_words)
        
        all_inputs.append(inputs)
    all_answers = []

    assignment_name = str(assignment_header.text)
    user = assignment_name.split("'s ")[0]
    assignment_name = assignment_name.replace(f"{user}'s ", "")
    assignment_name = encode_file_name(assignment_name)

    if not os.path.exists(f'{cache_path}{assignment_name}.json'):
        with open(f'{cache_path}{assignment_name}.json', mode='w', encoding='utf-8') as file:
            file.write('{\n}')

    for latin_input in latin_inputs:
        driver.execute_script("arguments[0].scrollIntoView();", latin_input)
        default_color = 'green'
        answers = []

        if 'color:red' in str(latin_input.get_attribute('style')).replace(' ', ''):
            default_color = 'red'
        
        span_texts = latin_input.find_elements(By.TAG_NAME, 'span')
        text = latin_input.text

        if default_color == 'green':
            if len(span_texts) != 0:
                for span_text in span_texts:
                    if 'red' in str(span_text.get_attribute('style')):
                        text.replace(span_text.text, '')
                        
            text = text.lower()
            answers.extend(text.split(' '))

        elif default_color == 'red' and len(span_texts) != 0:
            temp_answers = []

            for span_text in span_texts:
                if 'green' in str(span_text.get_attribute('style')) or 'rgb(255,255,255)' in str(span_text.get_attribute('style')).replace(' ', ''):
                    temp_answers.append(str(span_text.text).lower())

            answers.extend(temp_answers)

        all_answers.append(answers)

    cache_file = open(f'{cache_path}{assignment_name}.json', mode='r+', encoding='utf-8')
    data = json.load(cache_file)

    for english_text in english_texts:
        if data.get(english_text) is not None:
            continue
        
        data[english_text] = {'correct' : [], 'incorrect' : []}
    
    save_file(cache_file, data)

    total_inputs: int = 0

    for a in range(0, len(all_inputs)):
        for b in range(0, len(all_inputs[a])):
            same_inputs: list[str] = []

            for c in range(0, len(all_inputs[a][b])):
                if all_inputs[a][b][c] in same_inputs:
                    continue
                
                same_inputs.append(all_inputs[a][b][c])
                total_inputs += 1
    
    print(f'Total inputs: {total_inputs}')

    input_number: int = 0

    for a in range(0, len(all_inputs)):
        for b in range(0, len(all_inputs[a])):
            same_inputs: list[str] = []

            for c in range(0, len(all_inputs[a][b])):
                input_number += 1
                latin_word = strip_accents(all_inputs[a][b][c])

                if latin_word in same_inputs:
                    continue

                driver.execute_script("arguments[0].scrollIntoView();", latin_inputs[a])

                if latin_word in data[english_texts[a]]['incorrect']:
                    continue
                
                elif latin_word in data[english_texts[a]]['correct']:
                    if latin_word not in all_answers[a]:
                        all_answers[a].append(latin_word)
                    
                    continue

                latin_inputs[a].clear()
                latin_inputs[a].send_keys(latin_word)
                latin_inputs[a].send_keys(Keys.ENTER + ' a')

                while len(str(latin_inputs[a].text).split('\n')) != 1:
                    time.sleep(.05)

                time.sleep(.05)

                default_color: str = 'green'
                if 'color:red' in str(latin_inputs[a].get_attribute('style')).replace(' ', ''):
                    default_color = 'red'

                span_texts = latin_inputs[a].find_elements(By.TAG_NAME, 'span')

                if default_color == 'red' and len(span_texts) != 0 and latin_word not in all_answers[a]:
                    all_answers[a].append(latin_word)

                elif default_color == 'green' and len(span_texts) == 0 and latin_word not in all_answers[a]:
                    all_answers[a].append(latin_word)
                
                else:
                    temp_list = data[english_texts[a]]['incorrect']
                    temp_list.append(latin_word)
                    data[english_texts[a]]['incorrect'] = temp_list

                same_inputs.append(latin_word)
                
                if input_number % 100 == 0:
                    data[english_texts[a]]['correct'] = all_answers[a]
                    save_file(cache_file, data)

                    print(f'Completed {input_number} inputs out of {total_inputs}')

        data[english_texts[a]]['correct'] = all_answers[a]
        save_file(cache_file, data)

        (latin_inputs[a]).clear()
        time.sleep(.5)

        used_words = [] #backup repitition check
        driver.execute_script("arguments[0].scrollIntoView();", latin_inputs[a])

        for b in range(0, len(all_answers[a])):
            if all_answers[a][b] in used_words:
                continue
            
            latin_inputs[a].send_keys(all_answers[a][b])
            if b != len(all_answers[a]) - 1:
                latin_inputs[a].send_keys(' ')
            
            used_words.append(all_answers[a][b])

        latin_inputs[a].send_keys(Keys.ENTER)

    cache_file.close()