import csv
import openai
import os
import re
import time
from gtts import gTTS

# Group all settings into a dictionary
config = {
    'api_client': openai.OpenAI(),
    'base_folder': 'Verbs',
    'input_csv': 'filtered.csv',
    'batch_size': 10,
    'max_batches': 100,
    'tenses': {
        'present': {'folder': 'Present', 'csv': 'present.csv'},
        'past': {'folder': 'Past', 'csv': 'past.csv'},
        'future': {'folder': 'Future', 'csv': 'future.csv'},
    }
}

def filter_verbs(filename):
    print(f"Filtering verbs from '{filename}'...")
    with open(filename, mode='r', encoding='utf-8') as infile:
        reader = csv.reader(infile)
        verbs = [(row[0].strip(), row[1].strip()) for row in reader if len(row) >= 2 and row[0].lower().strip().startswith('to ')] # Find verbs with 'to '
    print(f"Found {len(verbs)} verbs to process.")
    return verbs

def fetch_conjugations(pt_verbs_batch):
    if not pt_verbs_batch:
        return ""
    
    joined_verbs = ", ".join(pt_verbs_batch)
    prompt = f"""
    You are a precise Portuguese language expert. Your task is to generate verb conjugations.
    For each of the following Portuguese verbs, provide the simple present, simple past (pretérito perfeito), and simple future conjugations.

    Verbs to conjugate: {joined_verbs}

    Format the output EXACTLY as follows for each verb, with no extra text or explanations:

    VERB: [The Portuguese verb infinitive]
    PRESENT:
    Eu [conjugation]
    Você/Ele/Ela [conjugation]
    Nós [conjugation]
    Vocês/Eles/Elas [conjugation]
    PAST:
    Eu [conjugation]
    Você/Ele/Ela [conjugation]
    Nós [conjugation]
    Vocês/Eles/Elas [conjugation]
    FUTURE:
    Eu [conjugation]
    Você/Ele/Ela [conjugation]
    Nós [conjugation]
    Vocês/Eles/Elas [conjugation]
    ---
    """ # Don't remove '---'. It's a delimiter here.
    
    print(f"Sending {len(pt_verbs_batch)} verbs to the API: {joined_verbs}")
    try:
        response = config['api_client'].chat.completions.create(
            model = "gpt-4o",
            messages = [{"role": "user", "content": prompt}],
            max_tokens = 4096
        )
        return response.choices[0].message.content.strip()
    except Exception as e:
        print(f"An error occurred during the API call: {e}")
        return ""

def parse_conjugations(raw_data):
    parsed_verbs = {} # Define empty dictionary to later add processed verbs to
    verb_blocks = raw_data.strip().split('---') # Separate API response by '---'

    def process_tense_block(text_block):
        lines = [line.strip().split(' ', 1)[1] for line in text_block.strip().split('\n') if ' ' in line.strip()]
        return {'html': "<br>".join(lines), 'gTTS': ", ".join(lines)} # Add <br> for Anki and , for gTTS

    for block in filter(None, verb_blocks):
        verb_match = re.search(r'VERB:\s*(.+)', block, re.IGNORECASE) # ID the infinitive
        if not verb_match: continue # Skip this block if no infinitive is found
        
        verb_infinitive = verb_match.group(1).lower().strip() # Clean infinitive
        parsed_verbs[verb_infinitive] = {} # Store in table

        tense_keys = list(config['tenses'].keys())
        for i, tense in enumerate(tense_keys):
            if i + 1 == len(tense_keys):
                pattern = re.compile(rf'{tense.upper()}:(.*)', re.DOTALL | re.IGNORECASE)
            else:
                next_tense = tense_keys[i + 1].upper()
                pattern = re.compile(rf'{tense.upper()}:(.*?){next_tense}', re.DOTALL | re.IGNORECASE)
            
            match = pattern.search(block)
            if match:
                parsed_verbs[verb_infinitive][tense] = process_tense_block(match.group(1))
    
    return parsed_verbs

