import csv
import openai
import os
import random
import time
from gtts import gTTS

csv_in = 'filtered.csv'
csv_out = 'sentences.csv'
csv_random = 'random.csv'
en_folder = 'EN_'
pt_folder = 'PT_'

client = openai.OpenAI()

def make_sentences(word):
    prompt = f"""Generate a simple sentence in English using the word '{word}'.
    The sentence should be simple and suitable for an English speaker learning basic Portuguese, and it must end with a period.
    After that, provide the Portuguese translation of the sentence, and ensure it also ends with a period.
    Output format: The English sentence first, followed by the Portuguese translation.
    Omit anything within parenthesis.
    When an English word is prefixed with 'to' it is a verb, example 'to cook'. Process these verbs in a variety of tenses.
    Example output:
    The cat is sleeping.
    O gato está dormindo."""
    
    response = client.chat.completions.create(
        model="gpt-3.5-turbo-1106",
        messages=[{"role": "user", "content": prompt}]
    )

    text = response.choices[0].message.content.strip()
    
    # Expecting output like: "The cat is sleeping. O gato está dormindo."
    if "." in text:
        en_sentence, pt_sentence = text.split(".", 1)
        return en_sentence.strip() + '.', pt_sentence.strip()
    else:
        return None, None

def make_audio(text, file, lang="pt"):
    tts = gTTS(text, lang=lang)
    tts.save(file)

with open(csv_in, "r", encoding="utf-8") as infile, open(csv_out, "w", encoding="utf-8", newline="") as outfile:
    reader = list(csv.reader(infile))
    writer = csv.writer(outfile)

    random_words = random.sample(reader, min(25, len(reader)))

    word_count = 0
    
    for row in random_words:
        word_en = row[0].strip()
        word_pt = row[1].strip()
        
        en_sentence, pt_sentence = make_sentences(word_en)

        en_audio = os.path.join(en_folder, f"{word_en}__en.mp3")
        pt_audio = os.path.join(pt_folder, f"{word_pt}__pt.mp3")

        print(word_en)
        print(f"Making EN audio: '{en_sentence}' -> {en_audio}")
        print(f"Making PT audio: '{pt_sentence}' -> {pt_audio}")

        if not en_sentence or not pt_sentence:
            print(f"Skip {word_en}")
            continue
    
        make_audio(en_sentence, en_audio, lang="en")
        make_audio(pt_sentence, pt_audio, lang="pt")

        front = f"{en_sentence}<br>[sound:{os.path.basename(en_audio)}]"
        back = f"{pt_sentence}<br>[sound:{os.path.basename(pt_audio)}]"

        writer.writerow([front, back])

        word_count += 1
        if word_count >= 50:  # Limit processing to X words
            break

        # Avoid rate limits
        time.sleep(1)