def get_existing_verbs(file):
    existing_verbs = set()
    try:
        with open(file, mode='r', encoding='utf-8') as infile:
            reader = csv.reader(infile)
            for row in reader:
                if len(row) >= 2:
                    match = re.search(r'<b>(.*?)</b>', row[1]) # Find the verb within the <b>...</b> tags on the back of the card
                    if match:
                        existing_verbs.add(match.group(1).lower())
    except FileNotFoundError:
        print("Output file not found. Starting from scratch.")
    return existing_verbs

def generate_audio(text, output_path):
    if not text or not text.strip(): # Skip if all_conjugations is empty
        print(f"Skipping audio generation for {output_path} due to empty input.")
        return
    try:
        gTTS(text=text, lang='pt').save(output_path)
    except Exception as e:
        print(f"Error generating audio for {output_path}: {e}")

def main():
    existing_verbs = get_existing_verbs(config['tenses']['present']['csv']) # Find existing verbs
    print(f"Found {len(existing_verbs)} existing verbs in the output files.")

    verb_pairs = filter_verbs(config['input_csv']) # Read 'filtered.csv' and make a list of verb pairs

    # Create a new list with ONLY the new verbs
    new_verb_pairs = [ 
        (en, pt) for en, pt in verb_pairs if pt.lower() not in existing_verbs
    ]

    if not new_verb_pairs:
        print("No new verbs to process. Exiting.")
        return # Stop if there's nothing new to add
    
    print(f"Processing {len(new_verb_pairs)} new verbs.")
    all_conjugations = {} # Define empty dictionary for saving results later
    pt_verbs = [pt for _, pt in new_verb_pairs] # Make a simple list of only Portuguese verbs
    
    for i in range(0, len(pt_verbs), config['batch_size']): # Loop through the Portuguese verbs in batches
        batch_num = (i // config['batch_size']) + 1
        if 0 < config['max_batches'] < batch_num:
            print(f"Reached the testing limit of {config['max_batches']} batches. Stopping.")
            break
        
        print(f"\n--- Processing Batch {batch_num} ---")
        batch = pt_verbs[i:i + config['batch_size']] # Use list slicing to extract a portion of the verb pairs
        response_data = fetch_conjugations(batch) # Make API call and return the raw resonse data
        parsed_data = parse_conjugations(response_data) # Parse the raw text into a structured dictionary
        all_conjugations.update(parsed_data) # Add the parsed verbs into our main collection
        print(f"Successfully parsed {len(parsed_data)} verbs from batch.")
        time.sleep(2) # Add a pause to avoid API limits
    
    print(f"Appending new Anki cards and audio files...")
    writers = { # Create a dictionary for each tense
        tense: csv.writer(open(details['csv'], 'a', newline='', encoding='utf-8'))
        for tense, details in config['tenses'].items()
    }

    for en_verb, pt_verb in new_verb_pairs: # Loop through the new verb pairs
        if pt_verb.lower() in all_conjugations:
            en_verb_clean = re.sub(r'\s*\(.*\)\s*', '', en_verb).strip() # Clean the English infinitive for gTTS by removing text within parenthesis
            
            for tense, data in all_conjugations[pt_verb.lower()].items(): # Loop through each Portuguese verb tense 
                tense_folder = os.path.join(config['base_folder'], config['tenses'][tense]['folder']) # Determine the correct folder for each tense
                os.makedirs(tense_folder, exist_ok=True) # Create folder if it does not exist
                
                audio_file = f"{pt_verb}_{tense}_verb.mp3" # Uniquely name each file with the correct verb and tense
                audio_path = os.path.join(tense_folder, audio_file) # Determine the correct folder for each audio file
                generate_audio(data['gTTS'], audio_path) # Call generate_audio()

                front = f"{en_verb}<br>[sound:{en_verb_clean}_en.mp3]"
                back  = f"<b>{pt_verb}</b><br>{data['html']}<br>[sound:{audio_file}]"
                writers[tense].writerow([front, back]) # Write front and back for each tense
    
    print(f"\nSuccess! Appended new cards to {', '.join(d['csv'] for d in config['tenses'].values())}.") # Note: File handles are left open until the script exits. For more robust applications, use a 'with' block.

if __name__ == "__main__":
    main()